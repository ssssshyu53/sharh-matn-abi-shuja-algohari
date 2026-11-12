#!/usr/bin/env python3
"""
Builds the interactive Dar Ibn Hazm Book Viewer HTML artifact
(`matn_abi_shuja_transcripts.html`) directly from:
  - `/home/antigravity/book_engine/full_book.html` (the exact 320 paginated Dar Ibn Hazm pages)
  - `/tmp/book_data.json` (the 25 lessons & 167 clause units)
  - `/home/antigravity/تفريغ_كامل_مجرد_كما_ذكر/*.txt` (raw verbatim transcripts)
"""
import glob
import json
import os
import re

ARTIFACT_DIR = "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/bd48a090-cb19-4d3b-a48b-9325825df25c"
BOOK_HTML_PATH = "/home/antigravity/book_engine/full_book.html"
BOOK_DATA_PATH = "/tmp/book_data.json"
RAW_TXT_DIR = "/home/antigravity/تفريغ_كامل_مجرد_كما_ذكر"
OUT_HTML = os.path.join(ARTIFACT_DIR, "matn_abi_shuja_transcripts.html")

with open(BOOK_DATA_PATH, encoding="utf-8") as f:
    book_data = json.load(f)

with open(BOOK_HTML_PATH, encoding="utf-8") as f:
    full_book_html = f.read()

# Extract individual <div class="page..." id="pg-N">...</div> blocks from full_book.html
m_root = re.search(r'<div id="book-root">(.*)</div>\s*</body>', full_book_html, flags=re.S)
book_root_inner = m_root.group(1) if m_root else ""

# Extract raw verbatim text for each lesson
raw_by_lesson = {}
for lnum in range(1, 26):
    matches = sorted(glob.glob(f"{RAW_TXT_DIR}/{lnum:02d}_*.txt"))
    if matches:
        with open(matches[0], encoding="utf-8") as rf:
            raw_by_lesson[lnum] = rf.read()

# Find which page each lesson starts on inside book_root_inner
lesson_start_pg = {}
for l in book_data["lessons"]:
    uid = l["first_unit_id"]
    # Find page containing id="unit-{uid}"
    m_pg = re.search(
        r'<div class="page[^"]*" id="pg-(\d+)"(?:(?!<div class="page).)*?id="unit-' + re.escape(uid) + r'"',
        book_root_inner,
        flags=re.S,
    )
    lesson_start_pg[l["lesson_num"]] = int(m_pg.group(1)) if m_pg else 7

