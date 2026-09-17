"""Command-line interface for DocuVision."""

from __future__ import annotations

import argparse
from pathlib import Path

from .io_utils import read_image, write_image
from .quality import analyze_quality
from .report import create_visual_report, save_json_report
from .scanner import scan_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan a document image and analyze capture quality.")
    parser.add_argument("--input", required=True, help="Path to an input document photo.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated outputs.")
    return parser


def run(input_path: str, output_dir: str = "outputs") -> dict[str, Path]:
    image = read_image(input_path)
    result = scan_document(image)
    quality = analyze_quality(result.warped)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    scanned_path = write_image(output_root / "scanned_document.png", result.enhanced)
    report_image_path = create_visual_report(result, quality, output_root / "visual_report.png")
    report_json_path = save_json_report(quality, output_root / "quality_report.json")

    return {
        "scanned_document": scanned_path,
        "visual_report": report_image_path,
        "quality_report": report_json_path,
    }


def main() -> None:
    args = build_parser().parse_args()
    outputs = run(args.input, args.output_dir)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()

