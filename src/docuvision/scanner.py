"""Document detection and perspective correction."""

from dataclasses import dataclass

import cv2
import numpy as np

from .config import ScannerConfig
from .io_utils import resize_to_height
from .preprocessing import detect_edges, enhance_document


@dataclass
class ScanResult:
    original: np.ndarray
    resized: np.ndarray
    edges: np.ndarray
    contour: np.ndarray
    warped: np.ndarray
    enhanced: np.ndarray
    used_fallback: bool


def order_points(points: np.ndarray) -> np.ndarray:
    pts = points.reshape(4, 2).astype("float32")
    point_sum = pts.sum(axis=1)
    point_diff = np.diff(pts, axis=1)

    ordered = np.zeros((4, 2), dtype="float32")
    ordered[0] = pts[np.argmin(point_sum)]
    ordered[2] = pts[np.argmax(point_sum)]
    ordered[1] = pts[np.argmin(point_diff)]
    ordered[3] = pts[np.argmax(point_diff)]
    return ordered


def four_point_transform(image: np.ndarray, points: np.ndarray, output_width: int) -> np.ndarray:
    rect = order_points(points)
    top_left, top_right, bottom_right, bottom_left = rect

    width_a = np.linalg.norm(bottom_right - bottom_left)
    width_b = np.linalg.norm(top_right - top_left)
    max_width = max(int(width_a), int(width_b), 1)

    height_a = np.linalg.norm(top_right - bottom_right)
    height_b = np.linalg.norm(top_left - bottom_left)
    max_height = max(int(height_a), int(height_b), 1)

    aspect = max_height / float(max_width)
    output_height = max(int(output_width * aspect), 1)

    destination = np.array(
        [
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (output_width, output_height))


def _fallback_contour(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    margin_x = int(width * 0.04)
    margin_y = int(height * 0.04)
    return np.array(
        [
            [[margin_x, margin_y]],
            [[width - margin_x, margin_y]],
            [[width - margin_x, height - margin_y]],
            [[margin_x, height - margin_y]],
        ],
        dtype=np.int32,
    )


def find_document_contour(edges: np.ndarray, config: ScannerConfig) -> tuple[np.ndarray, bool]:
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = edges.shape[0] * edges.shape[1]
    min_area = image_area * config.min_document_area_ratio

    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(contour) < min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        approximated = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approximated) == 4:
            return approximated, False

    return _fallback_contour(edges), True


def scan_document(image: np.ndarray, config: ScannerConfig | None = None) -> ScanResult:
    cfg = config or ScannerConfig()
    resized, scale = resize_to_height(image, cfg.resize_height)
    edges = detect_edges(resized, cfg)
    contour, used_fallback = find_document_contour(edges, cfg)

    contour_on_original = contour.astype("float32") / scale
    warped = four_point_transform(image, contour_on_original, cfg.output_width)
    enhanced = enhance_document(warped, cfg)

    return ScanResult(
        original=image,
        resized=resized,
        edges=edges,
        contour=contour,
        warped=warped,
        enhanced=enhanced,
        used_fallback=used_fallback,
    )

