#!/usr/bin/env python3
"""
Updates the 3 Google Docs (Full Volume, Volume 1: Kitab al-Taharah, Volume 2: Kitab al-Salah)
in-place using `gdocs mutate batch`:
  - Title: تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ
  - Sheikh honorific: لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ (without الدكتور)
  - No front audio lecture schedule table
  - Continuous book preface (`is_preface`) with no split rule
  - Matn-authentic headings only (`toc_book`, `toc_fasl`) — no artificial sub-headings or SHARH_HEADER
  - Upper Matn zone (13.5pt Amiri, justified, fully vocalized, soft cream background)
  - Horizontal dividing rule (`horizontal-rule`)
  - Lower Sharh zone (11.5pt Amiri, justified, bolded Matn phrases, ﴿...﴾ ayahs)
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
    pattern = re.compile(r'(<strong>.*?</strong>|<span class="ayah(?:-ref)?">.*?</span>)', flags=re.S)
    parts = pattern.split(p_html)
    runs = []
    for part in parts:
        if not part:
            continue
        is_bold = False
        color = "#111111"
        font_sz = 11.5
        txt = part
        if part.startswith("<strong>") and part.endswith("</strong>"):
            is_bold = True
            color = "#9b111e"
            txt = part[len("<strong>"):-len("</strong>")]
        elif part.startswith('<span class="ayah">') and part.endswith("</span>"):
            is_bold = True
            color = "#111111"
            txt = part[len('<span class="ayah">'):-len("</span>")]
        elif part.startswith('<span class="ayah-ref">') and part.endswith("</span>"):
            is_bold = False
            color = "#5F6368"
            font_sz = 8.8
            txt = part[len('<span class="ayah-ref">'):-len("</span>")]
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
                "font_size": font_sz,
                "text_color": color,
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


def build_header_ops(title_main: str, subtitle_line: str):
    return [
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
            "text": "لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ (حَفِظَهُ اللهُ تَعَالَى)",
            "font_family": "Amiri",
            "font_size": 13,
            "bold": True,
            "alignment": "CENTER",
            "text_color": "#111111",
        },
        {
            "op": "append",
            "text": "وَالْمَتْنُ لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ (٤٣٣ – ٥٩٣ هـ)\nتَفْرِيغٌ حَرْفِيٌّ كَامِلٌ مُرَاجَعٌ دُونَ حَذْفٍ أَوْ اخْتِصَارٍ ( الْمَتْنُ مَضْبُوطاً بِالشَّكْلِ فِي الأَعْلَى مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ أَسْفَلَهُ )",
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
        {"op": "horizontal-rule"},
    ]


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
        if u.get("is_preface"):
            preface_title = u.get("toc_fasl") or "مُقَدِّمَةُ الْكِتَابِ"
            ops.append({
                "op": "heading",
                "level": "2",
                "text": preface_title,
                "font_family": "Amiri",
                "font_size": 16,
                "bold": True,
                "alignment": "CENTER",
                "text_color": "#111111",
                "space_above": 8,
                "space_below": 4,
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
            continue

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
        if u.get("toc_fasl"):
            ops.append({
                "op": "heading",
                "level": "2",
                "text": u["toc_fasl"],
                "font_family": "Amiri",
                "font_size": 14.5,
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
            is_basmalah = (clean_m.strip() == "بِسْمِ اللهِ الرَّحْمَنِ الرَّحِيمِ")
            ops.append({
                "op": "append",
                "text": clean_m,
                "font_family": "Amiri",
                "font_size": 14.5 if is_basmalah else 13.5,
                "bold": True,
                "alignment": "CENTER" if is_basmalah else "JUSTIFIED",
                "indent_first_line": 0 if is_basmalah else 18,
                "paragraph_bg_color": "#faf7ef",
                "text_color": "#111111",
            })

        ops.append({"op": "horizontal-rule"})

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

        if u.get("fasl_end"):
            ops.append({
                "op": "append",
                "text": "✽      ✽      ✽",
                "font_family": "Amiri",
                "font_size": 12,
                "bold": True,
                "alignment": "CENTER",
                "text_color": "#111111",
            })
        else:
            ops.append({
                "op": "append",
                "text": "✽   ✽   ✽",
                "font_family": "Amiri",
                "font_size": 10.5,
                "bold": False,
                "alignment": "CENTER",
                "text_color": "#555555",
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
    units_v1 = [u for u in DATA["units"] if u["lesson_num"] <= 12]
    units_v2 = [u for u in DATA["units"] if u["lesson_num"] >= 13]

    ops_v1 = build_header_ops(
        "تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الأَوَّلُ",
        "مُقَدِّمَةُ الْكِتَابِ وَكِتَابُ الطَّهَارَةِ — التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِلِّقَاءَاتِ ( ١ – ١٢ )",
    ) + build_unit_ops(units_v1)
    run_batch(DOC_VOL1, ops_v1, replace_all=True, label="Volume 1 (L01-L12)")
    apply_rtl_to_entire_doc(DOC_VOL1)

    ops_v2 = build_header_ops(
        "تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — الْمُجَلَّدُ الثَّانِي",
        "كِتَابُ الصَّلاَةِ — التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِلِّقَاءَاتِ ( ١٣ – ٢٥ )",
    ) + build_unit_ops(units_v2)
    run_batch(DOC_VOL2, ops_v2, replace_all=True, label="Volume 2 (L13-L25)")
    apply_rtl_to_entire_doc(DOC_VOL2)

    ops_full_part1 = build_header_ops(
        "تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ",
        "الشَّرْحُ الْحَرْفِيُّ الْكَامِلُ عَلَى مَتْنِ الْغَايَةِ وَالتَّقْرِيبِ لِلْقَاضِي أَبِي شُجَاعٍ — اللِّقَاءَاتُ ( ١ – ٢٥ )",
    ) + build_unit_ops(units_v1)
    ops_full_part2 = build_unit_ops(units_v2)
    run_batch(DOC_FULL, ops_full_part1, replace_all=True, label="Full Volume Part 1")
    run_batch(DOC_FULL, ops_full_part2, replace_all=False, label="Full Volume Part 2")
    apply_rtl_to_entire_doc(DOC_FULL)


if __name__ == "__main__":
    main()
