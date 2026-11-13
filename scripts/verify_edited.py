#!/usr/bin/env python3
"""Validate edited lessons against clean_lessons structure, Quranic ayahs, colloquialisms, and fidelity."""
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLLOQUIAL_TOKENS = [
    r'(?<!\w)إيه(?!\w)',
    r'(?<!\w)كده(?!\w)',
    r'(?<!\w)عشان(?!\w)',
    r'(?<!\w)علشان(?!\w)',
    r'(?<!\w)بتاع\w*',
    r'(?<!\w)بتوع(?!\w)',
    r'(?<!\w)برضه(?!\w)',
    r'(?<!\w)برضو(?!\w)',
    r'(?<!\w)أهو(?!\w)',
    r'(?<!\w)لسه(?!\w)',
    r'(?<!\w)شوية(?!\w)',
    r'(?<!\w)خلينا(?!\w)',
    r'(?<!\w)آدي(?!\w)',
    r'(?<!\w)دول(?!\w)',
    r'(?<!\w)ده(?!\w)',
    r'(?<!\w)دي(?!\w)',
    r'(?<!\w)مش(?!\w)',
    r'(?<!\w)مفيش(?!\w)',
    r'(?<!\w)ما فيش(?!\w)',
    r'(?<!\w)اللي(?!\w)',
    r'(?<!\w)المية(?!\w)',
    r'(?<!\w)مية(?!\w)',
    r'(?<!\w)كتير(?!\w)',
    r'(?<!\w)ما ينفعش(?!\w)',
    r'(?<!\w)ينفعش(?!\w)',
    r'(?<!\w)ما بتفرقش(?!\w)',
    r'(?<!\w)بتفرقش(?!\w)',
    r'(?<!\w)هقول\w*',
    r'(?<!\w)هنقول\w*',
    r'(?<!\w)هعمل\w*',
    r'(?<!\w)حاجات(?!\w)',
    r'(?<!\w)بص(?!\w)',
    r'(?<!\w)شوف(?!\w)',
    r'(?<!\w)خالص(?!\w)',
    r'(?<!\w)طب(?!\w)',
    r'(?<!\w)زي(?!\w)',
    r'(?:^|\.\s+)طيب[،,]',
    r'الصوت انقطع',
    r'شيخ مصطفى',
    r'أستاذ نور',
    r'أستاذة سمية',
    r'مرحباً بكم أيها الإخوة',
    r'اللقاء القادم',
    r'المرة القادمة',
    r'الدرس القادم',
    r'هستأذنكم',
    r'سبحانك اللهم ربنا وبحمدك',
    r'نكتفي بهذا',
]
COLLOQUIAL_RX = re.compile('|'.join(COLLOQUIAL_TOKENS))
LATIN_RX = re.compile(r'[A-Za-z]')


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
    cu_cmp = cu[:7] if lnum == 1 else cu

    if len(cu_cmp) != len(eu):
        return False, f"L{lnum:02d}: unit count mismatch {len(eu)} != {len(cu_cmp)}"

    errors = []
    tot_c_words = 0
    tot_e_words = 0
    for idx, ((cm, cs), (em, es)) in enumerate(zip(cu_cmp, eu), 1):
        for k in ['TOC_BOOK', 'TOC_FASL', 'HEADING', 'MATN', 'FASL_END']:
            if cm[k] != em[k]:
                errors.append(f"U{idx:02d} {k} mismatch")
        if not es:
            errors.append(f"U{idx:02d} empty SHARH")
        c_ayahs = re.findall(r'﴿[^﴾]+﴾', cs)
        e_ayahs = re.findall(r'﴿[^﴾]+﴾', es)
        if c_ayahs != e_ayahs:
            errors.append(f"U{idx:02d} Ayah mismatch: clean={c_ayahs} vs edited={e_ayahs}")
        hits = COLLOQUIAL_RX.findall(es)
        if hits:
            errors.append(f"U{idx:02d} remaining colloquial/meta tokens: {hits[:8]}")
        if LATIN_RX.search(es):
            errors.append(f"U{idx:02d} Latin chars found")
        for forb in ['الدكتور', 'د. أحمد', 'دار ابن حزم']:
            if forb in es:
                errors.append(f"U{idx:02d} forbidden term: {forb}")
        tot_c_words += len(cs.split())
        tot_e_words += len(es.split())

    ratio = tot_e_words / max(1, tot_c_words)
    if ratio < 0.65:
        errors.append(f"Word retention too low ({ratio:.2%}: {tot_e_words}/{tot_c_words}) - possible over-summarization")
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
