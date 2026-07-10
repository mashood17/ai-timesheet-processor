"""
Section 7: POST /api/confirm — Section 5 step 14-16.
This is the ONLY place in the whole system that actually writes to an
Excel file. Everything before this point is read-only analysis.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_username
from app.config import Settings, get_settings
from app.models.process_models import (
    ConfirmRequest,
    ConfirmResponse,
    DuplicateEntry,
    EmployeeProcessResult,
    UnmatchedEntry,
)
from app.services.excel_writer_service import ExcelWriterService
from app.services.matching_service import MatchingService, normalize_id
from app.services.report_service import ReportService
from app.services.session_service import SessionService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/confirm", tags=["confirm"], dependencies=[Depends(get_current_username)])


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings)


@router.post("", response_model=ConfirmResponse)
async def confirm_and_generate(
    payload: ConfirmRequest,
    storage: StorageService = Depends(get_storage_service),
) -> ConfirmResponse:
    session_service = SessionService(storage)

    try:
        session_data = session_service.get(payload.session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        excel_path = storage.get_upload_path(session_data["excel_file_id"], ".xlsx")
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    results = [EmployeeProcessResult(**r) for r in session_data["results"]]
    mapping = session_data["mapping"]
    day_columns = {dc["iso_date"]: dc["excel_column"] for dc in mapping["day_columns"]}

    # Recompute unmatched/duplicates for the report, consistent with /api/process.
    unmatched = [
        UnmatchedEntry(
            iqama_or_passport=r.iqama_or_passport,
            employee_name=r.employee_name,
            reason="No matching IQAMA found in master Excel",
        )
        for r in results
        if not r.matched
    ]
    duplicate_counts = MatchingService().find_duplicate_pdf_iqamas(
        [r.iqama_or_passport for r in results]
    )
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

    processed_path = storage.session_file_path(payload.session_id, "processed.xlsx")
    report_path = storage.session_file_path(payload.session_id, "report.xlsx")

    try:
        write_summary = ExcelWriterService().write_confirmed_hours(
            source_excel_path=excel_path,
            sheet_name=session_data["sheet_name"],
            output_path=processed_path,
            results=results,
            corrections=payload.corrected_results,
            day_columns=day_columns,
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to write the processed Excel: {exc}"
        ) from exc

    ReportService().generate_report(
        output_path=report_path,
        unmatched=unmatched,
        duplicates=duplicates,
        corrections=payload.corrected_results,
        results=results,
    )

    session_service.mark_confirmed(
        payload.session_id, [c.model_dump() for c in payload.corrected_results]
    )

    # Section 9: uploaded files must be cleaned up once the session completes.
    # The processed Excel + report already live independently under this
    # session's own storage folder, so the original uploads are no longer
    # needed and are removed now rather than waiting for the TTL sweep.
    storage.delete_upload(session_data["excel_file_id"])
    storage.delete_upload(session_data["pdf_file_id"])

    return ConfirmResponse(
        processed=True,
        matched_count=write_summary["matched_written"],
        unmatched_count=len(unmatched),
        manually_corrected_count=write_summary["manually_corrected"],
    )