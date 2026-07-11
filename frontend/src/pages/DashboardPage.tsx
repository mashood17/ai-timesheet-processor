import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { detectMapping, processTimesheet, uploadExcel, uploadPdf } from "@/api/endpoints";
import { useAuth } from "@/auth/AuthContext";
import { ElapsedProgress } from "@/components/ElapsedProgress";
import { MappingConfirmation } from "@/components/MappingConfirmation";
import { ProgressBar } from "@/components/ProgressBar";
import { SheetSelector } from "@/components/SheetSelector";
import { UploadZone } from "@/components/UploadZone";
import type { MappingDetectResponse, MappingInput } from "@/types";

const STEPS = ["Upload files", "Confirm mapping", "Review", "Results"];

export function DashboardPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelFileId, setExcelFileId] = useState<string | null>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>("");

  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfFileId, setPdfFileId] = useState<string | null>(null);

  const [mapping, setMapping] = useState<MappingDetectResponse | null>(null);
  const [iqamaColumn, setIqamaColumn] = useState<string>("");

  const [loadingStep, setLoadingStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentStepIndex = mapping ? 1 : 0;

  async function handleExcelSelected(file: File) {
    setError(null);
    setExcelFile(file);
    setLoadingStep("Uploading Excel…");
    try {
      const result = await uploadExcel(file);
      setExcelFileId(result.file_id);
      setSheetNames(result.sheet_names);
      setSelectedSheet(result.sheet_names[0] ?? "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload Excel file.");
      setExcelFile(null);
    } finally {
      setLoadingStep(null);
    }
  }

  async function handlePdfSelected(file: File) {
    setError(null);
    setPdfFile(file);
    setLoadingStep("Uploading PDF…");
    try {
      const result = await uploadPdf(file);
      setPdfFileId(result.file_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload PDF file.");
      setPdfFile(null);
    } finally {
      setLoadingStep(null);
    }
  }

  async function handleDetectMapping() {
    if (!excelFileId || !pdfFileId || !selectedSheet) return;
    setError(null);
    setLoadingStep("Analyzing files and detecting mapping…");
    try {
      const result = await detectMapping(excelFileId, selectedSheet, pdfFileId);
      setMapping(result);
      setIqamaColumn(result.iqama_column ?? "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to detect mapping.");
    } finally {
      setLoadingStep(null);
    }
  }

  async function handleConfirmMapping() {
    if (!excelFileId || !pdfFileId || !selectedSheet || !mapping) return;
    setError(null);
    setLoadingStep("Reading PDF and running OCR — expect roughly 30–60s per 50 employees");
    try {
      const mappingInput: MappingInput = {
        header_row: mapping.header_row,
        data_start_row: mapping.data_start_row,
        iqama_column: iqamaColumn,
        day_columns: mapping.day_columns,
      };
      const result = await processTimesheet(excelFileId, selectedSheet, pdfFileId, mappingInput);
      navigate("/review", {
        state: {
          sessionId: result.session_id,
          results: result.results,
          unmatched: result.unmatched,
          duplicates: result.duplicates,
        },
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to process the timesheet.");
    } finally {
      setLoadingStep(null);
    }
  }

  const canDetectMapping = excelFileId && pdfFileId && selectedSheet && !mapping;

  return (
    <div className="min-h-screen bg-ink-50">
      <header className="border-b border-ink-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-ink-900 flex items-center justify-center">
              <span className="text-white text-[10px] font-semibold">TP</span>
            </div>
            <h1 className="text-sm font-semibold text-ink-900 tracking-tight">Timesheet Processor</h1>
          </div>
          <button
            onClick={logout}
            className="text-xs text-ink-400 hover:text-ink-900 font-medium transition-colors duration-150"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <ProgressBar steps={STEPS} currentStepIndex={currentStepIndex} />

        <div className="bg-white rounded-2xl shadow-card border border-ink-100 p-7">
          <h2 className="text-sm font-semibold text-ink-900 tracking-tight mb-5">
            1. Upload files
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <UploadZone
              label="Master Excel workbook"
              accept=".xlsx,.xlsm"
              onFileSelected={handleExcelSelected}
              uploadedFileName={excelFile?.name ?? null}
              disabled={!!mapping}
            />
            <UploadZone
              label="Monthly timesheet PDF"
              accept=".pdf"
              onFileSelected={handlePdfSelected}
              uploadedFileName={pdfFile?.name ?? null}
              disabled={!!mapping}
            />
          </div>

          {sheetNames.length > 1 && !mapping && (
            <SheetSelector
              sheetNames={sheetNames}
              selectedSheet={selectedSheet}
              onSelect={setSelectedSheet}
            />
          )}

          {error && (
            <div className="bg-red-50 border border-red-100 rounded-lg px-3.5 py-2.5 mt-5">
              <p className="text-sm text-red-600 font-medium">{error}</p>
            </div>
          )}

          {loadingStep && <ElapsedProgress label={loadingStep} />}

          {canDetectMapping && !loadingStep && (
            <button
              onClick={handleDetectMapping}
              className="w-full mt-5 rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 transition-all duration-150 hover:bg-accent-600 active:scale-[0.99] shadow-sm"
            >
              Detect mapping
            </button>
          )}

          {mapping && (
            <MappingConfirmation
              mapping={mapping}
              iqamaColumn={iqamaColumn}
              onIqamaColumnChange={setIqamaColumn}
              onConfirm={handleConfirmMapping}
              loading={loadingStep !== null}
            />
          )}
        </div>
      </main>
    </div>
  );
}