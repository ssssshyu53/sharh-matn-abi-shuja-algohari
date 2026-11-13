import fs from 'node:fs';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';

// Ensure Node fetch/WebSocket to 127.0.0.1 does not route through HTTP_PROXY
delete process.env.HTTP_PROXY;
delete process.env.HTTPS_PROXY;
delete process.env.http_proxy;
delete process.env.https_proxy;
process.env.NO_PROXY = '127.0.0.1,localhost';

const DATA_PATH = process.argv[2] || '/tmp/book_data.json';
const OUT_PDF = process.argv[3] || '/tmp/book_preview.pdf';
const OUT_HTML = process.argv[4] || '/tmp/book_paginated.html';
const PORT = 9241;

const TEMPLATE_HTML = fs.readFileSync('/home/antigravity/book_engine/template_book.html', 'utf8');
const BOOK_DATA = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function launchChrome() {
  const userDataDir = `/tmp/chrome_book_prof_${Date.now()}`;
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

// Client-side pagination code injected into Chromium DOM
const PAGINATE_FN_SRC = `
window.renderFullBook = async function(data) {
  await document.fonts.ready;
  const root = document.getElementById('book-root');
  root.innerHTML = '';

  const EDIGITS = '٠١٢٣٤٥٦٧٨٩';
  const toE = (n) => String(n).replace(/[0-9]/g, d => EDIGITS[+d]);
  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

  const STAR_SVG = '<svg class="star-svg" viewBox="0 0 100 100"><g transform="translate(50,50)"><circle r="9" fill="#111"/>' +
    [0,45,90,135,180,225,270,315].map(a => '<path d="M0,-12 C6,-28 8,-44 0,-48 C-8,-44 -6,-28 0,-12 Z" fill="#111" transform="rotate('+a+')"/>').join('') +
    '</g></svg>';
  const THREE_STARS_HTML = '<div class="stars-row">' + STAR_SVG + STAR_SVG + STAR_SVG + '</div>';

  // Helper: parse HTML paragraph cleanly into token atoms while merging adjacent wrappers cleanly on join
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
    // In Dar Ibn Hazm RTL book: Even pages (2, 4, 24..) have page # on TOP-RIGHT; Odd pages (5, 25..) on TOP-LEFT!
    const isEven = (pNum % 2 === 0);
    return '<div class="running-header">' +
      '<span class="rh-side rh-right">' + (isEven ? eNum : '') + '</span>' +
      '<span class="rh-center">' + esc(centerText) + '</span>' +
      '<span class="rh-side rh-left">' + (!isEven ? eNum : '') + '</span>' +
    '</div>';
  }

  function getHeaderTitle(pNum, isIntroOrBack) {
    if (pNum % 2 === 0) return '« تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ »';
    return 'لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ';
  }

  function createPage({ framed = false, skipHeader = false, centerTitle = null } = {}) {
    pageCounter++;
    const pNum = pageCounter;
    const el = document.createElement('div');
    el.className = 'page' + (framed ? ' framed-page' : '');
    el.id = 'pg-' + pNum;
    if (!skipHeader) {
      el.innerHTML = makeHeaderHtml(pNum, centerTitle || getHeaderTitle(pNum));
    }
    const bodyFrame = document.createElement('div');
    bodyFrame.className = 'body-frame';
    el.appendChild(bodyFrame);
    root.appendChild(el);
    return { el, bodyFrame, pNum };
  }

  // ==================== 1. FRONT MATTER ====================
  // Page 1: Title Page
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner">' +
        '<div style="width:100%;">' +
          '<div style="font-size: 24pt; font-weight: 700; line-height: 1.85; margin-top: 3mm;">' +
            'تَيْسِيرُ الانْتِفَاعِ<br>' +
            '<span style="font-size:17pt; font-weight:400;">بِشَرْحِ</span><br>' +
            '<span style="font-size:25pt;">مُخْتَصَرِ أَبِي شُجَاعٍ</span>' +
          '</div>' +
          '<div style="font-size: 14pt; margin: 10pt 0 4pt 0;">( الْمُسَمَّى بِـ « غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ » )</div>' +
          '<div style="font-size: 17pt; font-weight: 700; line-height: 1.85; margin-top: 8pt;">' +
            'التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِدُرُوسِ شَرْحِ مَتْنِ أَبِي شُجَاعٍ' +
          '</div>' +
        '</div>' +
        '<div style="font-size: 12pt; line-height: 1.95; width:92%;">' +
          '<div style="font-size: 13.5pt;">لِفَضِيلَةِ الشَّيْخِ <strong>أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ</strong></div>' +
          '<div style="font-size: 11pt;">( حَفِظَهُ اللهُ تَعَالَى وَنَفَعَ بِعِلْمِهِ )</div>' +
          '<div style="font-size: 11.2pt; margin-top: 10pt; border-top: 0.5pt solid #555; padding-top: 8pt;">' +
            'وَالْمَتْنُ لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ (٤٣٣ – ٥٩٣ هـ)' +
          '</div>' +
        '</div>' +
        '<div style="width:100%; display:flex; justify-content:space-between; font-size:10.8pt; font-weight:700; padding:0 4mm;">' +
          '<span>كِتَابُ الطَّهَارَةِ وَكِتَابُ الصَّلاَةِ</span>' +
          '<span>٢٥ لِقَاءً صَوْتِيًّا كَامِلاً</span>' +
        '</div>' +
      '</div></div>';
  }

  // Page 2: Colophon & Methodology Notice
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner">' +
        '<div style="font-size: 15.5pt; font-weight: 700; line-height: 2; margin-top: 10mm;">' +
          'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ<br>' +
          '<span style="font-size: 12pt; font-weight: 400;">تَفْرِيغٌ حَرْفِيٌّ كَامِلٌ مُرَاجَعٌ لِدُرُوسِ السِّلْسِلَةِ الْفِقْهِيَّةِ الشَّافِعِيَّةِ</span><br>' +
          '<span style="font-size: 11.5pt;">( اللِّقَاءَاتُ : ١ – ٢٥ )</span>' +
        '</div>' +
        '<div class="disclaimer-box">' +
          'أُعِدَّ هَذَا الْكِتَابُ بِإِثْبَاتِ كَلاَمِ الشَّيْخِ الشَّارِحِ كَامِلاً كَمَا أُلْقِيَ دُونَ حَذْفٍ أَوْ اخْتِصَارٍ ،<br>' +
          'مَعَ إِثْبَاتِ مَتْنِ أَبِي شُجَاعٍ مَضْبُوطاً بِالشَّكْلِ أَعْلَى الصَّفْحَةِ مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ أَسْفَلَهُ' +
        '</div>' +
        '<div style="font-size: 10.5pt; line-height: 1.9; width: 92%;">' +
          '<div><strong>رُمُوزُ الضَّبْطِ وَالتَّنْسِيقِ فِي هَذِهِ النُّسْخَةِ :</strong></div>' +
          '<div>الْمَتْنُ بِالْخَطِّ الْكَبِيرِ أَعْلَى الصَّفْحَةِ مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ أَسْفَلَهُ</div>' +
          '<div><strong>الْخَطُّ الْعَرِيضُ دَاخِلَ الشَّرْحِ</strong> يُمَيِّزُ أَلْفَاظَ الْمَتْنِ الَّتِي يَسْتَشْهِدُ بِهَا الشَّارِحُ</div>' +
          '<div>﴿ ... ﴾ لِلآيَاتِ الْقُرْآنِيَّةِ &nbsp;•&nbsp; « ... » لِلأَحَادِيثِ النَّبَوِيَّةِ &nbsp;•&nbsp; [ ... ] لِعَنَاوِينِ الْفُصُولِ</div>' +
        '</div>' +
        '<div style="border-top: 0.7pt solid #111; padding-top: 4pt; width: 85%; font-size: 10.5pt;">' +
          'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ' +
        '</div>' +
      '</div></div>';
  }

  // Page 3: Basmalah Opening Plate
  {
    const { bodyFrame } = createPage({ framed: true, skipHeader: true });
    bodyFrame.innerHTML =
      '<div class="frame-outer"><div class="frame-inner" style="justify-content:center;">' +
        '<div style="font-family:AmiriQuranFont,AmiriBook,serif; font-size:26pt; line-height:2; letter-spacing:0.3pt;">' +
          'بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ' +
        '</div>' +
        '<div style="margin-top:8pt;">' + THREE_STARS_HTML + '</div>' +
      '</div></div>';
  }

  // ==================== 2. CORE SPLIT-PAGE BODY LAYOUT ====================
  const tocEntries = [];
  const lessonStartPage = {};
  const ayahIndexMap = new Map(); // ayahText -> Set(pageNumbers)

  let curPageObj = null;
  let footnoteNum = 0;

  function openPrefacePage(centerOverride = null) {
    const p = createPage({ centerTitle: centerOverride });
    p.bodyFrame.innerHTML =
      '<div class="sharh-zone"></div>' +
      '<div class="footnote-area" style="display:none;"><div class="footnote-rule"></div><div class="footnote-text"></div></div>';
    p.matnZone = null;
    p.sharhZone = p.bodyFrame.querySelector('.sharh-zone');
    p.footnoteArea = p.bodyFrame.querySelector('.footnote-area');
    p.footnoteText = p.bodyFrame.querySelector('.footnote-text');
    p.hasFootnote = false;
    p.unitCountOnPage = 0;
    p.endsWithStars = false;
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
    p.footnoteArea = p.bodyFrame.querySelector('.footnote-area');
    p.footnoteText = p.bodyFrame.querySelector('.footnote-text');
    p.hasFootnote = false;
    p.unitCountOnPage = 0;
    p.endsWithStars = false;
    p.isContPage = false;
    p.isPrefacePage = false;
    return p;
  }

  function fitsPage(p) {
    return (
      p.sharhZone.clientHeight >= 24 &&
      p.sharhZone.scrollHeight <= p.sharhZone.clientHeight + 1 &&
      p.bodyFrame.scrollHeight <= p.bodyFrame.clientHeight + 1
    );
  }

  function buildMatnHtmlForUnit(u, isContinuationPage = false) {
    if (isContinuationPage) {
      return '<div class="matn-cont-dots">............................................</div>';
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
    for (let i = 0; i < u.matn_lines.length; i++) {
      const line = u.matn_lines[i];
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

  function addFootnoteToPage(p, noteText) {
    if (!noteText) return;
    footnoteNum++;
    p.footnoteArea.style.display = 'block';
    const prev = p.footnoteText.innerHTML;
    const line = '<div>(' + toE(footnoteNum) + ') ' + esc(noteText) + '</div>';
    p.footnoteText.innerHTML = prev + line;
    p.hasFootnote = true;
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
      np.matnZone.innerHTML = buildMatnHtmlForUnit(u, true);
    }
    np.unitCountOnPage++;
    return np;
  }

  curPageObj = (data.units.length > 0 && data.units[0].is_preface) ? openPrefacePage() : openBodyPage();

  for (let ui = 0; ui < data.units.length; ui++) {
    if (ui % 8 === 0) await new Promise(r => setTimeout(r, 0));
    const u = data.units[ui];
    const matnHtml = u.is_preface ? '' : buildMatnHtmlForUnit(u, false);

    // Start fresh page on book transitions or preface <-> Matn transitions
    if (curPageObj.unitCountOnPage > 0 && (u.toc_book || Boolean(u.is_preface) !== Boolean(curPageObj.isPrefacePage))) {
      curPageObj = u.is_preface ? openPrefacePage() : openBodyPage();
    }

    // Decide whether U can stack on curPageObj OR needs a fresh page
    if (curPageObj.unitCountOnPage > 0) {
      const savedMatn = curPageObj.matnZone ? curPageObj.matnZone.innerHTML : '';
      const savedSharh = curPageObj.sharhZone.innerHTML;
      const savedFnDisplay = curPageObj.footnoteArea.style.display;
      const savedFnHtml = curPageObj.footnoteText.innerHTML;
      const savedFnNum = footnoteNum;

      if (!curPageObj.endsWithStars) {
        if (curPageObj.matnZone) curPageObj.matnZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
        curPageObj.sharhZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
      }
      if (curPageObj.matnZone && matnHtml) {
        curPageObj.matnZone.insertAdjacentHTML('beforeend', matnHtml);
      }
      if (u.lesson_note) addFootnoteToPage(curPageObj, u.lesson_note);

      const firstAtoms = u.sharh_paras_html.length ? tokenizeHtml(u.sharh_paras_html[0]) : [];
      const reqCount = Math.min(28, firstAtoms.length);
      const minSnippet = firstAtoms.length > reqCount ? joinAtoms(firstAtoms.slice(0, reqCount)) : (u.sharh_paras_html[0] || '');
      const testP = document.createElement('p');
      testP.className = 'sharh-p';
      testP.innerHTML = minSnippet;
      curPageObj.sharhZone.appendChild(testP);

      const canStack = fitsPage(curPageObj);

      // Revert tentative DOM
      if (curPageObj.matnZone) curPageObj.matnZone.innerHTML = savedMatn;
      curPageObj.sharhZone.innerHTML = savedSharh;
      curPageObj.footnoteArea.style.display = savedFnDisplay;
      curPageObj.footnoteText.innerHTML = savedFnHtml;
      footnoteNum = savedFnNum;

      if (!canStack) {
        curPageObj = u.is_preface ? openPrefacePage() : openBodyPage();
      } else if (!curPageObj.endsWithStars) {
        if (curPageObj.matnZone) curPageObj.matnZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
        curPageObj.sharhZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
      }
    }

    // Record TOC & lesson start page
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
      curPageObj.matnZone.insertAdjacentHTML('beforeend', matnHtml);
    }
    if (u.lesson_note) {
      addFootnoteToPage(curPageObj, u.lesson_note);
    }
    curPageObj.unitCountOnPage++;
    curPageObj.endsWithStars = false;

    // Render all paragraphs of U's Sharh across as many pages as needed
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
          // Binary search for max fitting prefix inside atoms
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
          if (best <= 0 || (priorParaCount > 0 && best < 14)) {
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

    // Add closing 3 floral stars after U's Sharh if fasl_end — never let stars overflow!
    if (u.fasl_end) {
      curPageObj.sharhZone.insertAdjacentHTML('beforeend', THREE_STARS_HTML);
      if (!fitsPage(curPageObj)) {
        const starsEl = curPageObj.sharhZone.lastElementChild;
        if (starsEl) starsEl.style.margin = '1pt 0';
        if (!fitsPage(curPageObj)) {
          curPageObj.sharhZone.removeChild(starsEl);
          curPageObj.endsWithStars = false;
        } else {
          curPageObj.endsWithStars = true;
        }
      } else {
        curPageObj.endsWithStars = true;
      }
    }
  }

  // ==================== 3. BACK MATTER INDEXES ====================
  // 3A. فهرس الآيات القرآنية
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
      if (ayPage.bodyFrame.scrollHeight > ayPage.bodyFrame.clientHeight + 1 && ayBox.children.length > 1) {
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

  // 3B. الفهرس العام Two-Column General Index
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
    const maxColH = pObj.bodyFrame.clientHeight - 44;

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
        const nbTitle = esc(e.title).replace(/^\[\s+/, '[\u00A0').replace(/\s+\]$/, '\u00A0]');
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
      if (colRight.scrollHeight > maxColH && colRight.children.length > 1) {
        colRight.removeChild(el);
        break;
      }
      fIdx++;
    }
    while (fIdx < allTocEntries.length) {
      const el = makeTocEl(allTocEntries[fIdx]);
      colLeft.appendChild(el);
      if (colLeft.scrollHeight > maxColH && colLeft.children.length > 1) {
        colLeft.removeChild(el);
        break;
      }
      fIdx++;
    }
    if (fIdx === startFIdx) break;
  }

  return { totalPages: pageCounter, tocCount: tocEntries.length, ayahCount: ayahIndexMap.size };
};
`;

async function main() {
  console.log('1. Preparing self-executing pagination HTML...');
  const runnerScript = `<script>
window.__BOOK_DATA = ${JSON.stringify(BOOK_DATA)};
${PAGINATE_FN_SRC}
window.__BOOK_RESULT = null;
window.__BOOK_ERROR = null;
window.addEventListener('load', () => {
  window.renderFullBook(window.__BOOK_DATA)
    .then(r => { window.__BOOK_RESULT = r; })
    .catch(e => { window.__BOOK_ERROR = String(e && e.stack || e); });
});
</script>`;
  const tmpTemplatePath = '/tmp/book_template_run.html';
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
    for (let i = 0; i < 120; i++) {
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

    // Export standalone paginated HTML (strip runner script first)
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

    // Print PDF viaPage.printToPDF with transferMode: ReturnAsStream so large PDFs never choke WebSocket frames
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
        chunks.push( readRes.base64Encoded ? Buffer.from(readRes.data, 'base64') : Buffer.from(readRes.data) );
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
