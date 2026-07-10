from pydantic import BaseModel

from app.models.mapping_models import DayColumnMapping


class MappingInput(BaseModel):
    """The user-confirmed mapping from Section 4's confirmation step."""
    header_row: int
    data_start_row: int
    iqama_column: str
    day_columns: list[DayColumnMapping]


class ProcessRequest(BaseModel):
    excel_file_id: str
    sheet_name: str
    pdf_file_id: str
    mapping: MappingInput


class DayCellResult(BaseModel):
    iso_date: str
    value: str                 # a number 0-24 as string, a legend code, or "?" if unresolved
    confidence: float
    source: str                 # "text_layer" | "ocr"
    needs_review: bool
    is_legend_code: bool


class EmployeeProcessResult(BaseModel):
    sr_no: str | None
    iqama_or_passport: str | None
    employee_name: str | None
    designation: str | None
    matched: bool
    excel_row: int | None       # row number in the master workbook, if matched
    day_cells: list[DayCellResult]


class UnmatchedEntry(BaseModel):
    iqama_or_passport: str | None
    employee_name: str | None
    reason: str                 # e.g. "No matching IQAMA found in master Excel"


class DuplicateEntry(BaseModel):
    iqama_or_passport: str
    occurrences: int
    employee_names: list[str]


class ProcessResponse(BaseModel):
    session_id: str
    results: list[EmployeeProcessResult]
    unmatched: list[UnmatchedEntry]
    duplicates: list[DuplicateEntry]


class CorrectedCell(BaseModel):
    iqama_or_passport: str
    iso_date: str
    corrected_value: str


class ConfirmRequest(BaseModel):
    session_id: str
    corrected_results: list[CorrectedCell]


class ConfirmResponse(BaseModel):
    processed: bool
    matched_count: int
    unmatched_count: int
    manually_corrected_count: int