"""Browser upload UI and interactive web application for PaperPulse."""

from __future__ import annotations

import argparse
import email.policy
from email.parser import BytesParser
import json
import mimetypes
import os
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import cv2
import numpy as np

from .cli import run
from .io_utils import read_image, write_image
from .quality import analyze_quality
from .report import create_visual_report, draw_detected_contour, save_json_report
from .scanner import scan_document
from scripts.generate_sample import ensure_all_samples


ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
UPLOADS = OUTPUTS / "uploads"
UI_RUNS = OUTPUTS / "ui"
SAMPLES = ROOT / "samples"
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


INDEX_HTML = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PaperPulse — Intelligent Document Scanner & Quality Engine</title>
  <meta name="description" content="State-of-the-art computer vision document scanner, perspective rectifier, and quality analyzer.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --font-body: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-heading: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;

      --radius-sm: 8px;
      --radius-md: 12px;
      --radius-lg: 18px;
      --radius-xl: 24px;
      --radius-full: 9999px;

      --transition-fast: 150ms cubic-bezier(0.16, 1, 0.3, 1);
      --transition-normal: 250ms cubic-bezier(0.16, 1, 0.3, 1);
      --transition-smooth: 350ms cubic-bezier(0.16, 1, 0.3, 1);
    }

    [data-theme="dark"] {
      --bg: #090d16;
      --bg-alt: #0e1422;
      --surface: rgba(18, 25, 41, 0.75);
      --surface-elevated: #162035;
      --surface-hover: rgba(30, 42, 69, 0.7);
      --surface-solid: #131c30;
      --border: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --border-focus: rgba(99, 102, 241, 0.6);

      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --text-inverse: #090d16;

      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --accent-glow: rgba(99, 102, 241, 0.35);
      --accent-subtle: rgba(99, 102, 241, 0.12);

      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.3);
      --emerald-subtle: rgba(16, 185, 129, 0.12);

      --cyan: #06b6d4;
      --cyan-subtle: rgba(6, 182, 212, 0.12);

      --amber: #f59e0b;
      --amber-subtle: rgba(245, 158, 11, 0.12);

      --rose: #f43f5e;
      --rose-subtle: rgba(244, 63, 94, 0.12);

      --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.45);
      --shadow-lg: 0 16px 40px rgba(0, 0, 0, 0.6);
      --glass-filter: blur(24px) saturate(180%);
      --canvas-check: #111726;
    }

    [data-theme="light"] {
      --bg: #f8fafc;
      --bg-alt: #f1f5f9;
      --surface: rgba(255, 255, 255, 0.85);
      --surface-elevated: #ffffff;
      --surface-hover: #f1f5f9;
      --surface-solid: #ffffff;
      --border: #e2e8f0;
      --border-strong: #cbd5e1;
      --border-focus: rgba(99, 102, 241, 0.5);

      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #94a3b8;
      --text-inverse: #ffffff;

      --accent: #4f46e5;
      --accent-hover: #4338ca;
      --accent-glow: rgba(79, 70, 229, 0.25);
      --accent-subtle: rgba(79, 70, 229, 0.08);

      --emerald: #059669;
      --emerald-glow: rgba(5, 150, 105, 0.25);
      --emerald-subtle: rgba(5, 150, 105, 0.08);

      --cyan: #0891b2;
      --cyan-subtle: rgba(8, 145, 178, 0.08);

      --amber: #d97706;
      --amber-subtle: rgba(217, 119, 6, 0.08);

      --rose: #e11d48;
      --rose-subtle: rgba(225, 29, 72, 0.08);

      --shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.06);
      --shadow-md: 0 8px 24px rgba(15, 23, 42, 0.08);
      --shadow-lg: 0 16px 36px rgba(15, 23, 42, 0.12);
      --glass-filter: blur(20px) saturate(160%);
      --canvas-check: #e2e8f0;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      min-height: 100vh;
      background: var(--bg);
      background-image: 
        radial-gradient(circle at 15% 15%, var(--accent-subtle) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, var(--cyan-subtle) 0%, transparent 45%);
      background-attachment: fixed;
      color: var(--text-primary);
      font-family: var(--font-body);
      font-size: 14px;
      line-height: 1.5;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }

    /* Top Navigation Bar */
    .topbar {
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: var(--glass-filter);
      -webkit-backdrop-filter: var(--glass-filter);
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 12px 24px;
      transition: border-color var(--transition-normal);
    }

    .topbar-inner {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: inherit;
    }

    .brand-logo {
      width: 38px;
      height: 38px;
      border-radius: var(--radius-md);
      background: linear-gradient(135deg, var(--accent) 0%, #a855f7 50%, var(--cyan) 100%);
      display: grid;
      place-items: center;
      box-shadow: 0 4px 14px var(--accent-glow);
      color: white;
      font-weight: 800;
      font-family: var(--font-heading);
      font-size: 20px;
      flex-shrink: 0;
    }

    .brand-text {
      display: flex;
      flex-direction: column;
    }

    .brand-title {
      font-family: var(--font-heading);
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, var(--text-primary) 30%, var(--text-secondary) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      line-height: 1.15;
    }

    .brand-badge {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent);
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: var(--radius-full);
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      box-shadow: var(--shadow-sm);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 10px var(--emerald);
      animation: pulseDot 2s infinite ease-in-out;
    }

    .status-dot.busy {
      background: var(--amber);
      box-shadow: 0 0 10px var(--amber);
    }

    @keyframes pulseDot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }

    .icon-btn {
      width: 38px;
      height: 38px;
      border-radius: var(--radius-md);
      border: 1px solid var(--border);
      background: var(--surface-elevated);
      color: var(--text-secondary);
      display: grid;
      place-items: center;
      cursor: pointer;
      transition: all var(--transition-fast);
      box-shadow: var(--shadow-sm);
    }

    .icon-btn:hover {
      color: var(--text-primary);
      border-color: var(--border-strong);
      background: var(--surface-hover);
      transform: translateY(-1px);
    }

    /* Main Container Grid */
    .app-shell {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 390px 1fr;
      gap: 24px;
      align-items: start;
    }

    /* Generic Card / Glass Panel */
    .glass-panel {
      background: var(--surface);
      backdrop-filter: var(--glass-filter);
      -webkit-backdrop-filter: var(--glass-filter);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-md);
      overflow: hidden;
      transition: border-color var(--transition-normal), box-shadow var(--transition-normal);
    }

    .glass-panel:hover {
      border-color: var(--border-strong);
    }

    .panel-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: var(--surface-elevated);
    }

    .panel-title {
      font-family: var(--font-heading);
      font-size: 15px;
      font-weight: 700;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .panel-body {
      padding: 20px;
    }

    /* Studio Sidebar (Left Column) */
    .studio-sidebar {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Drag & Drop Zone */
    .dropzone-container {
      position: relative;
    }

    .dropzone {
      position: relative;
      border: 2px dashed var(--border-strong);
      border-radius: var(--radius-md);
      background: var(--bg-alt);
      padding: 32px 18px;
      text-align: center;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      transition: all var(--transition-normal);
      overflow: hidden;
    }

    .dropzone::before {
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at center, var(--accent-subtle) 0%, transparent 70%);
      opacity: 0;
      transition: opacity var(--transition-normal);
      pointer-events: none;
    }

    .dropzone:hover,
    .dropzone.dragover {
      border-color: var(--accent);
      background: var(--surface-hover);
      box-shadow: 0 0 24px var(--accent-glow);
      transform: scale(0.995);
    }

    .dropzone:hover::before,
    .dropzone.dragover::before {
      opacity: 1;
    }

    .dropzone input[type="file"] {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }

    .drop-icon-wrapper {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--accent-subtle);
      border: 1px solid var(--accent-glow);
      display: grid;
      place-items: center;
      color: var(--accent);
      transition: transform var(--transition-smooth);
    }

    .dropzone:hover .drop-icon-wrapper {
      transform: scale(1.1) translateY(-2px);
    }

    .drop-title {
      font-family: var(--font-heading);
      font-size: 16px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .drop-sub {
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.4;
    }

    .paste-hint {
      font-size: 11px;
      font-family: var(--font-mono);
      background: var(--surface-elevated);
      padding: 3px 8px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      margin-top: 4px;
    }

    /* Selected File Preview Box */
    .file-preview-card {
      display: none;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      margin-top: 14px;
      animation: fadeIn 0.2s ease;
    }

    .file-preview-card.active {
      display: flex;
    }

    .preview-thumb {
      width: 48px;
      height: 48px;
      border-radius: var(--radius-sm);
      object-fit: cover;
      background: var(--bg);
      border: 1px solid var(--border);
      flex-shrink: 0;
    }

    .file-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .file-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-meta {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }

    .btn-remove-file {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 6px;
      border-radius: var(--radius-sm);
      transition: all var(--transition-fast);
    }

    .btn-remove-file:hover {
      color: var(--rose);
      background: var(--rose-subtle);
    }

    /* Primary Action Buttons */
    .action-group {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 16px;
    }

    .btn-primary {
      width: 100%;
      height: 48px;
      border: none;
      border-radius: var(--radius-md);
      background: linear-gradient(135deg, var(--accent) 0%, #7c3aed 100%);
      color: #ffffff;
      font-family: var(--font-heading);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.01em;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      box-shadow: 0 4px 16px var(--accent-glow);
      transition: all var(--transition-normal);
      position: relative;
      overflow: hidden;
    }

    .btn-primary:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px var(--accent-glow);
      filter: brightness(1.08);
    }

    .btn-primary:active:not(:disabled) {
      transform: translateY(0);
    }

    .btn-primary:disabled {
      opacity: 0.45;
      cursor: not-allowed;
      box-shadow: none;
    }

    .btn-secondary {
      flex: 1;
      height: 40px;
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      background: var(--surface-elevated);
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all var(--transition-fast);
    }

    .btn-secondary:hover {
      color: var(--text-primary);
      border-color: var(--border-strong);
      background: var(--surface-hover);
    }

    .btn-row {
      display: flex;
      gap: 10px;
    }

    /* Pipeline Execution Stepper */
    .stepper {
      display: none;
      flex-direction: column;
      gap: 10px;
      margin-top: 16px;
      padding: 14px;
      background: var(--bg-alt);
      border-radius: var(--radius-md);
      border: 1px solid var(--border);
    }

    .stepper.active {
      display: flex;
    }

    .step-item {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      color: var(--text-muted);
      transition: color var(--transition-fast);
    }

    .step-item.current {
      color: var(--accent);
      font-weight: 600;
    }

    .step-item.done {
      color: var(--emerald);
    }

    .step-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--border-strong);
      flex-shrink: 0;
    }

    .step-item.current .step-dot {
      background: var(--accent);
      box-shadow: 0 0 8px var(--accent);
      animation: pulseDot 1s infinite alternate;
    }

    .step-item.done .step-dot {
      background: var(--emerald);
    }

    /* Sample Library Chips */
    .sample-section {
      margin-top: 8px;
    }

    .section-label {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .sample-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
    }

    .sample-chip {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      cursor: pointer;
      text-align: left;
      transition: all var(--transition-fast);
    }

    .sample-chip:hover {
      border-color: var(--accent);
      background: var(--surface-hover);
      transform: translateX(3px);
    }

    .sample-chip-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    .sample-chip-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .sample-chip-desc {
      font-size: 11px;
      color: var(--text-muted);
    }

    /* Inspection Stage (Right Column) */
    .inspection-stage {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Stage Viewer Controls */
    .stage-header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .view-mode-toggle {
      display: flex;
      background: var(--bg-alt);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 3px;
      gap: 2px;
    }

    .toggle-opt {
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      border: none;
      background: transparent;
      cursor: pointer;
      transition: all var(--transition-fast);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .toggle-opt.active {
      background: var(--surface-elevated);
      color: var(--text-primary);
      box-shadow: var(--shadow-sm);
    }

    /* Tabs Bar */
    .tabs-bar {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: var(--bg-alt);
      border-bottom: 1px solid var(--border);
      overflow-x: auto;
    }

    .tab-btn {
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      background: transparent;
      border: 1px solid transparent;
      cursor: pointer;
      white-space: nowrap;
      transition: all var(--transition-fast);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .tab-btn:hover {
      color: var(--text-primary);
      background: var(--surface-hover);
    }

    .tab-btn.active {
      background: var(--surface-elevated);
      color: var(--accent);
      border-color: var(--border);
      box-shadow: var(--shadow-sm);
    }

    /* Canvas Viewport */
    .viewport {
      position: relative;
      width: 100%;
      min-height: 480px;
      height: 540px;
      background: var(--bg-alt);
      background-image: 
        linear-gradient(45deg, var(--canvas-check) 25%, transparent 25%),
        linear-gradient(-45deg, var(--canvas-check) 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, var(--canvas-check) 75%),
        linear-gradient(-45deg, transparent 75%, var(--canvas-check) 75%);
      background-size: 20px 20px;
      background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
      display: grid;
      place-items: center;
      overflow: hidden;
    }

    .viewport-img {
      max-width: 95%;
      max-height: 95%;
      object-fit: contain;
      border-radius: var(--radius-sm);
      box-shadow: var(--shadow-lg);
      transition: transform var(--transition-normal);
      user-select: none;
    }

    .viewport-empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: var(--text-muted);
      text-align: center;
      padding: 32px;
    }

    .viewport-empty-icon {
      font-size: 48px;
      opacity: 0.6;
    }

    /* Split Comparison Slider View */
    .split-slider-container {
      position: relative;
      width: 100%;
      height: 100%;
      overflow: hidden;
      display: none;
      cursor: ew-resize;
      user-select: none;
    }

    .split-slider-container.active {
      display: block;
    }

    .split-img-layer {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .split-img-layer img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      box-shadow: var(--shadow-md);
      border-radius: var(--radius-sm);
    }

    .split-before-layer {
      position: absolute;
      inset: 0;
      overflow: hidden;
      width: 50%;
      border-right: 2px solid var(--accent);
      z-index: 2;
    }

    .split-before-layer .split-img-wrapper {
      position: absolute;
      inset: 0;
      width: var(--container-width, 800px);
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .split-handle {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      width: 3px;
      background: var(--accent);
      z-index: 5;
      cursor: ew-resize;
      transform: translateX(-50%);
      box-shadow: 0 0 14px var(--accent-glow);
    }

    .split-handle-btn {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--accent);
      border: 3px solid #ffffff;
      color: #ffffff;
      display: grid;
      place-items: center;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      font-size: 12px;
      pointer-events: none;
    }

    .split-badge {
      position: absolute;
      top: 16px;
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      z-index: 4;
      backdrop-filter: blur(8px);
      box-shadow: var(--shadow-sm);
    }

    .split-badge.left {
      left: 16px;
      background: rgba(15, 23, 42, 0.85);
      color: #94a3b8;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .split-badge.right {
      right: 16px;
      background: rgba(16, 185, 129, 0.9);
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Action Toolbar Below Viewport */
    .viewport-toolbar {
      padding: 12px 18px;
      background: var(--surface-elevated);
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .toolbar-left,
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .tool-btn {
      padding: 8px 14px;
      border-radius: var(--radius-md);
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      text-decoration: none;
      transition: all var(--transition-fast);
    }

    .tool-btn:hover {
      background: var(--surface-hover);
      border-color: var(--border-strong);
      transform: translateY(-1px);
    }

    .tool-btn.primary {
      background: var(--accent);
      color: #ffffff;
      border-color: transparent;
      box-shadow: 0 2px 10px var(--accent-glow);
    }

    .tool-btn.primary:hover {
      background: var(--accent-hover);
    }

    /* Quality Intelligence Dashboard */
    .quality-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-top: 16px;
    }

    .metric-card {
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all var(--transition-fast);
    }

    .metric-card:hover {
      border-color: var(--border-strong);
      transform: translateY(-2px);
    }

    .metric-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .metric-name {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .metric-tag {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: var(--radius-full);
      background: var(--emerald-subtle);
      color: var(--emerald);
    }

    .metric-tag.warn {
      background: var(--amber-subtle);
      color: var(--amber);
    }

    .metric-tag.bad {
      background: var(--rose-subtle);
      color: var(--rose);
    }

    .metric-value-row {
      display: flex;
      align-items: baseline;
      gap: 6px;
    }

    .metric-val {
      font-family: var(--font-mono);
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .metric-unit {
      font-size: 11px;
      color: var(--text-muted);
    }

    .metric-bar-bg {
      height: 6px;
      background: var(--border);
      border-radius: var(--radius-full);
      overflow: hidden;
      margin-top: 2px;
    }

    .metric-bar-fill {
      height: 100%;
      background: var(--emerald);
      border-radius: var(--radius-full);
      width: 0%;
      transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .metric-bar-fill.warn {
      background: var(--amber);
    }

    .metric-bar-fill.bad {
      background: var(--rose);
    }

    /* Overall Quality Banner */
    .quality-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 18px;
      border-radius: var(--radius-md);
      background: var(--emerald-subtle);
      border: 1px solid var(--emerald-glow);
      color: var(--emerald);
      margin-bottom: 16px;
    }

    .quality-banner.review {
      background: var(--amber-subtle);
      border-color: var(--amber);
      color: var(--amber);
    }

    .quality-banner-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .quality-verdict-icon {
      font-size: 24px;
    }

    .quality-verdict-title {
      font-family: var(--font-heading);
      font-size: 15px;
      font-weight: 700;
    }

    .quality-verdict-desc {
      font-size: 12px;
      opacity: 0.9;
    }

    /* Diagnostic Advice Box */
    .advice-box {
      margin-top: 14px;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      font-size: 13px;
      color: var(--text-secondary);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .advice-item {
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }

    .advice-item-icon {
      color: var(--accent);
      flex-shrink: 0;
      margin-top: 2px;
    }

    /* Session History Strip */
    .history-strip {
      display: flex;
      align-items: center;
      gap: 12px;
      overflow-x: auto;
      padding: 4px 0;
    }

    .history-card {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: var(--radius-md);
      background: var(--surface-elevated);
      border: 1px solid var(--border);
      cursor: pointer;
      flex-shrink: 0;
      transition: all var(--transition-fast);
    }

    .history-card:hover,
    .history-card.active {
      border-color: var(--accent);
      background: var(--surface-hover);
    }

    .history-thumb {
      width: 32px;
      height: 32px;
      border-radius: var(--radius-sm);
      object-fit: cover;
      background: var(--bg);
    }

    .history-title {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .history-time {
      font-size: 10px;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }

    /* Modals (Camera & Lightbox) */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(12px);
      z-index: 100;
      display: none;
      place-items: center;
      padding: 24px;
      animation: fadeIn 0.2s ease;
    }

    .modal-overlay.active {
      display: grid;
    }

    .modal-card {
      background: var(--surface-solid);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-lg);
      width: min(720px, 100%);
      max-height: 90vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .modal-header {
      padding: 16px 22px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-title {
      font-family: var(--font-heading);
      font-size: 17px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .modal-close {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
      padding: 4px;
      border-radius: var(--radius-sm);
      transition: color var(--transition-fast);
    }

    .modal-close:hover {
      color: var(--text-primary);
    }

    .modal-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }

    /* Camera Viewfinder */
    .camera-frame {
      position: relative;
      width: 100%;
      aspect-ratio: 4 / 3;
      background: #000000;
      border-radius: var(--radius-md);
      overflow: hidden;
      display: grid;
      place-items: center;
    }

    #cameraVideo {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .camera-guide {
      position: absolute;
      inset: 24px;
      border: 2px dashed rgba(255, 255, 255, 0.6);
      border-radius: var(--radius-md);
      pointer-events: none;
      box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.4);
    }

    .camera-shutter-btn {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: #ffffff;
      border: 4px solid var(--accent);
      cursor: pointer;
      display: grid;
      place-items: center;
      box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
      transition: transform var(--transition-fast);
    }

    .camera-shutter-btn:hover {
      transform: scale(1.08);
    }

    .camera-shutter-btn:active {
      transform: scale(0.92);
    }

    /* Lightbox Zoom Modal */
    .lightbox-card {
      background: var(--surface-solid);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-lg);
      width: min(1100px, 95vw);
      height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .lightbox-viewport {
      flex: 1;
      overflow: auto;
      display: grid;
      place-items: center;
      background: #060910;
      padding: 24px;
      cursor: grab;
    }

    .lightbox-viewport:active {
      cursor: grabbing;
    }

    .lightbox-img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      transform-origin: center center;
      transition: transform 0.15s ease;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8);
    }

    .lightbox-controls {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 12px;
      background: var(--surface-elevated);
      border-top: 1px solid var(--border);
    }

    /* Toast Notification */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      padding: 12px 20px;
      border-radius: var(--radius-md);
      background: var(--surface-solid);
      color: var(--text-primary);
      border: 1px solid var(--border-strong);
      box-shadow: var(--shadow-lg);
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      z-index: 200;
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .toast.show {
      transform: translateY(0);
      opacity: 1;
    }

    /* Animations */
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    /* Responsive Breakpoints */
    @media (max-width: 1100px) {
      .app-shell {
        grid-template-columns: 1fr;
      }
      .studio-sidebar {
        max-width: 600px;
        margin: 0 auto;
        width: 100%;
      }
      .quality-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 640px) {
      .app-shell {
        padding: 14px;
        gap: 16px;
      }
      .topbar {
        padding: 10px 14px;
      }
      .viewport {
        height: 380px;
        min-height: 380px;
      }
      .quality-grid {
        grid-template-columns: 1fr;
      }
      .brand-title {
        font-size: 18px;
      }
      .panel-body {
        padding: 14px;
      }
    }

    /* Print View */
    @media print {
      .topbar, .studio-sidebar, .stage-header-actions, .viewport-toolbar, .quality-grid, .advice-box, .tabs-bar {
        display: none !important;
      }
      body, .app-shell, .glass-panel {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
      }
      .viewport {
        background: none !important;
        height: auto !important;
        min-height: auto !important;
      }
      .viewport-img {
        max-width: 100% !important;
        box-shadow: none !important;
      }
    }
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <header class="topbar">
    <div class="topbar-inner">
      <a href="/" class="brand">
        <div class="brand-logo">PP</div>
        <div class="brand-text">
          <div class="brand-title">PaperPulse</div>
          <div class="brand-badge">Computer Vision Engine</div>
        </div>
      </a>

      <div class="topbar-right">
        <div class="status-badge" id="systemStatus">
          <span class="status-dot" id="statusDot"></span>
          <span id="statusLabel">Ready</span>
        </div>
        <button class="icon-btn" id="themeToggle" title="Toggle Dark / Light Theme" aria-label="Toggle Theme">
          <span id="themeIcon">🌙</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main App Studio Grid -->
  <main class="app-shell">

    <!-- Left Control Studio -->
    <aside class="studio-sidebar">
      
      <!-- Ingestion & Upload Card -->
      <section class="glass-panel">
        <div class="panel-header">
          <h2 class="panel-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            Ingest Document
          </h2>
        </div>
        <div class="panel-body">
          <form id="uploadForm">
            <div class="dropzone-container">
              <label class="dropzone" id="dropzone">
                <input type="file" id="mediaInput" accept="image/*">
                <div class="drop-icon-wrapper">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/></svg>
                </div>
                <div class="drop-title">Drop document image here</div>
                <div class="drop-sub">JPG, PNG, WebP, BMP, TIFF (Up to 16MB)</div>
                <div class="paste-hint">💡 Press Cmd+V / Ctrl+V to paste</div>
              </label>
            </div>

            <!-- File Preview State -->
            <div class="file-preview-card" id="filePreviewCard">
              <img id="thumbImg" class="preview-thumb" src="" alt="Thumbnail">
              <div class="file-info">
                <span class="file-name" id="selectedFileName">document.jpg</span>
                <span class="file-meta" id="selectedFileMeta">1.2 MB &bull; 1200x900</span>
              </div>
              <button type="button" class="btn-remove-file" id="btnRemoveFile" title="Remove file">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            <!-- Pipeline Progress Stepper -->
            <div class="stepper" id="pipelineStepper">
              <div class="step-item" id="step1"><span class="step-dot"></span> 1. Ingesting & Resizing Image</div>
              <div class="step-item" id="step2"><span class="step-dot"></span> 2. Gaussian Blur & Canny Edge Filter</div>
              <div class="step-item" id="step3"><span class="step-dot"></span> 3. Finding Document Polygon Contour</div>
              <div class="step-item" id="step4"><span class="step-dot"></span> 4. 4-Point Homography Perspective Warp</div>
              <div class="step-item" id="step5"><span class="step-dot"></span> 5. CLAHE & Adaptive Binarization</div>
              <div class="step-item" id="step6"><span class="step-dot"></span> 6. Laplacian Sharpness & Quality Audit</div>
            </div>

            <!-- Action Buttons -->
            <div class="action-group">
              <button type="submit" class="btn-primary" id="btnScan" disabled>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                <span id="btnScanText">Run Document Scanner</span>
              </button>
              
              <div class="btn-row">
                <button type="button" class="btn-secondary" id="btnOpenCam">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                  Camera Capture
                </button>
                <button type="button" class="btn-secondary" id="btnReset" title="Reset workspace">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                  Reset
                </button>
              </div>
            </div>
          </form>

          <!-- 1-Click Preset Samples -->
          <div class="sample-section">
            <div class="section-label">
              <span>Preset Document Library</span>
              <span>1-Click Test</span>
            </div>
            <div class="sample-grid">
              <button type="button" class="sample-chip" data-sample="sample_document">
                <span class="sample-chip-icon">📄</span>
                <div>
                  <div class="sample-chip-title">Technical Report</div>
                  <div class="sample-chip-desc">Academic format with text columns</div>
                </div>
              </button>
              <button type="button" class="sample-chip" data-sample="sample_invoice">
                <span class="sample-chip-icon">🧾</span>
                <div>
                  <div class="sample-chip-title">Commercial Invoice</div>
                  <div class="sample-chip-desc">Tabular invoice with prices & header</div>
                </div>
              </button>
              <button type="button" class="sample-chip" data-sample="sample_receipt">
                <span class="sample-chip-icon">☕</span>
                <div>
                  <div class="sample-chip-title">Store Receipt</div>
                  <div class="sample-chip-desc">Retail transaction receipt with tilt</div>
                </div>
              </button>
            </div>
          </div>

        </div>
      </section>

      <!-- Session Recent Scans Card -->
      <section class="glass-panel" id="historyPanel" style="display: none;">
        <div class="panel-header">
          <h2 class="panel-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Session History
          </h2>
        </div>
        <div class="panel-body">
          <div class="history-strip" id="historyStrip"></div>
        </div>
      </section>

    </aside>

    <!-- Right Inspection Studio -->
    <main class="inspection-stage">

      <!-- Stage Viewer Panel -->
      <section class="glass-panel">
        <div class="panel-header">
          <h2 class="panel-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            Output & Stage Inspector
          </h2>

          <div class="stage-header-actions">
            <!-- View Mode Switcher -->
            <div class="view-mode-toggle">
              <button type="button" class="toggle-opt active" id="btnModeSplit">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/></svg>
                Split Compare
              </button>
              <button type="button" class="toggle-opt" id="btnModeTabs">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
                Pipeline Stages
              </button>
            </div>
          </div>
        </div>

        <!-- Stage Inspector Tabs Bar (Visible in Tabs mode) -->
        <div class="tabs-bar" id="stageTabsBar" style="display: none;">
          <button type="button" class="tab-btn active" data-stage="enhanced">✨ 1. Scanned Document</button>
          <button type="button" class="tab-btn" data-stage="warped">🎨 2. Warped Color</button>
          <button type="button" class="tab-btn" data-stage="contour">📐 3. Contour Detection</button>
          <button type="button" class="tab-btn" data-stage="edges">⚡ 4. Edge Map</button>
          <button type="button" class="tab-btn" data-stage="visual_report">📊 5. Visual Report</button>
        </div>

        <!-- Canvas Viewport -->
        <div class="viewport" id="viewport">
          
          <!-- Default Empty State -->
          <div class="viewport-empty" id="viewportEmpty">
            <div class="viewport-empty-icon">📷</div>
            <div>
              <p style="font-size: 15px; font-weight: 700; color: var(--text-primary);">No scan performed yet</p>
              <p style="font-size: 13px;">Upload an image or pick a demo sample to inspect the computer vision pipeline.</p>
            </div>
          </div>

          <!-- Single Stage Image View -->
          <img id="stageImg" class="viewport-img" src="" alt="Pipeline Stage" style="display: none;">

          <!-- Interactive Before / After Split Slider -->
          <div class="split-slider-container" id="splitSlider">
            <span class="split-badge left">Original Capture</span>
            <span class="split-badge right">Digitized Scan</span>

            <!-- Bottom Layer: Original Photo -->
            <div class="split-img-layer">
              <img id="splitOriginalImg" src="" alt="Original Photo">
            </div>

            <!-- Top Layer: Scanned Output (Clipped by width) -->
            <div class="split-before-layer" id="splitBeforeLayer">
              <div class="split-img-wrapper" id="splitWrapper">
                <img id="splitScannedImg" src="" alt="Scanned Document">
              </div>
            </div>

            <!-- Draggable Divider Handle -->
            <div class="split-handle" id="splitHandle">
              <div class="split-handle-btn">⮂ ⮃</div>
            </div>
          </div>

        </div>

        <!-- Action Toolbar -->
        <div class="viewport-toolbar">
          <div class="toolbar-left">
            <button type="button" class="tool-btn" id="btnLightbox" title="Open fullscreen zoom lightbox">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
              Zoom & Pan
            </button>
            <button type="button" class="tool-btn" id="btnCopyImage" title="Copy scanned image to clipboard">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              Copy Image
            </button>
            <button type="button" class="tool-btn" id="btnPrint" title="Print scanned document">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
              Print
            </button>
          </div>

          <div class="toolbar-right">
            <a class="tool-btn" id="btnDownloadReport" href="#" download="paperpulse_report.png" style="display: none;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Report PNG
            </a>
            <a class="tool-btn primary" id="btnDownloadScan" href="#" download="scanned_document.png" style="display: none;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download Scan
            </a>
          </div>
        </div>
      </section>

      <!-- Quality Metrics & Intelligence Dashboard -->
      <section class="glass-panel" id="qualitySection">
        <div class="panel-header">
          <h2 class="panel-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Quality & Diagnostic Intelligence
          </h2>
          <button type="button" class="tool-btn" id="btnCopyJson">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            Copy JSON
          </button>
        </div>
        <div class="panel-body">
          
          <!-- Overall Status Banner -->
          <div class="quality-banner" id="qualityBanner">
            <div class="quality-banner-left">
              <span class="quality-verdict-icon" id="verdictIcon">🛡️</span>
              <div>
                <div class="quality-verdict-title" id="verdictTitle">Awaiting Document Analysis</div>
                <div class="quality-verdict-desc" id="verdictDesc">Capture or upload an image to view automated computer vision diagnostics.</div>
              </div>
            </div>
          </div>

          <!-- 4 Metric Gauge Cards -->
          <div class="quality-grid">
            
            <div class="metric-card" id="cardBrightness">
              <div class="metric-header">
                <span class="metric-name">Brightness</span>
                <span class="metric-tag" id="tagBrightness">--</span>
              </div>
              <div class="metric-value-row">
                <span class="metric-val" id="valBrightness">--</span>
                <span class="metric-unit">/ 255</span>
              </div>
              <div class="metric-bar-bg"><div class="metric-bar-fill" id="barBrightness"></div></div>
            </div>

            <div class="metric-card" id="cardContrast">
              <div class="metric-header">
                <span class="metric-name">Contrast</span>
                <span class="metric-tag" id="tagContrast">--</span>
              </div>
              <div class="metric-value-row">
                <span class="metric-val" id="valContrast">--</span>
                <span class="metric-unit">std dev</span>
              </div>
              <div class="metric-bar-bg"><div class="metric-bar-fill" id="barContrast"></div></div>
            </div>

            <div class="metric-card" id="cardSharpness">
              <div class="metric-header">
                <span class="metric-name">Sharpness</span>
                <span class="metric-tag" id="tagSharpness">--</span>
              </div>
              <div class="metric-value-row">
                <span class="metric-val" id="valSharpness">--</span>
                <span class="metric-unit">Laplacian</span>
              </div>
              <div class="metric-bar-bg"><div class="metric-bar-fill" id="barSharpness"></div></div>
            </div>

            <div class="metric-card" id="cardSkew">
              <div class="metric-header">
                <span class="metric-name">Skew Angle</span>
                <span class="metric-tag" id="tagSkew">--</span>
              </div>
              <div class="metric-value-row">
                <span class="metric-val" id="valSkew">--</span>
                <span class="metric-unit">deg</span>
              </div>
              <div class="metric-bar-bg"><div class="metric-bar-fill" id="barSkew"></div></div>
            </div>

          </div>

          <!-- Diagnostic Guidance Checklist -->
          <div class="advice-box" id="adviceBox" style="display: none;">
            <div style="font-weight: 700; font-size: 12px; text-transform: uppercase; color: var(--text-muted);">Diagnostic Notes:</div>
            <div id="adviceList"></div>
          </div>

        </div>
      </section>

    </main>

  </main>

  <!-- Live Camera Modal -->
  <div class="modal-overlay" id="cameraModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3 class="modal-title">Live Document Scanner Camera</h3>
        <button type="button" class="modal-close" id="btnCloseCam">&times;</button>
      </div>
      <div class="modal-body">
        <div class="camera-frame">
          <video id="cameraVideo" autoplay playsinline muted></video>
          <div class="camera-guide"></div>
        </div>
        <p style="font-size: 12px; color: var(--text-muted); text-align: center;">Align the edges of the page within the guide frame and press capture.</p>
        <button type="button" class="camera-shutter-btn" id="btnShutter" title="Take Photo"></button>
        <canvas id="cameraCanvas" style="display: none;"></canvas>
      </div>
    </div>
  </div>

  <!-- Fullscreen Zoom Lightbox Modal -->
  <div class="modal-overlay" id="lightboxModal">
    <div class="lightbox-card">
      <div class="modal-header">
        <h3 class="modal-title" id="lightboxTitle">High-Resolution Inspection</h3>
        <button type="button" class="modal-close" id="btnCloseLightbox">&times;</button>
      </div>
      <div class="lightbox-viewport" id="lightboxViewport">
        <img id="lightboxImg" class="lightbox-img" src="" alt="High-Res Zoom View">
      </div>
      <div class="lightbox-controls">
        <button type="button" class="tool-btn" id="btnZoomIn">➕ Zoom In</button>
        <button type="button" class="tool-btn" id="btnZoomOut">➖ Zoom Out</button>
        <button type="button" class="tool-btn" id="btnZoomReset">↺ Reset (100%)</button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div class="toast" id="toast">
    <span id="toastIcon">✓</span>
    <span id="toastMessage">Action completed</span>
  </div>

  <script>
    // State management
    const state = {
      currentRun: null,
      selectedFile: null,
      activeMode: 'split', // 'split' | 'tabs'
      activeStage: 'enhanced',
      zoomScale: 1.0,
      cameraStream: null,
      history: []
    };

    // DOM Elements
    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");
    const uploadForm = document.getElementById("uploadForm");
    const mediaInput = document.getElementById("mediaInput");
    const dropzone = document.getElementById("dropzone");
    const filePreviewCard = document.getElementById("filePreviewCard");
    const thumbImg = document.getElementById("thumbImg");
    const selectedFileName = document.getElementById("selectedFileName");
    const selectedFileMeta = document.getElementById("selectedFileMeta");
    const btnRemoveFile = document.getElementById("btnRemoveFile");
    const btnScan = document.getElementById("btnScan");
    const btnScanText = document.getElementById("btnScanText");
    const pipelineStepper = document.getElementById("pipelineStepper");
    const systemStatus = document.getElementById("systemStatus");
    const statusDot = document.getElementById("statusDot");
    const statusLabel = document.getElementById("statusLabel");

    // Viewport Elements
    const viewportEmpty = document.getElementById("viewportEmpty");
    const stageImg = document.getElementById("stageImg");
    const splitSlider = document.getElementById("splitSlider");
    const splitBeforeLayer = document.getElementById("splitBeforeLayer");
    const splitWrapper = document.getElementById("splitWrapper");
    const splitHandle = document.getElementById("splitHandle");
    const splitOriginalImg = document.getElementById("splitOriginalImg");
    const splitScannedImg = document.getElementById("splitScannedImg");
    const stageTabsBar = document.getElementById("stageTabsBar");
    const btnModeSplit = document.getElementById("btnModeSplit");
    const btnModeTabs = document.getElementById("btnModeTabs");

    // Action Toolbars
    const btnLightbox = document.getElementById("btnLightbox");
    const btnCopyImage = document.getElementById("btnCopyImage");
    const btnPrint = document.getElementById("btnPrint");
    const btnDownloadScan = document.getElementById("btnDownloadScan");
    const btnDownloadReport = document.getElementById("btnDownloadReport");
    const btnCopyJson = document.getElementById("btnCopyJson");
    const btnReset = document.getElementById("btnReset");

    // Camera Elements
    const btnOpenCam = document.getElementById("btnOpenCam");
    const cameraModal = document.getElementById("cameraModal");
    const btnCloseCam = document.getElementById("btnCloseCam");
    const cameraVideo = document.getElementById("cameraVideo");
    const cameraCanvas = document.getElementById("cameraCanvas");
    const btnShutter = document.getElementById("btnShutter");

    // Lightbox Elements
    const lightboxModal = document.getElementById("lightboxModal");
    const btnCloseLightbox = document.getElementById("btnCloseLightbox");
    const lightboxImg = document.getElementById("lightboxImg");
    const btnZoomIn = document.getElementById("btnZoomIn");
    const btnZoomOut = document.getElementById("btnZoomOut");
    const btnZoomReset = document.getElementById("btnZoomReset");

    // Toast
    const toast = document.getElementById("toast");
    const toastMessage = document.getElementById("toastMessage");

    // Theme Management
    function initTheme() {
      const saved = localStorage.getItem("paperpulse_theme") || "dark";
      document.documentElement.setAttribute("data-theme", saved);
      themeIcon.textContent = saved === "dark" ? "🌙" : "☀️";
    }

    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("paperpulse_theme", next);
      themeIcon.textContent = next === "dark" ? "🌙" : "☀️";
    });
    initTheme();

    // Toast Notification helper
    function showToast(msg, icon = "✓") {
      document.getElementById("toastIcon").textContent = icon;
      toastMessage.textContent = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 3000);
    }

    // Status Indicator
    function setSystemStatus(label, isBusy = false) {
      statusLabel.textContent = label;
      statusDot.classList.toggle("busy", isBusy);
    }

    // File selection handling
    function setSelectedFile(file) {
      if (!file) {
        state.selectedFile = null;
        filePreviewCard.classList.remove("active");
        btnScan.disabled = true;
        return;
      }
      state.selectedFile = file;
      selectedFileName.textContent = file.name;
      const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
      selectedFileMeta.textContent = `${sizeMb} MB &bull; ${file.type || 'Image'}`;

      const reader = new FileReader();
      reader.onload = (e) => {
        thumbImg.src = e.target.result;
        filePreviewCard.classList.add("active");
      };
      reader.readAsDataURL(file);

      btnScan.disabled = false;
      showToast(`Selected ${file.name}`);
    }

    mediaInput.addEventListener("change", (e) => {
      if (e.target.files.length) setSelectedFile(e.target.files[0]);
    });

    btnRemoveFile.addEventListener("click", () => {
      mediaInput.value = "";
      setSelectedFile(null);
    });

    // Drag & Drop
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        mediaInput.files = e.dataTransfer.files;
        setSelectedFile(e.dataTransfer.files[0]);
      }
    });

    // Global Paste Support (Cmd+V / Ctrl+V)
    window.addEventListener("paste", (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData).items;
      for (const item of items) {
        if (item.kind === "file" && item.type.startsWith("image/")) {
          const blob = item.getAsFile();
          const file = new File([blob], `pasted_document_${Date.now()}.png`, { type: blob.type });
          setSelectedFile(file);
          showToast("Image pasted from clipboard!");
          break;
        }
      }
    });

    // Reset workspace
    btnReset.addEventListener("click", () => {
      mediaInput.value = "";
      setSelectedFile(null);
      state.currentRun = null;
      viewportEmpty.style.display = "flex";
      stageImg.style.display = "none";
      splitSlider.classList.remove("active");
      btnDownloadScan.style.display = "none";
      btnDownloadReport.style.display = "none";
      resetQualityDashboard();
      setSystemStatus("Ready");
      showToast("Workspace reset");
    });

    // Preset Sample Handlers
    document.querySelectorAll(".sample-chip").forEach((chip) => {
      chip.addEventListener("click", async () => {
        const sampleId = chip.getAttribute("data-sample");
        setSystemStatus("Loading sample...", true);
        try {
          const res = await fetch(`/samples/${sampleId}.jpg`);
          if (!res.ok) throw new Error("Could not load sample");
          const blob = await res.blob();
          const file = new File([blob], `${sampleId}.jpg`, { type: "image/jpeg" });
          setSelectedFile(file);
          // Auto run scan on sample click for instant gratification
          executeScan(file);
        } catch (err) {
          showToast(err.message, "✕");
          setSystemStatus("Ready");
        }
      });
    });

    // View Mode Toggle (Split Slider vs Stage Tabs)
    btnModeSplit.addEventListener("click", () => {
      state.activeMode = 'split';
      btnModeSplit.classList.add("active");
      btnModeTabs.classList.remove("active");
      stageTabsBar.style.display = "none";
      renderViewport();
    });

    btnModeTabs.addEventListener("click", () => {
      state.activeMode = 'tabs';
      btnModeTabs.classList.add("active");
      btnModeSplit.classList.remove("active");
      stageTabsBar.style.display = "flex";
      renderViewport();
    });

    // Stage Tabs Switcher
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.activeStage = btn.getAttribute("data-stage");
        renderViewport();
      });
    });

    // Render Viewport Content
    function renderViewport() {
      if (!state.currentRun) {
        viewportEmpty.style.display = "flex";
        stageImg.style.display = "none";
        splitSlider.classList.remove("active");
        return;
      }

      viewportEmpty.style.display = "none";

      if (state.activeMode === 'split') {
        stageImg.style.display = "none";
        splitSlider.classList.add("active");

        splitOriginalImg.src = state.currentRun.original;
        splitScannedImg.src = state.currentRun.scanned_document;
        syncSplitSlider(50);
      } else {
        splitSlider.classList.remove("active");
        stageImg.style.display = "block";

        const stageMap = {
          enhanced: state.currentRun.scanned_document,
          warped: state.currentRun.warped,
          contour: state.currentRun.contour,
          edges: state.currentRun.edges,
          visual_report: state.currentRun.visual_report
        };
        stageImg.src = stageMap[state.activeStage] || state.currentRun.scanned_document;
      }
    }

    // Split Slider Interactivity
    function syncSplitSlider(percent) {
      const clamped = Math.max(0, Math.min(100, percent));
      splitBeforeLayer.style.width = `${clamped}%`;
      splitHandle.style.left = `${clamped}%`;
      const containerWidth = splitSlider.offsetWidth;
      splitWrapper.style.width = `${containerWidth}px`;
    }

    let isDraggingSplit = false;
    function handleSplitMove(e) {
      if (!isDraggingSplit) return;
      const rect = splitSlider.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const percent = ((clientX - rect.left) / rect.width) * 100;
      syncSplitSlider(percent);
    }

    splitSlider.addEventListener("mousedown", (e) => {
      isDraggingSplit = true;
      handleSplitMove(e);
    });
    window.addEventListener("mousemove", handleSplitMove);
    window.addEventListener("mouseup", () => isDraggingSplit = false);

    splitSlider.addEventListener("touchstart", (e) => {
      isDraggingSplit = true;
      handleSplitMove(e);
    });
    window.addEventListener("touchmove", handleSplitMove);
    window.addEventListener("touchend", () => isDraggingSplit = false);

    window.addEventListener("resize", () => {
      if (state.activeMode === 'split') syncSplitSlider(50);
    });

    // Scan Execution
    uploadForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (state.selectedFile) executeScan(state.selectedFile);
    });

    async function executeScan(file) {
      const data = new FormData();
      data.append("media", file);

      btnScan.disabled = true;
      btnScanText.textContent = "Processing Pipeline...";
      pipelineStepper.classList.add("active");
      setSystemStatus("Processing...", true);

      // Animate pipeline stepper steps
      const steps = [
        document.getElementById("step1"),
        document.getElementById("step2"),
        document.getElementById("step3"),
        document.getElementById("step4"),
        document.getElementById("step5"),
        document.getElementById("step6"),
      ];
      steps.forEach(s => { s.className = "step-item"; });

      let currentStepIdx = 0;
      const stepTimer = setInterval(() => {
        if (currentStepIdx > 0 && currentStepIdx <= steps.length) {
          steps[currentStepIdx - 1].className = "step-item done";
        }
        if (currentStepIdx < steps.length) {
          steps[currentStepIdx].className = "step-item current";
          currentStepIdx++;
        }
      }, 180);

      try {
        const res = await fetch("/scan", { method: "POST", body: data });
        const result = await res.json();
        clearInterval(stepTimer);

        if (!res.ok) throw new Error(result.error || "Scan pipeline failed");

        steps.forEach(s => { s.className = "step-item done"; });
        setTimeout(() => pipelineStepper.classList.remove("active"), 800);

        state.currentRun = result;

        // Update downloads
        btnDownloadScan.href = result.scanned_document;
        btnDownloadScan.style.display = "inline-flex";
        btnDownloadReport.href = result.visual_report;
        btnDownloadReport.style.display = "inline-flex";

        // Render viewport & quality metrics
        renderViewport();
        updateQualityDashboard(result.quality);

        // Add to history
        addToHistory(file.name, result);

        setSystemStatus("Complete");
        showToast("Document successfully scanned & rectified!");
      } catch (err) {
        clearInterval(stepTimer);
        pipelineStepper.classList.remove("active");
        setSystemStatus("Ready");
        showToast(err.message, "✕");
      } finally {
        btnScan.disabled = false;
        btnScanText.textContent = "Run Document Scanner";
      }
    }

    // Quality Dashboard Updates
    function updateQualityDashboard(quality) {
      const passed = quality.passed;
      const banner = document.getElementById("qualityBanner");
      banner.className = passed ? "quality-banner" : "quality-banner review";
      document.getElementById("verdictIcon").textContent = passed ? "🛡️" : "⚠️";
      document.getElementById("verdictTitle").textContent = passed ? "OPTIMAL: Image Quality Passed" : "REVIEW: Advisory Quality Warnings";
      document.getElementById("verdictDesc").textContent = passed 
        ? "Document contrast, illumination, sharpness, and tilt are well within digitization tolerances." 
        : "Some capture parameters are borderline. Check the diagnostic guidance below for optimal capture.";

      // Brightness (Optimal 70-220)
      const b = quality.brightness;
      document.getElementById("valBrightness").textContent = b;
      const bFill = Math.min(100, (b / 255) * 100);
      const bBar = document.getElementById("barBrightness");
      bBar.style.width = `${bFill}%`;
      const bTag = document.getElementById("tagBrightness");
      if (b >= 70 && b <= 220) {
        bTag.className = "metric-tag";
        bTag.textContent = "Optimal";
        bBar.className = "metric-bar-fill";
      } else {
        bTag.className = "metric-tag warn";
        bTag.textContent = b < 70 ? "Dark" : "Overexposed";
        bBar.className = "metric-bar-fill warn";
      }

      // Contrast (Optimal >= 35)
      const c = quality.contrast;
      document.getElementById("valContrast").textContent = c;
      const cFill = Math.min(100, (c / 80) * 100);
      const cBar = document.getElementById("barContrast");
      cBar.style.width = `${cFill}%`;
      const cTag = document.getElementById("tagContrast");
      if (c >= 35) {
        cTag.className = "metric-tag";
        cTag.textContent = "High";
        cBar.className = "metric-bar-fill";
      } else {
        cTag.className = "metric-tag warn";
        cTag.textContent = "Low";
        cBar.className = "metric-bar-fill warn";
      }

      // Sharpness (Optimal >= 45)
      const s = quality.sharpness;
      document.getElementById("valSharpness").textContent = s;
      const sFill = Math.min(100, (s / 200) * 100);
      const sBar = document.getElementById("barSharpness");
      sBar.style.width = `${sFill}%`;
      const sTag = document.getElementById("tagSharpness");
      if (s >= 45) {
        sTag.className = "metric-tag";
        sTag.textContent = "Sharp";
        sBar.className = "metric-bar-fill";
      } else {
        sTag.className = "metric-tag bad";
        sTag.textContent = "Blurry";
        sBar.className = "metric-bar-fill bad";
      }

      // Skew (Optimal <= 8 deg)
      const sk = Math.abs(quality.skew_degrees);
      document.getElementById("valSkew").textContent = `${quality.skew_degrees}°`;
      const skFill = Math.min(100, (sk / 20) * 100);
      const skBar = document.getElementById("barSkew");
      skBar.style.width = `${skFill}%`;
      const skTag = document.getElementById("tagSkew");
      if (sk <= 8) {
        skTag.className = "metric-tag";
        skTag.textContent = "Aligned";
        skBar.className = "metric-bar-fill";
      } else {
        skTag.className = "metric-tag warn";
        skTag.textContent = "Tilted";
        skBar.className = "metric-bar-fill warn";
      }

      // Advice Checklist
      const adviceBox = document.getElementById("adviceBox");
      const adviceList = document.getElementById("adviceList");
      adviceList.innerHTML = quality.messages.map(msg => `
        <div class="advice-item">
          <span class="advice-item-icon">${passed ? "✓" : "•"}</span>
          <span>${msg}</span>
        </div>
      `).join("");
      adviceBox.style.display = "flex";
    }

    function resetQualityDashboard() {
      document.getElementById("qualityBanner").className = "quality-banner";
      document.getElementById("verdictIcon").textContent = "🛡️";
      document.getElementById("verdictTitle").textContent = "Awaiting Document Analysis";
      document.getElementById("verdictDesc").textContent = "Capture or upload an image to view automated computer vision diagnostics.";
      ["Brightness", "Contrast", "Sharpness", "Skew"].forEach(name => {
        document.getElementById(`val${name}`).textContent = "--";
        document.getElementById(`tag${name}`).textContent = "--";
        document.getElementById(`tag${name}`).className = "metric-tag";
        document.getElementById(`bar${name}`).style.width = "0%";
      });
      document.getElementById("adviceBox").style.display = "none";
    }

    // Session History Management
    function addToHistory(filename, result) {
      state.history.unshift({ filename, result, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
      if (state.history.length > 6) state.history.pop();
      renderHistory();
    }

    function renderHistory() {
      const panel = document.getElementById("historyPanel");
      const strip = document.getElementById("historyStrip");
      if (!state.history.length) {
        panel.style.display = "none";
        return;
      }
      panel.style.display = "block";
      strip.innerHTML = state.history.map((item, idx) => `
        <div class="history-card ${idx === 0 ? 'active' : ''}" data-idx="${idx}">
          <img class="history-thumb" src="${item.result.scanned_document}" alt="Thumb">
          <div>
            <div class="history-title">${item.filename}</div>
            <div class="history-time">${item.time} &bull; ${item.result.quality.passed ? 'Pass' : 'Review'}</div>
          </div>
        </div>
      `).join("");

      strip.querySelectorAll(".history-card").forEach(card => {
        card.addEventListener("click", () => {
          const idx = parseInt(card.getAttribute("data-idx"), 10);
          strip.querySelectorAll(".history-card").forEach(c => c.classList.remove("active"));
          card.classList.add("active");
          state.currentRun = state.history[idx].result;
          renderViewport();
          updateQualityDashboard(state.currentRun.quality);
        });
      });
    }

    // Copy Scanned Image to Clipboard
    btnCopyImage.addEventListener("click", async () => {
      if (!state.currentRun) return showToast("No scan to copy", "✕");
      try {
        const res = await fetch(state.currentRun.scanned_document);
        const blob = await res.blob();
        await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
        showToast("Scanned image copied to clipboard!");
      } catch (err) {
        showToast("Clipboard copy requires HTTPS/secure context", "✕");
      }
    });

    // Copy JSON Metrics
    btnCopyJson.addEventListener("click", () => {
      if (!state.currentRun) return showToast("No metrics available", "✕");
      navigator.clipboard.writeText(JSON.stringify(state.currentRun.quality, null, 2));
      showToast("Quality JSON copied to clipboard!");
    });

    // Print
    btnPrint.addEventListener("click", () => {
      if (!state.currentRun) return showToast("No document to print", "✕");
      window.print();
    });

    // Fullscreen Zoom Lightbox
    btnLightbox.addEventListener("click", () => {
      if (!state.currentRun) return showToast("Run a scan first", "✕");
      const currentSrc = state.activeMode === 'split' 
        ? state.currentRun.scanned_document 
        : (document.getElementById("stageImg").src || state.currentRun.scanned_document);
      lightboxImg.src = currentSrc;
      state.zoomScale = 1.0;
      updateLightboxZoom();
      lightboxModal.classList.add("active");
    });

    btnCloseLightbox.addEventListener("click", () => lightboxModal.classList.remove("active"));
    lightboxModal.addEventListener("click", (e) => {
      if (e.target === lightboxModal) lightboxModal.classList.remove("active");
    });

    function updateLightboxZoom() {
      lightboxImg.style.transform = `scale(${state.zoomScale})`;
    }

    btnZoomIn.addEventListener("click", () => {
      state.zoomScale = Math.min(4.0, state.zoomScale + 0.25);
      updateLightboxZoom();
    });

    btnZoomOut.addEventListener("click", () => {
      state.zoomScale = Math.max(0.5, state.zoomScale - 0.25);
      updateLightboxZoom();
    });

    btnZoomReset.addEventListener("click", () => {
      state.zoomScale = 1.0;
      updateLightboxZoom();
    });

    // Live Camera Capture Modal
    btnOpenCam.addEventListener("click", async () => {
      cameraModal.classList.add("active");
      try {
        state.cameraStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } }
        });
        cameraVideo.srcObject = state.cameraStream;
      } catch (err) {
        showToast("Camera access denied or unavailable", "✕");
        closeCamera();
      }
    });

    function closeCamera() {
      if (state.cameraStream) {
        state.cameraStream.getTracks().forEach(t => t.stop());
        state.cameraStream = null;
      }
      cameraModal.classList.remove("active");
    }

    btnCloseCam.addEventListener("click", closeCamera);
    cameraModal.addEventListener("click", (e) => {
      if (e.target === cameraModal) closeCamera();
    });

    btnShutter.addEventListener("click", () => {
      if (!state.cameraStream) return;
      cameraCanvas.width = cameraVideo.videoWidth || 1280;
      cameraCanvas.height = cameraVideo.videoHeight || 720;
      const ctx = cameraCanvas.getContext("2d");
      ctx.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);
      cameraCanvas.toBlob((blob) => {
        const file = new File([blob], `camera_scan_${Date.now()}.jpg`, { type: "image/jpeg" });
        setSelectedFile(file);
        closeCamera();
        executeScan(file);
      }, "image/jpeg", 0.95);
    });

    // Keyboard Shortcuts (Esc to close modals)
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeCamera();
        lightboxModal.classList.remove("active");
      }
    });
  </script>
