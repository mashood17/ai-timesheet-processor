import type { MappingDetectResponse } from "@/types";

interface MappingConfirmationProps {
  mapping: MappingDetectResponse;
  iqamaColumn: string;
  onIqamaColumnChange: (value: string) => void;
  onConfirm: () => void;
  loading: boolean;
}

const EXCEL_COLUMN_LETTERS = Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i));

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
    <div className="border border-ink-100 rounded-xl p-5 mt-6">
      <h3 className="text-sm font-semibold text-ink-900 mb-4">Confirm detected mapping</h3>

      {mapping.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
          {mapping.warnings.map((warning, i) => (
            <p key={i} className="text-xs text-amber-800">
              {warning}
            </p>
          ))}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-sm font-medium text-ink-700 mb-1">
          IQAMA / Passport column
          <span
            className={`ml-2 text-xs font-normal ${
              iqamaConfidencePercent >= 80 ? "text-emerald-600" : "text-amber-600"
            }`}
          >
            {iqamaConfidencePercent}% confidence
          </span>
        </label>
        <select
          value={iqamaColumn}
          onChange={(e) => onIqamaColumnChange(e.target.value)}
          className="w-full rounded-lg border border-ink-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
        >
          <option value="">Select a column...</option>
          {EXCEL_COLUMN_LETTERS.map((letter) => (
            <option key={letter} value={letter}>
              Column {letter}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4">
        <p className="text-sm font-medium text-ink-700 mb-1">
          Day columns detected
          <span
            className={`ml-2 text-xs font-normal ${
              dayConfidencePercent >= 80 ? "text-emerald-600" : "text-amber-600"
            }`}
          >
            {dayConfidencePercent}% matched ({mapping.day_columns.length} of{" "}
            {mapping.day_columns.length + mapping.unmatched_pdf_dates.length} days)
          </span>
        </p>

        <p className="text-xs mb-1">
          Alignment method:{" "}
          <span className={mapping.alignment_method === "positional" ? "text-amber-600 font-medium" : "text-emerald-600 font-medium"}>
            {mapping.alignment_method === "positional"
              ? "By position (fallback — no real dates found in Excel)"
              : "By calendar date"}
          </span>
        </p>

        {mapping.day_columns.length > 0 && (
          <p className="text-xs text-ink-500">
            {mapping.day_columns[0].iso_date} → column {mapping.day_columns[0].excel_column}, through{" "}
            {mapping.day_columns[mapping.day_columns.length - 1].iso_date} → column{" "}
            {mapping.day_columns[mapping.day_columns.length - 1].excel_column}
          </p>
        )}
        {mapping.unmatched_pdf_dates.length > 0 && (
          <p className="text-xs text-amber-600 mt-1">
            {mapping.unmatched_pdf_dates.length} date(s) from the PDF had no matching Excel column:{" "}
            {mapping.unmatched_pdf_dates.join(", ")}
          </p>
        )}
      </div>

      <button
        onClick={onConfirm}
        disabled={loading || !iqamaColumn || mapping.day_columns.length === 0}
        className="w-full rounded-lg bg-accent-500 text-white text-sm font-medium py-2.5 hover:bg-accent-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Processing..." : "Confirm mapping & Process"}
      </button>
    </div>
  );
}