import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
const __ENG = path.dirname(fileURLToPath(import.meta.url));

// Ensure Node fetch/WebSocket to 127.0.0.1 does not route through HTTP_PROXY
delete process.env.HTTP_PROXY;
delete process.env.HTTPS_PROXY;
delete process.env.http_proxy;
delete process.env.https_proxy;
process.env.NO_PROXY = '127.0.0.1,localhost';

// Parse args supporting flags like --edition=two-color or --edition two-color
const positional = [];
let EDITION = 'classic';
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a.startsWith('--edition=')) {
    EDITION = a.split('=')[1].trim();
  } else if (a === '--edition' && i + 1 < argv.length) {
    EDITION = argv[++i].trim();
  } else {
    positional.push(a);
  }
}

const DATA_PATH = positional[0] || path.join(__ENG, 'book_data.json');
const OUT_PDF = positional[1] || '/tmp/book_preview.pdf';
const OUT_HTML = positional[2] || '/tmp/book_paginated.html';
const PORT = EDITION === 'two-color' ? 9243 : 9241;

const TEMPLATE_HTML = fs.readFileSync(path.join(__ENG, 'template_book.html'), 'utf8');
const BOOK_DATA = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function launchChrome() {
  const userDataDir = `/tmp/chrome_book_prof_${EDITION}_${Date.now()}`;
  const proc = spawn('chromium', [
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--allow-file-access-from-files',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank'
  ], { stdio: ['ignore', 'ignore', 'ignore'] });

  let targets = null;
  for (let i = 0; i < 40; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      if (res.ok) {
        targets = await res.json();
        if (targets.length > 0) break;
      }
    } catch {}
    await sleep(200);
  }
  if (!targets || targets.length === 0) {
    proc.kill();
    throw new Error('Failed to connect to Chromium CDP');
  }
  return { proc, wsUrl: targets[0].webSocketDebuggerUrl, userDataDir };
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 0;
    this.pending = new Map();
    this.ready = new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });
    this.ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    };
  }
  async send(method, params = {}) {
    await this.ready;
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { this.ws.close(); }
}

