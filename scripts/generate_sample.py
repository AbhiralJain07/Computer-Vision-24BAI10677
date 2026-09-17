"""Create synthetic document photos for demo, testing, and presets."""

from pathlib import Path

import cv2
import numpy as np


def create_sample(output_path: str | Path = "samples/sample_document.jpg") -> Path:
    canvas = np.full((900, 1200, 3), (42, 54, 68), dtype=np.uint8)
    noise = np.random.default_rng(7).normal(0, 8, canvas.shape).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    document = np.full((620, 440, 3), 245, dtype=np.uint8)
    cv2.putText(document, "PaperPulse", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.45, (20, 20, 20), 3)
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


def create_sample_invoice(output_path: str | Path = "samples/sample_invoice.jpg") -> Path:
    canvas = np.full((900, 1200, 3), (35, 45, 55), dtype=np.uint8)
    noise = np.random.default_rng(12).normal(0, 7, canvas.shape).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    doc = np.full((640, 460, 3), 250, dtype=np.uint8)
    cv2.putText(doc, "INVOICE #INV-2026-089", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    cv2.putText(doc, "PaperPulse Solutions Inc.", (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (90, 90, 90), 2)
    cv2.line(doc, (40, 115), (420, 115), (180, 180, 180), 2)

    cv2.putText(doc, "Bill To: Acme Global Corp", (40, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 40), 1)
    cv2.putText(doc, "Date: 2026-09-17", (40, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 40), 1)

    cv2.rectangle(doc, (40, 195), (420, 230), (220, 230, 240), -1)
    cv2.putText(doc, "Item Description", (50, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 2)
    cv2.putText(doc, "Amount", (330, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 2)

    items = [
        ("Computer Vision SDK", "$1,250.00"),
        ("OCR Optimization Model", "$850.00"),
        ("Document Auto-Warp API", "$450.00"),
        ("Enterprise Support (1Y)", "$350.00"),
    ]
    y = 265
    for item, price in items:
        cv2.putText(doc, item, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 50, 50), 1)
        cv2.putText(doc, price, (330, y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 50, 50), 1)
        cv2.line(doc, (40, y + 12), (420, y + 12), (230, 230, 230), 1)
        y += 42

    cv2.rectangle(doc, (240, 470), (420, 520), (20, 80, 50), 2)
    cv2.putText(doc, "TOTAL: $2,900.00", (255, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 80, 50), 2)
    cv2.putText(doc, "STATUS: PAID IN FULL", (40, 580), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 120, 0), 2)

    src = np.array([[0, 0], [459, 0], [459, 639], [0, 639]], dtype=np.float32)
    dst = np.array([[360, 110], [860, 130], [810, 810], [310, 750]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(doc, matrix, (1200, 900))

    mask = cv2.warpPerspective(np.full(doc.shape[:2], 255, dtype=np.uint8), matrix, (1200, 900))
    canvas[mask > 0] = warped[mask > 0]
    canvas = cv2.GaussianBlur(canvas, (3, 3), 0)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    return output


def create_sample_receipt(output_path: str = "samples/sample_receipt.jpg") -> Path:
    canvas = np.full((900, 1200, 3), (48, 40, 36), dtype=np.uint8)
    noise = np.random.default_rng(24).normal(0, 6, canvas.shape).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    doc = np.full((580, 340, 3), 248, dtype=np.uint8)
    cv2.putText(doc, "*** METRO CAFE ***", (60, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (20, 20, 20), 2)
    cv2.putText(doc, "Order #4092 - Dine In", (85, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (90, 90, 90), 1)
    cv2.putText(doc, "---------------------------------", (30, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)

    receipt_items = [
        ("2x Artisanal Espresso", "$8.50"),
        ("1x Avocado Toast", "$12.00"),
        ("1x Blueberry Scone", "$4.75"),
        ("1x Sparkling Water", "$3.50"),
    ]
    y = 145
    for item, cost in receipt_items:
        cv2.putText(doc, item, (35, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1)
        cv2.putText(doc, cost, (260, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1)
        y += 36

    cv2.putText(doc, "---------------------------------", (30, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)
    y += 40
    cv2.putText(doc, "Subtotal:       $28.75", (40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (30, 30, 30), 1)
    cv2.putText(doc, "Tax (8.5%):      $2.44", (40, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (30, 30, 30), 1)
    cv2.putText(doc, "TOTAL:          $31.19", (40, y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)
    cv2.putText(doc, "THANK YOU FOR VISITING!", (50, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (70, 70, 70), 1)

    src = np.array([[0, 0], [339, 0], [339, 579], [0, 579]], dtype=np.float32)
    dst = np.array([[440, 140], [800, 190], [710, 770], [370, 710]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(doc, matrix, (1200, 900))

    mask = cv2.warpPerspective(np.full(doc.shape[:2], 255, dtype=np.uint8), matrix, (1200, 900))
    canvas[mask > 0] = warped[mask > 0]
    canvas = cv2.GaussianBlur(canvas, (3, 3), 0)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    return output


def ensure_all_samples() -> dict[str, Path]:
    return {
        "sample_document": create_sample(Path("samples/sample_document.jpg")),
        "sample_invoice": create_sample_invoice(Path("samples/sample_invoice.jpg")),
        "sample_receipt": create_sample_receipt(Path("samples/sample_receipt.jpg")),
    }


if __name__ == "__main__":
    ensure_all_samples()


