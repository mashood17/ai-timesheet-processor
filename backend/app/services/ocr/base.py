"""
Section 2 — the OCR abstraction. Nothing outside this package should ever
import pytesseract directly. Routes, matching logic, and the review UI only
ever talk to OCREngine.

To add a Vision API engine later (Claude/GPT-4V/Gemini): implement this
interface in a new file (e.g. vision_api_engine.py), register it in factory.py,
and set OCR_ENGINE in .env. Zero other files change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRResult:
    raw_value: str          # best-guess value (a number 0-24 as string, or a legend code)
    confidence: float        # 0.0 - 1.0
    is_legend_code: bool     # True if raw_value matched a code like "SL", "WE", etc.


class OCREngine(ABC):
    """Abstract base for any handwriting/print recognition engine."""

    @abstractmethod
    def read_cell(self, image: bytes, allowed_values: list[str]) -> OCRResult:
        """
        Read a single day-cell image and return the best interpretation,
        constrained to `allowed_values` (numbers 0-24 as strings + legend codes,
        per Section 3). Implementations should never return a value outside
        this closed set — return the closest match with a low confidence
        instead of an arbitrary free-text guess.
        """
        raise NotImplementedError