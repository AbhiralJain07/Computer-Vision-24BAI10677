# DocuVision: Automatic Document Scanner and Quality Analyzer

DocuVision is a computer vision project that detects a document inside a camera image, corrects its perspective, enhances readability, and evaluates capture quality using measurable image-processing features.

## Features

- Detects document boundaries using grayscale conversion, Gaussian blur, Canny edge detection, dilation, contour extraction, and polygon approximation.
- Applies four-point perspective transformation to create a scanned-document view.
- Enhances scanned output using denoising, CLAHE contrast correction, and adaptive thresholding.
- Measures image quality through brightness, contrast, sharpness, and skew estimation.
- Generates output images and a JSON quality report.

## Technologies Used

- Python 3.10+
- OpenCV
- NumPy
- Pillow
- unittest
- Mermaid diagrams for documentation

## Project Structure

```text
src/docuvision/
  cli.py              Command-line interface
  config.py           Central thresholds and scanner settings
  io_utils.py         Image read/write and resizing utilities
  preprocessing.py    Edge detection and enhancement operations
  scanner.py          Contour detection and perspective correction
  quality.py          Quality metrics and feedback
  report.py           Visual and JSON report generation
scripts/
  generate_sample.py  Creates a synthetic demo document photo
tests/
  test_docuvision.py  Unit tests for core CV logic
docs/
  project_report.md   Full project report content
  diagrams/           Architecture, workflow, use case, class, sequence, ER notes
```

## Installation & Setup

### macOS / Linux

#### Option A: Using Conda (Recommended if using Anaconda / Miniconda)
If your terminal shows `(base)`, you can run directly using Conda:
```bash
# Install dependencies into your active environment
pip install -r requirements.txt
pip install -e .

# Run the app
python main.py
```

#### Option B: Using standard Python venv
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python3 main.py
```

### Windows

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install -e .
   ```

## Usage

> **Note:** Ensure your virtual environment is active before running commands (`source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\activate` on Windows).

### 1. Run the Web Upload UI

Start the application server:

```bash
# macOS / Linux
python3 main.py

# Windows
python main.py
```

Open **`http://127.0.0.1:8000`** in your browser (Safari, Chrome, etc.), upload a document photo, and the UI will display:
- The scanned and perspective-corrected document
- Real-time quality metrics (Brightness, Contrast, Sharpness, Skew angle)
- Step-by-step visual pipeline report

### 2. Run the Command-Line Interface (CLI)

Run the demo on the built-in sample document:

```bash
python3 main.py --cli
```

To process your own image directly from the terminal:

```bash
python3 main.py --cli --input path/to/document.jpg
```

Generated files are saved to the `outputs/` directory:

- `outputs/scanned_document.png` - Final enhanced scan
- `outputs/visual_report.png` - Multi-stage pipeline visualization
- `outputs/quality_report.json` - Numerical quality evaluation & validation report

## Testing

Run unit tests to verify the computer vision pipeline:

```bash
python3 -m unittest discover -s tests
```

## Screenshots / Results

After running the demo, open:

- `outputs/visual_report.png` for the complete pipeline visualization
- `outputs/scanned_document.png` for the final enhanced scan

## References

- OpenCV documentation: image filtering, Canny edge detection, contours, perspective transform, Hough lines
- Gonzalez and Woods, Digital Image Processing
- Szeliski, Computer Vision: Algorithms and Applications
