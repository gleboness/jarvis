"""LLM prompts for various bot tasks."""

# General chat system prompt
SYSTEM_PROMPT = "You are Jarvis, a helpful assistant. Be concise."

# Email drafting prompt
EMAIL_DRAFT_PROMPT_TEMPLATE = """\
Write a concise, polite email reply.

Rules:
- Output ONLY the email body (no subject line, no commentary).
- Do NOT ask questions.
- Do NOT provide multiple options.
- Do NOT sign as "Jarvis".
- Keep it short and natural.

Context:
Subject: {subj}
From: {frm}
Snippet: {snippet}

Email body:
"""

# Email triage prompt (in gmail/triage.py)
