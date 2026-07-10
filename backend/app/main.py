"""
FastAPI application entrypoint. Wires up CORS, routers, and startup/shutdown.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import get_settings
from app.routes.confirm_routes import router as confirm_router
from app.routes.download_routes import router as download_router
from app.routes.mapping_routes import router as mapping_router
from app.routes.process_routes import router as process_router
from app.routes.upload_routes import router as upload_router
from app.services.storage_service import StorageService
from app.utils.logging_config import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title="AI Timesheet Processor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(mapping_router)
app.include_router(process_router)
app.include_router(confirm_router)
app.include_router(download_router)


@app.on_event("startup")
def on_startup() -> None:
    StorageService(settings).cleanup_expired()


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)