lessons_meta = []
for i, l in enumerate(book_data["lessons"]):
    lnum = l["lesson_num"]
    start_p = lesson_start_pg.get(lnum, 7)
    end_p = (lesson_start_pg.get(lnum + 1, 315) - 1) if lnum < 25 else 314
    if end_p < start_p:
        end_p = start_p
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
<title>الشَّرْحُ الْكَامِلُ عَلَى مَتْنِ أَبِي شُجَاعٍ — طَبْعَةٌ عَلَى نَسَقِ فَتْحِ الْقَرِيبِ الْمُجِيبِ (دار ابن حزم)</title>
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
  --sidebar-bg: #1c1917;
  --sidebar-text: #f5f5f4;
  --accent-gold: #b45309;
  --accent-emerald: #065f46;
}}
[data-theme="sepia"] {{
  --bg-desk: #d6cbb5;
  --paper-bg: #f8f1e0;
  --ink: #1c1610;
}}
[data-theme="white"] {{
  --bg-desk: #cbd5e1;
  --paper-bg: #ffffff;
  --ink: #000000;
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
  font-size: 1.3rem;
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

/* Dar Ibn Hazm Exact Page Styles (162mm x 234mm) */
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
  padding: 13mm 19mm 17mm 19mm;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--paper-bg);
  box-shadow: 0 8px 28px rgba(0,0,0,0.22), 0 1px 3px rgba(0,0,0,0.12);
  border: 1px solid rgba(0,0,0,0.12);
  flex-shrink: 0;
}}
.page.framed-page {{
  padding: 12.5mm 14mm;
}}
.frame-outer {{
  width: 100%;
  height: 100%;
  border: 2.2pt solid var(--ink);
  padding: 2.5pt;
}}
.frame-inner {{
  width: 100%;
  height: 100%;
  border: 0.75pt solid var(--ink);
  padding: 14mm 10mm 11mm 10mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  text-align: center;
}}
.disclaimer-box {{
  border: 1pt solid var(--ink);
  padding: 6mm 10mm;
  margin: 4mm auto;
  width: 86%;
  font-size: 12.5pt;
  font-weight: 700;
  line-height: 1.9;
}}
.running-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 0.65pt solid var(--ink);
  padding-bottom: 3pt;
  margin-bottom: 6pt;
  font-size: 10.5pt;
  line-height: 1.3;
  flex-shrink: 0;
}}
.running-header .rh-side {{ width: 18mm; font-weight: 400; }}
.running-header .rh-right {{ text-align: right; }}
.running-header .rh-left {{ text-align: left; }}
.running-header .rh-center {{ flex: 1; text-align: center; font-weight: 400; }}
.body-frame {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  padding-bottom: 2pt;
}}
.matn-zone {{
  font-size: 13.4pt;
  line-height: 1.85;
  flex-shrink: 0;
}}
.matn-book-title {{
  text-align: center;
  font-size: 17.5pt;
  font-weight: 700;
  line-height: 1.6;
  margin: 0 0 4pt 0;
}}
.matn-bracket-title {{
  text-align: center;
  font-size: 14.5pt;
  font-weight: 700;
  line-height: 1.55;
  margin: 0 0 4pt 0;
}}
.matn-sub-label {{
  text-align: center;
  font-size: 12pt;
  font-weight: 700;
  line-height: 1.5;
  margin: 0 0 2.5pt 0;
  color: #222;
}}
.matn-p {{
  margin: 0 0 1.5pt 0;
  text-align: justify;
  text-align-last: right;
  text-indent: 1.4em;
}}
.matn-cont-context {{
  font-size: 11.8pt;
  line-height: 1.72;
  text-align: justify;
  text-align-last: right;
  color: var(--ink);
  margin: 0;
}}
.matn-cont-tag {{
  font-size: 10.5pt;
  font-weight: 700;
  color: #222;
  margin-left: 4pt;
}}
.stars-row {{
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24pt;
  margin: 4pt 0;
  flex-shrink: 0;
}}
.star-svg {{ width: 8pt; height: 8pt; display: inline-block; }}
.split-rule {{
  border: none;
  border-top: 0.75pt solid var(--ink);
  margin: 4pt 0 5.5pt 0;
  flex-shrink: 0;
}}
.sharh-zone {{
  font-size: 11.4pt;
  line-height: 1.78;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}}
