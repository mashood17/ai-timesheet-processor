"""
Section 2: a single config value (OCR_ENGINE) selects the implementation.
This is the ONLY place that decides which concrete OCREngine gets used.
"""
from app.config import Settings
from app.services.ocr.base import OCREngine
from app.services.ocr.tesseract_engine import TesseractOCREngine


def get_ocr_engine(settings: Settings) -> OCREngine:
    if settings.ocr_engine == "tesseract":
        return TesseractOCREngine(settings)

    # Future: elif settings.ocr_engine == "vision_api": return VisionAPIOCREngine(settings)
    raise ValueError(f"Unknown OCR_ENGINE '{settings.ocr_engine}'")