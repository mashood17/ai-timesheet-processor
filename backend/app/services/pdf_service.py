"""
Section 3/5: reads the monthly timesheet PDF.

Two-track extraction:
  1. pdfplumber — pulls the text layer (header block + IQAMA numbers, which
     Section 3 says are typed, not handwritten) and detects the bordered
     grid table structure using its line-based table strategy.
  2. PyMuPDF (fitz) — rasterizes each page at high DPI so day-cells can be
     cropped into individual images and handed to the OCREngine (Section 2)
     for the handwritten hour/leave-code values.

BUGFIX (found during testing): cell bounding boxes returned by pdfplumber's
line-based table detection can sit flush against the ruled grid lines. When
a neighboring column's text runs close to that shared border, extracting
text from the exact bbox occasionally picks up a stray leading character
from the next column (e.g. "SUMAN" + first letter of "SCAFFOLDING..." ->
"SUMAN S"). Fix: every cell bbox is inset by a small margin on all sides
before text extraction or image cropping, so extraction stays safely
within each cell's actual content area rather than touching its border.

PERFORMANCE FIX (found during testing): rasterizing cell images previously
reopened the PDF with PyMuPDF on every single cell call — for a 900-row,
30-day timesheet that's ~27,000 redundant file opens. The document is now
opened once per processing run and reused across every crop call.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from app.utils.date_utils import generate_sequential_dates, parse_timesheet_period

HEADER_FIELD_PATTERNS = {
    "company_name": re.compile(r"Company Name\s*:\s*(.+)", re.IGNORECASE),
    "subject_project": re.compile(r"Subject\s*/\s*Project\s*:\s*(.+)", re.IGNORECASE),
    "entity_supplier": re.compile(r"Entity\s*/\s*Supplier\s*:\s*(.+)", re.IGNORECASE),
    "month_label": re.compile(r"\b(20\d{2})[-\s]?([A-Za-z]+)\b"),
}

COLUMN_KEYWORDS = {
    "sr_no": ["sr.", "sr no", "s.no"],
    "iqama_or_passport": ["iqama", "passport"],
    "mb_no": ["mb no", "mb.no", "mb#"],
    "employee_name": ["employee name", "name"],
    "designation": ["designation"],
    "entity_name": ["entity name"],
    "dept_team": ["dept", "team"],
    "total_hours": ["total hours"],
    "total_a": ['total "a"', "total a"],
    "remarks": ["remarks"],
    "hourly_rate": ["hourly rate", "rate"],
    "total_amount": ["total amount", "amount"],
}

LEGEND_CODES = {
    "A", "AB", "AL", "CO", "DA", "HL", "ML", "NJ", "PA", "PH",
    "PL", "R", "RL", "SL", "SP", "T", "TO", "UL", "WD", "WE", "WI",
}

# BUGFIX: inset margin (in PDF points) applied to every cell bbox before
# extraction, to stay clear of ruled grid lines and adjacent-column bleed.
CELL_INSET_POINTS = 2.0


@dataclass
class HeaderInfo:
    company_name: str | None = None
    subject_project: str | None = None
    entity_supplier: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    month_label: str | None = None


@dataclass
class PDFCell:
    page_number: int
    bbox: tuple[float, float, float, float]
    text_layer_value: str | None
    # Populated only by PageTemplatePDFService (scanned/photographed,
    # per-employee-per-page formats with no vector table lines to defer
    # cropping against). When set, process_routes.py uses this value
    # directly instead of the text-layer-then-crop-and-OCR path used for
    # the ruled-table format.
    precomputed_ocr: object | None = None


@dataclass
class PDFEmployeeRow:
    page_number: int
    sr_no: str | None
    iqama_or_passport: str | None
    mb_no: str | None
    employee_name: str | None
    designation: str | None
    entity_name: str | None
    dept_team: str | None
    day_cells: dict[str, PDFCell] = field(default_factory=dict)
    total_hours_text: str | None = None
    total_a_text: str | None = None
    remarks: str | None = None
    hourly_rate_text: str | None = None
    total_amount_text: str | None = None


def _inset_bbox(bbox: tuple[float, float, float, float], margin: float) -> tuple[float, float, float, float]:
    """
    Shrinks a bbox inward by `margin` points on all sides. Guards against
    degenerate boxes (very narrow/short cells) by never inverting the box —
    if insetting would flip x0 > x1 or top > bottom, it falls back to a
    smaller margin that still leaves a valid, non-empty box.
    """
    x0, top, x1, bottom = bbox
    width = x1 - x0
    height = bottom - top

    safe_margin_x = min(margin, max(width / 2 - 0.5, 0))
    safe_margin_y = min(margin, max(height / 2 - 0.5, 0))

    return (x0 + safe_margin_x, top + safe_margin_y, x1 - safe_margin_x, bottom - safe_margin_y)


class PDFService:
    def get_page_count(self, pdf_path: Path) -> int:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
        
    def detect_format(self, pdf_path: Path) -> str:
        """
        Returns 'ruled_table' (row-per-employee, e.g. the SAC factory
        format — has either a text layer or vector table lines) or
        'scanned_page_per_employee' (e.g. the Sinopec supplier format —
        pure photographed/scanned images, no text layer, no vector lines).
        This determines which extraction path process_routes.py and
        mapping_routes.py should use for a given upload.
        """
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return "ruled_table"
            page = pdf.pages[0]
            has_text = len(page.chars) > 0
            has_vector_lines = len(page.lines) > 0 or len(page.rects) > 0
            has_image_only = len(page.images) > 0 and not has_text and not has_vector_lines
            return "scanned_page_per_employee" if has_image_only else "ruled_table"

    def extract_header_info(self, pdf_path: Path) -> HeaderInfo:
        with pdfplumber.open(pdf_path) as pdf:
            first_page_text = pdf.pages[0].extract_text() or ""

        info = HeaderInfo()
        for field_name, pattern in HEADER_FIELD_PATTERNS.items():
            match = pattern.search(first_page_text)
            if not match:
                continue
            if field_name == "month_label":
                info.month_label = match.group(0).strip()
            else:
                setattr(info, field_name, match.group(1).strip())

        period = parse_timesheet_period(first_page_text)
        if period:
            info.period_start, info.period_end = period

        return info

    def extract_employee_rows(self, pdf_path: Path) -> list[PDFEmployeeRow]:
        header_info = self.extract_header_info(pdf_path)
        if not header_info.period_start or not header_info.period_end:
            raise ValueError(
                "Could not determine the timesheet period from the PDF header. "
                "This must be resolved manually before day-column alignment can proceed."
            )
        expected_dates = generate_sequential_dates(header_info.period_start, header_info.period_end)

        rows: list[PDFEmployeeRow] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                }
                tables = page.find_tables(table_settings=table_settings)
                if not tables:
                    continue

                table = max(tables, key=lambda t: len(t.rows))
                header_row_cells = table.rows[0].cells
                header_texts = [
                    self._extract_cell_text(page, c) if c else ""
                    for c in header_row_cells
                ]
                header_texts = [t.lower() for t in header_texts]

                column_index = self._map_columns(header_texts)
                day_column_indices = self._map_day_columns(
                    header_texts, column_index, expected_dates
                )

                for row in table.rows[1:]:
                    cells = row.cells
                    if not any(cells):
                        continue

                    def cell_text(col_key: str) -> str | None:
                        idx = column_index.get(col_key)
                        if idx is None or idx >= len(cells) or cells[idx] is None:
                            return None
                        return self._extract_cell_text(page, cells[idx]) or None

                    sr_no = cell_text("sr_no")
                    iqama = cell_text("iqama_or_passport")
                    if not sr_no and not iqama:
                        continue

                    employee_row = PDFEmployeeRow(
                        page_number=page_index,
                        sr_no=sr_no,
                        iqama_or_passport=iqama,
                        mb_no=cell_text("mb_no"),
                        employee_name=cell_text("employee_name"),
                        designation=cell_text("designation"),
                        entity_name=cell_text("entity_name"),
                        dept_team=cell_text("dept_team"),
                        total_hours_text=cell_text("total_hours"),
                        total_a_text=cell_text("total_a"),
                        remarks=cell_text("remarks"),
                        hourly_rate_text=cell_text("hourly_rate"),
                        total_amount_text=cell_text("total_amount"),
                    )

                    for iso_date, col_idx in day_column_indices.items():
                        if col_idx >= len(cells) or cells[col_idx] is None:
                            continue
                        bbox = cells[col_idx]
                        text_val = self._extract_cell_text(page, bbox)
                        employee_row.day_cells[iso_date] = PDFCell(
                            page_number=page_index,
                            bbox=bbox,
                            text_layer_value=text_val or None,
                        )

                    rows.append(employee_row)

        return rows

    def open_document(self, pdf_path: Path) -> fitz.Document:
        """
        PERFORMANCE FIX: open the PDF once per processing run, then pass the
        returned document into crop_cell_image_from_doc for every cell. The
        caller is responsible for closing it (use a try/finally or context).
        """
        return fitz.open(pdf_path)

    def crop_cell_image_from_doc(
        self, doc: fitz.Document, page_number: int, bbox: tuple, dpi: int = 300
    ) -> bytes:
        """
        Rasterizes one cell region using an already-open fitz.Document.
        page_number is 1-indexed to match pdfplumber's convention.
        Applies the same inset-margin bugfix as text extraction, so the OCR
        engine never sees a sliver of the neighboring column either.
        """
        inset_bbox = _inset_bbox(bbox, CELL_INSET_POINTS)
        page = doc[page_number - 1]
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        clip = fitz.Rect(*inset_bbox)
        pix = page.get_pixmap(matrix=matrix, clip=clip)
        return pix.tobytes("png")

    def crop_cell_image(self, pdf_path: Path, page_number: int, bbox: tuple, dpi: int = 300) -> bytes:
        """
        Convenience single-cell version (opens+closes its own document).
        Kept for callers that only need one crop; process_routes.py now uses
        open_document + crop_cell_image_from_doc instead for bulk work.
        """
        doc = self.open_document(pdf_path)
        try:
            return self.crop_cell_image_from_doc(doc, page_number, bbox, dpi)
        finally:
            doc.close()

    # ---------- internal helpers ----------

    def _extract_cell_text(self, page, bbox: tuple[float, float, float, float]) -> str:
        """
        BUGFIX (hardened): rather than cropping by bounding-box overlap
        (which can still include a character that only barely intersects
        the cell edge — see CELL_INSET_POINTS comment above), this filters
        by whether each character's CENTER POINT falls inside the inset
        cell area. A stray glyph overflowing from a neighboring column
        (as seen in testing) will almost never have its center inside the
        wrong cell, so this is meaningfully more robust than a plain crop.
        """
        x0, top, x1, bottom = _inset_bbox(bbox, CELL_INSET_POINTS)

        def char_center_inside(obj: dict) -> bool:
            if obj.get("object_type") != "char":
                return True
            char_center_x = (obj["x0"] + obj["x1"]) / 2
            char_center_y = (obj["top"] + obj["bottom"]) / 2
            return x0 <= char_center_x <= x1 and top <= char_center_y <= bottom

        filtered_page = page.filter(char_center_inside)
        cropped = filtered_page.crop((x0, top, x1, bottom), strict=False)
        text = cropped.extract_text()
        return text.strip() if text else ""

    def _map_columns(self, header_texts: list[str]) -> dict[str, int]:
        column_index: dict[str, int] = {}
        for col_key, keywords in COLUMN_KEYWORDS.items():
            for idx, text in enumerate(header_texts):
                if any(kw in text for kw in keywords):
                    column_index[col_key] = idx
                    break
        return column_index

    def _map_day_columns(
        self,
        header_texts: list[str],
        column_index: dict[str, int],
        expected_dates: list[date],
    ) -> dict[str, int]:
        start_col = column_index.get("dept_team")
        end_col = column_index.get("total_hours")
        if start_col is None or end_col is None or end_col <= start_col + 1:
            return {}

        day_col_range = list(range(start_col + 1, end_col))
        mapping: dict[str, int] = {}
        for i, col_idx in enumerate(day_col_range):
            if i >= len(expected_dates):
                break
            mapping[expected_dates[i].isoformat()] = col_idx
        return mapping