const PAGINATE_FN_SRC = `
window.renderFullBook = async function(data, edition) {
  await Promise.all([
    document.fonts.load('400 12pt AmiriBook'),
    document.fonts.load('700 12pt AmiriBook'),
    document.fonts.load('italic 400 12pt AmiriBook'),
    document.fonts.load('400 12pt AmiriQuranFont'),
  ]);
  await document.fonts.ready;
  if (edition === 'two-color') {
    document.body.classList.add('edition-two-color');
  } else {
    document.body.classList.remove('edition-two-color');
  }

  const root = document.getElementById('book-root');
  root.innerHTML = '';

  const EDIGITS = '٠١٢٣٤٥٦٧٨٩';
  const toE = (n) => String(n).replace(/[0-9]/g, d => EDIGITS[+d]);
  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

  const STAR_SVG = '<svg class="star-svg" viewBox="0 0 100 100"><g transform="translate(50,50)"><circle r="9" fill="currentColor"/>' +
    [0,45,90,135,180,225,270,315].map(a => '<path d="M0,-12 C6,-28 8,-44 0,-48 C-8,-44 -6,-28 0,-12 Z" fill="currentColor" transform="rotate('+a+')"/>').join('') +
    '</g></svg>';
  const THREE_STARS_HTML = '<div class="stars-row">' + STAR_SVG + STAR_SVG + STAR_SVG + '</div>';

  function tokenizeHtml(htmlStr) {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlStr;
    const atoms = [];
    function walk(node, wrap) {
      if (node.nodeType === Node.TEXT_NODE) {
        const parts = node.textContent.split(/(\\s+)/);
        for (const p of parts) {
          if (!p) continue;
          if (/^\\s+$/.test(p)) {
            if (atoms.length) atoms[atoms.length - 1].trail = ' ';
          } else {
            atoms.push({ text: p, wrap: wrap, trail: '' });
          }
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const tag = node.tagName.toLowerCase();
        const cls = node.getAttribute('class') || '';
        walkChildren(node, [...wrap, { tag, cls }]);
      }
    }
    function walkChildren(el, wrap) {
      for (const ch of el.childNodes) walk(ch, wrap);
    }
    walkChildren(tmp, []);
    return atoms;
  }

  function joinAtoms(atoms) {
    if (!atoms.length) return '';
    let out = '';
    let openStack = [];
    const closeAll = (toLevel) => {
      while (openStack.length > toLevel) {
        const w = openStack.pop();
        out += '</' + w.tag + '>';
      }
    };
    for (let i = 0; i < atoms.length; i++) {
      const a = atoms[i];
      let matchLen = 0;
      while (matchLen < openStack.length && matchLen < a.wrap.length &&
             openStack[matchLen].tag === a.wrap[matchLen].tag &&
             openStack[matchLen].cls === a.wrap[matchLen].cls) {
        matchLen++;
      }
      closeAll(matchLen);
      for (let j = matchLen; j < a.wrap.length; j++) {
        const w = a.wrap[j];
        out += '<' + w.tag + (w.cls ? ' class="' + w.cls + '"' : '') + '>';
        openStack.push(w);
      }
      out += esc(a.text) + (i < atoms.length - 1 ? a.trail : '');
    }
    closeAll(0);
    return out;
  }

  let pageCounter = 0;
  function makeHeaderHtml(pNum, centerText) {
    const eNum = toE(pNum);
    const isEven = (pNum % 2 === 0);
    return '<div class="running-header">' +
      '<span class="rh-side rh-right">' + (isEven ? eNum : '') + '</span>' +
      '<span class="rh-center">' + esc(centerText) + '</span>' +
      '<span class="rh-side rh-left">' + (!isEven ? eNum : '') + '</span>' +
    '</div>';
  }

  function getHeaderTitle(pNum) {
    if (pNum % 2 === 0) return '« تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ »';
    return 'لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ';
  }

  function createPage({ framed = false, cover = false, skipHeader = false, centerTitle = null } = {}) {
    pageCounter++;
    const pNum = pageCounter;
    const el = document.createElement('div');
    let cls = 'page';
    if (framed) cls += ' framed-page';
    if (cover) cls += ' cover-page';
    el.className = cls;
    el.id = 'pg-' + pNum;
    if (cover) {
      root.appendChild(el);
      return { el, bodyFrame: null, pNum };
    }
    if (!skipHeader) {
      el.innerHTML = makeHeaderHtml(pNum, centerTitle || getHeaderTitle(pNum));
    }
    const bodyFrame = document.createElement('div');
    bodyFrame.className = 'body-frame';
    el.appendChild(bodyFrame);
    root.appendChild(el);
    return {
      el,
      bodyFrame,
      pNum,
      pageFnNum: 0,
      pageGlossaryIds: new Set(),
      pageGlossaryTerms: new Set(),
      lessonNoteText: null,
      glossaryNotes: [],
    };
  }

  // ==================== 1. FRONT MATTER ====================
  // Page 1: Full-Bleed Front Cover Artwork
  {
    const { el } = createPage({ cover: true, skipHeader: true });
    el.innerHTML = '<img class="cover-img" src="' + (window.__BOOK_COVER_URL || 'file:///home/antigravity/book_engine/cover_front.png') + '" alt="تيسير الانتفاع بشرح مختصر أبي شجاع">';
  }

  const isEdited = data.mode === 'edited';

  // Page 2: Inside Title Plate
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    const p2Desc = isEdited
      ? 'تَفْرِيغٌ مُحَرَّرٌ لِمُحَاضَرَاتِ الشَّيْخِ فِي شَرْحِ مَتْنِ أَبِي شُجَاعٍ'
      : 'التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِدُرُوسِ شَرْحِ مَتْنِ أَبِي شُجَاعٍ';
    const p2Right = isEdited
      ? '٢٥ مُحَاضَرَةً مُحَرَّرَةً'
      : '٢٥ لِقَاءً صَوْتِيًّا كَامِلاً';
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner">' +
        '<div style="width:100%;">' +
          '<div class="title-plate-main">' +
            'تَيْسِيرُ الانْتِفَاعِ<br>' +
            '<span style="font-size:17pt; font-weight:400;">بِشَرْحِ</span><br>' +
            '<span style="font-size:25pt;">مُخْتَصَرِ أَبِي شُجَاعٍ</span>' +
          '</div>' +
          '<div class="title-plate-sub">( الْمُسَمَّى بِـ « غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ » )</div>' +
          '<div class="title-plate-desc">' +
            p2Desc +
          '</div>' +
        '</div>' +
        '<div style="font-size: 12pt; line-height: 1.95; width:92%;">' +
          '<div class="title-plate-author">لِفَضِيلَةِ الشَّيْخِ <strong>أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ</strong></div>' +
          '<div style="font-size: 11pt;">( حَفِظَهُ اللهُ تَعَالَى وَنَفَعَ بِعِلْمِهِ )</div>' +
          '<div class="title-plate-divider">' +
            'وَالْمَتْنُ لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ (٤٣٣ – ٥٩٣ هـ)' +
          '</div>' +
        '</div>' +
        '<div class="title-plate-bottom">' +
          '<span>كِتَابُ الطَّهَارَةِ وَكِتَابُ الصَّلاَةِ</span>' +
          '<span>' + p2Right + '</span>' +
        '</div>' +
      '</div></div>';
  }

  // Page 3: Colophon, Methodology & Glossary Source Credit
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    const srcText = data.glossary_source || '«الأَنوَارُ عَلَى غَايَةِ الاِخْتِصَارِ» لِجَامِعِهِ عَبْدِ الرَّحْمَنِ مُحَمَّدٍ نُورِ الدِّينِ';
    const p3Sub = isEdited
      ? '<span style="font-size: 11.5pt; font-weight: 400;">تَفْرِيغٌ مُحَرَّرٌ لِمُحَاضَرَاتِ الشَّيْخِ فِي شَرْحِ مَتْنِ أَبِي شُجَاعٍ</span><br>' +
        '<span style="font-size: 11pt; font-weight: 400;">( الْمُحَاضَرَاتُ : ١ – ٢٥ )</span>'
      : '<span style="font-size: 11.5pt; font-weight: 400;">تَفْرِيغٌ حَرْفِيٌّ كَامِلٌ مُرَاجَعٌ لِدُرُوسِ السِّلْسِلَةِ الْفِقْهِيَّةِ الشَّافِعِيَّةِ</span><br>' +
        '<span style="font-size: 11pt; font-weight: 400;">( اللِّقَاءَاتُ : ١ – ٢٥ )</span>';
    const p3Disc = isEdited
      ? 'أُعِدَّ هَذَا الْكِتَابُ بِتَفْرِيغِ مُحَاضَرَاتِ الشَّيْخِ الشَّارِحِ وَتَحْرِيرِهَا بِالْعَرَبِيَّةِ الْفُصْحَى الْمُيَسَّرَةِ، وَتَنْقِيَتِهَا مِنَ الْعَامِّيَّةِ وَفَوَاتِحِ الدُّرُوسِ وَخَوَاتِمِهَا وَأَسْئِلَةِ الْحُضُورِ، مَعَ الأَمَانَةِ التَّامَّةِ فِي حِفْظِ الْمَعَانِي وَالأَحْكَامِ دُونَ تَغْيِيرٍ أَوْ زِيَادَةٍ.'
      : 'أُعِدَّ هَذَا الْكِتَابُ بِإِثْبَاتِ كَلاَمِ الشَّيْخِ الشَّارِحِ كَامِلاً كَمَا أُلْقِيَ دُونَ حَذْفٍ أَوْ اخْتِصَارٍ ،<br>' +
        'مَعَ إِثْبَاتِ مَتْنِ أَبِي شُجَاعٍ مَضْبُوطاً بِالشَّكْلِ أَعْلَى الصَّفْحَةِ مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ أَسْفَلَهُ';
    const p3Syms = isEdited
      ? '<div>﴿ ... ﴾ لِلآيَاتِ الْقُرْآنِيَّةِ &nbsp;•&nbsp; « ... » لِلأَحَادِيثِ &nbsp;•&nbsp; (١) لِغَرِيبِ الْمَتْنِ</div>'
      : '<div>﴿ ... ﴾ لِلآيَاتِ الْقُرْآنِيَّةِ &nbsp;•&nbsp; « ... » لِلأَحَادِيثِ &nbsp;•&nbsp; (١) لِغَرِيبِ الْمَتْنِ &nbsp;•&nbsp; (*) لِبَيَانِ اللِّقَاءِ الصَّوْتِيِّ</div>';
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner">' +
        '<div style="font-size: 15pt; font-weight: 700; line-height: 1.85; margin-top: 2mm;">' +
          '<span class="colophon-accent">تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ</span><br>' +
          p3Sub +
        '</div>' +
        '<div class="disclaimer-box">' +
          p3Disc +
        '</div>' +
        '<div class="colophon-source-box">' +
          '<div class="colophon-accent">مَنْهَجُ الحَوَاشِي وَتَفْسِيرِ غَرِيبِ الْمَتْنِ :</div>' +
          '<div>أُلْحِقَتْ بِالحَوَاشِي أَسْفَلَ الصَّفَحَاتِ مَعَانِي الأَلْفَاظِ الْغَرِيبَةِ وَبَعْضِ الْمُصْطَلَحَاتِ الَّتِي لَمْ يَتَعَرَّضْ الشَّيْخُ الشَّارِحُ لِبَيَانِهَا فِي مَوْضِعِهَا، مُنْتَقَاةً مِنْ رِسَالَةِ :</div>' +
          '<div class="colophon-source-title">' + esc(srcText) + '</div>' +
          '<div>بِتَرْقِيمٍ مُسْتَقِلٍّ لِكُلِّ صَفْحَةٍ يَبْدَأُ بِـ <span class="colophon-accent">(١)</span> دُونَ تَكْرَارٍ لِلْمَعْنَى فِي الصَّفْحَةِ الْوَاحِدَةِ.</div>' +
        '</div>' +
        '<div style="font-size: 10pt; line-height: 1.85; width: 92%;">' +
          '<div><span class="colophon-accent">رُمُوزُ الضَّبْطِ وَالتَّنْسِيقِ :</span></div>' +
          '<div><strong>الْخَطُّ الْعَرِيضُ دَاخِلَ الشَّرْحِ</strong> يُمَيِّزُ أَلْفَاظَ الْمَتْنِ الَّتِي يَسْتَشْهِدُ بِهَا الشَّارِحُ</div>' +
          p3Syms +
        '</div>' +
        '<div class="colophon-foot">' +
          'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ' +
        '</div>' +
      '</div></div>';
  }

  // Page 4: Basmalah Opening Plate
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner" style="justify-content:center;">' +
        '<div class="basmalah-plate-text">' +
          'بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ' +
        '</div>' +
        '<div style="margin-top:8pt;">' + THREE_STARS_HTML + '</div>' +
      '</div></div>';
  }

  // ==================== 2. CORE SPLIT-PAGE BODY LAYOUT ====================
  const tocEntries = [];
  const lessonStartPage = {};
  const ayahIndexMap = new Map();

  let curPageObj = null;

  function setupPageFootnotesDom(p) {
    p.footnoteArea = p.bodyFrame.querySelector('.footnote-area');
    p.footnoteText = p.bodyFrame.querySelector('.footnote-text');
    p.hasFootnote = false;
  }

  function renderPageFootnotes(p) {
    if (!p.lessonNoteText && p.glossaryNotes.length === 0) {
      p.footnoteArea.style.display = 'none';
      p.footnoteText.innerHTML = '';
      p.hasFootnote = false;
      return;
    }
    p.footnoteArea.style.display = 'block';
    let h = '';
    if (p.lessonNoteText) {
      h += '<div class="fn-lesson-note">(*) ' + esc(p.lessonNoteText) + '</div>';
    }
    for (const g of p.glossaryNotes) {
      const colonIdx = g.text.indexOf(':');
      if (colonIdx > 0) {
        const termPart = g.text.slice(0, colonIdx + 1);
        const bodyPart = g.text.slice(colonIdx + 1);
        h += '<div class="fn-gloss-row"><span class="fn-gloss-num">(' + toE(g.num) + ')</span> <span class="fn-gloss-term">' + esc(termPart) + '</span>' + esc(bodyPart) + '</div>';
      } else {
        h += '<div class="fn-gloss-row"><span class="fn-gloss-num">(' + toE(g.num) + ')</span> ' + esc(g.text) + '</div>';
      }
    }
    p.footnoteText.innerHTML = h;
    p.hasFootnote = true;
  }

  function openPrefacePage(centerOverride = null) {
    const p = createPage({ centerTitle: centerOverride });
    p.bodyFrame.innerHTML =
      '<div class="sharh-zone"></div>' +
      '<div class="footnote-area" style="display:none;"><div class="footnote-rule"></div><div class="footnote-text"></div></div>';
    p.matnZone = null;
    p.sharhZone = p.bodyFrame.querySelector('.sharh-zone');
    setupPageFootnotesDom(p);
    p.unitCountOnPage = 0;
    p.isContPage = false;
    p.isPrefacePage = true;
    return p;
  }

  function openBodyPage(centerOverride = null) {
    const p = createPage({ centerTitle: centerOverride });
    p.bodyFrame.innerHTML =
      '<div class="matn-zone"></div>' +
      '<hr class="split-rule">' +
      '<div class="sharh-zone"></div>' +
      '<div class="footnote-area" style="display:none;"><div class="footnote-rule"></div><div class="footnote-text"></div></div>';
    p.matnZone = p.bodyFrame.querySelector('.matn-zone');
    p.sharhZone = p.bodyFrame.querySelector('.sharh-zone');
    setupPageFootnotesDom(p);
    p.unitCountOnPage = 0;
    p.isContPage = false;
    p.isPrefacePage = false;
    return p;
  }

  // Reserve 2px safety buffer via lastElementChild bounding box for Word .docx font metrics parity.
  // Allow +1/+2px subpixel rounding tolerance on scrollHeight vs clientHeight for fractional footnote/flex boxes.
  function fitsPage(p) {
    if (p.sharhZone.clientHeight < 24) return false;
    if (p.sharhZone.scrollHeight > p.sharhZone.clientHeight + 1) return false;
    if (p.bodyFrame.scrollHeight > p.bodyFrame.clientHeight + 2) return false;
    const lastEl = p.sharhZone.lastElementChild;
    if (lastEl) {
      const sBottom = p.sharhZone.getBoundingClientRect().bottom;
      if (lastEl.getBoundingClientRect().bottom > sBottom - 2) return false;
    }
    return true;
  }

  function buildMatnHtmlForUnit(u, pageObj, isContinuationPage = false) {
    if (isContinuationPage) {
      return '<div class="matn-cont-dots">............................................</div>';
    }
    const glosses = Array.isArray(u.glosses) ? u.glosses : [];
    const lines = u.matn_lines.map(l => String(l));

    // Match each curated gloss on its FIRST unannotated occurrence inside u.matn_lines
    const placements = [];
    for (const g of glosses) {
      if (pageObj.pageGlossaryIds.has(g.id)) continue;
      const normKey = g.term.replace(/[\\u064b-\\u065f\\u0670\\u0640\\s]/g, '');
      if (pageObj.pageGlossaryTerms.has(normKey)) continue;
      const rx = new RegExp(g.pattern);
      for (let li = 0; li < lines.length; li++) {
        const m = rx.exec(lines[li]);
        if (m) {
          placements.push({ g, normKey, li, start: m.index, end: m.index + m[0].length });
          break;
        }
      }
    }
    // Sort by linear reading position so (١), (٢), (٣)... ALWAYS ascend chronologically down the page
    placements.sort((a, b) => (a.li - b.li) || (a.start - b.start));

    const byLine = new Map();
    for (const pl of placements) {
      if (pageObj.pageGlossaryIds.has(pl.g.id) || pageObj.pageGlossaryTerms.has(pl.normKey)) continue;
      pageObj.pageGlossaryIds.add(pl.g.id);
      pageObj.pageGlossaryTerms.add(pl.normKey);
      pageObj.pageFnNum++;
      pl.fnNum = pageObj.pageFnNum;
      pageObj.glossaryNotes.push({ num: pl.fnNum, text: pl.g.gloss });
      if (!byLine.has(pl.li)) byLine.set(pl.li, []);
      byLine.get(pl.li).push(pl);
    }

    // Insert superscript markers right-to-left within each line (string offsets remain valid)
    for (const [li, pls] of byLine.entries()) {
      pls.sort((a, b) => b.end - a.end);
      let s = lines[li];
      for (const pl of pls) {
        const tag = '<sup class="fn-ref">(' + toE(pl.fnNum) + ')</sup>';
        s = s.slice(0, pl.end) + tag + s.slice(pl.end);
      }
      lines[li] = s;
    }

    let h = '';
    let anchorPlaced = false;
    if (u.toc_book) {
      h += '<div class="matn-book-title" id="unit-' + esc(u.id) + '">' + esc(u.toc_book) + '</div>';
      anchorPlaced = true;
    }
    if (u.toc_fasl) {
      const anchorAttr = !anchorPlaced ? ' id="unit-' + esc(u.id) + '"' : '';
      h += '<div class="matn-bracket-title"' + anchorAttr + '>' + esc(u.toc_fasl) + '</div>';
      anchorPlaced = true;
    }
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const anchorAttr = (!anchorPlaced && i === 0) ? ' id="unit-' + esc(u.id) + '"' : '';
      const isBasmalah = (line.trim() === 'بِسْمِ اللهِ الرَّحْمَنِ الرَّحِيمِ');
      h += '<p class="' + (isBasmalah ? 'matn-basmalah' : 'matn-p') + '"' + anchorAttr + '>' + line + '</p>';
      anchorPlaced = true;
    }
    if (u.fasl_end) {
      h += THREE_STARS_HTML;
    }
    return h;
  }

  function recordAyahsOnPage(htmlChunk, pNum) {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlChunk;
    for (const sp of tmp.querySelectorAll('.ayah')) {
      const cleanAyah = sp.textContent.replace(/[﴿﴾]/g, '').replace(/\\s+/g, ' ').trim();
      const wordCount = cleanAyah ? cleanAyah.split(' ').length : 0;
      if (wordCount >= 2 && cleanAyah.length >= 8) {
        if (!ayahIndexMap.has(cleanAyah)) ayahIndexMap.set(cleanAyah, new Set());
        ayahIndexMap.get(cleanAyah).add(pNum);
      }
    }
  }

  function openOverflowPage(u) {
    const np = u.is_preface ? openPrefacePage() : openBodyPage();
    np.isContPage = true;
    if (!u.is_preface) {
      np.matnZone.innerHTML = buildMatnHtmlForUnit(u, np, true);
    }
    np.unitCountOnPage++;
    return np;
  }

  curPageObj = (data.units.length > 0 && data.units[0].is_preface) ? openPrefacePage() : openBodyPage();

  for (let ui = 0; ui < data.units.length; ui++) {
    if (ui % 8 === 0) await new Promise(r => setTimeout(r, 0));
    const u = data.units[ui];

    // STRICT SEPARATION: Every body unit (!u.is_preface) ALWAYS starts cleanly at the top of its own fresh page!
    // Never mix previous unit's continuation dots or Sharh tail with the next Matn unit.
    if (curPageObj.unitCountOnPage > 0) {
      curPageObj = u.is_preface ? openPrefacePage() : openBodyPage();
    }

    if (!(u.lesson_num in lessonStartPage)) {
      lessonStartPage[u.lesson_num] = curPageObj.pNum;
    }
    if (u.toc_book) {
      tocEntries.push({ kind: 'book', title: u.toc_book, page: curPageObj.pNum, anchor: 'unit-' + u.id });
    }
    if (u.toc_fasl) {
      tocEntries.push({ kind: 'fasl', title: u.toc_fasl, page: curPageObj.pNum, anchor: 'unit-' + u.id });
    }

    if (u.is_preface) {
      curPageObj.sharhZone.insertAdjacentHTML('beforeend', '<div class="preface-h" id="unit-' + esc(u.id) + '">' + esc(u.toc_fasl || 'مُقَدِّمَةُ الْكِتَابِ') + '</div>');
    } else {
      const matnHtml = buildMatnHtmlForUnit(u, curPageObj, false);
      curPageObj.matnZone.insertAdjacentHTML('beforeend', matnHtml);
    }
    if (u.lesson_note) {
      curPageObj.lessonNoteText = u.lesson_note;
    }
    renderPageFootnotes(curPageObj);
    curPageObj.unitCountOnPage++;

    // Flow all Sharh paragraphs across curPageObj and clean overflow continuation pages (............................................)
    for (let pi = 0; pi < u.sharh_paras_html.length; pi++) {
      let atoms = tokenizeHtml(u.sharh_paras_html[pi]);
      let isCont = false;

      while (atoms.length > 0) {
        const pEl = document.createElement('p');
        pEl.className = 'sharh-p' + (isCont ? ' cont' : '');
        pEl.innerHTML = joinAtoms(atoms);
        curPageObj.sharhZone.appendChild(pEl);

        if (fitsPage(curPageObj)) {
          recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
          atoms = [];
        } else {
          let lo = 1, hi = atoms.length - 1, best = 0;
          while (lo <= hi) {
            const mid = (lo + hi) >> 1;
            pEl.innerHTML = joinAtoms(atoms.slice(0, mid));
            if (fitsPage(curPageObj)) {
              best = mid;
              lo = mid + 1;
            } else {
              hi = mid - 1;
            }
          }

          const priorParaCount = curPageObj.sharhZone.querySelectorAll('p.sharh-p').length - 1;
          if (best <= 0 || (priorParaCount > 0 && best < 3)) {
            if (!curPageObj.isContPage || priorParaCount > 0) {
              curPageObj.sharhZone.removeChild(pEl);
              curPageObj = openOverflowPage(u);
              continue;
            } else {
              best = Math.min(12, atoms.length);
            }
          }

          const headAtoms = atoms.slice(0, best);
          const tailAtoms = atoms.slice(best);
          pEl.innerHTML = joinAtoms(headAtoms);
          recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);

          atoms = tailAtoms;
          isCont = true;

          if (atoms.length > 0) {
            curPageObj = openOverflowPage(u);
          }
        }
      }
    }

    if (u.fasl_end) {
      curPageObj.sharhZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
      if (!fitsPage(curPageObj)) {
        const starsEl = curPageObj.sharhZone.lastElementChild;
        if (starsEl) starsEl.style.margin = '1pt 0';
        if (!fitsPage(curPageObj)) {
          curPageObj.sharhZone.removeChild(starsEl);
        }
      }
    }
  }

  // ==================== 3. BACK MATTER INDEXES ====================
  let ayahStartPage = null;
  if (ayahIndexMap.size > 0) {
    const ayahList = Array.from(ayahIndexMap.entries());
    let ayPage = createPage({ centerTitle: 'فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ' });
    ayahStartPage = ayPage.pNum;
    ayPage.bodyFrame.innerHTML =
      '<div class="toc-page-title">فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ</div>' +
      '<div class="index-col-head"><span>الآيَةُ الْكَرِيمَةُ</span><span>الصَّفْحَةُ</span></div>' +
      '<div id="ayah-list-box"></div>';
    let ayBox = ayPage.bodyFrame.querySelector('#ayah-list-box');

    for (const [ayahTxt, pgSet] of ayahList) {
      const pgs = Array.from(pgSet).sort((a,b) => a-b);
      const pgLinks = pgs.map(p => '<a href="#pg-' + p + '">' + toE(p) + '</a>').join(' ، ');
      const row = document.createElement('div');
      row.className = 'ayah-idx-row';
      row.innerHTML = '<span class="ayah-idx-text">﴿' + esc(ayahTxt) + '﴾</span>' +
                      '<span class="ayah-idx-pages">' + pgLinks + '</span>';
      ayBox.appendChild(row);
      const lastAy = ayBox.lastElementChild;
      const ayOverflow = ayPage.bodyFrame.scrollHeight > ayPage.bodyFrame.clientHeight + 2 ||
        (lastAy && lastAy.getBoundingClientRect().bottom > ayPage.bodyFrame.getBoundingClientRect().bottom - 2);
      if (ayOverflow && ayBox.children.length > 1) {
        ayBox.removeChild(row);
        ayPage = createPage({ centerTitle: 'فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ' });
        ayPage.bodyFrame.innerHTML =
          '<div class="toc-page-title" style="font-size:13pt;">تَابِعُ فَهْرَسِ الآيَاتِ الْقُرْآنِيَّةِ</div>' +
          '<div class="index-col-head"><span>الآيَةُ الْكَرِيمَةُ</span><span>الصَّفْحَةُ</span></div>' +
          '<div id="ayah-list-box"></div>';
        ayBox = ayPage.bodyFrame.querySelector('#ayah-list-box');
        ayBox.appendChild(row);
      }
    }
  }

  const firstTocPg = pageCounter + 1;
  const allTocEntries = [
    ...tocEntries,
    { kind: 'center', title: 'اَلْفَهَارِسُ', page: null, anchor: '' },
  ];
  if (ayahStartPage) {
    allTocEntries.push({ kind: 'fasl', title: 'فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ', page: ayahStartPage, anchor: 'pg-' + ayahStartPage });
  }
  allTocEntries.push({ kind: 'fasl', title: 'اَلْفَهْرَسُ الْعَامُّ', page: firstTocPg, anchor: 'pg-' + firstTocPg });

  let fIdx = 0;
  let tocPgCount = 0;
  while (fIdx < allTocEntries.length) {
    tocPgCount++;
    const pObj = createPage({ centerTitle: 'اَلْفَهْرَسُ الْعَامُّ' });
    const titleStr = tocPgCount === 1 ? 'اَلْفَهْرَسُ الْعَامُّ' : 'تَابِعُ الْفَهْرَسِ الْعَامِّ';
    pObj.bodyFrame.innerHTML =
      '<div class="toc-page-title">' + titleStr + '</div>' +
      '<div class="toc-two-col">' +
        '<div class="toc-col toc-col-right"></div>' +
        '<div class="toc-col toc-col-left"></div>' +
      '</div>';
    const colRight = pObj.bodyFrame.querySelector('.toc-col-right');
    const colLeft = pObj.bodyFrame.querySelector('.toc-col-left');
    const colOverflows = (col) => {
      if (pObj.bodyFrame.scrollHeight > pObj.bodyFrame.clientHeight + 2) return true;
      const bfBottom = pObj.bodyFrame.getBoundingClientRect().bottom - 2;
      const last = col.lastElementChild;
      if (last && last.getBoundingClientRect().bottom > bfBottom) return true;
      return false;
    };

    const makeTocEl = (e) => {
      const div = document.createElement('div');
      if (e.kind === 'center') {
        div.className = 'toc-section-center';
        div.textContent = e.title;
      } else if (e.kind === 'book') {
        div.className = 'toc-book-row';
        div.innerHTML = '<span class="toc-book-label"><a href="#' + esc(e.anchor) + '">' + esc(e.title) + '</a></span>' +
                        '<span class="toc-dots"></span>' +
                        '<span class="toc-pg"><a href="#' + esc(e.anchor) + '">' + toE(e.page) + '</a></span>';
      } else {
        const nbTitle = esc(e.title).replace(/^\\[\\s+/, '[\\u00A0').replace(/\\s+\\]$/, '\\u00A0]');
        div.className = 'toc-row';
        div.innerHTML = '<span class="toc-row-title"><a href="#' + esc(e.anchor) + '">' + nbTitle + '</a></span>' +
                        '<span class="toc-dots"></span>' +
                        '<span class="toc-pg"><a href="#' + esc(e.anchor) + '">' + toE(e.page) + '</a></span>';
      }
      return div;
    };

    const startFIdx = fIdx;
    while (fIdx < allTocEntries.length) {
      const el = makeTocEl(allTocEntries[fIdx]);
      colRight.appendChild(el);
      if (colOverflows(colRight) && colRight.children.length > 1) {
        colRight.removeChild(el);
        break;
      }
      fIdx++;
    }
    while (fIdx < allTocEntries.length) {
      const el = makeTocEl(allTocEntries[fIdx]);
      colLeft.appendChild(el);
      if (colOverflows(colLeft) && colLeft.children.length > 1) {
        colLeft.removeChild(el);
        break;
      }
      fIdx++;
    }
    if (fIdx === startFIdx) break;
  }

  // Ensure all cover/embedded images are decoded before PDF capture
  await Promise.all(Array.from(document.images).map(img => (
    img.complete ? Promise.resolve() : new Promise(r => { img.onload = r; img.onerror = r; })
  )));

  return { totalPages: pageCounter, tocCount: tocEntries.length, ayahCount: ayahIndexMap.size, edition };
};
`;

