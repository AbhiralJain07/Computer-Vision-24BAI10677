"""Image input/output helpers."""

from pathlib import Path

import cv2
import numpy as np


def read_image(path: str | Path) -> np.ndarray:
    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image file: {image_path}")
    return image


def write_image(path: str | Path, image: np.ndarray) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(output_path), image)
    if not ok:
        raise ValueError(f"Unable to write image file: {output_path}")
    return output_path


def resize_to_height(image: np.ndarray, target_height: int) -> tuple[np.ndarray, float]:
    height, width = image.shape[:2]
    if height == target_height:
        return image.copy(), 1.0

    scale = target_height / float(height)
    resized = cv2.resize(image, (int(width * scale), target_height), interpolation=cv2.INTER_AREA)
    return resized, scale

