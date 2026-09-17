"""Build a simple PDF version of docs/project_report.md."""

from pathlib import Path
import textwrap
import unicodedata

from PIL import Image, ImageDraw, ImageFont


PAGE_SIZE = (1240, 1754)
MARGIN = 90
LINE_HEIGHT = 28


def _clean(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def markdown_to_pdf(markdown_path: str = "docs/project_report.md", output_path: str = "docs/project_report.pdf") -> Path:
    text = _clean(Path(markdown_path).read_text(encoding="utf-8"))
    pages: list[Image.Image] = []
    page = Image.new("RGB", PAGE_SIZE, "white")
    draw = ImageDraw.Draw(page)
    y = MARGIN

    normal = _font(22)
    heading = _font(32, bold=True)
    subheading = _font(26, bold=True)

    def new_page() -> None:
        nonlocal page, draw, y
        pages.append(page)
        page = Image.new("RGB", PAGE_SIZE, "white")
        draw = ImageDraw.Draw(page)
        y = MARGIN

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            y += LINE_HEIGHT
            continue

        current_font = normal
        wrap_width = 86
        if line.startswith("# "):
            line = line[2:]
            current_font = heading
            wrap_width = 48
            y += 8
        elif line.startswith("## "):
            line = line[3:]
            current_font = subheading
            wrap_width = 60
            y += 10
        elif line.startswith("- "):
            line = "* " + line[2:]
        elif line.startswith("|"):
            line = line.replace("|", "  ")
            wrap_width = 78

        line = line.replace("**", "").replace("`", "")
        if set(line) <= {"-", " "}:
            continue

        for wrapped in textwrap.wrap(line, width=wrap_width) or [""]:
            if y > PAGE_SIZE[1] - MARGIN:
                new_page()
            draw.text((MARGIN, y), wrapped, fill=(25, 25, 25), font=current_font)
            y += LINE_HEIGHT + (8 if current_font is not normal else 0)

    pages.append(page)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(output, "PDF", resolution=100.0, save_all=True, append_images=pages[1:])
    return output


if __name__ == "__main__":
    print(markdown_to_pdf())
