import type { EmployeeProcessResult } from "@/types";

interface CellEdit {
  iqama: string;
  isoDate: string;
  value: string;
}

interface ReviewGridProps {
  results: EmployeeProcessResult[];
  edits: Map<string, string>; // key: `${iqama}|${isoDate}` -> corrected value
  onCellEdit: (edit: CellEdit) => void;
}

function cellKey(iqama: string, isoDate: string): string {
  return `${iqama}|${isoDate}`;
}

export function ReviewGrid({ results, edits, onCellEdit }: ReviewGridProps) {
  const matchedResults = results.filter((r) => r.matched);
  const allDates = matchedResults[0]?.day_cells.map((c) => c.iso_date) ?? [];

  return (
    <div className="overflow-x-auto border border-ink-100 rounded-xl">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="bg-ink-700 text-white">
            <th className="px-3 py-2 text-left font-medium sticky left-0 bg-ink-700">IQAMA</th>
            <th className="px-3 py-2 text-left font-medium sticky left-[110px] bg-ink-700">
              Name
            </th>
            {allDates.map((isoDate) => (
              <th key={isoDate} className="px-2 py-2 text-center font-medium whitespace-nowrap">
                {isoDate.slice(5)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matchedResults.map((employee) => {
            const iqama = employee.iqama_or_passport ?? "";
            return (
              <tr key={iqama} className="border-t border-ink-100 hover:bg-ink-50">
                <td className="px-3 py-1.5 sticky left-0 bg-white whitespace-nowrap">
                  {iqama}
                </td>
                <td className="px-3 py-1.5 sticky left-[110px] bg-white whitespace-nowrap">
                  {employee.employee_name}
                </td>
                {employee.day_cells.map((cell) => {
                  const key = cellKey(iqama, cell.iso_date);
                  const currentValue = edits.get(key) ?? cell.value;
                  const isFlagged = cell.needs_review;

                  return (
                    <td key={cell.iso_date} className="px-1 py-1 text-center">
                      <input
                        value={currentValue}
                        onChange={(e) =>
                          onCellEdit({ iqama, isoDate: cell.iso_date, value: e.target.value })
                        }
                        className={`w-12 text-center text-xs rounded border px-1 py-1 focus:outline-none focus:ring-1 focus:ring-accent-500
                          ${isFlagged ? "border-amber-400 bg-amber-50" : "border-ink-100"}
                          ${currentValue === "?" ? "border-red-400 bg-red-50" : ""}
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