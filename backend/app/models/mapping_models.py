from pydantic import BaseModel


class DayColumnMapping(BaseModel):
    iso_date: str
    excel_column: str


class MappingDetectRequest(BaseModel):
    excel_file_id: str
    sheet_name: str
    pdf_file_id: str


class MappingDetectResponse(BaseModel):
    header_row: int
    data_start_row: int
    iqama_column: str | None
    iqama_column_confidence: float
    day_columns: list[DayColumnMapping]
    day_columns_confidence: float
    unmatched_pdf_dates: list[str]
    alignment_method: str          # "calendar" | "positional"
    calendar_match_count: int
    positional_match_count: int
    warnings: list[str]


class MappingConfirmRequest(BaseModel):
    header_row: int
    data_start_row: int
    iqama_column: str
    day_columns: list[DayColumnMapping]