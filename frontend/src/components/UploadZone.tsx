import { useRef, useState, type DragEvent } from "react";

interface UploadZoneProps {
  label: string;
  accept: string;
  onFileSelected: (file: File) => void;
  uploadedFileName: string | null;
  disabled?: boolean;
}

function FileIcon({ done }: { done: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={done ? "text-accent-500" : "text-ink-300"}
    >
      <path
        d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function UploadZone({
  label,
  accept,
  onFileSelected,
  uploadedFileName,
  disabled = false,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const file = event.dataTransfer.files[0];
    if (file) onFileSelected(file);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`group border rounded-xl px-5 py-6 text-center cursor-pointer transition-all duration-150
        ${isDragging ? "border-accent-500 bg-accent-50 ring-4 ring-accent-500/10" : "border-dashed border-ink-200 bg-ink-50/40"}
        ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-accent-400 hover:bg-accent-50/50"}
        ${uploadedFileName ? "border-solid border-accent-200 bg-accent-50/30" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelected(file);
        }}
      />
      <div className="flex justify-center mb-2.5">
        <FileIcon done={!!uploadedFileName} />
      </div>
      <p className="text-sm font-medium text-ink-700 tracking-tight">{label}</p>
      {uploadedFileName ? (
        <p className="text-xs text-accent-600 font-medium mt-1 truncate px-2">{uploadedFileName}</p>
      ) : (
        <p className="text-xs text-ink-300 mt-1">Click to browse or drag a file here</p>
      )}
    </div>
  );
}