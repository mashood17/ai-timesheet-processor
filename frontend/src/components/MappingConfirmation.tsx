import type { MappingDetectResponse } from "@/types";

interface MappingConfirmationProps {
  mapping: MappingDetectResponse;
  iqamaColumn: string;
  onIqamaColumnChange: (value: string) => void;
  onConfirm: () => void;
  loading: boolean;
}

const EXCEL_COLUMN_LETTERS = Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i));

function ConfidenceBadge({ percent }: { percent: number }) {
  const isHigh = percent >= 80;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-1.5 py-0.5 rounded-md ${
        isHigh ? "text-emerald-700 bg-emerald-50" : "text-amber-700 bg-amber-50"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isHigh ? "bg-emerald-600" : "bg-amber-500"}`} />
      {percent}% confidence
    </span>
  );
}

export function MappingConfirmation({
  mapping,
  iqamaColumn,
  onIqamaColumnChange,
  onConfirm,
  loading,
}: MappingConfirmationProps) {
  const iqamaConfidencePercent = Math.round(mapping.iqama_column_confidence * 100);
  const dayConfidencePercent = Math.round(mapping.day_columns_confidence * 100);

  return (
    <div className="border border-ink-100 rounded-xl p-6 mt-6 bg-white">
      <h3 className="text-sm font-semibold text-ink-900 tracking-tight mb-5">
        Confirm detected mapping
      </h3>

      {mapping.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200/70 rounded-lg px-3.5 py-3 mb-5">
          {mapping.warnings.map((warning, i) => (
            <p key={i} className="text-xs text-amber-800 leading-relaxed">
              {warning}
            </p>
          ))}
        </div>
      )}

      <div className="mb-5">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-medium text-ink-600 tracking-tight">
            IQAMA / Passport column
          </label>
          <ConfidenceBadge percent={iqamaConfidencePercent} />
        </div>
        <div className="relative">
          <select
            value={iqamaColumn}
            onChange={(e) => onIqamaColumnChange(e.target.value)}
            className="w-full appearance-none rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 pr-9 text-sm text-ink-900 transition-colors duration-150 focus:outline-none focus:border-accent-500 focus:ring-4 focus:ring-accent-500/10"
          >
            <option value="">Select a column…</option>
            {EXCEL_COLUMN_LETTERS.map((letter) => (
              <option key={letter} value={letter}>
                Column {letter}
              </option>
            ))}
          </select>
          <svg
            className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-400"
            width="14" height="14" viewBox="0 0 16 16" fill="none"
          >
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      <div className="mb-6 pb-5 border-b border-ink-100">
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-xs font-medium text-ink-600 tracking-tight">Day columns detected</p>
          <ConfidenceBadge percent={dayConfidencePercent} />
        </div>

        <p className="text-xs text-ink-500 mb-1">
          Alignment method:{" "}
          <span
            className={`font-medium ${
              mapping.alignment_method === "positional" ? "text-amber-600" : "text-emerald-700"
            }`}
          >
            {mapping.alignment_method === "positional"
              ? "By position (fallback — no real dates found in Excel)"
              : "By calendar date"}
          </span>
        </p>

        {mapping.day_columns.length > 0 && (
          <p className="text-xs text-ink-400">
            {mapping.day_columns[0].iso_date} → column{" "}
            <span className="font-medium text-ink-600">{mapping.day_columns[0].excel_column}</span>, through{" "}
            {mapping.day_columns[mapping.day_columns.length - 1].iso_date} → column{" "}
            <span className="font-medium text-ink-600">
              {mapping.day_columns[mapping.day_columns.length - 1].excel_column}
            </span>
          </p>
        )}
        {mapping.unmatched_pdf_dates.length > 0 && (
          <p className="text-xs text-amber-600 mt-1.5 leading-relaxed">
            {mapping.unmatched_pdf_dates.length} date(s) from the PDF had no matching Excel column:{" "}
            {mapping.unmatched_pdf_dates.join(", ")}
          </p>
        )}
      </div>

      <button
        onClick={onConfirm}
        disabled={loading || !iqamaColumn || mapping.day_columns.length === 0}
        className="w-full rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 transition-all duration-150 hover:bg-accent-600 active:scale-[0.99] disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 shadow-sm"
      >
        {loading ? "Processing…" : "Confirm mapping & Process"}
      </button>
    </div>
  );
}