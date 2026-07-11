import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { confirmAndGenerate } from "@/api/endpoints";
import { ElapsedProgress } from "@/components/ElapsedProgress";
import { ReportTable } from "@/components/ReportTable";
import { ReviewGrid } from "@/components/ReviewGrid";
import { acceptPossibleMatch } from "@/api/endpoints";
import type { CorrectedCell, DuplicateEntry, EmployeeProcessResult, UnmatchedEntry } from "@/types";

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

  const [results, setResults] = useState(state?.results ?? []);
  const [unmatched, setUnmatched] = useState(state?.unmatched ?? []);
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
        <div className="text-center max-w-xs">
          <p className="text-sm text-ink-500 mb-4 leading-relaxed">
            No processing session found. Please start from the dashboard.
          </p>
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

  function handleCellEdit(edit: { iqama: string; isoDate: string; value: string }) {
    setEdits((prev) => {
      const next = new Map(prev);
      next.set(`${edit.iqama}|${edit.isoDate}`, edit.value);
      return next;
    });
  }

  async function handleAcceptMatch(unmatchedIqama: string, acceptedIqama: string) {
    if (!state) return;
    try {
      const response = await acceptPossibleMatch(state.sessionId, unmatchedIqama, acceptedIqama);
      setResults(response.results);
      setUnmatched(response.unmatched);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to accept the match.");
    }
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
      <header className="border-b border-ink-100 bg-white/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <h1 className="text-sm font-semibold text-ink-900 tracking-tight">Review flagged cells</h1>
          <p className="text-xs text-ink-400 mt-1">
            {flaggedCount > 0 ? (
              <>
                <span className="font-medium text-amber-600">{flaggedCount} cell(s)</span> need your
                review — highlighted below. Correct or confirm them, then generate the final file.
              </>
            ) : (
              "No low-confidence cells were found. You can generate the file directly."
            )}
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <ReviewGrid results={results} edits={edits} onCellEdit={handleCellEdit} />

        <ReportTable
          unmatched={unmatched}
          duplicates={state.duplicates}
          onAcceptMatch={handleAcceptMatch}
        />

        {error && (
          <div className="bg-red-50 border border-red-100 rounded-lg px-3.5 py-2.5 mt-5">
            <p className="text-sm text-red-600 font-medium">{error}</p>
          </div>
        )}

        {loading && <ElapsedProgress label="Writing to Excel and generating reports…" />}

        <button
          onClick={handleConfirm}
          disabled={loading}
          className="mt-6 rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 px-6 transition-all duration-150 hover:bg-accent-600 active:scale-[0.99] disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 shadow-sm"
        >
          {loading ? "Generating…" : "Confirm & Generate"}
        </button>
      </main>
    </div>
  );
}