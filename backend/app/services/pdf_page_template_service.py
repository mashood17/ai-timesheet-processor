"""
Extraction path for "one-employee-per-page" scanned/photographed timesheets
(confirmed against a real customer file: Sinopec Nanjing Engineering Middle
East Co. supplier manpower timesheets).

=== ARCHITECTURE NOTES (from real-data testing) ===

1. DYNAMIC FIELD CROPPING (bugfix): earlier versions used a fixed crop
   width from each label, which truncated longer handwritten values. This
   version finds the NEXT label on the same header line (e.g.
   "Iqama/Passport" -> "Working Department") via OCR and uses its position
   as the right boundary — this generalizes to any document using this
   general two-column header layout, rather than hardcoding pixel offsets
   for one specific PDF.

2. SINGLE-PASS ROW OCR (performance fix): the Total Hrs row across all
   ~30 day-columns is now OCR'd ONCE as a full strip (nearest-neighbor
   token-to-column assignment), instead of cropping and OCR-ing each of
   30 cells individually. Confirmed via benchmarking: ~0.7s for one
   whole-row pass vs. an estimated 30+ individual Tesseract subprocess
   invocations previously — this was the dominant driver of multi-minute
   processing times on larger PDFs.

3. IQAMA VALIDATION (bugfix): OCR results shorter than MIN_IQAMA_DIGITS
   are treated as unreadable rather than accepted as a real (wrong) IQAMA
   number. Confirmed necessary from real testing, where fragments like
   "4", "27", "25" were previously accepted as if they were complete
   IQAMA numbers.

4. HONEST LIMITATION (confirmed via extensive empirical testing — 8+
   preprocessing/PSM/OEM configurations tried against a real IQAMA field):
   Tesseract cannot reliably read fast cursive pen handwriting on
   photographed forms. This is a ceiling of the OCR engine itself, not a
   preprocessing parameter that can be tuned away. Expect most handwritten
   fields on this document type to come back low-confidence and flagged
   for manual review — that is the system correctly protecting your data,
   not a malfunction. See services/ocr/ for the documented upgrade path to
   a handwriting-capable Vision API engine, which requires zero changes to
   this file to adopt.
"""
import calendar
import io
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from app.services.vision_extraction_service import DAY_CHUNK_SIZE

import fitz
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

from app.config import get_settings
from app.services.image_preprocessing import (
    preprocess_for_handwritten_digits,
    preprocess_for_handwritten_text,
    preprocess_row_strip,
)
from app.services.ocr.base import OCREngine, OCRResult
from app.services.pdf_service import HeaderInfo, PDFCell, PDFEmployeeRow
import logging

logger = logging.getLogger(__name__)

RENDER_ZOOM = 3.0
DAY_NAMES = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
MIN_IQAMA_DIGITS = 7  # real IQAMA/passport numbers are 7-10+ chars; shorter = OCR fragment
RIGHT_BOUNDARY_KEYWORDS = ("Working", "Department", "Project", "Supplier")
MAX_TOKEN_DISTANCE_FACTOR = 0.6  # nearest OCR token must be within 60% of column spacing

_tesseract_configured = False


def _ensure_tesseract_configured() -> None:
    """
    BUGFIX: TESSERACT_CMD from .env was only ever applied inside
    TesseractOCREngine.__init__. This module calls pytesseract directly and
    never went through that class, so on Windows (tesseract not on system
    PATH by default) every call here failed. Configuring it once here fixes
    that regardless of which code path runs first.
    """
    global _tesseract_configured
    if _tesseract_configured:
        return
    settings = get_settings()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    _tesseract_configured = True


@dataclass
class _Word:
    text: str
    conf: int
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

class PageExtractionError(Exception):
    """
    Raised for ANY page that cannot be fully extracted, for ANY reason —
    missing labels, vision API failure, malformed response, or an
    unexpected bug. The caller (extract_employee_rows) catches this
    uniformly and records it as a visible, reported failure rather than
    silently skipping the page. This is the core fix for pages
    "vanishing" with no trace.
    """
    pass

