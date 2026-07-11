"""
Section 7: POST /api/process — the core pipeline (Section 5, steps 7-12).

UPDATE: dispatches between the ruled-table extraction (pdf_service.py) and
the scanned page-per-employee extraction (pdf_page_template_service.py)
based on PDFService.detect_format(). The page-per-employee template
performs OCR inline during extraction (PDFCell.precomputed_ocr), so the
cell-processing loop below checks for that first before falling back to
the ruled-table's text-layer-then-crop-and-OCR path.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.vision_extraction_service import VisionExtractionService
from app.auth.dependencies import get_current_username
from app.config import Settings, get_settings
from app.models.process_models import AcceptMatchRequest, AcceptMatchResponse
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
from app.services.pdf_page_template_service import PageTemplatePDFService
from app.services.pdf_service import PDFService
from app.services.session_service import SessionService
from app.services.storage_service import StorageService
from app.models.process_models import AcceptMatchesRequest, AcceptMatchesResponse, MatchAcceptance
from app.services.extraction_validation_service import flag_suspicious_patterns

router = APIRouter(prefix="/api/process", tags=["process"], dependencies=[Depends(get_current_username)])

REVIEW_THRESHOLD = 0.6
ALLOWED_LEGEND_CODES = {
    "A", "AB", "AL", "CO", "DA", "HL", "ML", "NJ", "PA", "PH",
    "PL", "R", "RL", "SL", "SP", "T", "TO", "UL", "WD", "WE", "WI",
    # Sinopec-format legend (Note 3 on that template): distinct codes from
    # the SAC-factory legend above. Both sets are accepted so either PDF
    # format can be processed without reconfiguring anything.
    "S", "P", "V", "J", "M", "B", "C",
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

    pdf_format = pdf_service.detect_format(pdf_path)

    vision_service = VisionExtractionService(settings) if settings.vision_api_key else None

    try:
        if pdf_format == "scanned_page_per_employee":
            pdf_rows, extraction_failures = PageTemplatePDFService().extract_employee_rows(
                pdf_path, ocr_engine, ALLOWED_VALUES, vision_service=vision_service
            )
        else:
            pdf_rows = pdf_service.extract_employee_rows(pdf_path)
            extraction_failures = []
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

    fitz_doc = None
    if pdf_format != "scanned_page_per_employee":
        fitz_doc = pdf_service.open_document(pdf_path)

    try:
        for row in pdf_rows:
            normalized_iqama = normalize_id(row.iqama_or_passport)
            excel_row = iqama_index.get(normalized_iqama)
            matched = excel_row is not None

            if not matched:
                reason = (
                    "IQAMA number could not be read with sufficient confidence from the PDF"
                    if not row.iqama_or_passport
                    else "No matching IQAMA found in master Excel"
                )
                possible_match = None
                if row.iqama_or_passport:
                    possible_match = matching_service.find_possible_match(
                    normalized_iqama, iqama_index
                )
                unmatched.append(
                    UnmatchedEntry(
                        iqama_or_passport=row.iqama_or_passport,
                        employee_name=row.employee_name,
                        reason=reason,
                        possible_match=possible_match,
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

                # Page-per-employee template already ran OCR during extraction.
                if pdf_cell.precomputed_ocr is not None:
                    ocr_result = pdf_cell.precomputed_ocr
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
        if fitz_doc is not None:
            fitz_doc.close()

    for failure in extraction_failures:
        unmatched.append(
            UnmatchedEntry(
                iqama_or_passport=None,
                employee_name=None,
                reason=f"Page {failure['page_number']} could not be processed: {failure['reason']}",
                possible_match=None,
            )
        )

    duplicates = [
        DuplicateEntry(
            iqama_or_passport=iqama,
            occurrences=count,
            employee_names=seen_duplicate_names.get(iqama, []),
        )
        for iqama, count in duplicate_counts.items()
    ]

    quality_warnings = flag_suspicious_patterns(results)
    
    
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
        quality_warnings=quality_warnings,
    )
    
@router.post("/accept-matches", response_model=AcceptMatchesResponse)
async def accept_possible_matches(
    payload: AcceptMatchesRequest,
    storage: StorageService = Depends(get_storage_service),
) -> AcceptMatchesResponse:
    """
    Applies one or more user-confirmed near-miss match corrections in a
    single atomic pass. Handles any number of selections at once — this
    is the sole accept endpoint; a single acceptance is just a one-item
    batch, so there's one code path to reason about instead of two.

    Per Section requirements: this NEVER matches anything on its own —
    every correction here is a match the user explicitly reviewed and
    selected in the UI beforehand.
    """
    session_service = SessionService(storage)
    try:
        session_data = session_service.get(payload.session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        excel_path = storage.get_upload_path(session_data["excel_file_id"], ".xlsx")
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    mapping = session_data["mapping"]
    matching_service = MatchingService()
    iqama_index = matching_service.build_iqama_index(
        excel_path=excel_path,
        sheet_name=session_data["sheet_name"],
        iqama_column=mapping["iqama_column"],
        data_start_row=mapping["data_start_row"],
    )

    results = [EmployeeProcessResult(**r) for r in session_data["results"]]
    accepted_count = 0

    for acceptance in payload.matches:
        normalized_accepted = normalize_id(acceptance.accepted_iqama)
        excel_row = iqama_index.get(normalized_accepted)
        if excel_row is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Accepted IQAMA '{acceptance.accepted_iqama}' was not found in the "
                "master Excel — it may have changed since this session started.",
            )

        target = next(
            (r for r in results
             if r.iqama_or_passport == acceptance.unmatched_iqama_or_passport and not r.matched),
            None,
        )
        if target is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Could not find unmatched entry '{acceptance.unmatched_iqama_or_passport}' — "
                "it may have already been resolved.",
            )

        target.iqama_or_passport = acceptance.accepted_iqama
        target.matched = True
        target.excel_row = excel_row
        accepted_count += 1

    storage.update_session_data(
        payload.session_id,
        {**session_data, "results": [r.model_dump() for r in results]},
    )

    duplicate_counts = matching_service.find_duplicate_pdf_iqamas(
        [r.iqama_or_passport for r in results]
    )
    unmatched = [
        UnmatchedEntry(
            iqama_or_passport=r.iqama_or_passport,
            employee_name=r.employee_name,
            reason=(
                "IQAMA number could not be read with sufficient confidence from the PDF"
                if not r.iqama_or_passport
                else "No matching IQAMA found in master Excel"
            ),
            possible_match=matching_service.find_possible_match(
                normalize_id(r.iqama_or_passport), iqama_index
            ) if r.iqama_or_passport else None,
        )
        for r in results
        if not r.matched
    ]
    duplicates = [
        DuplicateEntry(
            iqama_or_passport=iqama,
            occurrences=count,
            employee_names=[
                r.employee_name for r in results
                if normalize_id(r.iqama_or_passport) == iqama and r.employee_name
            ],
        )
        for iqama, count in duplicate_counts.items()
    ]

    return AcceptMatchesResponse(
        results=results, unmatched=unmatched, duplicates=duplicates, accepted_count=accepted_count,
    )