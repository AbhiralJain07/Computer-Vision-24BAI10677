"""Computer-vision preprocessing operations."""

import cv2
import numpy as np

from .config import ScannerConfig


def to_grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def detect_edges(image: np.ndarray, config: ScannerConfig) -> np.ndarray:
    gray = to_grayscale(image)
    blurred = cv2.GaussianBlur(gray, (config.blur_kernel, config.blur_kernel), 0)
    edges = cv2.Canny(blurred, config.canny_low, config.canny_high)
    kernel = np.ones((3, 3), dtype=np.uint8)
    return cv2.dilate(edges, kernel, iterations=1)


def enhance_document(image: np.ndarray, config: ScannerConfig) -> np.ndarray:
    gray = to_grayscale(image)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)

    block_size = config.binary_block_size
    if block_size % 2 == 0:
        block_size += 1

    return cv2.adaptiveThreshold(
        contrasted,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        config.binary_c,
    )

