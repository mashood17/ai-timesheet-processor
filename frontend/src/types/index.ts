// Mirrors the backend Pydantic models 1:1 so the frontend never guesses shapes.

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface ExcelUploadResponse {
  file_id: string;
  sheet_names: string[];
}

export interface PdfUploadResponse {
  file_id: string;
  page_count: number;
}

export interface DayColumnMapping {
  iso_date: string;
  excel_column: string;
}

export interface MappingDetectResponse {
  header_row: number;
  data_start_row: number;
  iqama_column: string | null;
  iqama_column_confidence: number;
  day_columns: DayColumnMapping[];
  day_columns_confidence: number;
  unmatched_pdf_dates: string[];
  alignment_method: "calendar" | "positional";
  calendar_match_count: number;
  positional_match_count: number;
  warnings: string[];
}

export interface MappingInput {
  header_row: number;
  data_start_row: number;
  iqama_column: string;
  day_columns: DayColumnMapping[];
}

export interface DayCellResult {
  iso_date: string;
  value: string;
  confidence: number;
  source: "text_layer" | "ocr";
  needs_review: boolean;
  is_legend_code: boolean;
}

export interface EmployeeProcessResult {
  sr_no: string | null;
  iqama_or_passport: string | null;
  employee_name: string | null;
  designation: string | null;
  matched: boolean;
  excel_row: number | null;
  day_cells: DayCellResult[];
}

export interface UnmatchedEntry {
  iqama_or_passport: string | null;
  employee_name: string | null;
  reason: string;
  possible_match: string | null;
}

export interface DuplicateEntry {
  iqama_or_passport: string;
  occurrences: number;
  employee_names: string[];
}

export interface ProcessResponse {
  session_id: string;
  results: EmployeeProcessResult[];
  unmatched: UnmatchedEntry[];
  duplicates: DuplicateEntry[];
}

export interface CorrectedCell {
  iqama_or_passport: string;
  iso_date: string;
  corrected_value: string;
}

export interface ConfirmResponse {
  processed: boolean;
  matched_count: number;
  unmatched_count: number;
  manually_corrected_count: number;
}