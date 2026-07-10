"""
Section 7: GET /api/download/excel/{session_id} and GET /api/download/report/{session_id}.
Both stream files that only exist after /api/confirm has run.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.auth.dependencies import get_current_username
from app.config import Settings, get_settings
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/download", tags=["download"], dependencies=[Depends(get_current_username)])


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings)


@router.get("/excel/{session_id}")
async def download_excel(
    session_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> FileResponse:
    path = storage.session_file_path(session_id, "processed.xlsx")
    if not path.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Processed file not found. Make sure you've called /api/confirm first.",
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="processed_timesheet.xlsx",
    )


@router.get("/report/{session_id}")
async def download_report(
    session_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> FileResponse:
    path = storage.session_file_path(session_id, "report.xlsx")
    if not path.exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Validation report not found. Make sure you've called /api/confirm first.",
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="validation_report.xlsx",
    )