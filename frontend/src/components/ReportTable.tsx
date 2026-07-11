import { useState } from "react";
import type { DuplicateEntry, UnmatchedEntry } from "@/types";

interface ReportTableProps {
  unmatched: UnmatchedEntry[];
  duplicates: DuplicateEntry[];
  onAcceptMatches?: (
    matches: { unmatched_iqama_or_passport: string; accepted_iqama: string }[]
  ) => void;
}

export function ReportTable({ unmatched, duplicates, onAcceptMatches }: ReportTableProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const suggestable = unmatched.filter((e) => e.possible_match && e.iqama_or_passport);

  function toggleSelected(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === suggestable.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(suggestable.map((e) => e.iqama_or_passport!)));
    }
  }

  function handleAcceptSelected() {
    if (!onAcceptMatches) return;
    const matches = suggestable
      .filter((e) => selected.has(e.iqama_or_passport!))
      .map((e) => ({
        unmatched_iqama_or_passport: e.iqama_or_passport!,
        accepted_iqama: e.possible_match!,
      }));
    if (matches.length === 0) return;
    onAcceptMatches(matches);
    setSelected(new Set());
  }

  if (unmatched.length === 0 && duplicates.length === 0) return null;

  return (
    <div className="mt-6 space-y-5">
      {unmatched.length > 0 && (
        <div className="border border-ink-100 rounded-xl overflow-hidden bg-white shadow-card">
          <div className="flex items-center justify-between gap-3 bg-amber-50 border-b border-amber-100 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              <span className="text-xs font-semibold text-amber-800 tracking-tight">
                Unmatched IQAMAs ({unmatched.length})
              </span>
            </div>
            {suggestable.length > 0 && onAcceptMatches && (
              <button
                onClick={handleAcceptSelected}
                disabled={selected.size === 0}
                className="text-xs font-medium text-white bg-accent-500 hover:bg-accent-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-md px-3 py-1.5 transition-colors duration-150"
              >
                Accept selected ({selected.size})
              </button>
            )}
          </div>
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                {suggestable.length > 0 && onAcceptMatches && (
                  <th className="px-4 py-2.5 text-left border-b border-ink-50 w-10">
                    <input
                      type="checkbox"
                      checked={selected.size === suggestable.length && suggestable.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-ink-300"
                    />
                  </th>
                )}
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
              {unmatched.map((entry, i) => {
                const canSelect = !!entry.possible_match && !!entry.iqama_or_passport;
                const key = entry.iqama_or_passport ?? `row-${i}`;
                return (
                  <tr key={i} className="hover:bg-ink-50/60 transition-colors duration-150">
                    {suggestable.length > 0 && onAcceptMatches && (
                      <td className="px-4 py-2.5 border-b border-ink-50">
                        {canSelect && (
                          <input
                            type="checkbox"
                            checked={selected.has(key)}
                            onChange={() => toggleSelected(key)}
                            className="rounded border-ink-300"
                          />
                        )}
                      </td>
                    )}
                    <td className="px-4 py-2.5 text-ink-700 border-b border-ink-50">
                      {entry.iqama_or_passport}
                    </td>
                    <td className="px-4 py-2.5 text-ink-900 font-medium border-b border-ink-50">
                      {entry.employee_name}
                    </td>
                    <td className="px-4 py-2.5 text-ink-400 border-b border-ink-50">{entry.reason}</td>
                    <td className="px-4 py-2.5 border-b border-ink-50">
                      {entry.possible_match && (
                        <span className="text-amber-700 bg-amber-50 rounded-md px-2 py-0.5 text-xs font-medium">
                          Did you mean {entry.possible_match}?
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
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