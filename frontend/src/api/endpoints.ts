import { request, requestBlob, setToken } from "@/api/client";
import type {
  ConfirmResponse,
  CorrectedCell,
  ExcelUploadResponse,
  LoginResponse,
  MappingDetectResponse,
  MappingInput,
  PdfUploadResponse,
  ProcessResponse,
} from "@/types";

export async function login(username: string, password: string): Promise<void> {
  const result = await request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(result.access_token);
}

export async function uploadExcel(file: File): Promise<ExcelUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<ExcelUploadResponse>("/api/upload/excel", {
    method: "POST",
    body: formData,
  });
}

export async function uploadPdf(file: File): Promise<PdfUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<PdfUploadResponse>("/api/upload/pdf", {
    method: "POST",
    body: formData,
  });
}

export async function detectMapping(
  excelFileId: string,
  sheetName: string,
  pdfFileId: string
): Promise<MappingDetectResponse> {
  return request<MappingDetectResponse>("/api/mapping/detect", {
    method: "POST",
    body: JSON.stringify({
      excel_file_id: excelFileId,
      sheet_name: sheetName,
      pdf_file_id: pdfFileId,
    }),
  });
}

export async function processTimesheet(
  excelFileId: string,
  sheetName: string,
  pdfFileId: string,
  mapping: MappingInput
): Promise<ProcessResponse> {
  return request<ProcessResponse>("/api/process", {
    method: "POST",
    body: JSON.stringify({
      excel_file_id: excelFileId,
      sheet_name: sheetName,
      pdf_file_id: pdfFileId,
      mapping,
    }),
  });
}

export async function confirmAndGenerate(
  sessionId: string,
  correctedResults: CorrectedCell[]
): Promise<ConfirmResponse> {
  return request<ConfirmResponse>("/api/confirm", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      corrected_results: correctedResults,
    }),
  });
}

export async function downloadExcel(sessionId: string): Promise<Blob> {
  return requestBlob(`/api/download/excel/${sessionId}`);
}

export async function downloadReport(sessionId: string): Promise<Blob> {
  return requestBlob(`/api/download/report/${sessionId}`);
}

export async function acceptPossibleMatches(
  sessionId: string,
  matches: { unmatched_iqama_or_passport: string; accepted_iqama: string }[]
): Promise<{
  results: EmployeeProcessResult[];
  unmatched: UnmatchedEntry[];
  duplicates: DuplicateEntry[];
  accepted_count: number;
}> {
  return request("/api/process/accept-matches", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, matches }),
  });
}