.sharh-center-title {{
  text-align: center;
  font-size: 13.5pt;
  font-weight: 700;
  line-height: 1.6;
  margin: 1pt 0 4pt 0;
}}
.sharh-sub-title {{
  text-align: center;
  font-size: 12pt;
  font-weight: 700;
  line-height: 1.55;
  margin: 1pt 0 3.5pt 0;
}}
.sharh-p {{
  margin: 0 0 1.5pt 0;
  text-align: justify;
  text-align-last: right;
  text-indent: 1.4em;
}}
.sharh-p.cont {{ text-indent: 0; }}
.sharh-p.split-tail {{ text-align-last: justify; }}
.sharh-p strong, .sharh-zone strong {{ font-weight: 700; }}
.ayah {{
  font-family: 'AmiriQuranFont', 'Amiri Quran', 'AmiriBook', serif;
  font-size: 11.5pt;
  line-height: 1.78;
}}
.footnote-area {{
  margin-top: auto;
  padding-top: 5pt;
  flex-shrink: 0;
}}
.footnote-rule {{
  width: 34mm;
  border-top: 0.55pt solid var(--ink);
  margin-bottom: 2.5pt;
}}
.footnote-text {{
  font-size: 8.8pt;
  line-height: 1.55;
  color: var(--ink);
}}
.basmalah-block {{ text-align: center; margin: 1mm 0 2mm 0; }}
.basmalah-text {{
  font-family: 'AmiriQuranFont', 'Amiri Quran', 'AmiriBook', serif;
  font-size: 20pt;
  line-height: 1.65;
  display: inline-block;
  padding: 1pt 14pt;
}}
.front-h {{
  text-align: center;
  font-size: 14.5pt;
  font-weight: 700;
  line-height: 1.6;
  margin: 2pt 0 3.5pt 0;
}}
.front-sub {{ font-size: 12pt; font-weight: 700; margin: 4pt 0 2pt 0; }}
.front-p {{
  font-size: 11pt;
  line-height: 1.66;
  text-align: justify;
  text-align-last: right;
  text-indent: 1.4em;
  margin: 0 0 1.5pt 0;
}}
.classic-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 9.8pt;
  line-height: 1.55;
  margin-top: 4pt;
}}
.classic-table th {{
  border-top: 1pt solid var(--ink);
  border-bottom: 0.8pt solid var(--ink);
  padding: 3pt 4pt;
  font-weight: 700;
  text-align: right;
}}
.classic-table td {{
  border-bottom: 0.35pt solid #888;
  padding: 2.5pt 4pt;
  vertical-align: top;
}}
.classic-table td a, .toc-row a, .toc-book-row a, .ayah-idx-pages a {{
  color: var(--ink);
  text-decoration: none;
}}
.toc-page-title {{
  text-align: center;
  font-size: 17pt;
  font-weight: 700;
  margin: 2pt 0 7pt 0;
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
  border-left: 0.6pt solid var(--ink);
}}
.toc-col-left {{ padding-right: 5.5mm; }}
.toc-book-row {{
  font-size: 10.6pt;
  font-weight: 700;
  margin: 4pt 0 1.5pt 0;
  line-height: 1.55;
  display: flex;
  align-items: baseline;
}}
.toc-book-label {{ padding-right: 10pt; white-space: nowrap; }}
.toc-row {{
  display: flex;
  align-items: baseline;
  font-size: 9.8pt;
  line-height: 1.62;
  margin: 0.5pt 0;
}}
.toc-row-title {{ white-space: normal; max-width: 82%; }}
.toc-dots {{
  flex: 1;
  border-bottom: 1pt dotted #333;
  margin: 0 3pt 3pt 3pt;
  min-width: 8pt;
}}
.toc-pg {{ font-size: 9.8pt; white-space: nowrap; }}
.toc-section-center {{
  text-align: center;
  font-size: 11pt;
  font-weight: 700;
  margin: 5pt 0 2pt 0;
}}
.index-col-head {{
  display: flex;
  justify-content: space-between;
  font-size: 10.2pt;
  font-weight: 700;
  border-bottom: 0.6pt solid var(--ink);
  padding-bottom: 2pt;
  margin-bottom: 4pt;
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
  font-family: 'AmiriQuranFont', 'Amiri Quran', 'AmiriBook', serif;
  flex: 1;
  padding-left: 6pt;
}}
.ayah-idx-pages {{
  white-space: nowrap;
  font-size: 9.8pt;
  min-width: 14mm;
  text-align: left;
}}

/* Verbatim Raw Box */
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
<body data-theme="sepia">

<aside id="sidebar">
  <div class="sb-head">
    <div class="sb-title">الشَّرْحُ الْكَامِلُ عَلَى مَتْنِ أَبِي شُجَاعٍ</div>
    <div class="sb-sub">طَبْعَةٌ مُحَقَّقَةٌ عَلَى نَسَقِ «فَتْحِ الْقَرِيبِ الْمُجِيبِ» — دَارُ ابْنِ حَزْمٍ (٣٢٠ صَفْحَةً)</div>
  </div>
  <div class="sb-search">
    <input type="text" id="searchInput" placeholder="ابحث في الكتاب أو الفصول أو الآيات...">
  </div>
  <ul class="sb-list" id="sidebarList"></ul>
</aside>

