#!/usr/bin/env python3
"""
Updates the 3 Google Docs (Full Volume, Volume 1: Kitab al-Taharah, Volume 2: Kitab al-Salah & al-Jana'iz)
in-place using `gdocs mutate batch` with the Dar Ibn Hazm split-section layout:
  - Upper Matn zone (13.5pt Amiri, justified, fully vocalized, soft cream background)
  - Horizontal dividing rule (`horizontal-rule`)
  - Lower Sharh zone (11.5pt Amiri, justified, bolded Matn phrases, ﴿...﴾ ayahs)
  - Centered `✽      ✽      ✽` floral section separators
  - Full RTL paragraph direction (`RIGHT_TO_LEFT`) across the entire document body.
"""
import json
import os
import re
import subprocess

os.environ.setdefault("ANTIGRAVITY_APP_DATA_DIR", "/home/antigravity/.local/gdocs_data")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(REPO_ROOT, "book_engine", "book_data.json")

with open(DATA_PATH, encoding="utf-8") as f:
    DATA = json.load(f)

DOC_VOL1 = "1xqRrQTK862s9p8OchjSHOBRyFbGeWxndfiY2vj3hsN8"
DOC_VOL2 = "167eTHwNCyjte0hrtJZQ9oCKvjBIGtjv9fkM2bFPRJ3M"
DOC_FULL = "1JWeLsDtlU76TSQt-uac_vmXxDf1RCLLogj3tjZsYxUE"


def html_para_to_runs(p_html: str):
    pattern = re.compile(r'(<strong>.*?</strong>|<span class="ayah">.*?</span>)', flags=re.S)
    parts = pattern.split(p_html)
    runs = []
    for part in parts:
        if not part:
            continue
        is_bold = False
        txt = part
        if part.startswith("<strong>") and part.endswith("</strong>"):
            is_bold = True
            txt = part[len("<strong>"):-len("</strong>")]
        elif part.startswith('<span class="ayah">') and part.endswith("</span>"):
            is_bold = True
            txt = part[len('<span class="ayah">'):-len("</span>")]
        txt = re.sub(r"<[^>]+>", "", txt)
        txt = (
            txt.replace("&quot;", '"')
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )
        if txt:
            runs.append({
                "text": txt,
                "bold": is_bold,
                "italic": False,
                "font_family": "Amiri",
                "font_size": 11.5,
                "text_color": "#111111",
            })
    if not runs:
        runs.append({
            "text": " ",
            "bold": False,
            "italic": False,
            "font_family": "Amiri",
            "font_size": 11.5,
            "text_color": "#111111",
        })
    return runs


