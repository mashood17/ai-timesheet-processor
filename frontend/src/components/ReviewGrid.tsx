import type { EmployeeProcessResult } from "@/types";

interface CellEdit {
  iqama: string;
  isoDate: string;
  value: string;
}

interface ReviewGridProps {
  results: EmployeeProcessResult[];
  edits: Map<string, string>;
  onCellEdit: (edit: CellEdit) => void;
}

function cellKey(iqama: string, isoDate: string): string {
  return `${iqama}|${isoDate}`;
}

export function ReviewGrid({ results, edits, onCellEdit }: ReviewGridProps) {
  const matchedResults = results.filter((r) => r.matched);
  const allDates = matchedResults[0]?.day_cells.map((c) => c.iso_date) ?? [];

  return (
    <div className="overflow-x-auto border border-ink-100 rounded-xl bg-white shadow-card">
      <table className="min-w-full text-sm border-separate border-spacing-0">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-ink-500 tracking-wide uppercase sticky left-0 bg-ink-50 border-b border-ink-100 z-10">
              IQAMA
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-ink-500 tracking-wide uppercase sticky left-[128px] bg-ink-50 border-b border-ink-100 z-10">
              Name
            </th>
            {allDates.map((isoDate) => (
              <th
                key={isoDate}
                className="px-1.5 py-3 text-center text-xs font-semibold text-ink-500 tracking-wide uppercase whitespace-nowrap bg-ink-50 border-b border-ink-100"
              >
                {isoDate.slice(5)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matchedResults.map((employee, rowIdx) => {
            const iqama = employee.iqama_or_passport ?? "";
            return (
              <tr key={iqama + rowIdx} className="group">
                <td className="px-4 py-2 text-sm text-ink-700 sticky left-0 bg-white group-hover:bg-ink-50/60 whitespace-nowrap border-b border-ink-50 transition-colors duration-150">
                  {iqama}
                </td>
                <td className="px-4 py-2 text-sm text-ink-900 font-medium sticky left-[128px] bg-white group-hover:bg-ink-50/60 whitespace-nowrap border-b border-ink-50 transition-colors duration-150">
                  {employee.employee_name}
                </td>
                {employee.day_cells.map((cell) => {
                  const key = cellKey(iqama, cell.iso_date);
                  const currentValue = edits.get(key) ?? cell.value;
                  const isFlagged = cell.needs_review;
                  const isUnresolved = currentValue === "?";

                  return (
                    <td
                      key={cell.iso_date}
                      className="px-1 py-1.5 text-center border-b border-ink-50 group-hover:bg-ink-50/60 transition-colors duration-150"
                    >
                      <input
                        value={currentValue}
                        onChange={(e) =>
                          onCellEdit({ iqama, isoDate: cell.iso_date, value: e.target.value })
                        }
                        className={`w-11 text-center text-xs rounded-md border px-1 py-1.5 transition-all duration-150 focus:outline-none focus:ring-4 focus:ring-accent-500/10 focus:border-accent-500
                          ${isFlagged ? "border-amber-300 bg-amber-50 text-amber-800 font-medium" : "border-ink-150 border-ink-200 bg-white text-ink-700"}
                          ${isUnresolved ? "border-red-300 bg-red-50 text-red-700 font-medium" : ""}
                        `}
                        title={
                          isFlagged
                            ? `Low confidence (${Math.round(cell.confidence * 100)}%) — please verify`
                            : `${Math.round(cell.confidence * 100)}% confidence`
                        }
                      />
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}