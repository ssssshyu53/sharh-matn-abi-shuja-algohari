import json
import os
import re
import shutil

_ENG = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_ENG)
out_dir = os.path.join(_REPO, 'تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع')
old_out_dir = os.path.join(_REPO, 'شرح_أبي_شجاع_على_نسق_فتح_القريب_المجيب')
legacy_md_dir = os.path.join(_REPO, 'تفريغ_شرح_متن_أبي_شجاع')
os.makedirs(out_dir, exist_ok=True)
os.makedirs(legacy_md_dir, exist_ok=True)

EDIGITS = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')


def to_e(n):
    return str(n).translate(EDIGITS)


LESSON_SPECS = [
    (1, '01_الدرس_الأول_مقدمة_الكتاب_وأنواع_المياه_وأقسامها.md', 'اللقاء الأول: مقدمة الكتاب، ومقدمة المؤلف، وكتاب الطهارة (أنواع المياه وأقسامها)', 'مقدمة الكتاب وكتاب الطهارة'),
    (2, '02_الدرس_الثاني_الماء_النجس_ومقدار_القلتين.md', 'اللقاء الثاني: تتمة أقسام المياه، والماء المتغير والماء النجس ومقدار القلتين', 'كتاب الطهارة'),
    (3, '03_الدرس_الثالث_الدباغ_والأواني_والسواك.md', 'اللقاء الثالث: فصول جلود الميتة والدباغ، والأواني، واستعمال السواك', 'كتاب الطهارة'),
    (4, '04_الدرس_الرابع_فرائض_الوضوء_وسننه.md', 'اللقاء الرابع: فصل فروض الوضوء الستة وسننه العشر', 'كتاب الطهارة'),
    (5, '05_الدرس_الخامس_تتمة_سنن_الوضوء_والاستطابة_وآداب_الخلاء.md', 'اللقاء الخامس: تتمة سنن الوضوء، وفصل الاستنجاء وآداب قاضي الحاجة', 'كتاب الطهارة'),
    (6, '06_الدرس_السادس_نواقض_الوضوء_الستة.md', 'اللقاء السادس: فصل نواقض الوضوء الستة', 'كتاب الطهارة'),
    (7, '07_الدرس_السابع_موجبات_الغسل_وفرائضه_وسننه.md', 'اللقاء السابع: فصل موجبات الغسل الستة، وفصل فرائض الغسل وسننه', 'كتاب الطهارة'),
    (8, '08_الدرس_الثامن_الأغسال_المسنونة_السبعة_عشر.md', 'اللقاء الثامن: فصل الاغتسالات المسنونة السبعة عشر', 'كتاب الطهارة'),
    (9, '09_الدرس_التاسع_أحكام_المسح_على_الخفين.md', 'اللقاء التاسع: فصل المسح على الخفين وشرائطه ومدته ومبطلاته', 'كتاب الطهارة'),
    (10, '10_الدرس_العاشر_أحكام_التيمم_وشروطه_وفرائضه.md', 'اللقاء العاشر: فصل التيمم وشرائطه وفرائضه وسننه ومبطلاته وحكم الجبائر', 'كتاب الطهارة'),
    (11, '11_الدرس_الحادي_عشر_النجاسات_وكيفية_تطهيرها.md', 'اللقاء الحادي عشر: تتمة أحكام صاحب الجبائر، وفصل بيان النجاسات وإزالتها', 'كتاب الطهارة'),
    (12, '12_الدرس_الثاني_عشر_الحيض_والنفاس_والاستحاضة.md', 'اللقاء الثاني عشر: تتمة تطهير النجاسات، وفصل الحيض والنفاس والاستحاضة', 'كتاب الطهارة'),
    (13, '13_الدرس_الثالث_عشر_كتاب_الصلاة_ومواقيتها.md', 'اللقاء الثالث عشر: كتاب الصلاة — مواقيت الصلاة الخمسة', 'كتاب الصلاة'),
    (14, '14_الدرس_الرابع_عشر_شرائط_وجوب_الصلاة_والسنن_الرواتب.md', 'اللقاء الرابع عشر: فصل شرائط وجوب الصلاة، وفصل الصلوات المسنونة والرواتب', 'كتاب الصلاة'),
    (15, '15_الدرس_الخامس_عشر_شرائط_صحة_الصلاة_الخمسة.md', 'اللقاء الخامس عشر: فصل شرائط الصلاة قبل الدخول فيها', 'كتاب الصلاة'),
    (16, '16_الدرس_السادس_عشر_أركان_الصلاة_الثمانية_عشر.md', 'اللقاء السادس عشر: فصل أركان الصلاة الثمانية عشر', 'كتاب الصلاة'),
    (17, '17_الدرس_السابع_عشر_سنن_الصلاة_وأبعاضها_وهيئاتها.md', 'اللقاء السابع عشر: تتمة أركان الصلاة، وفصل سننها قبل الدخول فيها وبعده وهيئاتها', 'كتاب الصلاة'),
    (18, '18_الدرس_الثامن_عشر_مخالفة_المرأة_للرجل_ومبطلات_الصلاة_وإحصاء_الركعات.md', 'اللقاء الثامن عشر: فصول مخالفة المرأة للرجل، ومبطلات الصلاة، وعدد الركعات', 'كتاب الصلاة'),
    (19, '19_الدرس_التاسع_عشر_صلاة_العاجز_وسجود_السهو.md', 'اللقاء التاسع عشر: صلاة العاجز عن القيام، وفصل المتروك من الصلاة وسجود السهو', 'كتاب الصلاة'),
    (20, '20_الدرس_العشرون_الأوقات_المكروهة_وصلاة_الجماعة.md', 'اللقاء العشرون: فصل الأوقات التي تكره الصلاة فيها، وفصل صلاة الجماعة', 'كتاب الصلاة'),
    (21, '21_الدرس_الحادي_والعشرون_تتمة_الجماعة_وقصر_الصلاة_وجمعها.md', 'اللقاء الحادي والعشرون: تتمة صلاة الجماعة، وفصل قصر الصلاة وجمعها', 'كتاب الصلاة'),
    (22, '22_الدرس_الثاني_والعشرون_أحكام_صلاة_الجمعة.md', 'اللقاء الثاني والعشرون: فصل صلاة الجمعة وشروطها وفرائضها وهيئاتها', 'كتاب الصلاة'),
    (23, '23_الدرس_الثالث_والعشرون_صلاة_العيدين_ومقدمة_الكسوف.md', 'اللقاء الثالث والعشرون: فصل صلاة العيدين، ومقدمة فصل صلاة الكسوف والخسوف', 'كتاب الصلاة'),
    (24, '24_الدرس_الرابع_والعشرون_الكسوف_والاستسقاء_وصلاة_الخوف.md', 'اللقاء الرابع والعشرون: تتمة الكسوف والخسوف، وفصل الاستسقاء، وفصل صلاة الخوف', 'كتاب الصلاة'),
    (25, '25_الدرس_الخامس_والعشرون_أحكام_اللباس_والجنائز.md', 'اللقاء الخامس والعشرون: فصل اللباس، وفصل الجنائز وما يلزم في الميت', 'كتاب الصلاة'),
]

