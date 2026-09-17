"""One-command runner for the DocuVision project."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def _ensure_import_path() -> None:
    src_path = str(SRC)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the complete DocuVision document scanner project."
    )
    parser.add_argument(
        "--input",
        help="Optional image path to process once before starting the UI, or to process in --cli mode.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where output files will be saved.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run unit tests before starting the UI.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the command-line scanner and exit instead of starting the browser UI.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for the browser upload UI.",
    )
    parser.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Port for the browser upload UI.",
    )
    return parser


def run_tests() -> int:
    print("\nRunning tests...")
    env = os.environ.copy()
    existing_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing_path else f"{SRC}{os.pathsep}{existing_path}"
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT,
        env=env,
        check=False,
    )
    return completed.returncode


def run_scan(input_path: Path | None, output_dir: str) -> None:
    from docuvision.cli import run
    from scripts.generate_sample import create_sample

    selected_input = input_path if input_path else create_sample(ROOT / "samples" / "sample_document.jpg")

    print("DocuVision: Automatic Document Scanner and Quality Analyzer")
    print(f"Input image: {selected_input}")
    print(f"Output directory: {output_dir}\n")

    outputs = run(str(selected_input), output_dir)

    print("Generated outputs:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


def main() -> int:
    _ensure_import_path()

    args = build_parser().parse_args()
    input_path = Path(args.input) if args.input else None

    if args.run_tests:
        test_status = run_tests()
        if test_status != 0:
            return test_status

    if args.cli:
        run_scan(input_path, args.output_dir)
        return 0

    if input_path:
        run_scan(input_path, args.output_dir)

    from docuvision.web import serve

    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
