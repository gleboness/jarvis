"""Email triage logic."""
import json
from typing import Dict, List, Optional


def gmail_fastpath_label(label_ids: List[str]) -> Optional[str]:
    """
    Fast-path classification based on Gmail labels.
    Returns 'spam' if message matches spam criteria, None otherwise.
    """
    # Treat promotions as spam automatically
    if "CATEGORY_PROMOTIONS" in label_ids:
        return "spam"
    # Optional: you may also want these as spam
    if "CATEGORY_SOCIAL" in label_ids or "CATEGORY_FORUMS" in label_ids:
        return "spam"
    return None


TRIAGE_PROMPT_TEMPLATE = """\
Classify this email for an inbox assistant.

Return ONLY valid JSON with keys:
- label: one of ["meaningful","spam","uncertain"]
- confidence: number from 0.0 to 1.0
- reason: short string

Heuristics:
- "spam" for obvious marketing, promos, low-value notifications, scams, affiliate, etc.
- "meaningful" for personal, work, bills, account security, direct requests, things requiring action.
- "uncertain" if not sure.

Email:
From: {frm}
Subject: {subj}
Snippet: {snippet}
"""


def triage_email(llm_call_fn, frm: str, subj: str, snippet: str) -> Dict:
    """
    Triage an email using LLM.
    
    Args:
        llm_call_fn: Function to call LLM (takes prompt string, returns response string)
        frm: Email sender
        subj: Email subject
        snippet: Email snippet
        
    Returns:
        Dict with keys: label, confidence, reason
    """
    prompt = TRIAGE_PROMPT_TEMPLATE.format(frm=frm, subj=subj, snippet=snippet)
    raw = llm_call_fn(prompt).strip()
    try:
        data = json.loads(raw)
        if data.get("label") not in ("meaningful", "spam", "uncertain"):
            raise ValueError("bad label")
        return data
    except Exception:
        # fallback: if parsing fails, treat as uncertain (safe)
        return {"label": "uncertain", "confidence": 0.0, "reason": "failed_to_parse"}
