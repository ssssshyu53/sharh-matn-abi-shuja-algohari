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
const PORT = EDITION === 'two-color' ? 9263 : 9261;

const TEMPLATE_HTML = fs.readFileSync(path.join(__ENG, 'template_book.html'), 'utf8');
const BOOK_DATA = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function launchChrome() {
  const userDataDir = `/tmp/chrome_book_prof_${EDITION}_${Date.now()}`;
  const chromeBin = process.env.CHROME_BIN || ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].find(p => fs.existsSync(p)) || 'chromium';
  const proc = spawn(chromeBin, [
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

  const WING_SVG =
    '<svg class="rh-wing-svg" viewBox="0 0 28 12">' +
      '<line x1="2" y1="2.5" x2="26" y2="2.5" stroke="currentColor" stroke-width="0.95"/>' +
      '<line x1="0" y1="6" x2="28" y2="6" stroke="currentColor" stroke-width="0.95"/>' +
      '<line x1="2" y1="9.5" x2="26" y2="9.5" stroke="currentColor" stroke-width="0.95"/>' +
    '</svg>';

  // Preload & decode all book plate/banner images BEFORE synchronous pagination
  const coverUrl = window.__BOOK_COVER_URL || 'file:///home/antigravity/sharh-matn-abi-shuja-algohari/book_engine/cover_front.png';
  const basmalahUrl = window.__BASMALAH_URL || ('file:///home/antigravity/sharh-matn-abi-shuja-algohari/book_engine/' + (edition === 'two-color' ? 'basmalah_crimson.png' : 'basmalah.png'));
  const bannerUrl = window.__BANNER_URL || ('file:///home/antigravity/sharh-matn-abi-shuja-algohari/book_engine/' + (edition === 'two-color' ? 'banner_crimson.png' : 'banner_classic.png'));
  await Promise.all([coverUrl, basmalahUrl, bannerUrl].map(u => new Promise(res => {
    const im = new Image();
    im.onload = () => (im.decode ? im.decode().catch(() => {}).finally(res) : res());
    im.onerror = res;
    im.src = u;
  })));

  const CHAPTER_BANNER_HTML = '<div class="chapter-banner"><img class="chapter-banner-img" src="' + bannerUrl + '" alt=""></div>';

  // Three side-by-side ornamental 8-petal floral stars (no center diamond symbol)
  const THREE_STARS_HTML = '<div class="stars-row">' + STAR_SVG + STAR_SVG + STAR_SVG + '</div>';

  function tokenizeHtml(htmlStr) {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlStr;
    const atoms = [];
    function pushTextWords(str, wrap) {
      const parts = str.split(/(\\s+)/);
      for (const p of parts) {
        if (!p) continue;
        if (/^\\s+$/.test(p)) {
          if (atoms.length) atoms[atoms.length - 1].trail = ' ';
        } else if (atoms.length && !atoms[atoms.length - 1].trail && /^[.،؛:؟!»)\\]]+$/.test(p)) {
          atoms[atoms.length - 1].postPunct = (atoms[atoms.length - 1].postPunct || '') + p;
        } else {
          atoms.push({ text: p, wrap: wrap, trail: '', postPunct: '' });
        }
      }
    }
    function walk(node, wrap) {
      if (node.nodeType === Node.TEXT_NODE) {
        pushTextWords(node.textContent, wrap);
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const tag = node.tagName.toLowerCase();
        const cls = node.getAttribute('class') || '';
        const clsList = cls.split(/\\s+/).filter(Boolean);
        if (clsList.includes('ayah-ref')) {
          const refTxt = node.textContent.trim().replace(/\\s+/g, '\\u00A0');
          if (refTxt) {
            if (atoms.length) {
              atoms[atoms.length - 1].suffixRef = refTxt;
              atoms[atoms.length - 1].trail = '';
            } else {
              atoms.push({ text: refTxt, wrap: [...wrap, { tag, cls }], trail: '', postPunct: '' });
            }
          }
          return;
        }
        if (clsList.includes('ayah')) {
          const wordsCount = node.textContent.trim().split(/\\s+/).filter(Boolean).length;
          if (wordsCount <= 42) {
            atoms.push({ text: node.textContent.trim(), wrap: [...wrap, { tag, cls }], trail: '', postPunct: '' });
            return;
          }
        }
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
      out += esc(a.text);
      if (a.suffixRef) {
        closeAll(0);
        out += '\\u00A0<span class="ayah-ref">' + esc(a.suffixRef) + '</span>';
      }
      if (a.postPunct) {
        if (openStack.some(w => w.cls && w.cls.includes('ayah'))) {
          let closeIdx = openStack.findIndex(w => w.cls && w.cls.includes('ayah'));
          closeAll(closeIdx);
        }
        out += esc(a.postPunct);
      }
      if (i < atoms.length - 1) out += a.trail;
    }
    closeAll(0);
    return out;
  }

  const BOOK_HDR_TITLE = 'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ';
  let activeSectionTitle = 'مُقَدِّمَةُ الْكِتَابِ';
  let pageCounter = 0;

  function makeHeaderHtml(pNum, sectionTitleOverride = null) {
    const eNum = toE(pNum);
    const isEven = (pNum % 2 === 0);
    const badgeHtml = '<span class="rh-badge-wrap">' + WING_SVG + '<span class="rh-pill">' + eNum + '</span>' + WING_SVG + '</span>';
    const titleStr = isEven ? BOOK_HDR_TITLE : (sectionTitleOverride || activeSectionTitle || BOOK_HDR_TITLE);
    const titleHtml = '<span class="rh-title">' + esc(titleStr) + '</span>';
    return '<div class="running-header">' +
      (isEven ? (badgeHtml + titleHtml) : (titleHtml + badgeHtml)) +
    '</div>';
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
      el.innerHTML = makeHeaderHtml(pNum, centerTitle);
    }
    const bodyFrame = document.createElement('div');
    bodyFrame.className = 'body-frame';
    el.appendChild(bodyFrame);
    root.appendChild(el);
    return {
      el,
      bodyFrame,
      pNum,
      headerEl: el.querySelector('.running-header'),
      pageFnNum: 0,
      pageGlossaryIds: new Set(),
      pageGlossaryTerms: new Set(),
      lessonNoteText: null,
      glossaryNotes: [],
    };
  }

  function setPageOddHeaderTitle(pageObj, rawTitle) {
    if (!pageObj || !pageObj.headerEl || pageObj.pNum % 2 === 0) return;
    const cleaned = String(rawTitle || '').replace(/^\\[\\s*|\\s*\\]$/g, '').trim();
    if (!cleaned) return;
    activeSectionTitle = cleaned;
    const tEl = pageObj.headerEl.querySelector('.rh-title');
    if (tEl) tEl.textContent = cleaned;
  }

  // ==================== 1. FRONT MATTER ====================
  // Page 1: Full-Bleed Front Cover Artwork
  {
    const { el } = createPage({ cover: true, skipHeader: true });
    el.innerHTML = '<img class="cover-img" src="' + coverUrl + '" alt="تيسير الانتفاع بشرح مختصر أبي شجاع">';
  }

  const isEdited = data.mode === 'edited';

  // Page 2: Inside Title Plate
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    const p2Desc = isEdited
      ? 'تَفْرِيغٌ مُحَرَّرٌ مُهَذَّبٌ لِمُحَاضَرَاتِ الشَّيْخِ فِي شَرْحِ مَتْنِ أَبِي شُجَاعٍ'
      : 'التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِدُرُوسِ شَرْحِ مَتْنِ أَبِي شُجَاعٍ';
    const p2Right = isEdited
      ? '٢٥ مُحَاضَرَةً مُهَذَّبَةً'
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
            'وَالْمَتْنُ لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ <span style="white-space:nowrap;">(٤٣٣ – ٥٩٣ هـ)</span>' +
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
      ? '<span style="font-size: 11.5pt; font-weight: 400;">تَفْرِيغٌ مُحَرَّرٌ مُهَذَّبٌ لِمُحَاضَرَاتِ الشَّيْخِ فِي شَرْحِ مَتْنِ أَبِي شُجَاعٍ</span><br>' +
        '<span style="font-size: 11pt; font-weight: 400;">( الْمُحَاضَرَاتُ : ١ – ٢٥ )</span>'
      : '<span style="font-size: 11.5pt; font-weight: 400;">تَفْرِيغٌ حَرْفِيٌّ كَامِلٌ مُرَاجَعٌ لِدُرُوسِ السِّلْسِلَةِ الْفِقْهِيَّةِ الشَّافِعِيَّةِ</span><br>' +
        '<span style="font-size: 11pt; font-weight: 400;">( اللِّقَاءَاتُ : ١ – ٢٥ )</span>';
    const p3Disc = isEdited
      ? 'أُعِدَّ هَذَا الْكِتَابُ بِتَفْرِيغِ مُحَاضَرَاتِ الشَّيْخِ الشَّارِحِ بِإِثْبَاتِ كَلاَمِهِ كَامِلاً بِلَفْظِهِ دُونَ تَبْدِيلٍ أَوِ اخْتِصَارٍ، مَعَ الاقْتِصَارِ عَلَى مُقَدِّمَةِ اللِّقَاءِ الأَوَّلِ وَخَاتِمَةِ اللِّقَاءِ الأَخِيرِ وَتَهْذِيبِ التَّكْرَارِ اللَّفْظِيِّ الْمُتَتَابِعِ فَحَسْبُ.'
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

  // Page 4: Calligraphic Basmalah PNG Plate
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner" style="justify-content:center;">' +
        '<img class="basmalah-plate-img" src="' + basmalahUrl + '" alt="بسم الله الرحمن الرحيم">' +
        '<div style="margin-top:16pt;">' + THREE_STARS_HTML + '</div>' +
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

  function fitsPage(p) {
    if (p.sharhZone.clientHeight < 24) return false;
    if (p.sharhZone.scrollHeight > p.sharhZone.clientHeight + 1) return false;
    if (p.bodyFrame.scrollHeight > p.bodyFrame.clientHeight + 2) return false;
    const lastEl = p.sharhZone.lastElementChild;
    if (lastEl) {
      const lastBottom = lastEl.getBoundingClientRect().bottom;
      const sBottom = p.sharhZone.getBoundingClientRect().bottom;
      if (lastBottom > sBottom - 2) return false;
      if (p.hasFootnote && p.footnoteArea && lastBottom > p.footnoteArea.getBoundingClientRect().top - 3) return false;
    }
    return true;
  }

  function matnFitsQuota(p, maxMatnPx, keepRoomForSharh) {
    if (p.bodyFrame.scrollHeight > p.bodyFrame.clientHeight + 1) return false;
    if (keepRoomForSharh && p.sharhZone.clientHeight < 92) return false;
    if (maxMatnPx > 0 && p.matnZone.scrollHeight > maxMatnPx) return false;
    return true;
  }

  function prepareUnitMatnData(u) {
    const glosses = Array.isArray(u.glosses) ? u.glosses : [];
    const rawLines = u.matn_lines.map(l => String(l));
    const glossMetaMap = new Map();
    let hasLeadingDots = false;
    let hasTrailingDots = false;

    if (!(rawLines.length === 1 && rawLines[0].trim() === '............................................')) {
      if (rawLines.length > 0 && /^\\.{5,}\\s*/.test(rawLines[0])) {
        hasLeadingDots = true;
        rawLines[0] = rawLines[0].replace(/^\\.{5,}\\s*/, '').trim();
      }
      if (rawLines.length > 0 && /\\s*\\.{5,}$/.test(rawLines[rawLines.length - 1])) {
        hasTrailingDots = true;
        rawLines[rawLines.length - 1] = rawLines[rawLines.length - 1].replace(/\\s*\\.{5,}$/, '').trim();
      }
      const placements = [];
      const seenIds = new Set();
      const seenNorms = new Set();
      for (const g of glosses) {
        if (seenIds.has(g.id)) continue;
        const normKey = g.term.replace(/[\\u064b-\\u065f\\u0670\\u0640\\s]/g, '');
        if (seenNorms.has(normKey)) continue;
        const rx = new RegExp(g.pattern);
        for (let li = 0; li < rawLines.length; li++) {
          const m = rx.exec(rawLines[li]);
          if (m) {
            seenIds.add(g.id);
            seenNorms.add(normKey);
            placements.push({ g, normKey, li, start: m.index, end: m.index + m[0].length });
            break;
          }
        }
      }
      const byLine = new Map();
      for (const pl of placements) {
        if (!byLine.has(pl.li)) byLine.set(pl.li, []);
        byLine.get(pl.li).push(pl);
      }
      for (const [li, pls] of byLine.entries()) {
        pls.sort((a, b) => b.end - a.end);
        let s = rawLines[li];
        for (const pl of pls) {
          const clsName = 'gl-k-' + glossMetaMap.size;
          glossMetaMap.set(clsName, { id: pl.g.id, normKey: pl.normKey, gloss: pl.g.gloss });
          const matchedTxt = s.slice(pl.start, pl.end);
          const tag = '<span class="' + clsName + '">' + matchedTxt + '</span>';
          s = s.slice(0, pl.start) + tag + s.slice(pl.end);
        }
        rawLines[li] = s;
      }
    }

    const wrapMatnAyahs = (s) => {
      return s
        .replace(/(﴿[^﴾]+﴾)/g, '<span class="ayah">$1</span>')
        .replace(/(\\[[^\\]:]+:\\s*[٠-٩\\-]+\\])/g, '<span class="ayah-ref">$1</span>');
    };

    const paraHtmls = rawLines.filter(ln => ln.length > 0).map(ln => wrapMatnAyahs(ln));
    return { paraHtmls, glossMetaMap, hasLeadingDots, hasTrailingDots };
  }

  function finalizeSplitPara(pEl, atoms, best, allowJustify) {
    let splitIdx = best;
    if (atoms.length - splitIdx > 0 && atoms.length - splitIdx <= 5 && splitIdx >= 2) {
      pEl.innerHTML = joinAtoms(atoms.slice(0, splitIdx));
      const hAt = pEl.getBoundingClientRect().height;
      let b2 = splitIdx - 1;
      while (b2 >= 1) {
        pEl.innerHTML = joinAtoms(atoms.slice(0, b2));
        if (pEl.getBoundingClientRect().height < hAt - 2) {
          splitIdx = b2;
          break;
        }
        b2--;
      }
    }
    const headAtoms = atoms.slice(0, splitIdx);
    const tailAtoms = atoms.slice(splitIdx);
    pEl.innerHTML = joinAtoms(headAtoms);
    if (allowJustify && tailAtoms.length > 0) {
      const range = document.createRange();
      range.selectNodeContents(pEl);
      const rects = range.getClientRects();
      const lr = rects.length ? rects[rects.length - 1] : null;
      if (lr && pEl.clientWidth > 0 && lr.width >= pEl.clientWidth * 0.62) {
        pEl.classList.add('split-head');
      }
    }
    return { headAtoms, tailAtoms };
  }

  function applyMatnGlossFootnotes(pageObj, glossMetaMap) {
    pageObj.pageFnNum = 0;
    pageObj.pageGlossaryIds = new Set();
    pageObj.pageGlossaryTerms = new Set();
    pageObj.glossaryNotes = [];
    if (!pageObj.matnZone) return;
    pageObj.matnZone.querySelectorAll('sup.fn-ref').forEach(el => el.remove());
    const spans = pageObj.matnZone.querySelectorAll('[class*="gl-k-"]');
    for (const sp of spans) {
      const clsKey = Array.from(sp.classList).find(c => c.startsWith('gl-k-'));
      const meta = clsKey ? glossMetaMap.get(clsKey) : null;
      if (!meta) continue;
      if (pageObj.pageGlossaryIds.has(meta.id) || pageObj.pageGlossaryTerms.has(meta.normKey)) continue;
      pageObj.pageGlossaryIds.add(meta.id);
      pageObj.pageGlossaryTerms.add(meta.normKey);
      pageObj.pageFnNum++;
      pageObj.glossaryNotes.push({ num: pageObj.pageFnNum, text: meta.gloss });
      const sup = document.createElement('sup');
      sup.className = 'fn-ref';
      sup.textContent = '(' + toE(pageObj.pageFnNum) + ')';
      sp.insertAdjacentElement('afterend', sup);
    }
    renderPageFootnotes(pageObj);
  }

  const ayahRefLookup = new Map();
  if (data.ayah_refs && typeof data.ayah_refs === 'object') {
    for (const [k, v] of Object.entries(data.ayah_refs)) {
      const cleanK = k.replace(/\\s+/g, ' ').trim();
      if (cleanK && v) ayahRefLookup.set(cleanK, String(v).trim());
    }
  }
  for (const u of data.units) {
    for (const pHtml of (u.sharh_paras_html || [])) {
      const tmpA = document.createElement('div');
      tmpA.innerHTML = pHtml;
      for (const sp of tmpA.querySelectorAll('.ayah')) {
        const cleanA = sp.textContent.replace(/[﴿﴾]/g, '').replace(/\\s+/g, ' ').trim();
        const nxt = sp.nextElementSibling;
        if (cleanA && nxt && nxt.classList.contains('ayah-ref') && !ayahRefLookup.has(cleanA)) {
          ayahRefLookup.set(cleanA, nxt.textContent.trim());
        }
      }
    }
  }

  function recordAyahsOnPage(htmlChunk, pNum) {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlChunk;
    tmp.querySelectorAll('.fn-ref').forEach(el => el.remove());
    for (const sp of tmp.querySelectorAll('.ayah')) {
      const cleanAyah = sp.textContent.replace(/[﴿﴾]/g, '').replace(/\\s+/g, ' ').trim();
      const wordCount = cleanAyah ? cleanAyah.split(' ').length : 0;
      if (wordCount >= 2 && cleanAyah.length >= 8) {
        if (!ayahIndexMap.has(cleanAyah)) ayahIndexMap.set(cleanAyah, new Set());
        ayahIndexMap.get(cleanAyah).add(pNum);
      }
    }
  }

  function openOverflowPage(u, overrideMatnHtml = null, overrideGlossMap = null) {
    const np = u.is_preface ? openPrefacePage() : openBodyPage();
    np.isContPage = true;
    if (!u.is_preface) {
      if (overrideMatnHtml) {
        np.matnZone.innerHTML = overrideMatnHtml;
        if (overrideGlossMap) applyMatnGlossFootnotes(np, overrideGlossMap);
        recordAyahsOnPage(np.matnZone.innerHTML, np.pNum);
      } else {
        np.matnZone.innerHTML = '<div class="matn-cont-dots">............................................</div>';
      }
    }
    np.unitCountOnPage++;
    return np;
  }

  curPageObj = (data.units.length > 0 && data.units[0].is_preface) ? openPrefacePage() : openBodyPage();

  for (let ui = 0; ui < data.units.length; ui++) {
    if (ui % 8 === 0) await new Promise(r => setTimeout(r, 0));
    const u = data.units[ui];

    const secLabel = u.toc_fasl || u.toc_book || '';
    if (secLabel) {
      activeSectionTitle = secLabel.replace(/^\\[\\s*|\\s*\\]$/g, '').trim();
    }

    if (curPageObj.unitCountOnPage > 0) {
      curPageObj = u.is_preface ? openPrefacePage() : openBodyPage();
    } else if (secLabel) {
      setPageOddHeaderTitle(curPageObj, secLabel);
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

    if (!isEdited && u.lesson_note) {
      curPageObj.lessonNoteText = u.lesson_note;
    }

    let extraMatnChunks = [];
    let unitGlossMetaMap = null;
    let hasTrailingDots = false;

    if (u.is_preface) {
      curPageObj.sharhZone.insertAdjacentHTML('beforeend',
        (u.id === 'L01_U01' ? CHAPTER_BANNER_HTML : '') +
        '<div class="preface-h" id="unit-' + esc(u.id) + '">' + esc(u.toc_fasl || 'مُقَدِّمَةُ الْكِتَابِ') + '</div>'
      );
      renderPageFootnotes(curPageObj);
      curPageObj.unitCountOnPage++;
    } else if (u.matn_lines.length === 1 && u.matn_lines[0].trim() === '............................................') {
      let hc = '';
      let ancP = false;
      if (u.toc_fasl) {
        hc += '<div class="matn-bracket-title" id="unit-' + esc(u.id) + '">' + esc(u.toc_fasl) + '</div>';
        ancP = true;
      }
      hc += '<div class="matn-cont-dots"' + (ancP ? '' : ' id="unit-' + esc(u.id) + '"') + '>............................................</div>';
      curPageObj.matnZone.innerHTML = hc;
      renderPageFootnotes(curPageObj);
      curPageObj.unitCountOnPage++;
    } else {
      const mPrep = prepareUnitMatnData(u);
      const paraHtmls = mPrep.paraHtmls;
      const glossMetaMap = mPrep.glossMetaMap;
      const hasLeadingDots = mPrep.hasLeadingDots;
      hasTrailingDots = mPrep.hasTrailingDots;
      unitGlossMetaMap = glossMetaMap;
      const hasSharh = (u.sharh_paras_html && u.sharh_paras_html.length > 0);
      const maxMatnPx = hasSharh ? Math.round(curPageObj.bodyFrame.clientHeight * 0.64) : curPageObj.bodyFrame.clientHeight - 8;

      let headerPrefixHtml = '';
      let anchorPlaced = false;
      if (u.toc_book) {
        headerPrefixHtml += CHAPTER_BANNER_HTML;
        headerPrefixHtml += '<div class="matn-book-title" id="unit-' + esc(u.id) + '">' + esc(u.toc_book) + '</div>';
        anchorPlaced = true;
      }
      if (u.toc_fasl) {
        const anchorAttr = !anchorPlaced ? ' id="unit-' + esc(u.id) + '"' : '';
        headerPrefixHtml += '<div class="matn-bracket-title"' + anchorAttr + '>' + esc(u.toc_fasl) + '</div>';
        anchorPlaced = true;
      }
      if (hasLeadingDots) {
        headerPrefixHtml += '<div class="matn-cont-dots">............................................</div>';
      }

      const buildFullCandidate = () => {
        let h = headerPrefixHtml;
        for (let i = 0; i < paraHtmls.length; i++) {
          const anchorAttr = (!anchorPlaced && i === 0) ? ' id="unit-' + esc(u.id) + '"' : '';
          const plainM = paraHtmls[i].replace(/<[^>]+>/g, '').trim();
          const isBasmalah = /^بِسْمِ\\s+اللَّ?هِ\\s+الرَّحْم[َٰـ]*نِ\\s+الرَّحِيمِ$/.test(plainM);
          h += '<p class="' + (isBasmalah ? 'matn-basmalah' : 'matn-p') + '"' + anchorAttr + '>' + paraHtmls[i] + '</p>';
        }
        if (hasTrailingDots) h += '<div class="matn-cont-dots">............................................</div>';
        if (u.fasl_end) h += THREE_STARS_HTML;
        return h;
      };

      // Fast path: check if entire Matn fits without crowding Sharh/Footnotes
      curPageObj.matnZone.innerHTML = buildFullCandidate();
      applyMatnGlossFootnotes(curPageObj, glossMetaMap);
      if (curPageObj.bodyFrame.scrollHeight <= curPageObj.bodyFrame.clientHeight + 1 && (!hasSharh || curPageObj.sharhZone.clientHeight >= 110)) {
        recordAyahsOnPage(curPageObj.matnZone.innerHTML, curPageObj.pNum);
        curPageObj.unitCountOnPage++;
      } else {
        // Paginate Matn lines/atoms cleanly across pages!
        let mItems = paraHtmls.map((ph, idx) => {
          const plainM = ph.replace(/<[^>]+>/g, '').trim();
          const isBasmalah = /^بِسْمِ\\s+اللَّ?هِ\\s+الرَّحْم[َٰـ]*نِ\\s+الرَّحِيمِ$/.test(plainM);
          return {
            atoms: tokenizeHtml(ph),
            isBasmalah,
            isCont: false,
            anchorAttr: (!anchorPlaced && idx === 0) ? ' id="unit-' + esc(u.id) + '"' : '',
          };
        });

        let targetPage = curPageObj;
        let isFirstMatnPage = true;
        while (mItems.length > 0) {
          targetPage.matnZone.innerHTML = isFirstMatnPage ? headerPrefixHtml : '';
          const quotaPx = hasSharh ? Math.round(targetPage.bodyFrame.clientHeight * 0.58) : (targetPage.bodyFrame.clientHeight - 8);
          let fittedAny = false;
          while (mItems.length > 0) {
            const cur = mItems[0];
            const pEl = document.createElement('p');
            pEl.className = (cur.isBasmalah ? 'matn-basmalah' : 'matn-p') + (cur.isCont ? ' cont' : '');
            if (cur.anchorAttr) pEl.id = 'unit-' + u.id;
            pEl.innerHTML = joinAtoms(cur.atoms);
            targetPage.matnZone.appendChild(pEl);
            applyMatnGlossFootnotes(targetPage, glossMetaMap);

            if (matnFitsQuota(targetPage, quotaPx, hasSharh)) {
              mItems.shift();
              fittedAny = true;
            } else {
              // Binary search atoms within current paragraph
              let lo = 1, hi = cur.atoms.length - 1, best = 0;
              while (lo <= hi) {
                const mid = (lo + hi) >> 1;
                pEl.innerHTML = joinAtoms(cur.atoms.slice(0, mid));
                applyMatnGlossFootnotes(targetPage, glossMetaMap);
                if (matnFitsQuota(targetPage, quotaPx, hasSharh)) {
                  best = mid;
                  lo = mid + 1;
                } else {
                  hi = mid - 1;
                }
              }
              if (best < 4 && fittedAny) {
                targetPage.matnZone.removeChild(pEl);
                applyMatnGlossFootnotes(targetPage, glossMetaMap);
                break;
              }
              if (best <= 0) best = Math.min(20, cur.atoms.length);
              const splitRes = finalizeSplitPara(pEl, cur.atoms, best, !cur.isBasmalah);
              applyMatnGlossFootnotes(targetPage, glossMetaMap);
              cur.atoms = splitRes.tailAtoms;
              cur.isCont = true;
              cur.anchorAttr = '';
              if (cur.atoms.length === 0) mItems.shift();
              break;
            }
          }
          if (mItems.length === 0 && hasTrailingDots) {
            targetPage.matnZone.insertAdjacentHTML('beforeend', '<div class="matn-cont-dots">............................................</div>');
            if (!matnFitsQuota(targetPage, quotaPx + 24, hasSharh)) {
              targetPage.matnZone.lastElementChild.remove();
            }
          }
          if (mItems.length === 0 && u.fasl_end) {
            targetPage.matnZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
            if (!matnFitsQuota(targetPage, quotaPx + 24, hasSharh)) {
              targetPage.matnZone.lastElementChild.remove();
            }
          }
          if (isFirstMatnPage) {
            recordAyahsOnPage(targetPage.matnZone.innerHTML, targetPage.pNum);
            targetPage.unitCountOnPage++;
            isFirstMatnPage = false;
            if (mItems.length > 0) {
              // Accumulate remaining Matn chunks for continuation pages
              extraMatnChunks = mItems;
              break;
            }
          }
        }
      }
    }

    // Helper: fill a continuation page's matnZone from extraMatnChunks if any remain
    const populateNextMatnSliceOnPage = (np) => {
      if (!extraMatnChunks || extraMatnChunks.length === 0) return;
      const quotaPx = Math.round(np.bodyFrame.clientHeight * 0.56);
      np.matnZone.innerHTML = '';
      let fittedAny = false;
      while (extraMatnChunks.length > 0) {
        const cur = extraMatnChunks[0];
        const pEl = document.createElement('p');
        pEl.className = (cur.isBasmalah ? 'matn-basmalah' : 'matn-p') + (cur.isCont ? ' cont' : '');
        pEl.innerHTML = joinAtoms(cur.atoms);
        np.matnZone.appendChild(pEl);
        applyMatnGlossFootnotes(np, unitGlossMetaMap);
        if (matnFitsQuota(np, quotaPx, true)) {
          extraMatnChunks.shift();
          fittedAny = true;
        } else {
          let lo = 1, hi = cur.atoms.length - 1, best = 0;
          while (lo <= hi) {
            const mid = (lo + hi) >> 1;
            pEl.innerHTML = joinAtoms(cur.atoms.slice(0, mid));
            applyMatnGlossFootnotes(np, unitGlossMetaMap);
            if (matnFitsQuota(np, quotaPx, true)) {
              best = mid;
              lo = mid + 1;
            } else {
              hi = mid - 1;
            }
          }
          if (best < 4 && fittedAny) {
            np.matnZone.removeChild(pEl);
            applyMatnGlossFootnotes(np, unitGlossMetaMap);
            break;
          }
          if (best <= 0) best = Math.min(20, cur.atoms.length);
          const splitRes = finalizeSplitPara(pEl, cur.atoms, best, !cur.isBasmalah);
          applyMatnGlossFootnotes(np, unitGlossMetaMap);
          cur.atoms = splitRes.tailAtoms;
          cur.isCont = true;
          if (cur.atoms.length === 0) extraMatnChunks.shift();
          break;
        }
      }
      if (extraMatnChunks.length === 0 && hasTrailingDots) {
        np.matnZone.insertAdjacentHTML('beforeend', '<div class="matn-cont-dots">............................................</div>');
        if (np.bodyFrame.scrollHeight > np.bodyFrame.clientHeight || np.sharhZone.clientHeight < 75) {
          np.matnZone.lastElementChild.remove();
        }
      }
      if (extraMatnChunks.length === 0 && u.fasl_end) {
        np.matnZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
        if (np.bodyFrame.scrollHeight > np.bodyFrame.clientHeight || np.sharhZone.clientHeight < 75) {
          np.matnZone.lastElementChild.remove();
        }
      }
      recordAyahsOnPage(np.matnZone.innerHTML, np.pNum);
    };

    const advanceOverflowPage = () => {
      const np = u.is_preface ? openPrefacePage() : openBodyPage();
      np.isContPage = true;
      if (!u.is_preface) {
        if (extraMatnChunks && extraMatnChunks.length > 0) {
          populateNextMatnSliceOnPage(np);
        } else {
          np.matnZone.innerHTML = '<div class="matn-cont-dots">............................................</div>';
        }
      }
      np.unitCountOnPage++;
      return np;
    };

    for (let pi = 0; pi < u.sharh_paras_html.length; pi++) {
      let atoms = tokenizeHtml(u.sharh_paras_html[pi]);
      const plainP = u.sharh_paras_html[pi].replace(/<[^>]+>/g, '').trim();
      const isPoemBayt = /^[^<>\\n]{8,65}\\s+\\.\\.\\.\\s+[^<>\\n]{8,65}$/.test(plainP);
      let isCont = false;
      const isLastParaOfUnit = (pi === u.sharh_paras_html.length - 1);

      while (atoms.length > 0) {
        const pEl = document.createElement('p');
        pEl.className = 'sharh-p' + (isPoemBayt ? ' poem-bayt' : '') + (isCont ? ' cont' : '');
        pEl.innerHTML = joinAtoms(atoms);
        curPageObj.sharhZone.appendChild(pEl);

        if (fitsPage(curPageObj)) {
          recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
          atoms = [];
        } else {
          // Micro-fit pass: prevent tiny <= 34-word orphan overflow on the last paragraph of a unit
          if (isLastParaOfUnit && atoms.length <= 34 && !curPageObj.sharhZone.classList.contains('tight-fit')) {
            curPageObj.sharhZone.classList.add('tight-fit');
            if (fitsPage(curPageObj)) {
              recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
              atoms = [];
              continue;
            }
            curPageObj.sharhZone.classList.remove('tight-fit');
          }

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
          if (best <= 0 || (priorParaCount > 0 && best < 3) || (isPoemBayt && best < atoms.length)) {
            if (!curPageObj.isContPage || priorParaCount > 0) {
              curPageObj.sharhZone.removeChild(pEl);
              curPageObj = advanceOverflowPage();
              continue;
            } else {
              best = Math.min(12, atoms.length);
            }
          }

          const preliminaryTailLen = atoms.length - best;

          // If splitting would leave a <= 34 word tail on the last paragraph, try tight-fit!
          if (isLastParaOfUnit && preliminaryTailLen <= 34 && !curPageObj.sharhZone.classList.contains('tight-fit')) {
            pEl.innerHTML = joinAtoms(atoms);
            curPageObj.sharhZone.classList.add('tight-fit');
            if (fitsPage(curPageObj)) {
              recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);
              atoms = [];
              continue;
            }
            curPageObj.sharhZone.classList.remove('tight-fit');
          }

          const splitRes = finalizeSplitPara(pEl, atoms, best, !isPoemBayt);
          recordAyahsOnPage(pEl.innerHTML, curPageObj.pNum);

          atoms = splitRes.tailAtoms;
          isCont = true;

          if (atoms.length > 0) {
            curPageObj = advanceOverflowPage();
          }
        }
      }
    }

    // Flush any remaining extraMatnChunks if Sharh finished before Matn
    while (extraMatnChunks && extraMatnChunks.length > 0) {
      curPageObj = advanceOverflowPage();
    }

    if (u.fasl_end) {
      curPageObj.sharhZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
      if (!fitsPage(curPageObj)) {
        const tailEl = curPageObj.sharhZone.lastElementChild;
        if (tailEl) tailEl.style.margin = '1pt 0';
        if (!fitsPage(curPageObj)) {
          curPageObj.sharhZone.removeChild(tailEl);
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
      CHAPTER_BANNER_HTML +
      '<div class="toc-page-title">فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ</div>' +
      '<div class="index-col-head"><span>الآيَةُ الْكَرِيمَةُ</span><span>الصَّفْحَةُ</span></div>' +
      '<div id="ayah-list-box"></div>';
    let ayBox = ayPage.bodyFrame.querySelector('#ayah-list-box');

    for (const [ayahTxt, pgSet] of ayahList) {
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
      (tocPgCount === 1 ? CHAPTER_BANNER_HTML : '') +
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
    if (fIdx >= allTocEntries.length && (fIdx - startFIdx) >= 4) {
      // Balance final TOC page symmetrically across both columns!
      const rem = allTocEntries.slice(startFIdx);
      const half = Math.ceil(rem.length / 2);
      colRight.innerHTML = '';
      colLeft.innerHTML = '';
      for (let i = 0; i < rem.length; i++) {
        (i < half ? colRight : colLeft).appendChild(makeTocEl(rem[i]));
      }
    } else {
      while (fIdx < allTocEntries.length) {
        const el = makeTocEl(allTocEntries[fIdx]);
        colLeft.appendChild(el);
        if (colOverflows(colLeft) && colLeft.children.length > 1) {
          colLeft.removeChild(el);
          break;
        }
        fIdx++;
      }
    }
    if (fIdx === startFIdx) break;
  }

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
window.__BASMALAH_URL = ${JSON.stringify('file://' + path.join(__ENG, EDITION === 'two-color' ? 'basmalah_crimson.png' : 'basmalah.png'))};
window.__BANNER_URL = ${JSON.stringify('file://' + path.join(__ENG, EDITION === 'two-color' ? 'banner_crimson.png' : 'banner_classic.png'))};
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
