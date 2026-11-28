#!/usr/bin/env python3
"""
Builds the self-contained Interactive Book Studio & Direct Live Editor:
  «استوديو تيسير الانتفاع — محرر ومولّد الكتاب التفاعلي (١٦٢ × ٢٣٤ ملم)»

Outputs:
  1. Repo web app: viewer/editor.html
  2. Standalone Artifact HTML: <ARTIFACT_DIR>/shuja_book_editor.html

Features:
  - Direct on-page inline editing (Headings, Matn lines, Front Matter, Sharh paragraphs)
    + Rich WYSIWYG Unit Editor (Bold Matn tags, Uthmani Quran <span class="ayah">,
      <span class="ayah-ref"> [السورة: الآية], Add/Delete/Reorder paragraphs & units)
  - Full Image & Ornament Management (Remove/Replace/Toggle Cover, Basmalah Plate,
    Arabesque Chapter Banner, Three-Star Dividers, plus Insert/Resize/Position/Remove
    custom images inside any unit)
  - Exact 162mm x 234mm Chromium-parity DOM pagination engine with embedded Amiri &
    Amiri Quran TTF fonts, auto-updated running headers, independent per-page footnotes,
    auto-rebuilt Ayah Index, and auto-rebuilt 2-column General TOC
  - Direct Print-to-PDF (@page 162mm 234mm, zero margins), Standalone Print HTML export,
    and JSON project Import/Export + localStorage auto-save
"""
import base64
import io
import json
import os
import re
from PIL import Image

_ENG = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_ENG)
ARTIFACT_DIR = "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p_devbox/29cb44ab-ce55-4ed1-b550-9526f2720bd4"

FONT_DIR = "/home/antigravity/.local/share/fonts/amiri"
OUT_REPO_HTML = os.path.join(_REPO, "viewer", "editor.html")
OUT_ARTIFACT_HTML = os.path.join(ARTIFACT_DIR, "shuja_book_editor.html")


def encode_file_b64(path: str, mime: str) -> str:
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode("ascii")


def encode_cover_jpeg(img_path: str) -> str:
    im = Image.open(img_path).convert("RGB")
    im_resized = im.resize((972, 1404), Image.LANCZOS)
    buf = io.BytesIO()
    im_resized.save(buf, format="JPEG", quality=86, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    with open(os.path.join(_ENG, "book_data.json"), encoding="utf-8") as f:
        book_verbatim = json.load(f)
    with open(os.path.join(_ENG, "book_data_edited.json"), encoding="utf-8") as f:
        book_edited = json.load(f)

    assets = {
        "cover": encode_cover_jpeg(os.path.join(_ENG, "cover_front.png")),
        "basmalah_classic": encode_file_b64(os.path.join(_ENG, "basmalah.png"), "image/png"),
        "basmalah_crimson": encode_file_b64(os.path.join(_ENG, "basmalah_crimson.png"), "image/png"),
        "banner_classic": encode_file_b64(os.path.join(_ENG, "banner_classic.png"), "image/png"),
        "banner_crimson": encode_file_b64(os.path.join(_ENG, "banner_crimson.png"), "image/png"),
    }

    fonts = {
        "regular": encode_file_b64(os.path.join(FONT_DIR, "Amiri-Regular.ttf"), "font/ttf"),
        "bold": encode_file_b64(os.path.join(FONT_DIR, "Amiri-Bold.ttf"), "font/ttf"),
        "italic": encode_file_b64(os.path.join(FONT_DIR, "Amiri-Italic.ttf"), "font/ttf"),
        "quran": encode_file_b64(os.path.join(FONT_DIR, "AmiriQuran.ttf"), "font/ttf"),
    }

    # Prevent accidental </script> termination inside JSON
    safe_verbatim_json = json.dumps(book_verbatim, ensure_ascii=False).replace("</", "<\\/")
    safe_edited_json = json.dumps(book_edited, ensure_ascii=False).replace("</", "<\\/")
    safe_assets_json = json.dumps(assets, ensure_ascii=False).replace("</", "<\\/")

    html = build_studio_html(fonts, safe_assets_json, safe_edited_json, safe_verbatim_json)

    os.makedirs(os.path.dirname(OUT_REPO_HTML), exist_ok=True)
    with open(OUT_REPO_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    with open(OUT_ARTIFACT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    sz = os.path.getsize(OUT_REPO_HTML)
    print(f"Successfully built Book Studio Editor ({sz:,} bytes):")
    print(f"  - {OUT_REPO_HTML}")
    print(f"  - {OUT_ARTIFACT_HTML}")


def build_studio_html(fonts: dict, assets_json: str, edited_json: str, verbatim_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>محرر ومولّد الكتاب — تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@500;600;700;800&display=swap" rel="stylesheet">
<style id="embedded-book-fonts">
@font-face {{
  font-family: 'AmiriBook';
  src: url('{fonts["regular"]}') format('truetype');
  font-weight: 400; font-style: normal;
}}
@font-face {{
  font-family: 'AmiriBook';
  src: url('{fonts["bold"]}') format('truetype');
  font-weight: 700; font-style: normal;
}}
@font-face {{
  font-family: 'AmiriBook';
  src: url('{fonts["italic"]}') format('truetype');
  font-weight: 400; font-style: italic;
}}
@font-face {{
  font-family: 'AmiriQuranFont';
  src: url('{fonts["quran"]}') format('truetype');
  font-weight: 400; font-style: normal;
}}
</style>
<style id="book-print-css">
:root {{
  --ink: #111111;
  --accent: #111111;
  --matn-ink: #111111;
  --strong-ink: #111111;
  --ayah-ink: #111111;
  --rule-ink: #111111;
  --fn-num-ink: #111111;
  --subtle-ink: #333333;
  --paper-bg: #ffffff;
}}

body.edition-two-color {{
  --ink: #111111;
  --accent: #9b111e;
  --matn-ink: #9b111e;
  --strong-ink: #9b111e;
  --ayah-ink: #111111;
  --rule-ink: #9b111e;
  --fn-num-ink: #9b111e;
  --subtle-ink: #444444;
  --paper-bg: #ffffff;
}}

body.edition-sepia {{
  --ink: #1c1610;
  --accent: #7c2d12;
  --matn-ink: #7c2d12;
  --strong-ink: #7c2d12;
  --ayah-ink: #1c1610;
  --rule-ink: #7c2d12;
  --fn-num-ink: #7c2d12;
  --subtle-ink: #4a3d2f;
  --paper-bg: #f9f2e3;
}}

@page {{
  size: 162mm 234mm;
  margin: 0;
}}

/* Exact 162mm x 234mm Book Page & Typography CSS */
#book-root {{
  font-family: 'AmiriBook', serif;
  font-size: 16px;
  line-height: normal;
  color: var(--ink);
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  font-feature-settings: "kern" 1, "liga" 1, "mark" 1, "mkmk" 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}}

.page {{
  width: 162mm;
  height: 234mm;
  padding: 10.5mm 19mm 12.5mm 19mm;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--paper-bg);
  box-shadow: 0 10px 30px rgba(0,0,0,0.22), 0 1px 4px rgba(0,0,0,0.12);
  outline: 1px solid rgba(0,0,0,0.12);
  border: none;
  flex-shrink: 0;
  box-sizing: border-box;
}}
.page.cover-page {{ padding: 0; }}
.cover-img {{
  width: 162mm;
  height: 234mm;
  display: block;
  object-fit: cover;
}}
.page.framed-page {{ padding: 12.5mm 14mm; }}

.frame-outer {{
  width: 100%;
  height: 100%;
  border: 2.2pt solid var(--accent);
  padding: 2.5pt;
  box-sizing: border-box;
}}
.frame-inner {{
  width: 100%;
  height: 100%;
  border: 0.75pt solid var(--accent);
  padding: 12mm 10mm 10mm 10mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  text-align: center;
  box-sizing: border-box;
}}
.title-plate-main {{
  font-size: 24pt;
  font-weight: 700;
  line-height: 1.9;
  margin-top: 3mm;
  color: var(--accent);
}}
.title-plate-sub {{
  font-size: 14pt;
  margin: 10pt 0 4pt 0;
  color: var(--ink);
}}
.title-plate-desc {{
  font-size: 17pt;
  font-weight: 700;
  line-height: 1.9;
  margin-top: 8pt;
  color: var(--ink);
}}
.title-plate-author {{
  font-size: 13.5pt;
  color: var(--ink);
}}
.title-plate-author strong {{ color: var(--accent); }}
.title-plate-divider {{
  font-size: 11.2pt;
  margin-top: 10pt;
  border-top: 0.5pt solid var(--rule-ink);
  padding-top: 8pt;
}}
.title-plate-bottom {{
  width: 100%;
  display: flex;
  justify-content: space-between;
  font-size: 10.8pt;
  font-weight: 700;
  padding: 0 4mm;
  color: var(--accent);
}}

.disclaimer-box {{
  border: 1pt solid var(--accent);
  padding: 5mm 9mm;
  margin: 2mm auto;
  width: 90%;
  font-size: 12pt;
  font-weight: 700;
  line-height: 1.85;
  color: var(--ink);
}}
.colophon-source-box {{
  border-top: 0.6pt solid var(--rule-ink);
  padding-top: 5pt;
  width: 90%;
  font-size: 10.2pt;
  line-height: 1.8;
}}
.colophon-source-title {{
  font-weight: 700;
  color: var(--accent);
  font-size: 10.8pt;
  margin: 1pt 0;
}}
.colophon-accent {{ color: var(--accent); font-weight: 700; }}
.colophon-foot {{
  border-top: 0.7pt solid var(--rule-ink);
  padding-top: 4pt;
  width: 85%;
  font-size: 10.5pt;
  color: var(--accent);
  font-weight: 700;
}}

.running-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 0.8pt solid var(--rule-ink);
  padding: 2pt 0 3pt 0;
  margin-bottom: 4pt;
  font-size: 9.8pt;
  line-height: 2.05;
  flex-shrink: 0;
  overflow: visible;
}}
.rh-title {{
  color: var(--accent);
  font-weight: 700;
  white-space: nowrap;
  overflow: visible;
  line-height: 2.05;
  padding-top: 1.5pt;
}}
.rh-badge-wrap {{
  display: inline-flex;
  align-items: center;
  gap: 2.5pt;
  color: var(--accent);
  direction: ltr;
  flex-shrink: 0;
  padding-top: 1.5pt;
}}
.rh-wing-svg {{ width: 18pt; height: 9pt; display: block; color: var(--accent); }}
.rh-pill {{
  border: 0.85pt solid var(--accent);
  border-radius: 999px;
  padding: 0.5pt 7.5pt 1pt 7.5pt;
  min-width: 10.5mm;
  text-align: center;
  font-weight: 700;
  font-size: 9.5pt;
  line-height: 1.3;
  color: var(--accent);
}}

.body-frame {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: visible;
  min-height: 0;
  padding-top: 4pt;
  padding-bottom: 0;
}}

.chapter-banner {{
  width: 100%;
  margin: 0;
  text-align: center;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}}
.chapter-banner-img {{
  width: 124mm;
  height: auto;
  max-height: 28mm;
  object-fit: contain;
  display: block;
  margin: 0 auto;
}}
.chapter-banner + .preface-h,
.chapter-banner + .matn-book-title,
.chapter-banner + .toc-page-title {{
  margin-top: -5mm;
  position: relative;
  z-index: 2;
}}

.matn-zone {{
  font-size: 13.2pt;
  line-height: 1.88;
  flex-shrink: 0;
  color: var(--matn-ink);
}}
.matn-book-title {{
  text-align: center;
  font-size: 17pt;
  font-weight: 700;
  line-height: 2.05;
  padding-top: 3pt;
  margin: 0 0 4pt 0;
  color: var(--accent);
}}
.matn-bracket-title {{
  text-align: center;
  font-size: 14pt;
  font-weight: 700;
  line-height: 2.0;
  padding-top: 3pt;
  margin: 0 0 4pt 0;
  color: var(--accent);
}}
.matn-p {{
  margin: 0 0 1.5pt 0;
  text-align: justify;
  text-align-last: right;
  text-indent: 1.4em;
}}
.matn-basmalah {{
  text-align: center;
  font-family: 'AmiriQuranFont', 'AmiriBook', serif;
  font-size: 15.5pt;
  line-height: 1.95;
  margin: 1pt 0 3pt 0;
  color: var(--matn-ink);
}}
.matn-cont-dots {{
  text-align: center;
  font-size: 13.5pt;
  line-height: 1.35;
  letter-spacing: 0.5pt;
  color: var(--accent);
  margin: 1pt 0 3pt 0;
}}
.preface-h {{
  text-align: center;
  font-size: 16.5pt;
  font-weight: 700;
  line-height: 2.05;
  padding-top: 3pt;
  margin: 2pt 0 6pt 0;
  color: var(--accent);
}}
.fn-ref {{
  font-size: 0.62em;
  vertical-align: super;
  line-height: 0;
  font-weight: 700;
  margin-right: 1pt;
  color: var(--fn-num-ink);
}}
.stars-row {{
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24pt;
  margin: 4.5pt 0 3.5pt 0;
  flex-shrink: 0;
  color: var(--accent);
}}
.star-svg {{ width: 11pt; height: 11pt; display: block; color: var(--accent); }}
.custom-stars-img {{
  display: block;
  margin: 0 auto;
  max-width: 110mm;
  max-height: 14mm;
  object-fit: contain;
}}

.split-rule {{
  border: none;
  border-top: 0.75pt solid var(--rule-ink);
  margin: 4pt 0 5.5pt 0;
  flex-shrink: 0;
}}

.sharh-zone {{
  font-size: 11.4pt;
  line-height: 1.78;
  flex: 1;
  overflow: visible;
  min-height: 0;
  color: var(--ink);
}}
.sharh-p {{
  margin: 0 0 1.5pt 0;
  text-align: justify;
  text-align-last: right;
  text-indent: 1.4em;
}}
.sharh-zone.tight-fit {{ font-size: 10.95pt; line-height: 1.67; }}
.sharh-zone.tight-fit .sharh-p {{ margin-bottom: 0.5pt; }}
.sharh-p.cont {{ text-indent: 0; }}
.matn-p.split-head, .sharh-p.split-head {{ text-align-last: justify; }}
.sharh-p.poem-bayt {{ text-align: center; text-align-last: center; text-indent: 0; margin: 2pt 0; }}
.sharh-p strong, .sharh-zone strong {{ font-weight: 700; color: var(--strong-ink); }}
.ayah {{
  font-family: 'AmiriQuranFont', 'AmiriBook', serif;
  font-size: 11.4pt;
  line-height: 1.78;
  color: var(--ayah-ink);
}}
.matn-zone .ayah {{ font-size: 13.2pt; color: var(--matn-ink); }}
.ayah-ref {{
  font-family: 'AmiriBook', serif;
  font-size: 8.5pt;
  font-weight: 400;
  color: var(--subtle-ink);
  letter-spacing: 0;
  white-space: nowrap;
}}

/* Custom Unit Figures inserted by User */
.unit-figure {{
  margin: 5pt 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  position: relative;
}}
.unit-figure.align-center {{ align-items: center; text-align: center; }}
.unit-figure.align-right {{ align-items: flex-start; text-align: right; }}
.unit-figure.align-left {{ align-items: flex-end; text-align: left; }}
.unit-figure img {{
  max-width: 124mm;
  max-height: 135mm;
  height: auto;
  object-fit: contain;
  display: block;
  border-radius: 2pt;
}}
.unit-figure figcaption {{
  font-size: 9.2pt;
  line-height: 1.5;
  color: var(--subtle-ink);
  margin-top: 2.5pt;
}}

.footnote-area {{
  margin-top: auto;
  padding-top: 5pt;
  flex-shrink: 0;
}}
.footnote-rule {{
  width: 34mm;
  border-top: 0.55pt solid var(--rule-ink);
  margin-bottom: 2.5pt;
}}
.footnote-text {{
  font-size: 8.8pt;
  line-height: 1.55;
  color: var(--ink);
}}
.fn-lesson-note {{
  color: var(--subtle-ink);
  font-size: 8.4pt;
  margin-bottom: 1pt;
}}
.fn-gloss-row {{ margin-top: 0.5pt; }}
.fn-gloss-num {{ font-weight: 700; color: var(--fn-num-ink); }}
.fn-gloss-term {{ font-weight: 700; color: var(--ink); }}

