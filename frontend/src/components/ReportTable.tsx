import type { DuplicateEntry, UnmatchedEntry } from "@/types";

interface ReportTableProps {
  unmatched: UnmatchedEntry[];
  duplicates: DuplicateEntry[];
}

export function ReportTable({ unmatched, duplicates }: ReportTableProps) {
  if (unmatched.length === 0 && duplicates.length === 0) return null;

  return (
    <div className="mt-6 space-y-4">
      {unmatched.length > 0 && (
        <div className="border border-ink-100 rounded-xl overflow-hidden">
          <div className="bg-ink-700 text-white text-xs font-medium px-3 py-2">
            Unmatched IQAMAs ({unmatched.length})
          </div>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="bg-ink-50 text-ink-500">
                <th className="px-3 py-2 text-left font-medium">IQAMA / Passport</th>
                <th className="px-3 py-2 text-left font-medium">Employee Name</th>
                <th className="px-3 py-2 text-left font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {unmatched.map((entry, i) => (
                <tr key={i} className="border-t border-ink-100">
                  <td className="px-3 py-1.5">{entry.iqama_or_passport}</td>
                  <td className="px-3 py-1.5">{entry.employee_name}</td>
                  <td className="px-3 py-1.5 text-ink-500">{entry.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {duplicates.length > 0 && (
        <div className="border border-ink-100 rounded-xl overflow-hidden">
          <div className="bg-ink-700 text-white text-xs font-medium px-3 py-2">
            Duplicate IQAMAs found in PDF ({duplicates.length})
          </div>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="bg-ink-50 text-ink-500">
                <th className="px-3 py-2 text-left font-medium">IQAMA / Passport</th>
                <th className="px-3 py-2 text-left font-medium">Occurrences</th>
                <th className="px-3 py-2 text-left font-medium">Employee Name(s)</th>
              </tr>
            </thead>
            <tbody>
              {duplicates.map((entry, i) => (
                <tr key={i} className="border-t border-ink-100">
                  <td className="px-3 py-1.5">{entry.iqama_or_passport}</td>
                  <td className="px-3 py-1.5">{entry.occurrences}</td>
                  <td className="px-3 py-1.5 text-ink-500">
                    {entry.employee_names.join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}