def build_header_ops(title_main: str, subtitle_line: str, lessons_slice):
    ops = [
        {
            "op": "set-default-style",
            "font_family": "Amiri",
            "font_size": 11.5,
            "text_color": "#111111",
            "line_spacing": 115,
            "space_above": 2,
            "space_below": 3,
        },
        {
            "op": "append",
            "text": "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ",
            "font_family": "Amiri",
            "font_size": 20,
            "bold": True,
            "alignment": "CENTER",
        },
        {
            "op": "heading",
            "level": "TITLE",
            "text": title_main,
            "font_family": "Amiri",
            "font_size": 22,
            "bold": True,
            "alignment": "CENTER",
            "text_color": "#111111",
            "space_above": 4,
            "space_below": 4,
        },
        {
            "op": "append",
            "text": subtitle_line,
            "font_family": "Amiri",
            "font_size": 13,
            "bold": True,
            "alignment": "CENTER",
            "text_color": "#222222",
        },
        {
            "op": "append",
            "text": "لِفَضِيلَةِ الشَّيْخِ الدُّكْتُورِ أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ (حَفِظَهُ اللهُ تَعَالَى)",
            "font_family": "Amiri",
            "font_size": 13,
            "bold": True,
            "alignment": "CENTER",
            "text_color": "#111111",
        },
        {
            "op": "append",
            "text": "مُعَدٌّ وَمُنَسَّقٌ كَامِلاً دُونَ اخْتِصَارٍ عَلَى طَرِيقَةِ طَبْعَةِ دَارِ ابْنِ حَزْمٍ لِكِتَابِ « فَتْحِ الْقَرِيبِ الْمُجِيبِ »\n( الْمَتْنُ فِي أَعْلَى الْمَقْطَعِ مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ الْحَرْفِيِّ الْكَامِلِ أَسْفَلَهُ )",
            "font_family": "Amiri",
            "font_size": 11,
            "bold": False,
            "alignment": "CENTER",
            "text_color": "#333333",
        },
        {
            "op": "append",
            "text": "✽      ✽      ✽",
            "font_family": "Amiri",
            "font_size": 13,
            "bold": True,
            "alignment": "CENTER",
        },
    ]

    table_data = [["م", "مَوْضُوعُ اللِّقَاءِ الصَّوْتِيِّ", "الْمُدَّةُ", "عَدَدُ الْكَلِمَاتِ"]]
    for l in lessons_slice:
        clean_t = re.sub(r"^اللقاء [^:]+:\s*", "", l["title"])
        table_data.append([
            l["eastern_num"],
            clean_t,
            f"{l['eastern_dur']} د",
            str(l["word_count"]),
        ])
    ops.append({
        "op": "insert-table",
        "rows": len(table_data),
        "cols": 4,
        "table_data": table_data,
        "table_header_bold": True,
        "table_header_bg_color": "#f3f0e6",
        "table_header_text_color": "#111111",
        "table_font_family": "Amiri",
        "table_font_size": 10.5,
        "table_border_color": "#222222",
        "table_border_width": 0.75,
        "table_col_widths": [36, 300, 56, 70],
    })
    ops.append({"op": "horizontal-rule"})
    return ops


def build_unit_ops(units_slice):
    ops = [
        {
            "op": "set-default-style",
            "font_family": "Amiri",
            "font_size": 11.5,
            "text_color": "#111111",
            "line_spacing": 115,
            "space_above": 2,
            "space_below": 3,
        }
    ]
    for u in units_slice:
        if u.get("toc_book"):
            ops.append({
                "op": "heading",
                "level": "1",
                "text": u["toc_book"],
                "font_family": "Amiri",
                "font_size": 18,
                "bold": True,
                "alignment": "CENTER",
                "text_color": "#111111",
                "space_above": 10,
                "space_below": 4,
            })
        heading_level = "2" if (u.get("toc_fasl") or u["unit_num"] == 1) else "3"
        ops.append({
            "op": "heading",
            "level": heading_level,
            "text": u["heading"],
            "font_family": "Amiri",
            "font_size": 14.5 if heading_level == "2" else 13,
            "bold": True,
            "alignment": "CENTER",
            "text_color": "#111111",
            "space_above": 6,
            "space_below": 3,
        })
        if u.get("lesson_note"):
            ops.append({
                "op": "append",
                "text": f"({u['lesson_note']})",
                "font_family": "Amiri",
                "font_size": 10,
                "bold": False,
                "alignment": "CENTER",
                "text_color": "#444444",
            })

        for m_line in u["matn_lines"]:
            clean_m = (
                m_line.replace("&quot;", '"')
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
            )
            ops.append({
                "op": "append",
                "text": clean_m,
                "font_family": "Amiri",
                "font_size": 13.5,
                "bold": True,
                "alignment": "JUSTIFIED",
                "indent_first_line": 18,
                "paragraph_bg_color": "#faf7ef",
                "text_color": "#111111",
            })

        ops.append({"op": "horizontal-rule"})

        if u.get("sharh_header"):
            ops.append({
                "op": "append",
                "text": u["sharh_header"],
                "font_family": "Amiri",
                "font_size": 13,
                "bold": True,
                "alignment": "CENTER",
                "text_color": "#111111",
            })

        for p_html in u["sharh_paras_html"]:
            runs = html_para_to_runs(p_html)
            ops.append({
                "op": "rich-text",
                "font_family": "Amiri",
                "font_size": 11.5,
                "text_color": "#111111",
                "alignment": "JUSTIFIED",
                "indent_first_line": 18,
                "runs": runs,
            })

        ops.append({
            "op": "append",
            "text": "✽      ✽      ✽",
            "font_family": "Amiri",
            "font_size": 12,
            "bold": True,
            "alignment": "CENTER",
            "text_color": "#111111",
        })
    return ops