.basmalah-plate-img {{
  width: 72mm;
  height: auto;
  max-height: 95mm;
  object-fit: contain;
  display: block;
  margin: 0 auto;
}}

.toc-page-title {{
  text-align: center;
  font-size: 16.5pt;
  font-weight: 700;
  line-height: 2.0;
  padding-top: 3pt;
  margin: 2pt 0 7pt 0;
  color: var(--accent);
}}
.toc-two-col {{
  display: flex;
  flex-direction: row;
  gap: 0;
  flex: 1;
  align-items: stretch;
  min-height: 0;
}}
.toc-col {{
  width: 50%;
  padding: 0;
  display: flex;
  flex-direction: column;
}}
.toc-col-right {{ padding-left: 5.5mm; border-left: 0.6pt solid var(--rule-ink); }}
.toc-col-left {{ padding-right: 5.5mm; }}
.toc-book-row {{
  font-size: 9.8pt;
  font-weight: 700;
  margin: 4pt 0 1.5pt 0;
  line-height: 1.5;
  display: flex;
  align-items: baseline;
  color: var(--accent);
}}
.toc-book-row a {{ color: var(--accent); text-decoration: none; }}
.toc-book-label {{ padding-right: 10pt; white-space: nowrap; }}
.toc-row {{
  display: flex;
  align-items: baseline;
  font-size: 8.8pt;
  line-height: 1.55;
  margin: 0.5pt 0;
}}
.toc-row a, .ayah-idx-pages a {{ color: var(--ink); text-decoration: none; }}
.toc-row-title {{ white-space: normal; max-width: 85%; }}
.toc-dots {{ flex: 1; border-bottom: 1pt dotted #555; margin: 0 3pt 3pt 3pt; min-width: 8pt; }}
.toc-pg {{ font-size: 9pt; white-space: nowrap; color: var(--accent); font-weight: 700; }}
.toc-section-center {{
  text-align: center;
  font-size: 11pt;
  font-weight: 700;
  margin: 5pt 0 2pt 0;
  color: var(--accent);
}}
.index-col-head {{
  display: flex;
  justify-content: space-between;
  font-size: 10.2pt;
  font-weight: 700;
  border-bottom: 0.6pt solid var(--rule-ink);
  padding-bottom: 2pt;
  margin-bottom: 4pt;
  color: var(--accent);
}}
.ayah-idx-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 0.3pt solid #ccc;
  padding: 2.5pt 0;
  font-size: 10pt;
  line-height: 1.6;
}}
.ayah-idx-text {{
  font-family: 'AmiriQuranFont', 'AmiriBook', serif;
  flex: 1;
  padding-left: 6pt;
  color: var(--ink);
}}
.ayah-idx-pages {{
  white-space: nowrap;
  font-size: 9.8pt;
  min-width: 14mm;
  text-align: left;
  color: var(--accent);
  font-weight: 700;
}}
</style>
<style id="studio-ui-css">
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
  font-family: 'Cairo', system-ui, sans-serif;
  background: #e5e1d8;
  color: #1f1b18;
  display: flex;
  flex-direction: column;
}}

/* Top Studio Bar */
.studio-topbar {{
  height: 54px;
  background: #1c1917;
  color: #f5f5f4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  gap: 10px;
  border-bottom: 1px solid #332e2a;
  flex-shrink: 0;
  z-index: 40;
}}
.tb-brand {{
  display: flex;
  align-items: center;
  gap: 10px;
}}
.tb-brand-title {{
  font-family: 'AmiriBook', serif;
  font-size: 1.12rem;
  font-weight: 700;
  color: #f3e8d2;
  white-space: nowrap;
}}
.tb-dim-pill {{
  font-size: 0.72rem;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.16);
  color: #d6d3d1;
  padding: 2px 9px;
  border-radius: 999px;
  white-space: nowrap;
}}
.tb-dirty-pill {{
  font-size: 0.72rem;
  padding: 2px 9px;
  border-radius: 999px;
  background: #92400e;
  color: #fef3c7;
  display: none;
  white-space: nowrap;
}}
.tb-dirty-pill.show {{ display: inline-block; }}
.tb-saved-pill {{
  font-size: 0.72rem;
  color: #a7f3d0;
  white-space: nowrap;
}}