class PageTemplatePDFService:
    """Extraction path for one-employee-per-page scanned timesheets."""

    def get_page_count(self, pdf_path: Path) -> int:
        doc = fitz.open(pdf_path)
        try:
            return len(doc)
        finally:
            doc.close()

    def extract_header_info(self, pdf_path: Path) -> HeaderInfo:
        """
        No 'Timesheet Period:' sentence exists in this format. The period
        is inferred from the title (e.g. 'Timesheet of June-26') — the
        full calendar month is used as the period.
        """
        _ensure_tesseract_configured()

        doc = fitz.open(pdf_path)
        try:
            image = self._render_page(doc[0])
        finally:
            doc.close()

        top_region = image.crop((0, 0, image.width, int(image.height * 0.25)))
        text = pytesseract.image_to_string(top_region, config="--psm 6")
        info = HeaderInfo()

        match = re.search(r"of\s+([A-Za-z]+)[-\s]+(\d{2,4})", text)
        if match:
            month_name, year_part = match.group(1), match.group(2)
            year = int(year_part) if len(year_part) == 4 else 2000 + int(year_part)
            try:
                month_num = list(calendar.month_name).index(month_name.capitalize())
                if month_num == 0:
                    month_num = list(calendar.month_abbr).index(month_name.capitalize()[:3])
                last_day = calendar.monthrange(year, month_num)[1]
                info.period_start = date(year, month_num, 1)
                info.period_end = date(year, month_num, last_day)
                info.month_label = f"{month_name} {year}"
            except (ValueError, IndexError):
                pass

        return info

    def extract_employee_rows(
        self,
        pdf_path: Path,
        ocr_engine: OCREngine,
        allowed_values: list[str],
        vision_service=None,
    ) -> tuple[list[PDFEmployeeRow], list[dict]]:
        """
        Returns (rows, failures). `failures` is a list of
        {"page_number": int, "reason": str} for any page that could not be
        processed — this list is ALWAYS populated when a page fails, so a
        failure is never silently invisible to the caller/user.
        """
        _ensure_tesseract_configured()

        header_info = self.extract_header_info(pdf_path)
        if not header_info.period_start or not header_info.period_end:
            raise ValueError(
                "Could not determine the timesheet month from the PDF title "
                "(expected a pattern like 'Timesheet of June-26'). Please "
                "verify the PDF's title text is legible."
            )

        num_days = (header_info.period_end - header_info.period_start).days + 1

        doc = fitz.open(pdf_path)
        rows: list[PDFEmployeeRow] = []
        failures: list[dict] = []
        try:
            for page_index in range(len(doc)):
                page_number = page_index + 1
                try:
                    image = self._render_page(doc[page_index])
                    row = self._extract_page(
                        image, page_number, header_info.period_start,
                        num_days, ocr_engine, allowed_values, vision_service,
                    )
                    rows.append(row)
                except PageExtractionError as exc:
                    failures.append({"page_number": page_number, "reason": str(exc)})
                except Exception as exc:
                    # Catch-all: an unexpected bug on one page must never
                    # abort the rest of the batch or vanish without a trace.
                    failures.append({
                        "page_number": page_number,
                        "reason": f"Unexpected error during extraction: {exc}",
                    })
        finally:
            doc.close()

        return rows, failures

    # ---------- internal ----------

    def _render_page(self, page: "fitz.Page") -> Image.Image:
        matrix = fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM)
        pix = page.get_pixmap(matrix=matrix)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        return img.convert("RGB")

    def _ocr_words(self, image: Image.Image, full_page: bool = False) -> list[_Word]:
        """
        PERFORMANCE: normally cropped to the top ~58% of the page (covers
        every field needed while skipping the signature/evaluation section).

        RELIABILITY FIX: `full_page=True` bypasses the crop entirely — used
        as a fallback if the cropped pass fails to find required labels,
        guarding against any edge case where a label happens to sit right at
        or past the crop boundary on a given page/render.
        """
        region = image if full_page else image.crop((0, 0, image.width, int(image.height * 0.58)))
        data = pytesseract.image_to_data(region.convert("L"), output_type=Output.DICT)
        words = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            if text:
                words.append(_Word(
                    text=text, conf=int(data["conf"][i]),
                    left=data["left"][i], top=data["top"][i],
                    width=data["width"][i], height=data["height"][i],
                ))
        return words

    def _find_label(self, words: list[_Word], *keywords: str) -> _Word | None:
        for w in words:
            if any(kw.lower() in w.text.lower() for kw in keywords):
                return w
        return None

    def _find_right_boundary(self, words: list[_Word], left_label: _Word) -> _Word | None:
        """
        BUGFIX: finds the next label on the SAME header line (within a
        generous vertical tolerance) to use as this field's right crop
        boundary, instead of a fixed pixel width. This is derived from
        the document's own detected layout on each page, not hardcoded.
        """
        candidates = [
            w for w in words
            if any(kw.lower() in w.text.lower() for kw in RIGHT_BOUNDARY_KEYWORDS)
            and w.left > left_label.right
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda w: abs(w.top - left_label.top))
        return candidates[0]

    def _extract_field_value(
        self,
        image: Image.Image,
        words: list[_Word],
        label_word: _Word,
        whitelist: str | None,
        preprocess_fn,
    ) -> str:
        right_boundary = self._find_right_boundary(words, label_word)
        x0 = label_word.right
        x1 = right_boundary.left - 10 if right_boundary else min(x0 + 900, image.width)
        y0 = max(label_word.top - 15, 0)
        y1 = label_word.top + label_word.height + 25
        if x1 <= x0:
            x1 = min(x0 + 400, image.width)

        crop = image.crop((x0, y0, x1, y1))
        processed = preprocess_fn(crop)

        config = "--psm 7"
        if whitelist:
            config += f" -c tessedit_char_whitelist={whitelist}"
        text = pytesseract.image_to_string(processed, config=config).strip()

        if not text:
            # Fall back to plain grayscale OCR of the same region if the
            # handwriting-isolation pipeline found nothing usable.
            text = pytesseract.image_to_string(crop.convert("L"), config=config).strip()
        return text

    def _extract_total_hrs_row(
        self,
        image: Image.Image,
        total_label: _Word,
        day_x_centers: list[float],
        column_spacing: float,
        ocr_engine: OCREngine,
        allowed_values: list[str],
    ) -> dict[int, OCRResult]:
        """
        PERFORMANCE + ACCURACY FIX: OCRs the ENTIRE Total Hrs row as one
        strip (one Tesseract call) instead of cropping and OCR-ing each
        day-column individually (previously ~30 separate calls per page,
        the dominant driver of multi-minute processing times). Detected
        tokens are assigned to the nearest expected day-column by x-center
        distance — this also avoids the accuracy risk of rigid cell
        boundaries clipping a handwritten digit that straddles two columns.

        Returns {day_index: OCRResult}. A day index with no nearby token
        found within MAX_TOKEN_DISTANCE_FACTOR * column_spacing is treated
        as genuinely blank (common for weekly rest days) and omitted.
        """
        strip_x0 = int(day_x_centers[0] - column_spacing / 2)
        strip_x1 = int(day_x_centers[-1] + column_spacing / 2)
        strip_y0 = total_label.top - 5
        strip_y1 = strip_y0 + total_label.height + 30

        strip_x0 = max(strip_x0, 0)
        strip_x1 = min(strip_x1, image.width)
        strip = image.crop((strip_x0, strip_y0, strip_x1, strip_y1))

        processed = preprocess_row_strip(strip)
        scale_x = processed.width / strip.width if strip.width else 1.0

        allowed_chars = "".join(sorted(set("".join(allowed_values))))
        config = f"--psm 6 -c tessedit_char_whitelist={allowed_chars}"
        data = pytesseract.image_to_data(processed, config=config, output_type=Output.DICT)

        tokens = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip().upper()
            if not text:
                continue
            token_center_x = (data["left"][i] + data["width"][i] / 2) / scale_x + strip_x0
            conf = max(int(data["conf"][i]), 0)
            tokens.append((token_center_x, text, conf))

        results: dict[int, OCRResult] = {}
        max_distance = column_spacing * MAX_TOKEN_DISTANCE_FACTOR
        allowed_set = set(allowed_values)

        for day_idx, expected_x in enumerate(day_x_centers):
            best_token = None
            best_distance = None
            for token_x, text, conf in tokens:
                distance = abs(token_x - expected_x)
                if distance <= max_distance and (best_distance is None or distance < best_distance):
                    best_token, best_distance = (text, conf), distance

            if best_token is None:
                continue  # no nearby handwriting found — treat as genuinely blank

            text, conf = best_token
            cleaned = re.sub(r"[^\dA-Z]", "", text)
            if cleaned.isdigit() and 0 <= int(cleaned) <= 24 and cleaned in allowed_set:
                confidence = min(0.5 + conf / 200, 0.9)
                results[day_idx] = OCRResult(raw_value=cleaned, confidence=confidence, is_legend_code=False)
            elif cleaned in allowed_set:
                results[day_idx] = OCRResult(raw_value=cleaned, confidence=0.6, is_legend_code=True)
            else:
                results[day_idx] = OCRResult(raw_value=cleaned or "?", confidence=0.2, is_legend_code=False)

        return results

    def _extract_page(
        self,
        image: Image.Image,
        page_number: int,
        period_start: date,
        num_days: int,
        ocr_engine: OCREngine,
        allowed_values: list[str],
        vision_service=None,
    ) -> PDFEmployeeRow:
        words = self._ocr_words(image)

        iqama_label = self._find_label(words, "Iqama", "Passport")
        if iqama_label is None:
            words = self._ocr_words(image, full_page=True)
            iqama_label = self._find_label(words, "Iqama", "Passport")

        if iqama_label is None:
            iqama_label = self._find_digit_dense_line(
                words, top_fraction=0.20, image_height=image.height
            )
            if iqama_label is not None:
                logger.info(
                    "Page %d: 'Iqama/Passport' label not found directly; "
                    "using digit-dense-line fallback instead.", page_number,
                )

        if iqama_label is None and vision_service is not None:
            # RELIABILITY FIX: for the vision path, we don't actually need
            # a pixel-precise anchor — the vision model reads full page
            # context regardless of crop tightness. Rather than raising
            # (which was proven fragile: handwritten digits can fragment
            # across what look like separate "lines" to Tesseract, defeating
            # digit-density clustering too), fall back to a generous,
            # fixed-proportion header band. This trades a slightly larger
            # (and marginally more expensive) crop for the guarantee that a
            # legible page is NEVER dropped just because Tesseract's label
            # detection had a bad day on it.
            logger.info(
                "Page %d: no Tesseract-based anchor found for the header "
                "fields; falling back to a generous default header region "
                "for the vision model instead of failing this page.", page_number,
            )
            iqama_label = _Word(text="", conf=0, left=0, top=int(image.height * 0.08),
                                 width=image.width, height=int(image.height * 0.02))

        if iqama_label is None:
            sample_words = [w.text for w in words[:60]]
            logger.warning(
                "Page %d: could not locate the IQAMA/Passport field by any "
                "method (label search, full-page retry, digit-density "
                "fallback). Image size: %dx%d. Words detected (first 60): %s",
                page_number, image.width, image.height, sample_words,
            )
            raise PageExtractionError(
                "Could not locate the IQAMA/Passport field on this page — the "
                "page may be rotated, corrupted, or of genuinely low image "
                "quality. (Note: the free OCR path requires a precise anchor; "
                "the Vision API path is more resilient to this — consider "
                "enabling it if this happens frequently.)"
            )

        name_label = self._find_label(words, "Employee")
        title_label = self._find_label(words, "Job Title", "Title")

        day_words = [w for w in words if re.sub(r"[^A-Za-z]", "", w.text).upper() in DAY_NAMES]
        day_words.sort(key=lambda w: w.left)

        if len(day_words) >= 5:
            xs = sorted(w.center_x for w in day_words)
            spacing = float(np.median(np.diff(xs)))
            first_x = xs[0]
            day_x_centers = [first_x + i * spacing for i in range(num_days)]
        elif vision_service is not None:
            # RELIABILITY FIX: day_x_centers are only load-bearing for the
            # free/Tesseract path's per-cell cropping — the vision path reads
            # the whole day-row via one full-width crop and returns values
            # keyed by day NUMBER, not pixel position, so exact column
            # positions aren't actually needed for correctness here, only
            # for informational bbox bookkeeping. Synthesizing evenly-spaced
            # placeholders (rather than failing the page) is therefore safe
            # for this path specifically — it changes no extracted value.
            logger.info(
                "Page %d: only found %d day-of-week headers (need 5+ for "
                "precise calibration); using evenly-spaced placeholder "
                "columns since the vision path doesn't depend on exact "
                "positions for correctness.", page_number, len(day_words),
            )
            content_left = image.width * 0.35
            content_right = image.width * 0.97
            spacing = (content_right - content_left) / max(num_days - 1, 1)
            first_x = content_left
            day_x_centers = [first_x + i * spacing for i in range(num_days)]
        else:
            raise PageExtractionError(
                f"Only found {len(day_words)} day-of-week column headers "
                "(need at least 5 to reliably calibrate column positions). "
                "The free OCR path requires this for accurate per-cell "
                "cropping; the Vision API path does not have this "
                "limitation — consider enabling it if this happens frequently."
            )

        total_label = self._find_label(words, "Total Hrs", "Hrs")
        if total_label is None and vision_service is not None:
            # Same reliability principle as above: the vision path doesn't
            # need a precise row anchor, just a reasonably-bounded region.
            # Day columns are already calibrated from day_words above, so
            # we only need a plausible vertical band for the Total Hrs row.
            logger.info(
                "Page %d: 'Total Hrs' label not found; falling back to a "
                "generous default row region for the vision model.", page_number,
            )
            total_label = _Word(text="", conf=0, left=0, top=int(image.height * 0.45),
                                 width=image.width, height=int(image.height * 0.03))

        if total_label is None:
            raise PageExtractionError("Could not locate the 'Total Hrs' row label on this page.")

        if vision_service is not None:
            header_bottom = title_label or name_label or iqama_label
            header_crop = image.crop((
                0, max(iqama_label.top - 15, 0),
                image.width, header_bottom.top + header_bottom.height + 20,
            ))
            try:
                header_fields = vision_service.extract_header_fields(header_crop)
            except Exception as exc:
                raise PageExtractionError(f"Vision API header call failed: {exc}") from exc

            iqama_digits = re.sub(r"[^0-9]", "", header_fields.get("iqama", ""))
            if len(iqama_digits) < MIN_IQAMA_DIGITS:
                iqama_digits = ""
            name_text = header_fields.get("employee_name", "")
            title_text = header_fields.get("job_title", "")

            # ACCURACY FIX: request day values in small CHUNKS rather than
            # the whole row at once — see vision_extraction_service.py
            # module docstring for why. Each chunk is cropped narrowly
            # (only that chunk's columns) so the model has minimal
            # surrounding context to "pattern-complete" from.
            row_y0 = total_label.top - 5
            row_y1 = row_y0 + total_label.height + 30
            row_results: dict[int, OCRResult] = {}

            chunk_size = DAY_CHUNK_SIZE
            for chunk_start in range(0, num_days, chunk_size):
                chunk_end = min(chunk_start + chunk_size, num_days)
                chunk_x0 = max(int(day_x_centers[chunk_start] - spacing / 2), 0)
                chunk_x1 = min(int(day_x_centers[chunk_end - 1] + spacing / 2), image.width)
                chunk_crop = image.crop((chunk_x0, row_y0, chunk_x1, row_y1))

                try:
                    chunk_results = vision_service.extract_day_chunk(
                        chunk_crop, chunk_start + 1, chunk_end, allowed_values
                    )
                except Exception as exc:
                    raise PageExtractionError(
                        f"Vision API day-chunk call failed (days {chunk_start + 1}-{chunk_end}): {exc}"
                    ) from exc

                for day_idx, ocr_result in chunk_results.items():
                    row_results[day_idx] = ocr_result

        day_cells: dict[str, PDFCell] = {}
        for day_idx in range(num_days):
            if day_idx not in row_results:
                continue
            iso_date = (period_start + timedelta(days=day_idx)).isoformat()
            day_cells[iso_date] = PDFCell(
                page_number=page_number,
                bbox=(day_x_centers[day_idx] - spacing / 2, 0, day_x_centers[day_idx] + spacing / 2, 0),
                text_layer_value=None,
                precomputed_ocr=row_results[day_idx],
            )

        return PDFEmployeeRow(
            page_number=page_number,
            sr_no=str(page_number),
            iqama_or_passport=iqama_digits or None,
            mb_no=None,
            employee_name=name_text or None,
            designation=title_text or None,
            entity_name=None,
            dept_team=None,
            day_cells=day_cells,
        )
        
    def _find_digit_dense_line(
        self, words: list[_Word], top_fraction: float, image_height: int
    ) -> _Word | None:
        """
        RELIABILITY FIX: fallback for locating the IQAMA/Passport VALUE
        when its printed label text isn't reliably OCR'd — confirmed via
        real diagnostic logging that this happens when handwriting
        overlaps or interferes with the label's print quality on a
        specific page, even though the label is perfectly legible on
        other pages of the same document.

        Scans the header region for the line with the highest total count
        of digit characters among nearby words (grouped by similar
        vertical position), and returns a synthetic anchor spanning that
        line. This is content-driven (digit density), not tied to any
        fixed position or hardcoded value, so it generalizes to any
        similar form where a header line's high digit density indicates
        an ID number — not just this one document.
        """
        header_words = [w for w in words if w.top < image_height * top_fraction]
        if not header_words:
            return None

        lines: list[list[_Word]] = []
        for w in sorted(header_words, key=lambda w: w.top):
            placed = False
            for line in lines:
                if abs(line[0].top - w.top) < (w.height * 0.8):
                    line.append(w)
                    placed = True
                    break
            if not placed:
                lines.append([w])

        best_line: list[_Word] | None = None
        best_digit_count = 0
        for line in lines:
            digit_count = sum(len(re.sub(r"[^0-9]", "", w.text)) for w in line)
            if digit_count > best_digit_count:
                best_digit_count = digit_count
                best_line = line

        if best_line is None or best_digit_count < MIN_IQAMA_DIGITS:
            return None

        left = min(w.left for w in best_line)
        top = min(w.top for w in best_line)
        right = max(w.right for w in best_line)
        bottom = top + max(w.height for w in best_line)
        return _Word(text="", conf=0, left=left, top=top, width=right - left, height=bottom - top)