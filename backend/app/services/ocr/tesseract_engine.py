"""
Default OCR implementation (Section 2/10). Free, self-hosted, no API key.

PERFORMANCE FIX: previously ran the digit-pass AND text-pass on every
single cell unconditionally (2 subprocess invocations per call). Now runs
the digit-pass first and only falls back to the text-pass if the digit
result is empty or invalid — cutting invocations roughly in half for the
common case (numeric hours), which are the majority of cells in a typical
timesheet.

Honest note for the README: Tesseract's accuracy on handwritten digits is
inconsistent — this is exactly why the manual review step (Section 5, step
12-13) exists and is mandatory. Confirmed against real customer data during
testing: don't expect high automatic accuracy on cursive pen handwriting;
budget real time for the review screen, or swap in a Vision API engine via
OCR_ENGINE for materially better results with zero other code changes.
"""
import re

import pytesseract
from PIL import Image

from app.config import Settings
from app.services.ocr.base import OCREngine, OCRResult

LEGEND_CODES = {
    "A", "AB", "AL", "CO", "DA", "HL", "ML", "NJ", "PA", "PH",
    "PL", "R", "RL", "SL", "SP", "T", "TO", "UL", "WD", "WE", "WI",
    "S", "P", "V", "J", "M", "B", "C",
}


class TesseractOCREngine(OCREngine):
    def __init__(self, settings: Settings):
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def read_cell(self, image: bytes, allowed_values: list[str]) -> OCRResult:
        import io
        img = Image.open(io.BytesIO(image)).convert("L")
        allowed_set = set(allowed_values)

        digit_config = "--psm 8 -c tessedit_char_whitelist=0123456789.,"
        digit_raw = pytesseract.image_to_string(img, config=digit_config).strip()
        cleaned_digit = re.sub(r"[^\d]", "", digit_raw)

        if cleaned_digit and cleaned_digit.isdigit() and 0 <= int(cleaned_digit) <= 24:
            if cleaned_digit in allowed_set:
                confidence = 0.9 if len(cleaned_digit) <= 2 else 0.5
                return OCRResult(raw_value=cleaned_digit, confidence=confidence, is_legend_code=False)

        # Digit pass didn't produce a valid result — try the text pass
        # (legend codes) as a second attempt, not unconditionally.
        text_config = "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        text_raw = pytesseract.image_to_string(img, config=text_config).strip().upper()

        if text_raw in LEGEND_CODES:
            return OCRResult(raw_value=text_raw, confidence=0.75, is_legend_code=True)

        fallback = cleaned_digit or text_raw or "?"
        return OCRResult(raw_value=fallback, confidence=0.2, is_legend_code=fallback in LEGEND_CODES)