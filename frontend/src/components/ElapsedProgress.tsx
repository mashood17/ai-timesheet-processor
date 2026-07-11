import { useEffect, useState } from "react";

interface ElapsedProgressProps {
  label: string;
}

export function ElapsedProgress({ label }: ElapsedProgressProps) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const minutes = Math.floor(seconds / 60);
  const displaySeconds = seconds % 60;
  const timeLabel = minutes > 0 ? `${minutes}m ${displaySeconds}s` : `${displaySeconds}s`;

  return (
    <div className="flex items-center gap-2.5 text-sm bg-accent-50/60 border border-accent-100 rounded-lg px-3.5 py-3 mt-4">
      <span className="w-3.5 h-3.5 border-2 border-accent-500 border-t-transparent rounded-full animate-spin shrink-0" />
      <span className="text-accent-700 font-medium">{label}</span>
      <span className="text-accent-400 text-xs ml-auto tabular-nums">{timeLabel}</span>
    </div>
  );
}