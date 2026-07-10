from pydantic import BaseModel


class ExcelUploadResponse(BaseModel):
    file_id: str
    sheet_names: list[str]


class PdfUploadResponse(BaseModel):
    file_id: str
    page_count: int