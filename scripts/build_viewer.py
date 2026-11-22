#!/usr/bin/env python3
"""
Builds the interactive Book Viewer HTML artifact for:
«تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ»
Directly from:
  - `full_book.html` / `full_book_edited.html`
  - `cover_front.png`
  - `book_data.json` / `book_data_edited.json`
  - Raw transcripts in `تفريغ_كامل_مجرد_كما_ذكر/`

Supports 3 reading themes:
  1. نسخة لونين — أحمر وأسود (`two-color`)
  2. أبيض كلاسيكي (`white`)
  3. ورق قديم (`sepia`)
"""
import argparse
import base64
import glob
import io
import json
import os
import re
from PIL import Image

_PARSER = argparse.ArgumentParser()
_PARSER.add_argument("--mode", choices=("verbatim", "edited"), default="verbatim")
_ARGS, _ = _PARSER.parse_known_args()
IS_EDITED = (_ARGS.mode == "edited")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENG = os.path.join(_REPO, "book_engine")
ARTIFACT_DIR = "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/bd48a090-cb19-4d3b-a48b-9325825df25c"

BOOK_HTML_PATH = os.path.join(_ENG, "full_book_edited.html" if IS_EDITED else "full_book.html")
BOOK_DATA_PATH = os.path.join(_ENG, "book_data_edited.json" if IS_EDITED else "book_data.json")
COVER_PATH = os.path.join(_ENG, "cover_front.png")
RAW_TXT_DIR = os.path.join(_REPO, "تفريغ_كامل_مجرد_كما_ذكر")
OUT_HTML = os.path.join(ARTIFACT_DIR, "matn_abi_shuja_edited.html" if IS_EDITED else "matn_abi_shuja_transcripts.html")
REPO_VIEWER_HTML = os.path.join(_REPO, "viewer", "matn_abi_shuja_edited.html" if IS_EDITED else "matn_abi_shuja_transcripts.html")
ROOT_INDEX_HTML = None if IS_EDITED else os.path.join(_REPO, "index.html")

EDIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

def to_e(n) -> str:
    return str(n).translate(EDIGITS)

