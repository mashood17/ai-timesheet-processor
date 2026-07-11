interface SheetSelectorProps {
  sheetNames: string[];
  selectedSheet: string;
  onSelect: (sheetName: string) => void;
}

export function SheetSelector({ sheetNames, selectedSheet, onSelect }: SheetSelectorProps) {
  if (sheetNames.length <= 1) return null;

  return (
    <div className="mt-5">
      <label className="block text-xs font-medium text-ink-600 mb-1.5 tracking-tight">
        Target sheet
      </label>
      <div className="relative">
        <select
          value={selectedSheet}
          onChange={(e) => onSelect(e.target.value)}
          className="w-full appearance-none rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 pr-9 text-sm text-ink-900 transition-colors duration-150 focus:outline-none focus:border-accent-500 focus:ring-4 focus:ring-accent-500/10"
        >
          {sheetNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <svg
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-400"
          width="14"
          height="14"
          viewBox="0 0 16 16"
          fill="none"
        >
          <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}