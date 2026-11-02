"use client";

import { CODE_TITLES, CONFIDENCE_HELP, QUESTION_TO_INTAKE } from "@/lib/content";
import type { Diagnosis, Explanation, Intake } from "@/lib/types";
import { Button, Card, ErrorNote, NavRow, Spinner, StepHeading } from "./ui";

/** Codes whose fix is a Joint Declaration, so the category matters. */
const JD_CODES = ["R01", "R03", "R05"];

const REDACTION_WORDS: Record<string, string> = {
  AADHAAR: "Aadhaar number",
  PAN: "PAN",
  UAN: "UAN",
  ACCOUNT: "bank account number",
  MOBILE: "mobile number",
  EMAIL: "email address",
  NAME: "name",
  NUMBER: "long number",
};

function redactionNote(redactions: Record<string, number>): string | null {
  const parts = Object.entries(redactions).map(([k, n]) => `${n} ${REDACTION_WORDS[k] ?? k.toLowerCase()}${n > 1 ? "s" : ""}`);
  return parts.length ? `We removed ${parts.join(", ")} before analysing your text.` : null;
}

/** Render "[C12]" markers as small source tags. */
function CitedText({ text }: { text: string }) {
  const parts = text.split(/(\[C\d+\])/g);
  return (
    <>
      {parts.map((p, i) =>
        /^\[C\d+\]$/.test(p) ? (
          <sup key={i} className="ml-0.5 rounded bg-slate-100 px-1 text-xs font-medium text-slate-600">
            {p.slice(1, -1)}
          </sup>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

function ExplanationView({ explanation }: { explanation: Explanation }) {
  const live = explanation.model !== "canned";
  return (
    <div className="space-y-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {live ? "AI explanation, checked against the sources below" : "Standard explanation"}
      </p>
      {explanation.paragraphs.map((p, i) => (
        <div key={i}>
          <p className="whitespace-pre-line leading-relaxed text-slate-800">
            <CitedText text={p.text} />
          </p>
          {p.citations.length > 0 && (
            <details className="mt-1 text-sm">
              <summary className="cursor-pointer text-teal-800 hover:underline">
                {p.citations.length === 1 ? "1 source" : `${p.citations.length} sources`}
              </summary>
              <ul className="mt-1 space-y-1 border-l-2 border-slate-200 pl-3">
                {p.citations.map((c) => (
                  <li key={c.id} className="text-slate-700">
                    <span className="font-medium text-slate-500">{c.id}</span>{" "}
                    {c.source_url ? (
                      <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="break-words text-teal-800 underline">
                        {c.source_title}
                      </a>
                    ) : (
                      c.source_title
                    )}
                    {c.source_date && <span className="text-slate-500"> ({c.source_date})</span>}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}

export function StepDiagnosis({
  diagnosis,
  explanation,
  explainError,
  onAnswer,
  busy,
  onBack,
  onNext,
}: {
  diagnosis: Diagnosis;
  explanation: Explanation | null;
  explainError: string | null;
  onAnswer: (key: keyof Intake, value: boolean) => void;
  busy: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  const note = redactionNote(diagnosis.redactions);
  const answerKey = diagnosis.clarifying_question ? QUESTION_TO_INTAKE[diagnosis.clarifying_question] : undefined;

  return (
    <Card>
      <StepHeading id="step-heading" title="What went wrong" />

      <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
        <p className="text-lg font-semibold leading-snug text-slate-900">{CODE_TITLES[diagnosis.code]}</p>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-600">How sure we are</dt>
            <dd className="font-medium text-slate-900">
              {diagnosis.confidence_label}
              <span className="block font-normal text-slate-600">{CONFIDENCE_HELP[diagnosis.confidence_label]}</span>
            </dd>
          </div>
          {diagnosis.jd_category && JD_CODES.includes(diagnosis.code) && (
            <div>
              <dt className="text-slate-600">Your Joint Declaration category</dt>
              <dd className="font-medium text-slate-900">
                Category {diagnosis.jd_category}
                <span className="block font-normal text-slate-600">{diagnosis.jd_meaning}</span>
              </dd>
            </div>
          )}
        </dl>
        <p className="mt-3 text-xs text-slate-500">
          Code {diagnosis.code}: {diagnosis.name}
        </p>
      </div>

      {note && <p className="mt-3 text-sm text-slate-600">{note}</p>}

      {diagnosis.clarifying_question && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="font-medium text-amber-900">{diagnosis.clarifying_question}</p>
          {answerKey ? (
            <div className="mt-2 flex gap-2">
              <Button variant="secondary" disabled={busy} onClick={() => onAnswer(answerKey, true)}>
                Yes
              </Button>
              <Button variant="secondary" disabled={busy} onClick={() => onAnswer(answerKey, false)}>
                No
              </Button>
            </div>
          ) : (
            <p className="mt-1 text-sm text-amber-900">Check this on the EPFO portal, then go back and update your answers.</p>
          )}
        </div>
      )}

      <h3 className="mb-2 mt-6 text-lg font-semibold text-slate-900">What this means</h3>
      {explanation ? (
        <ExplanationView explanation={explanation} />
      ) : explainError ? (
        <ErrorNote message={explainError} />
      ) : (
        <Spinner label="Writing a plain-language explanation…" />
      )}

      <NavRow>
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext}>See your fix</Button>
      </NavRow>
    </Card>
  );
}
