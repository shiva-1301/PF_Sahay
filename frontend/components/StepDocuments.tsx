"use client";

import { useEffect, useMemo, useState } from "react";
import { downloadDocuments, grievanceText, offices as fetchOffices } from "@/lib/api";
import { CORRECTION_FIELDS, DOC_LABELS } from "@/lib/content";
import { EMPTY_FIELDS, type Diagnosis, type DocFields, type DocName, type Intake, type Office } from "@/lib/types";
import { Button, Card, ErrorNote, NavRow, Spinner, StepHeading } from "./ui";

const INPUT =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-base focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/30";

function Field({
  id,
  label,
  hint,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="block font-medium text-slate-800">
        {label}
      </label>
      {hint && <p className="text-sm text-slate-600">{hint}</p>}
      <div className="mt-1">{children}</div>
    </div>
  );
}

export function StepDocuments({
  diagnosis,
  remark,
  intake,
  onBack,
  onRestart,
}: {
  diagnosis: Diagnosis;
  remark: string;
  intake: Intake;
  onBack: () => void;
  onRestart: () => void;
}) {
  const [fields, setFields] = useState<DocFields>(EMPTY_FIELDS);
  const [officeList, setOfficeList] = useState<Office[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchOffices().then(setOfficeList).catch(() => setOfficeList([]));
  }, []);

  const zones = useMemo(() => {
    const byZone = new Map<string, string[]>();
    for (const o of officeList) byZone.set(o.zone_label, [...(byZone.get(o.zone_label) ?? []), o.office]);
    return Array.from(byZone.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [officeList]);

  const set = (k: keyof DocFields) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFields({ ...fields, [k]: e.target.value });
  const uanValid = fields.uan_last4 === "" || /^\d{4}$/.test(fields.uan_last4);
  const docs = diagnosis.recommended_documents;
  const needsCorrection = docs.includes("jd_checklist") || ["R01", "R03", "R05"].includes(diagnosis.code);

  async function download(which: DocName[], key: string) {
    setError(null);
    setBusy(key);
    try {
      await downloadDocuments(diagnosis.code, remark, intake, fields, which);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the document");
    } finally {
      setBusy(null);
    }
  }

  async function copyGrievance() {
    setError(null);
    try {
      const { grievance } = await grievanceText(diagnosis.code, remark, intake, fields);
      await navigator.clipboard.writeText(grievance);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setError("Could not copy the grievance text. Download the PDF instead.");
    }
  }

  return (
    <Card>
      <StepHeading
        id="step-heading"
        title="Your documents"
        lead="Add a few details so the documents are ready to send. Anything you leave blank prints as a [blank] to fill by hand."
      />

      <div className="space-y-4">
        <Field id="member_name" label="Your full name">
          <input id="member_name" className={INPUT} value={fields.member_name} onChange={set("member_name")} maxLength={80} autoComplete="name" />
        </Field>
        <Field id="employer_name" label="Employer (company) name">
          <input id="employer_name" className={INPUT} value={fields.employer_name} onChange={set("employer_name")} maxLength={120} autoComplete="organization" />
        </Field>
        <Field id="uan_last4" label="Last 4 digits of your UAN" hint="Only the last 4 digits. The documents show it as XXXXXXXX1234.">
          <input
            id="uan_last4"
            className={`${INPUT} max-w-32 tracking-widest`}
            value={fields.uan_last4}
            onChange={(e) => setFields({ ...fields, uan_last4: e.target.value.replace(/\D/g, "").slice(0, 4) })}
            inputMode="numeric"
            autoComplete="off"
            aria-invalid={!uanValid}
          />
        </Field>
        <Field id="regional_office" label="EPFO Regional Office" hint="Used to address the RTI application.">
          <select id="regional_office" className={INPUT} value={fields.regional_office} onChange={set("regional_office")}>
            <option value="">Choose your office…</option>
            {zones.map(([zone, names]) => (
              <optgroup key={zone} label={zone}>
                {names.map((n) => (
                  <option key={`${zone}-${n}`} value={n}>
                    {n}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </Field>

        <details className="rounded-lg border border-slate-200 p-3">
          <summary className="cursor-pointer font-medium text-teal-800">More details (optional)</summary>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {needsCorrection && (
              <>
                <Field id="correction_field" label="Detail to correct">
                  <select id="correction_field" className={INPUT} value={fields.correction_field} onChange={set("correction_field")}>
                    <option value="">Use the usual one</option>
                    {CORRECTION_FIELDS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field id="correction_details" label="Correct value" hint="e.g. Name as on Aadhaar">
                  <input id="correction_details" className={INPUT} value={fields.correction_details} onChange={set("correction_details")} maxLength={150} />
                </Field>
              </>
            )}
            {(
              [
                ["claim_id", "Claim ID", 30],
                ["claim_date", "Date you filed the claim", 20],
                ["rejection_date", "Date it was rejected", 20],
                ["date_of_joining", "Date you joined", 20],
                ["date_of_exit", "Your last working day", 20],
                ["place", "Your town or city", 40],
                ["member_address", "Your postal address", 200],
                ["employer_address", "Employer address", 200],
              ] as [keyof DocFields, string, number][]
            ).map(([k, label, max]) => (
              <Field key={k} id={k} label={label}>
                <input id={k} className={INPUT} value={fields[k]} onChange={set(k)} maxLength={max} />
              </Field>
            ))}
          </div>
        </details>
      </div>

      <h3 className="mb-2 mt-6 text-lg font-semibold text-slate-900">Download</h3>
      <ul className="space-y-2">
        {docs.map((d) => (
          <li key={d} className="flex flex-col gap-2 rounded-lg border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium text-slate-900">{DOC_LABELS[d].title}</p>
              <p className="text-sm text-slate-600">{DOC_LABELS[d].hint}</p>
            </div>
            <div className="flex gap-2">
              {d === "grievance" && (
                <Button variant="ghost" onClick={copyGrievance} disabled={!uanValid}>
                  {copied ? "Copied" : "Copy text"}
                </Button>
              )}
              <Button variant="secondary" onClick={() => download([d], d)} disabled={!uanValid || busy !== null}>
                {busy === d ? <Spinner label="Making PDF…" /> : "PDF"}
              </Button>
            </div>
          </li>
        ))}
      </ul>
      {docs.length > 1 && (
        <Button className="mt-3 w-full" onClick={() => download(docs, "all")} disabled={!uanValid || busy !== null}>
          {busy === "all" ? <Spinner label="Making documents…" /> : "Download all (.zip)"}
        </Button>
      )}
      {!uanValid && <ErrorNote message="Enter exactly 4 digits for the UAN, or leave it blank." />}
      {error && <ErrorNote message={error} />}
      <p className="mt-3 text-sm text-slate-600">
        These are drafts. Read them, fill any [blanks], sign, and send them yourself.
      </p>

      <NavRow>
        <Button variant="secondary" onClick={onBack}>
          Back
        </Button>
        <Button variant="ghost" onClick={onRestart}>
          Start a new check
        </Button>
      </NavRow>
    </Card>
  );
}
