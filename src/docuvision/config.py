"""Central configuration for the DocuVision pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScannerConfig:
    resize_height: int = 900
    blur_kernel: int = 5
    canny_low: int = 50
    canny_high: int = 160
    min_document_area_ratio: float = 0.18
    output_width: int = 900
    binary_block_size: int = 31
    binary_c: int = 12


@dataclass(frozen=True)
class QualityThresholds:
    min_sharpness: float = 45.0
    min_contrast: float = 35.0
    min_brightness: float = 70.0
    max_brightness: float = 245.0
    max_skew_degrees: float = 8.0
