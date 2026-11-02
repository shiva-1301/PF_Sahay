"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Stepper } from "@/components/Stepper";
import { StepDiagnosis } from "@/components/StepDiagnosis";
import { StepDocuments } from "@/components/StepDocuments";
import { StepFix } from "@/components/StepFix";
import { StepIntake } from "@/components/StepIntake";
import { StepPaste } from "@/components/StepPaste";
import { classify, explain, ocrStatus } from "@/lib/api";
import { DEMO_CASES } from "@/lib/content";
import { EMPTY_INTAKE, type Diagnosis, type Explanation, type Intake } from "@/lib/types";

function Flow() {
  const demo = useSearchParams().get("demo") === "1";
  const [step, setStep] = useState(0);
  const [remark, setRemark] = useState("");
  const [intake, setIntake] = useState<Intake>(EMPTY_INTAKE);
  const [answered, setAnswered] = useState<Set<keyof Intake>>(new Set());
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explainError, setExplainError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ocrAvailable, setOcrAvailable] = useState(false);
  const request = useRef(0);

  useEffect(() => {
    ocrStatus().then(setOcrAvailable);
  }, []);

  // Move focus to the new step's heading so keyboard and screen-reader users follow along.
  useEffect(() => {
    window.scrollTo({ top: 0 });
    document.getElementById("step-heading")?.focus();
  }, [step]);

  const diagnose = useCallback(
    async (text: string, answers: Intake) => {
      const id = ++request.current;
      setBusy(true);
      setError(null);
      try {
        const d = await classify(text, answers);
        if (id !== request.current) return;
        setDiagnosis(d);
        setExplanation(null);
        setExplainError(null);
        setStep(2);
        // The diagnosis shows at once; the explanation fills in when it arrives.
        explain(d.code, text, answers, demo)
          .then((e) => id === request.current && setExplanation(e))
          .catch(() => id === request.current && setExplainError("The explanation could not be loaded. Your fix and documents below still work."));
      } catch {
        if (id === request.current) setError("We could not reach the PF Sahay server. Check that it is running and try again.");
      } finally {
        if (id === request.current) setBusy(false);
      }
    },
    [demo],
  );

  function runDemo(i: number) {
    const c = DEMO_CASES[i];
    setRemark(c.remark);
    setIntake(c.intake);
    setAnswered(new Set(Object.keys(c.intake) as (keyof Intake)[]));
    diagnose(c.remark, c.intake);
  }

  function answer(key: keyof Intake, value: boolean) {
    const next = { ...intake, [key]: value };
    setIntake(next);
    setAnswered(new Set(answered).add(key));
    diagnose(remark, next);
  }

  function restart() {
    request.current++;
    setStep(0);
    setRemark("");
    setIntake(EMPTY_INTAKE);
    setAnswered(new Set());
    setDiagnosis(null);
    setExplanation(null);
  }

  return (
    <>
      <Stepper current={step} />
      {step === 0 && (
        <StepPaste
          remark={remark}
          setRemark={setRemark}
          ocrAvailable={ocrAvailable}
          demo={demo}
          onDemo={runDemo}
          onNext={() => setStep(1)}
        />
      )}
      {step === 1 && (
        <StepIntake
          intake={intake}
          setIntake={setIntake}
          answered={answered}
          setAnswered={setAnswered}
          busy={busy}
          error={error}
          onBack={() => setStep(0)}
          onNext={() => diagnose(remark, intake)}
        />
      )}
      {step === 2 && diagnosis && (
        <StepDiagnosis
          diagnosis={diagnosis}
          explanation={explanation}
          explainError={explainError}
          onAnswer={answer}
          busy={busy}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
        />
      )}
      {step === 3 && diagnosis && <StepFix diagnosis={diagnosis} onBack={() => setStep(2)} onNext={() => setStep(4)} />}
      {step === 4 && diagnosis && (
        <StepDocuments diagnosis={diagnosis} remark={remark} intake={intake} onBack={() => setStep(3)} onRestart={restart} />
      )}
      {error && step === 0 && (
        <p role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}
    </>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div role="note" className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-950">
        Drafts only — verify before you submit. Not legal advice. EPFO alone decides your claim.
      </div>
      <main className="mx-auto max-w-2xl px-4 pb-12 pt-6">
        <header className="mb-5">
          <h1 className="text-2xl font-bold text-teal-800">PF Sahay</h1>
          <p className="text-slate-700">Find out why your EPF claim was rejected and get the papers to fix it.</p>
          <p className="mt-2 text-sm text-slate-600">
            Nothing you type is stored. Identity numbers are removed before any AI processing.
          </p>
        </header>
        <Suspense fallback={null}>
          <Flow />
        </Suspense>
        <footer className="mt-8 text-xs leading-relaxed text-slate-500">
          PF Sahay is an independent helper, not an EPFO service. Never share your UAN password or OTP. Sources are
          EPFO circulars and public rules; check them before you rely on them.
        </footer>
      </main>
    </div>
  );
}
