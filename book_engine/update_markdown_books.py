import glob
import json
import os
import re
import shutil

out_dir = '/home/antigravity/تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع'
old_out_dir = '/home/antigravity/شرح_أبي_شجاع_على_نسق_فتح_القريب_المجيب'
legacy_md_dir = '/home/antigravity/تفريغ_شرح_متن_أبي_شجاع'
os.makedirs(out_dir, exist_ok=True)
os.makedirs(legacy_md_dir, exist_ok=True)

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

playlist_info = json.load(open('/home/antigravity/playlist_info.json', encoding='utf-8'))
vid_by_num = {}
for e in playlist_info.get('entries', []):
    m = re.search(r'\((\d+)\)', e.get('title', ''))
    if m:
        lnum = int(m.group(1))
        vid_by_num[lnum] = (e.get('id'), round((e.get('duration') or 0) / 60))


def parse_clean_units(path: str):
    content = open(path, encoding='utf-8').read()
    parts = re.split(r'^@@UNIT\s*$', content, flags=re.M)[1:]
    units = []
    for part in parts:
        m = re.search(r'@@SHARH\s*\n(.*)', part, flags=re.S)
        header = part[:m.start()]
        sharh = m.group(1).strip()
        meta = {'toc_book': '', 'toc_fasl': '', 'heading': '', 'sharh_header': '', 'matn': [], 'fasl_end': False}
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
        meta['matn_str'] = '\n'.join(matn_lines).strip()
        meta['sharh'] = sharh
        units.append(meta)
    return units


book_header = """# تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ
## («غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ»)

**المتن:** غاية الاختصار (متن الغاية والتقريب) للإمام القاضي أبي شجاع أحمد بن الحسين الأصفهاني الشافعي (٤٣٣ – ٥٩٣ هـ)  
**الشرح:** التفريغ الحرفي الكامل المراجع لدروس فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  
**المنهج:** إثبات كلام الشيخ الشارح كاملاً كما أُلقي دون حذف أو اختصار، مع وضع كل مقطع من المتن مضبوطاً بالشكل في الأعلى، ثم الخط الفاصل، فالشرح الخاص به أسفله، وتمييز ألفاظ المتن المشروحة داخل الشرح **بالخط العريض**، وضبط الآيات القرآنية بين ﴿...﴾ والأحاديث النبوية بين «...» وخواتيم الفصول بعلامة (✽  ✽  ✽).

---
"""

vol1_header = """# تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الأَوَّلُ (اللقاءات ١ – ١٢)
## مُقَدِّمَةُ الْكِتَابِ وَكِتَابُ الطَّهَارَةِ

**المتن:** غاية الاختصار للإمام القاضي أبي شجاع أحمد بن الحسين الأصفهاني الشافعي (رحمه الله تعالى)  
**الشرح:** التفريغ الكامل غير المختصر لدروس فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  

---
"""

vol2_header = """# تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الثَّانِي (اللقاءات ١٣ – ٢٥)
## كِتَابُ الصَّلاَةِ

**المتن:** غاية الاختصار للإمام القاضي أبي شجاع أحمد بن الحسين الأصفهاني الشافعي (رحمه الله تعالى)  
**الشرح:** التفريغ الكامل غير المختصر لدروس فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  

---
"""

# Clean old files inside legacy_md_dir & out_dir (preserve PDF in out_dir)
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
    units = parse_clean_units(f'/home/antigravity/clean_lessons/L{num:02d}.txt')
    lines = [
        f"# {title}",
        "",
        f"**القسم:** {book_name} — تيسير الانتفاع بشرح مختصر أبي شجاع  ",
        f"**الشارح:** فضيلة الشيخ أحمد الجوهري عبد الجواد (حفظه الله تعالى)  ",
        f"**التسجيل الصوتي:** [اللقاء رقم ({num}) على يوتيوب](https://www.youtube.com/watch?v={vid}) ({dur} دقيقة)  ",
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
        if u['matn_str']:
            for mline in u['matn_str'].splitlines():
                if mline.strip():
                    lines.append(f"> **« {mline.strip()} »**")
            lines.append("")
            lines.append("---")
            lines.append("")
        lines.append(u['sharh'])
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