def encode_cover_data_uri(img_path: str) -> str:
    im = Image.open(img_path).convert("RGB")
    im_resized = im.resize((972, 1404), Image.LANCZOS)
    buf = io.BytesIO()
    im_resized.save(buf, format="JPEG", quality=88, optimize=True, progressive=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"

def encode_png_data_uri(img_path: str) -> str:
    with open(img_path, "rb") as pf:
        b64 = base64.b64encode(pf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"

with open(BOOK_DATA_PATH, encoding="utf-8") as f:
    book_data = json.load(f)

with open(BOOK_HTML_PATH, encoding="utf-8") as f:
    full_book_html = f.read()

m_root = re.search(r'<div id="book-root">(.*)</div>\s*</body>', full_book_html, flags=re.S)
book_root_inner = m_root.group(1) if m_root else ""

cover_uri = encode_cover_data_uri(COVER_PATH)
basmalah_classic_uri = encode_png_data_uri(os.path.join(_ENG, "basmalah.png"))
basmalah_plum_uri = encode_png_data_uri(os.path.join(_ENG, "basmalah_crimson.png"))
banner_classic_uri = encode_png_data_uri(os.path.join(_ENG, "banner_classic.png"))
banner_plum_uri = encode_png_data_uri(os.path.join(_ENG, "banner_crimson.png"))
book_root_inner = (
    book_root_inner
    .replace(f"file://{COVER_PATH}", cover_uri)
    .replace(f"file://{os.path.join(_ENG, 'basmalah.png')}", basmalah_plum_uri)
    .replace(f"file://{os.path.join(_ENG, 'basmalah_crimson.png')}", basmalah_plum_uri)
    .replace(f"file://{os.path.join(_ENG, 'banner_classic.png')}", banner_plum_uri)
    .replace(f"file://{os.path.join(_ENG, 'banner_crimson.png')}", banner_plum_uri)
)

# Extract page map for exact page discovery
pg_tokens = re.split(r'<div class="page[^"]*" id="pg-(\d+)"', book_root_inner)[1:]
pg_map = {int(pg_tokens[i]): pg_tokens[i + 1] for i in range(0, len(pg_tokens), 2)}
TOTAL_PAGES = max(pg_map.keys()) if pg_map else 1

indexes_start_pg = TOTAL_PAGES
for pnum in sorted(pg_map.keys()):
    if "فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ" in pg_map[pnum]:
        indexes_start_pg = pnum
        break

# Extract continuous text for each lesson
raw_by_lesson = {}
if IS_EDITED:
    for u in book_data.get("units", []):
        lnum = u["lesson_num"]
        parts = []
        if u.get("heading"):
            parts.append(u["heading"])
        if u.get("matn_raw"):
            parts.append(u["matn_raw"])
        for ph in u.get("sharh_paras_html", []):
            txt = re.sub(r"<[^>]+>", "", ph).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            parts.append(txt)
        raw_by_lesson.setdefault(lnum, []).append("\n\n".join(parts))
    raw_by_lesson = {k: "\n\n━━━━━━━━━━\n\n".join(v) for k, v in raw_by_lesson.items()}
else:
    for lnum in range(1, 26):
        matches = sorted(glob.glob(f"{RAW_TXT_DIR}/{lnum:02d}_*.txt"))
        if matches:
            with open(matches[0], encoding="utf-8") as rf:
                raw_by_lesson[lnum] = rf.read()

# Find which page each lesson starts on inside pg_map
lesson_start_pg = {}
for l in book_data["lessons"]:
    uid = l["first_unit_id"]
    needle = f'id="unit-{uid}"'
    found_pg = None
    for pnum in sorted(pg_map.keys()):
        if pnum >= indexes_start_pg:
            break
        if needle in pg_map[pnum]:
            found_pg = pnum
            break
    lesson_start_pg[l["lesson_num"]] = found_pg if found_pg is not None else 5

first_body_pg = lesson_start_pg.get(1, 5)
front_end_pg = max(1, first_body_pg - 1)

num_lessons = len(book_data["lessons"])
lessons_meta = []
for l in book_data["lessons"]:
    lnum = l["lesson_num"]
    start_p = lesson_start_pg.get(lnum, first_body_pg)
    if lnum < num_lessons:
        next_start = lesson_start_pg.get(lnum + 1, indexes_start_pg)
        end_p = next_start - 1 if next_start > start_p else start_p
    else:
        end_p = max(start_p, indexes_start_pg - 1)
    vid_id = l.get("url", "").split("v=")[-1] if "v=" in l.get("url", "") else ""
    lessons_meta.append({
        "lesson_num": lnum,
        "title": l["title"],
        "video_id": vid_id,
        "duration_min": l["duration_min"],
        "start_page": start_p,
        "end_page": end_p,
        "verbatim": raw_by_lesson.get(lnum, ""),
    })

meta_json = json.dumps(lessons_meta, ensure_ascii=False)

viewer_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Amiri:ital,wght@0,400;0,700;1,400&family=Cairo:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>
@font-face {{
  font-family: 'AmiriBook';
  src: local('Amiri'), url('https://fonts.gstatic.com/s/amiri/v27/J7aRnpd8CGxBHpUrtLMA7w.woff2') format('woff2');
  font-weight: 400; font-style: normal;
}}
@font-face {{
  font-family: 'AmiriBook';
  src: local('Amiri Bold'), url('https://fonts.gstatic.com/s/amiri/v27/J7acnpd8CGxBHp2VkaY6zp5yGw.woff2') format('woff2');
  font-weight: 700; font-style: normal;
}}
@font-face {{
  font-family: 'AmiriQuranFont';
  src: local('Amiri Quran'), url('https://fonts.gstatic.com/s/amiriquran/v15/_Xmo-Hk0rD6DbUL4_vH8ZqP5qQ.woff2') format('woff2');
  font-weight: 400; font-style: normal;
}}

:root {{
  --bg-desk: #e5e0d5;
  --paper-bg: #fffef9;
  --ink: #111111;
  --accent: #111111;
  --matn-ink: #111111;
  --strong-ink: #111111;
  --ayah-ink: #111111;
  --rule-ink: #111111;
  --fn-num-ink: #111111;
  --subtle-ink: #333333;
  --sidebar-bg: #1c1917;
  --sidebar-text: #f5f5f4;
  --accent-gold: #b45309;
}}
[data-theme="sepia"] {{
  --bg-desk: #d6cbb5;
  --paper-bg: #f8f1e0;
  --ink: #1c1610;
  --accent: #1c1610;
  --matn-ink: #1c1610;
  --strong-ink: #1c1610;
  --ayah-ink: #1c1610;
  --rule-ink: #1c1610;
  --fn-num-ink: #1c1610;
  --subtle-ink: #3a3026;
}}
[data-theme="white"] {{
  --bg-desk: #cbd5e1;
  --paper-bg: #ffffff;
  --ink: #111111;
  --accent: #111111;
  --matn-ink: #111111;
  --strong-ink: #111111;
  --ayah-ink: #111111;
  --rule-ink: #111111;
  --fn-num-ink: #111111;
  --subtle-ink: #333333;
}}
[data-theme="two-color"] {{
  --bg-desk: #dfe6ee;
  --paper-bg: #ffffff;
  --ink: #111111;
  --accent: #9b111e;
  --matn-ink: #9b111e;
  --strong-ink: #9b111e;
  --ayah-ink: #111111;
  --rule-ink: #9b111e;
  --fn-num-ink: #9b111e;
  --subtle-ink: #444444;
}}

* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  padding: 0;
  background: var(--bg-desk);
  color: var(--ink);
  font-family: 'Cairo', sans-serif;
  height: 100vh;
  overflow: hidden;
  display: flex;
}}

