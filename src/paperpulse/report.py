"""Visual and JSON report generation."""

import json
from pathlib import Path

import cv2
import numpy as np

from .io_utils import write_image
from .quality import QualityReport
from .scanner import ScanResult


def draw_detected_contour(result: ScanResult) -> np.ndarray:
    preview = result.resized.copy()
    cv2.drawContours(preview, [result.contour], -1, (0, 180, 0), 3)
    label = "fallback boundary" if result.used_fallback else "detected document"
    cv2.putText(preview, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 180, 0), 2)
    return preview


def _panel(title: str, image: np.ndarray, width: int = 420, height: int = 540) -> np.ndarray:
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    canvas = np.full((height + 48, width, 3), 245, dtype=np.uint8)
    canvas[48:, :] = resized
    cv2.putText(canvas, title, (14, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (30, 30, 30), 2)
    return canvas


def create_visual_report(result: ScanResult, quality: QualityReport, output_path: str | Path) -> Path:
    detection = draw_detected_contour(result)

    panels = [
        _panel("1. Input + contour", detection),
        _panel("2. Edge map", result.edges),
        _panel("3. Perspective corrected", result.warped),
        _panel("4. Enhanced output", result.enhanced),
    ]
    top = np.hstack(panels[:2])
    bottom = np.hstack(panels[2:])
    dashboard = np.vstack([top, bottom])

    footer = np.full((130, dashboard.shape[1], 3), 250, dtype=np.uint8)
    status = "PASS" if quality.passed else "REVIEW"
    cv2.putText(footer, f"Quality: {status}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)
    cv2.putText(
        footer,
        f"brightness={quality.brightness} contrast={quality.contrast} sharpness={quality.sharpness} skew={quality.skew_degrees}",
        (20, 73),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (40, 40, 40),
        2,
    )
    cv2.putText(footer, quality.messages[0][:105], (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1)
    return write_image(output_path, np.vstack([dashboard, footer]))


def save_json_report(quality: QualityReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(quality.to_dict(), indent=2), encoding="utf-8")
    return path

