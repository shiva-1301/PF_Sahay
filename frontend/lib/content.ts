import type { Code, DocName, Intake } from "./types";

/** Plain-language headline for each root cause. */
export const CODE_TITLES: Record<Code, string> = {
  R00: "We need a little more information",
  R01: "Your name, date of birth or gender does not match your Aadhaar",
  R02: "The date you left your last job is missing",
  R03: "The dates of your jobs overlap",
  R04: "There is a problem with your bank account details",
  R05: "Your Aadhaar is not properly linked to your UAN",
  R06: "Your PF history is split across more than one account",
  R07: "Another claim of yours is already being processed",
  R08: "You are not eligible yet, or the wrong form was used",
  R09: "A tax document (PAN or Form 121) is missing",
  R10: "There is a problem with your pension (EPS) record",
};

export const DOC_LABELS: Record<DocName, { title: string; hint: string }> = {
  employer_letter: { title: "Letter to your employer", hint: "Asks them to fix the record within 15 days" },
  jd_checklist: { title: "Joint Declaration checklist", hint: "Steps and documents for your category" },
  grievance: { title: "EPFiGMS grievance", hint: "Complaint text for epfigms.gov.in" },
  rti: { title: "RTI application", hint: "Formal request to EPFO for your claim details" },
};

export const CONFIDENCE_HELP: Record<string, string> = {
  Likely: "The rejection reason clearly points to this.",
  Probable: "This is the best match, but check it against your portal.",
  Unsure: "The reason is too general to be sure.",
};

type Option<T> = { label: string; value: T };

export const QUESTIONS: {
  key: keyof Intake;
  question: string;
  help?: string;
  options: Option<Intake[keyof Intake]>[];
}[] = [
  {
    key: "claim_form",
    question: "Which form did you use for the claim?",
    help: "You can see it under Track Claim Status on the EPFO portal.",
    options: [
      { label: "Form 19 (full PF withdrawal)", value: "19" },
      { label: "Form 31 (advance / part withdrawal)", value: "31" },
      { label: "Form 10C (pension withdrawal)", value: "10C" },
      { label: "Form 10D (monthly pension)", value: "10D" },
      { label: "Form 13 (transfer)", value: "13" },
      { label: "Not sure", value: null },
    ],
  },
  {
    key: "uan_issued",
    question: "When did you first get your UAN?",
    help: "UAN is your 12-digit PF account number. Do not type it here.",
    options: [
      { label: "Before October 2017", value: "before_oct_2017" },
      { label: "October 2017 or later", value: "after_oct_2017" },
      { label: "I don't have a UAN", value: "no_uan" },
      { label: "Not sure", value: null },
    ],
  },
  {
    key: "aadhaar_validated",
    question: "Does your UAN profile show your Aadhaar as verified?",
    options: [
      { label: "Yes", value: true },
      { label: "No", value: false },
      { label: "Not sure", value: null },
    ],
  },
  {
    key: "employer_reachable",
    question: "Can you still contact your last employer?",
    options: [
      { label: "Yes", value: true },
      { label: "No", value: false },
      { label: "Not sure", value: null },
    ],
  },
  {
    key: "exit_date_shown",
    question: "Does the portal show a Date of Exit for your last job?",
    help: "Look under Service History on the member portal.",
    options: [
      { label: "Yes", value: true },
      { label: "No", value: false },
      { label: "Not sure", value: null },
    ],
  },
];

/** Clarifying questions that map to an intake answer we can re-classify with. */
export const QUESTION_TO_INTAKE: Record<string, keyof Intake> = {
  "Does the portal show a Date of Exit against your last employer?": "exit_date_shown",
  "Does your UAN profile show your Aadhaar as verified?": "aadhaar_validated",
};

export const CORRECTION_FIELDS = [
  { value: "name", label: "Name" },
  { value: "date_of_birth", label: "Date of birth" },
  { value: "gender", label: "Gender" },
  { value: "father_mother_spouse", label: "Father / mother / spouse name" },
  { value: "marital_status", label: "Marital status" },
  { value: "service_dates", label: "Date of joining / exit" },
  { value: "aadhaar", label: "Aadhaar linked to UAN" },
];

export const DEMO_CASES: { label: string; remark: string; intake: Intake }[] = [
  {
    label: "Name mismatch (Category A)",
    remark: "Name mismatch: Aadhaar RAMESH KUMAR SINGH vs UAN RAMESH K SINGH",
    intake: { claim_form: "19", uan_issued: "after_oct_2017", aadhaar_validated: true, employer_reachable: true, exit_date_shown: true },
  },
  {
    label: "Date of exit missing",
    remark: "Date of exit not available",
    intake: { claim_form: "19", uan_issued: "before_oct_2017", aadhaar_validated: true, employer_reachable: false, exit_date_shown: false },
  },
  {
    label: "Multiple UANs",
    remark: "Multiple UAN found against the member",
    intake: { claim_form: "19", uan_issued: "before_oct_2017", aadhaar_validated: true, employer_reachable: true, exit_date_shown: true },
  },
];

export const STEPS = ["Rejection reason", "Quick questions", "Diagnosis", "Your fix", "Documents"];
