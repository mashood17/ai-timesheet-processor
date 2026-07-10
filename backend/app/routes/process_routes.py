"""
Section 7: POST /api/process — the core pipeline (Section 5, steps 7-12).

PERFORMANCE FIX: the PDF is now opened once per request (via
PDFService.open_document) and reused across every cell crop, instead of
reopening the file for every single day-cell. For a 900-row, ~30-day
timesheet this eliminates roughly 27,000 redundant file opens.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_username
from app.config import Settings, get_settings
from app.models.process_models import (
    DayCellResult,
    DuplicateEntry,
    EmployeeProcessResult,
    ProcessRequest,
    ProcessResponse,
    UnmatchedEntry,
)
from app.services.matching_service import MatchingService, normalize_id
from app.services.ocr.factory import get_ocr_engine
from app.services.pdf_service import PDFService
from app.services.session_service import SessionService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/process", tags=["process"], dependencies=[Depends(get_current_username)])

REVIEW_THRESHOLD = 0.6
ALLOWED_LEGEND_CODES = {
    "A", "AB", "AL", "CO", "DA", "HL", "ML", "NJ", "PA", "PH",
    "PL", "R", "RL", "SL", "SP", "T", "TO", "UL", "WD", "WE", "WI",
}
ALLOWED_NUMBERS = [str(n) for n in range(0, 25)]
ALLOWED_VALUES = ALLOWED_NUMBERS + sorted(ALLOWED_LEGEND_CODES)


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings)


@router.post("", response_model=ProcessResponse)
async def process_timesheet(
    payload: ProcessRequest,
    settings: Settings = Depends(get_settings),
    storage: StorageService = Depends(get_storage_service),
) -> ProcessResponse:
    try:
        excel_path = storage.get_upload_path(payload.excel_file_id, ".xlsx")
        pdf_path = storage.get_upload_path(payload.pdf_file_id, ".pdf")
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    pdf_service = PDFService()
    matching_service = MatchingService()
    ocr_engine = get_ocr_engine(settings)

    try:
        pdf_rows = pdf_service.extract_employee_rows(pdf_path)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Failed to read employee rows from the PDF: {exc}"
        ) from exc

    iqama_index = matching_service.build_iqama_index(
        excel_path=excel_path,
        sheet_name=payload.sheet_name,
        iqama_column=payload.mapping.iqama_column,
        data_start_row=payload.mapping.data_start_row,
    )

    duplicate_counts = matching_service.find_duplicate_pdf_iqamas(
        [row.iqama_or_passport for row in pdf_rows]
    )

    mapped_dates = {dc.iso_date for dc in payload.mapping.day_columns}

    results: list[EmployeeProcessResult] = []
    unmatched: list[UnmatchedEntry] = []
    seen_duplicate_names: dict[str, list[str]] = {}

    # PERFORMANCE FIX: open the PDF once for the whole request.
    fitz_doc = pdf_service.open_document(pdf_path)
    try:
        for row in pdf_rows:
            normalized_iqama = normalize_id(row.iqama_or_passport)
            excel_row = iqama_index.get(normalized_iqama)
            matched = excel_row is not None

            if not matched:
                unmatched.append(
                    UnmatchedEntry(
                        iqama_or_passport=row.iqama_or_passport,
                        employee_name=row.employee_name,
                        reason="No matching IQAMA found in master Excel",
                    )
                )

            if normalized_iqama in duplicate_counts:
                seen_duplicate_names.setdefault(normalized_iqama, [])
                if row.employee_name:
                    seen_duplicate_names[normalized_iqama].append(row.employee_name)

            day_cell_results: list[DayCellResult] = []
            for iso_date in sorted(mapped_dates):
                pdf_cell = row.day_cells.get(iso_date)
                if pdf_cell is None:
                    continue

                if pdf_cell.text_layer_value and pdf_cell.text_layer_value.strip().upper() in ALLOWED_VALUES:
                    value = pdf_cell.text_layer_value.strip().upper()
                    day_cell_results.append(
                        DayCellResult(
                            iso_date=iso_date,
                            value=value,
                            confidence=0.99,
                            source="text_layer",
                            needs_review=False,
                            is_legend_code=value in ALLOWED_LEGEND_CODES,
                        )
                    )
                    continue

                try:
                    image_bytes = pdf_service.crop_cell_image_from_doc(
                        fitz_doc, pdf_cell.page_number, pdf_cell.bbox
                    )
                    ocr_result = ocr_engine.read_cell(image_bytes, ALLOWED_VALUES)
                except Exception:
                    ocr_result = None

                if ocr_result is None:
                    day_cell_results.append(
                        DayCellResult(
                            iso_date=iso_date, value="?", confidence=0.0,
                            source="ocr", needs_review=True, is_legend_code=False,
                        )
                    )
                else:
                    day_cell_results.append(
                        DayCellResult(
                            iso_date=iso_date,
                            value=ocr_result.raw_value,
                            confidence=ocr_result.confidence,
                            source="ocr",
                            needs_review=ocr_result.confidence < REVIEW_THRESHOLD,
                            is_legend_code=ocr_result.is_legend_code,
                        )
                    )

            results.append(
                EmployeeProcessResult(
                    sr_no=row.sr_no,
                    iqama_or_passport=row.iqama_or_passport,
                    employee_name=row.employee_name,
                    designation=row.designation,
                    matched=matched,
                    excel_row=excel_row,
                    day_cells=day_cell_results,
                )
            )
    finally:
        fitz_doc.close()

    duplicates = [
        DuplicateEntry(
            iqama_or_passport=iqama,
            occurrences=count,
            employee_names=seen_duplicate_names.get(iqama, []),
        )
        for iqama, count in duplicate_counts.items()
    ]

    session_service = SessionService(storage)
    session_id = session_service.create(
        excel_file_id=payload.excel_file_id,
        sheet_name=payload.sheet_name,
        pdf_file_id=payload.pdf_file_id,
        mapping=payload.mapping.model_dump(),
        results=[r.model_dump() for r in results],
    )

    return ProcessResponse(
        session_id=session_id,
        results=results,
        unmatched=unmatched,
        duplicates=duplicates,
    )