book_json = json.load(open(os.path.join(_ENG, 'book_data.json'), encoding='utf-8'))
vid_by_num_init = {l['lesson_num']: (l.get('url', '').split('v=')[-1] if 'v=' in l.get('url', '') else '', l.get('duration_min', 0)) for l in book_json.get('lessons', [])}
playlist_info = {'entries': []}
vid_by_num = vid_by_num_init

glossary_data = json.load(open(os.path.join(_ENG, 'glossary_data.json'), encoding='utf-8'))
SOURCE_CREDIT = glossary_data.get(
    'source_credit',
    '«الأَنوَارُ عَلَى غَايَةِ الاِخْتِصَارِ» لِجَامِعِهِ عَبْدِ الرَّحْمَنِ مُحَمَّدٍ نُورِ الدِّينِ'
)
GLOSS_BY_UNIT = glossary_data.get('by_unit', {})


def parse_clean_units(lnum: int, path: str):
    content = open(path, encoding='utf-8').read()
    parts = re.split(r'^@@UNIT\s*$', content, flags=re.M)[1:]
    units = []
    for idx, part in enumerate(parts, start=1):
        m = re.search(r'@@SHARH\s*\n(.*)', part, flags=re.S)
        header = part[:m.start()]
        sharh = m.group(1).strip()
        meta = {
            'id': f'L{lnum:02d}_U{idx:02d}',
            'toc_book': '', 'toc_fasl': '', 'heading': '', 'sharh_header': '',
            'matn': [], 'fasl_end': False
        }
        cur = None
        for line in header.splitlines():
            if line.startswith('TOC_BOOK:'):
                meta['toc_book'] = line[9:].strip(); cur = None
            elif line.startswith('TOC_FASL:'):
                meta['toc_fasl'] = line[9:].strip(); cur = None
            elif line.startswith('HEADING:'):
                meta['heading'] = line[8:].strip(); cur = None
            elif line.startswith('SHARH_HEADER:'):
                meta['sharh_header'] = line[13:].strip(); cur = None
            elif line.startswith('MATN:'):
                meta['matn'].append(line[5:].strip()); cur = 'M'
            elif line.startswith('FASL_END:'):
                meta['fasl_end'] = line[9:].strip().lower() in ('yes', 'true', '1', 'نعم'); cur = None
            elif cur == 'M' and line.strip():
                meta['matn'].append(line.strip())
        matn_lines = [l for l in meta['matn'] if l]
        if meta['toc_book'] and matn_lines and matn_lines[0].strip().rstrip(':') == meta['toc_book'].strip().rstrip(':'):
            matn_lines = matn_lines[1:]
        meta['matn_lines'] = matn_lines
        meta['sharh'] = sharh
        units.append(meta)
    return units


