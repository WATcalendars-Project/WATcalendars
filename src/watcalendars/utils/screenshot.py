import os
import sys
import subprocess
from typing import Optional, List

import mammoth
from playwright.sync_api import sync_playwright

# Optional heavy deps: imported lazily; if missing, we fall back to HTML+browser
try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None  # type: ignore
try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore
try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:  # pragma: no cover
    docx2pdf_convert = None  # type: ignore


BASE_STYLE = """
  body { margin: 16px; background: #ffffff; }
  .docx-container { 
    box-sizing: border-box; 
    margin: 0 auto; 
    padding: 8px; 
    width: 100%;
    max-width: 2200px; /* widen for timetable tables */
    color: #000;
    font-family: Arial, Helvetica, sans-serif; 
    font-size: 12px; 
    line-height: 1.25;
  }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #888; padding: 2px 4px; vertical-align: top; }
  p { margin: 4px 0; }
  /* try to preserve timetable grid density */
  table td p { margin: 2px 0; }
"""


def _docx_to_html(docx_path: str) -> str:
    try:
        with open(docx_path, "rb") as f:
            result = mammoth.convert_to_html(f)
            return result.value or ""
    except Exception:
        # Fallback minimal HTML so that rendering still produces a PNG placeholder
        name = os.path.basename(docx_path)
        return f"<h1 style='font-family: Arial, sans-serif'>Preview unavailable</h1><p>{name}</p>"


def _save_png_via_pdf_pipeline(docx_path: str, out_png_path: str) -> bool:
    """Use Word (docx2pdf) + PyMuPDF + Pillow to produce a single tall PNG with all pages.

    Returns False if any dependency is missing or conversion fails.
    """
    if docx2pdf_convert is None or fitz is None or Image is None:
        return False
    try:
        # Convert to a temporary PDF next to PNG output
        base_dir = os.path.dirname(out_png_path)
        base_name = os.path.splitext(os.path.basename(out_png_path))[0]
        tmp_pdf = os.path.join(base_dir, f"{base_name}.pdf")

        # Remove stale files if present
        if os.path.exists(tmp_pdf):
            try:
                os.remove(tmp_pdf)
            except Exception:
                pass

        # docx2pdf requires absolute paths on Windows
        docx_abs = os.path.abspath(docx_path)
        pdf_abs = os.path.abspath(tmp_pdf)
        docx2pdf_convert(docx_abs, pdf_abs)
        if not os.path.exists(pdf_abs):
            return False

        # Render PDF pages at higher zoom for readability
        doc = fitz.open(pdf_abs)
        images = []
        zoom = 2.0  # roughly ~144 DPI
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            mode = "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()

        if not images:
            return False

        # Stitch pages vertically into one image
        width = max(im.width for im in images)
        total_height = sum(im.height for im in images)
        combined = Image.new("RGB", (width, total_height), (255, 255, 255))
        y = 0
        for im in images:
            if im.width != width:
                im = im.resize((width, int(im.height * (width / im.width))), Image.LANCZOS)
            combined.paste(im, (0, y))
            y += im.height

        combined.save(out_png_path, format="PNG")

        # Optionally clean up the temporary PDF
        try:
            os.remove(tmp_pdf)
        except Exception:
            pass

        return True
    except Exception:
        return False


def save_docx_screenshot(
    docx_path: str,
    out_png_path: str,
    viewport_width: int = 2200,
    background_color: Optional[str] = "#ffffff",
    save_html: bool = False,
) -> bool:
    """Render a DOCX file to a full-page PNG.

    Preferred pipeline on Windows:
    1) DOCX -> PDF via Microsoft Word (docx2pdf) to preserve colors/styling
    2) PDF pages -> single tall PNG via PyMuPDF + Pillow

    Fallback: mammoth(HTML) + Playwright (may lose some table shading/colors).
    """
    try:
        os.makedirs(os.path.dirname(out_png_path), exist_ok=True)

        # 1) Try Word->PDF->PNG path first
        if _save_png_via_pdf_pipeline(docx_path, out_png_path):
            return True

        # 2) Fallback to mammoth+Playwright
        body_html = _docx_to_html(docx_path)
        html = f"""
        <!doctype html>
        <html>
        <head>
          <meta charset='utf-8'>
          <meta name='viewport' content='width=device-width, initial-scale=1'>
          <style>{BASE_STYLE}</style>
        </head>
        <body>
          <div class=\"docx-container\">{body_html}</div>
        </body>
        </html>
        """

        # Optionally save HTML next to PNG for debugging/inspection
        if save_html:
            out_html_path = os.path.splitext(out_png_path)[0] + ".html"
            try:
                with open(out_html_path, "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass

        def _render() -> None:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": viewport_width, "height": 1000})
                if background_color:
                    page.evaluate(f"document.documentElement.style.background='{background_color}'")
                page.set_content(html, wait_until="load")
                page.screenshot(path=out_png_path, full_page=True)
                browser.close()

        try:
            _render()
            return True
        except Exception:
            # Try to auto-install chromium and retry once
            try:
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
                _render()
                return True
            except Exception:
                return False
    except Exception:
        return False