<main>
  <header class="top-bar">
    <div class="tb-right">
      <button class="tb-btn active" id="btnAllPages" onclick="showAllBookPages()">📚 عَرْضُ الْكِتَابِ كَامِلاً (٣٢٠ ص)</button>
      <button class="tb-btn" id="btnFront" onclick="showPageRange(1, 6, 'الغلاف والمقدمات وجدول اللقاءات')">📜 الغلاف والمقدمات</button>
      <button class="tb-btn" id="btnIndexes" onclick="showPageRange(315, 320, 'فهرس الآيات والفهرس العام')">🗂️ الفهارس العامة</button>
      <button class="tb-btn" id="btnRawMode" onclick="toggleRawVerbatim()">📝 النص الحرفي الخام للدرس</button>
      <button class="tb-btn" id="btnVideo" onclick="toggleVideo()" style="display:none;">🎥 التسجيل الصوتي/المرئي</button>
    </div>
    <div class="tb-left">
      <span style="font-size:0.8rem;">انتقل لصفحة:</span>
      <input type="number" min="1" max="320" value="1" id="pgJump" class="pg-jump-input" onchange="jumpToPage(this.value)">
      <button class="tb-btn" onclick="cyclePaperTheme()">🎨 لون الورق</button>
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
const EDIGITS = '٠١٢٣٤٥٦٧٨٩';
const toE = (n) => String(n).replace(/[0-9]/g, d => EDIGITS[+d]);

let activeLessonIdx = -1; // -1 = full book mode
let isRawMode = false;
let isVideoOpen = false;

const allPageEls = Array.from(document.querySelectorAll('#book-root > .page'));

function buildSidebar(filterQ = '') {{
  const ul = document.getElementById('sidebarList');
  ul.innerHTML = '';
  const q = filterQ.trim();

  // Item 0: Cover & Intro (Pages 1-6)
  if (!q) {{
    const liIntro = document.createElement('li');
    liIntro.className = 'sb-item' + (activeLessonIdx === -2 ? ' active' : '');
    liIntro.innerHTML = '<span class="sb-badge">مقدمة</span><span style="flex:1;">الغلاف وترجمة المصنف وجدول الدروس</span><span class="sb-pg">ص ١–٦</span>';
    liIntro.onclick = () => {{ activeLessonIdx = -2; showPageRange(1, 6, 'الغلاف والمقدمات'); buildSidebar(filterQ); }};
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
    liIdx.innerHTML = '<span class="sb-badge">فهارس</span><span style="flex:1;">فهرس الآيات القرآنية والفهرس العام</span><span class="sb-pg">ص ٣١٥–٣٢٠</span>';
    liIdx.onclick = () => {{ activeLessonIdx = -3; showPageRange(315, 320, 'الفهارس العامة'); buildSidebar(filterQ); }};
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
  document.getElementById('btnIndexes').classList.toggle('active', startP >= 314);
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
  }}
  document.getElementById('verbatimPanel').textContent = l.verbatim || '';
  buildSidebar(document.getElementById('searchInput').value);
}}

function jumpToPage(val) {{
  const pNum = Math.max(1, Math.min(320, parseInt(val, 10) || 1));
  const target = document.getElementById('pg-' + pNum);
  if (!target) return;
  if (target.style.display === 'none') {{
    allPageEls.forEach(p => p.style.display = 'flex');
    document.getElementById('btnAllPages').classList.add('active');
  }}
  target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}}

function toggleRawVerbatim() {{
  if (activeLessonIdx < 0) {{
    selectLesson(0);
  }}
  isRawMode = !isRawMode;
  updateRawModeUI();
}}

function updateRawModeUI() {{
  const vPanel = document.getElementById('verbatimPanel');
  const bookRoot = document.getElementById('book-root');
  const btn = document.getElementById('btnRawMode');
  if (isRawMode) {{
    vPanel.style.display = 'block';
    bookRoot.style.display = 'none';
    btn.classList.add('active');
    btn.textContent = '📖 العودة لصفحات طبعة دار ابن حزم';
  }} else {{
    vPanel.style.display = 'none';
    bookRoot.style.display = 'flex';
    btn.classList.remove('active');
    btn.textContent = '📝 النص الحرفي الخام للدرس';
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

const themes = ['sepia', 'white'];
let tIdx = 0;
function cyclePaperTheme() {{
  tIdx = (tIdx + 1) % themes.length;
  document.body.setAttribute('data-theme', themes[tIdx]);
}}

// Intercept internal #pg-N and #unit-... links so clicking TOC or Lesson Schedule jumps smoothly!
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
  // Also filter visible pages in book-root if in all-pages mode
  allPageEls.forEach(p => {{
    p.style.display = p.textContent.includes(q) ? 'flex' : 'none';
  }});
}});

buildSidebar();
</script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as out_f:
    out_f.write(viewer_html)

print(f"Successfully wrote Dar Ibn Hazm interactive viewer ({len(viewer_html):,} bytes) to {OUT_HTML}")
