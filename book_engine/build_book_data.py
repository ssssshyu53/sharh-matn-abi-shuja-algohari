import glob
import html
import json
import os
import re
import sys

EASTERN_DIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

def to_eastern(n) -> str:
    return str(n).translate(EASTERN_DIGITS)

def clean_matn_html(matn_text: str) -> str:
    # Split lines; preserve brackets and lines cleanly
    lines = [l.strip() for l in matn_text.strip().splitlines() if l.strip()]
    out = []
    for l in lines:
        esc = html.escape(l)
        out.append(esc)
    return '\n'.join(out)

def format_sharh_inline_html(text: str) -> str:
    esc = html.escape(text)
    # Bold **...** (handle across inline spans safely)
    esc = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc, flags=re.S)
    # Quranic Ayahs ﴿...﴾ -> styled with AmiriQuran
    esc = re.sub(r'(﴿[^﴾]+﴾)', r'<span class="ayah">\1</span>', esc)
    # Convert صلى الله عليه وسلم / عليه السلام nicely if needed, keep verbatim!
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

        # Separate paragraphs by blank lines
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

def main():
    os.makedirs('/home/antigravity/book_engine', exist_ok=True)
    playlist_path = '/home/antigravity/playlist_info.json'
    playlist_meta = {}
    if os.path.exists(playlist_path):
        pl = json.load(open(playlist_path, encoding='utf-8'))
        for e in pl.get('entries', []):
            m = re.search(r'\((\d+)\)', e.get('title', ''))
            if m:
                n = int(m.group(1))
                playlist_meta[n] = {
                    'vid': e.get('id', ''),
                    'url': f"https://www.youtube.com/watch?v={e.get('id', '')}",
                    'duration_min': round((e.get('duration') or 0) / 60),
                    'yt_title': e.get('title', ''),
                }

    files = sorted(glob.glob('/home/antigravity/clean_lessons/L*.txt'))
    all_units = []
    lessons_summary = []
    for f in files:
        m = re.search(r'L(\d+)\.txt$', f)
        if not m:
            continue
        lnum = int(m.group(1))
        units = parse_clean_file(f, lnum)
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

    out_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/book_data.json'
    with open(out_path, 'w', encoding='utf-8') as out:
        json.dump({
            'lessons': lessons_summary,
            'units': all_units,
            'total_words': sum(l['word_count'] for l in lessons_summary),
        }, out, ensure_ascii=False, indent=2)
    print(f"Built {out_path}: {len(lessons_summary)} lessons, {len(all_units)} clause units, {sum(l['word_count'] for l in lessons_summary)} Sharh words.")

if __name__ == '__main__':
    main()
