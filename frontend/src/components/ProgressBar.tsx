interface ProgressBarProps {
  steps: string[];
  currentStepIndex: number;
}

export function ProgressBar({ steps, currentStepIndex }: ProgressBarProps) {
  return (
    <div className="flex items-center w-full mb-8">
      {steps.map((step, index) => {
        const isComplete = index < currentStepIndex;
        const isCurrent = index === currentStepIndex;
        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold
                  ${isComplete ? "bg-accent-500 text-white" : ""}
                  ${isCurrent ? "bg-accent-100 text-accent-700 border-2 border-accent-500" : ""}
                  ${!isComplete && !isCurrent ? "bg-ink-100 text-ink-300" : ""}
                `}
              >
                {isComplete ? "✓" : index + 1}
              </div>
              <span
                className={`mt-2 text-xs whitespace-nowrap ${
                  isCurrent ? "text-ink-900 font-medium" : "text-ink-300"
                }`}
              >
                {step}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-2 ${isComplete ? "bg-accent-500" : "bg-ink-100"}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}