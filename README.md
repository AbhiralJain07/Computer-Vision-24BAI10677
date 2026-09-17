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

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run the Upload UI

Start the complete project:

```bash
python main.py
```

Open `http://127.0.0.1:8000` in a browser, upload a document image, and the UI will display the scanned document, quality metrics, and visual report.

## Run the Command-Line Demo

```bash
python main.py --cli
```

To process your own image from the terminal:

```bash
python main.py --cli --input path/to/document.jpg
```

Generated files:

- `outputs/scanned_document.png`
- `outputs/visual_report.png`
- `outputs/quality_report.json`

## Testing

```bash
python -m unittest discover -s tests
```

## Screenshots / Results

After running the demo, open:

- `outputs/visual_report.png` for the complete pipeline visualization
- `outputs/scanned_document.png` for the final enhanced scan

## References

- OpenCV documentation: image filtering, Canny edge detection, contours, perspective transform, Hough lines
- Gonzalez and Woods, Digital Image Processing
- Szeliski, Computer Vision: Algorithms and Applications