.tb-actions {{
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}}
.s-btn {{
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.08);
  color: #f5f5f4;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: background 0.14s, border-color 0.14s;
  white-space: nowrap;
}}
.s-btn:hover {{ background: rgba(255,255,255,0.16); }}
.s-btn.primary {{
  background: #9b111e;
  border-color: #b92b38;
  color: #fff;
}}
.s-btn.primary:hover {{ background: #780c16; }}
.s-btn.emerald {{
  background: #14532d;
  border-color: #22c55e55;
  color: #ecfdf5;
}}
.s-btn.emerald:hover {{ background: #166534; }}
.s-btn.active {{
  background: #d97706;
  border-color: #f59e0b;
  color: #111;
}}
select.s-select {{
  background: #292524;
  color: #f5f5f4;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 6px;
  padding: 4px 8px;
  font-family: inherit;
  font-size: 0.77rem;
  cursor: pointer;
}}

/* Main 3-Column Studio Workspace */
.studio-workspace {{
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}}

/* Right Navigation Sidebar */
aside.studio-nav {{
  width: 270px;
  background: #24201d;
  color: #f5f5f4;
  border-left: 1px solid #3a342f;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}}
.nav-tabs {{
  display: flex;
  border-bottom: 1px solid #3a342f;
  background: #1c1917;
}}
.nav-tab {{
  flex: 1;
  padding: 9px 4px;
  text-align: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: #a8a29e;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: inherit;
}}
.nav-tab.active {{
  color: #fde68a;
  border-bottom-color: #d97706;
  background: rgba(255,255,255,0.03);
}}
.nav-panel {{
  display: none;
  flex: 1;
  flex-direction: column;
  overflow-y: auto;
  padding: 10px;
  min-height: 0;
}}
.nav-panel.active {{ display: flex; }}

.nav-search-row {{
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}}
.nav-search-row input {{
  flex: 1;
  padding: 6px 9px;
  border-radius: 6px;
  border: 1px solid #44403c;
  background: #1c1917;
  color: #fff;
  font-family: inherit;
  font-size: 0.8rem;
  outline: none;
}}
.unit-list {{
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  overflow-y: auto;
}}
.unit-item {{
  padding: 7px 9px;
  border-radius: 6px;
  margin-bottom: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 0.78rem;
  color: #e7e5e4;
  border: 1px solid transparent;
}}
.unit-item:hover {{ background: rgba(255,255,255,0.07); }}
.unit-item.active {{
  background: #9b111e;
  border-color: #f8717155;
  color: #fff;
  font-weight: 700;
}}
.unit-item-pg {{
  font-family: 'AmiriBook', serif;
  font-size: 0.85rem;
  background: rgba(0,0,0,0.28);
  padding: 1px 6px;
  border-radius: 8px;
  color: #fde68a;
  flex-shrink: 0;
}}

/* Global Assets & Front Matter Form Cards inside Sidebar */
.asset-card {{
  background: #1c1917;
  border: 1px solid #3a342f;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
}}
.asset-card-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 7px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #fde68a;
}}
.asset-thumb {{
  width: 100%;
  max-height: 92px;
  object-fit: contain;
  background: #fff;
  border-radius: 5px;
  padding: 4px;
  margin-bottom: 8px;
  display: block;
}}
.asset-row {{
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
  font-size: 0.75rem;
}}
.mini-btn {{
  padding: 4px 8px;
  border-radius: 5px;
  border: 1px solid #57534e;
  background: #292524;
  color: #f5f5f4;
  font-family: inherit;
  font-size: 0.73rem;
  cursor: pointer;
}}
.mini-btn:hover {{ background: #3f3a36; }}
.mini-btn.danger {{ border-color: #991b1b; color: #fecaca; background: #450a0a; }}
.mini-btn.danger:hover {{ background: #7f1d1d; }}
.mini-btn.accent {{ border-color: #9b111e; background: #9b111e; color: #fff; }}

.fm-label {{
  display: block;
  font-size: 0.74rem;
  color: #d6d3d1;
  margin: 8px 0 3px 0;
  font-weight: 600;
}}
.fm-input, .fm-textarea {{
  width: 100%;
  background: #1c1917;
  border: 1px solid #44403c;
  color: #fff;
  border-radius: 6px;
  padding: 6px 8px;
  font-family: 'AmiriBook', serif;
  font-size: 0.92rem;
}}
.fm-textarea {{ min-height: 62px; resize: vertical; line-height: 1.65; }}

/* Center WYSIWYG Unit Editor Pane */
.editor-pane {{
  width: 470px;
  background: #fbfaf7;
  border-left: 1px solid #d6d0c4;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}}
.editor-pane.collapsed {{ width: 0; border-left: none; }}
.ed-header {{
  padding: 10px 14px;
  background: #f3efe6;
  border-bottom: 1px solid #dfd8ca;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}}
.ed-title {{
  font-size: 0.88rem;
  font-weight: 700;
  color: #4a0810;
}}
.ed-scroll {{
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px 40px 14px;
}}
.ed-section {{
  background: #fff;
  border: 1px solid #e5dfd3;
  border-radius: 8px;
  padding: 11px 12px;
  margin-bottom: 12px;
}}
.ed-sec-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #57534e;
}}
.ed-field-row {{
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}}
.ed-input {{
  flex: 1;
  padding: 6px 9px;
  border: 1px solid #d6d0c4;
  border-radius: 6px;
  font-family: 'AmiriBook', serif;
  font-size: 1rem;
  color: #111;
  background: #fff;
}}
.ed-textarea {{
  width: 100%;
  min-height: 92px;
  padding: 8px 10px;
  border: 1px solid #d6d0c4;
  border-radius: 6px;
  font-family: 'AmiriBook', serif;
  font-size: 1.08rem;
  line-height: 1.85;
  color: #9b111e;
  resize: vertical;
}}
.ed-btn-light {{
  padding: 4px 9px;
  border-radius: 5px;
  border: 1px solid #d6d0c4;
  background: #f5f2eb;
  color: #292524;
  font-family: inherit;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
}}
.ed-btn-light:hover {{ background: #eae4d7; }}
.ed-btn-light.del {{ color: #b91c1c; border-color: #fecaca; background: #fef2f2; }}
.ed-btn-light.del:hover {{ background: #fee2e2; }}
.ed-btn-light.plum {{ background: #9b111e; color: #fff; border-color: #9b111e; }}
.ed-btn-light.plum:hover {{ background: #780c16; }}

/* Rich WYSIWYG Paragraph Card */
.para-card {{
  border: 1px solid #e5dfd3;
  border-radius: 7px;
  margin-bottom: 9px;
  background: #fff;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
}}
.para-card:focus-within {{
  border-color: #9b111e;
  box-shadow: 0 0 0 2px rgba(155,17,30,0.12);
}}
.para-bar {{
  background: #f7f4ed;
  border-bottom: 1px solid #ebe5d8;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  flex-wrap: wrap;
}}
.para-tools {{
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
}}
.fmt-btn {{
  padding: 2px 7px;
  border: 1px solid #d6d0c4;
  background: #fff;
  border-radius: 4px;
  font-family: 'Cairo', sans-serif;
  font-size: 0.72rem;
  font-weight: 700;
  color: #333;
  cursor: pointer;
}}
.fmt-btn:hover {{ background: #fbecee; border-color: #9b111e; color: #9b111e; }}
.para-rich {{
  padding: 8px 11px;
  min-height: 48px;
  font-family: 'AmiriBook', serif;
  font-size: 1.06rem;
  line-height: 1.82;
  color: #111;
  outline: none;
  text-align: justify;
}}
.para-rich strong {{ color: #9b111e; font-weight: 700; }}
.para-rich .ayah {{ font-family: 'AmiriQuranFont', 'AmiriBook', serif; color: #111; }}
.para-rich .ayah-ref {{ font-family: 'AmiriBook', serif; font-size: 0.8rem; color: #555; }}

/* Unit Custom Image Item inside Editor */
.uimg-card {{
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #faf8f4;
  border: 1px solid #e5dfd3;
  border-radius: 7px;
  padding: 8px;
  margin-bottom: 8px;
}}
.uimg-thumb {{
  width: 68px;
  height: 68px;
  object-fit: contain;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 5px;
  flex-shrink: 0;
}}
.uimg-fields {{
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 0.75rem;
}}
.uimg-row {{
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}}
.uimg-fields select, .uimg-fields input[type="text"] {{
  padding: 3px 6px;
  border: 1px solid #d6d0c4;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.74rem;
  background: #fff;
}}

/* Left Live Book Preview Area */
.preview-pane {{
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background: #dcd6ca;
}}
.preview-bar {{
  height: 40px;
  background: #ebe6dc;
  border-bottom: 1px solid #cfc8b8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  gap: 10px;
  font-size: 0.77rem;
  flex-shrink: 0;
}}
.preview-scroll {{
  flex: 1;
  overflow: auto;
  padding: 20px 14px 60px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
}}
#book-stage {{
  transform-origin: top center;
  transition: transform 0.12s ease;
}}

/* Direct-on-page interactive helpers (hidden in print) */
.page [contenteditable="true"] {{
  outline: none;
  border-radius: 2px;
  transition: background 0.12s;
}}
.page [contenteditable="true"]:hover {{
  background: rgba(155, 17, 30, 0.045);
}}
.page [contenteditable="true"]:focus {{
  background: rgba(254, 243, 199, 0.45);
  box-shadow: 0 0 0 1.5px rgba(155, 17, 30, 0.4);
}}
.active-unit-glow {{
  background: rgba(155, 17, 30, 0.04);
  border-radius: 3px;
}}

.hover-img-tools {{
  position: absolute;
  top: 6px;
  left: 6px;
  display: none;
  gap: 4px;
  background: rgba(28, 25, 23, 0.88);
  padding: 4px 6px;
  border-radius: 6px;
  z-index: 15;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}}
.img-editable-wrap {{
  position: relative;
  display: inline-block;
  max-width: 100%;
}}
.img-editable-wrap:hover .hover-img-tools,
.unit-figure:hover .hover-img-tools,
.chapter-banner:hover .hover-img-tools,
.cover-page:hover .hover-img-tools {{
  display: flex;
}}
.img-tool-btn {{
  font-family: 'Cairo', sans-serif;
  font-size: 0.68rem;
  font-weight: 700;
  color: #fff;
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 4px;
  padding: 2px 7px;
  cursor: pointer;
}}
.img-tool-btn:hover {{ background: #9b111e; }}
.img-tool-btn.rm:hover {{ background: #dc2626; }}

.toast {{
  position: fixed;
  bottom: 20px;
  left: 20px;
  background: #1c1917;
  color: #fef3c7;
  border: 1px solid #9b111e;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(0,0,0,0.28);
  opacity: 0;
  pointer-events: none;
  transform: translateY(10px);
  transition: all 0.2s;
  z-index: 100;
}}
.toast.show {{ opacity: 1; transform: translateY(0); }}

@media print {{
  @page {{
    size: 162mm 234mm;
    margin: 0 !important;
  }}
  html, body {{
    width: 162mm !important;
    height: auto !important;
    overflow: visible !important;
    background: #fff !important;
    display: block !important;
    margin: 0 !important;
    padding: 0 !important;
  }}
  body.edition-sepia {{
    --paper-bg: #ffffff;
  }}
  .studio-topbar, aside.studio-nav, .editor-pane, .preview-bar, .hover-img-tools, .toast {{
    display: none !important;
  }}
  .studio-workspace, .preview-pane, .preview-scroll {{
    display: block !important;
    position: static !important;
    width: auto !important;
    height: auto !important;
    overflow: visible !important;
    padding: 0 !important;
    margin: 0 !important;
    background: #fff !important;
    border: none !important;
  }}
  #book-stage {{
    transform: none !important;
    width: 162mm !important;
    margin: 0 !important;
    padding: 0 !important;
  }}
  #book-root {{
    display: block !important;
    gap: 0 !important;
  }}
  .page {{
    width: 162mm !important;
    height: 234mm !important;
    margin: 0 !important;
    border: none !important;
    box-shadow: none !important;
    page-break-after: always !important;
    break-after: page !important;
    background: #fff !important;
  }}
  .page:last-child {{
    page-break-after: auto !important;
    break-after: auto !important;
  }}
  .page [contenteditable="true"]:hover,
  .page [contenteditable="true"]:focus {{
    background: transparent !important;
    box-shadow: none !important;
  }}
  .active-unit-glow {{
    background: transparent !important;
  }}
}}
</style>
</head>
<body class="edition-two-color">

<!-- TOP STUDIO BAR -->
<header class="studio-topbar">
  <div class="tb-brand">
    <span class="tb-brand-title">استوديو تيسير الانتفاع</span>
    <span class="tb-dim-pill">١٦٢ × ٢٣٤ ملم</span>
    <span class="tb-dirty-pill" id="dirty-pill">يوجد تعديل — اضغط تنضيد</span>
    <span class="tb-saved-pill" id="save-status">محفوظ</span>
  </div>
  <div class="tb-actions">
    <select class="s-select" id="edition-mode-sel" title="الإصدار">
      <option value="edited">النسخة المحررة</option>
      <option value="verbatim">النسخة الحرفية الكاملة</option>
    </select>
    <select class="s-select" id="theme-sel" title="ألوان الطباعة">
      <option value="two-color">لونان (أحمر قرمزي + أسود)</option>
      <option value="classic">كلاسيكي (أبيض وأسود)</option>
      <option value="sepia">معاينة ورق قديم</option>
    </select>
    <button class="s-btn primary" id="btn-repaginate" title="إعادة تنضيد الصفحات والفهارس (Ctrl+Enter)">⟳ تنضيد الكتاب</button>
    <button class="s-btn emerald" id="btn-print-pdf" title="حفظ الكتاب كملف PDF بمقاس 162×234 ملم">🖨️ توليد PDF</button>
    <button class="s-btn" id="btn-export-html" title="تصدير ملف HTML منضد كامل جاهز للطباعة">📄 تصدير HTML</button>
    <button class="s-btn" id="btn-export-json" title="تصدير نسخة JSON للمشروع">💾 حفظ JSON</button>
    <button class="s-btn" id="btn-import-json" title="استيراد ملف JSON">📂 استيراد</button>
    <button class="s-btn" id="btn-toggle-editor" title="إظهار / إخفاء لوحة تحرير الوحدة">✏️ المحرر</button>
  </div>
</header>

<!-- MAIN 3-COLUMN WORKSPACE -->
<div class="studio-workspace">

  <!-- RIGHT: UNITS / IMAGES / FRONT MATTER DRAWER -->
  <aside class="studio-nav">
    <div class="nav-tabs">
      <button class="nav-tab active" data-tab="units">الوحدات (<span id="unit-count-lbl">0</span>)</button>
      <button class="nav-tab" data-tab="images">الصور والزخارف</button>
      <button class="nav-tab" data-tab="front">الغلاف والصدارة</button>
    </div>

    <!-- Tab 1: Units -->
    <div class="nav-panel active" id="panel-units">
      <div class="nav-search-row">
        <input type="text" id="unit-search" placeholder="ابحث في الفصول والوحدات...">
        <button class="mini-btn accent" id="btn-add-unit" title="إضافة فصل أو وحدة جديدة">+ وحدة</button>
      </div>
      <ul class="unit-list" id="unit-list"></ul>
    </div>

    <!-- Tab 2: Book Plates & Ornaments -->
    <div class="nav-panel" id="panel-images">
      <div class="asset-card">
        <div class="asset-card-head">
          <span>١. غلاف الكتاب (ص ١)</span>
          <label style="font-size:0.72rem; cursor:pointer;"><input type="checkbox" id="cfg-show-cover" checked> إظهار</label>
        </div>
        <img class="asset-thumb" id="thumb-cover" alt="الغلاف">
        <div class="asset-row">
          <button class="mini-btn accent" onclick="triggerGlobalImgUpload('cover_data_url')">تغيير / رفع صورة</button>
          <button class="mini-btn" onclick="resetGlobalImg('cover_data_url')">الافتراضي</button>
        </div>
      </div>

      <div class="asset-card">
        <div class="asset-card-head">
          <span>٢. لوحة البسملة الخطية (ص ٤)</span>
          <label style="font-size:0.72rem; cursor:pointer;"><input type="checkbox" id="cfg-show-basmalah" checked> إظهار</label>
        </div>
        <img class="asset-thumb" id="thumb-basmalah" alt="البسملة">
        <div class="asset-row">
          <button class="mini-btn accent" onclick="triggerGlobalImgUpload('basmalah_data_url')">تغيير / رفع صورة</button>
          <button class="mini-btn" onclick="resetGlobalImg('basmalah_data_url')">الافتراضي</button>
        </div>
        <div class="asset-row">
          <span>العرض: <strong id="lbl-basmalah-w">72</strong> ملم</span>
          <input type="range" id="cfg-basmalah-w" min="40" max="115" value="72" style="flex:1;">
        </div>
      </div>

      <div class="asset-card">
        <div class="asset-card-head">
          <span>٣. أفريز رءوس الفصول والفهارس</span>
          <label style="font-size:0.72rem; cursor:pointer;"><input type="checkbox" id="cfg-show-banner" checked> إظهار</label>
        </div>
        <img class="asset-thumb" id="thumb-banner" alt="الأفريز">
        <div class="asset-row">
          <button class="mini-btn accent" onclick="triggerGlobalImgUpload('banner_data_url')">تغيير / رفع صورة</button>
          <button class="mini-btn" onclick="resetGlobalImg('banner_data_url')">الافتراضي</button>
        </div>
        <div class="asset-row">
          <span>العرض: <strong id="lbl-banner-w">124</strong> ملم</span>
          <input type="range" id="cfg-banner-w" min="70" max="126" value="124" style="flex:1;">
        </div>
      </div>

      <div class="asset-card">
        <div class="asset-card-head">
          <span>٤. فواصل النجمات الثلاث</span>
          <label style="font-size:0.72rem; cursor:pointer;"><input type="checkbox" id="cfg-show-stars" checked> إظهار</label>
        </div>
        <div class="asset-row">
          <button class="mini-btn accent" onclick="triggerGlobalImgUpload('stars_data_url')">رفع صورة فاصل</button>
          <button class="mini-btn" onclick="resetGlobalImg('stars_data_url')">النجمات الافتراضية</button>
        </div>
      </div>

      <div class="asset-card">
        <div class="asset-card-head"><span>٥. صفحات الصدارة والتذييل</span></div>
        <label style="font-size:0.75rem; display:block; margin-bottom:4px; cursor:pointer;">
          <input type="checkbox" id="cfg-show-p2" checked> إظهار صفحة العنوان الداخلية (ص ٢)
        </label>
        <label style="font-size:0.75rem; display:block; margin-bottom:4px; cursor:pointer;">
          <input type="checkbox" id="cfg-show-p3" checked> إظهار صفحة المنهج والحواشي (ص ٣)
        </label>
        <label style="font-size:0.75rem; display:block; cursor:pointer;">
          <input type="checkbox" id="cfg-show-p4" checked> إظهار صفحة لوحة البسملة (ص ٤)
        </label>
      </div>

      <button class="mini-btn danger" id="btn-reset-all" style="width:100%; padding:8px;">↺ استعادة الكتاب الأصلي بالكامل (تصفير التعديلات)</button>
    </div>

    <!-- Tab 3: Front Matter Text -->
    <div class="nav-panel" id="panel-front">
      <label class="fm-label">عنوان الكتاب الرئيسي</label>
      <input class="fm-input" id="fm-title">
      <label class="fm-label">العنوان الفرعي (بين قوسين)</label>
      <input class="fm-input" id="fm-subtitle">
      <label class="fm-label">وصف الطبعة (ص ٢)</label>
      <textarea class="fm-textarea" id="fm-p2desc"></textarea>
      <label class="fm-label">اسم الشيخ الشارح</label>
      <input class="fm-input" id="fm-author-sharh">
      <label class="fm-label">عبارة الدعاء أسفل اسم الشارح</label>
      <input class="fm-input" id="fm-author-dua">
      <label class="fm-label">نسبة المتن للإمام أبي شجاع</label>
      <textarea class="fm-textarea" id="fm-matn-credit"></textarea>
      <label class="fm-label">نص تعريف المنهج (ص ٣)</label>
      <textarea class="fm-textarea" id="fm-p3disc" style="min-height:84px;"></textarea>
      <label class="fm-label">مصدر غريب الألفاظ (ص ٣)</label>
      <textarea class="fm-textarea" id="fm-glossary-src"></textarea>
    </div>
  </aside>

  <!-- CENTER: FOCUSED WYSIWYG UNIT & IMAGE EDITOR -->
  <section class="editor-pane" id="editor-pane">
    <div class="ed-header">
      <span class="ed-title" id="ed-unit-label">محرر الوحدة</span>
      <div style="display:flex; gap:4px;">
        <button class="ed-btn-light" id="btn-move-unit-up" title="نقل الوحدة لأعلى">↑</button>
        <button class="ed-btn-light" id="btn-move-unit-down" title="نقل الوحدة لأسفل">↓</button>
        <button class="ed-btn-light" id="btn-jump-unit-page" title="عرض صفحة الوحدة">👁 للّصفحة</button>
        <button class="ed-btn-light del" id="btn-del-unit" title="حذف هذه الوحدة">🗑 حذف</button>
      </div>
    </div>

    <div class="ed-scroll" id="ed-scroll">
      <!-- Headings & Flags -->
      <div class="ed-section">
        <div class="ed-sec-head">
          <span>العناوين والخصائص</span>
          <label style="font-size:0.74rem; font-weight:600; cursor:pointer;">
            <input type="checkbox" id="ed-fasl-end"> ختم بنجمات ٣
          </label>
        </div>
        <div class="ed-field-row">
          <span style="font-size:0.74rem; color:#666; min-width:72px;">عنوان باب:</span>
          <input class="ed-input" id="ed-toc-book" placeholder="اختياري (مثال: بيان عقيدة أهل السنة...)">
        </div>
        <div class="ed-field-row">
          <span style="font-size:0.74rem; color:#666; min-width:72px;">عنوان فصل:</span>
          <input class="ed-input" id="ed-toc-fasl" placeholder="[ عنوان الوحدة أو الموضوع ]">
        </div>
        <div class="ed-field-row" style="margin-bottom:0;">
          <span style="font-size:0.74rem; color:#666; min-width:72px;">بيان اللقاء:</span>
          <input class="ed-input" id="ed-lesson-note" placeholder="اختياري (حاشية رقم اللقاء للحرفية)">
        </div>
      </div>

      <!-- Matn Editor -->
      <div class="ed-section" id="ed-matn-section">
        <div class="ed-sec-head">
          <span>المَتْنُ المَشْكُولُ (أعلى الصفحة)</span>
          <button class="ed-btn-light" id="btn-dots-matn" title="تعيين نقاط استمرار">نقاط استمرار (....)</button>
        </div>
        <textarea class="ed-textarea" id="ed-matn-text" placeholder="أدخل سطور المتن (سطر لكل فقرة)..."></textarea>
      </div>

      <!-- Custom Unit Images -->
      <div class="ed-section">
        <div class="ed-sec-head">
          <span>الصور داخل هذه الوحدة (<span id="ed-img-count">0</span>)</span>
          <button class="ed-btn-light plum" id="btn-add-unit-img">+ إضافة صورة هنا</button>
        </div>
        <div id="ed-unit-images-list"></div>
      </div>

      <!-- Sharh Rich Paragraphs -->
      <div class="ed-section">
        <div class="ed-sec-head">
          <span>الشَّرْحُ (فقرات تفاعلية)</span>
          <button class="ed-btn-light plum" id="btn-add-para">+ فقرة شرح جديدة</button>
        </div>
        <div id="ed-sharh-paras-list"></div>
      </div>

      <!-- Gloss Footnotes -->
      <div class="ed-section">
        <div class="ed-sec-head">
          <span>حواشي غريب المتن لهذه الوحدة (<span id="ed-gloss-count">0</span>)</span>
          <button class="ed-btn-light" id="btn-add-gloss">+ إضافة حاشية</button>
        </div>
        <div id="ed-gloss-list"></div>
      </div>
    </div>
  </section>

  <!-- LEFT: LIVE EXACT 162mm x 234mm BOOK PREVIEW -->
  <section class="preview-pane">
    <div class="preview-bar">
      <div style="display:flex; align-items:center; gap:8px;">
        <strong>المعاينة الحية:</strong>
        <span id="preview-stats">جارٍ التحميل...</span>
        <span style="color:#666;">| انقر على أي نص في الصفحة للتعديل المباشر</span>
      </div>
      <div style="display:flex; align-items:center; gap:6px;">
        <button class="ed-btn-light" id="btn-prev-pg">السابق</button>
        <input type="number" id="jump-pg-in" min="1" value="1" style="width:54px; text-align:center; padding:2px 4px; border:1px solid #bbb; border-radius:4px;">
        <button class="ed-btn-light" id="btn-next-pg">التالي</button>
        <select id="zoom-sel" style="padding:2px 6px; border:1px solid #bbb; border-radius:4px; font-family:inherit; font-size:0.75rem;">
          <option value="0.65">٦٥٪</option>
          <option value="0.78" selected>٧٨٪</option>
          <option value="0.9">٩٠٪</option>
          <option value="1">١٠٠٪ (مقاس حقيقي)</option>
        </select>
      </div>
    </div>

    <div class="preview-scroll" id="preview-scroll">
      <div id="book-stage">
        <div id="book-root"></div>
      </div>
    </div>
  </section>
</div>

<!-- Hidden File Inputs -->
<input type="file" id="file-img-picker" accept="image/*" style="display:none;">
<input type="file" id="file-json-picker" accept="application/json,.json" style="display:none;">
<div class="toast" id="toast"></div>

<script>
const DEFAULT_ASSETS = {assets_json};
const BASE_EDITED_DATA = {edited_json};
const BASE_VERBATIM_DATA = {verbatim_json};
</script>
<script>
(function() {{
  const EDIGITS = '٠١٢٣٤٥٦٧٨٩';
  const toE = (n) => String(n).replace(/[0-9]/g, d => EDIGITS[+d]);
  const esc = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const deepClone = (obj) => JSON.parse(JSON.stringify(obj));

  const STAR_SVG = '<svg class="star-svg" viewBox="0 0 100 100"><g transform="translate(50,50)"><circle r="9" fill="currentColor"/>' +
    [0,45,90,135,180,225,270,315].map(a => '<path d="M0,-12 C6,-28 8,-44 0,-48 C-8,-44 -6,-28 0,-12 Z" fill="currentColor" transform="rotate('+a+')"/>').join('') +
    '</g></svg>';
  const WING_SVG = '<svg class="rh-wing-svg" viewBox="0 0 28 12">' +
    '<line x1="2" y1="2.5" x2="26" y2="2.5" stroke="currentColor" stroke-width="0.95"/>' +
    '<line x1="0" y1="6" x2="28" y2="6" stroke="currentColor" stroke-width="0.95"/>' +
    '<line x1="2" y1="9.5" x2="26" y2="9.5" stroke="currentColor" stroke-width="0.95"/>' +
    '</svg>';

  const STORAGE_KEY_PREFIX = 'shuja_studio_v2_';
  let currentMode = 'edited';
  let currentTheme = 'two-color';
  let currentZoom = 0.78;
  let activeUnitIdx = 0;
  let dirty = false;
  let isPaginating = false;
  let repagTimer = null;

  function defaultConfig() {{
    return {{
      show_cover: true,
      show_p2: true,
      show_p3: true,
      show_p4: true,
      show_basmalah: true,
      show_banner: true,
      show_stars: true,
      cover_data_url: null,
      basmalah_data_url: null,
      banner_data_url: null,
      stars_data_url: null,
      basmalah_width_mm: 72,
      banner_width_mm: 124,
    }};
  }}

  function defaultFrontMatter(mode) {{
    const isEd = mode === 'edited';
    return {{
      title: 'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ',
      subtitle: '( الْمُسَمَّى بِـ « غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ » )',
      p2_desc: isEd
        ? 'تَفْرِيغٌ مُحَرَّرٌ مُهَذَّبٌ لِمُحَاضَرَاتِ الشَّيْخِ فِي شَرْحِ مَتْنِ أَبِي شُجَاعٍ'
        : 'التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِدُرُوسِ شَرْحِ مَتْنِ أَبِي شُجَاعٍ',
      p2_right: isEd ? '٢٥ مُحَاضَرَةً مُهَذَّبَةً' : '٢٥ لِقَاءً صَوْتِيًّا كَامِلاً',
      author_sharh: 'أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ',
      author_dua: '( حَفِظَهُ اللهُ تَعَالَى وَنَفَعَ بِعِلْمِهِ )',
      matn_credit: 'وَالْمَتْنُ لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ (٤٣٣ – ٥٩٣ هـ)',
      p3_disc: isEd
        ? 'أُعِدَّ هَذَا الْكِتَابُ بِتَفْرِيغِ مُحَاضَرَاتِ الشَّيْخِ الشَّارِحِ بِإِثْبَاتِ كَلاَمِهِ كَامِلاً بِلَفْظِهِ دُونَ تَبْدِيلٍ أَوِ اخْتِصَارٍ، مَعَ الاقْتِصَارِ عَلَى مُقَدِّمَةِ اللِّقَاءِ الأَوَّلِ وَخَاتِمَةِ اللِّقَاءِ الأَخِيرِ وَتَهْذِيبِ التَّكْرَارِ اللَّفْظِيِّ الْمُتَتَابِعِ فَحَسْبُ.'
        : 'أُعِدَّ هَذَا الْكِتَابُ بِإِثْبَاتِ كَلاَمِ الشَّيْخِ الشَّارِحِ كَامِلاً كَمَا أُلْقِيَ دُونَ حَذْفٍ أَوْ اخْتِصَارٍ ، مَعَ إِثْبَاتِ مَتْنِ أَبِي شُجَاعٍ مَضْبُوطاً بِالشَّكْلِ أَعْلَى الصَّفْحَةِ مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ أَسْفَلَهُ',
      glossary_source: '«الأَنوَارُ عَلَى غَايَةِ الاِخْتِصَارِ» لِجَامِعِهِ عَبْدِ الرَّحْمَنِ مُحَمَّدٍ نُورِ الدِّينِ'
    }};
  }}

  function ensureBookSchema(raw, mode) {{
    const d = deepClone(raw);
    if (!d.book_config) d.book_config = defaultConfig();
    else d.book_config = Object.assign(defaultConfig(), d.book_config);
    if (!d.front_matter) d.front_matter = defaultFrontMatter(mode);
    else d.front_matter = Object.assign(defaultFrontMatter(mode), d.front_matter);
    if (d.glossary_source && !d.front_matter.glossary_source) d.front_matter.glossary_source = d.glossary_source;
    for (const u of d.units) {{
      if (!Array.isArray(u.matn_lines)) u.matn_lines = [];
      if (!Array.isArray(u.sharh_paras_html)) u.sharh_paras_html = [];
      if (!Array.isArray(u.glosses)) u.glosses = [];
      if (!Array.isArray(u.images)) u.images = [];
    }}
    return d;
  }}

  function loadBook(mode) {{
    try {{
      const saved = localStorage.getItem(STORAGE_KEY_PREFIX + mode);
      if (saved) return ensureBookSchema(JSON.parse(saved), mode);
    }} catch (e) {{}}
    return ensureBookSchema(mode === 'edited' ? BASE_EDITED_DATA : BASE_VERBATIM_DATA, mode);
  }}

  let bookData = loadBook(currentMode);

  function saveToLocalStorage() {{
    try {{
      localStorage.setItem(STORAGE_KEY_PREFIX + currentMode, JSON.stringify(bookData));
      document.getElementById('save-status').textContent = 'محفوظ محلياً';
    }} catch (e) {{
      document.getElementById('save-status').textContent = 'تحذير: حجم الصور كبير للحفظ التلقائي (استخدم حفظ JSON)';
    }}
  }}

  function markDirty(autoSchedule = false) {{
    dirty = true;
    document.getElementById('dirty-pill').classList.add('show');
    saveToLocalStorage();
    if (autoSchedule) {{
      clearTimeout(repagTimer);
      repagTimer = setTimeout(() => paginateAndRender(), 750);
    }}
  }}

  function clearDirty() {{
    dirty = false;
    document.getElementById('dirty-pill').classList.remove('show');
  }}

  function showToast(msg) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._tm);
    t._tm = setTimeout(() => t.classList.remove('show'), 2600);
  }}

  // Sanitize rich HTML paragraph from contenteditable so only clean book tags survive
  function sanitizeParaHtml(rawHtml) {{
    const tmp = document.createElement('div');
    tmp.innerHTML = rawHtml.replace(/<div><br><\\/div>/gi, ' ').replace(/<br\\s*\\/?>/gi, ' ');
    function walk(node) {{
      if (node.nodeType === Node.TEXT_NODE) return esc(node.textContent);
      if (node.nodeType !== Node.ELEMENT_NODE) return '';
      const tag = node.tagName.toLowerCase();
      const cls = (node.getAttribute('class') || '').split(/\\s+/);
      let inner = '';
      for (const ch of node.childNodes) inner += walk(ch);
      if (tag === 'strong' || tag === 'b') return '<strong>' + inner + '</strong>';
      if (cls.includes('ayah')) return '<span class="ayah">' + inner + '</span>';
      if (cls.includes('ayah-ref')) return '<span class="ayah-ref">' + inner + '</span>';
      if (tag === 'p' || tag === 'div') return inner + ' ';
      return inner;
    }}
    return walk(tmp).replace(/\\s+/g, ' ').trim();
  }}

  // ==================== EXACT 162mm x 234mm PAGINATION ENGINE ====================
  let unitPageMap = new Map();

  async function renderFullBook(data, theme) {{
    const root = document.getElementById('book-root');
    const stage = document.getElementById('book-stage');
    const prevTransform = stage.style.transform;
    stage.style.transform = 'none';

    document.body.classList.remove('edition-two-color', 'edition-sepia');
    if (theme === 'two-color') document.body.classList.add('edition-two-color');
    else if (theme === 'sepia') document.body.classList.add('edition-sepia');

    root.innerHTML = '';
    unitPageMap = new Map();

    await Promise.all([
      document.fonts.load('400 12pt AmiriBook'),
      document.fonts.load('700 12pt AmiriBook'),
      document.fonts.load('italic 400 12pt AmiriBook'),
      document.fonts.load('400 12pt AmiriQuranFont'),
    ]);
    await document.fonts.ready;

    const cfg = data.book_config || defaultConfig();
    const fm = data.front_matter || defaultFrontMatter(data.mode);
    const isClassicImg = (theme === 'classic');

    const coverUrl = cfg.cover_data_url || DEFAULT_ASSETS.cover;
    const basmalahUrl = cfg.basmalah_data_url || (isClassicImg ? DEFAULT_ASSETS.basmalah_classic : DEFAULT_ASSETS.basmalah_crimson);
    const bannerUrl = cfg.banner_data_url || (isClassicImg ? DEFAULT_ASSETS.banner_classic : DEFAULT_ASSETS.banner_crimson);

    // Preload all active image URLs (default + unit custom images) BEFORE measuring
    const urlsToDecode = [coverUrl, basmalahUrl, bannerUrl];
    if (cfg.stars_data_url) urlsToDecode.push(cfg.stars_data_url);
    for (const u of data.units) {{
      for (const im of (u.images || [])) {{
        if (im && im.data_url) urlsToDecode.push(im.data_url);
      }}
    }}
    await Promise.all(urlsToDecode.map(u => new Promise(res => {{
      const im = new Image();
      im.onload = () => (im.decode ? im.decode().catch(() => {{}}).finally(res) : res());
      im.onerror = res;
      im.src = u;
    }})));

    const CHAPTER_BANNER_HTML = cfg.show_banner
      ? '<div class="chapter-banner">' +
          '<div class="hover-img-tools">' +
            '<button class="img-tool-btn" onclick="triggerGlobalImgUpload(\\'banner_data_url\\')">تغيير الأفريز</button>' +
            '<button class="img-tool-btn rm" onclick="toggleGlobalAsset(\\'show_banner\\', false)">إزالة</button>' +
          '</div>' +
          '<img class="chapter-banner-img" style="width:' + (cfg.banner_width_mm || 124) + 'mm;" src="' + bannerUrl + '" alt="">' +
        '</div>'
      : '';

    const THREE_STARS_HTML = cfg.show_stars
      ? (cfg.stars_data_url
          ? '<div class="stars-row"><img class="custom-stars-img" src="' + cfg.stars_data_url + '" alt=""></div>'
          : '<div class="stars-row">' + STAR_SVG + STAR_SVG + STAR_SVG + '</div>')
      : '';

    function tokenizeHtml(htmlStr) {{
      const tmp = document.createElement('div');
      tmp.innerHTML = htmlStr;
      const atoms = [];
      function pushTextWords(str, wrap) {{
        const parts = str.split(/(\\s+)/);
        for (const p of parts) {{
          if (!p) continue;
          if (/^\\s+$/.test(p)) {{
            if (atoms.length) atoms[atoms.length - 1].trail = ' ';
          }} else if (atoms.length && !atoms[atoms.length - 1].trail && /^[.،؛:؟!»)\]]+$/.test(p)) {{
            atoms[atoms.length - 1].postPunct = (atoms[atoms.length - 1].postPunct || '') + p;
          }} else {{
            atoms.push({{ text: p, wrap: wrap, trail: '', postPunct: '' }});
          }}
        }}
      }}
      function walk(node, wrap) {{
        if (node.nodeType === Node.TEXT_NODE) {{
          pushTextWords(node.textContent, wrap);
        }} else if (node.nodeType === Node.ELEMENT_NODE) {{
          const tag = node.tagName.toLowerCase();
          const cls = node.getAttribute('class') || '';
          const clsList = cls.split(/\\s+/).filter(Boolean);
          if (clsList.includes('ayah-ref')) {{
            const refTxt = node.textContent.trim().replace(/\\s+/g, '\\u00A0');
            if (refTxt) {{
              if (atoms.length) {{
                atoms[atoms.length - 1].suffixRef = refTxt;
                atoms[atoms.length - 1].trail = '';
              }} else {{
                atoms.push({{ text: refTxt, wrap: [...wrap, {{ tag, cls }}], trail: '', postPunct: '' }});
              }}
            }}
            return;
          }}
          if (clsList.includes('ayah')) {{
            const wordsCount = node.textContent.trim().split(/\\s+/).filter(Boolean).length;
            if (wordsCount <= 42) {{
              atoms.push({{ text: node.textContent.trim(), wrap: [...wrap, {{ tag, cls }}], trail: '', postPunct: '' }});
              return;
            }}
          }}
          for (const ch of node.childNodes) walk(ch, [...wrap, {{ tag, cls }}]);
        }}
      }}
      for (const ch of tmp.childNodes) walk(ch, []);
      return atoms;
    }}

    function joinAtoms(atoms) {{
      if (!atoms.length) return '';
      let out = '';
      let openStack = [];
      const closeAll = (toLevel) => {{
        while (openStack.length > toLevel) out += '</' + openStack.pop().tag + '>';
      }};
      for (let i = 0; i < atoms.length; i++) {{
        const a = atoms[i];
        let matchLen = 0;
        while (matchLen < openStack.length && matchLen < a.wrap.length &&
               openStack[matchLen].tag === a.wrap[matchLen].tag &&
               openStack[matchLen].cls === a.wrap[matchLen].cls) matchLen++;
        closeAll(matchLen);
        for (let j = matchLen; j < a.wrap.length; j++) {{
          const w = a.wrap[j];
          out += '<' + w.tag + (w.cls ? ' class="' + w.cls + '"' : '') + '>';
          openStack.push(w);
        }}
        out += esc(a.text);
        if (a.suffixRef) {{
          closeAll(0);
          out += '\\u00A0<span class="ayah-ref">' + esc(a.suffixRef) + '</span>';
        }}
        if (a.postPunct) {{
          if (openStack.some(w => w.cls && w.cls.includes('ayah'))) {{
            const closeIdx = openStack.findIndex(w => w.cls && w.cls.includes('ayah'));
            closeAll(closeIdx);
          }}
          out += esc(a.postPunct);
        }}
        if (i < atoms.length - 1) out += a.trail;
      }}
      closeAll(0);
      return out;
    }}

    const BOOK_HDR_TITLE = fm.title || 'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ';
    let activeSectionTitle = 'مُقَدِّمَةُ الْكِتَابِ';
    let pageCounter = 0;

    function makeHeaderHtml(pNum, sectionTitleOverride = null) {{
      const eNum = toE(pNum);
      const isEven = (pNum % 2 === 0);
      const badgeHtml = '<span class="rh-badge-wrap">' + WING_SVG + '<span class="rh-pill">' + eNum + '</span>' + WING_SVG + '</span>';
      const titleStr = isEven ? BOOK_HDR_TITLE : (sectionTitleOverride || activeSectionTitle || BOOK_HDR_TITLE);
      const titleHtml = '<span class="rh-title">' + esc(titleStr) + '</span>';
      return '<div class="running-header">' + (isEven ? (badgeHtml + titleHtml) : (titleHtml + badgeHtml)) + '</div>';
    }}

    function createPage({{ framed = false, cover = false, skipHeader = false, centerTitle = null }} = {{}}) {{
      pageCounter++;
      const pNum = pageCounter;
      const el = document.createElement('div');
      let cls = 'page';
      if (framed) cls += ' framed-page';
      if (cover) cls += ' cover-page';
      el.className = cls;
      el.id = 'pg-' + pNum;
      if (cover) {{
        root.appendChild(el);
        return {{ el, bodyFrame: null, pNum }};
      }}
      if (!skipHeader) el.innerHTML = makeHeaderHtml(pNum, centerTitle);
      const bodyFrame = document.createElement('div');
      bodyFrame.className = 'body-frame';
      el.appendChild(bodyFrame);
      root.appendChild(el);
      return {{
        el, bodyFrame, pNum,
        headerEl: el.querySelector('.running-header'),
        pageFnNum: 0,
        pageGlossaryIds: new Set(),
        pageGlossaryTerms: new Set(),
        lessonNoteText: null,
        glossaryNotes: [],
      }};
    }}

    function setPageOddHeaderTitle(pageObj, rawTitle) {{
      if (!pageObj || !pageObj.headerEl || pageObj.pNum % 2 === 0) return;
      const cleaned = String(rawTitle || '').replace(/^\\[\\s*|\\s*\\]$/g, '').trim();
      if (!cleaned) return;
      activeSectionTitle = cleaned;
      const tEl = pageObj.headerEl.querySelector('.rh-title');
      if (tEl) tEl.textContent = cleaned;
    }}

    // 1. FRONT MATTER
    if (cfg.show_cover) {{
      const {{ el }} = createPage({{ cover: true, skipHeader: true }});
      el.innerHTML =
        '<div class="hover-img-tools">' +
          '<button class="img-tool-btn" onclick="triggerGlobalImgUpload(\\'cover_data_url\\')">تغيير الغلاف</button>' +
          '<button class="img-tool-btn rm" onclick="toggleGlobalAsset(\\'show_cover\\', false)">شيل الغلاف</button>' +
        '</div>' +
        '<img class="cover-img" src="' + coverUrl + '" alt="غلاف الكتاب">';
    }}

    if (cfg.show_p2) {{
      const {{ bodyFrame }} = createPage({{ framed: true, skipHeader: true }});
      bodyFrame.innerHTML =
        '<div class="frame-outer"><div class="frame-inner">' +
          '<div style="width:100%;">' +
            '<div class="title-plate-main" contenteditable="true" data-fm="title">' + esc(fm.title) + '</div>' +
            '<div class="title-plate-sub" contenteditable="true" data-fm="subtitle">' + esc(fm.subtitle) + '</div>' +
            '<div class="title-plate-desc" contenteditable="true" data-fm="p2_desc">' + esc(fm.p2_desc) + '</div>' +
          '</div>' +
          '<div style="font-size: 12pt; line-height: 1.95; width:92%;">' +
            '<div class="title-plate-author">لِفَضِيلَةِ الشَّيْخِ <strong contenteditable="true" data-fm="author_sharh">' + esc(fm.author_sharh) + '</strong></div>' +
            '<div style="font-size: 11pt;" contenteditable="true" data-fm="author_dua">' + esc(fm.author_dua) + '</div>' +
            '<div class="title-plate-divider" contenteditable="true" data-fm="matn_credit">' + esc(fm.matn_credit) + '</div>' +
          '</div>' +
          '<div class="title-plate-bottom">' +
            '<span>كِتَابُ الطَّهَارَةِ وَكِتَابُ الصَّلاَةِ</span>' +
            '<span>' + esc(fm.p2_right) + '</span>' +
          '</div>' +
        '</div></div>';
    }}

    if (cfg.show_p3) {{
      const {{ bodyFrame }} = createPage({{ framed: true, skipHeader: true }});
      const isEd = data.mode === 'edited';
      const p3Sub = isEd
        ? '<span style="font-size: 11.5pt; font-weight: 400;">تَفْرِيغٌ مُحَرَّرٌ مُهَذَّبٌ لِمُحَاضَرَاتِ الشَّيْخِ فِي شَرْحِ مَتْنِ أَبِي شُجَاعٍ</span><br><span style="font-size: 11pt; font-weight: 400;">( الْمُحَاضَرَاتُ : ١ – ٢٥ )</span>'
        : '<span style="font-size: 11.5pt; font-weight: 400;">تَفْرِيغٌ حَرْفِيٌّ كَامِلٌ مُرَاجَعٌ لِدُرُوسِ السِّلْسِلَةِ الْفِقْهِيَّةِ الشَّافِعِيَّةِ</span><br><span style="font-size: 11pt; font-weight: 400;">( اللِّقَاءَاتُ : ١ – ٢٥ )</span>';
      const p3Syms = isEd
        ? '<div>﴿ ... ﴾ لِلآيَاتِ الْقُرْآنِيَّةِ &nbsp;•&nbsp; « ... » لِلأَحَادِيثِ &nbsp;•&nbsp; (١) لِغَرِيبِ الْمَتْنِ</div>'
        : '<div>﴿ ... ﴾ لِلآيَاتِ الْقُرْآنِيَّةِ &nbsp;•&nbsp; « ... » لِلأَحَادِيثِ &nbsp;•&nbsp; (١) لِغَرِيبِ الْمَتْنِ &nbsp;•&nbsp; (*) لِبَيَانِ اللِّقَاءِ الصَّوْتِيِّ</div>';
      bodyFrame.innerHTML =
        '<div class="frame-outer"><div class="frame-inner">' +
          '<div style="font-size: 15pt; font-weight: 700; line-height: 1.85; margin-top: 2mm;">' +
            '<span class="colophon-accent">' + esc(fm.title) + '</span><br>' + p3Sub +
          '</div>' +
          '<div class="disclaimer-box" contenteditable="true" data-fm="p3_disc">' + esc(fm.p3_disc) + '</div>' +
          '<div class="colophon-source-box">' +
            '<div class="colophon-accent">مَنْهَجُ الحَوَاشِي وَتَفْسِيرِ غَرِيبِ الْمَتْنِ :</div>' +
            '<div>أُلْحِقَتْ بِالحَوَاشِي أَسْفَلَ الصَّفَحَاتِ مَعَانِي الأَلْفَاظِ الْغَرِيبَةِ وَبَعْضِ الْمُصْطَلَحَاتِ الَّتِي لَمْ يَتَعَرَّضْ الشَّيْخُ الشَّارِحُ لِبَيَانِهَا فِي مَوْضِعِهَا، مُنْتَقَاةً مِنْ :</div>' +
            '<div class="colophon-source-title" contenteditable="true" data-fm="glossary_source">' + esc(fm.glossary_source) + '</div>' +
            '<div>بِتَرْقِيمٍ مُسْتَقِلٍّ لِكُلِّ صَفْحَةٍ يَبْدَأُ بِـ <span class="colophon-accent">(١)</span> دُونَ تَكْرَارٍ لِلْمَعْنَى فِي الصَّفْحَةِ الْوَاحِدَةِ.</div>' +
          '</div>' +
          '<div style="font-size: 10pt; line-height: 1.85; width: 92%;">' +
            '<div><span class="colophon-accent">رُمُوزُ الضَّبْطِ وَالتَّنْسِيقِ :</span></div>' +
            '<div><strong>الْخَطُّ الْعَرِيضُ دَاخِلَ الشَّرْحِ</strong> يُمَيِّزُ أَلْفَاظَ الْمَتْنِ الَّتِي يَسْتَشْهِدُ بِهَا الشَّارِحُ</div>' +
            p3Syms +
          '</div>' +
          '<div class="colophon-foot">' + esc(fm.title) + ' — لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ</div>' +
        '</div></div>';
    }}

    if (cfg.show_p4) {{
      const {{ bodyFrame }} = createPage({{ framed: true, skipHeader: true }});
      const basImgHtml = cfg.show_basmalah
        ? '<div class="img-editable-wrap">' +
            '<div class="hover-img-tools">' +
              '<button class="img-tool-btn" onclick="triggerGlobalImgUpload(\\'basmalah_data_url\\')">تغيير الصورة</button>' +
              '<button class="img-tool-btn rm" onclick="toggleGlobalAsset(\\'show_basmalah\\', false)">إزالة</button>' +
            '</div>' +
            '<img class="basmalah-plate-img" style="width:' + (cfg.basmalah_width_mm || 72) + 'mm;" src="' + basmalahUrl + '" alt="بسم الله الرحمن الرحيم">' +
          '</div>'
        : '<div style="font-family:AmiriQuranFont,serif; font-size:28pt; color:var(--accent);">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</div>';
      bodyFrame.innerHTML =
        '<div class="frame-outer"><div class="frame-inner" style="justify-content:center;">' +
          basImgHtml +
          '<div style="margin-top:16pt;">' + THREE_STARS_HTML + '</div>' +
        '</div></div>';
    }}

    // 2. BODY PAGES
    const tocEntries = [];
    const ayahIndexMap = new Map();
    const isEdited = data.mode === 'edited';
    let curPageObj = null;

    function setupPageFootnotesDom(p) {{
      p.footnoteArea = p.bodyFrame.querySelector('.footnote-area');
      p.footnoteText = p.bodyFrame.querySelector('.footnote-text');
      p.hasFootnote = false;
    }}

    function renderPageFootnotes(p) {{
      if (!p.lessonNoteText && p.glossaryNotes.length === 0) {{
        p.footnoteArea.style.display = 'none';
        p.footnoteText.innerHTML = '';
        p.hasFootnote = false;
        return;
      }}
      p.footnoteArea.style.display = 'block';
      let h = '';
      if (p.lessonNoteText) h += '<div class="fn-lesson-note">(*) ' + esc(p.lessonNoteText) + '</div>';
      for (const g of p.glossaryNotes) {{
        const colonIdx = g.text.indexOf(':');
        if (colonIdx > 0) {{
          h += '<div class="fn-gloss-row"><span class="fn-gloss-num">(' + toE(g.num) + ')</span> <span class="fn-gloss-term">' + esc(g.text.slice(0, colonIdx + 1)) + '</span>' + esc(g.text.slice(colonIdx + 1)) + '</div>';
        }} else {{
          h += '<div class="fn-gloss-row"><span class="fn-gloss-num">(' + toE(g.num) + ')</span> ' + esc(g.text) + '</div>';
        }}
      }}
      p.footnoteText.innerHTML = h;
      p.hasFootnote = true;
    }}

    function openPrefacePage() {{
      const p = createPage();
      p.bodyFrame.innerHTML = '<div class="sharh-zone"></div><div class="footnote-area" style="display:none;"><div class="footnote-rule"></div><div class="footnote-text"></div></div>';
      p.matnZone = null;
      p.sharhZone = p.bodyFrame.querySelector('.sharh-zone');
      setupPageFootnotesDom(p);
      p.unitCountOnPage = 0;
      p.isContPage = false;
      return p;
    }}

    function openBodyPage() {{
      const p = createPage();
      p.bodyFrame.innerHTML = '<div class="matn-zone"></div><hr class="split-rule"><div class="sharh-zone"></div><div class="footnote-area" style="display:none;"><div class="footnote-rule"></div><div class="footnote-text"></div></div>';
      p.matnZone = p.bodyFrame.querySelector('.matn-zone');
      p.sharhZone = p.bodyFrame.querySelector('.sharh-zone');
      setupPageFootnotesDom(p);
      p.unitCountOnPage = 0;
      p.isContPage = false;
      return p;
    }}

    function finalizeSplitPara(pEl, atoms, best, allowJustify) {{
      let splitIdx = best;
      if (atoms.length - splitIdx > 0 && atoms.length - splitIdx <= 5 && splitIdx >= 2) {{
        pEl.innerHTML = joinAtoms(atoms.slice(0, splitIdx));
        const hAt = pEl.getBoundingClientRect().height;
        let b2 = splitIdx - 1;
        while (b2 >= 1) {{
          pEl.innerHTML = joinAtoms(atoms.slice(0, b2));
          if (pEl.getBoundingClientRect().height < hAt - 2) {{
            splitIdx = b2;
            break;
          }}
          b2--;
        }}
      }}
      const headAtoms = atoms.slice(0, splitIdx);
      const tailAtoms = atoms.slice(splitIdx);
      pEl.innerHTML = joinAtoms(headAtoms);
      if (allowJustify && tailAtoms.length > 0) {{
        const range = document.createRange();
        range.selectNodeContents(pEl);
        const rects = range.getClientRects();
        const lr = rects.length ? rects[rects.length - 1] : null;
        if (lr && pEl.clientWidth > 0 && lr.width >= pEl.clientWidth * 0.62) {{
          pEl.classList.add('split-head');
        }}
      }}
      return {{ headAtoms, tailAtoms }};
    }}

    function fitsPage(p) {{
      if (p.sharhZone.clientHeight < 24) return false;
      if (p.sharhZone.scrollHeight > p.sharhZone.clientHeight + 1) return false;
      if (p.bodyFrame.scrollHeight > p.bodyFrame.clientHeight + 2) return false;
      const lastEl = p.sharhZone.lastElementChild;
      if (lastEl) {{
        const lastBottom = lastEl.getBoundingClientRect().bottom;
        const sBottom = p.sharhZone.getBoundingClientRect().bottom;
        if (lastBottom > sBottom - 2) return false;
        if (p.hasFootnote && p.footnoteArea && lastBottom > p.footnoteArea.getBoundingClientRect().top - 3) return false;
      }}
      return true;
    }}

    function makeFigureEl(ui, imgObj) {{
      const fig = document.createElement('figure');
      fig.className = 'unit-figure align-' + (imgObj.align || 'center');
      fig.dataset.uidx = ui;
      fig.dataset.imgid = imgObj.id;
      const capHtml = imgObj.caption ? '<figcaption>' + esc(imgObj.caption) + '</figcaption>' : '';
      fig.innerHTML =
        '<div class="hover-img-tools">' +
          '<button class="img-tool-btn" onclick="selectUnitAndFocus(' + ui + ')">تعديل الصورة</button>' +
          '<button class="img-tool-btn rm" onclick="removeUnitImage(' + ui + ', \\'' + esc(imgObj.id) + '\\')">حذف الصورة</button>' +
        '</div>' +
        '<img src="' + imgObj.data_url + '" style="width:' + (imgObj.width_mm || 85) + 'mm;" alt="">' +
        capHtml;
      return fig;
    }}

    function buildMatnHtmlForUnit(u, ui, pageObj, isContinuationPage = false) {{
      if (isContinuationPage) {{
        return '<div class="matn-cont-dots">............................................</div>';
      }}
      const matnLines = u.matn_lines || [];
      if (matnLines.length === 1 && matnLines[0].trim() === '............................................') {{
        let hc = '';
        let ancP = false;
        if (u.toc_fasl) {{
          hc += '<div class="matn-bracket-title" id="unit-' + esc(u.id) + '" contenteditable="true" data-uidx="' + ui + '" data-field="toc_fasl">' + esc(u.toc_fasl) + '</div>';
          ancP = true;
        }}
        hc += '<div class="matn-cont-dots"' + (ancP ? '' : ' id="unit-' + esc(u.id) + '"') + '>............................................</div>';
        return hc;
      }}
      const glosses = Array.isArray(u.glosses) ? u.glosses : [];
      const lines = matnLines.map(l => String(l));
      let hasLeadingDots = false;
      let hasTrailingDots = false;
      if (lines.length > 0 && /^\.{5,}\s*/.test(lines[0])) {{
        hasLeadingDots = true;
        lines[0] = lines[0].replace(/^\.{5,}\s*/, '').trim();
      }}
      if (lines.length > 0 && /\s*\.{5,}$/.test(lines[lines.length - 1])) {{
        hasTrailingDots = true;
        lines[lines.length - 1] = lines[lines.length - 1].replace(/\s*\.{5,}$/, '').trim();
      }}
      const placements = [];
      for (const g of glosses) {{
        if (pageObj.pageGlossaryIds.has(g.id)) continue;
        const normKey = g.term.replace(/[\\u064b-\\u065f\\u0670\\u0640\\s]/g, '');
        if (pageObj.pageGlossaryTerms.has(normKey)) continue;
        try {{
          const rx = new RegExp(g.pattern || g.term);
          for (let li = 0; li < lines.length; li++) {{
            const m = rx.exec(lines[li]);
            if (m) {{
              placements.push({{ g, normKey, li, start: m.index, end: m.index + m[0].length }});
              break;
            }}
          }}
        }} catch (e) {{}}
      }}
      placements.sort((a, b) => (a.li - b.li) || (a.start - b.start));
      const byLine = new Map();
      for (const pl of placements) {{
        if (pageObj.pageGlossaryIds.has(pl.g.id) || pageObj.pageGlossaryTerms.has(pl.normKey)) continue;
        pageObj.pageGlossaryIds.add(pl.g.id);
        pageObj.pageGlossaryTerms.add(pl.normKey);
        pageObj.pageFnNum++;
        pl.fnNum = pageObj.pageFnNum;
        pageObj.glossaryNotes.push({{ num: pl.fnNum, text: pl.g.gloss }});
        if (!byLine.has(pl.li)) byLine.set(pl.li, []);
        byLine.get(pl.li).push(pl);
      }}
      for (const [li, pls] of byLine.entries()) {{
        pls.sort((a, b) => b.end - a.end);
        let s = lines[li];
        for (const pl of pls) {{
          s = s.slice(0, pl.end) + '<sup class="fn-ref">(' + toE(pl.fnNum) + ')</sup>' + s.slice(pl.end);
        }}
        lines[li] = s;
      }}
      const wrapMatnAyahs = (s) => s
        .replace(/(﴿[^﴾]+﴾)/g, '<span class="ayah">$1</span>')
        .replace(/(\\[[^\\]:]+:\\s*[٠-٩\\-]+\\])/g, '<span class="ayah-ref">$1</span>');

      let h = '';
      let anchorPlaced = false;
      if (u.toc_book) {{
        h += CHAPTER_BANNER_HTML;
        h += '<div class="matn-book-title" id="unit-' + esc(u.id) + '" contenteditable="true" data-uidx="' + ui + '" data-field="toc_book">' + esc(u.toc_book) + '</div>';
        anchorPlaced = true;
      }}
      if (u.toc_fasl) {{
        const anchorAttr = !anchorPlaced ? ' id="unit-' + esc(u.id) + '"' : '';
        h += '<div class="matn-bracket-title"' + anchorAttr + ' contenteditable="true" data-uidx="' + ui + '" data-field="toc_fasl">' + esc(u.toc_fasl) + '</div>';
        anchorPlaced = true;
      }}
      for (const im of (u.images || [])) {{
        if (im.placement === 'before_matn') {{
          h += makeFigureEl(ui, im).outerHTML;
        }}
      }}
      if (hasLeadingDots) h += '<div class="matn-cont-dots">............................................</div>';
      for (let i = 0; i < lines.length; i++) {{
        const line = lines[i];
        if (!line.trim()) continue;
        const anchorAttr = (!anchorPlaced && i === 0) ? ' id="unit-' + esc(u.id) + '"' : '';
        const isBasmalah = /^بِسْمِ\\s+اللَّ?هِ\\s+الرَّحْم[َٰـ]*نِ\\s+الرَّحِيمِ$/.test(line.trim());
        h += '<p class="' + (isBasmalah ? 'matn-basmalah' : 'matn-p') + '"' + anchorAttr + ' contenteditable="true" data-uidx="' + ui + '" data-matn-li="' + i + '">' + wrapMatnAyahs(line) + '</p>';
        anchorPlaced = true;
      }}
      if (hasTrailingDots) h += '<div class="matn-cont-dots">............................................</div>';
      if (u.fasl_end) h += THREE_STARS_HTML;
      return h;
    }}

    const ayahRefLookup = new Map();
    if (data.ayah_refs && typeof data.ayah_refs === 'object') {{
      for (const [k, v] of Object.entries(data.ayah_refs)) {{
        const cleanK = k.replace(/\\s+/g, ' ').trim();
        if (cleanK && v) ayahRefLookup.set(cleanK, String(v).trim());
      }}
    }}
    for (const u of data.units) {{
      for (const pHtml of (u.sharh_paras_html || [])) {{
        const tmpA = document.createElement('div');
        tmpA.innerHTML = pHtml;
        for (const sp of tmpA.querySelectorAll('.ayah')) {{
          const cleanA = sp.textContent.replace(/[﴿﴾]/g, '').replace(/\\s+/g, ' ').trim();
          const nxt = sp.nextElementSibling;
          if (cleanA && nxt && nxt.classList.contains('ayah-ref') && !ayahRefLookup.has(cleanA)) {{
            ayahRefLookup.set(cleanA, nxt.textContent.trim());
          }}
        }}
      }}
    }}

    function recordAyahsOnPage(htmlChunk, pNum) {{
      const tmp = document.createElement('div');
      tmp.innerHTML = htmlChunk;
      tmp.querySelectorAll('.fn-ref').forEach(el => el.remove());
      for (const sp of tmp.querySelectorAll('.ayah')) {{
        const cleanAyah = sp.textContent.replace(/[﴿﴾]/g, '').replace(/\\s+/g, ' ').trim();
        const wordCount = cleanAyah ? cleanAyah.split(' ').length : 0;
        if (wordCount >= 2 && cleanAyah.length >= 8) {{
          if (!ayahIndexMap.has(cleanAyah)) ayahIndexMap.set(cleanAyah, new Set());
          ayahIndexMap.get(cleanAyah).add(pNum);
        }}
      }}
    }}

    function openOverflowPage(u) {{
      const np = u.is_preface ? openPrefacePage() : openBodyPage();
      np.isContPage = true;
      if (!u.is_preface) np.matnZone.innerHTML = buildMatnHtmlForUnit(u, -1, np, true);
      np.unitCountOnPage++;
      return np;
    }}

    function appendFigureSafely(figEl, u) {{
      curPageObj.sharhZone.appendChild(figEl);
      if (!fitsPage(curPageObj)) {{
        const hasOther = curPageObj.sharhZone.children.length > 1;
        if (hasOther || !curPageObj.isContPage) {{
          curPageObj.sharhZone.removeChild(figEl);
          curPageObj = openOverflowPage(u);
          curPageObj.sharhZone.appendChild(figEl);
        }}
      }}
    }}

    if (data.units.length > 0) {{
      curPageObj = data.units[0].is_preface ? openPrefacePage() : openBodyPage();
    }}

    for (let ui = 0; ui < data.units.length; ui++) {{
      if (ui % 10 === 0) await new Promise(r => setTimeout(r, 0));
      const u = data.units[ui];
      const secLabel = u.toc_fasl || u.toc_book || '';
      if (secLabel) activeSectionTitle = secLabel.replace(/^\\[\\s*|\\s*\\]$/g, '').trim();

      if (curPageObj.unitCountOnPage > 0) {{
        curPageObj = u.is_preface ? openPrefacePage() : openBodyPage();
      }} else if (secLabel) {{
        setPageOddHeaderTitle(curPageObj, secLabel);
      }}

      unitPageMap.set(ui, curPageObj.pNum);
      if (u.toc_book) tocEntries.push({{ kind: 'book', title: u.toc_book, page: curPageObj.pNum, anchor: 'unit-' + u.id }});
      if (u.toc_fasl) tocEntries.push({{ kind: 'fasl', title: u.toc_fasl, page: curPageObj.pNum, anchor: 'unit-' + u.id }});

      if (u.is_preface) {{
        curPageObj.sharhZone.insertAdjacentHTML('beforeend',
          (u.id === 'L01_U01' ? CHAPTER_BANNER_HTML : '') +
          '<div class="preface-h" id="unit-' + esc(u.id) + '" contenteditable="true" data-uidx="' + ui + '" data-field="toc_fasl">' + esc(u.toc_fasl || 'مُقَدِّمَةُ الْكِتَابِ') + '</div>'
        );
      }} else {{
        const matnHtml = buildMatnHtmlForUnit(u, ui, curPageObj, false);
        curPageObj.matnZone.insertAdjacentHTML('beforeend', matnHtml);
        recordAyahsOnPage(matnHtml, curPageObj.pNum);
      }}

      if (!isEdited && u.lesson_note) curPageObj.lessonNoteText = u.lesson_note;
      renderPageFootnotes(curPageObj);
      curPageObj.unitCountOnPage++;

      // Prevent tall Matn-only units from clipping off footnotes or bottom edge
      if (!u.is_preface && curPageObj.bodyFrame.scrollHeight > curPageObj.bodyFrame.clientHeight - 4) {{
        curPageObj.matnZone.style.fontSize = '11.4pt';
        curPageObj.matnZone.style.lineHeight = '1.64';
      }}

      // Images placed right before Sharh (or top of Preface Sharh)
      for (const im of (u.images || [])) {{
        if (im.placement === 'before_sharh' || (u.is_preface && im.placement === 'before_matn')) {{
          appendFigureSafely(makeFigureEl(ui, im), u);
        }}
      }}

      const paras = u.sharh_paras_html || [];
      for (let pi = 0; pi < paras.length; pi++) {{
        let atoms = tokenizeHtml(paras[pi]);
        const plainP = paras[pi].replace(/<[^>]+>/g, '').trim();
        const isPoemBayt = /^[^<>\\n]{8,65}\\s+\\.\\.\\.\\s+[^<>\\n]{8,65}$/.test(plainP);
        let isCont = false;
        let firstPartOnPage = true;
        const placedElsForPara = [];
        const isLastPara = (pi === paras.length - 1);

        while (atoms.length > 0) {{
          const pEl = document.createElement('p');
          pEl.className = 'sharh-p' + (isPoemBayt ? ' poem-bayt' : '') + (isCont ? ' cont' : '');
          pEl.dataset.uidx = ui;
          pEl.dataset.pi = pi;
          pEl.innerHTML = joinAtoms(atoms);
          curPageObj.sharhZone.appendChild(pEl);

          if (fitsPage(curPageObj)) {{
            recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
            placedElsForPara.push(pEl);
            atoms = [];
          }} else {{
            if (isLastPara && atoms.length <= 34 && !curPageObj.sharhZone.classList.contains('tight-fit')) {{
              curPageObj.sharhZone.classList.add('tight-fit');
              if (fitsPage(curPageObj)) {{
                recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
                placedElsForPara.push(pEl);
                atoms = [];
                continue;
              }}
              curPageObj.sharhZone.classList.remove('tight-fit');
            }}
            let lo = 1, hi = atoms.length - 1, best = 0;
            while (lo <= hi) {{
              const mid = (lo + hi) >> 1;
              pEl.innerHTML = joinAtoms(atoms.slice(0, mid));
              if (fitsPage(curPageObj)) {{ best = mid; lo = mid + 1; }}
              else hi = mid - 1;
            }}
            const priorParaCount = curPageObj.sharhZone.querySelectorAll('p.sharh-p').length - 1;
            if (best <= 0 || (priorParaCount > 0 && best < 3) || (isPoemBayt && best < atoms.length)) {{
              if (!curPageObj.isContPage || priorParaCount > 0) {{
                curPageObj.sharhZone.removeChild(pEl);
                curPageObj = openOverflowPage(u);
                continue;
              }} else {{
                best = Math.min(12, atoms.length);
              }}
            }}
            const prelimTailLen = atoms.length - best;
            if (isLastPara && prelimTailLen <= 34 && !curPageObj.sharhZone.classList.contains('tight-fit')) {{
              pEl.innerHTML = joinAtoms(atoms);
              curPageObj.sharhZone.classList.add('tight-fit');
              if (fitsPage(curPageObj)) {{
                recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
                placedElsForPara.push(pEl);
                atoms = [];
                continue;
              }}
              curPageObj.sharhZone.classList.remove('tight-fit');
            }}
            const splitRes = finalizeSplitPara(pEl, atoms, best, !isPoemBayt);
            recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
            placedElsForPara.push(pEl);
            atoms = splitRes.tailAtoms;
            isCont = true;
            firstPartOnPage = false;
            if (atoms.length > 0) curPageObj = openOverflowPage(u);
          }}
        }}

        // If paragraph sits completely unsplit on a single page, enable direct inline contenteditable!
        if (placedElsForPara.length === 1) {{
          placedElsForPara[0].setAttribute('contenteditable', 'true');
          placedElsForPara[0].dataset.part = 'full';
        }} else {{
          placedElsForPara.forEach(el => {{ el.dataset.part = 'split'; el.style.cursor = 'pointer'; }});
        }}

        // Images placed right after this Sharh paragraph
        for (const im of (u.images || [])) {{
          if (im.placement === 'after_para' && Number(im.after_para_idx) === pi) {{
            appendFigureSafely(makeFigureEl(ui, im), u);
          }}
        }}
      }}

      // Images placed at end of Sharh
      for (const im of (u.images || [])) {{
        if (im.placement === 'end_sharh') {{
          appendFigureSafely(makeFigureEl(ui, im), u);
        }}
      }}

      if (u.fasl_end && THREE_STARS_HTML) {{
        curPageObj.sharhZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
        if (!fitsPage(curPageObj)) {{
          const tailEl = curPageObj.sharhZone.lastElementChild;
          if (tailEl) tailEl.style.margin = '1pt 0';
          if (!fitsPage(curPageObj) && tailEl) curPageObj.sharhZone.removeChild(tailEl);
        }}
      }}
    }}

    // 3. BACK MATTER INDEXES
    let ayahStartPage = null;
    if (ayahIndexMap.size > 0) {{
      const ayahList = Array.from(ayahIndexMap.entries());
      let ayPage = createPage({{ centerTitle: 'فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ' }});
      ayahStartPage = ayPage.pNum;
      ayPage.bodyFrame.innerHTML =
        CHAPTER_BANNER_HTML +
        '<div class="toc-page-title">فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ</div>' +
        '<div class="index-col-head"><span>الآيَةُ الْكَرِيمَةُ</span><span>الصَّفْحَةُ</span></div>' +
        '<div id="ayah-list-box"></div>';
      let ayBox = ayPage.bodyFrame.querySelector('#ayah-list-box');

      for (const [ayahTxt, pgSet] of ayahList) {{
        const pgs = Array.from(pgSet).sort((a,b) => a-b);
        const pgLinks = pgs.map(p => '<a href="#pg-' + p + '">' + toE(p) + '</a>').join(' ، ');
        const refStr = ayahRefLookup.get(ayahTxt);
        const refHtml = refStr ? '\\u00A0<span class="ayah-ref">' + esc(refStr.replace(/\\s+/g, '\\u00A0')) + '</span>' : '';
        const row = document.createElement('div');
        row.className = 'ayah-idx-row';
        row.innerHTML = '<span class="ayah-idx-text">﴿' + esc(ayahTxt) + '﴾' + refHtml + '</span>' +
                        '<span class="ayah-idx-pages">' + pgLinks + '</span>';
        ayBox.appendChild(row);
        const lastAy = ayBox.lastElementChild;
        const ayOverflow = ayPage.bodyFrame.scrollHeight > ayPage.bodyFrame.clientHeight + 2 ||
          (lastAy && lastAy.getBoundingClientRect().bottom > ayPage.bodyFrame.getBoundingClientRect().bottom - 2);
        if (ayOverflow && ayBox.children.length > 1) {{
          ayBox.removeChild(row);
          ayPage = createPage({{ centerTitle: 'فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ' }});
          ayPage.bodyFrame.innerHTML =
            '<div class="toc-page-title" style="font-size:13pt;">تَابِعُ فَهْرَسِ الآيَاتِ الْقُرْآنِيَّةِ</div>' +
            '<div class="index-col-head"><span>الآيَةُ الْكَرِيمَةُ</span><span>الصَّفْحَةُ</span></div>' +
            '<div id="ayah-list-box"></div>';
          ayBox = ayPage.bodyFrame.querySelector('#ayah-list-box');
          ayBox.appendChild(row);
        }}
      }}
    }}

    const firstTocPg = pageCounter + 1;
    const allTocEntries = [...tocEntries, {{ kind: 'center', title: 'اَلْفَهَارِسُ', page: null, anchor: '' }}];
    if (ayahStartPage) allTocEntries.push({{ kind: 'fasl', title: 'فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ', page: ayahStartPage, anchor: 'pg-' + ayahStartPage }});
    allTocEntries.push({{ kind: 'fasl', title: 'اَلْفَهْرَسُ الْعَامُّ', page: firstTocPg, anchor: 'pg-' + firstTocPg }});

    let fIdx = 0;
    let tocPgCount = 0;
    while (fIdx < allTocEntries.length) {{
      tocPgCount++;
      const pObj = createPage({{ centerTitle: 'اَلْفَهْرَسُ الْعَامُّ' }});
      const titleStr = tocPgCount === 1 ? 'اَلْفَهْرَسُ الْعَامُّ' : 'تَابِعُ الْفَهْرَسِ الْعَامِّ';
      pObj.bodyFrame.innerHTML =
        (tocPgCount === 1 ? CHAPTER_BANNER_HTML : '') +
        '<div class="toc-page-title">' + titleStr + '</div>' +
        '<div class="toc-two-col"><div class="toc-col toc-col-right"></div><div class="toc-col toc-col-left"></div></div>';
      const colRight = pObj.bodyFrame.querySelector('.toc-col-right');
      const colLeft = pObj.bodyFrame.querySelector('.toc-col-left');
      const colOverflows = (col) => {{
        if (pObj.bodyFrame.scrollHeight > pObj.bodyFrame.clientHeight + 2) return true;
        const bfBottom = pObj.bodyFrame.getBoundingClientRect().bottom - 2;
        const last = col.lastElementChild;
        return Boolean(last && last.getBoundingClientRect().bottom > bfBottom);
      }};
      const makeTocEl = (e) => {{
        const div = document.createElement('div');
        if (e.kind === 'center') {{ div.className = 'toc-section-center'; div.textContent = e.title; }}
        else if (e.kind === 'book') {{
          div.className = 'toc-book-row';
          div.innerHTML = '<span class="toc-book-label"><a href="#' + esc(e.anchor) + '">' + esc(e.title) + '</a></span><span class="toc-dots"></span><span class="toc-pg"><a href="#' + esc(e.anchor) + '">' + toE(e.page) + '</a></span>';
        }} else {{
          const nbTitle = esc(e.title).replace(/^\\[\\s+/, '[\\u00A0').replace(/\\s+\\]$/, '\\u00A0]');
          div.className = 'toc-row';
          div.innerHTML = '<span class="toc-row-title"><a href="#' + esc(e.anchor) + '">' + nbTitle + '</a></span><span class="toc-dots"></span><span class="toc-pg"><a href="#' + esc(e.anchor) + '">' + toE(e.page) + '</a></span>';
        }}
        return div;
      }};
      const startFIdx = fIdx;
      while (fIdx < allTocEntries.length) {{
        const el = makeTocEl(allTocEntries[fIdx]);
        colRight.appendChild(el);
        if (colOverflows(colRight) && colRight.children.length > 1) {{ colRight.removeChild(el); break; }}
        fIdx++;
      }}
      if (fIdx >= allTocEntries.length && (fIdx - startFIdx) >= 4) {{
        const rem = allTocEntries.slice(startFIdx);
        const half = Math.ceil(rem.length / 2);
        colRight.innerHTML = '';
        colLeft.innerHTML = '';
        for (let i = 0; i < rem.length; i++) {{
          (i < half ? colRight : colLeft).appendChild(makeTocEl(rem[i]));
        }}
      }} else {{
        while (fIdx < allTocEntries.length) {{
          const el = makeTocEl(allTocEntries[fIdx]);
          colLeft.appendChild(el);
          if (colOverflows(colLeft) && colLeft.children.length > 1) {{ colLeft.removeChild(el); break; }}
          fIdx++;
        }}
      }}
      if (fIdx === startFIdx) break;
    }}

    stage.style.transform = prevTransform;
    return {{ totalPages: pageCounter, ayahCount: ayahIndexMap.size, tocCount: tocEntries.length }};
  }}

  // ==================== UI SYNCHRONIZATION & DIRECT EDITING ====================
  async function paginateAndRender(scrollToUnitIdx = null) {{
    if (isPaginating) return;
    isPaginating = true;
    try {{
      const res = await renderFullBook(bookData, currentTheme);
      clearDirty();
      document.getElementById('preview-stats').textContent =
        toE(res.totalPages) + ' صفحة • ' + toE(res.ayahCount) + ' آية مفهرسة • ١٦٢×٢٣٤ ملم';
      document.getElementById('jump-pg-in').max = res.totalPages;
      renderUnitNavList();
      refreshGlobalAssetThumbs();
      applyZoom();
      if (scrollToUnitIdx !== null) scrollPreviewToUnit(scrollToUnitIdx);
    }} finally {{
      isPaginating = false;
    }}
  }}

  function applyZoom() {{
    const st = document.getElementById('book-stage');
    st.style.transform = currentZoom === 1 ? 'none' : 'scale(' + currentZoom + ')';
  }}

  function scrollPreviewToUnit(ui) {{
    const pNum = unitPageMap.get(ui);
    if (!pNum) return;
    const el = document.getElementById('pg-' + pNum);
    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}

  function renderUnitNavList() {{
    const q = document.getElementById('unit-search').value.trim();
    const listEl = document.getElementById('unit-list');
    document.getElementById('unit-count-lbl').textContent = toE(bookData.units.length);
    listEl.innerHTML = '';
    bookData.units.forEach((u, idx) => {{
      const label = (u.toc_fasl || u.toc_book || u.heading || ('وحدة ' + (idx + 1))).replace(/^\\[\\s*|\\s*\\]$/g, '');
      if (q && !label.includes(q) && !(u.matn_raw || '').includes(q)) return;
      const li = document.createElement('li');
      li.className = 'unit-item' + (idx === activeUnitIdx ? ' active' : '');
      const pg = unitPageMap.get(idx) || '—';
      li.innerHTML = '<span style="flex:1; line-height:1.45;">' + esc(label) + '</span>' +
                     '<span class="unit-item-pg">' + (pg === '—' ? '—' : 'ص ' + toE(pg)) + '</span>';
      li.onclick = () => {{
        selectUnitAndFocus(idx, true);
      }};
      listEl.appendChild(li);
    }});
  }}

  window.selectUnitAndFocus = function(idx, alsoScroll = false) {{
    if (idx < 0 || idx >= bookData.units.length) return;
    activeUnitIdx = idx;
    renderUnitNavList();
    renderUnitEditor();
    if (alsoScroll) scrollPreviewToUnit(idx);
  }};

  function renderUnitEditor() {{
    const u = bookData.units[activeUnitIdx];
    if (!u) return;
    document.getElementById('ed-unit-label').textContent = 'تحرير الوحدة (' + toE(activeUnitIdx + 1) + ' / ' + toE(bookData.units.length) + ')';
    document.getElementById('ed-toc-book').value = u.toc_book || '';
    document.getElementById('ed-toc-fasl').value = u.toc_fasl || '';
    document.getElementById('ed-lesson-note').value = u.lesson_note || '';
    document.getElementById('ed-fasl-end').checked = Boolean(u.fasl_end);

    const matnSec = document.getElementById('ed-matn-section');
    matnSec.style.display = u.is_preface ? 'none' : 'block';
    document.getElementById('ed-matn-text').value = (u.matn_lines || []).join('\\n');

    renderUnitImagesEditor(u);
    renderSharhParasEditor(u);
    renderGlossEditor(u);
  }}

  function renderUnitImagesEditor(u) {{
    const box = document.getElementById('ed-unit-images-list');
    const imgs = u.images || [];
    document.getElementById('ed-img-count').textContent = toE(imgs.length);
    box.innerHTML = '';
    if (!imgs.length) {{
      box.innerHTML = '<div style="font-size:0.75rem; color:#888; text-align:center; padding:6px;">لا توجد صور مضافة داخل هذه الوحدة.</div>';
      return;
    }}
    const paraOpts = (u.sharh_paras_html || []).map((_, pi) => '<option value="' + pi + '">بعد الفقرة ' + toE(pi + 1) + '</option>').join('');
    imgs.forEach((im, idx) => {{
      const card = document.createElement('div');
      card.className = 'uimg-card';
      card.innerHTML =
        '<img class="uimg-thumb" src="' + im.data_url + '" alt="">' +
        '<div class="uimg-fields">' +
          '<div class="uimg-row">' +
            '<label>الموضع:</label>' +
            '<select data-k="placement">' +
              '<option value="before_matn"' + (im.placement==='before_matn'?' selected':'') + '>أعلى الوحدة</option>' +
              '<option value="before_sharh"' + (im.placement==='before_sharh'?' selected':'') + '>قبل الشرح</option>' +
              '<option value="after_para"' + (im.placement==='after_para'?' selected':'') + '>بعد فقرة محددة</option>' +
              '<option value="end_sharh"' + (im.placement==='end_sharh'?' selected':'') + '>ختام الوحدة</option>' +
            '</select>' +
            (im.placement === 'after_para' ? '<select data-k="after_para_idx">' + paraOpts + '</select>' : '') +
            '<select data-k="align">' +
              '<option value="center"' + (im.align==='center'?' selected':'') + '>توسيط</option>' +
              '<option value="right"' + (im.align==='right'?' selected':'') + '>يمين</option>' +
              '<option value="left"' + (im.align==='left'?' selected':'') + '>يسار</option>' +
            '</select>' +
          '</div>' +
          '<div class="uimg-row">' +
            '<span>العرض: <strong class="w-lbl">' + (im.width_mm || 85) + '</strong> ملم</span>' +
            '<input type="range" data-k="width_mm" min="20" max="124" value="' + (im.width_mm || 85) + '" style="flex:1;">' +
          '</div>' +
          '<div class="uimg-row">' +
            '<input type="text" data-k="caption" value="' + esc(im.caption || '') + '" placeholder="تعليق أسفل الصورة (اختياري)" style="flex:1;">' +
            '<button class="ed-btn-light del" data-act="rm">حذف</button>' +
          '</div>' +
        '</div>';
      if (im.placement === 'after_para') {{
        const ap = card.querySelector('[data-k="after_para_idx"]');
        if (ap) ap.value = String(im.after_para_idx || 0);
      }}
      card.querySelectorAll('select, input').forEach(inp => {{
        inp.addEventListener('input', () => {{
          const k = inp.dataset.k;
          im[k] = (k === 'width_mm' || k === 'after_para_idx') ? Number(inp.value) : inp.value;
          if (k === 'width_mm') card.querySelector('.w-lbl').textContent = im[k];
          if (k === 'placement') renderUnitImagesEditor(u);
          markDirty(true);
        }});
      }});
      card.querySelector('[data-act="rm"]').onclick = () => {{
        u.images.splice(idx, 1);
        renderUnitImagesEditor(u);
        markDirty();
        paginateAndRender(activeUnitIdx);
      }};
      box.appendChild(card);
    }});
  }}

  window.removeUnitImage = function(ui, imgId) {{
    const u = bookData.units[ui];
    if (!u || !u.images) return;
    u.images = u.images.filter(im => im.id !== imgId);
    if (ui === activeUnitIdx) renderUnitImagesEditor(u);
    markDirty();
    paginateAndRender(ui);
    showToast('تمت إزالة الصورة وتحديث الصفحات');
  }};

  function wrapSelectionInRich(richEl, fn) {{
    richEl.focus();
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    if (!richEl.contains(range.commonAncestorContainer)) return;
    const txt = range.toString();
    fn(range, txt);
    sel.collapseToEnd();
    richEl.dispatchEvent(new Event('input'));
  }}

  function renderSharhParasEditor(u, focusParaIdx = null) {{
    const box = document.getElementById('ed-sharh-paras-list');
    box.innerHTML = '';
    const paras = u.sharh_paras_html || [];
    paras.forEach((pHtml, pi) => {{
      const card = document.createElement('div');
      card.className = 'para-card';
      card.innerHTML =
        '<div class="para-bar">' +
          '<span style="font-size:0.72rem; font-weight:700; color:#78716c;">فقرة ' + toE(pi + 1) + '</span>' +
          '<div class="para-tools">' +
            '<button class="fmt-btn" data-fmt="bold" title="تغليظ نص المتن داخل الشرح"><b>عريض</b></button>' +
            '<button class="fmt-btn" data-fmt="ayah" title="تمييز آية بالرسم العثماني">﴿آية﴾</button>' +
            '<button class="fmt-btn" data-fmt="ref" title="عزو السورة والآية">[السورة: الآية]</button>' +
            '<button class="fmt-btn" data-fmt="hadith" title="قوسا حديث">«حديث»</button>' +
            '<button class="fmt-btn" data-act="up" title="لأعلى">↑</button>' +
            '<button class="fmt-btn" data-act="dn" title="لأسفل">↓</button>' +
            '<button class="fmt-btn" data-act="del" style="color:#b91c1c;" title="حذف الفقرة">×</button>' +
          '</div>' +
        '</div>' +
        '<div class="para-rich" contenteditable="true" dir="rtl">' + pHtml + '</div>';

      const rich = card.querySelector('.para-rich');
      rich.addEventListener('input', () => {{
        u.sharh_paras_html[pi] = sanitizeParaHtml(rich.innerHTML);
        markDirty();
      }});

      card.querySelectorAll('.fmt-btn[data-fmt]').forEach(btn => {{
        btn.onmousedown = (e) => e.preventDefault();
        btn.onclick = () => {{
          const fmt = btn.dataset.fmt;
          wrapSelectionInRich(rich, (range, txt) => {{
            if (fmt === 'bold') {{
              const st = document.createElement('strong');
              st.textContent = txt || 'نص متني';
              range.deleteContents();
              range.insertNode(st);
            }} else if (fmt === 'ayah') {{
              const sp = document.createElement('span');
              sp.className = 'ayah';
              const clean = txt.replace(/^[﴿\\s]+|[﴾\\s]+$/g, '') || 'آيَةٌ كَرِيمَةٌ';
              sp.textContent = '﴿' + clean + '﴾';
              range.deleteContents();
              range.insertNode(sp);
            }} else if (fmt === 'ref') {{
              const sp = document.createElement('span');
              sp.className = 'ayah-ref';
              const clean = txt.replace(/^[\\[\\s]+|[\\]\\s]+$/g, '') || 'البقرة: ٢٥٥';
              sp.textContent = '[' + clean + ']';
              range.deleteContents();
              range.insertNode(sp);
            }} else if (fmt === 'hadith') {{
              const clean = txt.replace(/^[«\\s]+|[»\\s]+$/g, '') || 'الحديث';
              const nd = document.createTextNode('«' + clean + '»');
              range.deleteContents();
              range.insertNode(nd);
            }}
          }});
        }};
      }});

      card.querySelector('[data-act="up"]').onclick = () => {{
        if (pi === 0) return;
        [u.sharh_paras_html[pi - 1], u.sharh_paras_html[pi]] = [u.sharh_paras_html[pi], u.sharh_paras_html[pi - 1]];
        renderSharhParasEditor(u);
        markDirty(true);
      }};
      card.querySelector('[data-act="dn"]').onclick = () => {{
        if (pi >= u.sharh_paras_html.length - 1) return;
        [u.sharh_paras_html[pi + 1], u.sharh_paras_html[pi]] = [u.sharh_paras_html[pi], u.sharh_paras_html[pi + 1]];
        renderSharhParasEditor(u);
        markDirty(true);
      }};
      card.querySelector('[data-act="del"]').onclick = () => {{
        u.sharh_paras_html.splice(pi, 1);
        renderSharhParasEditor(u);
        markDirty(true);
      }};

      box.appendChild(card);
      if (focusParaIdx === pi) {{
        setTimeout(() => {{ card.scrollIntoView({{ block: 'center', behavior: 'smooth' }}); rich.focus(); }}, 30);
      }}
    }});
  }}

  function renderGlossEditor(u) {{
    const box = document.getElementById('ed-gloss-list');
    const gl = u.glosses || [];
    document.getElementById('ed-gloss-count').textContent = toE(gl.length);
    box.innerHTML = '';
    if (!gl.length) {{
      box.innerHTML = '<div style="font-size:0.75rem; color:#888; text-align:center; padding:4px;">لا توجد حواشي غريب لهذه الوحدة.</div>';
      return;
    }}
    gl.forEach((g, gi) => {{
      const row = document.createElement('div');
      row.style.cssText = 'border:1px solid #e5dfd3; border-radius:6px; padding:7px; margin-bottom:6px; background:#faf8f4;';
      row.innerHTML =
        '<div style="display:flex; gap:6px; margin-bottom:5px;">' +
          '<input class="ed-input" data-gk="term" value="' + esc(g.term) + '" placeholder="اللفظة في المتن" style="font-size:0.88rem;">' +
          '<button class="ed-btn-light del" data-gdel="1">×</button>' +
        '</div>' +
        '<input class="ed-input" data-gk="gloss" value="' + esc(g.gloss) + '" placeholder="اللفظة: شرحها..." style="width:100%; font-size:0.88rem;">';
      row.querySelector('[data-gk="term"]').addEventListener('input', (e) => {{
        g.term = e.target.value;
        g.pattern = e.target.value.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
        markDirty();
      }});
      row.querySelector('[data-gk="gloss"]').addEventListener('input', (e) => {{
        g.gloss = e.target.value;
        markDirty();
      }});
      row.querySelector('[data-gdel]').onclick = () => {{
        gl.splice(gi, 1);
        renderGlossEditor(u);
        markDirty(true);
      }};
      box.appendChild(row);
    }});
  }}

  // Direct on-page inline editing listeners via delegation
  const bookRootEl = document.getElementById('book-root');
  bookRootEl.addEventListener('input', (ev) => {{
    const target = ev.target.closest('[contenteditable="true"]');
    if (!target) return;
    if (target.dataset.fm) {{
      const k = target.dataset.fm;
      bookData.front_matter[k] = target.textContent.trim();
      syncFrontMatterInputs();
      markDirty();
      return;
    }}
    const ui = Number(target.dataset.uidx);
    const u = bookData.units[ui];
    if (!u) return;
    if (ui !== activeUnitIdx) {{
      activeUnitIdx = ui;
      renderUnitNavList();
      renderUnitEditor();
    }}
    if (target.dataset.field) {{
      u[target.dataset.field] = target.textContent.trim();
      if (target.dataset.field === 'toc_fasl') u.heading = u.toc_fasl;
      renderUnitEditor();
      markDirty();
    }} else if (target.dataset.matnLi !== undefined) {{
      const li = Number(target.dataset.matnLi);
      const clone = target.cloneNode(true);
      clone.querySelectorAll('.fn-ref').forEach(x => x.remove());
      u.matn_lines[li] = clone.textContent.replace(/\\s+/g, ' ').trim();
      document.getElementById('ed-matn-text').value = u.matn_lines.join('\\n');
      markDirty();
    }} else if (target.dataset.pi !== undefined) {{
      const pi = Number(target.dataset.pi);
      u.sharh_paras_html[pi] = sanitizeParaHtml(target.innerHTML);
      const cards = document.querySelectorAll('#ed-sharh-paras-list .para-rich');
      if (cards[pi]) cards[pi].innerHTML = u.sharh_paras_html[pi];
      markDirty();
    }}
  }});

  bookRootEl.addEventListener('click', (ev) => {{
    const el = ev.target.closest('[data-uidx]');
    if (!el) return;
    const ui = Number(el.dataset.uidx);
    if (Number.isNaN(ui) || ui < 0) return;
    if (ui !== activeUnitIdx) {{
      activeUnitIdx = ui;
      renderUnitNavList();
      renderUnitEditor();
    }}
    if (el.dataset.pi !== undefined && el.dataset.part === 'split') {{
      renderSharhParasEditor(bookData.units[ui], Number(el.dataset.pi));
      showToast('هذه الفقرة ممتدة عبر صفحتين — حُرِّرَت كاملةً في لوحة التحرير');
    }}
  }});

  // Unit Field Inputs inside Center Editor
  document.getElementById('ed-toc-book').addEventListener('input', (e) => {{
    bookData.units[activeUnitIdx].toc_book = e.target.value;
    markDirty();
  }});
  document.getElementById('ed-toc-fasl').addEventListener('input', (e) => {{
    const u = bookData.units[activeUnitIdx];
    u.toc_fasl = e.target.value;
    u.heading = e.target.value;
    markDirty();
  }});
  document.getElementById('ed-lesson-note').addEventListener('input', (e) => {{
    bookData.units[activeUnitIdx].lesson_note = e.target.value;
    markDirty();
  }});
  document.getElementById('ed-fasl-end').addEventListener('change', (e) => {{
    bookData.units[activeUnitIdx].fasl_end = e.target.checked;
    markDirty(true);
  }});
  document.getElementById('ed-matn-text').addEventListener('input', (e) => {{
    const raw = e.target.value;
    const u = bookData.units[activeUnitIdx];
    u.matn_raw = raw;
    u.matn_lines = raw.split(/\\r?\\n/).map(s => s.trimEnd()).filter((s, i, a) => s.length > 0 || a.length === 1);
    markDirty();
  }});
  document.getElementById('btn-dots-matn').onclick = () => {{
    const u = bookData.units[activeUnitIdx];
    u.matn_lines = ['............................................'];
    u.matn_raw = '............................................';
    document.getElementById('ed-matn-text').value = '............................................';
    markDirty(true);
  }};

  document.getElementById('btn-add-para').onclick = () => {{
    const u = bookData.units[activeUnitIdx];
    u.sharh_paras_html.push('فقرة شرح جديدة...');
    renderSharhParasEditor(u, u.sharh_paras_html.length - 1);
    markDirty();
  }};

  document.getElementById('btn-add-gloss').onclick = () => {{
    const u = bookData.units[activeUnitIdx];
    u.glosses.push({{ id: 'g_custom_' + Date.now(), term: 'كلمة', pattern: 'كلمة', gloss: 'كلمة: معناها...' }});
    renderGlossEditor(u);
    markDirty();
  }};

  // Unit Operations: Add / Move / Delete
  document.getElementById('btn-add-unit').onclick = () => {{
    const newUnit = {{
      id: 'U_CUSTOM_' + Date.now(),
      lesson_num: bookData.units[activeUnitIdx]?.lesson_num || 1,
      unit_num: bookData.units.length + 1,
      is_preface: false,
      toc_book: '',
      toc_fasl: '[ مَوْضُوعٌ جَدِيدٌ ]',
      lesson_note: '',
      heading: '[ مَوْضُوعٌ جَدِيدٌ ]',
      sharh_header: '',
      matn_raw: 'أَدْخِلْ نَصَّ الْمَتْنِ هُنَا.',
      matn_lines: ['أَدْخِلْ نَصَّ الْمَتْنِ هُنَا.'],
      fasl_end: false,
      sharh_paras_html: ['أَدْخِلْ نَصَّ الشَّرْحِ هُنَا...'],
      ayahs: [],
      glosses: [],
      images: []
    }};
    bookData.units.splice(activeUnitIdx + 1, 0, newUnit);
    activeUnitIdx = activeUnitIdx + 1;
    renderUnitEditor();
    markDirty();
    paginateAndRender(activeUnitIdx);
    showToast('تمت إضافة وحدة جديدة');
  }};

  document.getElementById('btn-move-unit-up').onclick = () => {{
    if (activeUnitIdx <= 0) return;
    const arr = bookData.units;
    [arr[activeUnitIdx - 1], arr[activeUnitIdx]] = [arr[activeUnitIdx], arr[activeUnitIdx - 1]];
    activeUnitIdx--;
    renderUnitEditor();
    markDirty();
    paginateAndRender(activeUnitIdx);
  }};

  document.getElementById('btn-move-unit-down').onclick = () => {{
    const arr = bookData.units;
    if (activeUnitIdx >= arr.length - 1) return;
    [arr[activeUnitIdx + 1], arr[activeUnitIdx]] = [arr[activeUnitIdx], arr[activeUnitIdx + 1]];
    activeUnitIdx++;
    renderUnitEditor();
    markDirty();
    paginateAndRender(activeUnitIdx);
  }};

  document.getElementById('btn-del-unit').onclick = () => {{
    if (bookData.units.length <= 1) return showToast('لا يمكن حذف آخر وحدة في الكتاب');
    if (!confirm('هل تريد حذف هذه الوحدة نهائياً؟')) return;
    bookData.units.splice(activeUnitIdx, 1);
    if (activeUnitIdx >= bookData.units.length) activeUnitIdx = bookData.units.length - 1;
    renderUnitEditor();
    markDirty();
    paginateAndRender(activeUnitIdx);
    showToast('تم حذف الوحدة');
  }};

  document.getElementById('btn-jump-unit-page').onclick = () => scrollPreviewToUnit(activeUnitIdx);

  // ==================== IMAGE UPLOAD HANDLERS ====================
  let pendingImgTarget = null;
  const imgPicker = document.getElementById('file-img-picker');

  function readImageOptimized(file, cb) {{
    const reader = new FileReader();
    reader.onload = () => {{
      const rawUrl = reader.result;
      // Preserve PNG/SVG/WebP with transparency directly unless very huge (> 2.5MB)
      if (file.size < 1800000 || file.type === 'image/svg+xml') {{
        cb(rawUrl);
        return;
      }}
      const img = new Image();
      img.onload = () => {{
        const maxDim = 1400;
        let w = img.width, h = img.height;
        if (w > maxDim || h > maxDim) {{
          const s = maxDim / Math.max(w, h);
          w = Math.round(w * s);
          h = Math.round(h * s);
        }}
        const cv = document.createElement('canvas');
        cv.width = w; cv.height = h;
        cv.getContext('2d').drawImage(img, 0, 0, w, h);
        cb(file.type === 'image/png' ? cv.toDataURL('image/png') : cv.toDataURL('image/jpeg', 0.88));
      }};
      img.src = rawUrl;
    }};
    reader.readAsDataURL(file);
  }}

  imgPicker.addEventListener('change', () => {{
    const f = imgPicker.files[0];
    imgPicker.value = '';
    if (!f || !pendingImgTarget) return;
    readImageOptimized(f, (dataUrl) => {{
      if (pendingImgTarget.kind === 'global') {{
        bookData.book_config[pendingImgTarget.key] = dataUrl;
        const showMap = {{ cover_data_url: 'show_cover', basmalah_data_url: 'show_basmalah', banner_data_url: 'show_banner', stars_data_url: 'show_stars' }};
        if (showMap[pendingImgTarget.key]) bookData.book_config[showMap[pendingImgTarget.key]] = true;
        refreshGlobalAssetThumbs();
        markDirty();
        paginateAndRender();
        showToast('تم تحديث الصورة وإعادة تنضيد الصفحات');
      }} else if (pendingImgTarget.kind === 'unit') {{
        const u = bookData.units[activeUnitIdx];
        if (!u.images) u.images = [];
        u.images.push({{
          id: 'img_' + Date.now(),
          data_url: dataUrl,
          placement: 'before_sharh',
          after_para_idx: 0,
          width_mm: 85,
          align: 'center',
          caption: ''
        }});
        renderUnitImagesEditor(u);
        markDirty();
        paginateAndRender(activeUnitIdx);
        showToast('تمت إضافة الصورة داخل الوحدة');
      }}
    }});
  }});

  window.triggerGlobalImgUpload = function(key) {{
    pendingImgTarget = {{ kind: 'global', key }};
    imgPicker.click();
  }};

  window.resetGlobalImg = function(key) {{
    bookData.book_config[key] = null;
    refreshGlobalAssetThumbs();
    markDirty();
    paginateAndRender();
    showToast('تمت استعادة الصورة الافتراضية');
  }};

  window.toggleGlobalAsset = function(key, val) {{
    bookData.book_config[key] = val;
    syncGlobalAssetControls();
    markDirty();
    paginateAndRender();
  }};

  document.getElementById('btn-add-unit-img').onclick = () => {{
    pendingImgTarget = {{ kind: 'unit' }};
    imgPicker.click();
  }};

  function refreshGlobalAssetThumbs() {{
    const cfg = bookData.book_config;
    const isCl = currentTheme === 'classic';
    document.getElementById('thumb-cover').src = cfg.cover_data_url || DEFAULT_ASSETS.cover;
    document.getElementById('thumb-basmalah').src = cfg.basmalah_data_url || (isCl ? DEFAULT_ASSETS.basmalah_classic : DEFAULT_ASSETS.basmalah_crimson);
    document.getElementById('thumb-banner').src = cfg.banner_data_url || (isCl ? DEFAULT_ASSETS.banner_classic : DEFAULT_ASSETS.banner_crimson);
  }}

  function syncGlobalAssetControls() {{
    const cfg = bookData.book_config;
    document.getElementById('cfg-show-cover').checked = cfg.show_cover;
    document.getElementById('cfg-show-basmalah').checked = cfg.show_basmalah;
    document.getElementById('cfg-show-banner').checked = cfg.show_banner;
    document.getElementById('cfg-show-stars').checked = cfg.show_stars;
    document.getElementById('cfg-show-p2').checked = cfg.show_p2;
    document.getElementById('cfg-show-p3').checked = cfg.show_p3;
    document.getElementById('cfg-show-p4').checked = cfg.show_p4;
    document.getElementById('cfg-basmalah-w').value = cfg.basmalah_width_mm || 72;
    document.getElementById('lbl-basmalah-w').textContent = cfg.basmalah_width_mm || 72;
    document.getElementById('cfg-banner-w').value = cfg.banner_width_mm || 124;
    document.getElementById('lbl-banner-w').textContent = cfg.banner_width_mm || 124;
    refreshGlobalAssetThumbs();
  }}

  ['show_cover', 'show_basmalah', 'show_banner', 'show_stars', 'show_p2', 'show_p3', 'show_p4'].forEach(k => {{
    document.getElementById('cfg-' + k.replace('_', '-')).addEventListener('change', (e) => {{
      bookData.book_config[k] = e.target.checked;
      markDirty();
      paginateAndRender();
    }});
  }});
  document.getElementById('cfg-basmalah-w').addEventListener('input', (e) => {{
    bookData.book_config.basmalah_width_mm = Number(e.target.value);
    document.getElementById('lbl-basmalah-w').textContent = e.target.value;
    markDirty(true);
  }});
  document.getElementById('cfg-banner-w').addEventListener('input', (e) => {{
    bookData.book_config.banner_width_mm = Number(e.target.value);
    document.getElementById('lbl-banner-w').textContent = e.target.value;
    markDirty(true);
  }});

  // Front Matter Tab Binding
  const fmMap = [
    ['fm-title', 'title'], ['fm-subtitle', 'subtitle'], ['fm-p2desc', 'p2_desc'],
    ['fm-author-sharh', 'author_sharh'], ['fm-author-dua', 'author_dua'],
    ['fm-matn-credit', 'matn_credit'], ['fm-p3disc', 'p3_disc'], ['fm-glossary-src', 'glossary_source']
  ];
  function syncFrontMatterInputs() {{
    const fm = bookData.front_matter;
    for (const [id, k] of fmMap) document.getElementById(id).value = fm[k] || '';
  }}
  for (const [id, k] of fmMap) {{
    document.getElementById(id).addEventListener('input', (e) => {{
      bookData.front_matter[k] = e.target.value;
      markDirty();
    }});
  }}

  // Navigation Tabs & Search
  document.querySelectorAll('.nav-tab').forEach(tab => {{
    tab.onclick = () => {{
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.nav-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    }};
  }});
  document.getElementById('unit-search').addEventListener('input', renderUnitNavList);

  // Topbar Controls
  document.getElementById('edition-mode-sel').addEventListener('change', (e) => {{
    currentMode = e.target.value;
    bookData = loadBook(currentMode);
    activeUnitIdx = 0;
    syncGlobalAssetControls();
    syncFrontMatterInputs();
    renderUnitEditor();
    paginateAndRender();
    showToast(currentMode === 'edited' ? 'تم تحميل النسخة المحررة' : 'تم تحميل النسخة الحرفية الكاملة');
  }});

  document.getElementById('theme-sel').addEventListener('change', (e) => {{
    currentTheme = e.target.value;
    paginateAndRender();
  }});

  document.getElementById('zoom-sel').addEventListener('change', (e) => {{
    currentZoom = Number(e.target.value);
    applyZoom();
  }});

  document.getElementById('btn-repaginate').onclick = () => paginateAndRender(activeUnitIdx);

  document.getElementById('btn-toggle-editor').onclick = () => {{
    document.getElementById('editor-pane').classList.toggle('collapsed');
  }};

  document.getElementById('btn-reset-all').onclick = () => {{
    if (!confirm('سيؤدي هذا إلى مسح تعديلاتك المحلية لهذه النسخة والعودة إلى نص الكتاب الأصلي. هل أنت متأكد؟')) return;
    localStorage.removeItem(STORAGE_KEY_PREFIX + currentMode);
    bookData = loadBook(currentMode);
    activeUnitIdx = 0;
    syncGlobalAssetControls();
    syncFrontMatterInputs();
    renderUnitEditor();
    paginateAndRender();
    showToast('تمت استعادة النسخة الأصلية');
  }};

  // Pagination Navigation Buttons
  document.getElementById('jump-pg-in').addEventListener('change', (e) => {{
    const p = Number(e.target.value);
    const el = document.getElementById('pg-' + p);
    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }});
  document.getElementById('btn-prev-pg').onclick = () => {{
    const inp = document.getElementById('jump-pg-in');
    const p = Math.max(1, Number(inp.value) - 1);
    inp.value = p;
    const el = document.getElementById('pg-' + p);
    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }};
  document.getElementById('btn-next-pg').onclick = () => {{
    const inp = document.getElementById('jump-pg-in');
    const maxP = Number(inp.max) || 999;
    const p = Math.min(maxP, Number(inp.value) + 1);
    inp.value = p;
    const el = document.getElementById('pg-' + p);
    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }};

  // Export PDF (162mm x 234mm exact print stylesheet)
  document.getElementById('btn-print-pdf').onclick = async () => {{
    if (dirty) await paginateAndRender();
    showToast('في نافذة الطباعة: اختر Save as PDF واختر Margins: None وتأكد من تفعيل Background graphics');
    setTimeout(() => window.print(), 250);
  }};

  // Export Standalone Print-Ready HTML
  document.getElementById('btn-export-html').onclick = async () => {{
    if (dirty) await paginateAndRender();
    const fontsCss = document.getElementById('embedded-book-fonts').textContent;
    const printCss = document.getElementById('book-print-css').textContent;
    const cloneRoot = document.getElementById('book-root').cloneNode(true);
    cloneRoot.querySelectorAll('.hover-img-tools').forEach(x => x.remove());
    cloneRoot.querySelectorAll('[contenteditable]').forEach(x => x.removeAttribute('contenteditable'));
    const bodyCls = document.body.className;
    const standalone =
      '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">' +
      '<title>' + esc(bookData.front_matter.title) + '</title>' +
      '<style>' + fontsCss + '\\n' + printCss + '\\nhtml,body{{margin:0;padding:0;background:#fff;}} #book-root{{gap:0;}} .page{{margin:0 auto;box-shadow:none;border:none;page-break-after:always;break-after:page;}} .page:last-child{{page-break-after:auto;break-after:auto;}} @media print{{.page{{margin:0;}}}}</style>' +
      '</head><body class="' + bodyCls + '">' + cloneRoot.outerHTML + '</body></html>';
    const blob = new Blob([standalone], {{ type: 'text/html;charset=utf-8' }});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'تيسير_الانتفاع_' + currentMode + '_للطباعة.html';
    a.click();
    showToast('تم تصدير ملف HTML المنضد الجاهز للطباعة');
  }};

  // Export / Import JSON Project
  document.getElementById('btn-export-json').onclick = () => {{
    const blob = new Blob([JSON.stringify(bookData, null, 2)], {{ type: 'application/json;charset=utf-8' }});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'book_data_' + currentMode + '_edited.json';
    a.click();
    showToast('تم حفظ ملف مشروع الكتاب JSON');
  }};

  const jsonPicker = document.getElementById('file-json-picker');
  document.getElementById('btn-import-json').onclick = () => jsonPicker.click();
  jsonPicker.addEventListener('change', () => {{
    const f = jsonPicker.files[0];
    jsonPicker.value = '';
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {{
      try {{
        const parsed = JSON.parse(r.result);
        if (!Array.isArray(parsed.units)) throw new Error('Invalid');
        bookData = ensureBookSchema(parsed, parsed.mode || currentMode);
        activeUnitIdx = 0;
        syncGlobalAssetControls();
        syncFrontMatterInputs();
        renderUnitEditor();
        saveToLocalStorage();
        paginateAndRender();
        showToast('تم استيراد مشروع الكتاب بنجاح');
      }} catch (err) {{
        alert('تعذّر قراءة ملف JSON: تأكد من صحة الملف.');
      }}
    }};
    r.readAsText(f, 'utf-8');
  }});

  // Keyboard shortcut Ctrl+Enter to repaginate cleanly
  document.addEventListener('keydown', (e) => {{
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {{
      e.preventDefault();
      paginateAndRender(activeUnitIdx);
    }}
  }});

  // Boot
  window.addEventListener('load', () => {{
    syncGlobalAssetControls();
    syncFrontMatterInputs();
    renderUnitEditor();
    paginateAndRender();
  }});
}})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
