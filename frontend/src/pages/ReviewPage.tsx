import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { confirmAndGenerate } from "@/api/endpoints";
import { ReportTable } from "@/components/ReportTable";
import { ReviewGrid } from "@/components/ReviewGrid";
import type { CorrectedCell, DuplicateEntry, EmployeeProcessResult, UnmatchedEntry } from "@/types";
import { ElapsedProgress } from "@/components/ElapsedProgress";

interface LocationState {
  sessionId: string;
  results: EmployeeProcessResult[];
  unmatched: UnmatchedEntry[];
  duplicates: DuplicateEntry[];
}

export function ReviewPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState | undefined;

  const [edits, setEdits] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const flaggedCount = useMemo(() => {
    if (!state) return 0;
    return state.results
      .filter((r) => r.matched)
      .reduce((sum, r) => sum + r.day_cells.filter((c) => c.needs_review).length, 0);
  }, [state]);

  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink-50">
        <div className="text-center">
          <p className="text-sm text-ink-500 mb-4">
            No processing session found. Please start from the dashboard.
          </p>
          <button
            onClick={() => navigate("/dashboard")}
            className="text-sm text-accent-600 font-medium"
          >
            Go to dashboard
          </button>
        </div>
      </div>
    );
  }

  function handleCellEdit(edit: { iqama: string; isoDate: string; value: string }) {
    setEdits((prev) => {
      const next = new Map(prev);
      next.set(`${edit.iqama}|${edit.isoDate}`, edit.value);
      return next;
    });
  }

  async function handleConfirm() {
    setError(null);
    setLoading(true);
    try {
      const correctedResults: CorrectedCell[] = Array.from(edits.entries()).map(([key, value]) => {
        const [iqama, isoDate] = key.split("|");
        return { iqama_or_passport: iqama, iso_date: isoDate, corrected_value: value };
      });

      const result = await confirmAndGenerate(state!.sessionId, correctedResults);
      navigate("/results", {
        state: { sessionId: state!.sessionId, summary: result },
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to confirm and generate the file.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-ink-50">
      <header className="border-b border-ink-100 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <h1 className="text-sm font-semibold text-ink-900">Review flagged cells</h1>
          <p className="text-xs text-ink-500 mt-1">
            {flaggedCount > 0
              ? `${flaggedCount} cell(s) need your review — highlighted in yellow. Correct or confirm them, then generate the final file.`
              : "No low-confidence cells were found. You can generate the file directly."}
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <ReviewGrid results={state.results} edits={edits} onCellEdit={handleCellEdit} />

        <ReportTable unmatched={state.unmatched} duplicates={state.duplicates} />

        {error && (
          <p className="text-sm text-red-600 mt-4 bg-red-50 border border-red-100 rounded-lg p-3">
            {error}
          </p>
        )}

        {loading && <ElapsedProgress label="Writing to Excel and generating reports..." />}

        <button
          onClick={handleConfirm}
          disabled={loading}
          className="mt-6 rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 px-6 hover:bg-accent-600 transition-colors disabled:opacity-50"
        >
          {loading ? "Generating..." : "Confirm & Generate"}
        </button>
      </main>
    </div>
  );
}