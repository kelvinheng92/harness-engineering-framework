#!/usr/bin/env python3
"""
OCBC AI Platform — Pre-commit PII & Secrets Scanner
====================================================
Scans staged files for PII patterns before allowing a git commit.

Severity policy: ALL patterns are hard block (zero tolerance).
Any detection causes exit code 1 and aborts the commit.

Optionally uses spaCy (en_core_web_sm) for company name NER.
Degrades gracefully to regex-only if spaCy is not installed.

Install spaCy:
  pip install spacy --index-url https://pypi.internal/simple
  python -m spacy download en_core_web_sm

Add to .pre-commit-config.yaml or run directly:
  python hooks/pre_commit_pii.py
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Pattern definitions — ALL severity: block (zero-tolerance policy)
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    name: str
    regex: str
    description: str
    example: str   # shown in error output to guide the developer


PATTERNS: list[Pattern] = [

    # ── Personal identifiers ──────────────────────────────────────────────

    Pattern(
        name="SG_NRIC_FIN",
        regex=r"\b[STFG]\d{7}[A-Z]\b",
        description="Singapore NRIC or FIN number",
        example="SXXXXXXXA",
    ),
    Pattern(
        name="SG_PASSPORT",
        regex=r"\bE\d{7}[A-Z]\b",
        description="Singapore passport number",
        example="EXXXXXXXA",
    ),
    Pattern(
        name="PASSPORT_GENERIC",
        regex=r"\b[A-Z]{1,2}\d{6,9}\b",
        description="Generic passport number (non-SG format)",
        example="AB1234567 → use XXXXXXXXX",
    ),

    # ── Financial account identifiers ─────────────────────────────────────

    Pattern(
        name="OCBC_ACCOUNT",
        regex=r"\b\d{3}-\d{6}-\d{3}\b",
        description="OCBC bank account number (XXX-XXXXXX-XXX format)",
        example="XXX-XXXXXX-XXX",
    ),
    Pattern(
        name="CREDIT_CARD",
        regex=r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[- ]?\d{4}[- ]?\d{4}[- ]?\d{3,4}\b",
        description="Credit or debit card number",
        example="4XXX XXXX XXXX XXXX",
    ),
    Pattern(
        name="IBAN",
        regex=r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})\b",
        description="IBAN (International Bank Account Number)",
        example="SGXX XXXX XXXX XXXX XXXX X",
    ),
    Pattern(
        name="LOAN_REFERENCE",
        # Long-number heuristic: 10–14 digit standalone number.
        # Catches most internal loan/facility reference formats.
        regex=r"\b\d{10,14}\b",
        description="Possible loan or facility reference number (10–14 digits)",
        example="XXXXXXXXXXXXXX",
    ),

    # ── Corporate & internal identifiers ──────────────────────────────────

    Pattern(
        name="SG_UEN",
        regex=r"\b(?:(?:19|20)\d{6}[A-Z]|\d{9}[A-Z])\b",
        description="Singapore corporate UEN",
        example="XXXXXXXXXA",
    ),
    Pattern(
        name="MAS_LICENCE",
        regex=r"\b[A-Z]{2}\d{6}\b",
        description="MAS licence number",
        example="MBXXXXXX",
    ),
    Pattern(
        name="LEI",
        # ISO 17442: 18 uppercase alphanumeric + 2 numeric check digits
        regex=r"\b[A-Z0-9]{18}\d{2}\b",
        description="Legal Entity Identifier (LEI, 20 characters)",
        example="XXXXXXXXXXXXXXXXXXXXXXXXXX",
    ),
    Pattern(
        name="OCBC_CUSTOMER_ID",
        regex=r"\bCUST[_-]?\d{6,12}\b",
        description="Internal OCBC customer ID",
        example="CUST_XXXXXXXX",
    ),

    # ── Secrets & credentials ─────────────────────────────────────────────

    Pattern(
        name="HARDCODED_SECRET",
        regex=r"""(?i)(?:password|passwd|secret|token|api_key|apikey|auth_key)\s*=\s*['"][^'"]{8,}['"]""",
        description="Hardcoded credential, secret, or API key",
        example='password = os.environ["MY_PASSWORD"]',
    ),
    Pattern(
        name="PRIVATE_KEY",
        regex=r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        description="Private key material",
        example="Store in Vault — never commit key files",
    ),

    # ── Contact & contextual PII ──────────────────────────────────────────

    Pattern(
        name="SG_PHONE",
        regex=r"\b(?:\+65[\s-]?)?[689]\d{3}[\s-]?\d{4}\b",
        description="Singapore phone number",
        example="+65 9XXX XXXX",
    ),
    Pattern(
        name="EMAIL",
        # Allow @ocbc.com (internal staff), @example.com, @test.com, @placeholder.com
        regex=r"\b[a-zA-Z0-9._%+\-]+@(?!ocbc\.com\b|example\.com\b|test\.com\b|placeholder\.com\b|anthropic\.com\b)[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
        description="External email address (possible customer PII)",
        example="customer@placeholder.com",
    ),
]


# ---------------------------------------------------------------------------
# spaCy NER — company name detection (optional, degrades gracefully)
# ---------------------------------------------------------------------------

def load_spacy_model():
    """Load spaCy en_core_web_sm. Returns None if not installed."""
    try:
        import spacy  # noqa: PLC0415
        return spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return None


def load_corporate_watchlist() -> set[str]:
    """
    Load hooks/corporate_watchlist.txt — one known client name per line.
    Team maintains this file; it boosts NER recall for known entities.
    Lines starting with # are comments.
    """
    watchlist_path = Path(__file__).parent / "corporate_watchlist.txt"
    if not watchlist_path.exists():
        return set()
    names = set()
    for line in watchlist_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            names.add(stripped.lower())
    return names


def detect_company_names(text: str, nlp, watchlist: set[str]) -> list[dict]:
    """Return NER + watchlist findings for organisation names."""
    findings = []

    if nlp is not None:
        doc = nlp(text[:100_000])   # cap to bound latency
        seen: set[str] = set()
        for ent in doc.ents:
            if ent.label_ == "ORG" and ent.text not in seen:
                seen.add(ent.text)
                line_no = text[: ent.start_char].count("\n") + 1
                findings.append({
                    "pattern": "COMPANY_NAME_NER",
                    "description": f'Organisation detected: "{ent.text}"',
                    "line": line_no,
                    "snippet": ent.text[:60],
                    "example": "CompanyName Pte Ltd → use COMPANY_NAME_PLACEHOLDER",
                })

    if watchlist:
        text_lower = text.lower()
        for name in watchlist:
            if name in text_lower:
                idx = text_lower.index(name)
                line_no = text[:idx].count("\n") + 1
                findings.append({
                    "pattern": "COMPANY_NAME_WATCHLIST",
                    "description": f'Watchlist match: "{name}"',
                    "line": line_no,
                    "snippet": name[:60],
                    "example": "COMPANY_NAME_PLACEHOLDER",
                })

    return findings


# ---------------------------------------------------------------------------
# File filtering
# ---------------------------------------------------------------------------

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".whl", ".egg",
    ".parquet", ".orc", ".avro", ".lock",
}

SKIP_DIRS = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", "dist", "build",
}

SCAN_EXTENSIONS = {
    ".py", ".sql", ".yaml", ".yml", ".json", ".toml",
    ".ini", ".cfg", ".conf", ".sh", ".bash",
    ".ipynb", ".md", ".txt", ".csv", ".env",
}

ALWAYS_SCAN_NAMES = {".env", ".env.local", ".env.production", "Makefile", "Dockerfile"}


def get_staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    return [Path(p) for p in result.stdout.strip().splitlines() if p]


def should_scan(path: Path) -> bool:
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return False
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name in ALWAYS_SCAN_NAMES:
        return True
    return path.suffix.lower() in SCAN_EXTENSIONS


def read_file_text(path: Path) -> str:
    """Read file text; for .ipynb extracts cell sources only (no outputs)."""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix == ".ipynb":
        try:
            nb = json.loads(raw)
            sources = []
            for cell in nb.get("cells", []):
                sources.extend(cell.get("source", []))
            return "\n".join(sources)
        except json.JSONDecodeError:
            return raw
    return raw


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------

def scan_regex(path: Path, text: str) -> list[dict]:
    findings = []
    for pat in PATTERNS:
        for match in re.compile(pat.regex).finditer(text):
            line_no = text[: match.start()].count("\n") + 1
            findings.append({
                "file": str(path),
                "line": line_no,
                "pattern": pat.name,
                "description": pat.description,
                "snippet": match.group(0)[:60],
                "example": pat.example,
            })
    return findings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    staged = get_staged_files()
    if not staged:
        print("OCBC PII Scanner: no staged files to check.")
        return 0

    nlp = load_spacy_model()
    watchlist = load_corporate_watchlist()

    if nlp is None:
        print(
            "ℹ  spaCy not found — company name NER disabled (regex-only mode).\n"
            "   Install: pip install spacy && python -m spacy download en_core_web_sm\n"
        )

    all_findings: list[dict] = []
    scanned = 0

    for path in staged:
        if not should_scan(path):
            continue
        scanned += 1
        try:
            text = read_file_text(path)
        except OSError:
            continue
        all_findings.extend(scan_regex(path, text))
        all_findings.extend(
            {**f, "file": str(path)}
            for f in detect_company_names(text, nlp, watchlist)
        )

    print(f"\n{'='*62}")
    print(f"  OCBC PII Scanner  |  {scanned} file(s) scanned")
    print(f"{'='*62}\n")

    if not all_findings:
        print("✅  Clean — no PII or secrets detected. Commit allowed.\n")
        return 0

    # Zero-tolerance: all findings → hard block
    print(f"🚫  COMMIT BLOCKED — {len(all_findings)} violation(s)\n")

    by_file: dict[str, list[dict]] = {}
    for f in all_findings:
        by_file.setdefault(f["file"], []).append(f)

    for filepath, findings in by_file.items():
        print(f"  📄  {filepath}")
        for f in findings:
            print(f"      Line {f['line']:>4}  [{f['pattern']}]  {f['description']}")
            print(f"             Found : {f['snippet']}")
            print(f"             Use   : {f['example']}\n")

    print("─" * 62)
    print("How to fix and retry:")
    print("  1. Replace real values with synthetic placeholders")
    print("     e.g.  nric='SXXXXXXXA'   account='XXX-XXXXXX-XXX'")
    print("  2. Move secrets/keys to Vault or environment variables")
    print("  3. For dev data, use  hdfs:///internal/synth-data/")
    print("  4. Re-stage and commit:  git add <file> && git commit")
    print("\n  Questions? → Slack #ai-platform-support\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
