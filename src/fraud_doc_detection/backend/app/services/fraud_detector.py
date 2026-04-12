"""
Core fraud detection algorithms for document analysis.
Detects forgery indicators in PDF documents using multiple analysis techniques,
based on resistant.ai methodology and bank statement fraud research.
"""
import fitz  # PyMuPDF
import re
from collections import Counter
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dateutil import parser as date_parser

from app.models.schemas import (
    FraudIndicator, MetadataEntry, DocumentMetadata,
    IndicatorSeverity, AnalysisResult
)


# ─── Constants ───────────────────────────────────────────────────────────────

KNOWN_LEGITIMATE_TOOLS = {
    "microsoft word", "microsoft excel", "adobe acrobat",
    "libreoffice", "google docs", "wps office", "pages",
    "nitro pdf", "foxit phantompdf", "pdfelement",
    "openoffice", "quartz pdfcontext", "mac os x quartz",
    "cairo", "ghostscript", "crystal reports",
}

SUSPICIOUS_CREATOR_PATTERNS = [
    r"pdf\s*edit", r"pdf\s*forge", r"i\s*love\s*pdf", r"smallpdf",
    r"sejda", r"online\s*pdf", r"free\s*pdf", r"pdf\s*converter",
    r"pdf\s*online", r"pdf24", r"unknown", r"photoshop",
    r"gimp", r"paint", r"canva", r"sodapdf",
]

# Legitimate bank statement generators rarely use these
IMAGE_EDITING_TOOLS = ["photoshop", "gimp", "paint.net", "affinity photo", "pixelmator"]

# Generic/suspicious deposit descriptions that lack specific employer names
GENERIC_DEPOSIT_PATTERNS = [
    r'\bdeposit\b', r'\bcredit\b', r'\btransfer in\b', r'\bfunds received\b',
    r'\bmobile deposit\b', r'\batm deposit\b',
]

# Normal recurring expense keywords expected in genuine bank statements
EXPECTED_EXPENSE_KEYWORDS = [
    "electric", "gas", "water", "utility", "utilities",
    "grocery", "groceries", "supermarket", "walmart", "target", "kroger",
    "rent", "mortgage", "insurance",
    "internet", "phone", "mobile", "cellular",
    "netflix", "spotify", "amazon", "subscription",
    "fuel", "gas station", "shell", "chevron", "bp",
    "restaurant", "dining", "food",
]

# Weekend day numbers (Mon=0 … Sun=6)
WEEKEND_DAYS = {5, 6}  # Saturday, Sunday

# US bank holidays (month, day) — approximate static list
BANK_HOLIDAYS = {
    (1, 1), (7, 4), (12, 25), (11, 11),  # New Year, Independence, Christmas, Veterans
}


