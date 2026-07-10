"""
Wraps StorageService with the specific JSON shape used for a processing
session: the full per-employee OCR results, the confirmed mapping, and file
references needed later by /api/confirm and /api/download/*.

Kept as its own service (rather than inlining JSON shape knowledge into the
routes) so the shape only has to change in one place.
"""
from typing import Any

from app.services.storage_service import StorageService


class SessionService:
    def __init__(self, storage: StorageService):
        self.storage = storage

    def create(
        self,
        excel_file_id: str,
        sheet_name: str,
        pdf_file_id: str,
        mapping: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> str:
        session_data = {
            "excel_file_id": excel_file_id,
            "sheet_name": sheet_name,
            "pdf_file_id": pdf_file_id,
            "mapping": mapping,
            "results": results,
            "confirmed": False,
        }
        return self.storage.create_session(session_data)

    def get(self, session_id: str) -> dict[str, Any]:
        return self.storage.get_session_data(session_id)

    def mark_confirmed(self, session_id: str, corrected_results: list[dict[str, Any]]) -> dict[str, Any]:
        data = self.storage.get_session_data(session_id)
        data["confirmed"] = True
        data["corrected_results"] = corrected_results
        self.storage.update_session_data(session_id, data)
        return data