def annotate_matn_lines_and_notes(matn_lines, glosses):
    if not glosses or not matn_lines:
        return matn_lines, []
    lines = list(matn_lines)
    placements = []
    seen_terms = set()
    for g in glosses:
        nk = re.sub(r'[\u064b-\u065f\u0670\u0640\s]', '', g['term'])
        if nk in seen_terms:
            continue
        rx = re.compile(g['pattern'])
        for li, ln in enumerate(lines):
            m = rx.search(ln)
            if m:
                seen_terms.add(nk)
                placements.append((li, m.start(), m.end(), g))
                break
    placements.sort(key=lambda x: (x[0], x[1]))
    notes = []
    by_line = {}
    for num_idx, (li, _st, end, g) in enumerate(placements, start=1):
        notes.append((to_e(num_idx), g['gloss']))
        by_line.setdefault(li, []).append((end, to_e(num_idx)))
    for li, items in by_line.items():
        s = lines[li]
        for end, e_num in sorted(items, key=lambda x: -x[0]):
            s = s[:end] + f' ({e_num})' + s[end:]
        lines[li] = s
    return lines, notes


book_header = f"""# تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ
## («غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ»)

**المتن:** غاية الاختصار (متن الغاية والتقريب) للإمام القاضي أبي شجاع أحمد بن الحسين الأصفهاني الشافعي (٤٣٣ – ٥٩٣ هـ)  
**الشرح:** التفريغ الحرفي الكامل المراجع لدروس فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  
**المنهج:** إثبات كلام الشيخ الشارح كاملاً كما أُلقي دون حذف أو اختصار، مع وضع كل مقطع من المتن مضبوطاً بالشكل في الأعلى، ثم الخط الفاصل، فالشرح الخاص به أسفله، وتمييز ألفاظ المتن المشروحة داخل الشرح **بالخط العريض**، وضبط الآيات القرآنية بين ﴿...﴾ والأحاديث النبوية بين «...» وخواتيم الفصول بعلامة (✽  ✽  ✽).  
**الحواشي وغريب المتن:** أُلحقت في ذيل المقاطع معاني الألفاظ الغريبة التي لم يتعرّض الشيخ الشارح لبيانها في موضعها، منتقاةً من رسالة **{SOURCE_CREDIT}**.

---
"""