/* Sidebar Navigation */
aside {{
  width: 330px;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  display: flex;
  flex-direction: column;
  height: 100vh;
  border-left: 1px solid rgba(255,255,255,0.12);
  flex-shrink: 0;
  z-index: 30;
}}
.sb-head {{
  padding: 16px 16px 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  background: rgba(0,0,0,0.25);
}}
.sb-title {{
  font-family: 'AmiriBook', 'Amiri', serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #fde68a;
  line-height: 1.4;
}}
.sb-sub {{
  font-size: 0.78rem;
  color: #a8a29e;
  margin-top: 3px;
}}
.sb-search {{
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}}
.sb-search input {{
  width: 100%;
  padding: 7px 11px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.07);
  color: #fff;
  font-family: inherit;
  font-size: 0.85rem;
  outline: none;
}}
.sb-search input:focus {{
  border-color: #f59e0b;
}}
.sb-list {{
  list-style: none;
  margin: 0;
  padding: 8px;
  overflow-y: auto;
  flex: 1;
}}
.sb-item {{
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
  color: #e7e5e4;
  transition: background 0.15s;
}}
.sb-item:hover {{
  background: rgba(255,255,255,0.09);
}}
.sb-item.active {{
  background: var(--accent-gold);
  color: #fff;
  font-weight: 700;
}}
.sb-badge {{
  background: rgba(0,0,0,0.35);
  color: #fde68a;
  padding: 2px 7px;
  border-radius: 10px;
  font-size: 0.72rem;
  flex-shrink: 0;
}}
.sb-pg {{
  font-family: 'AmiriBook', 'Amiri', serif;
  font-size: 0.85rem;
  color: #d6d3d1;
  flex-shrink: 0;
}}

/* Main Reader Area */
main {{
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}}
header.top-bar {{
  background: #292524;
  color: #f5f5f4;
  padding: 9px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  z-index: 20;
}}
.tb-left, .tb-right {{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}}
.tb-btn {{
  background: rgba(255,255,255,0.09);
  color: #f5f5f4;
  border: 1px solid rgba(255,255,255,0.18);
  padding: 5px 11px;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}}
.tb-btn:hover {{
  background: rgba(255,255,255,0.18);
}}
.tb-btn.active {{
  background: #f59e0b;
  color: #111;
  border-color: #f59e0b;
  font-weight: 700;
}}
.pg-jump-input {{
  width: 64px;
  padding: 4px 7px;
  border-radius: 5px;
  border: 1px solid rgba(255,255,255,0.25);
  background: rgba(0,0,0,0.3);
  color: #fff;
  text-align: center;
  font-family: inherit;
  font-size: 0.82rem;
}}

.reader-scroll {{
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px 60px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
}}

/* Video drawer */
.video-drawer {{
  width: 162mm;
  max-width: 96vw;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 6px 20px rgba(0,0,0,0.25);
  aspect-ratio: 16/9;
  flex-shrink: 0;
  display: none;
}}
.video-drawer iframe {{
  width: 100%;
  height: 100%;
  border: none;
}}

