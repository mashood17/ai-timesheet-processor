"""
Vision-language-model-based field extraction for the scanned/photographed,
one-employee-per-page timesheet format.

CRITICAL DESIGN CHANGE (from a real accuracy failure found via manual
verification): sending an entire ~30-day row in a single image + single
prompt allowed the model to "complete a plausible pattern" instead of
reading each day independently — confirmed by finding two different
employees' day-rows collapsed into an IDENTICAL clean step-function
pattern, silently discarding a genuine outlier (a lone "6" among "10"s/
"11"s) that IS actually written on the source page.

FIX: day values are now requested in small CHUNKS (a few days per call)
rather than the whole row at once. A smaller crop with fewer neighboring
cells visible gives the model far less context to "complete a pattern"
from — this structurally reduces (not just prompts against) the smoothing
failure mode. Each chunk call also requests a per-day self-reported
confidence, and the prompt explicitly and repeatedly instructs independent,
literal reading with no pattern-based inference.

This is intentionally slower and more expensive (more API calls) than a
single combined call — a deliberate accuracy-over-speed tradeoff for a
production system, per explicit requirement.
"""
import base64
import io
import json
import re
import time

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from PIL import Image

from app.config import Settings
from app.services.ocr.base import OCRResult

RETRYABLE_EXCEPTIONS = (RateLimitError, APIConnectionError, APITimeoutError)
MAX_RETRIES = 2

CONFIDENCE_MAP = {"high": 0.9, "medium": 0.6, "low": 0.3}

# Chunk size for day-row extraction: smaller = more independent reads,
# more API calls. This is a generic tuning constant, not tied to any
# specific document's day count.
DAY_CHUNK_SIZE = 5

MAX_IMAGE_DIMENSION = 1000

class VisionExtractionService:
    MAX_IMAGE_DIMENSION = 1000 
    def __init__(self, settings: Settings):
        base_url = "https://openrouter.ai/api/v1" if settings.vision_provider == "openrouter" else None
        self.client = OpenAI(api_key=settings.vision_api_key, base_url=base_url)
        self.model = settings.vision_model

    def extract_header_fields(self, image: Image.Image) -> dict:
        """
        Reads IQAMA/Passport number, employee name, and job title from a
        crop covering the header lines. Returns
        {"iqama": str, "employee_name": str, "job_title": str}.
        """
        prompt = (
            "This is a cropped region from a supplier timesheet form. It contains "
            "three handwritten fields, each following a printed label:\n"
            "1. 'Iqama/Passport' - a numeric ID (usually 7-10 digits)\n"
            "2. 'Employee Name' - a person's name\n"
            "3. 'Job Title' - a job title/position\n\n"
            "Read the HANDWRITTEN value for each field exactly as written (ignore "
            "the printed labels themselves). Respond with ONLY a JSON object in "
            "this exact shape, with no other text: "
            '{"iqama": "...", "employee_name": "...", "job_title": "..."}\n'
            "If any field is genuinely illegible or blank, use an empty string "
            "for that field rather than guessing."
        )
        raw = self._call_vision_with_retry(image, prompt)
        return self._parse_json_response(
            raw, default={"iqama": "", "employee_name": "", "job_title": ""}
        )

    def extract_day_chunk(
        self,
        image: Image.Image,
        day_start: int,
        day_end: int,
        allowed_values: list[str],
    ) -> dict[int, OCRResult]:
        """
        Reads a SMALL chunk of consecutive day-columns (day_start to
        day_end inclusive, 1-indexed) from a narrow crop. Returns
        {day_index_0based: OCRResult}.

        CRITICAL: the prompt explicitly forbids pattern-based inference —
        every day must be read as an independent, isolated observation.
        This is the primary defense against the smoothing failure mode;
        the small chunk size is the structural backup in case the prompt
        alone isn't sufficient.
        """
        num_in_chunk = day_end - day_start + 1
        allowed_str = ", ".join(sorted(set(allowed_values), key=lambda v: (len(v), v)))

        prompt = (
            f"This is a cropped section of a timesheet showing exactly "
            f"{num_in_chunk} handwritten daily values, for days {day_start} "
            f"through {day_end} of the month, left to right in that order.\n\n"
            f"Each value is either a number of hours worked (0-24) or a "
            f"leave/status code from this exact set: {allowed_str}.\n\n"
            "CRITICAL INSTRUCTIONS — read carefully:\n"
            "- Read EACH day's handwritten mark as a completely INDEPENDENT, "
            "isolated observation. Do not consider what value would be "
            "'expected' based on neighboring days.\n"
            "- NEVER infer, smooth, average, or 'complete a pattern' across "
            "days. If one day's value looks different from the days next to "
            "it, that is completely normal for a real timesheet — report "
            "EXACTLY what is written for that specific day, even if it "
            "breaks an otherwise consistent pattern.\n"
            "- Do not assume all days in this chunk have the same or similar "
            "values just because some do. Look at each cell's actual "
            "handwritten mark individually.\n"
            "- If a specific day's cell is genuinely blank (no handwriting at "
            "all), omit that day's key entirely rather than guessing a value.\n\n"
            "For each day, also self-report your confidence as exactly one of "
            '"high", "medium", or "low" based on how legible that SPECIFIC '
            "day's handwriting is — not based on whether it fits a pattern.\n\n"
            "Respond with ONLY a JSON object in this exact shape, with no other "
            "text:\n"
            '{"1": {"value": "10", "confidence": "high"}, '
            '"2": {"value": "6", "confidence": "medium"}, ...}\n'
            "(using the actual day numbers for this chunk as keys)"
        )
        raw = self._call_vision_with_retry(image, prompt)
        parsed = self._parse_json_response(raw, default={})

        results: dict[int, OCRResult] = {}
        allowed_set = set(allowed_values)
        for day_str, entry in parsed.items():
            try:
                day_idx = int(day_str) - 1
            except (ValueError, TypeError):
                continue
            if not isinstance(entry, dict):
                continue
            value = str(entry.get("value", "")).strip().upper()
            confidence_label = str(entry.get("confidence", "low")).strip().lower()
            confidence = CONFIDENCE_MAP.get(confidence_label, 0.3)

            if value in allowed_set:
                is_legend = not value.isdigit()
                results[day_idx] = OCRResult(raw_value=value, confidence=confidence, is_legend_code=is_legend)

        return results

    # ---------- internal ----------
    def _resize_for_api(self, image: Image.Image) -> Image.Image:
        """
        Downscales the image before sending, capping the longer side at
        MAX_IMAGE_DIMENSION. Vision APIs tokenize images based on pixel
        dimensions — a full-resolution 2500px-wide crop costs meaningfully
        more per call than a 1000px version, with no real accuracy loss for
        reading clear handwriting/print at this size.
        """
        width, height = image.size
        longest_side = max(width, height)
        if longest_side <= self.MAX_IMAGE_DIMENSION:
            return image
        scale = self.MAX_IMAGE_DIMENSION / longest_side
        new_size = (int(width * scale), int(height * scale))
        return image.resize(new_size, Image.LANCZOS)
    
    def _image_to_data_url(self, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    def _call_vision_with_retry(self, image: Image.Image, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self._call_vision(image, prompt)
            except RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
        raise last_error

    def _call_vision(self, image: Image.Image, prompt: str) -> str:
        resized = self._resize_for_api(image)
        data_url = self._image_to_data_url(resized)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0,
            max_tokens=150,
        )
        return response.choices[0].message.content or ""

    def _parse_json_response(self, raw: str, default: dict) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                return default
            return parsed
        except (json.JSONDecodeError, TypeError):
            return default