vol1_header = f"""# تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الأَوَّلُ (اللقاءات ١ – ١٢)
## مُقَدِّمَةُ الْكِتَابِ وَكِتَابُ الطَّهَارَةِ

**المتن:** غاية الاختصار للإمام القاضي أبي شجاع أحمد بن الحسين الأصفهاني الشافعي (رحمه الله تعالى)  
**الشرح:** التفريغ الكامل غير المختصر لدروس فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  
**الحواشي وغريب المتن:** منتقاة من رسالة **{SOURCE_CREDIT}**.

---
"""

vol2_header = f"""# تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الثَّانِي (اللقاءات ١٣ – ٢٥)
## كِتَابُ الصَّلاَةِ

**المتن:** غاية الاختصار للإمام القاضي أبي شجاع أحمد بن الحسين الأصفهاني الشافعي (رحمه الله تعالى)  
**الشرح:** التفريغ الكامل غير المختصر لدروس فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  
**الحواشي وغريب المتن:** منتقاة من رسالة **{SOURCE_CREDIT}**.

---
"""

# Clean old markdown files while keeping binary deliverables intact
for fname_existing in os.listdir(legacy_md_dir):
    if fname_existing.endswith('.md'):
        os.remove(os.path.join(legacy_md_dir, fname_existing))
for fname_existing in os.listdir(out_dir):
    if fname_existing.endswith('.md'):
        os.remove(os.path.join(out_dir, fname_existing))

full_book_parts = [book_header]
vol1_parts = [vol1_header]
vol2_parts = [vol2_header]
total_words = 0

for num, fname, title, book_name in LESSON_SPECS:
    vid, dur = vid_by_num.get(num, ('', 0))
    units = parse_clean_units(num, os.path.join(_REPO, 'clean_lessons', f'L{num:02d}.txt'))
    lines = [
        f"# {title}",
        "",
        f"**القسم:** {book_name} — تيسير الانتفاع بشرح مختصر أبي شجاع  ",
        "**الشارح:** فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  ",
        f"**التسجيل الصوتي:** [اللقاء رقم ({num}) على يوتيوب](https://www.youtube.com/watch?v={vid}) ({dur} دقيقة)  ",
        f"**مرجع حواشي غريب المتن:** {SOURCE_CREDIT}  ",
        "",
        "---",
        "",
    ]
    for u in units:
        if u['toc_book']:
            lines.append(f"## {u['toc_book']}")
            lines.append("")
        if u['toc_fasl']:
            lines.append(f"### {u['toc_fasl']}")
            lines.append("")
        m_lines, notes = annotate_matn_lines_and_notes(u['matn_lines'], GLOSS_BY_UNIT.get(u['id'], []))
        if m_lines:
            for mline in m_lines:
                if mline.strip():
                    lines.append(f"> **« {mline.strip()} »**")
            lines.append("")
            lines.append("---")
            lines.append("")
        lines.append(u['sharh'])
        lines.append("")
        if notes:
            lines.append("> **حاشية غريب المتن:**  ")
            for n_num, n_text in notes:
                lines.append(f"> **({n_num})** {n_text}  ")
            lines.append("")
        if u['fasl_end']:
            lines.append("<p align=\"center\">✽ &nbsp;&nbsp;&nbsp; ✽ &nbsp;&nbsp;&nbsp; ✽</p>")
            lines.append("")
        lines.append("---")
        lines.append("")
        total_words += len(u['sharh'].split())

    md_text = '\n'.join(lines)
    with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
        f.write(md_text)
    with open(os.path.join(legacy_md_dir, fname), 'w', encoding='utf-8') as f:
        f.write(md_text)

    full_book_parts.append(md_text)
    if num <= 12:
        vol1_parts.append(md_text)
    else:
        vol2_parts.append(md_text)

with open(os.path.join(out_dir, '00_المجلد_الكامل_تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(full_book_parts))
with open(os.path.join(out_dir, 'المجلد_الأول_مقدمة_الكتاب_وكتاب_الطهارة_اللقاءات_1_إلى_12.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(vol1_parts))
with open(os.path.join(out_dir, 'المجلد_الثاني_كتاب_الصلاة_اللقاءات_13_إلى_25.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(vol2_parts))

if os.path.isdir(old_out_dir):
    shutil.rmtree(old_out_dir)

print(f"Updated all 25 lesson markdown files and 3 volume files in {out_dir}! Total Sharh words: {total_words}")
