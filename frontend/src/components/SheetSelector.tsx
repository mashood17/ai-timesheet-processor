interface SheetSelectorProps {
  sheetNames: string[];
  selectedSheet: string;
  onSelect: (sheetName: string) => void;
}

export function SheetSelector({ sheetNames, selectedSheet, onSelect }: SheetSelectorProps) {
  if (sheetNames.length <= 1) return null;

  return (
    <div className="mt-4">
      <label className="block text-sm font-medium text-ink-700 mb-1">
        Select the target sheet
      </label>
      <select
        value={selectedSheet}
        onChange={(e) => onSelect(e.target.value)}
        className="w-full rounded-lg border border-ink-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
      >
        {sheetNames.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </div>
  );
}