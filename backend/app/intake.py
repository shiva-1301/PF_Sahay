"""The five intake questions and the Joint Declaration category they imply."""
from typing import Literal, Optional

from pydantic import BaseModel

ClaimForm = Literal["19", "10C", "10D", "31", "13"]
UanIssued = Literal["before_oct_2017", "after_oct_2017", "not_sure", "no_uan"]
JdCategory = Literal["A", "B", "C"]


class Intake(BaseModel):
    """Every field is optional: 'not sure' is a valid answer and is sent as null."""

    claim_form: Optional[ClaimForm] = None
    uan_issued: Optional[UanIssued] = None
    aadhaar_validated: Optional[bool] = None
    employer_reachable: Optional[bool] = None
    exit_date_shown: Optional[bool] = None


def jd_category(intake: Intake) -> Optional[JdCategory]:
    """Category per EPFO circular of 16 Jan 2025 (datasets/joint_declaration/jd_categories.json).

    A: UAN issued on/after 1 Oct 2017 and Aadhaar validated
    B: UAN issued before 1 Oct 2017 and Aadhaar validated
    C: Aadhaar not validated, or no UAN
    None: not enough answers to tell.
    """
    if intake.uan_issued == "no_uan" or intake.aadhaar_validated is False:
        return "C"
    if intake.aadhaar_validated:
        if intake.uan_issued == "after_oct_2017":
            return "A"
        if intake.uan_issued == "before_oct_2017":
            return "B"
    return None


JD_MEANING = {
    "A": "You can usually correct your details yourself online, with no documents.",
    "B": "You file the correction online and your employer approves it.",
    "C": "You file a paper Joint Declaration with documents, signed by your employer or an attesting officer.",
}
