"""
Core fraud detection algorithms for document analysis.

Algorithms are split into two independent tiers:

  PART I  — Universal checks (non-content-based)
            Inspect the PDF container itself: metadata, structure, fonts,
            images, text layers, and annotations. These run identically on
            any PDF document regardless of its content type.

  PART II — Content-based checks (bank-statement-specific)
            Parse the extracted text for financial logic errors, implausible
            numeric patterns, and fabricated transaction data. These are
            meaningless on non-financial documents.
"""
import fitz  # PyMuPDF
import math
import re
from collections import Counter
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dateutil import parser as date_parser

from app.models.schemas import (
    FraudIndicator, HighlightBox, MetadataEntry, DocumentMetadata,
    IndicatorSeverity, AnalysisResult
)
from app.services.ocr_service import OCRService, OCRWord


# ─── Constants ───────────────────────────────────────────────────────────────

KNOWN_LEGITIMATE_TOOLS = {
    "microsoft word", "microsoft excel", "adobe acrobat",
    "libreoffice", "google docs", "wps office", "pages",
    "nitro pdf", "foxit phantompdf", "pdfelement",
    "openoffice", "quartz pdfcontext", "mac os x quartz",
    "cairo", "ghostscript", "crystal reports",
    # Enterprise Customer Communications Management / document generation platforms
    "quadient", "inspire",          # Quadient Inspire (used by DBS, major banks)
    "opentext", "output transformation",  # OpenText Output Transformation Engine
    "vault rendering", "rendering engine",  # Vault Rendering Engine (UOB)
    "pdfgen", "streamline",         # Streamline PDFGen (OCBC)
    "ricoh", "afp2pdf", "afp",      # Ricoh AFP2PDF Plus (Citibank)
    "docutech", "bottomline", "finastra", "temenos",
    "oracle bi", "sap crystal", "jasperreports", "ireport",
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

# Benford's Law — expected first-digit probabilities for naturally occurring amounts
BENFORD_EXPECTED: Dict[int, float] = {
    1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
    5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046,
}

# Deviation threshold per digit before raising Benford flag.
# 15% gives more tolerance for small samples; requires 3+ deviating digits to fire.
BENFORD_DEVIATION_THRESHOLD = 0.15
BENFORD_MIN_SAMPLES = 50            # Need a reasonable sample for the law to apply

# US bank holidays (month, day) — approximate static list
BANK_HOLIDAYS = {
    (1, 1), (7, 4), (12, 25), (11, 11),  # New Year, Independence, Christmas, Veterans
}


class DocumentFraudDetector:
    def __init__(self, file_path: str, ocr_service: Optional[OCRService] = None):
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.indicators: List[FraudIndicator] = []
        self.metadata_entries: List[MetadataEntry] = []
        self._indicator_counter = 0
        self._full_text: Optional[str] = None
        self._ocr_service: Optional[OCRService] = ocr_service
        self._ocr_words: Optional[List[OCRWord]] = None  # populated on demand

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
        highlights: Optional[List[HighlightBox]] = None,
    ):
        self.indicators.append(FraudIndicator(
            id=self._new_indicator_id(),
            title=title,
            description=description,
            severity=severity,
            details=details,
            confidence=confidence,
            highlights=highlights or [],
        ))

    def _get_full_text(self) -> str:
        if self._full_text is None:
            self._full_text = "".join(page.get_text() for page in self.doc)
        return self._full_text

    @property
    def _native_text_empty(self) -> bool:
        """True when the PDF has no native/extractable text layer."""
        return len(self._get_full_text().strip()) < 20

    @property
    def _is_image_only(self) -> bool:
        """True when no usable text is available (native OR OCR).

        After OCR runs, this becomes False so all content checks proceed using
        the OCR-extracted text instead of the native text layer.
        """
        if not self._native_text_empty:
            return False
        # If OCR words have been loaded, we have text — not truly image-only
        if self._ocr_words is not None and len(self._ocr_words) > 0:
            return False
        return True

    def _run_ocr(self) -> None:
        """Run OCR over the whole document and cache results in _ocr_words."""
        if self._ocr_words is not None:
            return  # already done
        if self._ocr_service is None or not self._ocr_service.is_available():
            self._ocr_words = []
            return
        self._ocr_words = self._ocr_service.run_document(self.doc)

    def _get_text_for_analysis(self) -> str:
        """Return the best available text: native layer, or OCR fallback."""
        native = self._get_full_text()
        if native.strip():
            return native
        if self._ocr_words:
            return " ".join(w.text for w in self._ocr_words)
        return ""

    def _ocr_search_highlights(
        self,
        query: str,
        label: str,
        max_per_page: int = 3,
    ) -> List[HighlightBox]:
        """Search OCR word list for query tokens and return highlight boxes.

        Used as a fallback when page.search_for() returns nothing because the
        PDF has no native text layer.
        """
        if not self._ocr_words:
            return []
        query_lower = query.lower()
        results: List[HighlightBox] = []
        seen_pages: dict = {}
        for w in self._ocr_words:
            if query_lower in w.text.lower():
                cnt = seen_pages.get(w.page, 0)
                if cnt >= max_per_page:
                    continue
                page = self.doc[w.page - 1]
                results.append(HighlightBox(
                    page=w.page,
                    x0=w.x0, y0=w.y0, x1=w.x1, y1=w.y1,
                    label=label,
                    page_width=page.rect.width,
                    page_height=page.rect.height,
                ))
                seen_pages[w.page] = cnt + 1
        return results

    # ═══════════════════════════════════════════════════════════════════════
    # PART I — UNIVERSAL CHECKS  (non-content-based)
    # Applicable to any PDF document regardless of content type.
    # Checks: metadata integrity, PDF structure, fonts, images, text layers,
    #         annotations.  No financial domain knowledge required.
    # ═══════════════════════════════════════════════════════════════════════

    # ─── I-1. Metadata ───────────────────────────────────────────────────────

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
        producer_lower = producer.lower()
        if creator:
            creator_lower = creator.lower()
            combined = creator_lower + " " + producer_lower
            is_image_editor = any(t in creator_lower for t in IMAGE_EDITING_TOOLS)
            is_suspicious = any(re.search(p, creator_lower) for p in SUSPICIOUS_CREATOR_PATTERNS)
            # A tool is "known" if the creator OR the producer matches a recognised system.
            # Many bank-internal generators have generic creator names (e.g. "pdfgen") but
            # descriptive producers ("Streamline PDFGen for OCBC Group").
            is_known = (
                any(t in combined for t in KNOWN_LEGITIMATE_TOOLS)
                or re.search(r'bank|financial|statement|report|group|finance', combined)
            )

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
                    details=f"Creator: {creator}  |  Producer: {producer or '—'}",
                    confidence=62.0,
                )
        else:
            # If the producer field identifies a known legitimate system, the
            # missing creator is not suspicious — some generators omit it.
            producer_known = any(t in producer_lower for t in KNOWN_LEGITIMATE_TOOLS) or (
                re.search(r'bank|financial|statement|report|group|finance|engine|transform', producer_lower) is not None
            )
            if not producer_known:
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

    # ─── I-2. Font Analysis ──────────────────────────────────────────────────

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
        # Use the union of fonts across ALL pages as the expected set, then flag
        # pages that are MISSING core fonts — not pages that merely add extra fonts
        # (e.g. a CJK font on a bilingual page is expected and not suspicious).
        if len(font_sets) > 1:
            # Fonts present on more than half the pages are "core" fonts
            n_pages = len(font_sets)
            all_page_fonts: Dict[str, int] = {}
            for fs in font_sets:
                for f in fs:
                    all_page_fonts[f] = all_page_fonts.get(f, 0) + 1
            core_fonts = {f for f, cnt in all_page_fonts.items() if cnt > n_pages / 2}

            missing_pages = [
                i + 1 for i, fs in enumerate(font_sets)
                if core_fonts - fs  # page is missing at least one core font
            ]
            # Tail pages (last 25% of document) commonly shed bold/decorative fonts
            # for fine-print / T&C sections — this is normal and not suspicious.
            tail_start = max(1, int(n_pages * 0.75) + 1)
            non_tail_missing = [p for p in missing_pages if p < tail_start]
            if len(non_tail_missing) > 1:
                self._add_indicator(
                    title="Inconsistent Font Usage Across Pages",
                    description="Multiple mid-document pages are missing fonts that appear consistently throughout the rest of the document, suggesting pages from a different source were inserted.",
                    severity=IndicatorSeverity.HIGH,
                    details=f"Pages missing core fonts: {non_tail_missing}",
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

        self._check_intra_line_font_fingerprint()

    def _check_intra_line_font_fingerprint(self):
        """Detect spans within a single transaction row whose font fingerprint
        differs from the rest of that row.

        A font fingerprint is the tuple (normalised font name, rounded size,
        bold/italic flags, colour).  In a bank-generated PDF every span on the
        same row shares an identical fingerprint.  A single outlier span —
        especially one containing a monetary amount — is a strong signal that
        the value was individually replaced after generation.
        """
        # (font_name, size_1dp, flags, color) → strip subset prefixes like "ABCDEF+"
        def fingerprint(span: dict) -> tuple:
            name = re.sub(r'^[A-Z]{6}\+', '', span.get("font", "") or "")
            return (
                name.lower().strip(),
                round(span.get("size", 0), 1),
                span.get("flags", 0) & 0b11110,   # bold/italic/monospace bits only
                span.get("color", 0),
            )

        outlier_rows: List[dict] = []   # {page, line_text, outlier_text, row_fp, outlier_fp, bbox, pw, ph}

        for page_num, page in enumerate(self.doc, start=1):
            pw, ph = page.rect.width, page.rect.height
            blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in blocks.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    # Only examine lines that look like transaction rows:
                    # must contain at least one monetary amount and 3+ spans
                    line_text = "".join(s.get("text", "") for s in spans)
                    if not re.search(r'\d+[.,]\d{2}', line_text):
                        continue
                    if len(spans) < 3:
                        continue

                    fps = [fingerprint(s) for s in spans]
                    fp_counts = Counter(fps)
                    dominant_fp, dominant_count = fp_counts.most_common(1)[0]

                    # An outlier is a span with a unique fingerprint (count == 1)
                    # that differs from the dominant AND contains a digit
                    for span, fp in zip(spans, fps):
                        if fp == dominant_fp:
                            continue
                        if fp_counts[fp] > 1:
                            continue  # not a singleton — probably a header label
                        text = span.get("text", "").strip()
                        if not re.search(r'\d', text):
                            continue  # only care about numeric outliers

                        # Suppress very small size differences (< 0.3pt) — rounding artefacts
                        size_delta = abs(fp[1] - dominant_fp[1])
                        name_differs = fp[0] != dominant_fp[0]
                        flags_differ = fp[2] != dominant_fp[2]
                        color_differs = fp[3] != dominant_fp[3]

                        if size_delta < 0.3 and not name_differs and not flags_differ and not color_differs:
                            continue

                        outlier_rows.append({
                            "page": page_num,
                            "line": line_text[:80],
                            "span_text": text,
                            "dominant": dominant_fp,
                            "outlier": fp,
                            "size_delta": round(size_delta, 2),
                            "name_differs": name_differs,
                            "color_differs": color_differs,
                            "bbox": span.get("bbox"),
                            "pw": pw,
                            "ph": ph,
                        })

        if not outlier_rows:
            self.metadata_entries.append(MetadataEntry(
                field="Intra-Line Font Fingerprint",
                original_text="Consistent",
                new_text=None,
                status="match",
            ))
            return

        # Build a concise detail string for the top outliers
        detail_parts = []
        for r in outlier_rows[:5]:
            reasons = []
            if r["name_differs"]:
                reasons.append(f"font '{r['outlier'][0]}' vs '{r['dominant'][0]}'")
            if r["size_delta"] >= 0.3:
                reasons.append(f"size {r['outlier'][1]}pt vs {r['dominant'][1]}pt")
            if r["color_differs"]:
                reasons.append(f"colour #{r['outlier'][3]:06X} vs #{r['dominant'][3]:06X}")
            detail_parts.append(
                f"p{r['page']} — \"{r['span_text']}\" ({', '.join(reasons)})"
            )

        severity = IndicatorSeverity.HIGH if len(outlier_rows) >= 3 else IndicatorSeverity.MEDIUM
        confidence = 88.0 if len(outlier_rows) >= 3 else 74.0

        highlights = [
            HighlightBox(
                page=r["page"],
                x0=r["bbox"][0], y0=r["bbox"][1],
                x1=r["bbox"][2], y1=r["bbox"][3],
                label=f"Font mismatch: \"{r['span_text']}\"",
                page_width=r["pw"], page_height=r["ph"],
            )
            for r in outlier_rows if r.get("bbox")
        ]

        self._add_indicator(
            title="Intra-Line Font Fingerprint Mismatch",
            description=(
                f"{len(outlier_rows)} transaction row(s) contain a span whose font fingerprint "
                "(name, size, style, colour) differs from every other span on that row. "
                "Bank-generated PDFs typeset each row with a single consistent style; "
                "a lone outlier span — particularly on a monetary amount — indicates that "
                "individual value was replaced after the document was generated."
            ),
            severity=severity,
            details=" | ".join(detail_parts),
            confidence=confidence,
            highlights=highlights,
        )
        self.metadata_entries.append(MetadataEntry(
            field="Intra-Line Font Fingerprint",
            original_text="Consistent expected",
            new_text=f"{len(outlier_rows)} outlier span(s)",
            status="mismatch",
        ))

    # ─── I-3. Text Layer Analysis ────────────────────────────────────────────

    def analyze_text_layers(self):
        """Check for hidden or overlapping text layers."""
        hidden_text_pages = []
        invisible_text_pages = []
        hidden_highlights: List[HighlightBox] = []
        invisible_highlights: List[HighlightBox] = []

        for page_num, page in enumerate(self.doc, start=1):
            pw, ph = page.rect.width, page.rect.height
            blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in blocks.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        bbox = span.get("bbox")
                        if span.get("size", 12) < 0.5:
                            hidden_text_pages.append(page_num)
                            if bbox:
                                hidden_highlights.append(HighlightBox(
                                    page=page_num, x0=bbox[0], y0=bbox[1],
                                    x1=bbox[2], y1=bbox[3],
                                    label="Hidden text",
                                    page_width=pw, page_height=ph,
                                ))
                        color = span.get("color", 0)
                        span_text = span.get("text", "")
                        # Only flag if the span contains actual non-whitespace content —
                        # PDF generators legitimately use white-colored spaces for layout.
                        if (color == 0xFFFFFF or color == 16777215) and span_text.strip():
                            invisible_text_pages.append(page_num)
                            if bbox:
                                invisible_highlights.append(HighlightBox(
                                    page=page_num, x0=bbox[0], y0=bbox[1],
                                    x1=bbox[2], y1=bbox[3],
                                    label="Invisible text",
                                    page_width=pw, page_height=ph,
                                ))

        if hidden_text_pages:
            self._add_indicator(
                title="Hidden Text Layer Detected",
                description="Extremely small text (< 0.5pt) found — a known technique to embed hidden data or pass OCR checks.",
                severity=IndicatorSeverity.HIGH,
                details=f"Affected pages: {sorted(set(hidden_text_pages))}",
                confidence=91.0,
                highlights=hidden_highlights,
            )
        if invisible_text_pages:
            self._add_indicator(
                title="White-on-White Invisible Text",
                description="White-colored text detected — used to hide content from human reviewers while remaining machine-readable.",
                severity=IndicatorSeverity.HIGH,
                details=f"Affected pages: {sorted(set(invisible_text_pages))}",
                confidence=93.0,
                highlights=invisible_highlights,
            )

    # ─── I-4. Image Analysis ─────────────────────────────────────────────────

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

                    # Tracking pixels / replacement artifacts are typically ≤ 5px.
                    # Small UI icons (24–48 px) are standard in professional PDFs.
                    if 0 < w_px <= 5 and 0 < h_px <= 5:
                        micro_images.append({"page": page_num, "w": w_px, "h": h_px})

                    # Estimate effective DPI: image pixel width vs page width in inches.
                    # Only flag images large enough to be content (> 100px) — small icons
                    # are always low-DPI by design and are not suspicious.
                    if w_px > 0 and page_width_pt > 0:
                        est_dpi = (w_px / page_width_pt) * 72
                        if est_dpi < 20 and w_px > 100 and h_px > 60:  # Extremely low DPI for content-sized image (< 20 strongly suggests screenshot/copy-paste; excludes AFP/print-stream logos)
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

    # ─── I-5. PDF Structure Analysis ─────────────────────────────────────────

    def analyze_document_type(self):
        """Detect image-only (scanned) PDFs.

        When no native text layer is found, attempt OCR via PaddleOCR. If OCR
        succeeds the document is treated as readable for all subsequent checks.
        """
        if self._native_text_empty:
            # Attempt OCR before raising an indicator
            self._run_ocr()

            if self._ocr_words:
                # OCR succeeded — document is analysable
                ocr_char_count = sum(len(w.text) for w in self._ocr_words)
                self._add_indicator(
                    title="No Native Text Layer — OCR Applied",
                    description=(
                        "This PDF contains no extractable text layer. Genuine bank statements are "
                        "digitally generated and always embed a searchable text layer. "
                        "An image-only document suggests it was printed and re-scanned — a common "
                        "technique to remove digital metadata. OCR has been applied to extract text "
                        "for further analysis."
                    ),
                    severity=IndicatorSeverity.MEDIUM,
                    details=f"0 native chars; OCR extracted ~{ocr_char_count} chars across {len(self.doc)} pages.",
                    confidence=80.0,
                )
                self.metadata_entries.append(MetadataEntry(
                    field="Text Layer Present",
                    original_text="No (image-only)",
                    new_text=f"OCR: ~{ocr_char_count} chars",
                    status="annotation",
                ))
            else:
                # No native text and OCR unavailable / failed
                ocr_note = (
                    " OCR service is unavailable — content checks cannot run."
                    if self._ocr_service is not None
                    else " No OCR service configured — content checks cannot run."
                )
                self._add_indicator(
                    title="No Text Layer — Image-Only PDF",
                    description=(
                        "This PDF contains no extractable text. Genuine bank statements are digitally "
                        "generated by banking software and always embed a searchable text layer. "
                        "An image-only document suggests it was printed and re-scanned — a common "
                        "technique to remove digital metadata and editing traces before submission."
                        + ocr_note
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

    # ─── I-6. PDF Annotation / Whitebox Overlay Analysis ────────────────────

    def analyze_annotations(self):
        """Detect white-rectangle PDF annotations used to cover and replace original text.

        A common editing technique is to place an opaque white box over original text
        and then layer new text on top — creating the visual appearance of a change
        while leaving evidence in the PDF annotation/appearance stream.
        """
        whitebox_pages: List[int] = []
        text_annot_pages: List[int] = []
        whitebox_highlights: List[HighlightBox] = []
        text_annot_highlights: List[HighlightBox] = []
        total_annots = 0

        for page_num, page in enumerate(self.doc, start=1):
            pw, ph = page.rect.width, page.rect.height
            annots = page.annots()
            if annots is None:
                continue
            for annot in annots:
                total_annots += 1
                annot_type = annot.type[1] if annot.type else ""
                rect = annot.rect

                # Square / Rectangle annotations that are filled white are the classic
                # "whiteout box" technique
                if annot_type in ("Square", "FreeText", "Redact"):
                    colors = annot.colors
                    fill = colors.get("fill") if colors else None
                    # White fill: (1, 1, 1) in RGB
                    if fill and all(abs(c - 1.0) < 0.05 for c in fill[:3]):
                        whitebox_pages.append(page_num)
                        whitebox_highlights.append(HighlightBox(
                            page=page_num,
                            x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1,
                            label="Whiteout box",
                            page_width=pw, page_height=ph,
                        ))

                # FreeText annotations with content are used to overlay replacement values
                if annot_type == "FreeText":
                    content = annot.info.get("content", "") or ""
                    if re.search(r'\d+\.\d{2}', content):
                        text_annot_pages.append(page_num)
                        text_annot_highlights.append(HighlightBox(
                            page=page_num,
                            x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1,
                            label=f"Annotation: {content[:40]}",
                            page_width=pw, page_height=ph,
                        ))

        if whitebox_pages:
            self._add_indicator(
                title="White Rectangle Annotations (Whiteout Boxes)",
                description=(
                    f"White-filled rectangular annotation(s) found on page(s) "
                    f"{sorted(set(whitebox_pages))}. This is the digital equivalent of correction "
                    "fluid — a classic technique to cover original bank figures and paste new values "
                    "on top. Genuine bank PDFs never contain opaque overlay annotations."
                ),
                severity=IndicatorSeverity.HIGH,
                details=f"Affected pages: {sorted(set(whitebox_pages))} | Total annotations: {total_annots}",
                confidence=92.0,
                highlights=whitebox_highlights,
            )

        if text_annot_pages:
            self._add_indicator(
                title="Numeric Values in PDF Annotations",
                description=(
                    f"FreeText annotation(s) containing monetary amounts found on page(s) "
                    f"{sorted(set(text_annot_pages))}. Amounts embedded in annotations sit "
                    "outside the main content stream, indicating values were added post-generation."
                ),
                severity=IndicatorSeverity.HIGH,
                details=f"Affected pages: {sorted(set(text_annot_pages))}",
                confidence=89.0,
                highlights=text_annot_highlights,
            )

        if not whitebox_pages and not text_annot_pages and total_annots > 0:
            self.metadata_entries.append(MetadataEntry(
                field="PDF Annotations",
                original_text=f"{total_annots} annotation(s)",
                new_text="Non-whitebox annotations present",
                status="annotation",
            ))
        elif total_annots == 0:
            self.metadata_entries.append(MetadataEntry(
                field="PDF Annotations",
                original_text="None",
                new_text=None,
                status="match",
            ))

    def analyze_universal(self) -> DocumentMetadata:
        """Run all Part I universal checks applicable to any PDF document.

        Returns the extracted DocumentMetadata for use in the final result.
        """
        metadata = self.analyze_metadata()
        self.analyze_document_type()
        self.analyze_fonts()
        self.analyze_text_layers()
        self.analyze_images()
        self.analyze_structure()
        self.analyze_annotations()
        return metadata

    # ═══════════════════════════════════════════════════════════════════════
    # PART II — CONTENT-BASED CHECKS  (bank-statement-specific)
    # Parse the extracted text for financial logic errors, implausible numeric
    # patterns, and fabricated transaction data.  Skipped automatically when
    # the document has no extractable text layer.
    # ═══════════════════════════════════════════════════════════════════════

    # ─── II-1. Financial Content Entry Point ─────────────────────────────────

    def analyze_financial_content(self):
        """Heuristic analysis of statement text for bank-statement-specific red flags."""
        if self._is_image_only:
            # No native text and no OCR results available
            for field in [
                "Balance Math Check", "Rounded Deposits Check",
                "Account Number Consistency", "Everyday Expense Categories",
                "Weekend Transaction Check", "Column Alignment Check",
                "Benford's Law Check", "Duplicate Transaction Check",
                "Transaction Date Ordering", "Opening/Closing Balance Continuity",
            ]:
                self.metadata_entries.append(MetadataEntry(
                    field=field,
                    original_text="N/A",
                    new_text="OCR required",
                    status="annotation",
                ))
            return

        text = self._get_text_for_analysis()
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
        # ── New algorithms ─────────────────────────────────────────────────────
        self._check_benfords_law(text)
        self._check_duplicate_transactions(text)
        self._check_transaction_date_ordering(text)
        self._check_opening_closing_balance(text)
        self._check_uniform_transaction_intervals(text)
        self._check_implausible_income_expense_ratio(text)

    def _check_running_balance_math(self, text: str):
        """Verify that running balances add up (debit/credit → new balance)."""
        line_pattern = re.compile(
            r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
        )
        errors = 0
        checked = 0
        error_amounts: List[str] = []  # balance values of failing rows for highlight search

        for line in text.splitlines():
            m = line_pattern.search(line)
            if not m:
                continue
            try:
                a = float(m.group(1).replace(',', ''))
                b = float(m.group(2).replace(',', ''))
                c = float(m.group(3).replace(',', ''))
                if abs((a + b) - c) < 0.02 or abs((a - b) - c) < 0.02:
                    checked += 1
                elif checked > 0:
                    errors += 1
                    # Record the balance value (third number) to locate the row
                    error_amounts.append(m.group(3))
            except Exception:
                pass

        if checked >= 3 and errors >= 2:
            highlights: List[HighlightBox] = []
            for amt in error_amounts[:5]:
                highlights.extend(self._search_all_pages(amt, f"Balance error: {amt}"))
            self._add_indicator(
                title="Running Balance Math Errors",
                description=f"Mathematical verification of transaction amounts against running balances found {errors} inconsistenc{'y' if errors == 1 else 'ies'}. Legitimate statements always balance exactly — errors indicate values were manually altered.",
                severity=IndicatorSeverity.HIGH,
                details=f"Checked {checked + errors} rows, {errors} failed balance verification",
                confidence=88.0,
                highlights=highlights,
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
        """Detect suspiciously round or repeated deposit amounts.

        Only scans lines that look like transaction rows (contain a date) to
        avoid counting amounts in boilerplate footers, legal disclaimers, or
        deposit-insurance notices (e.g. "insured up to S$100,000 per depositor").
        """
        # Date pattern: DD/MM/YYYY, DD-MM-YYYY, DD MMM YYYY, MMM DD YYYY, etc.
        date_re = re.compile(
            r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'
            r'|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b'
            r'|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            re.IGNORECASE,
        )
        transaction_lines = [ln for ln in text.splitlines() if date_re.search(ln)]
        # If no transaction lines found (e.g. OCR text lacks line breaks), skip
        # the check entirely — results would be unreliable.
        if not transaction_lines:
            return
        scan_text = "\n".join(transaction_lines)

        amounts = re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b', scan_text)
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
            highlights: List[HighlightBox] = []
            for v, _ in highly_repeated[:3]:
                # Search for the formatted amount string e.g. "5,000.00"
                fmt = f"{v:,.2f}"
                highlights.extend(self._search_all_pages(fmt, f"Repeated amount: {fmt}"))
            self._add_indicator(
                title="Identical Deposit Amounts Repeated",
                description=f"Certain amounts appear {highly_repeated[0][1]}+ times identically. While recurring salaries are normal, multiple large identical amounts suggest fabricated data.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Repeated: {[(f'${v:,.2f} × {c}') for v, c in highly_repeated[:5]]}",
                confidence=70.0,
                highlights=highlights,
            )

    def _check_account_number_consistency(self, text: str):
        """Detect different account numbers appearing across pages."""
        # Account numbers: 8–17 digit sequences near keywords
        pattern = re.compile(
            r'(?:account\s*(?:number|no\.?|#)?|acct\.?)\s*[:\-]?\s*[\*xX]*(\d[\d\s\-]{6,18}\d)',
            re.IGNORECASE,
        )
        raw: List[str] = []
        for m in pattern.finditer(text):
            num = re.sub(r'[\s\-]', '', m.group(1))
            if 8 <= len(num) <= 17:
                raw.append(num)

        # Deduplicate: if one number is a prefix of another (greedy regex sometimes
        # captures 1-2 extra trailing digits), keep the shorter canonical form.
        raw_unique = sorted(set(raw))
        found: set = set()
        for n in raw_unique:
            # Skip if a shorter version of this number is already in found
            if any(n.startswith(existing) and len(n) - len(existing) <= 2
                   for existing in found):
                continue
            # Replace any longer version already in found that this is a prefix of
            found = {e for e in found
                     if not (e.startswith(n) and len(e) - len(n) <= 2)}
            found.add(n)

        self.metadata_entries.append(MetadataEntry(
            field="Account Numbers Found",
            original_text=str(len(found)),
            new_text=None,
            status="suspicious" if len(found) > 1 else "match",
        ))

        if len(found) > 2:
            # Allow up to 2 accounts — combined statements (e.g. savings + SRS,
            # or current + credit card) are common and legitimate.
            highlights: List[HighlightBox] = []
            for num in found:
                highlights.extend(self._search_all_pages(num, f"Account: ***{num[-4:]}"))
            self._add_indicator(
                title="Multiple Different Account Numbers Detected",
                description=f"Found {len(found)} distinct account numbers in a single statement. While combined statements may cover 2 accounts, more than 2 suggests pages from different documents were merged.",
                severity=IndicatorSeverity.HIGH,
                details=f"Account numbers (masked): {['***' + n[-4:] for n in found]}",
                confidence=89.0,
                highlights=highlights,
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
            highlights: List[HighlightBox] = []
            for d in weekend_txns[:6]:
                highlights.extend(self._search_all_pages(d, f"Weekend txn: {d}"))
            self._add_indicator(
                title="Multiple Transactions on Weekends",
                description=f"{len(weekend_txns)} transactions dated on weekends. Bank-posted transactions (ACH, wire, direct deposit) typically do not process on Saturdays or Sundays. A high count suggests backdated or fabricated entries.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Weekend dates: {weekend_txns[:8]}",
                confidence=67.0,
                highlights=highlights,
            )

        if holiday_txns:
            highlights = []
            for d in holiday_txns[:4]:
                highlights.extend(self._search_all_pages(d, f"Bank holiday txn: {d}"))
            self._add_indicator(
                title="Transactions Dated on Bank Holidays",
                description=f"Transactions found on known US bank holidays: {holiday_txns}. Banks do not process ACH or wire transfers on federal holidays.",
                severity=IndicatorSeverity.MEDIUM,
                details=f"Holiday dates: {holiday_txns}",
                confidence=72.0,
                highlights=highlights,
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
        """Detect sample/draft/void watermark text.

        Excludes legitimate banking phrases that contain these words:
        'demand draft', 'bank draft', 'draft account', 'overdraft',
        'test drive', 'void cheque' (some banks print this legitimately), etc.
        """
        # Remove known-legitimate multi-word phrases before scanning for keywords
        scrubbed = re.sub(
            r'\b(?:demand\s+draft|bank\s+draft|draft\s+account|over\s*draft|'
            r'test\s+drive|test\s+user|void\s+cheque|void\s+check)\b',
            ' ', text_lower
        )
        patterns = [r'\bsample\b', r'\bdraft\b', r'\bvoid\b', r'\bspecimen\b']
        found = [p.strip(r'\b') for p in patterns if re.search(p, scrubbed)]
        if found:
            highlights: List[HighlightBox] = []
            for kw in found:
                highlights.extend(self._search_all_pages(kw.upper(), f"Watermark: {kw.upper()}"))
                highlights.extend(self._search_all_pages(kw.capitalize(), f"Watermark: {kw}"))
            self._add_indicator(
                title="Sample / Draft Watermark Text Detected",
                description="Words like 'SAMPLE', 'DRAFT', 'VOID', or 'SPECIMEN' found — indicates a template document presented as genuine.",
                severity=IndicatorSeverity.HIGH,
                details=f"Keywords: {found}",
                confidence=85.0,
                highlights=highlights,
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

    def _check_benfords_law(self, text: str):
        """Apply Benford's Law to first digits of transaction amounts.

        Genuine financial data follows Benford's distribution — forged statements
        where figures are manually invented tend to deviate significantly because
        humans unconsciously over-use mid-range digits (5, 6, 7) and avoid 1.
        """
        raw_amounts = re.findall(r'\b([1-9][\d,]*\.\d{2})\b', text)
        first_digits: List[int] = []
        for a in raw_amounts:
            try:
                v = float(a.replace(',', ''))
                if v >= 10.0:  # Ignore sub-$10 amounts — too common as fees/charges
                    first_digits.append(int(str(int(v))[0]))
            except Exception:
                pass

        if len(first_digits) < BENFORD_MIN_SAMPLES:
            return

        total = len(first_digits)
        digit_counts = Counter(first_digits)
        deviating: List[Tuple[int, float, float]] = []

        for d in range(1, 10):
            observed = digit_counts.get(d, 0) / total
            expected = BENFORD_EXPECTED[d]
            if abs(observed - expected) > BENFORD_DEVIATION_THRESHOLD:
                deviating.append((d, round(observed * 100, 1), round(expected * 100, 1)))

        if len(deviating) >= 3:
            detail_parts = [f"digit {d}: {obs}% observed vs {exp}% expected" for d, obs, exp in deviating]
            self._add_indicator(
                title="Benford's Law Violation",
                description=(
                    f"First-digit frequency analysis of {total} transaction amounts deviates "
                    f"significantly from Benford's Law on {len(deviating)} digits. "
                    "Genuine financial records naturally follow this logarithmic distribution; "
                    "fabricated figures invented by humans consistently violate it."
                ),
                severity=IndicatorSeverity.HIGH,
                details=" | ".join(detail_parts),
                confidence=82.0,
            )
        elif len(deviating) >= 2:
            self._add_indicator(
                title="Partial Benford's Law Deviation",
                description=(
                    f"First-digit analysis of {total} amounts shows deviation on {len(deviating)} digits. "
                    "May indicate partially fabricated transaction data."
                ),
                severity=IndicatorSeverity.MEDIUM,
                details=" | ".join(
                    f"digit {d}: {obs}% vs {exp}% expected"
                    for d, obs, exp in deviating
                ),
                confidence=65.0,
            )

        self.metadata_entries.append(MetadataEntry(
            field="Benford's Law Check",
            original_text=f"{total} amounts sampled",
            new_text=f"{len(deviating)} digit(s) deviate" if deviating else "Pass",
            status="suspicious" if len(deviating) >= 2 else "match",
        ))

    def _check_duplicate_transactions(self, text: str):
        """Detect copy-pasted duplicate transaction rows.

        Fraudsters often inflate account activity by duplicating genuine transaction
        lines verbatim, forgetting that each transaction should be unique.
        """
        # Normalise lines: keep only those with a monetary amount and enough content
        candidate_lines = [
            re.sub(r'\s+', ' ', l.strip())
            for l in text.splitlines()
            if re.search(r'\d+\.\d{2}', l) and len(l.strip()) > 25
        ]

        counts = Counter(candidate_lines)
        exact_dupes = [(line, cnt) for line, cnt in counts.items() if cnt >= 3]
        near_dupes_count = 0

        # Near-duplicate check: same amount, same description ignoring date
        amount_desc_pairs: Dict[str, int] = {}
        for line in candidate_lines:
            # Strip leading date-like tokens (MM/DD, DD-MM-YYYY, etc.)
            stripped = re.sub(r'^\s*\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?\s*', '', line)
            amount_desc_pairs[stripped] = amount_desc_pairs.get(stripped, 0) + 1
        near_dupes = [(d, c) for d, c in amount_desc_pairs.items() if c >= 3 and len(d) > 20]
        near_dupes_count = len(near_dupes)

        if exact_dupes:
            highlights: List[HighlightBox] = []
            for line, _ in exact_dupes[:3]:
                # Search for a distinctive middle fragment (skip leading date, cap length)
                fragment = re.sub(r'^\S+\s+', '', line)[:40].strip()
                if len(fragment) >= 6:
                    highlights.extend(self._search_all_pages(fragment, "Duplicate row"))
            self._add_indicator(
                title="Exact Duplicate Transaction Rows",
                description=(
                    f"{len(exact_dupes)} transaction line(s) appear {exact_dupes[0][1]}+ times verbatim. "
                    "Genuine bank-generated statements never repeat identical transaction rows — "
                    "this is a clear sign of copy-paste fabrication."
                ),
                severity=IndicatorSeverity.HIGH,
                details=f"Example duplicate: \"{exact_dupes[0][0][:80]}\"",
                confidence=91.0,
                highlights=highlights,
            )
        elif near_dupes_count >= 2:
            self._add_indicator(
                title="Near-Duplicate Transactions Detected",
                description=(
                    f"{near_dupes_count} transaction(s) share identical amounts and descriptions "
                    "across different dates. Recurring amounts are normal (e.g. salary) but "
                    "multiple near-identical entries suggest templated fabrication."
                ),
                severity=IndicatorSeverity.MEDIUM,
                details=f"Repeated patterns: {near_dupes_count}",
                confidence=68.0,
            )

        self.metadata_entries.append(MetadataEntry(
            field="Duplicate Transaction Check",
            original_text="None expected",
            new_text=f"{len(exact_dupes)} exact duplicate(s)" if exact_dupes else "Pass",
            status="mismatch" if exact_dupes else "match",
        ))

    def _check_transaction_date_ordering(self, text: str):
        """Detect transactions that appear out of chronological order.

        Genuine bank statements list transactions in strict date order (oldest to
        newest or vice versa). Out-of-order entries indicate rows were inserted or
        rearranged after the fact.
        """
        date_pattern = re.compile(
            r'\b((?:0?[1-9]|1[0-2])[\/\-](?:0?[1-9]|[12]\d|3[01])(?:[\/\-](?:20\d{2}|\d{2}))?)\b'
        )
        parsed_dates: List[date] = []

        for line in text.splitlines():
            if not re.search(r'\d+\.\d{2}', line):
                continue
            m = date_pattern.search(line)
            if not m:
                continue
            raw = m.group(1)
            parts = re.split(r'[\/\-]', raw)
            try:
                month, day = int(parts[0]), int(parts[1])
                year = int(parts[2]) if len(parts) == 3 else datetime.now().year
                if year < 100:
                    year += 2000
                parsed_dates.append(date(year, month, day))
            except Exception:
                pass

        if len(parsed_dates) < 6:
            return

        # Detect inversions relative to the predominant ordering direction
        asc_violations = sum(
            1 for i in range(1, len(parsed_dates)) if parsed_dates[i] < parsed_dates[i - 1]
        )
        desc_violations = sum(
            1 for i in range(1, len(parsed_dates)) if parsed_dates[i] > parsed_dates[i - 1]
        )
        violations = min(asc_violations, desc_violations)

        if violations >= 3:
            self._add_indicator(
                title="Out-of-Order Transaction Dates",
                description=(
                    f"{violations} date ordering violation(s) found across {len(parsed_dates)} "
                    "dated transaction rows. Bank-generated statements always present transactions "
                    "in strict chronological order; inversions indicate rows were inserted or "
                    "rearranged after generation."
                ),
                severity=IndicatorSeverity.HIGH,
                details=f"Ordering violations: {violations} / {len(parsed_dates)} rows",
                confidence=85.0,
            )
        elif violations >= 1:
            self._add_indicator(
                title="Transaction Date Sequence Anomaly",
                description=f"Minor date ordering irregularity detected ({violations} violation(s)).",
                severity=IndicatorSeverity.LOW,
                details=f"Ordering violations: {violations} / {len(parsed_dates)} rows",
                confidence=55.0,
            )

        self.metadata_entries.append(MetadataEntry(
            field="Transaction Date Ordering",
            original_text="Sequential expected",
            new_text=f"{violations} violation(s)" if violations else "Pass",
            status="suspicious" if violations >= 3 else "match",
        ))

    def _check_opening_closing_balance(self, text: str):
        """Verify that closing balance from one period carries to the next page.

        In multi-page statements the closing balance printed on page N should equal
        the opening balance on page N+1. Mismatches expose page-swapping fraud where
        pages from different genuine statements are spliced together.
        """
        pages_text = [page.get_text() for page in self.doc]
        if len(pages_text) < 2:
            return

        closing_pattern = re.compile(
            r'(?:closing|ending|end)\s*balance[^\d]*([\d,]+\.\d{2})', re.IGNORECASE
        )
        opening_pattern = re.compile(
            r'(?:opening|beginning|start(?:ing)?|brought\s+forward|b/?f)\s*balance[^\d]*([\d,]+\.\d{2})',
            re.IGNORECASE,
        )

        mismatches = 0
        for i in range(len(pages_text) - 1):
            close_m = closing_pattern.search(pages_text[i])
            open_m = opening_pattern.search(pages_text[i + 1])
            if not close_m or not open_m:
                continue
            try:
                closing_val = float(close_m.group(1).replace(',', ''))
                opening_val = float(open_m.group(1).replace(',', ''))
                if abs(closing_val - opening_val) > 0.02:
                    mismatches += 1
            except Exception:
                pass

        if mismatches >= 1:
            self._add_indicator(
                title="Opening/Closing Balance Mismatch Across Pages",
                description=(
                    f"Closing balance on {mismatches} page(s) does not match the opening balance "
                    "on the following page. In a genuine statement these values must be identical — "
                    "a mismatch proves pages were taken from different statements and spliced together."
                ),
                severity=IndicatorSeverity.HIGH,
                details=f"Page-to-page balance continuity failures: {mismatches}",
                confidence=93.0,
            )
            self.metadata_entries.append(MetadataEntry(
                field="Opening/Closing Balance Continuity",
                original_text="Match expected",
                new_text=f"{mismatches} mismatch(es)",
                status="mismatch",
            ))
        else:
            self.metadata_entries.append(MetadataEntry(
                field="Opening/Closing Balance Continuity",
                original_text="Match",
                new_text=None,
                status="match",
            ))

    def _check_uniform_transaction_intervals(self, text: str):
        """Detect transactions occurring at suspiciously regular time intervals.

        Real spending is irregular. When a fraudster fabricates a statement by
        assigning dates to invented transactions, they often space them out too
        evenly (every 7, 14, or 30 days exactly), which is statistically implausible
        for genuine transaction data.
        """
        date_pattern = re.compile(
            r'\b((?:0?[1-9]|1[0-2])[\/\-](?:0?[1-9]|[12]\d|3[01])(?:[\/\-](?:20\d{2}|\d{2}))?)\b'
        )
        txn_dates: List[date] = []

        for line in text.splitlines():
            if not re.search(r'\d+\.\d{2}', line):
                continue
            m = date_pattern.search(line)
            if not m:
                continue
            parts = re.split(r'[\/\-]', m.group(1))
            try:
                month, day = int(parts[0]), int(parts[1])
                year = int(parts[2]) if len(parts) == 3 else datetime.now().year
                if year < 100:
                    year += 2000
                txn_dates.append(date(year, month, day))
            except Exception:
                pass

        unique_dates = sorted(set(txn_dates))
        if len(unique_dates) < 8:
            return

        gaps = [(unique_dates[i + 1] - unique_dates[i]).days for i in range(len(unique_dates) - 1)]
        if not gaps:
            return

        mean_gap = sum(gaps) / len(gaps)
        variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
        std_dev = math.sqrt(variance)

        # A coefficient of variation < 0.15 means gaps are suspiciously uniform
        if mean_gap > 0 and (std_dev / mean_gap) < 0.15 and len(gaps) >= 7:
            self._add_indicator(
                title="Suspiciously Uniform Transaction Intervals",
                description=(
                    f"Transactions are spaced at nearly identical intervals "
                    f"(avg {mean_gap:.1f} days, std dev {std_dev:.1f} days — CV {std_dev/mean_gap:.2f}). "
                    "Real spending patterns show high variance in timing; artificial regularity "
                    "strongly suggests dates were assigned programmatically or manually to "
                    "fabricated transactions."
                ),
                severity=IndicatorSeverity.MEDIUM,
                details=f"Mean gap: {mean_gap:.1f} days | Std dev: {std_dev:.1f} | {len(gaps)} intervals checked",
                confidence=75.0,
            )

    def _check_implausible_income_expense_ratio(self, text: str):
        """Flag statements where deposits vastly outweigh any outflows.

        Fraudsters crafting a statement to show high income often forget to include
        realistic outflow transactions, resulting in a balance that only grows with
        no recognisable recurring expenses. This check combines the income volume
        check with outflow analysis for a combined signal.
        """
        if self._is_image_only:
            return

        # Collect credit-side and debit-side amounts from lines containing directional keywords
        credit_amounts: List[float] = []
        debit_amounts: List[float] = []

        for line in text.splitlines():
            line_lower = line.lower()
            amount_matches = re.findall(r'\b([\d,]+\.\d{2})\b', line)
            amounts = []
            for a in amount_matches:
                try:
                    amounts.append(float(a.replace(',', '')))
                except Exception:
                    pass
            if not amounts:
                continue
            largest = max(amounts)

            if any(kw in line_lower for kw in ['deposit', 'credit', 'salary', 'payroll', 'transfer in', 'received']):
                credit_amounts.append(largest)
            elif any(kw in line_lower for kw in ['debit', 'withdrawal', 'payment', 'purchase', 'charge', 'fee']):
                debit_amounts.append(largest)

        if len(credit_amounts) < 3 or len(debit_amounts) < 1:
            return

        total_credits = sum(credit_amounts)
        total_debits = sum(debit_amounts)

        if total_debits == 0:
            return

        ratio = total_credits / total_debits
        if ratio > 15.0 and total_credits > 5000:
            self._add_indicator(
                title="Implausible Income-to-Expense Ratio",
                description=(
                    f"Total credited amounts ({total_credits:,.2f}) are {ratio:.0f}× larger than "
                    f"total debited amounts ({total_debits:,.2f}). "
                    "Real bank statements show a balanced mix of income and expenses; "
                    "an extreme ratio suggests the statement was fabricated to inflate income "
                    "while omitting realistic daily spending."
                ),
                severity=IndicatorSeverity.MEDIUM,
                details=f"Credits: {total_credits:,.2f} | Debits: {total_debits:,.2f} | Ratio: {ratio:.1f}×",
                confidence=72.0,
            )

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _search_all_pages(self, query: str, label: str, max_per_page: int = 3) -> List[HighlightBox]:
        """Search every page for `query` and return bounding boxes.

        Uses PyMuPDF's page.search_for() on PDFs with a native text layer.
        Falls back to _ocr_search_highlights() for image-only PDFs after OCR.
        """
        results: List[HighlightBox] = []
        query = query.strip()
        if not query or len(query) < 3:
            return results

        # For image-only PDFs that have been OCR-ed, use the OCR word list
        if self._native_text_empty and self._ocr_words:
            return self._ocr_search_highlights(query, label, max_per_page)

        for page_num, page in enumerate(self.doc, start=1):
            pw, ph = page.rect.width, page.rect.height
            try:
                rects = page.search_for(query)
            except Exception:
                continue
            for rect in rects[:max_per_page]:
                if rect.is_empty or rect.is_infinite:
                    continue
                results.append(HighlightBox(
                    page=page_num,
                    x0=rect.x0, y0=rect.y0,
                    x1=rect.x1, y1=rect.y1,
                    label=label,
                    page_width=pw, page_height=ph,
                ))
        return results

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
        # Part I: universal — applicable to any PDF document type
        metadata = self.analyze_universal()
        # Part II: content-based — bank-statement-specific heuristics
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
