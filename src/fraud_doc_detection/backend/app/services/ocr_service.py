"""
OCR service for image-only PDF pages.

Primary backend: Apple Vision framework (VNRecognizeTextRequest) — no external
service required, runs fully on-device with hardware acceleration on Apple Silicon.

Fallback HTTP backend: PaddleOCR HubServing endpoint (POST /predict/ocr_system).
Activated when the PADDLE_OCR_URL environment variable is set and the Vision
framework import fails.

Bounding boxes from both backends are returned in PDF points (origin top-left,
y downward) so they map directly onto fitz page coordinates.
"""
import base64
import os
from dataclasses import dataclass
from typing import List, Optional

import fitz  # PyMuPDF

PADDLE_OCR_URL = os.getenv("PADDLE_OCR_URL", "")
DEFAULT_DPI = 150


@dataclass
class OCRWord:
    text: str
    x0: float   # PDF points
    y0: float
    x1: float
    y1: float
    page: int   # 1-based
    confidence: float


# ─── Vision framework backend ────────────────────────────────────────────────

def _vision_available() -> bool:
    try:
        import objc  # noqa: F401
        import Vision  # noqa: F401
        return True
    except ImportError:
        return False


def _ocr_page_vision(page: fitz.Page, page_num: int, dpi: int = DEFAULT_DPI) -> List[OCRWord]:
    """Run OCR on a single page using Apple Vision framework."""
    import Vision
    import Quartz
    import objc

    # Render the page to a PNG bytes buffer
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix)
    img_bytes = pix.tobytes("png")

    pw = page.rect.width   # PDF points
    ph = page.rect.height

    # Build a CGImage from the PNG bytes
    data_provider = Quartz.CGDataProviderCreateWithData(None, img_bytes, len(img_bytes), None)
    cg_image = Quartz.CGImageCreateWithPNGDataProvider(data_provider, None, False, Quartz.kCGRenderingIntentDefault)
    if cg_image is None:
        return []

    results: List[OCRWord] = []
    done = [False]

    def handler(request, error):
        if error:
            done[0] = True
            return
        for obs in request.results():
            # obs is a VNRecognizedTextObservation
            candidates = obs.topCandidates_(1)
            if not candidates:
                continue
            candidate = candidates[0]
            text = str(candidate.string())
            confidence = float(candidate.confidence())

            # Vision bbox: normalised coordinates, origin BOTTOM-LEFT
            bbox = obs.boundingBox()  # CGRect
            nx, ny, nw, nh = bbox.origin.x, bbox.origin.y, bbox.size.width, bbox.size.height

            # Convert normalised Vision coords → PDF points
            # Vision: (0,0) = bottom-left; fitz: (0,0) = top-left
            x0 = nx * pw
            y1 = (1.0 - ny) * ph
            x1 = (nx + nw) * pw
            y0 = (1.0 - ny - nh) * ph

            results.append(OCRWord(
                text=text, x0=x0, y0=y0, x1=x1, y1=y1,
                page=page_num, confidence=confidence,
            ))
        done[0] = True

    req = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler)
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(True)

    handler_obj = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
    handler_obj.performRequests_error_([req], None)

    return results


# ─── PaddleOCR HTTP fallback ──────────────────────────────────────────────────

def _ocr_page_paddle(page: fitz.Page, page_num: int, dpi: int = DEFAULT_DPI, endpoint: str = "") -> List[OCRWord]:
    """Run OCR via PaddleOCR HubServing HTTP endpoint."""
    import httpx

    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix)
    b64 = base64.b64encode(pix.tobytes("png")).decode()

    try:
        resp = httpx.post(endpoint, json={"images": [b64]}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    words: List[OCRWord] = []
    scale = 72.0 / dpi
    for item in (data.get("results") or [[]])[0]:
        text = (item.get("text") or "").strip()
        region = item.get("text_region") or []
        if not text or len(region) < 2:
            continue
        xs = [pt[0] * scale for pt in region]
        ys = [pt[1] * scale for pt in region]
        words.append(OCRWord(
            text=text, x0=min(xs), y0=min(ys),
            x1=max(xs), y1=max(ys),
            page=page_num, confidence=float(item.get("confidence") or 1.0),
        ))
    return words


# ─── Public OCRService class ──────────────────────────────────────────────────

class OCRService:
    """Unified OCR service.

    Uses Apple Vision framework by default (on-device, no server required).
    Falls back to PaddleOCR HTTP if PADDLE_OCR_URL is set and Vision is unavailable.
    """

    def __init__(self):
        self._use_vision = _vision_available()
        self._paddle_endpoint = (PADDLE_OCR_URL.rstrip("/") + "/predict/ocr_system") if PADDLE_OCR_URL else ""

    def is_available(self) -> bool:
        """Return True if at least one OCR backend is usable."""
        if self._use_vision:
            return True
        if self._paddle_endpoint:
            try:
                import httpx
                httpx.get(self._paddle_endpoint.rsplit("/predict", 1)[0], timeout=2)
                return True
            except Exception:
                return False
        return False

    def run_page(self, page: fitz.Page, page_num: int, dpi: int = DEFAULT_DPI) -> List[OCRWord]:
        """OCR a single page and return word-level bounding boxes in PDF points."""
        if self._use_vision:
            return _ocr_page_vision(page, page_num, dpi)
        if self._paddle_endpoint:
            return _ocr_page_paddle(page, page_num, dpi, self._paddle_endpoint)
        return []

    def run_document(self, doc: fitz.Document, dpi: int = DEFAULT_DPI) -> List[OCRWord]:
        """OCR all pages of an open fitz document."""
        all_words: List[OCRWord] = []
        for i, page in enumerate(doc):
            all_words.extend(self.run_page(page, page_num=i + 1, dpi=dpi))
        return all_words
