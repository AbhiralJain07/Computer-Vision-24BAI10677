"""Create a synthetic document photo for demo and testing."""

from pathlib import Path

import cv2
import numpy as np


def create_sample(output_path: str = "samples/sample_document.jpg") -> Path:
    canvas = np.full((900, 1200, 3), (42, 54, 68), dtype=np.uint8)
    noise = np.random.default_rng(7).normal(0, 8, canvas.shape).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    document = np.full((620, 440, 3), 245, dtype=np.uint8)
    cv2.putText(document, "DocuVision", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.45, (20, 20, 20), 3)
    cv2.putText(document, "Computer Vision Project", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (60, 60, 60), 2)

    y = 205
    for i in range(8):
        cv2.line(document, (50, y), (390 - (i % 3) * 45, y), (70, 70, 70), 2)
        y += 46

    cv2.rectangle(document, (50, 520), (390, 575), (20, 20, 20), 2)
    cv2.putText(document, "Quality: readable", (75, 555), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (20, 20, 20), 2)

    source = np.array([[0, 0], [439, 0], [439, 619], [0, 619]], dtype=np.float32)
    destination = np.array([[390, 95], [840, 160], [765, 790], [295, 695]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(document, matrix, (1200, 900))

    mask = cv2.warpPerspective(np.full(document.shape[:2], 255, dtype=np.uint8), matrix, (1200, 900))
    canvas[mask > 0] = warped[mask > 0]
    canvas = cv2.GaussianBlur(canvas, (3, 3), 0)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    return output


if __name__ == "__main__":
    print(create_sample())

