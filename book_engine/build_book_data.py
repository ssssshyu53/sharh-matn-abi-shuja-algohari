#!/usr/bin/env python3
import os
import sys
import glob
import re
import json
import html

EASTERN_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def to_eastern(n) -> str:
    return str(n).translate(EASTERN_DIGITS)


def format_sharh_inline_html(text: str) -> str:
    esc = html.escape(text)
    # Bold **...** (handle across inline spans safely)
    esc = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc, flags=re.S)
    # Quranic Ayahs ﴿...﴾ + optional [السورة: الآية] -> styled with AmiriQuran & smaller ref badge
    esc = re.sub(
        r'(﴿[^﴾]+﴾)(\s*\[[^\]:]+:\s*[٠-٩\-]+\])?',
        lambda m: f'<span class="ayah">{m.group(1)}</span>'
        + (f'\u00A0<span class="ayah-ref">{re.sub(chr(92) + "s+", chr(160), m.group(2).strip())}</span>' if m.group(2) else ''),
        esc,
    )
    return esc


def extract_ayahs(text: str):
    return re.findall(r'﴿([^﴾]+)﴾', text)


def parse_clean_file(path: str, lesson_num: int):
    content = open(path, encoding='utf-8').read()
    parts = re.split(r'^@@UNIT\s*$', content, flags=re.M)
    units = []
    for u_idx, part in enumerate(parts[1:], 1):
        m = re.search(r'@@SHARH\s*\n(.*)', part, flags=re.S)
        if not m:
            raise ValueError(f"Missing @@SHARH in {path} unit {u_idx}")
        header = part[:m.start()]
        sharh_raw = m.group(1).strip()

        meta = {
            'toc_book': '',
            'toc_fasl': '',
            'lesson_note': '',
            'heading': '',
            'sharh_header': '',
            'matn': [],
            'fasl_end': False,
        }
        cur = None
        for line in header.splitlines():
            if line.startswith('TOC_BOOK:'):
                meta['toc_book'] = line[len('TOC_BOOK:'):].strip()
                cur = 'TB'
            elif line.startswith('TOC_FASL:'):
                meta['toc_fasl'] = line[len('TOC_FASL:'):].strip()
                cur = 'TF'
            elif line.startswith('LESSON_NOTE:'):
                meta['lesson_note'] = line[len('LESSON_NOTE:'):].strip()
                cur = 'LN'
            elif line.startswith('HEADING:'):
                meta['heading'] = line[len('HEADING:'):].strip()
                cur = 'H'
            elif line.startswith('SHARH_HEADER:'):
                meta['sharh_header'] = line[len('SHARH_HEADER:'):].strip()
                cur = 'SH'
            elif line.startswith('MATN:'):
                meta['matn'].append(line[len('MATN:'):].strip())
                cur = 'M'
            elif line.startswith('FASL_END:'):
                val = line[len('FASL_END:'):].strip().lower()
                meta['fasl_end'] = val in ('yes', 'true', '1', 'نعم')
                cur = 'FE'
            elif cur == 'M' and line.strip():
                meta['matn'].append(line.strip())

        matn_raw_lines = [l for l in meta['matn'] if l]
        if meta['toc_book'] and matn_raw_lines and matn_raw_lines[0].strip().rstrip(':') == meta['toc_book'].strip().rstrip(':'):
            matn_raw_lines = matn_raw_lines[1:]
        matn_text = '\n'.join(matn_raw_lines).strip()
        is_preface = (len(matn_raw_lines) == 0)

        paras_raw = [p.strip() for p in re.split(r'\n\s*\n', sharh_raw) if p.strip()]
        paras_html = [format_sharh_inline_html(re.sub(r'\s*\n\s*', ' ', p)) for p in paras_raw]
        ayahs = extract_ayahs(sharh_raw)

        heading = meta['heading'].strip()
        if heading and not is_preface and not heading.startswith('['):
            heading = f'[ {heading} ]'

        units.append({
            'id': f'L{lesson_num:02d}_U{u_idx:02d}',
            'lesson_num': lesson_num,
            'unit_num': u_idx,
            'is_preface': is_preface,
            'toc_book': meta['toc_book'],
            'toc_fasl': meta['toc_fasl'],
            'lesson_note': meta['lesson_note'],
            'heading': heading,
            'sharh_header': '',
            'matn_raw': matn_text,
            'matn_lines': [html.escape(l) for l in matn_text.splitlines() if l.strip()],
            'fasl_end': meta['fasl_end'],
            'sharh_paras_html': paras_html,
            'ayahs': ayahs,
        })
    return units


