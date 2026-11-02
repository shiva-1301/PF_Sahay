"use client";

import { QUESTIONS } from "@/lib/content";
import type { Intake } from "@/lib/types";
import { Button, Card, ErrorNote, NavRow, Spinner, StepHeading } from "./ui";

export function StepIntake({
  intake,
  setIntake,
  answered,
  setAnswered,
  busy,
  error,
  onBack,
  onNext,
}: {
  intake: Intake;
  setIntake: (i: Intake) => void;
  answered: Set<keyof Intake>;
  setAnswered: (s: Set<keyof Intake>) => void;
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <Card>
      <StepHeading
        id="step-heading"
        title="Five quick questions"
        lead="These help us find the right fix. If you don't know, choose “Not sure”."
      />
      <div className="space-y-5">
        {QUESTIONS.map((q) => (
          <fieldset key={q.key}>
            <legend className="font-medium text-slate-900">{q.question}</legend>
            {q.help && <p className="text-sm text-slate-600">{q.help}</p>}
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {q.options.map((o) => {
                const checked = answered.has(q.key) && intake[q.key] === o.value;
                return (
                  <label
                    key={o.label}
                    className={`flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 ${
                      checked ? "border-teal-600 bg-teal-50" : "border-slate-300 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name={q.key}
                      className="h-4 w-4 accent-teal-700"
                      checked={checked}
                      onChange={() => {
                        setIntake({ ...intake, [q.key]: o.value });
                        setAnswered(new Set(answered).add(q.key));
                      }}
                    />
                    <span>{o.label}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
      {error && <ErrorNote message={error} />}
      <NavRow>
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext} disabled={busy}>
          {busy ? <Spinner label="Checking…" /> : "See diagnosis"}
        </Button>
      </NavRow>
    </Card>
  );
}
