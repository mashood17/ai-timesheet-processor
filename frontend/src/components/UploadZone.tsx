import { useRef, useState, type DragEvent } from "react";

interface UploadZoneProps {
  label: string;
  accept: string;
  onFileSelected: (file: File) => void;
  uploadedFileName: string | null;
  disabled?: boolean;
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
      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors
        ${isDragging ? "border-accent-500 bg-accent-50" : "border-ink-100"}
        ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-accent-500 hover:bg-accent-50"}
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
      <p className="text-sm font-medium text-ink-700">{label}</p>
      {uploadedFileName ? (
        <p className="text-sm text-accent-600 mt-1">{uploadedFileName}</p>
      ) : (
        <p className="text-xs text-ink-300 mt-1">Click or drag a file here</p>
      )}
    </div>
  );
}