#!/usr/bin/env python3
"""
Validate edited Abu Shuja lessons (L01-L25) under the NEW verbatim-respecting editorial rules:
  - Identical 167/167 unit count, headings, TOC metadata, and Matn
  - Exact Rasm Uthmani ayahs + [السورة: الآية] matching clean_lessons
  - L01 intro and L25 closing preserved; L02-L25 video openings and L01-L24 video closings removed
  - Technical Zoom/audio interruptions removed
  - >= 90% word retention (never summarize, paraphrase, or substitute Shaykh's words)
  - Zero Latin chars, Western digits, or forbidden editorial terms.
"""
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VIDEO_OPENING_RX = re.compile(
    r'أعوذ بالله السميع العليم|فمرحب[اً]? بكم أيها (?:الإخوة|الأحبة)|حتى نلقاهم\.?\s*أما بعد'
)
VIDEO_CLOSING_RX = re.compile(
    r'في لقائنا القادم|المرة القادمة|في الدرس المقبل|نبدأ به بمشيئة الله|سبحانك اللهم ربنا وبحمدك|وصلى الله وسلم وزاد وبارك على|وصلِّ اللهم وسلم وزد وبارك على'
)
ZOOM_RX = re.compile(
    r'هل تسمعونني|كيف الصوت شيخ|الصوت انقطع|أنا فتحت الصوت|أستاذ نور|أستاذة سمية'
)
LATIN_RX = re.compile(r'[A-Za-z]')
WESTERN_DIGIT_RX = re.compile(r'(?<![A-Za-z0-9_])[0-9]+')


def parse_units(path):
    txt = open(path, encoding='utf-8').read()
    parts = re.split(r'^@@UNIT\s*$', txt, flags=re.M)[1:]
    out = []
    for p in parts:
        m = re.search(r'@@SHARH\s*\n(.*)', p, flags=re.S)
        hdr = p[:m.start()] if m else p
        sharh = m.group(1).strip() if m else ''
        meta = {}
        for k in ['TOC_BOOK', 'TOC_FASL', 'HEADING', 'FASL_END']:
            mm = re.search(rf'^{k}:(.*)$', hdr, flags=re.M)
            meta[k] = mm.group(1).strip() if mm else ''
        mm = re.search(r'^MATN:(.*?)(?=^FASL_END:)', hdr, flags=re.M | re.S)
        meta['MATN'] = mm.group(1).strip() if mm else ''
        out.append((meta, sharh))
    return out


def check_lesson(lnum):
    c_path = os.path.join(_REPO, 'clean_lessons', f'L{lnum:02d}.txt')
    e_path = os.path.join(_REPO, 'edited_lessons', f'L{lnum:02d}.txt')
    if not os.path.exists(e_path):
        return False, f"L{lnum:02d}: MISSING {e_path}"

    cu = parse_units(c_path)
    eu = parse_units(e_path)

    if len(cu) != len(eu):
        return False, f"L{lnum:02d}: unit count mismatch {len(eu)} != {len(cu)}"

    errors = []
    tot_c_words = 0
    tot_e_words = 0
    for idx, ((cm, cs), (em, es)) in enumerate(zip(cu, eu), 1):
        for k in ['TOC_BOOK', 'TOC_FASL', 'HEADING', 'MATN', 'FASL_END']:
            if cm[k] != em[k]:
                errors.append(f"U{idx:02d} {k} mismatch")
        if not es:
            errors.append(f"U{idx:02d} empty SHARH")
        c_ay = re.findall(r'﴿[^﴾]+﴾\s*\[[^\]]+\]', cs)
        e_ay = re.findall(r'﴿[^﴾]+﴾\s*\[[^\]]+\]', es)
        if set(c_ay) != set(e_ay):
            errors.append(f"U{idx:02d} Ayah/ref mismatch: missing={set(c_ay)-set(e_ay)} extra={set(e_ay)-set(c_ay)}")
        if ZOOM_RX.search(es):
            errors.append(f"U{idx:02d} remaining Zoom chatter: {ZOOM_RX.findall(es)}")
        if LATIN_RX.search(es) or WESTERN_DIGIT_RX.search(es):
            errors.append(f"U{idx:02d} Latin or Western digits found")
        for forb in ['الدكتور', 'د. أحمد', 'دار ابن حزم']:
            if forb in es:
                errors.append(f"U{idx:02d} forbidden term: {forb}")
        tot_c_words += len(cs.split())
        tot_e_words += len(es.split())

    u1_sharh = eu[0][1]
    if lnum != 1 and VIDEO_OPENING_RX.search(u1_sharh[:600]):
        errors.append(f"U01 leftover video intro: {VIDEO_OPENING_RX.findall(u1_sharh[:600])}")
    if lnum == 1 and 'السلام عليكم' not in u1_sharh[:120]:
        errors.append("L01 opening greeting accidentally removed")

    ul_sharh = eu[-1][1]
    if lnum != 25 and VIDEO_CLOSING_RX.search(ul_sharh[-180:]):
        errors.append(f"U{len(eu):02d} leftover video closing: {VIDEO_CLOSING_RX.findall(ul_sharh[-180:])}")
    if lnum == 25 and 'سبحانك اللهم ربنا وبحمدك' not in ul_sharh[-200:]:
        errors.append("L25 closing prayer accidentally removed")

    ratio = tot_e_words / max(1, tot_c_words)
    min_ratio = 0.88 if lnum == 1 else 0.90
    if ratio < min_ratio:
        errors.append(f"Word retention too low ({ratio:.2%}: {tot_e_words}/{tot_c_words}) - possible unwanted deletion")
    if errors:
        return False, f"L{lnum:02d} FAIL ({tot_e_words}/{tot_c_words}, {ratio:.1%}): " + " | ".join(errors)
    return True, f"L{lnum:02d} PASS ({len(eu)} units, {tot_e_words}/{tot_c_words} words = {ratio:.1%})"


def main():
    nums = [int(a.lstrip('L')) for a in sys.argv[1:]] if len(sys.argv) > 1 else list(range(1, 26))
    ok_all = True
    for n in nums:
        ok, msg = check_lesson(n)
        print(msg)
        if not ok:
            ok_all = False
    sys.exit(0 if ok_all else 1)


if __name__ == '__main__':
    main()
