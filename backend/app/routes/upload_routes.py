"""
Section 7: POST /api/upload/excel and POST /api/upload/pdf.
Both are behind auth (Section 6) via get_current_username.
"""
from pathlib import Path

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_username
from app.config import Settings, get_settings
from app.models.upload_models import ExcelUploadResponse, PdfUploadResponse
from app.services.pdf_service import PDFService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/upload", tags=["upload"], dependencies=[Depends(get_current_username)])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB — generous for a 900+ row PDF or large workbook


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings)


@router.post("/excel", response_model=ExcelUploadResponse)
async def upload_excel(
    file: UploadFile,
    storage: StorageService = Depends(get_storage_service),
) -> ExcelUploadResponse:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .xlsx/.xlsm files are accepted.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File exceeds the 50MB limit.")

    file_id = storage.save_upload(contents, extension=".xlsx")

    try:
        path = storage.get_upload_path(file_id, ".xlsx")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
        sheet_names = workbook.sheetnames
        workbook.close()
    except Exception as exc:
        storage.delete_upload(file_id)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Could not read the Excel file: {exc}"
        ) from exc

    return ExcelUploadResponse(file_id=file_id, sheet_names=sheet_names)


@router.post("/pdf", response_model=PdfUploadResponse)
async def upload_pdf(
    file: UploadFile,
    storage: StorageService = Depends(get_storage_service),
) -> PdfUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .pdf files are accepted.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File exceeds the 50MB limit.")

    file_id = storage.save_upload(contents, extension=".pdf")

    try:
        path = storage.get_upload_path(file_id, ".pdf")
        page_count = PDFService().get_page_count(path)
    except Exception as exc:
        storage.delete_upload(file_id)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Could not read the PDF file: {exc}"
        ) from exc

    return PdfUploadResponse(file_id=file_id, page_count=page_count)