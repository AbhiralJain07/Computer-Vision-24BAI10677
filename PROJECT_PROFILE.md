# Project Profile

## Project Title

DocuVision: Automatic Document Scanner and Quality Analyzer

## Problem Statement

Students and staff often capture assignment pages, ID cards, forms, and notes using mobile cameras. These images may be tilted, poorly cropped, blurry, underexposed, or difficult to read. Manual cropping and correction takes time and can still produce inconsistent results. The problem is to build a computer vision system that automatically detects the document region, corrects perspective distortion, enhances readability, and reports whether the capture quality is acceptable.

## Scope

The project focuses on single-image document scanning. It accepts one image at a time, detects the document boundary, produces a corrected scan, enhances the document, and generates quality feedback. The current version handles images where the document is the main object in the frame and is visually separable from the background.

## Target Users

- Students submitting scanned assignments
- Faculty collecting handwritten documents
- Office users digitizing forms
- Anyone who needs quick document cleanup without a full scanning device

## High-Level Features

- Document contour detection
- Perspective correction
- Binary scan enhancement
- Quality metrics and feedback
- Visual pipeline report
- JSON report for further integration

## Functional Modules

1. Image input and preprocessing
2. Document boundary detection and perspective correction
3. Enhancement and quality analysis
4. Report generation

## Non-Functional Requirements

- Performance: Process standard phone images in a few seconds on a normal laptop.
- Usability: Provide a simple command-line interface with clear outputs.
- Reliability: Use fallback boundary handling when contour detection is uncertain.
- Maintainability: Keep CV operations separated into small modules with clear responsibilities.
- Error handling: Validate missing or unreadable image paths.
- Resource efficiency: Avoid large models or external datasets for the baseline version.

