"""
Date helpers shared by pdf_service (reading the PDF's timesheet period +
day columns) and excel_mapping_service (aligning PDF day-columns to Excel
day-columns by actual calendar date, per Section 4 — never by position).
"""
import re
from datetime import date, datetime, timedelta

# Matches things like "26-05-2026 to 25-06-2026" or "26/05/2026 - 25/06/2026"
PERIOD_PATTERN = re.compile(
    r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s*(?:to|-|–)\s*(\d{1,2})[-/](\d{1,2})[-/](\d{4})",
    re.IGNORECASE,
)


def parse_timesheet_period(header_text: str) -> tuple[date, date] | None:
    """
    Extracts (period_start, period_end) from raw header text such as:
    'Timesheet Period: 26-05-2026 to 25-06-2026'
    Returns None if no recognizable range is found — caller must handle
    this as an ambiguous case requiring user input, not silently guess.
    """
    match = PERIOD_PATTERN.search(header_text)
    if not match:
        return None

    d1, m1, y1, d2, m2, y2 = match.groups()
    start = date(int(y1), int(m1), int(d1))
    end = date(int(y2), int(m2), int(d2))
    return start, end


def generate_sequential_dates(start: date, end: date) -> list[date]:
    """
    Section 3: the PDF has one column per calendar day of the period.
    Assumption (stated per Section 13): day columns run left-to-right in
    strict chronological order with no gaps, matching the period range.
    If a PDF ever violates this, mapping/detect should surface a mismatch
    rather than mis-align silently.
    """
    days = (end - start).days
    if days < 0:
        return []
    return [start + timedelta(days=i) for i in range(days + 1)]


def excel_serial_to_date(serial_value) -> date | None:
    """
    Excel sometimes stores day-column headers as real datetime objects
    (openpyxl already converts these for us), but occasionally as raw
    serial numbers when a cell is oddly formatted. Handle both.
    """
    if isinstance(serial_value, datetime):
        return serial_value.date()
    if isinstance(serial_value, date):
        return serial_value
    if isinstance(serial_value, (int, float)):
        # Excel's epoch: day 1 = 1899-12-31, with the well-known 1900 leap-year bug.
        try:
            base = date(1899, 12, 30)
            return base + timedelta(days=int(serial_value))
        except (OverflowError, ValueError):
            return None
    return None