async function main() {
  console.log(`1. Preparing pagination HTML (edition=${EDITION})...`);
  const runnerScript = `<script>
window.__BOOK_DATA = ${JSON.stringify(BOOK_DATA)};
window.__BOOK_EDITION = ${JSON.stringify(EDITION)};
window.__BOOK_COVER_URL = ${JSON.stringify('file://' + path.join(__ENG, 'cover_front.png'))};
${PAGINATE_FN_SRC}
window.__BOOK_RESULT = null;
window.__BOOK_ERROR = null;
window.addEventListener('load', () => {
  window.renderFullBook(window.__BOOK_DATA, window.__BOOK_EDITION)
    .then(r => { window.__BOOK_RESULT = r; })
    .catch(e => { window.__BOOK_ERROR = String(e && e.stack || e); });
});
</script>`;
  const tmpTemplatePath = `/tmp/book_template_run_${EDITION}.html`;
  fs.writeFileSync(tmpTemplatePath, TEMPLATE_HTML.replace('</body>', runnerScript + '\n</body>'), 'utf8');

  console.log('2. Launching Chromium CDP...');
  const { proc, wsUrl, userDataDir } = await launchChrome();
  const cdp = new CDPClient(wsUrl);
  try {
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Page.navigate', { url: 'file://' + tmpTemplatePath });

    console.log('3. Waiting for DOM pagination...');
    let pagRes = null;
    for (let i = 0; i < 240; i++) {
      await sleep(250);
      const check = await cdp.send('Runtime.evaluate', {
        expression: `JSON.stringify({ res: window.__BOOK_RESULT, err: window.__BOOK_ERROR, pg: document.querySelectorAll('.page').length })`,
        returnByValue: true,
      });
      const val = JSON.parse(check.result.value || '{}');
      if (val.err) throw new Error('Pagination error: ' + val.err);
      if (val.res) {
        pagRes = val.res;
        break;
      }
      if (i % 8 === 0) console.log('   ... pages rendered so far:', val.pg);
    }
    if (!pagRes) throw new Error('Pagination timed out');
    console.log('4. Pagination complete:', pagRes);

    const htmlPath = OUT_HTML || '/tmp/book_paginated.html';
    await cdp.send('Runtime.evaluate', {
      expression: `document.querySelectorAll('script').forEach(s => s.remove()); window.__HTML_LEN = document.documentElement.outerHTML.length;`,
      returnByValue: true,
    });
    const lenRes = await cdp.send('Runtime.evaluate', { expression: `window.__HTML_LEN`, returnByValue: true });
    const totalLen = lenRes.result.value;
    let fullHtml = '<!DOCTYPE html>';
    const chunkSize = 120000;
    for (let offset = 0; offset < totalLen; offset += chunkSize) {
      const ch = await cdp.send('Runtime.evaluate', {
        expression: `document.documentElement.outerHTML.slice(${offset}, ${offset + chunkSize})`,
        returnByValue: true,
      });
      fullHtml += ch.result.value;
    }
    fs.writeFileSync(htmlPath, fullHtml, 'utf8');
    console.log('5. Saved paginated HTML book:', htmlPath, `(${fullHtml.length} chars)`);

    console.log('6. Rendering print-grade PDF...');
    const pdfRes = await cdp.send('Page.printToPDF', {
      paperWidth: 162 / 25.4,
      paperHeight: 234 / 25.4,
      marginTop: 0,
      marginBottom: 0,
      marginLeft: 0,
      marginRight: 0,
      printBackground: true,
      preferCSSPageSize: true,
      generateDocumentOutline: true,
      transferMode: 'ReturnAsStream',
    });
    const streamHandle = pdfRes.stream;
    const chunks = [];
    while (true) {
      const readRes = await cdp.send('IO.read', { handle: streamHandle, size: 256 * 1024 });
      if (readRes.data) {
        chunks.push(readRes.base64Encoded ? Buffer.from(readRes.data, 'base64') : Buffer.from(readRes.data));
      }
      if (readRes.eof) break;
    }
    await cdp.send('IO.close', { handle: streamHandle });
    const pdfBuf = Buffer.concat(chunks);
    fs.writeFileSync(OUT_PDF, pdfBuf);
    console.log('7. Saved PDF:', OUT_PDF, `(${pdfBuf.length} bytes)`);
  } finally {
    cdp.close();
    proc.kill();
    try { fs.rmSync(userDataDir, { recursive: true, force: true }); } catch {}
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
