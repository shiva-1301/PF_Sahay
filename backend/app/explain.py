"""Plain-English explanation of a diagnosis: one Claude call, grounded in corpus chunks.

The model may cite only the chunk IDs it was given. A validator drops every sentence
that cites anything else; if more than 30 % of sentences are dropped, or the call
fails, the canned explanation for the code is returned instead.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Optional

import anthropic

from app import config
from app.classifier import rules
from app.intake import JD_MEANING, Intake, jd_category
from app.retrieval import retrieve

log = logging.getLogger("pfsahay.explain")

PROMPTS_DIR = config.BACKEND_DIR / "prompts"
MAX_TOKENS = 700
MAX_DROP_SHARE = 0.30
CITATION = re.compile(r"\[(C\d+)\]")
LEADING_CITATIONS = re.compile(r"^(?:\[C\d+\][\s.,;]*)+")
# Sentence ends at . ! ? followed by space, but not after a list number like "1."
SENTENCE_END = re.compile(r"(?<=[.!?])(?<!\b\d\.)(?<!\b\d\d\.)\s+")


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return (PROMPTS_DIR / "explain_system.md").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=16)
def canned_text(code: str) -> str:
    return (PROMPTS_DIR / "canned" / f"{code}.md").read_text(encoding="utf-8").strip()


def get_client() -> Optional[anthropic.Anthropic]:
    """Anthropic client, or None when no key is configured (canned mode)."""
    if not config.ANTHROPIC_KEY:
        return None
    return anthropic.Anthropic(api_key=config.ANTHROPIC_KEY, timeout=20.0, max_retries=1)


def model_params(model: str) -> dict:
    """Per-model request settings.

    Sonnet 5.5 thinks by default and thinking counts toward max_tokens; this is a short
    explanation, so extended thinking is turned off ("between_tools" is Sonnet 5.5's
    lowest setting and is rejected by other models).
    """
    if model.startswith("claude-sonnet-5-5"):
        return {"thinking": {"type": "between_tools"}, "output_config": {"effort": "low"}}
    return {}


def _citation(chunk: dict) -> dict:
    return {k: chunk[k] for k in ("id", "source_title", "source_url", "source_date")}


def build_user_message(code: str, remark: str, intake: Intake, chunks: list[dict]) -> str:
    spec = rules().codes[code]
    fix = spec.fix_path
    cat = jd_category(intake)
    if isinstance(fix, dict):  # R01: fix depends on the JD category
        fix = fix.get(cat) if cat else " ".join(f"Category {k}: {v}" for k, v in fix.items())
    lines = [
        f"Rejection remark: {remark}",
        f"Diagnosis: {code} - {spec.name}",
        f"Usual fix: {fix}",
    ]
    if cat:
        lines.append(f"Joint Declaration category: {cat} ({JD_MEANING[cat]})")
    lines.append("\nSource extracts:")
    for c in chunks:
        date = f", {c['source_date']}" if c.get("source_date") else ""
        lines.append(f"\n[{c['id']}] {c['source_title']}{date}\n{c['text']}")
    return "\n".join(lines)


def _split_sentences(line: str) -> list[str]:
    parts = [p for p in SENTENCE_END.split(line.strip()) if p]
    merged: list[str] = []
    for p in parts:
        # citations written after the full stop ("... rule. [C12] Next ...") belong to
        # the sentence before
        lead = LEADING_CITATIONS.match(p)
        if merged and lead:
            merged[-1] = f"{merged[-1]} {lead.group(0).strip()}"
            p = p[lead.end():].strip()
        if p:
            merged.append(p)
    return merged


def validate(text: str, allowed: dict[str, dict]) -> tuple[list[dict], int, int]:
    """Drop sentences citing IDs outside `allowed`.

    Returns (paragraphs, dropped_sentences, total_sentences).
    """
    paragraphs, dropped, total = [], 0, 0
    for block in re.split(r"\n\s*\n", text.strip()):
        kept_lines, cited = [], []
        for line in block.splitlines():
            kept = []
            for sent in _split_sentences(line):
                total += 1
                ids = CITATION.findall(sent)
                if any(i not in allowed for i in ids):
                    dropped += 1
                    continue
                kept.append(sent)
                cited += [i for i in ids if i not in cited]
            if kept:
                kept_lines.append(" ".join(kept))
        if kept_lines:
            paragraphs.append({"text": "\n".join(kept_lines),
                               "citations": [_citation(allowed[i]) for i in cited]})
    return paragraphs, dropped, total


def canned(code: str, chunks: list[dict], reason: str) -> dict:
    paragraphs = [{"text": p.strip(), "citations": []}
                  for p in re.split(r"\n\s*\n", canned_text(code)) if p.strip()]
    if paragraphs and chunks:
        # Canned text is not tied to chunk IDs (they change on rebuild); point the
        # reader to the top retrieved sources on the first paragraph instead.
        paragraphs[0]["citations"] = [_citation(c) for c in chunks[:3]]
    return {"paragraphs": paragraphs, "model": "canned", "dropped_sentences": 0, "fallback_reason": reason}


def explain(code: str, remark: str, intake: Optional[Intake] = None,
            client: Optional[anthropic.Anthropic] = None, force_canned: bool = False) -> dict:
    """`remark` must already be PII-stripped."""
    intake = intake or Intake()
    fix = rules().codes[code].fix_path
    fix_text = fix if isinstance(fix, str) else " ".join(fix.values())
    chunks = retrieve(code, remark, fix_text, k=5)

    if force_canned:
        return canned(code, chunks, "demo")
    if client is None:
        return canned(code, chunks, "no_api_key")

    try:
        resp = client.messages.create(
            model=config.EXPLAIN_MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt(),
            messages=[{"role": "user", "content": build_user_message(code, remark, intake, chunks)}],
            **model_params(config.EXPLAIN_MODEL),
        )
    except anthropic.APIConnectionError:
        log.warning("explain fallback=connection_error code=%s", code)
        return canned(code, chunks, "connection_error")
    except anthropic.RateLimitError:
        log.warning("explain fallback=rate_limited code=%s", code)
        return canned(code, chunks, "rate_limited")
    except anthropic.APIStatusError as e:
        log.warning("explain fallback=api_error status=%s code=%s", e.status_code, code)
        return canned(code, chunks, "api_error")

    if resp.stop_reason == "refusal":
        return canned(code, chunks, "refusal")
    if resp.stop_reason == "max_tokens":  # the "Next steps" block would be cut off
        return canned(code, chunks, "truncated")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        return canned(code, chunks, "empty_response")

    allowed = {c["id"]: c for c in chunks}
    paragraphs, dropped, total = validate(text, allowed)
    if total == 0 or dropped / total > MAX_DROP_SHARE:
        log.info("explain fallback=too_many_dropped code=%s dropped=%d total=%d", code, dropped, total)
        return {**canned(code, chunks, "citations_invalid"), "dropped_sentences": dropped}
    log.info("explain code=%s model=%s dropped=%d total=%d", code, resp.model, dropped, total)
    return {"paragraphs": paragraphs, "model": resp.model, "dropped_sentences": dropped, "fallback_reason": None}
