import type { Code, Diagnosis, DocFields, DocName, Explanation, Intake, Office } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} failed (${res.status})`);
  return res.json() as Promise<T>;
}

export function classify(remark_text: string, intake: Intake) {
  return post<Diagnosis>("/classify", { remark_text, intake });
}

export function explain(code: Code, remark_text: string, intake: Intake, canned: boolean) {
  return post<Explanation>("/explain", { code, remark_text, intake, canned });
}

export function grievanceText(code: Code, remark_text: string, intake: Intake, fields: DocFields) {
  return post<{ grievance: string }>("/documents/text", { code, remark_text, intake, fields: cleanFields(fields) });
}

export async function ocrStatus(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/ocr/status`);
    return res.ok && (await res.json()).available === true;
  } catch {
    return false;
  }
}

export async function ocrImage(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/ocr`, { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? "Could not read the image");
  return (await res.json()).text as string;
}

export async function offices(): Promise<Office[]> {
  const res = await fetch(`${API_URL}/offices`);
  return res.ok ? res.json() : [];
}

/** Drop optional fields the user left empty so the backend prints placeholders. */
function cleanFields(fields: DocFields) {
  const { correction_field, ...rest } = fields;
  return correction_field ? { ...rest, correction_field } : rest;
}

/** Fetch generated PDFs (one doc) or a zip (several) and trigger a download. */
export async function downloadDocuments(
  code: Code,
  remark_text: string,
  intake: Intake,
  fields: DocFields,
  docs: DocName[],
): Promise<void> {
  const res = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, remark_text, intake, fields: cleanFields(fields), docs }),
  });
  if (!res.ok) throw new Error(`Could not create the document (${res.status})`);
  const blob = await res.blob();
  const name = docs.length === 1 ? `PFSahay_${code}_${docs[0]}.pdf` : `PFSahay_${code}_documents.zip`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
