import type { Diagnosis } from "@/lib/types";
import { Button, Card, NavRow, StepHeading } from "./ui";

export function StepFix({ diagnosis, onBack, onNext }: { diagnosis: Diagnosis; onBack: () => void; onNext: () => void }) {
  return (
    <Card>
      <StepHeading id="step-heading" title="Your fix" lead="This is the usual way this rejection is fixed. Do the steps in order." />
      <ol className="space-y-3">
        {diagnosis.fix_steps.map((step, i) => (
          <li key={i} className="flex gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-teal-700 text-sm font-semibold text-white">
              {i + 1}
            </span>
            <span className="pt-0.5 leading-relaxed text-slate-800">{step}</span>
          </li>
        ))}
      </ol>
      <p className="mt-5 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
        EPFO decides every claim. These steps fix the usual cause; they cannot promise a result. Never share your UAN
        password or OTP with anyone.
      </p>
      <NavRow>
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext}>Get your documents</Button>
      </NavRow>
    </Card>
  );
}
