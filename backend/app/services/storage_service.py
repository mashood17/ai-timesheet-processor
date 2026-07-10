"""
Handles all temp-file persistence for uploaded Excel/PDF files and
in-progress processing sessions (Section 9: server-side temp storage,
not publicly exposed, cleaned up after the session completes).

No database — files live on disk under STORAGE_DIR, keyed by a UUID.
Layout:
    storage/
      uploads/{file_id}/original.xlsx
      uploads/{file_id}/original.pdf
      sessions/{session_id}/session.json
      sessions/{session_id}/processed.xlsx
      sessions/{session_id}/report.xlsx
"""
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import Settings


class StorageService:
    def __init__(self, settings: Settings):
        self.base_dir = Path(settings.storage_dir)
        self.uploads_dir = self.base_dir / "uploads"
        self.sessions_dir = self.base_dir / "sessions"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.session_ttl_seconds = settings.session_ttl_minutes * 60

    # ---------- Uploaded files ----------

    def save_upload(self, file_bytes: bytes, extension: str) -> str:
        """Saves an uploaded file under a new file_id, returns that file_id."""
        file_id = str(uuid.uuid4())
        file_dir = self.uploads_dir / file_id
        file_dir.mkdir(parents=True, exist_ok=True)
        target = file_dir / f"original{extension}"
        target.write_bytes(file_bytes)
        return file_id

    def get_upload_path(self, file_id: str, extension: str) -> Path:
        path = self.uploads_dir / file_id / f"original{extension}"
        if not path.exists():
            raise FileNotFoundError(f"Uploaded file '{file_id}' not found or expired.")
        return path

    # ---------- Processing sessions ----------

    def create_session(self, data: dict[str, Any]) -> str:
        session_id = str(uuid.uuid4())
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        self._write_session_data(session_id, data)
        return session_id

    def get_session_data(self, session_id: str) -> dict[str, Any]:
        path = self.sessions_dir / session_id / "session.json"
        if not path.exists():
            raise FileNotFoundError(f"Session '{session_id}' not found or expired.")
        return json.loads(path.read_text(encoding="utf-8"))

    def update_session_data(self, session_id: str, data: dict[str, Any]) -> None:
        self._write_session_data(session_id, data)

    def session_file_path(self, session_id: str, filename: str) -> Path:
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / filename

    def _write_session_data(self, session_id: str, data: dict[str, Any]) -> None:
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "session.json").write_text(
            json.dumps(data, default=str, indent=2), encoding="utf-8"
        )

    # ---------- Cleanup ----------

    def cleanup_expired(self) -> None:
        """
        Deletes uploads/sessions older than SESSION_TTL_MINUTES. Call this on
        startup and optionally on a background schedule — there's no DB
        tracking expiry, so we rely on filesystem mtime.
        """
        now = time.time()
        for root in (self.uploads_dir, self.sessions_dir):
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                if now - child.stat().st_mtime > self.session_ttl_seconds:
                    shutil.rmtree(child, ignore_errors=True)

    def delete_upload(self, file_id: str) -> None:
        shutil.rmtree(self.uploads_dir / file_id, ignore_errors=True)

    def delete_session(self, session_id: str) -> None:
        shutil.rmtree(self.sessions_dir / session_id, ignore_errors=True)