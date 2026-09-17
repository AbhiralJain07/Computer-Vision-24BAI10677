"""Browser upload UI for DocuVision."""

from __future__ import annotations

import argparse
import cgi
import json
import mimetypes
import os
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .cli import run


ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
UPLOADS = OUTPUTS / "uploads"
UI_RUNS = OUTPUTS / "ui"
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DocuVision</title>
  <style>
    :root {
      --bg: #f4f7f8;
      --panel: #ffffff;
      --ink: #172026;
      --muted: #63717a;
      --line: #d8e0e3;
      --accent: #166b59;
      --accent-2: #c84f31;
      --soft: #e9f4f1;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }
    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0;
      font-size: 32px;
      line-height: 1.1;
      font-weight: 800;
      letter-spacing: 0;
    }
    .status-pill {
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 8px 12px;
      border-radius: 8px;
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
    }
    main {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .panel-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      font-weight: 700;
    }
    .upload-panel {
      padding: 16px;
    }
    .dropzone {
      display: grid;
      place-items: center;
      min-height: 220px;
      border: 2px dashed #9eb5b1;
      border-radius: 8px;
      background: var(--soft);
      text-align: center;
      cursor: pointer;
      transition: border-color 150ms ease, background 150ms ease;
    }
    .dropzone:hover,
    .dropzone.dragover {
      border-color: var(--accent);
      background: #dcefeb;
    }
    .dropzone input {
      position: absolute;
      inline-size: 1px;
      block-size: 1px;
      opacity: 0;
      pointer-events: none;
    }
    .upload-icon {
      width: 54px;
      height: 54px;
      margin: 0 auto 10px;
      border: 2px solid var(--accent);
      border-radius: 50%;
      position: relative;
    }
    .upload-icon::before {
      content: "";
      position: absolute;
      width: 16px;
      height: 16px;
      border-left: 3px solid var(--accent);
      border-top: 3px solid var(--accent);
      transform: rotate(45deg);
      left: 17px;
      top: 14px;
    }
    .upload-icon::after {
      content: "";
      position: absolute;
      width: 3px;
      height: 25px;
      background: var(--accent);
      left: 24px;
      top: 16px;
    }
    .drop-title {
      margin: 0 0 6px;
      font-weight: 800;
      font-size: 18px;
    }
    .drop-meta {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    .file-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 44px;
      margin-top: 14px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--muted);
      overflow: hidden;
    }
    .file-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    button {
      width: 100%;
      height: 44px;
      margin-top: 14px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      font-weight: 800;
      font-size: 15px;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .message {
      min-height: 22px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }
    .message.error {
      color: var(--accent-2);
      font-weight: 700;
    }
    .results {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }
    .result-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      min-width: 0;
    }
    .result-card.wide {
      grid-column: 1 / -1;
    }
    .result-card header {
      margin: 0;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
    }
    .result-card h2 {
      margin: 0;
      font-size: 16px;
      letter-spacing: 0;
    }
    .preview {
      width: 100%;
      aspect-ratio: 4 / 3;
      background: #eef2f3;
      display: grid;
      place-items: center;
      overflow: hidden;
    }
    .preview.tall {
      aspect-ratio: 16 / 11;
    }
    .preview img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }
    .empty {
      color: var(--muted);
      font-size: 15px;
    }
    .actions {
      display: flex;
      gap: 10px;
      padding: 12px 14px;
      border-top: 1px solid var(--line);
    }
    .actions a {
      flex: 1;
      min-height: 38px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--ink);
      text-decoration: none;
      font-weight: 700;
      font-size: 14px;
    }
    .quality {
      padding: 14px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-width: 0;
    }
    .metric-label {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .metric-value {
      font-size: 20px;
      font-weight: 800;
      overflow-wrap: anywhere;
    }
    .quality-note {
      grid-column: 1 / -1;
      color: var(--muted);
      border-top: 1px solid var(--line);
      padding-top: 12px;
      line-height: 1.45;
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
      .results { grid-template-columns: 1fr; }
      .quality { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 520px) {
      .shell { width: min(100% - 20px, 1180px); padding: 16px 0; }
      h1 { font-size: 26px; }
      .quality { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <h1>DocuVision</h1>
      <div class="status-pill" id="serverStatus">Ready</div>
    </header>
    <main>
      <section class="panel">
        <div class="panel-head">Upload Media</div>
        <form class="upload-panel" id="uploadForm">
          <label class="dropzone" id="dropzone">
            <input id="media" name="media" type="file" accept="image/*">
            <span>
              <span class="upload-icon" aria-hidden="true"></span>
              <p class="drop-title">Choose image</p>
              <p class="drop-meta">JPG, PNG, WebP, BMP, TIFF</p>
            </span>
          </label>
          <div class="file-row">
            <span class="file-name" id="fileName">No file selected</span>
            <span id="fileSize"></span>
          </div>
          <button id="scanButton" type="submit" disabled>Run Scanner</button>
          <div class="message" id="message"></div>
        </form>
      </section>
      <section class="results">
        <article class="result-card">
          <header><h2>Scanned Document</h2></header>
          <div class="preview" id="scanPreview"><span class="empty">Waiting for upload</span></div>
          <div class="actions"><a id="scanDownload" href="#" download>Download</a></div>
        </article>
        <article class="result-card">
          <header><h2>Quality Metrics</h2></header>
          <div class="quality" id="qualityBox">
            <div class="metric"><div class="metric-label">Brightness</div><div class="metric-value">--</div></div>
            <div class="metric"><div class="metric-label">Contrast</div><div class="metric-value">--</div></div>
            <div class="metric"><div class="metric-label">Sharpness</div><div class="metric-value">--</div></div>
            <div class="metric"><div class="metric-label">Skew</div><div class="metric-value">--</div></div>
            <div class="quality-note">No analysis yet.</div>
          </div>
          <div class="actions"><a id="jsonDownload" href="#" download>Download JSON</a></div>
        </article>
        <article class="result-card wide">
          <header><h2>Visual Report</h2></header>
          <div class="preview tall" id="reportPreview"><span class="empty">Pipeline preview will appear here</span></div>
          <div class="actions"><a id="reportDownload" href="#" download>Download Report</a></div>
        </article>
      </section>
    </main>
  </div>
  <script>
    const form = document.getElementById("uploadForm");
    const input = document.getElementById("media");
    const dropzone = document.getElementById("dropzone");
    const button = document.getElementById("scanButton");
    const message = document.getElementById("message");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");
    const statusPill = document.getElementById("serverStatus");

    function setMessage(text, isError = false) {
      message.textContent = text;
      message.classList.toggle("error", isError);
    }

    function setSelected(file) {
      if (!file) {
        fileName.textContent = "No file selected";
        fileSize.textContent = "";
        button.disabled = true;
        return;
      }
      fileName.textContent = file.name;
      fileSize.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
      button.disabled = false;
      setMessage("");
    }

    input.addEventListener("change", () => setSelected(input.files[0]));
    dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
      if (event.dataTransfer.files.length) {
        input.files = event.dataTransfer.files;
        setSelected(input.files[0]);
      }
    });

    function imageHtml(src, alt) {
      return `<img src="${src}?t=${Date.now()}" alt="${alt}">`;
    }

    function updateQuality(report) {
      const values = [
        ["Brightness", report.brightness],
        ["Contrast", report.contrast],
        ["Sharpness", report.sharpness],
        ["Skew", `${report.skew_degrees} deg`],
      ];
      const metrics = values.map(([label, value]) => `
        <div class="metric">
          <div class="metric-label">${label}</div>
          <div class="metric-value">${value}</div>
        </div>
      `).join("");
      const verdict = report.passed ? "PASS" : "REVIEW";
      document.getElementById("qualityBox").innerHTML = `
        ${metrics}
        <div class="quality-note"><strong>${verdict}</strong>: ${report.messages.join(" ")}</div>
      `;
    }

    function setDownload(id, href) {
      const link = document.getElementById(id);
      link.href = href;
      link.removeAttribute("aria-disabled");
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = input.files[0];
      if (!file) return;

      const data = new FormData();
      data.append("media", file);
      button.disabled = true;
      statusPill.textContent = "Processing";
      setMessage("Processing image...");

      try {
        const response = await fetch("/scan", { method: "POST", body: data });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Scan failed");

        document.getElementById("scanPreview").innerHTML = imageHtml(payload.scanned_document, "Scanned document");
        document.getElementById("reportPreview").innerHTML = imageHtml(payload.visual_report, "Visual report");
        updateQuality(payload.quality);
        setDownload("scanDownload", payload.scanned_document);
        setDownload("reportDownload", payload.visual_report);
        setDownload("jsonDownload", payload.quality_report);
        statusPill.textContent = "Complete";
        setMessage("Scan complete.");
      } catch (error) {
        statusPill.textContent = "Ready";
        setMessage(error.message, true);
      } finally {
        button.disabled = false;
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


def _json(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, object]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class DocuVisionHandler(BaseHTTPRequestHandler):
    server_version = "DocuVisionHTTP/1.0"

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

        if parsed.path.startswith("/outputs/"):
            self._serve_output(parsed.path)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/scan":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self._handle_scan()

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
            _json(self, HTTPStatus.BAD_REQUEST, {"error": "Upload must be between 1 byte and 12 MB."})
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": str(content_length),
            },
        )
        item = form["media"] if "media" in form else None
        if item is None or not item.filename:
            _json(self, HTTPStatus.BAD_REQUEST, {"error": "No image file was uploaded."})
            return

        extension = Path(item.filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            _json(self, HTTPStatus.BAD_REQUEST, {"error": "Unsupported image type."})
            return

        run_id = uuid.uuid4().hex[:12]
        UPLOADS.mkdir(parents=True, exist_ok=True)
        upload_path = UPLOADS / f"{run_id}{extension}"
        upload_path.write_bytes(item.file.read())

        output_dir = UI_RUNS / run_id
        try:
            outputs = run(str(upload_path), str(output_dir))
            quality_path = outputs["quality_report"]
            quality = json.loads(Path(quality_path).read_text(encoding="utf-8"))
        except Exception as exc:
            _json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Processing failed: {exc}"})
            return

        def as_url(path: Path) -> str:
            return "/outputs/" + path.resolve().relative_to(OUTPUTS.resolve()).as_posix()

        _json(
            self,
            HTTPStatus.OK,
            {
                "scanned_document": as_url(outputs["scanned_document"]),
                "visual_report": as_url(outputs["visual_report"]),
                "quality_report": as_url(outputs["quality_report"]),
                "quality": quality,
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write("%s - %s\n" % (self.address_string(), format % args))


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), DocuVisionHandler)
    print(f"DocuVision UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop the server.")
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the DocuVision browser upload UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()

