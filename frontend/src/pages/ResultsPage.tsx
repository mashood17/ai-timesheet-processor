import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { downloadExcel, downloadReport } from "@/api/endpoints";
import type { ConfirmResponse } from "@/types";

interface LocationState {
  sessionId: string;
  summary: ConfirmResponse;
}

function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState | undefined;
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink-50">
        <div className="text-center">
          <p className="text-sm text-ink-500 mb-4">No results found. Please start over.</p>
          <button onClick={() => navigate("/dashboard")} className="text-sm text-accent-600 font-medium">
            Go to dashboard
          </button>
        </div>
      </div>
    );
  }

  async function handleDownloadExcel() {
    setError(null);
    setDownloading("excel");
    try {
      const blob = await downloadExcel(state!.sessionId);
      triggerDownload(blob, "processed_timesheet.xlsx");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download the Excel file.");
    } finally {
      setDownloading(null);
    }
  }

  async function handleDownloadReport() {
    setError(null);
    setDownloading("report");
    try {
      const blob = await downloadReport(state!.sessionId);
      triggerDownload(blob, "validation_report.xlsx");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download the report.");
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="min-h-screen bg-ink-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-ink-100 p-8">
        <h1 className="text-lg font-semibold text-ink-900 mb-1">Processing complete</h1>
        <p className="text-sm text-ink-500 mb-6">
          Your master Excel has been updated. Review the summary below.
        </p>

        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-ink-50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-emerald-600">{state.summary.matched_count}</p>
            <p className="text-[11px] text-ink-500 mt-1">Matched</p>
          </div>
          <div className="bg-ink-50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-amber-600">{state.summary.unmatched_count}</p>
            <p className="text-[11px] text-ink-500 mt-1">Unmatched</p>
          </div>
          <div className="bg-ink-50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-accent-600">
              {state.summary.manually_corrected_count}
            </p>
            <p className="text-[11px] text-ink-500 mt-1">Corrected</p>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 mb-4 bg-red-50 border border-red-100 rounded-lg p-3">
            {error}
          </p>
        )}

        <div className="space-y-3">
          <button
            onClick={handleDownloadExcel}
            disabled={downloading !== null}
            className="w-full rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 hover:bg-accent-600 transition-colors disabled:opacity-50"
          >
            {downloading === "excel" ? "Downloading..." : "Download processed Excel"}
          </button>
          <button
            onClick={handleDownloadReport}
            disabled={downloading !== null}
            className="w-full rounded-lg bg-white border border-ink-100 text-ink-700 text-sm font-medium py-2.5 hover:bg-ink-50 transition-colors disabled:opacity-50"
          >
            {downloading === "report" ? "Downloading..." : "Download validation report"}
          </button>
        </div>

        <button
          onClick={() => navigate("/dashboard")}
          className="w-full text-center text-xs text-ink-500 hover:text-ink-900 mt-6"
        >
          Process another timesheet
        </button>
      </div>
    </div>
  );
}