interface ProgressBarProps {
  steps: string[];
  currentStepIndex: number;
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M13.5 4.5L6 12L2.5 8.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ProgressBar({ steps, currentStepIndex }: ProgressBarProps) {
  return (
    <div className="flex items-start w-full mb-10">
      {steps.map((step, index) => {
        const isComplete = index < currentStepIndex;
        const isCurrent = index === currentStepIndex;
        return (
          <div key={step} className="flex items-start flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors duration-150
                  ${isComplete ? "bg-ink-900 text-white" : ""}
                  ${isCurrent ? "bg-white text-accent-600 border-2 border-accent-500 shadow-sm" : ""}
                  ${!isComplete && !isCurrent ? "bg-white text-ink-300 border border-ink-200" : ""}
                `}
              >
                {isComplete ? <CheckIcon /> : index + 1}
              </div>
              <span
                className={`mt-2 text-xs whitespace-nowrap tracking-tight transition-colors duration-150 ${
                  isCurrent ? "text-ink-900 font-medium" : isComplete ? "text-ink-500 font-medium" : "text-ink-300"
                }`}
              >
                {step}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={`flex-1 h-px mx-3 mt-3.5 transition-colors duration-150 ${
                  isComplete ? "bg-ink-900" : "bg-ink-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}