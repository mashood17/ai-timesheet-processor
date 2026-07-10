import { useEffect, useState } from "react";

interface ElapsedProgressProps {
  label: string;
}

/**
 * Section 11 requires "a real progress indicator (not a fake spinner)".
 * Since /api/process is a single long-running request with no
 * intermediate progress events (per Section 7's fixed endpoint contract —
 * no additional polling endpoint is added), this shows genuine elapsed
 * time instead of a fake percentage, so the user can see the app is
 * actively working rather than frozen — honest feedback rather than a
 * misleading progress bar.
 */
export function ElapsedProgress({ label }: ElapsedProgressProps) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const minutes = Math.floor(seconds / 60);
  const displaySeconds = seconds % 60;
  const timeLabel =
    minutes > 0 ? `${minutes}m ${displaySeconds}s` : `${displaySeconds}s`;

  return (
    <div className="flex items-center gap-3 text-sm text-accent-600 mt-4">
      <span className="w-4 h-4 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
      <span>
        {label} <span className="text-ink-400">({timeLabel} elapsed)</span>
      </span>
    </div>
  );
}