"""
Shared image preprocessing utilities for OCR across the extraction
pipeline. Centralizing this means every OCR call point (IQAMA, names,
day-cell values) uses the same well-tested primitives instead of ad-hoc
per-call logic scattered across files.

HONEST NOTE FROM TESTING: these techniques (blue-ink isolation, adaptive
thresholding, morphological cleanup, upscaling) were validated empirically
against a real scanned/photographed timesheet. They measurably help with
borderline/light handwriting and reduce noise from the printed template,
but they do NOT make Tesseract reliably read fast cursive pen handwriting —
that is a fundamental limitation of a classical OCR engine, not something
preprocessing parameters can close. See OCREngine (services/ocr/) for the
documented upgrade path to a handwriting-capable Vision API engine.
"""
import cv2
import numpy as np
from PIL import Image

BLUE_DIFF_THRESHOLD = 20


def pil_to_cv(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def cv_to_pil(mat: np.ndarray) -> Image.Image:
    if len(mat.shape) == 2:
        return Image.fromarray(mat)
    return Image.fromarray(cv2.cvtColor(mat, cv2.COLOR_BGR2RGB))


def isolate_handwriting_ink(image: Image.Image, threshold: int = BLUE_DIFF_THRESHOLD) -> np.ndarray:
    """
    Separates blue handwritten ink from black printed template text/lines,
    rendering ink as black-on-white. Confirmed empirically to cleanly
    remove printed template interference (see pdf_page_template_service.py
    module docstring for testing notes).
    """
    mat = pil_to_cv(image)
    b, _, r = cv2.split(mat)
    diff = cv2.subtract(b.astype(np.int16), r.astype(np.int16))
    diff = np.clip(diff, 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    out = np.full(mat.shape[:2], 255, dtype=np.uint8)
    out[mask > 0] = 0
    return out


def denoise_and_clean(mask: np.ndarray, open_kernel: int = 2) -> np.ndarray:
    """Removes isolated speckle noise without eroding genuine strokes."""
    kernel = np.ones((open_kernel, open_kernel), np.uint8)
    inverted = 255 - mask  # morphology expects foreground=white
    cleaned = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, kernel)
    return 255 - cleaned


def deskew(mat: np.ndarray, max_angle: float = 8.0) -> np.ndarray:
    """
    Corrects mild rotation from photographed (non-flatbed) pages using
    the minimum-area bounding rectangle of dark pixels. Skipped entirely
    if the detected angle exceeds max_angle, since large "angles" from
    this method on sparse content (a short text crop) are usually noise,
    not real skew — applying them would do more harm than good.
    """
    coords = np.column_stack(np.where(mat < 200))
    if len(coords) < 20:
        return mat
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) > max_angle:
        return mat
    (h, w) = mat.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        mat, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255,
    )


def upscale(mat: np.ndarray, factor: float = 3.0) -> np.ndarray:
    return cv2.resize(mat, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def preprocess_for_handwritten_digits(image: Image.Image) -> Image.Image:
    """Pipeline for IQAMA/passport numbers: isolate ink -> denoise -> deskew -> upscale."""
    mask = isolate_handwriting_ink(image)
    mask = denoise_and_clean(mask, open_kernel=2)
    mask = deskew(mask)
    mask = upscale(mask, factor=3.0)
    return cv_to_pil(mask)


def preprocess_for_handwritten_text(image: Image.Image) -> Image.Image:
    """Pipeline for names/titles: same as digits but lighter denoising
    (names have finer strokes that aggressive opening can erase)."""
    mask = isolate_handwriting_ink(image)
    mask = deskew(mask)
    mask = upscale(mask, factor=2.5)
    return cv_to_pil(mask)


def preprocess_row_strip(image: Image.Image) -> Image.Image:
    """Pipeline for a full handwritten row (e.g. Total Hrs across all
    day-columns) — deskew matters more here since a wide strip amplifies
    the visible effect of any page rotation."""
    mask = isolate_handwriting_ink(image)
    mask = denoise_and_clean(mask, open_kernel=2)
    mask = deskew(mask, max_angle=5.0)
    mask = upscale(mask, factor=2.0)
    return cv_to_pil(mask)