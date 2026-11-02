"use client";

import { useRef, useState } from "react";
import { ocrImage } from "@/lib/api";
import { DEMO_CASES } from "@/lib/content";
import { Button, Card, ErrorNote, NavRow, Spinner, StepHeading } from "./ui";

export function StepPaste({
  remark,
  setRemark,
  ocrAvailable,
  demo,
  onDemo,
  onNext,
}: {
  remark: string;
  setRemark: (v: string) => void;
  ocrAvailable: boolean;
  demo: boolean;
  onDemo: (i: number) => void;
  onNext: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromImage, setFromImage] = useState(false);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setReading(true);
    try {
      setRemark(await ocrImage(file));
      setFromImage(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the image");
    } finally {
      setReading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Card>
      <StepHeading
        id="step-heading"
        title="Why was your claim rejected?"
        lead="Copy the rejection reason from Track Claim Status on the EPFO portal and paste it here."
      />

      {demo && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="mb-2 text-sm font-medium text-amber-900">Demo mode: try a sample case</p>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            {DEMO_CASES.map((c, i) => (
              <Button key={c.label} variant="secondary" className="text-sm" onClick={() => onDemo(i)}>
                {c.label}
              </Button>
            ))}
          </div>
        </div>
      )}

      <label htmlFor="remark" className="mb-1 block font-medium text-slate-800">
        Rejection reason
      </label>
      <textarea
        id="remark"
        value={remark}
        onChange={(e) => setRemark(e.target.value)}
        rows={4}
        maxLength={2000}
        placeholder="Paste the rejection reason from the EPFO portal…"
        className="w-full rounded-lg border border-slate-300 p-3 text-base focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/30"
      />
      {fromImage && (
        <p className="mt-1 text-sm text-slate-600">
          Text read from your screenshot. Check it and correct any mistakes before you continue.
        </p>
      )}

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])}
        />
        <Button variant="secondary" disabled={!ocrAvailable || reading} onClick={() => fileRef.current?.click()}>
          {ocrAvailable ? "Upload a screenshot instead" : "OCR unavailable on this machine"}
        </Button>
        {reading && <Spinner label="Reading the screenshot…" />}
      </div>
      {error && <ErrorNote message={error} />}

      <NavRow>
        <span />
        <Button onClick={onNext} disabled={remark.trim().length < 3}>
          Next
        </Button>
      </NavRow>
    </Card>
  );
}
