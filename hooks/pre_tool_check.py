#!/usr/bin/env python3
"""
OCBC AI Platform — Claude Code PreToolUse PII Hook
===================================================
Called by Claude Code before EVERY tool use via the PreToolUse hook.
Receives tool name + input as JSON on stdin.
Scans for PII and blocks the tool call before anything leaves the machine.

Exit codes (Claude Code contract):
  0  → allow tool use to proceed
  2  → block tool use; Claude sees stderr as the reason (hard block)

Wired up in ~/.claude/settings.json:
  {
    "hooks": {
      "PreToolUse": [
        { "matcher": "", "hooks": [{"type": "command", "command": "python3 ~/claude-framework/hooks/pre_tool_check.py"}] }
      ]
    }
  }

The empty matcher "" means: run on ALL tool calls.
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Import the shared pattern registry from the pre-commit scanner.
# Falls back to an inline copy if the framework repo is not at ~/claude-framework.
# ---------------------------------------------------------------------------

def _load_patterns():
    """Load PATTERNS from pre_commit_pii.py if importable, else define inline."""
    try:
        framework = Path.home() / "claude-framework"
        sys.path.insert(0, str(framework))
        from hooks.pre_commit_pii import PATTERNS  # noqa: PLC0415
        return PATTERNS
    except ImportError:
        # Inline fallback — kept in sync with pre_commit_pii.py manually
        from dataclasses import dataclass  # noqa: PLC0415

        @dataclass
        class _P:
            name: str
            regex: str
            description: str
            example: str

        return [
            _P("SG_NRIC_FIN",      r"\b[STFG]\d{7}[A-Z]\b",       "Singapore NRIC/FIN",                    "SXXXXXXXA"),
            _P("SG_PASSPORT",      r"\bE\d{7}[A-Z]\b",             "Singapore passport",                    "EXXXXXXXA"),
            _P("PASSPORT_GENERIC", r"\b[A-Z]{1,2}\d{6,9}\b",       "Generic passport number",               "XXXXXXXXX"),
            _P("SG_VEHICLE_REG",   r"\b[A-Z]{2,3}\d{1,4}[A-Z]\b",  "Vehicle registration",                  "SKAXXXXB"),
            _P("OCBC_ACCOUNT",     r"\b\d{3}-\d{6}-\d{3}\b",       "OCBC account number",                   "XXX-XXXXXX-XXX"),
            _P("CREDIT_CARD",      r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[- ]?\d{4}[- ]?\d{4}[- ]?\d{3,4}\b",
                                                                     "Credit/debit card number",              "4XXX XXXX XXXX XXXX"),
            _P("IBAN",             r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})\b",
                                                                     "IBAN",                                  "SGXX XXXX XXXX XXXX"),
            _P("LOAN_REFERENCE",   r"\b\d{10,14}\b",                "Loan/facility reference (10-14 digits)","XXXXXXXXXXXXXX"),
            _P("SG_UEN",           r"\b(?:(?:19|20)\d{6}[A-Z]|\d{9}[A-Z])\b", "Singapore UEN",             "XXXXXXXXXA"),
            _P("MAS_LICENCE",      r"\b[A-Z]{2}\d{6}\b",            "MAS licence number",                    "MBXXXXXX"),
            _P("LEI",              r"\b[A-Z0-9]{18}\d{2}\b",        "Legal Entity Identifier",               "XXXXXXXXXXXXXXXXXXXXXXXXXX"),
            _P("OCBC_CUSTOMER_ID", r"\bCUST[_-]?\d{6,12}\b",        "Internal OCBC customer ID",             "CUST_XXXXXXXX"),
            _P("AWS_ACCESS_KEY",   r"(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}", "AWS access key",               "→ use Vault"),
            _P("HARDCODED_SECRET", r"""(?i)(?:password|passwd|secret|token|api_key|apikey|auth_key)\s*=\s*['"][^'"]{8,}['"]""",
                                                                     "Hardcoded credential",                  "→ use env var"),
            _P("PRIVATE_KEY",      r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                                                                     "Private key material",                  "→ use Vault"),
            _P("SG_PHONE",         r"\b(?:\+65[\s-]?)?[689]\d{3}[\s-]?\d{4}\b",
                                                                     "Singapore phone number",                "+65 9XXX XXXX"),
            _P("EMAIL",            r"\b[a-zA-Z0-9._%+\-]+@(?!ocbc\.com\b|example\.com\b|test\.com\b|placeholder\.com\b)[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
                                                                     "External email address",                "user@placeholder.com"),
        ]


PATTERNS = _load_patterns()
_COMPILED = [(p, re.compile(p.regex)) for p in PATTERNS]

# Max file size to scan inline (skip binary / very large files)
MAX_SCAN_BYTES = 500_000


# ---------------------------------------------------------------------------
# spaCy NER (optional)
# ---------------------------------------------------------------------------

def _load_nlp():
    try:
        import spacy  # noqa: PLC0415
        return spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return None

_NLP = _load_nlp()


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------

def scan_text(text: str, source_label: str) -> list[dict]:
    """Return list of violation dicts found in text."""
    findings = []

    for pattern, compiled in _COMPILED:
        for match in compiled.finditer(text):
            line_no = text[: match.start()].count("\n") + 1
            findings.append({
                "source": source_label,
                "line": line_no,
                "pattern": pattern.name,
                "description": pattern.description,
                "snippet": match.group(0)[:40],
                "example": pattern.example,
            })

    # Company name NER
    if _NLP is not None:
        doc = _NLP(text[:50_000])
        seen: set[str] = set()
        for ent in doc.ents:
            if ent.label_ == "ORG" and ent.text not in seen:
                seen.add(ent.text)
                line_no = text[: ent.start_char].count("\n") + 1
                findings.append({
                    "source": source_label,
                    "line": line_no,
                    "pattern": "COMPANY_NAME_NER",
                    "description": f'Organisation name: "{ent.text}"',
                    "snippet": ent.text[:40],
                    "example": "COMPANY_PLACEHOLDER",
                })

    return findings


# ---------------------------------------------------------------------------
# Tool-specific handlers
# ---------------------------------------------------------------------------

def handle_read(tool_input: dict) -> list[dict]:
    """Scan the file Claude is about to read."""
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return []

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return []

    # Skip binary files and oversized files
    try:
        stat = path.stat()
        if stat.st_size > MAX_SCAN_BYTES:
            # Still scan the first 500K bytes
            text = path.read_bytes()[:MAX_SCAN_BYTES].decode("utf-8", errors="ignore")
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    return scan_text(text, source_label=str(file_path))


def handle_write(tool_input: dict) -> list[dict]:
    """Scan content Claude is about to write to a file."""
    content = tool_input.get("content", "")
    file_path = tool_input.get("file_path", "<write>")
    if not content:
        return []
    return scan_text(content, source_label=f"write→{file_path}")


def handle_bash(tool_input: dict) -> list[dict]:
    """
    Scan a Bash command for PII patterns.
    This catches cases like: echo "S1234567A" or curl ... with embedded data.
    Does NOT execute the command — scans the command string only.
    """
    command = tool_input.get("command", "")
    if not command:
        return []
    return scan_text(command, source_label="bash_command")


def handle_edit(tool_input: dict) -> list[dict]:
    """Scan str_replace / insert content before edits are applied."""
    findings = []
    for key in ("new_string", "insert_line", "content"):
        text = tool_input.get(key, "")
        if text:
            findings.extend(scan_text(text, source_label=f"edit.{key}"))
    return findings


# Tool name → handler mapping
TOOL_HANDLERS = {
    "Read":              handle_read,
    "Write":             handle_write,
    "Bash":              handle_bash,
    "Edit":              handle_edit,
    "MultiEdit":         handle_edit,
    "str_replace_based_edit_tool": handle_edit,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    # Claude Code passes the hook payload as JSON on stdin
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        # Can't parse — allow through (don't break Claude Code on hook errors)
        return 0

    tool_name: str = payload.get("tool_name", "")
    tool_input: dict = payload.get("tool_input", {})

    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        # Unknown tool — allow through
        return 0

    findings = handler(tool_input)

    if not findings:
        return 0  # Clean — allow tool use

    # ── Hard block: exit 2 so Claude Code aborts the tool call ──────────
    print(f"\n🚫 OCBC PII SHIELD — Tool use blocked: [{tool_name}]\n", file=sys.stderr)
    print(f"   {len(findings)} violation(s) detected before the tool ran:\n", file=sys.stderr)

    for f in findings:
        print(f"   [{f['pattern']}]  {f['description']}", file=sys.stderr)
        print(f"   Found   : {f['snippet']}", file=sys.stderr)
        print(f"   Replace : {f['example']}\n", file=sys.stderr)

    print("   ─────────────────────────────────────────────────────", file=sys.stderr)
    print("   No data left this machine. Fix the values and retry.", file=sys.stderr)
    print("   Questions? → Slack #ai-platform-support\n", file=sys.stderr)

    return 2  # Claude Code hard-blocks the tool on exit code 2


if __name__ == "__main__":
    sys.exit(main())
