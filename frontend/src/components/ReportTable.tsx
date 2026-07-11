import type { DuplicateEntry, UnmatchedEntry } from "@/types";

interface ReportTableProps {
  unmatched: UnmatchedEntry[];
  duplicates: DuplicateEntry[];
  onAcceptMatch?: (unmatchedIqama: string, acceptedIqama: string) => void;
}


export function ReportTable({ unmatched, duplicates, onAcceptMatch }: ReportTableProps) {

  if (unmatched.length === 0 && duplicates.length === 0) return null;

  return (
    <div className="mt-6 space-y-5">
      {unmatched.length > 0 && (
        <div className="border border-ink-100 rounded-xl overflow-hidden bg-white shadow-card">
          <div className="flex items-center gap-2 bg-amber-50 border-b border-amber-100 px-4 py-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            <span className="text-xs font-semibold text-amber-800 tracking-tight">
              Unmatched IQAMAs ({unmatched.length})
            </span>
          </div>
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  IQAMA / Passport
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  Employee Name
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  Reason
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  Possible Match
                </th>
              </tr>
            </thead>
            <tbody>
              {unmatched.map((entry, i) => (
                <tr key={i} className="hover:bg-ink-50/60 transition-colors duration-150">
                  <td className="px-4 py-2.5 text-ink-700 border-b border-ink-50">
                    {entry.iqama_or_passport}
                  </td>
                  <td className="px-4 py-2.5 text-ink-900 font-medium border-b border-ink-50">
                    {entry.employee_name}
                  </td>
                  <td className="px-4 py-2.5 text-ink-400 border-b border-ink-50">{entry.reason}</td>
                  <td className="px-4 py-2.5 border-b border-ink-50">
                    {entry.possible_match && entry.iqama_or_passport && (
                      <div className="flex items-center gap-2">
                        <span className="text-amber-700 bg-amber-50 rounded-md px-2 py-0.5 text-xs font-medium">
                          Did you mean {entry.possible_match}?
                        </span>
                        {onAcceptMatch && (
                          <button
                            onClick={() =>
                              onAcceptMatch(entry.iqama_or_passport!, entry.possible_match!)
                            }
                            className="text-xs font-medium text-accent-600 hover:text-accent-700 underline"
                          >
                            Accept
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {duplicates.length > 0 && (
        <div className="border border-ink-100 rounded-xl overflow-hidden bg-white shadow-card">
          <div className="flex items-center gap-2 bg-red-50 border-b border-red-100 px-4 py-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-red-600" />
            <span className="text-xs font-semibold text-red-700 tracking-tight">
              Duplicate IQAMAs found in PDF ({duplicates.length})
            </span>
          </div>
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  IQAMA / Passport
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  Occurrences
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-ink-400 tracking-wide uppercase border-b border-ink-50">
                  Employee Name(s)
                </th>
              </tr>
            </thead>
            <tbody>
              {duplicates.map((entry, i) => (
                <tr key={i} className="hover:bg-ink-50/60 transition-colors duration-150">
                  <td className="px-4 py-2.5 text-ink-700 border-b border-ink-50">
                    {entry.iqama_or_passport}
                  </td>
                  <td className="px-4 py-2.5 text-ink-900 font-medium border-b border-ink-50">
                    {entry.occurrences}
                  </td>
                  <td className="px-4 py-2.5 text-ink-400 border-b border-ink-50">
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