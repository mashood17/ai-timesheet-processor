"""
Vision-language-model-based field extraction for the scanned/photographed,
one-employee-per-page timesheet format.

UPDATE: combined header-fields + day-row extraction into ONE API call per
page (previously two), cutting cost and latency roughly in half. Also adds
retry-with-backoff for transient API errors (rate limits, timeouts,
connection drops) — these are common with real-world API usage and were
previously unhandled, meaning a single transient hiccup on one page could
silently derail that page's entire result.
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


class VisionExtractionService:
    def __init__(self, settings: Settings):
        base_url = "https://openrouter.ai/api/v1" if settings.vision_provider == "openrouter" else None
        self.client = OpenAI(api_key=settings.vision_api_key, base_url=base_url)
        self.model = settings.vision_model

    def extract_employee_data(
        self, image: Image.Image, num_days: int, allowed_values: list[str]
    ) -> dict:
        """
        Single combined call: reads IQAMA/Passport number, employee name,
        job title, AND every day-column value in ONE request. Returns:
        {
          "iqama": str, "employee_name": str, "job_title": str,
          "days": {"1": "10", "2": "WE", ...}
        }
        Any field that's genuinely illegible comes back empty/omitted
        rather than guessed — the prompt explicitly instructs this.
        """
        allowed_str = ", ".join(sorted(set(allowed_values), key=lambda v: (len(v), v)))
        prompt = (
            "This is a cropped region from a supplier timesheet form, covering "
            "the employee's header fields and their full row of daily hours.\n\n"
            "It contains three handwritten header fields, each following a "
            "printed label:\n"
            "1. 'Iqama/Passport' - a numeric ID (usually 7-10 digits)\n"
            "2. 'Employee Name' - a person's name\n"
            "3. 'Job Title' - a job title/position\n\n"
            f"It also contains a row of {num_days} handwritten daily values, one "
            f"per day of the month, left to right, in order (day 1 through day "
            f"{num_days}). Each value is either a number of hours worked (0-24) "
            f"or a leave/status code from this exact set: {allowed_str}.\n\n"
            "Read the HANDWRITTEN value for each field (ignore the printed labels "
            "themselves). Respond with ONLY a JSON object in this exact shape, "
            "with no other text:\n"
            '{"iqama": "...", "employee_name": "...", "job_title": "...", '
            '"days": {"1": "10", "2": "WE", ...}}\n\n'
            "If a header field is genuinely illegible or blank, use an empty "
            "string for it. If a specific day's cell is genuinely blank (no "
            "handwriting at all), omit that day's key from the 'days' object "
            "entirely rather than guessing."
        )
        raw = self._call_vision_with_retry(image, prompt)
        return self._parse_json_response(
            raw, default={"iqama": "", "employee_name": "", "job_title": "", "days": {}}
        )

    def parse_day_results(
        self, days_dict: dict, num_days: int, allowed_values: list[str]
    ) -> dict[int, OCRResult]:
        """Converts the raw {"1": "10", ...} dict into {day_index: OCRResult}."""
        results: dict[int, OCRResult] = {}
        allowed_set = set(allowed_values)
        for day_str, value in days_dict.items():
            try:
                day_idx = int(day_str) - 1
            except (ValueError, TypeError):
                continue
            if day_idx < 0 or day_idx >= num_days:
                continue
            cleaned = str(value).strip().upper()
            if cleaned in allowed_set:
                is_legend = not cleaned.isdigit()
                results[day_idx] = OCRResult(raw_value=cleaned, confidence=0.9, is_legend_code=is_legend)
        return results

    # ---------- internal ----------

    def _image_to_data_url(self, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    def _call_vision_with_retry(self, image: Image.Image, prompt: str) -> str:
        """
        Retries transient API errors (rate limits, timeouts, connection
        drops) with exponential backoff. Genuinely malformed responses
        (bad JSON) are NOT retried here — those are handled downstream by
        _parse_json_response falling back to safe defaults, since retrying
        won't fix a model's response-formatting choice.
        """
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self._call_vision(image, prompt)
            except RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
        raise last_error  # re-raised only after exhausting retries

    def _call_vision(self, image: Image.Image, prompt: str) -> str:
        data_url = self._image_to_data_url(image)
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
            max_tokens=800,
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