class DocumentFraudDetector:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.indicators: List[FraudIndicator] = []
        self.metadata_entries: List[MetadataEntry] = []
        self._indicator_counter = 0
        self._full_text: Optional[str] = None

    def _new_indicator_id(self) -> str:
        self._indicator_counter += 1
        return f"IND-{self._indicator_counter:03d}"

    def _add_indicator(
        self,
        title: str,
        description: str,
        severity: IndicatorSeverity,
        details: Optional[str] = None,
        confidence: float = 85.0,
    ):
        self.indicators.append(FraudIndicator(
            id=self._new_indicator_id(),
            title=title,
            description=description,
            severity=severity,
            details=details,
            confidence=confidence,
        ))

    def _get_full_text(self) -> str:
        if self._full_text is None:
            self._full_text = "".join(page.get_text() for page in self.doc)
        return self._full_text

    @property
    def _is_image_only(self) -> bool:
        """True when the PDF has no extractable text layer (scanned/image-based)."""
        return len(self._get_full_text().strip()) < 20

    # ─── 1. Metadata Analysis ────────────────────────────────────────────────

    def analyze_metadata(self) -> DocumentMetadata:
        """Extract and analyze PDF metadata for inconsistencies."""
        meta = self.doc.metadata
        creation_date = meta.get("creationDate", "") or ""
        mod_date = meta.get("modDate", "") or ""
        creator = (meta.get("creator", "") or "").strip()
        producer = (meta.get("producer", "") or "").strip()
        author = (meta.get("author", "") or "").strip()
        title = (meta.get("title", "") or "").strip()

        # Date ordering check
        if creation_date and mod_date:
            try:
                cd = self._parse_pdf_date(creation_date)
                md = self._parse_pdf_date(mod_date)
                if cd and md and md < cd:
                    self._add_indicator(
                        title="Modification Date Before Creation Date",
                        description="The modification date is earlier than the creation date — an impossible state that strongly indicates date tampering.",
                        severity=IndicatorSeverity.HIGH,
                        details=f"Created: {creation_date}  |  Modified: {mod_date}",
                        confidence=97.0,
                    )
                elif cd and md and (md - cd).days > 3650:
                    self._add_indicator(
                        title="Unusually Large Date Gap",
                        description="The gap between creation and modification dates spans over 10 years, which is atypical for financial documents.",
                        severity=IndicatorSeverity.MEDIUM,
                        details=f"Gap: {(md - cd).days} days",
                        confidence=70.0,
                    )
            except Exception:
                pass

        # Creation date vs statement period mismatch
        self._check_creation_date_vs_statement_period(creation_date)

        # Creator tool checks
        if creator:
            creator_lower = creator.lower()
            is_image_editor = any(t in creator_lower for t in IMAGE_EDITING_TOOLS)
            is_suspicious = any(re.search(p, creator_lower) for p in SUSPICIOUS_CREATOR_PATTERNS)
            is_known = any(t in creator_lower for t in KNOWN_LEGITIMATE_TOOLS)

            if is_image_editor:
                self._add_indicator(
                    title="Image Editing Software Used as PDF Creator",
                    description=f"The PDF was created or processed using image editing software ('{creator}'). Genuine bank statements are generated by banking systems, not image editors — a strong indicator of forgery.",
                    severity=IndicatorSeverity.HIGH,
                    details=f"Creator: {creator}",
                    confidence=93.0,
                )
            elif is_suspicious:
                self._add_indicator(
                    title="Suspicious PDF Creator Tool",
                    description=f"Document was created/edited using a tool associated with document manipulation: '{creator}'.",
                    severity=IndicatorSeverity.HIGH,
                    details=f"Creator: {creator}",
                    confidence=88.0,
                )
            elif not is_known:
                self._add_indicator(
                    title="Unknown PDF Creator Tool",
                    description=f"The creator tool '{creator}' is not a recognized banking or document system. Legitimate statements use well-known generators.",
                    severity=IndicatorSeverity.MEDIUM,
                    details=f"Creator: {creator}",
                    confidence=62.0,
                )
        else:
            self._add_indicator(
                title="Missing Creator Metadata",
                description="No creator application recorded — indicates deliberate metadata stripping, common in forged documents.",
                severity=IndicatorSeverity.MEDIUM,
                confidence=65.0,
            )

        self.metadata_entries.extend([
            MetadataEntry(field="Document Title", original_text=title or None,
                          new_text="Annotation" if not title else None,
                          status="annotation" if not title else "match"),
            MetadataEntry(field="Author / Issuer", original_text=author or None,
                          new_text="Annotation" if not author else None,
                          status="annotation" if not author else "match"),
            MetadataEntry(field="Creator Application", original_text=creator or None,
                          new_text="Annotation" if not creator else None,
                          status="annotation" if not creator else "match"),
            MetadataEntry(field="PDF Producer", original_text=producer or None,
                          new_text="Annotation" if not producer else None,
                          status="annotation" if not producer else "match"),
            MetadataEntry(field="Creation Date", original_text=creation_date or None,
                          new_text=None, status="match" if creation_date else "missing"),
            MetadataEntry(field="Modification Date", original_text=mod_date or None,
                          new_text=None, status="match" if mod_date else "missing"),
        ])

        return DocumentMetadata(
            title=title or None,
            author=author or None,
            creator=creator or None,
            producer=producer or None,
            creation_date=creation_date or None,
            modification_date=mod_date or None,
            page_count=len(self.doc),
            file_size=Path(self.file_path).stat().st_size,
            is_encrypted=self.doc.is_encrypted,
            has_digital_signature=self._check_digital_signature(),
            pdf_version=self.doc.metadata.get("format", ""),
        )

    def _check_creation_date_vs_statement_period(self, creation_date: str):
        """Flag if PDF was created long after the statement period it claims to cover."""
        if not creation_date:
            return
        cd = self._parse_pdf_date(creation_date)
        if not cd:
            return

        text = self._get_full_text()
        # Look for year references in the statement (e.g. "January 2022", "03/2022")
        years_in_text = set(int(y) for y in re.findall(r'\b(20\d{2})\b', text))
        if not years_in_text:
            return

        latest_statement_year = max(years_in_text)
        creation_year = cd.year

        if creation_year > latest_statement_year + 1:
            self._add_indicator(
                title="PDF Created Long After Statement Period",
                description=f"The PDF file was created in {creation_year}, but the document content references dates up to {latest_statement_year}. A genuine statement would be generated close to the statement close date.",
                severity=IndicatorSeverity.HIGH,
                details=f"PDF creation year: {creation_year}  |  Latest year in content: {latest_statement_year}",
                confidence=85.0,
            )
            self.metadata_entries.append(MetadataEntry(
                field="Statement Period vs Creation Date",
                original_text=str(latest_statement_year),
                new_text=str(creation_year),
                status="mismatch",
            ))

    # ─── 2. Font Analysis ────────────────────────────────────────────────────

    def analyze_fonts(self):
        """Detect inconsistent font types and sizes — hallmarks of value editing."""
        font_sets: List[set] = []
        all_fonts: Dict[str, int] = {}
        # Track font sizes per span to detect size mixing in similar contexts
        size_samples: List[float] = []

        for page in self.doc:
            page_fonts = set()
            for font in page.get_fonts(full=True):
                name = font[3] or font[4] or "unknown"
                name_clean = re.sub(r'\+[A-Z]{6}', '', name)
                page_fonts.add(name_clean)
                all_fonts[name_clean] = all_fonts.get(name_clean, 0) + 1
            font_sets.append(page_fonts)

            # Collect sizes of numeric spans (amounts)
            blocks = page.get_text("rawdict")
            for block in blocks.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if re.search(r'\d', text):
                            size_samples.append(round(span.get("size", 0), 1))

        # Cross-page font inconsistency
        if len(font_sets) > 1:
            base = font_sets[0]
            inconsistent_pages = [
                i + 2 for i, fs in enumerate(font_sets[1:])
                if base.symmetric_difference(fs)
            ]
            if inconsistent_pages:
                self._add_indicator(
                    title="Inconsistent Font Usage Across Pages",
                    description="Different pages use different font sets, suggesting pages from separate documents were merged — a common technique in fabricated multi-page statements.",
                    severity=IndicatorSeverity.HIGH,
                    details=f"Inconsistent pages: {inconsistent_pages}",
                    confidence=82.0,
                )

        # Excessive distinct fonts
        if len(all_fonts) > 15:
            self._add_indicator(
                title="Excessive Number of Distinct Fonts",
                description=f"Found {len(all_fonts)} distinct fonts — far above the 3–5 typical of a genuine bank statement. Suggests content was pasted from multiple sources.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Fonts: {', '.join(list(all_fonts.keys())[:10])}{'...' if len(all_fonts) > 10 else ''}",
                confidence=72.0,
            )

        # Numeric span size inconsistency (edited values often have different sizes)
        if len(size_samples) >= 10:
            size_counts = Counter(size_samples)
            dominant_size, dominant_count = size_counts.most_common(1)[0]
            outlier_sizes = [
                s for s in size_samples
                if abs(s - dominant_size) > 1.5 and size_counts[s] < dominant_count * 0.2
            ]
            if len(outlier_sizes) >= 2:
                self._add_indicator(
                    title="Inconsistent Font Sizes in Numeric Fields",
                    description=f"Numeric values use inconsistent font sizes. The dominant size is {dominant_size}pt, but {len(outlier_sizes)} values use different sizes — a sign that individual figures were edited.",
                    severity=IndicatorSeverity.HIGH,
                    details=f"Dominant size: {dominant_size}pt  |  Outlier sizes: {sorted(set(outlier_sizes))}",
                    confidence=80.0,
                )

        self.metadata_entries.append(MetadataEntry(
            field="Distinct Fonts Used",
            original_text=str(len(all_fonts)),
            new_text=None,
            status="suspicious" if len(all_fonts) > 15 else "match",
        ))

    # ─── 3. Text Layer Analysis ──────────────────────────────────────────────

    def analyze_text_layers(self):
        """Check for hidden or overlapping text layers."""
        hidden_text_pages = []
        invisible_text_pages = []

        for page_num, page in enumerate(self.doc, start=1):
            blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in blocks.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("size", 12) < 0.5:
                            hidden_text_pages.append(page_num)
                        color = span.get("color", 0)
                        if color == 0xFFFFFF or color == 16777215:
                            invisible_text_pages.append(page_num)

        if hidden_text_pages:
            self._add_indicator(
                title="Hidden Text Layer Detected",
                description="Extremely small text (< 0.5pt) found — a known technique to embed hidden data or pass OCR checks.",
                severity=IndicatorSeverity.HIGH,
                details=f"Affected pages: {sorted(set(hidden_text_pages))}",
                confidence=91.0,
            )
        if invisible_text_pages:
            self._add_indicator(
                title="White-on-White Invisible Text",
                description="White-colored text detected — used to hide content from human reviewers while remaining machine-readable.",
                severity=IndicatorSeverity.HIGH,
                details=f"Affected pages: {sorted(set(invisible_text_pages))}",
                confidence=93.0,
            )

    # ─── 4. Image Analysis ───────────────────────────────────────────────────

    def analyze_images(self):
        """Detect suspicious image characteristics including low-res/blurry logos."""
        micro_images = []
        low_res_images = []
        total_images = 0

        for page_num, page in enumerate(self.doc, start=1):
            page_rect = page.rect
            page_width_pt = page_rect.width  # points

            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    img_dict = self.doc.extract_image(xref)
                    total_images += 1
                    w_px = img_dict.get("width", 0)
                    h_px = img_dict.get("height", 0)

                    if 0 < w_px < 50 and 0 < h_px < 50:
                        micro_images.append({"page": page_num, "w": w_px, "h": h_px})

                    # Estimate effective DPI: image pixel width vs page width in inches
                    # A4/Letter ~8.27 in wide = 595pt. If image spans full page:
                    if w_px > 0 and page_width_pt > 0:
                        est_dpi = (w_px / page_width_pt) * 72
                        if est_dpi < 72 and w_px > 50:  # Low DPI for non-tiny image
                            low_res_images.append({
                                "page": page_num, "w": w_px, "h": h_px,
                                "est_dpi": round(est_dpi)
                            })
                except Exception:
                    pass

        if micro_images:
            self._add_indicator(
                title="Suspicious Micro-Images Embedded",
                description="Very small images (< 50×50 px) found — artifacts of image-based text replacement or tracking pixels.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"{len(micro_images)} micro-images on pages: {[i['page'] for i in micro_images]}",
                confidence=68.0,
            )

        if low_res_images:
            self._add_indicator(
                title="Low-Resolution Images (Possible Scanned/Copied Logo)",
                description="Images with very low effective resolution detected. Genuine bank statement logos are rendered at high resolution by the bank's PDF generator; low-res images suggest the logo was copied from a screenshot or webpage.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"{len(low_res_images)} low-res image(s) — estimated DPI: {[i['est_dpi'] for i in low_res_images]}",
                confidence=72.0,
            )

        self.metadata_entries.append(MetadataEntry(
            field="Embedded Images",
            original_text=str(total_images),
            new_text=None,
            status="match",
        ))

    # ─── 5. PDF Structure Analysis ───────────────────────────────────────────

    def analyze_document_type(self):
        """Detect image-only (scanned) PDFs — genuine bank statements always have a text layer."""
        if self._is_image_only:
            self._add_indicator(
                title="No Text Layer — Image-Only PDF",
                description=(
                    "This PDF contains no extractable text. Genuine bank statements are digitally "
                    "generated by banking software and always embed a searchable text layer. "
                    "An image-only document suggests it was printed and re-scanned — a common "
                    "technique to remove digital metadata and editing traces before submission."
                ),
                severity=IndicatorSeverity.HIGH,
                details="0 characters of text extracted across all pages. All text-based checks are unavailable.",
                confidence=88.0,
            )
            self.metadata_entries.append(MetadataEntry(
                field="Text Layer Present",
                original_text="No",
                new_text="Expected: Yes",
                status="mismatch",
            ))
        else:
            char_count = len(self._get_full_text().strip())
            self.metadata_entries.append(MetadataEntry(
                field="Text Layer Present",
                original_text="Yes",
                new_text=f"{char_count} chars",
                status="match",
            ))

    def analyze_structure(self):
        """Check PDF binary structure for signs of manipulation."""
        with open(self.file_path, "rb") as f:
            raw = f.read()

        xref_count = raw.count(b"%%EOF")
        if xref_count > 1:
            self._add_indicator(
                title="Multiple Document Revisions Detected",
                description=f"The PDF has {xref_count} end-of-file markers, meaning it was edited after initial creation ({xref_count - 1} incremental save(s)). Genuine bank statements are generated once and never incrementally modified.",
                severity=IndicatorSeverity.HIGH,
                details=f"Incremental saves: {xref_count - 1}",
                confidence=90.0,
            )
            self.metadata_entries.append(MetadataEntry(
                field="Incremental Saves (Edits)",
                original_text="0",
                new_text=str(xref_count - 1),
                status="mismatch",
            ))
        else:
            self.metadata_entries.append(MetadataEntry(
                field="Incremental Saves (Edits)",
                original_text="0",
                new_text=None,
                status="match",
            ))

        if b"/JavaScript" in raw or b"/JS" in raw:
            self._add_indicator(
                title="JavaScript Embedded in PDF",
                description="JavaScript found — financial documents never contain scripts. May indicate an attempt to manipulate the viewer or exfiltrate data.",
                severity=IndicatorSeverity.HIGH,
                confidence=88.0,
            )

        if b"/AcroForm" in raw:
            self._add_indicator(
                title="Editable Form Fields Present",
                description="Fillable AcroForm fields detected. Bank statements are read-only; editable fields suggest the document was designed for manual value entry.",
                severity=IndicatorSeverity.MEDIUM,
                confidence=75.0,
            )

    # ─── 6. Financial Content Analysis ──────────────────────────────────────

    def analyze_financial_content(self):
        """Heuristic analysis of statement text for bank-statement-specific red flags."""
        if self._is_image_only:
            # All text-dependent checks cannot run — already flagged in analyze_document_type
            for field in [
                "Balance Math Check", "Rounded Deposits Check",
                "Account Number Consistency", "Everyday Expense Categories",
                "Weekend Transaction Check", "Column Alignment Check",
            ]:
                self.metadata_entries.append(MetadataEntry(
                    field=field,
                    original_text="N/A",
                    new_text="OCR required",
                    status="annotation",
                ))
            return

        text = self._get_full_text()
        text_lower = text.lower()

        self._check_running_balance_math(text)
        self._check_rounded_repeated_deposits(text)
        self._check_account_number_consistency(text)
        self._check_account_name_consistency(text)
        self._check_missing_everyday_expenses(text_lower)
        self._check_transaction_backdating(text)
        self._check_generic_deposit_descriptions(text_lower)
        self._check_watermarks(text_lower)
        self._check_currency_formatting(text)
        self._check_issuer_signatures(text_lower)
        self._check_mismatched_columns(text)

    def _check_running_balance_math(self, text: str):
        """Verify that running balances add up (debit/credit → new balance)."""
        # Extract lines with a pattern: amount debit/credit, then balance
        # Pattern: optional date, description, amount, balance on same line
        line_pattern = re.compile(
            r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
        )
        errors = 0
        checked = 0

        for line in text.splitlines():
            m = line_pattern.search(line)
            if not m:
                continue
            try:
                a = float(m.group(1).replace(',', ''))
                b = float(m.group(2).replace(',', ''))
                c = float(m.group(3).replace(',', ''))
                # Check if a + b ≈ c or a - b ≈ c (debit or credit)
                if abs((a + b) - c) < 0.02 or abs((a - b) - c) < 0.02:
                    checked += 1
                elif checked > 0:
                    # We found a pattern but this line breaks it
                    errors += 1
            except Exception:
                pass

        if checked >= 3 and errors >= 2:
            self._add_indicator(
                title="Running Balance Math Errors",
                description=f"Mathematical verification of transaction amounts against running balances found {errors} inconsistenc{'y' if errors == 1 else 'ies'}. Legitimate statements always balance exactly — errors indicate values were manually altered.",
                severity=IndicatorSeverity.HIGH,
                details=f"Checked {checked + errors} rows, {errors} failed balance verification",
                confidence=88.0,
            )
            self.metadata_entries.append(MetadataEntry(
                field="Balance Math Check",
                original_text="Pass",
                new_text=f"{errors} error(s)",
                status="mismatch",
            ))
        elif checked >= 3:
            self.metadata_entries.append(MetadataEntry(
                field="Balance Math Check",
                original_text="Pass",
                new_text=None,
                status="match",
            ))

    def _check_rounded_repeated_deposits(self, text: str):
        """Detect suspiciously round or repeated deposit amounts."""
        amounts = re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b', text)
        parsed = []
        for a in amounts:
            try:
                v = float(a.replace(',', ''))
                if v > 10:
                    parsed.append(v)
            except Exception:
                pass

        if not parsed:
            return

        # Perfectly round amounts (divisible by 100 or 1000)
        round_amounts = [v for v in parsed if v >= 100 and v % 100 == 0]
        round_ratio = len(round_amounts) / len(parsed) if parsed else 0
        if round_ratio > 0.7 and len(parsed) >= 5:
            self._add_indicator(
                title="Suspiciously Round Transaction Amounts",
                description=f"{round_ratio:.0%} of monetary values are perfectly round numbers (divisible by 100). Real transaction histories contain varied amounts from everyday spending.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Round amounts: {sorted(set(round_amounts))[:10]}",
                confidence=74.0,
            )

        # Identical repeated amounts (e.g. same deposit every time)
        count = Counter(parsed)
        highly_repeated = [(v, c) for v, c in count.items() if c >= 4 and v >= 500]
        if highly_repeated:
            self._add_indicator(
                title="Identical Deposit Amounts Repeated",
                description=f"Certain amounts appear {highly_repeated[0][1]}+ times identically. While recurring salaries are normal, multiple large identical amounts suggest fabricated data.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Repeated: {[(f'${v:,.2f} × {c}') for v, c in highly_repeated[:5]]}",
                confidence=70.0,
            )

    def _check_account_number_consistency(self, text: str):
        """Detect different account numbers appearing across pages."""
        # Account numbers: 8–17 digit sequences near keywords
        pattern = re.compile(
            r'(?:account\s*(?:number|no\.?|#)?|acct\.?)\s*[:\-]?\s*[\*xX]*(\d[\d\s\-]{6,18}\d)',
            re.IGNORECASE,
        )
        found = set()
        for m in pattern.finditer(text):
            num = re.sub(r'[\s\-]', '', m.group(1))
            if 8 <= len(num) <= 17:
                found.add(num)

        self.metadata_entries.append(MetadataEntry(
            field="Account Numbers Found",
            original_text=str(len(found)),
            new_text=None,
            status="suspicious" if len(found) > 1 else "match",
        ))

        if len(found) > 1:
            self._add_indicator(
                title="Multiple Different Account Numbers Detected",
                description=f"Found {len(found)} distinct account numbers in a single statement. A genuine bank statement covers exactly one account.",
                severity=IndicatorSeverity.HIGH,
                details=f"Account numbers (masked): {['***' + n[-4:] for n in found]}",
                confidence=89.0,
            )

    def _check_account_name_consistency(self, text: str):
        """Detect holder name changes across pages (page-swapping fraud)."""
        pages_text = [page.get_text() for page in self.doc]
        if len(pages_text) < 2:
            return

        # Extract capitalized name-like sequences near "name" keywords
        name_pattern = re.compile(
            r'(?:account\s*holder|customer\s*name|name|client)\s*[:\-]?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3})',
            re.IGNORECASE,
        )
        page_names: List[set] = []
        for pt in pages_text:
            names = set(m.group(1).strip().upper() for m in name_pattern.finditer(pt))
            if names:
                page_names.append(names)

        if len(page_names) < 2:
            return

        all_names: set = set()
        for ns in page_names:
            all_names.update(ns)

        if len(all_names) > 1:
            self._add_indicator(
                title="Account Holder Name Inconsistency Across Pages",
                description=f"Different account holder names were found on different pages ({len(all_names)} distinct names). This is a strong indicator of page-swapping — replacing pages from a genuine statement with forged ones.",
                severity=IndicatorSeverity.HIGH,
                details=f"Names found: {list(all_names)[:5]}",
                confidence=87.0,
            )

    def _check_missing_everyday_expenses(self, text_lower: str):
        """Flag statements with no recognizable everyday spending patterns."""
        found = [kw for kw in EXPECTED_EXPENSE_KEYWORDS if kw in text_lower]
        total_words = len(text_lower.split())

        if total_words < 100:
            return  # Too little text to judge

        # A real 30-day statement for an active account should have some everyday expenses
        if len(found) == 0:
            self._add_indicator(
                title="No Everyday Expenses Detected",
                description="No recognizable everyday expense categories (groceries, utilities, fuel, dining, subscriptions, etc.) were found. Genuine personal bank statements almost always contain routine spending.",
                severity=IndicatorSeverity.MEDIUM,
                details="Missing: groceries, utilities, fuel, dining, subscriptions, rent, etc.",
                confidence=65.0,
            )
        elif len(found) <= 2:
            self._add_indicator(
                title="Very Few Everyday Expense Categories",
                description=f"Only {len(found)} everyday expense categor{'y' if len(found) == 1 else 'ies'} found ({', '.join(found)}). Real statements typically show diverse spending across utilities, groceries, dining, and more.",
                severity=IndicatorSeverity.LOW,
                details=f"Found: {found}",
                confidence=55.0,
            )

        self.metadata_entries.append(MetadataEntry(
            field="Everyday Expense Categories",
            original_text=str(len(found)),
            new_text=None,
            status="suspicious" if len(found) == 0 else "match",
        ))

    def _check_transaction_backdating(self, text: str):
        """Detect transactions dated on weekends or bank holidays."""
        # Look for date patterns followed by amounts
        date_pattern = re.compile(
            r'\b(0?[1-9]|1[0-2])[\/\-](0?[1-9]|[12]\d|3[01])[\/\-]?(20\d{2})?\b'
        )
        weekend_txns = []
        holiday_txns = []

        for m in date_pattern.finditer(text):
            try:
                month = int(m.group(1))
                day = int(m.group(2))
                year_str = m.group(3)
                year = int(year_str) if year_str else datetime.now().year
                d = date(year, month, day)

                if d.weekday() in WEEKEND_DAYS:
                    weekend_txns.append(m.group(0))
                if (month, day) in BANK_HOLIDAYS:
                    holiday_txns.append(m.group(0))
            except Exception:
                pass

        if len(weekend_txns) > 3:
            self._add_indicator(
                title="Multiple Transactions on Weekends",
                description=f"{len(weekend_txns)} transactions dated on weekends. Bank-posted transactions (ACH, wire, direct deposit) typically do not process on Saturdays or Sundays. A high count suggests backdated or fabricated entries.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Weekend dates: {weekend_txns[:8]}",
                confidence=67.0,
            )

        if holiday_txns:
            self._add_indicator(
                title="Transactions Dated on Bank Holidays",
                description=f"Transactions found on known US bank holidays: {holiday_txns}. Banks do not process ACH or wire transfers on federal holidays.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Holiday dates: {holiday_txns}",
                confidence=72.0,
            )

    def _check_generic_deposit_descriptions(self, text_lower: str):
        """Flag deposits with vague descriptions instead of specific employer/sender names."""
        lines = text_lower.splitlines()
        generic_count = 0
        total_deposit_lines = 0

        for line in lines:
            has_amount = bool(re.search(r'\d+\.\d{2}', line))
            if not has_amount:
                continue
            # Lines that look like deposits/credits
            if any(kw in line for kw in ['deposit', 'credit', 'transfer in', 'received']):
                total_deposit_lines += 1
                if any(re.search(p, line) for p in GENERIC_DEPOSIT_PATTERNS):
                    # Check if it lacks a specific name/identifier beyond the generic term
                    stripped = re.sub(r'\d[\d\.,]*', '', line).strip()
                    words = [w for w in stripped.split() if len(w) > 3]
                    if len(words) <= 2:
                        generic_count += 1

        if total_deposit_lines >= 3 and generic_count >= total_deposit_lines * 0.6:
            self._add_indicator(
                title="Generic Transaction Descriptions",
                description=f"{generic_count} of {total_deposit_lines} deposit/credit entries use vague labels like 'DEPOSIT' or 'TRANSFER IN' with no specific employer or sender name. Genuine payroll and transfers typically include the originating company name.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Generic entries: {generic_count}/{total_deposit_lines}",
                confidence=68.0,
            )

    def _check_watermarks(self, text_lower: str):
        """Detect sample/draft/void watermark text."""
        patterns = [r'\bsample\b', r'\bdraft\b', r'\bvoid\b', r'\bspecimen\b', r'\btest\b']
        found = [p.strip(r'\b') for p in patterns if re.search(p, text_lower)]
        if found:
            self._add_indicator(
                title="Sample / Draft Watermark Text Detected",
                description="Words like 'SAMPLE', 'DRAFT', 'VOID', or 'SPECIMEN' found — indicates a template document presented as genuine.",
                severity=IndicatorSeverity.HIGH,
                details=f"Keywords: {found}",
                confidence=85.0,
            )

    def _check_currency_formatting(self, text: str):
        """Detect mixed currency formatting styles."""
        amounts = re.findall(r'\$[\d,]+\.?\d*', text)
        inconsistent = [a for a in amounts if re.search(r'\$\d+,\d{1,2}$', a)]
        if inconsistent:
            self._add_indicator(
                title="Inconsistent Currency Formatting",
                description="Currency amounts with inconsistent formatting detected — suggests values were copied from a different locale or source.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Examples: {inconsistent[:5]}",
                confidence=70.0,
            )

    def _check_issuer_signatures(self, text_lower: str):
        """Record whether issuer signature references are present."""
        sig_keywords = [
            "signature of issuing", "authorized signatory",
            "signed by", "electronically signed", "digital signature",
        ]
        has_sig = any(kw in text_lower for kw in sig_keywords)
        self.metadata_entries.append(MetadataEntry(
            field="Signature of Issuing",
            original_text="Present" if has_sig else None,
            new_text="Annotation" if not has_sig else None,
            status="annotation" if not has_sig else "match",
        ))

        # Common third-party invoice/doc sources
        for source, pattern in {
            "Google Invoices": r'google\s+invoice|invoice\s+from\s+google',
            "HubSpot Docs": r'hubspot',
            "Stripe Invoices": r'stripe\s+invoice',
        }.items():
            if re.search(pattern, text_lower):
                self.metadata_entries.append(MetadataEntry(
                    field=source, original_text="Detected",
                    new_text="Annotation", status="annotation",
                ))

    def _check_mismatched_columns(self, text: str):
        """Detect columnar alignment issues — sign of manual text editing."""
        lines = [l for l in text.splitlines() if re.search(r'\d+\.\d{2}', l)]
        if len(lines) < 5:
            return

        # Count how many decimal points appear per line
        decimal_positions = []
        for line in lines:
            positions = [m.start() for m in re.finditer(r'\.\d{2}\b', line)]
            if positions:
                decimal_positions.append(positions[-1])  # rightmost amount (balance column)

        if len(decimal_positions) < 5:
            return

        # If balance column positions vary wildly, columns are misaligned
        avg = sum(decimal_positions) / len(decimal_positions)
        outliers = [p for p in decimal_positions if abs(p - avg) > 15]
        if len(outliers) > len(decimal_positions) * 0.3:
            self._add_indicator(
                title="Misaligned Column Formatting",
                description=f"Decimal alignment in the balance column is inconsistent across {len(outliers)} rows. Bank-generated PDFs use precise column alignment; misalignment indicates manual editing of individual values.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Expected alignment ~col {int(avg)}, {len(outliers)} rows deviate >15 chars",
                confidence=73.0,
            )

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _check_digital_signature(self) -> bool:
        try:
            with open(self.file_path, "rb") as f:
                raw = f.read()
            return b"/Sig" in raw and b"/ByteRange" in raw
        except Exception:
            return False

    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = re.sub(r'^D:', '', date_str)
        date_str = re.sub(r'[Z+\-]\d{2}\'?\d{0,2}\'?$', '', date_str)
        try:
            return datetime.strptime(date_str[:14], '%Y%m%d%H%M%S')
        except Exception:
            try:
                return date_parser.parse(date_str)
            except Exception:
                return None

    # ─── Scoring ─────────────────────────────────────────────────────────────

    def compute_risk(self) -> Tuple[IndicatorSeverity, float]:
        if not self.indicators:
            return IndicatorSeverity.SAFE, 5.0

        severity_weights = {
            IndicatorSeverity.HIGH: 35,
            IndicatorSeverity.MEDIUM: 15,
            IndicatorSeverity.LOW: 5,
            IndicatorSeverity.SAFE: 0,
        }
        weighted_score = sum(
            severity_weights[ind.severity] * (ind.confidence / 100)
            for ind in self.indicators
        )
        fraud_score = min(100.0, weighted_score)

        if fraud_score >= 60:
            return IndicatorSeverity.HIGH, fraud_score
        elif fraud_score >= 30:
            return IndicatorSeverity.MEDIUM, fraud_score
        elif fraud_score >= 10:
            return IndicatorSeverity.LOW, fraud_score
        return IndicatorSeverity.SAFE, fraud_score

    # ─── Entry Point ─────────────────────────────────────────────────────────

    def run(self, document_id: str, filename: str) -> AnalysisResult:
        metadata = self.analyze_metadata()
        self.analyze_document_type()
        self.analyze_fonts()
        self.analyze_text_layers()
        self.analyze_images()
        self.analyze_structure()
        self.analyze_financial_content()

        overall_risk, fraud_score = self.compute_risk()

        summaries = {
            IndicatorSeverity.HIGH: (
                "Based on the previously studied data patterns, we are almost certain that "
                "we can classify this document as dangerous. The final decision is up to you."
            ),
            IndicatorSeverity.MEDIUM: (
                "This document shows several suspicious characteristics. "
                "Manual review is strongly recommended before accepting this document."
            ),
            IndicatorSeverity.LOW: (
                "Minor anomalies were detected. The document may be legitimate, "
                "but some properties warrant a closer look."
            ),
            IndicatorSeverity.SAFE: (
                "No significant fraud indicators found. This document appears consistent "
                "with a genuine financial document."
            ),
        }

        return AnalysisResult(
            document_id=document_id,
            filename=filename,
            overall_risk=overall_risk,
            fraud_score=round(fraud_score, 1),
            indicators=self.indicators,
            metadata_entries=self.metadata_entries,
            metadata=metadata,
            summary=summaries[overall_risk],
            page_count=len(self.doc),
            analyzed_at=datetime.utcnow().isoformat(),
        )

    def close(self):
        self.doc.close()
