"""
Section 7: POST /api/mapping/detect.
This endpoint only *proposes* a mapping — Section 4 requires the user to
confirm (or manually correct) it in the UI before anything gets written.
No Excel writes happen here.

UPDATE: now dispatches between the ruled-table format (pdf_service.py) and
the scanned page-per-employee format (pdf_page_template_service.py) based
on PDFService.detect_format(), since header/period extraction differs
completely between the two.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_username
from app.config import Settings, get_settings
from app.models.mapping_models import MappingDetectRequest, MappingDetectResponse
from app.services.excel_mapping_service import ExcelMappingService
from app.services.pdf_page_template_service import PageTemplatePDFService
from app.services.pdf_service import PDFService
from app.services.storage_service import StorageService
from app.utils.date_utils import generate_sequential_dates

router = APIRouter(prefix="/api/mapping", tags=["mapping"], dependencies=[Depends(get_current_username)])


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings)


@router.post("/detect", response_model=MappingDetectResponse)
async def detect_mapping(
    payload: MappingDetectRequest,
    storage: StorageService = Depends(get_storage_service),
) -> MappingDetectResponse:
    try:
        excel_path = storage.get_upload_path(payload.excel_file_id, ".xlsx")
        pdf_path = storage.get_upload_path(payload.pdf_file_id, ".pdf")
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    pdf_service = PDFService()
    pdf_format = pdf_service.detect_format(pdf_path)
    extractor = PageTemplatePDFService() if pdf_format == "scanned_page_per_employee" else pdf_service

    try:
        header_info = extractor.extract_header_info(pdf_path)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Could not read the PDF header/period: {exc}"
        ) from exc

    if not header_info.period_start or not header_info.period_end:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Could not determine the timesheet period from the PDF. "
            "Check that the PDF contains a readable period or title line.",
        )

    pdf_dates = generate_sequential_dates(header_info.period_start, header_info.period_end)

    try:
        result = ExcelMappingService().detect_mapping(
            excel_path=excel_path,
            sheet_name=payload.sheet_name,
            pdf_dates=pdf_dates,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return MappingDetectResponse(**result)