</body>
</html>
"""


def _safe_output_path(url_path: str) -> Path | None:
    relative = unquote(url_path.removeprefix("/outputs/")).replace("/", os.sep)
    candidate = (OUTPUTS / relative).resolve()
    try:
        candidate.relative_to(OUTPUTS.resolve())
    except ValueError:
        return None
    return candidate


def _safe_sample_path(url_path: str) -> Path | None:
    relative = unquote(url_path.removeprefix("/samples/")).replace("/", os.sep)
    candidate = (SAMPLES / relative).resolve()
    try:
        candidate.relative_to(SAMPLES.resolve())
    except ValueError:
        return None
    return candidate


def _json(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, object]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class PaperPulseHandler(BaseHTTPRequestHandler):
    server_version = "PaperPulseHTTP/2.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/samples":
            sample_list = [
                {
                    "id": "sample_document",
                    "name": "Technical Report",
                    "description": "Standard multi-column academic report",
                    "url": "/samples/sample_document.jpg",
                },
                {
                    "id": "sample_invoice",
                    "name": "Commercial Invoice",
                    "description": "Tabular corporate invoice layout",
                    "url": "/samples/sample_invoice.jpg",
                },
                {
                    "id": "sample_receipt",
                    "name": "Store Receipt",
                    "description": "Retail transaction receipt with perspective tilt",
                    "url": "/samples/sample_receipt.jpg",
                },
            ]
            _json(self, HTTPStatus.OK, {"samples": sample_list})
            return

        if parsed.path.startswith("/samples/"):
            self._serve_sample(parsed.path)
            return

        if parsed.path.startswith("/outputs/"):
            self._serve_output(parsed.path)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/scan":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self._handle_scan()

    def _serve_sample(self, path: str) -> None:
        file_path = _safe_sample_path(path)
        if file_path is None or not file_path.exists() or not file_path.is_file():
            # If samples missing, generate them
            ensure_all_samples()
            file_path = _safe_sample_path(path)
            if file_path is None or not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "Sample not found")
                return

        content_type = mimetypes.guess_type(file_path.name)[0] or "image/jpeg"
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def _serve_output(self, path: str) -> None:
        file_path = _safe_output_path(path)
        if file_path is None or not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _handle_scan(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
            _json(self, HTTPStatus.BAD_REQUEST, {"error": "Upload must be between 1 byte and 16 MB."})
            return

        content_type = self.headers.get("Content-Type", "")
        raw_body = self.rfile.read(content_length)

        msg_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("latin-1") + raw_body
        msg = BytesParser(policy=email.policy.default).parsebytes(msg_bytes)

        file_bytes = None
        filename = None

        for part in msg.iter_parts():
            if part.get_param("name", header="content-disposition") == "media":
                filename = part.get_filename()
                file_bytes = part.get_payload(decode=True)
                break

        if not filename or file_bytes is None:
            _json(self, HTTPStatus.BAD_REQUEST, {"error": "No image file was uploaded."})
            return

        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            _json(self, HTTPStatus.BAD_REQUEST, {"error": f"Unsupported image type: {extension}"})
            return

        run_id = uuid.uuid4().hex[:12]
        UPLOADS.mkdir(parents=True, exist_ok=True)
        upload_path = UPLOADS / f"{run_id}{extension}"
        upload_path.write_bytes(file_bytes)

        output_dir = UI_RUNS / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Read input image
            image = read_image(upload_path)
            scan_result = scan_document(image)
            quality_result = analyze_quality(scan_result.warped)

            # Write all pipeline stage images for the interactive UI
            orig_output = output_dir / f"original{extension}"
            orig_output.write_bytes(file_bytes)

            scanned_path = write_image(output_dir / "scanned_document.png", scan_result.enhanced)
            warped_path = write_image(output_dir / "warped.png", scan_result.warped)

            detection_img = draw_detected_contour(scan_result)
            contour_path = write_image(output_dir / "contour.png", detection_img)

            edges_path = write_image(output_dir / "edges.png", scan_result.edges)
            report_img_path = create_visual_report(scan_result, quality_result, output_dir / "visual_report.png")
            report_json_path = save_json_report(quality_result, output_dir / "quality_report.json")

            quality = quality_result.to_dict()
        except Exception as exc:
            _json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Processing failed: {exc}"})
            return

        def as_url(path: Path) -> str:
            return "/outputs/" + path.resolve().relative_to(OUTPUTS.resolve()).as_posix()

        _json(
            self,
            HTTPStatus.OK,
            {
                "run_id": run_id,
                "original": as_url(orig_output),
                "scanned_document": as_url(scanned_path),
                "warped": as_url(warped_path),
                "contour": as_url(contour_path),
                "edges": as_url(edges_path),
                "visual_report": as_url(report_img_path),
                "quality_report": as_url(report_json_path),
                "quality": quality,
                "used_fallback": scan_result.used_fallback,
                "dimensions": {
                    "original": {"width": image.shape[1], "height": image.shape[0]},
                    "scanned": {"width": scan_result.enhanced.shape[1], "height": scan_result.enhanced.shape[0]},
                },
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write("%s - %s\n" % (self.address_string(), format % args))


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    ensure_all_samples()
    server = ThreadingHTTPServer((host, port), PaperPulseHandler)
    print(f"PaperPulse UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop the server.")
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the PaperPulse browser upload UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
