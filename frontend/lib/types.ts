export type Code = "R00" | "R01" | "R02" | "R03" | "R04" | "R05" | "R06" | "R07" | "R08" | "R09" | "R10";
export type ClaimForm = "19" | "10C" | "10D" | "31" | "13";
export type UanIssued = "before_oct_2017" | "after_oct_2017" | "not_sure" | "no_uan";
export type DocName = "employer_letter" | "jd_checklist" | "grievance" | "rti";

export interface Intake {
  claim_form: ClaimForm | null;
  uan_issued: UanIssued | null;
  aadhaar_validated: boolean | null;
  employer_reachable: boolean | null;
  exit_date_shown: boolean | null;
}

export interface Diagnosis {
  code: Code;
  name: string;
  confidence: number;
  confidence_label: "Likely" | "Probable" | "Unsure";
  matched_phrases: string[];
  jd_category: "A" | "B" | "C" | null;
  jd_meaning: string | null;
  fix_path: string;
  fix_steps: string[];
  documents: string[];
  clarifying_question: string | null;
  remark_text: string;
  redactions: Record<string, number>;
  recommended_documents: DocName[];
}

export interface Citation {
  id: string;
  source_title: string;
  source_url: string;
  source_date: string;
}

export interface Explanation {
  paragraphs: { text: string; citations: Citation[] }[];
  model: string;
  dropped_sentences: number;
  fallback_reason: string | null;
}

export interface Office {
  office: string;
  zone_label: string;
}

export interface DocFields {
  member_name: string;
  employer_name: string;
  uan_last4: string;
  regional_office: string;
  member_address: string;
  employer_address: string;
  claim_id: string;
  claim_date: string;
  rejection_date: string;
  date_of_joining: string;
  date_of_exit: string;
  correction_field: string;
  correction_details: string;
  place: string;
}

export const EMPTY_INTAKE: Intake = {
  claim_form: null,
  uan_issued: null,
  aadhaar_validated: null,
  employer_reachable: null,
  exit_date_shown: null,
};

export const EMPTY_FIELDS: DocFields = {
  member_name: "",
  employer_name: "",
  uan_last4: "",
  regional_office: "",
  member_address: "",
  employer_address: "",
  claim_id: "",
  claim_date: "",
  rejection_date: "",
  date_of_joining: "",
  date_of_exit: "",
  correction_field: "",
  correction_details: "",
  place: "",
};
