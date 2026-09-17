"""Document image quality metrics."""

from dataclasses import dataclass, asdict

import cv2
import numpy as np

from .config import QualityThresholds


@dataclass
class QualityReport:
    brightness: float
    contrast: float
    sharpness: float
    skew_degrees: float
    passed: bool
    messages: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _estimate_skew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=120)
    if lines is None:
        return 0.0

    angles = []
    for line in lines[:40]:
        rho, theta = line[0]
        angle = (theta * 180 / np.pi) - 90
        if -45 <= angle <= 45:
            angles.append(angle)
    if not angles:
        return 0.0
    return float(np.median(angles))


def analyze_quality(image: np.ndarray, thresholds: QualityThresholds | None = None) -> QualityReport:
    cfg = thresholds or QualityThresholds()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    skew = _estimate_skew(gray)

    messages: list[str] = []
    if sharpness < cfg.min_sharpness:
        messages.append("Image may be blurry; capture again or improve focus.")
    if contrast < cfg.min_contrast:
        messages.append("Low contrast detected; use stronger lighting or a darker background.")
    if brightness < cfg.min_brightness:
        messages.append("Image is too dark; increase illumination.")
    if brightness > cfg.max_brightness:
        messages.append("Image is overexposed; reduce glare.")
    if abs(skew) > cfg.max_skew_degrees:
        messages.append("Document is noticeably tilted; align the camera with the page.")

    passed = len(messages) == 0
    if passed:
        messages.append("Image quality is acceptable for document digitization.")

    return QualityReport(
        brightness=round(brightness, 2),
        contrast=round(contrast, 2),
        sharpness=round(sharpness, 2),
        skew_degrees=round(skew, 2),
        passed=passed,
        messages=messages,
    )