def run_batch(doc_id: str, ops, replace_all: bool = False, label: str = ""):
    tmp_path = f"/tmp/gdoc_ops_{doc_id}_{'rep' if replace_all else 'app'}.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(ops, f, ensure_ascii=False)
    cmd = ["gdocs", "mutate", "batch", doc_id, "-f", tmp_path]
    if replace_all:
        cmd.append("--replace-all")
    print(f"Running {label} ({len(ops)} ops, replace_all={replace_all}) -> {doc_id} ...")
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"Batch failed on {doc_id}: {res.stderr[-400:]}")


def apply_rtl_to_entire_doc(doc_id: str):
    res = subprocess.run(
        ["gdocs", "readonly", "dump-body", doc_id],
        capture_output=True,
        text=True,
        check=True,
    )
    body = json.loads(res.stdout)
    content = body.get("content", [])
    end_idx = content[-1].get("endIndex", 2) - 1 if content else 2
    if end_idx <= 1:
        return
    rtl_ops = [
        {
            "op": "raw",
            "raw_request": {
                "updateParagraphStyle": {
                    "range": {"startIndex": 1, "endIndex": end_idx},
                    "paragraphStyle": {"direction": "RIGHT_TO_LEFT"},
                    "fields": "direction",
                }
            },
        }
    ]
    run_batch(doc_id, rtl_ops, replace_all=False, label=f"RTL direction (1..{end_idx})")


def main():
    lessons_v1 = [l for l in DATA["lessons"] if l["lesson_num"] <= 12]
    lessons_v2 = [l for l in DATA["lessons"] if l["lesson_num"] >= 13]
    units_v1 = [u for u in DATA["units"] if u["lesson_num"] <= 12]
    units_v2 = [u for u in DATA["units"] if u["lesson_num"] >= 13]

    ops_v1 = build_header_ops(
        "الشَّرْحُ الْكَامِلُ عَلَى أَلْفَاظِ مَتْنِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الأَوَّلُ: كِتَابُ الطَّهَارَةِ",
        "التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ الْمُرَاجَعُ لِلِّقَاءَاتِ ( ١ – ١٢ )",
        lessons_v1,
    ) + build_unit_ops(units_v1)
    run_batch(DOC_VOL1, ops_v1, replace_all=True, label="Volume 1 (L01-L12)")
    apply_rtl_to_entire_doc(DOC_VOL1)

    ops_v2 = build_header_ops(
        "الشَّرْحُ الْكَامِلُ عَلَى أَلْفَاظِ مَتْنِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الثَّانِي: كِتَابُ الصَّلاَةِ وَالْجَنَائِزِ",
        "التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ الْمُرَاجَعُ لِلِّقَاءَاتِ ( ١٣ – ٢٥ )",
        lessons_v2,
    ) + build_unit_ops(units_v2)
    run_batch(DOC_VOL2, ops_v2, replace_all=True, label="Volume 2 (L13-L25)")
    apply_rtl_to_entire_doc(DOC_VOL2)

    ops_full_part1 = build_header_ops(
        "الشَّرْحُ الْكَامِلُ عَلَى أَلْفَاظِ مَتْنِ أَبِي شُجَاعٍ (الْمُسَمَّى بِغَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ)",
        "الْمُجَلَّدُ الْكَامِلُ لِلدُّرُوسِ الْخَمْسَةِ وَالْعِشْرِينَ ( ١ – ٢٥ ) — الطَّهَارَةُ وَالصَّلاَةُ وَالْجَنَائِزُ",
        DATA["lessons"],
    ) + build_unit_ops(units_v1)
    ops_full_part2 = build_unit_ops(units_v2)
    run_batch(DOC_FULL, ops_full_part1, replace_all=True, label="Full Volume Part 1")
    run_batch(DOC_FULL, ops_full_part2, replace_all=False, label="Full Volume Part 2")
    apply_rtl_to_entire_doc(DOC_FULL)


if __name__ == "__main__":
    main()
