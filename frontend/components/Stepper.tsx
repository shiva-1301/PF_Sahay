import { STEPS } from "@/lib/content";

export function Stepper({ current }: { current: number }) {
  return (
    <nav aria-label="Progress" className="mb-5">
      <p className="mb-2 text-sm font-medium text-slate-600">
        Step {current + 1} of {STEPS.length}: <span className="text-slate-900">{STEPS[current]}</span>
      </p>
      <ol className="grid grid-cols-5 gap-1.5">
        {STEPS.map((label, i) => (
          <li key={label} aria-current={i === current ? "step" : undefined}>
            <span
              className={`block h-2 rounded-full ${i < current ? "bg-teal-700" : i === current ? "bg-teal-500" : "bg-slate-200"}`}
            />
            <span className="sr-only">
              {label}
              {i < current ? " (done)" : i === current ? " (current)" : ""}
            </span>
          </li>
        ))}
      </ol>
    </nav>
  );
}
