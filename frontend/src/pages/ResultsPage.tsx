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

function SuccessIcon() {
  return (
    <div className="w-11 h-11 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
      <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
        <path
          d="M13.5 4.5L6 12L2.5 8.5"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-emerald-600"
        />
      </svg>
    </div>
  );
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
        <div className="text-center max-w-xs">
          <p className="text-sm text-ink-500 mb-4 leading-relaxed">No results found. Please start over.</p>
          <button
            onClick={() => navigate("/dashboard")}
            className="text-sm text-accent-600 font-medium hover:text-accent-700 transition-colors duration-150"
          >
            Go to dashboard →
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
    <div className="min-h-screen bg-gradient-to-b from-ink-50 to-white flex items-center justify-center px-4">
      <div className="w-full max-w-[420px] bg-white rounded-2xl shadow-card border border-ink-100 px-8 py-9">
        <SuccessIcon />
        <h1 className="text-lg font-semibold text-ink-900 tracking-tight mb-1">
          Processing complete
        </h1>
        <p className="text-sm text-ink-400 mb-7 leading-relaxed">
          Your master Excel has been updated. Review the summary below.
        </p>

        <div className="grid grid-cols-3 gap-2.5 mb-7">
          <div className="bg-ink-50 rounded-xl px-3 py-3.5 text-center">
            <p className="text-xl font-semibold text-emerald-600 tabular-nums">
              {state.summary.matched_count}
            </p>
            <p className="text-[11px] text-ink-400 mt-1 font-medium tracking-tight">Matched</p>
          </div>
          <div className="bg-ink-50 rounded-xl px-3 py-3.5 text-center">
            <p className="text-xl font-semibold text-amber-600 tabular-nums">
              {state.summary.unmatched_count}
            </p>
            <p className="text-[11px] text-ink-400 mt-1 font-medium tracking-tight">Unmatched</p>
          </div>
          <div className="bg-ink-50 rounded-xl px-3 py-3.5 text-center">
            <p className="text-xl font-semibold text-accent-600 tabular-nums">
              {state.summary.manually_corrected_count}
            </p>
            <p className="text-[11px] text-ink-400 mt-1 font-medium tracking-tight">Corrected</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-100 rounded-lg px-3.5 py-2.5 mb-5">
            <p className="text-sm text-red-600 font-medium">{error}</p>
          </div>
        )}

        <div className="space-y-2.5">
          <button
            onClick={handleDownloadExcel}
            disabled={downloading !== null}
            className="w-full rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 transition-all duration-150 hover:bg-accent-600 active:scale-[0.99] disabled:opacity-50 disabled:active:scale-100 shadow-sm"
          >
            {downloading === "excel" ? "Downloading…" : "Download processed Excel"}
          </button>
          <button
            onClick={handleDownloadReport}
            disabled={downloading !== null}
            className="w-full rounded-lg bg-white border border-ink-200 text-ink-700 text-sm font-medium py-2.5 transition-all duration-150 hover:bg-ink-50 hover:border-ink-300 active:scale-[0.99] disabled:opacity-50 disabled:active:scale-100"
          >
            {downloading === "report" ? "Downloading…" : "Download validation report"}
          </button>
        </div>

        <button
          onClick={() => navigate("/dashboard")}
          className="w-full text-center text-xs text-ink-400 hover:text-ink-700 font-medium mt-6 transition-colors duration-150"
        >
          Process another timesheet
        </button>
      </div>
    </div>
  );
}