def build_ayah_refs_map(units, repo_root: str) -> dict:
    """Resolve [السورة: الآية] for every Quranic ayah in Matn & Sharh using inline refs + QuranIndex."""
    refs = {}
    all_ayahs = []
    # 1) Collect explicit inline refs first
    for u in units:
        combined = '\n'.join(u['matn_lines']) + '\n' + '\n'.join(u['sharh_paras_html'])
        for m in re.finditer(r'﴿([^﴾]+)﴾(?:\s*(?:<span class="ayah-ref">)?(\[[^\]:]+:\s*[٠-٩\-]+\]))?', combined):
            ay = re.sub(r'<[^>]+>', '', m.group(1))
            ay = re.sub(r'\s+', ' ', ay).strip()
            all_ayahs.append(ay)
            if m.group(2) and ay not in refs:
                refs[ay] = re.sub(r'\s+', '\u00A0', m.group(2).strip())

    # 2) Resolve remaining ayahs via QuranIndex (quran_uthmani.json)
    qjson = os.path.join(repo_root, 'quran_uthmani.json')
    scripts_dir = os.path.join(repo_root, 'scripts')
    if os.path.exists(qjson) and os.path.isdir(scripts_dir):
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        try:
            import quran_helper
            qi = quran_helper.QuranIndex(qjson)
            for ay in all_ayahs:
                if ay in refs or len(ay.split()) < 2:
                    continue
                hits = qi.search(ay, top_k=2)
                if not hits:
                    # Try splitting concatenated consecutive verses using head/tail words
                    words = ay.split()
                    k = 3 if len(words) >= 6 else (2 if len(words) >= 4 else 1)
                    if len(words) >= 3:
                        head_hits = qi.search(' '.join(words[:k]), top_k=5)
                        for hh in head_hits:
                            end_hits = qi.search(' '.join(words[-k:]), top_k=5)
                            for eh in end_hits:
                                if eh['s'] == hh['s'] and 0 < (eh['a'] - hh['a']) <= 12:
                                    sname = hh['name']
                                    refs[ay] = f"[{sname}:\u00A0{to_eastern(hh['a'])}-{to_eastern(eh['a'])}]"
                                    break
                            if ay in refs:
                                break
                        if ay in refs:
                            continue
                if hits:
                    # Check if multi-ayah span
                    sname = hits[0]['name']
                    a1 = hits[0]['a']
                    words = ay.split()
                    end_hits = qi.search(' '.join(words[-4:]), top_k=3) if len(words) >= 5 else []
                    a2 = a1
                    for eh in end_hits:
                        if eh['s'] == hits[0]['s'] and eh['a'] > a1 and eh['a'] - a1 <= 6:
                            a2 = eh['a']
                            break
                    if a2 > a1:
                        refs[ay] = f"[{sname}:\u00A0{to_eastern(a1)}-{to_eastern(a2)}]"
                    else:
                        refs[ay] = f"[{sname}:\u00A0{to_eastern(a1)}]"
        except Exception as e:
            print("Warning: QuranIndex ayah_refs lookup partial:", e)
    return refs


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('out_pos', nargs='?', default=None)
    parser.add_argument('--mode', choices=('verbatim', 'edited'), default='verbatim')
    parser.add_argument('--input-dir', default=None)
    parser.add_argument('--out', default=None)
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    engine_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(engine_dir, exist_ok=True)

    playlist_path = os.path.join(repo_root, 'playlist_info.json')
    playlist_meta = {}
    if os.path.exists(playlist_path):
        pl = json.load(open(playlist_path, encoding='utf-8'))
        for idx, e in enumerate(pl.get('entries', []), 1):
            m = re.search(r'\((\d+)\)|«(\d+)»|(\d+)$', e.get('title', ''))
            lnum = int(m.group(1) or m.group(2) or m.group(3)) if m else idx
            playlist_meta[lnum] = {
                'vid': e.get('id', ''),
                'url': f"https://www.youtube.com/watch?v={e.get('id', '')}",
                'duration_min': round((e.get('duration') or 0) / 60),
                'yt_title': e.get('title', ''),
            }

    glossary_path = os.path.join(engine_dir, 'glossary_data.json')
    glossary_meta = {'source_credit': '', 'by_unit': {}, 'count': 0}
    if os.path.exists(glossary_path):
        glossary_meta = json.load(open(glossary_path, encoding='utf-8'))

    in_dir = args.input_dir or os.path.join(repo_root, 'edited_lessons' if args.mode == 'edited' else 'clean_lessons')
    files = sorted(glob.glob(os.path.join(in_dir, 'L*.txt')))
    all_units = []
    lessons_summary = []
    for f in files:
        m = re.search(r'L(\d+)\.txt$', f)
        if not m:
            continue
        lnum = int(m.group(1))
        units = parse_clean_file(f, lnum)
        for u in units:
            u['glosses'] = glossary_meta.get('by_unit', {}).get(u['id'], [])
        word_cnt = sum(len(re.sub(r'<[^>]+>', '', p).split()) for u in units for p in u['sharh_paras_html'])
        pinfo = playlist_meta.get(lnum, {'vid': '', 'url': '', 'duration_min': 0, 'yt_title': f'الدرس {lnum}'})
        first_note = next((u['lesson_note'] for u in units if u['lesson_note']), f'اللقاء {to_eastern(lnum)}')
        lessons_summary.append({
            'lesson_num': lnum,
            'eastern_num': to_eastern(lnum),
            'title': first_note,
            'duration_min': pinfo['duration_min'],
            'eastern_dur': to_eastern(pinfo['duration_min']),
            'url': pinfo['url'],
            'units_count': len(units),
            'word_count': word_cnt,
            'first_unit_id': units[0]['id'] if units else '',
        })
        all_units.extend(units)

    ayah_refs = build_ayah_refs_map(all_units, repo_root)

    default_out = os.path.join(engine_dir, 'book_data_edited.json' if args.mode == 'edited' else 'book_data.json')
    out_path = args.out or args.out_pos or default_out
    with open(out_path, 'w', encoding='utf-8') as out:
        json.dump({
            'title': 'تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ',
            'subtitle': 'المُسَمَّى بِـ «غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ»',
            'author_matn': 'لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ (٤٣٣ – ٥٩٣ هـ)',
            'author_sharh': 'لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ (حَفِظَهُ اللَّهُ تَعَالَى)',
            'description': 'تَفْرِيغٌ لِمُحَاضَرَاتِ فَضِيلَةِ الشَّيْخِ لِشَرْحِ المَتْنِ',
            'mode': args.mode,
            'glossary_source': glossary_meta.get('source_credit', ''),
            'glossary_count': glossary_meta.get('count', 0),
            'ayah_refs': ayah_refs,
            'lessons': lessons_summary,
            'units': all_units,
            'total_words': sum(l['word_count'] for l in lessons_summary),
        }, out, ensure_ascii=False, indent=2)
    print(f"Built {out_path} ({args.mode}): {len(lessons_summary)} lessons, {len(all_units)} units, {sum(l['word_count'] for l in lessons_summary)} Sharh words, {glossary_meta.get('count', 0)} curated glosses, {len(ayah_refs)} ayah_refs.")


if __name__ == '__main__':
    main()
