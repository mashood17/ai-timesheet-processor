"""
Default OCR implementation (Section 2/10). Free, self-hosted, no API key.

Honest note for the README: Tesseract's accuracy on handwritten digits is
inconsistent — this is exactly why the manual review step (Section 5, step 12-13)
exists and is mandatory. Don't expect >70-80% clean auto-fill on messy handwriting;
budget real time for the review screen.
"""
import io
import re

import pytesseract
from PIL import Image

from app.config import Settings
from app.services.ocr.base import OCREngine, OCRResult

# Section 3 closed set: numbers 0-24 plus the legend codes.
LEGEND_CODES = {
    "A", "AB", "AL", "CO", "DA", "HL", "ML", "NJ", "PA", "PH",
    "PL", "R", "RL", "SL", "SP", "T", "TO", "UL", "WD", "WE", "WI",
}


class TesseractOCREngine(OCREngine):
    def __init__(self, settings: Settings):
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def read_cell(self, image: bytes, allowed_values: list[str]) -> OCRResult:
        img = Image.open(io.BytesIO(image)).convert("L")

        # Two passes: digits-only PSM, then a general single-word PSM for legend codes.
        digit_config = "--psm 8 -c tessedit_char_whitelist=0123456789.,"
        text_config = "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        digit_raw = pytesseract.image_to_string(img, config=digit_config).strip()
        text_raw = pytesseract.image_to_string(img, config=text_config).strip().upper()

        cleaned_digit = re.sub(r"[^\d]", "", digit_raw)
        allowed_set = set(allowed_values)

        # Prefer a numeric read if it falls in 0-24 and is in the allowed set.
        if cleaned_digit and cleaned_digit.isdigit() and 0 <= int(cleaned_digit) <= 24:
            if cleaned_digit in allowed_set:
                confidence = 0.9 if len(cleaned_digit) <= 2 else 0.5
                return OCRResult(raw_value=cleaned_digit, confidence=confidence, is_legend_code=False)

        # Otherwise try to match a legend code.
        if text_raw in LEGEND_CODES:
            return OCRResult(raw_value=text_raw, confidence=0.75, is_legend_code=True)

        # Nothing confidently matched the closed set — flag for manual review.
        fallback = cleaned_digit or text_raw or "?"
        return OCRResult(raw_value=fallback, confidence=0.2, is_legend_code=fallback in LEGEND_CODES)