/* Book Page Styles (162mm x 234mm) */
#book-root {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  font-family: 'AmiriBook', 'Amiri', serif;
  color: var(--ink);
  font-feature-settings: "kern" 1, "liga" 1, "mark" 1, "mkmk" 1;
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
  box-shadow: 0 8px 28px rgba(0,0,0,0.22), 0 1px 3px rgba(0,0,0,0.12);
  border: 1px solid rgba(0,0,0,0.12);
  flex-shrink: 0;
}}
.page.cover-page {{
  padding: 0;
}}
.cover-img {{
  width: 162mm;
  height: 234mm;
  display: block;
  object-fit: cover;
}}
.page.framed-page {{
  padding: 12.5mm 14mm;
}}
.frame-outer {{
  width: 100%;
  height: 100%;
  border: 2.2pt solid var(--accent);
  padding: 2.5pt;
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
.title-plate-author strong {{
  color: var(--accent);
}}
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
.colophon-accent {{
  color: var(--accent);
  font-weight: 700;
}}
.colophon-foot {{
  border-top: 0.7pt solid var(--rule-ink);
  padding-top: 4pt;
  width: 85%;
  font-size: 10.5pt;
  color: var(--accent);
  font-weight: 700;
}}
.basmalah-plate-img {{
  width: 72mm;
  height: 67.36mm;
  display: block;
  margin: 0 auto;
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
.rh-wing-svg {{
  width: 18pt;
  height: 9pt;
  display: block;
  color: var(--accent);
}}
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
  height: 22.32mm;
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
  font-family: 'AmiriQuranFont', 'Amiri Quran', serif;
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
.star-svg {{
  width: 11pt;
  height: 11pt;
  display: block;
  color: var(--accent);
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
.sharh-p.cont {{
  text-indent: 0;
}}
.sharh-p strong, .sharh-zone strong {{
  font-weight: 700;
  color: var(--strong-ink);
}}
.ayah {{
  font-family: 'AmiriQuranFont', 'Amiri Quran', serif;
  font-size: 11.4pt;
  line-height: 1.78;
  color: var(--ayah-ink);
}}
.matn-zone .ayah {{
  font-size: 13.2pt;
  color: var(--matn-ink);
}}
.ayah-ref {{
  font-family: 'AmiriBook', 'Amiri', serif;
  font-size: 8.5pt;
  font-weight: 400;
  color: var(--subtle-ink);
  white-space: nowrap;
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
.fn-gloss-row {{
  margin-top: 0.5pt;
}}
.fn-gloss-num {{
  font-weight: 700;
  color: var(--fn-num-ink);
}}
.fn-gloss-term {{
  font-weight: 700;
  color: var(--ink);
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
.toc-col-right {{
  padding-left: 5.5mm;
  border-left: 0.6pt solid var(--rule-ink);
}}
.toc-col-left {{
  padding-right: 5.5mm;
}}
.toc-book-row {{
  font-size: 9.8pt;
  font-weight: 700;
  margin: 4pt 0 1.5pt 0;
  line-height: 1.5;
  display: flex;
  align-items: baseline;
  color: var(--accent);
}}
.toc-book-row a {{
  color: var(--accent);
  text-decoration: none;
}}
.toc-book-label {{
  padding-right: 10pt;
  white-space: nowrap;
}}
.toc-row {{
  display: flex;
  align-items: baseline;
  font-size: 8.8pt;
  line-height: 1.55;
  margin: 0.5pt 0;
}}
.toc-row a, .ayah-idx-pages a {{
  color: var(--ink);
  text-decoration: none;
}}
.toc-row-title {{
  white-space: normal;
  max-width: 85%;
}}
.toc-dots {{
  flex: 1;
  border-bottom: 1pt dotted #555;
  margin: 0 3pt 3pt 3pt;
  min-width: 8pt;
}}
.toc-pg {{
  font-size: 9pt;
  white-space: nowrap;
  color: var(--accent);
  font-weight: 700;
}}
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
  font-family: 'AmiriQuranFont', 'Amiri Quran', serif;
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

/* Verbatim Panel */
.verbatim-panel {{
  width: 162mm;
  max-width: 96vw;
  background: var(--paper-bg);
  color: var(--ink);
  padding: 28px 34px;
  border-radius: 8px;
  box-shadow: 0 8px 28px rgba(0,0,0,0.22);
  font-family: 'AmiriBook', 'Amiri', serif;
  font-size: 14pt;
  line-height: 2.05;
  white-space: pre-wrap;
  text-align: justify;
  display: none;
}}

@media print {{
  aside, header.top-bar, .video-drawer, .verbatim-panel {{ display: none !important; }}
  html, body, main, .reader-scroll {{
    height: auto !important;
    overflow: visible !important;
    background: #fff !important;
    padding: 0 !important;
  }}
  #book-root {{ gap: 0 !important; }}
  .page {{
    box-shadow: none !important;
    border: none !important;
    page-break-after: always;
    break-after: page;
  }}
}}
</style>
</head>
<body data-theme="two-color">

<aside id="sidebar">
  <div class="sb-head">
    <div class="sb-title">تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ{' — النُّسْخَةُ الْمُحَرَّرَةُ' if IS_EDITED else ''}</div>
    <div class="sb-sub">لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ ({to_e(TOTAL_PAGES)} صَفْحَةً)</div>
  </div>
  <div class="sb-search">
    <input type="text" id="searchInput" placeholder="ابحث في الكتاب أو الفصول أو الآيات...">
  </div>
  <ul class="sb-list" id="sidebarList"></ul>
</aside>

<main>
  <header class="top-bar">
    <div class="tb-right">
      <button class="tb-btn active" id="btnAllPages" onclick="showAllBookPages()">📚 عَرْضُ الْكِتَابِ كَامِلاً ({to_e(TOTAL_PAGES)} ص)</button>
      <button class="tb-btn" id="btnFront" onclick="showPageRange(1, {front_end_pg}, 'الغلاف والافتتاحية')">📜 الغلاف والافتتاحية</button>
      <button class="tb-btn" id="btnIndexes" onclick="showPageRange({indexes_start_pg}, {TOTAL_PAGES}, 'فهرس الآيات والفهرس العام')">🗂️ الفهارس العامة</button>
      <button class="tb-btn" id="btnRawMode" onclick="toggleRawVerbatim()">{'📝 النص المتصل المحرر للباب' if IS_EDITED else '📝 النص الحرفي الخام للدرس'}</button>
      <button class="tb-btn" id="btnVideo" onclick="toggleVideo()" style="display:none;">🎥 التسجيل الصوتي/المرئي</button>
    </div>
    <div class="tb-left">
      <span style="font-size:0.8rem;">انتقل لصفحة:</span>
      <input type="number" min="1" max="{TOTAL_PAGES}" value="1" id="pgJump" class="pg-jump-input" onchange="jumpToPage(this.value)">
      <button class="tb-btn" id="btnTheme" onclick="cyclePaperTheme()">🎨 نسخة لونين</button>
      <button class="tb-btn" onclick="window.print()">🖨️ طباعة / PDF</button>
    </div>
  </header>

  <div class="reader-scroll" id="readerScroll">
    <div class="video-drawer" id="videoDrawer">
      <iframe id="ytIframe" src="" allowfullscreen></iframe>
    </div>
    <div id="verbatimPanel" class="verbatim-panel"></div>
    <div id="book-root">{book_root_inner}</div>
  </div>
</main>

<script>
const LESSONS = {meta_json};
const TOTAL_PAGES = {TOTAL_PAGES};
const FRONT_END_PG = {front_end_pg};
const INDEXES_START_PG = {indexes_start_pg};
const EDIGITS = '٠١٢٣٤٥٦٧٨٩';
const toE = (n) => String(n).replace(/[0-9]/g, d => EDIGITS[+d]);

let activeLessonIdx = -1;
let isRawMode = false;
let isVideoOpen = false;

const allPageEls = Array.from(document.querySelectorAll('#book-root > .page'));

function buildSidebar(filterQ = '') {{
  const ul = document.getElementById('sidebarList');
  ul.innerHTML = '';
  const q = filterQ.trim();

  if (!q) {{
    const liIntro = document.createElement('li');
    liIntro.className = 'sb-item' + (activeLessonIdx === -2 ? ' active' : '');
    liIntro.innerHTML = '<span class="sb-badge">الافتتاحية</span><span style="flex:1;">الغلاف وبيانات الطبعة والبسملة</span><span class="sb-pg">ص ١–' + toE(FRONT_END_PG) + '</span>';
    liIntro.onclick = () => {{ activeLessonIdx = -2; showPageRange(1, FRONT_END_PG, 'الغلاف والافتتاحية'); buildSidebar(filterQ); }};
    ul.appendChild(liIntro);
  }}

  LESSONS.forEach((l, idx) => {{
    if (q) {{
      const matchLesson = l.title.includes(q) || (l.verbatim && l.verbatim.includes(q));
      if (!matchLesson) return;
    }}
    const li = document.createElement('li');
    li.className = 'sb-item' + (activeLessonIdx === idx ? ' active' : '');
    const shortTitle = l.title.replace(/^اللقاء [^:]+:\\s*/, '');
    li.innerHTML =
      '<span class="sb-badge">لقاء ' + toE(l.lesson_num) + '</span>' +
      '<span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">' + shortTitle + '</span>' +
      '<span class="sb-pg">ص ' + toE(l.start_page) + '</span>';
    li.onclick = () => selectLesson(idx);
    ul.appendChild(li);
  }});

  if (!q) {{
    const liIdx = document.createElement('li');
    liIdx.className = 'sb-item' + (activeLessonIdx === -3 ? ' active' : '');
    liIdx.innerHTML = '<span class="sb-badge">فهارس</span><span style="flex:1;">فهرس الآيات القرآنية والفهرس العام</span><span class="sb-pg">ص ' + toE(INDEXES_START_PG) + '–' + toE(TOTAL_PAGES) + '</span>';
    liIdx.onclick = () => {{ activeLessonIdx = -3; showPageRange(INDEXES_START_PG, TOTAL_PAGES, 'الفهارس العامة'); buildSidebar(filterQ); }};
    ul.appendChild(liIdx);
  }}
}}

function showAllBookPages() {{
  activeLessonIdx = -1;
  isRawMode = false;
  updateRawModeUI();
  document.getElementById('btnAllPages').classList.add('active');
  document.getElementById('btnFront').classList.remove('active');
  document.getElementById('btnIndexes').classList.remove('active');
  document.getElementById('btnVideo').style.display = 'none';
  document.getElementById('videoDrawer').style.display = 'none';
  allPageEls.forEach(p => p.style.display = 'flex');
  buildSidebar(document.getElementById('searchInput').value);
  document.getElementById('readerScroll').scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function showPageRange(startP, endP, label) {{
  isRawMode = false;
  updateRawModeUI();
  document.getElementById('btnAllPages').classList.remove('active');
  document.getElementById('btnFront').classList.toggle('active', startP === 1);
  document.getElementById('btnIndexes').classList.toggle('active', startP >= INDEXES_START_PG);
  allPageEls.forEach(p => {{
    const pNum = parseInt(p.id.replace('pg-', ''), 10);
    p.style.display = (pNum >= startP && pNum <= endP) ? 'flex' : 'none';
  }});
  document.getElementById('readerScroll').scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function selectLesson(idx) {{
  activeLessonIdx = idx;
  const l = LESSONS[idx];
  showPageRange(l.start_page, l.end_page, l.title);
  document.getElementById('pgJump').value = l.start_page;
  const vBtn = document.getElementById('btnVideo');
  if (l.video_id) {{
    vBtn.style.display = 'inline-block';
    if (isVideoOpen) {{
      document.getElementById('ytIframe').src = 'https://www.youtube-nocookie.com/embed/' + l.video_id + '?rel=0';
    }}
  }} else {{
    vBtn.style.display = 'none';
    document.getElementById('videoDrawer').style.display = 'none';
  }}
  buildSidebar(document.getElementById('searchInput').value);
}}

function jumpToPage(val) {{
  const n = parseInt(val, 10);
  if (isNaN(n) || n < 1 || n > TOTAL_PAGES) return;
  const target = document.getElementById('pg-' + n);
  if (!target) return;
  if (target.style.display === 'none') {{
    allPageEls.forEach(p => p.style.display = 'flex');
    document.getElementById('btnAllPages').classList.add('active');
  }}
  target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}}

function toggleRawVerbatim() {{
  isRawMode = !isRawMode;
  updateRawModeUI();
}}

function updateRawModeUI() {{
  const panel = document.getElementById('verbatimPanel');
  const bookRoot = document.getElementById('book-root');
  const btn = document.getElementById('btnRawMode');
  if (isRawMode) {{
    btn.classList.add('active');
    bookRoot.style.display = 'none';
    panel.style.display = 'block';
    if (activeLessonIdx >= 0) {{
      panel.textContent = LESSONS[activeLessonIdx].verbatim || 'لا يتوفر تفريغ خام لهذا اللقاء.';
    }} else {{
      panel.textContent = LESSONS.map(l => '=== ' + l.title + ' ===\\n\\n' + l.verbatim).join('\\n\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n');
    }}
  }} else {{
    btn.classList.remove('active');
    panel.style.display = 'none';
    bookRoot.style.display = 'flex';
  }}
}}

function toggleVideo() {{
  isVideoOpen = !isVideoOpen;
  const drawer = document.getElementById('videoDrawer');
  const iframe = document.getElementById('ytIframe');
  const btn = document.getElementById('btnVideo');
  if (isVideoOpen && activeLessonIdx >= 0 && LESSONS[activeLessonIdx].video_id) {{
    drawer.style.display = 'block';
    iframe.src = 'https://www.youtube-nocookie.com/embed/' + LESSONS[activeLessonIdx].video_id + '?rel=0';
    btn.classList.add('active');
  }} else {{
    drawer.style.display = 'none';
    iframe.src = '';
    btn.classList.remove('active');
  }}
}}

const BASMALAH_PLUM_URI = {json.dumps(basmalah_plum_uri)};
const BASMALAH_CLASSIC_URI = {json.dumps(basmalah_classic_uri)};
const BANNER_PLUM_URI = {json.dumps(banner_plum_uri)};
const BANNER_CLASSIC_URI = {json.dumps(banner_classic_uri)};
const themes = [
  {{ key: 'two-color', label: '🎨 نسخة لونين' }},
  {{ key: 'white',     label: '🎨 أبيض كلاسيكي' }},
  {{ key: 'sepia',     label: '🎨 ورق قديم' }},
];
let tIdx = 0;
function cyclePaperTheme() {{
  tIdx = (tIdx + 1) % themes.length;
  const k = themes[tIdx].key;
  document.body.setAttribute('data-theme', k);
  document.getElementById('btnTheme').textContent = themes[tIdx].label;
  document.querySelectorAll('.basmalah-plate-img').forEach(im => {{
    im.src = (k === 'two-color') ? BASMALAH_PLUM_URI : BASMALAH_CLASSIC_URI;
  }});
  document.querySelectorAll('.chapter-banner-img').forEach(im => {{
    im.src = (k === 'two-color') ? BANNER_PLUM_URI : BANNER_CLASSIC_URI;
  }});
}}

document.getElementById('book-root').addEventListener('click', (e) => {{
  const a = e.target.closest('a[href^="#"]');
  if (!a) return;
  e.preventDefault();
  const id = a.getAttribute('href').slice(1);
  const el = document.getElementById(id);
  if (!el) return;
  const pgEl = el.closest('.page') || el;
  if (pgEl.style.display === 'none') {{
    allPageEls.forEach(p => p.style.display = 'flex');
    document.getElementById('btnAllPages').classList.add('active');
  }}
  pgEl.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}});

document.getElementById('searchInput').addEventListener('input', (e) => {{
  const q = e.target.value.trim();
  buildSidebar(q);
  if (!q) return;
  allPageEls.forEach(p => {{
    p.style.display = p.textContent.includes(q) ? 'flex' : 'none';
  }});
}});

buildSidebar();
</script>
</body>
</html>
"""

os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
with open(OUT_HTML, "w", encoding="utf-8") as out_f:
    out_f.write(viewer_html)

os.makedirs(os.path.dirname(REPO_VIEWER_HTML), exist_ok=True)
with open(REPO_VIEWER_HTML, "w", encoding="utf-8") as out_repo:
    out_repo.write(viewer_html)
if ROOT_INDEX_HTML:
    with open(ROOT_INDEX_HTML, "w", encoding="utf-8") as out_root:
        out_root.write(viewer_html)

print(
    f"Successfully wrote interactive viewer ({len(viewer_html):,} bytes, {TOTAL_PAGES} pages, "
    f"indexes={indexes_start_pg}..{TOTAL_PAGES}, front=1..{front_end_pg}) to:\n  - {OUT_HTML}\n  - {REPO_VIEWER_HTML}"
)
