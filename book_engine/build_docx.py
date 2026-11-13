#!/usr/bin/env python3
"""
Builds pixel- & millimeter-aligned editable Word (.docx) editions directly from
Chromium's paginated HTML DOM (`full_book.html` / `full_book_two_color.html`):
  - Exact Trim Size: 162mm x 234mm
  - Cover Plate (pg-1, full-bleed cover_front.png anchored edge-to-edge 162x234mm)
  - Framed Front Plates (pg-2..pg-4: double thick-thin border frame, 204mm frame height)
  - Running Alternating Headers (pg-5..pg-365: evenAndOddHeaders with live PAGE field)
  - Body Pages (pg-5..pg-359): Upper Matn with superscript gloss numbers (١),
    middle horizontal split rule, Lower Sharh (bold Matn citations + Amiri Quran ayahs),
    and per-page bottom footnote area ((*) lesson + (١) Al-Anwar glosses)
  - Back Matter Indexes (pg-360..pg-364 Ayah Index table + pg-365 Two-Column General TOC)
  - Strict ECMA-376 OOXML child ordering and zero duplicate property nodes.
  - Supports `--edition classic` and `--edition two-color` (#9b111e crimson + #111111 black on white).
"""
import argparse
import os
from lxml import html as lhtml
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

_ENG = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_ENG)
COVER_IMG = os.path.join(_ENG, "cover_front.png")
ASSETS_HTML = {
    "classic": os.path.join(_ENG, "full_book.html"),
    "two-color": os.path.join(_ENG, "full_book_two_color.html"),
}
OUT_PATHS = {
    "classic": os.path.join(_REPO, "تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع", "تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع.docx"),
    "two-color": os.path.join(_REPO, "تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع", "تيسير_الانتفاع_بشرح_مختصر_أبي_شجاع_نسخة_لونين.docx"),
}

EDIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

PPR_SEQ = [
    qn(t) for t in (
        "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
        "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
        "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
        "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
        "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
        "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
        "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl",
        "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange",
    )
]
TBLPR_SEQ = [
    qn(t) for t in (
        "w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
        "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW", "w:jc",
        "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd", "w:tblLayout",
        "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription", "w:tblPrChange",
    )
]
TCPR_SEQ = [
    qn(t) for t in (
        "w:cnfStyle", "w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge",
        "w:tcBorders", "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
        "w:tcFitText", "w:vAlign", "w:hideMark", "w:headers", "w:tcPrChange",
    )
]
SECTPR_SEQ = [
    qn(t) for t in (
        "w:headerReference", "w:footerReference", "w:footnotePr", "w:endnotePr",
        "w:type", "w:pgSz", "w:pgMar", "w:paperSrc", "w:pgBorders", "w:lnNumType",
        "w:pgNumType", "w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg",
        "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid", "w:printerSettings",
        "w:sectPrChange",
    )
]


def get_or_add(parent, qname_str: str):
    el = parent.find(qn(qname_str))
    if el is None:
        el = OxmlElement(qname_str)
        parent.append(el)
    return el


def sort_xml_children(el, seq_tags):
    order_map = {tag: i for i, tag in enumerate(seq_tags)}
    children = list(el)
    children.sort(key=lambda ch: order_map.get(ch.tag, 999))
    for ch in children:
        el.remove(ch)
        el.append(ch)


def to_e(n) -> str:
    return str(n).translate(EDIGITS)


def get_palette(edition: str) -> dict:
    if edition == "two-color":
        return {
            "ink": "111111",
            "accent": "9B111E",
            "matn_ink": "9B111E",
            "strong_ink": "9B111E",
            "ayah_ink": "111111",
            "rule_ink": "9B111E",
            "fn_num_ink": "9B111E",
            "subtle_ink": "333333",
        }
    return {
        "ink": "111111",
        "accent": "111111",
        "matn_ink": "111111",
        "strong_ink": "111111",
        "ayah_ink": "111111",
        "rule_ink": "111111",
        "fn_num_ink": "111111",
        "subtle_ink": "333333",
    }


def configure_ppr_rtl(pPr, align_val=None, line_pt=None,
                      sb_tw=None, sa_tw=None, indent_first_tw=None,
                      page_break_before=False, mark_size_pt=None):
    get_or_add(pPr, "w:bidi")
    get_or_add(pPr, "w:adjustRightInd")
    if page_break_before:
        get_or_add(pPr, "w:pageBreakBefore")
    if line_pt is not None or sb_tw is not None or sa_tw is not None:
        sp = get_or_add(pPr, "w:spacing")
        if sb_tw is not None:
            sp.set(qn("w:before"), str(int(round(sb_tw))))
        if sa_tw is not None:
            sp.set(qn("w:after"), str(int(round(sa_tw))))
        if line_pt is not None:
            sp.set(qn("w:line"), str(int(round(line_pt * 20))))
            sp.set(qn("w:lineRule"), "exact")
    if indent_first_tw is not None:
        ind = get_or_add(pPr, "w:ind")
        ind.set(qn("w:firstLine"), str(int(round(indent_first_tw))))
    if align_val is not None:
        jc = get_or_add(pPr, "w:jc")
        jc.set(qn("w:val"), align_val)
    if mark_size_pt is not None:
        rPr = get_or_add(pPr, "w:rPr")
        sz_half = str(int(round(mark_size_pt * 2)))
        get_or_add(rPr, "w:sz").set(qn("w:val"), sz_half)
        get_or_add(rPr, "w:szCs").set(qn("w:val"), sz_half)
    sort_xml_children(pPr, PPR_SEQ)


def set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=None,
                 sb_pt=0.0, sa_pt=0.0, indent_first_pt=0.0, page_break_before=False,
                 mark_size_pt: float = None):
    jc_map = {
        WD_ALIGN_PARAGRAPH.RIGHT: "right",
        WD_ALIGN_PARAGRAPH.LEFT: "left",
        WD_ALIGN_PARAGRAPH.CENTER: "center",
        WD_ALIGN_PARAGRAPH.JUSTIFY: "both",
    }
    pPr = p._p.get_or_add_pPr()
    configure_ppr_rtl(
        pPr,
        align_val=jc_map.get(align, "right"),
        line_pt=line_pt,
        sb_tw=sb_pt * 20,
        sa_tw=sa_pt * 20,
        indent_first_tw=(indent_first_pt * 20 if indent_first_pt else 0),
        page_break_before=page_break_before,
        mark_size_pt=mark_size_pt,
    )
    return p


def shrink_section_break_para(prev_sec):
    """Ensures section-break-holding paragraph is 1pt tall so full preceding pages never overflow."""
    pPr = prev_sec._sectPr.getparent()
    if pPr is not None and pPr.tag == qn("w:pPr"):
        configure_ppr_rtl(pPr, align_val="right", line_pt=1.0, sb_tw=0, sa_tw=0,
                          indent_first_tw=0, mark_size_pt=1.0)


def set_para_top_border(p, color_hex: str, sz_eighths: int = 6,
                        ind_left_twips: int = 0, ind_right_twips: int = 0):
    pPr = p._p.get_or_add_pPr()
    if ind_left_twips or ind_right_twips:
        ind = get_or_add(pPr, "w:ind")
        if ind_left_twips:
            ind.set(qn("w:left"), str(ind_left_twips))
        if ind_right_twips:
            ind.set(qn("w:right"), str(ind_right_twips))
    pBdr = get_or_add(pPr, "w:pBdr")
    top = get_or_add(pBdr, "w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), str(sz_eighths))
    top.set(qn("w:space"), "1")
    top.set(qn("w:color"), color_hex)
    sort_xml_children(pPr, PPR_SEQ)


def set_para_box_border(p, color_hex: str, sz_eighths: int = 8, space_pt: int = 6,
                        ind_lr_mm: float = 5.0):
    pPr = p._p.get_or_add_pPr()
    tw = int(Mm(ind_lr_mm).twips)
    ind = get_or_add(pPr, "w:ind")
    ind.set(qn("w:left"), str(tw))
    ind.set(qn("w:right"), str(tw))
    pBdr = get_or_add(pPr, "w:pBdr")
    for side in ("top", "left", "bottom", "right"):
        b = get_or_add(pBdr, f"w:{side}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(sz_eighths))
        b.set(qn("w:space"), str(space_pt))
        b.set(qn("w:color"), color_hex)
    sort_xml_children(pPr, PPR_SEQ)


def apply_run_style(run, size_pt: float, color_hex: str, bold: bool = False,
                    italic: bool = False, font_name: str = "Amiri",
                    superscript: bool = False):
    """Populates <w:rPr> in strict ECMA-376 child sequence."""
    sz_half = str(int(round(size_pt * 2)))
    rPr = run._r.get_or_add_rPr()

    rFonts = OxmlElement("w:rFonts")
    for a in ("ascii", "hAnsi", "cs", "eastAsia"):
        rFonts.set(qn(f"w:{a}"), font_name)
    rPr.append(rFonts)

    if bold:
        rPr.append(OxmlElement("w:b"))
        rPr.append(OxmlElement("w:bCs"))
    if italic:
        rPr.append(OxmlElement("w:i"))
        rPr.append(OxmlElement("w:iCs"))

    c = OxmlElement("w:color")
    c.set(qn("w:val"), color_hex)
    rPr.append(c)

    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), sz_half)
    rPr.append(sz)

    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), sz_half)
    rPr.append(szCs)

    if superscript:
        va = OxmlElement("w:vertAlign")
        va.set(qn("w:val"), "superscript")
        rPr.append(va)

    rPr.append(OxmlElement("w:rtl"))
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "ar-SA")
    lang.set(qn("w:bidi"), "ar-SA")
    rPr.append(lang)
    return run


def add_run(p, text: str, size_pt: float, color_hex: str, bold: bool = False,
            italic: bool = False, font_name: str = "Amiri",
            superscript: bool = False):
    r = p.add_run(text)
    apply_run_style(r, size_pt, color_hex, bold=bold, italic=italic,
                    font_name=font_name, superscript=superscript)
    return r


def add_page_field(p, fallback_str: str, size_pt: float, color_hex: str, bold: bool = True):
    def make_fld(fld_type: str):
        r = p.add_run()
        apply_run_style(r, size_pt, color_hex, bold=bold)
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), fld_type)
        r._r.append(fc)

    make_fld("begin")
    r_instr = p.add_run()
    apply_run_style(r_instr, size_pt, color_hex, bold=bold)
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " PAGE "
    r_instr._r.append(it)
    make_fld("separate")
    add_run(p, fallback_str, size_pt, color_hex, bold=bold)
    make_fld("end")


class BookmarkGen:
    def __init__(self):
        self.counter = 0

    def add_bookmark(self, p, name: str):
        safe_name = name.replace("-", "_")
        bm_id = str(self.counter)
        self.counter += 1
        start = OxmlElement("w:bookmarkStart")
        start.set(qn("w:id"), bm_id)
        start.set(qn("w:name"), safe_name)
        end = OxmlElement("w:bookmarkEnd")
        end.set(qn("w:id"), bm_id)
        p._p.insert(0, start)
        p._p.append(end)


def add_hyperlink_run(p, anchor_name: str, text: str, size_pt: float,
                      color_hex: str, bold: bool = False, font_name: str = "Amiri"):
    hl = OxmlElement("w:hyperlink")
    hl.set(qn("w:anchor"), anchor_name.replace("-", "_"))
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for a in ("ascii", "hAnsi", "cs", "eastAsia"):
        rFonts.set(qn(f"w:{a}"), font_name)
    rPr.append(rFonts)
    if bold:
        rPr.append(OxmlElement("w:b"))
        rPr.append(OxmlElement("w:bCs"))
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color_hex)
    rPr.append(c)
    sz_half = str(int(round(size_pt * 2)))
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), sz_half)
    rPr.append(sz)
    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), sz_half)
    rPr.append(szCs)
    rPr.append(OxmlElement("w:rtl"))
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "ar-SA")
    lang.set(qn("w:bidi"), "ar-SA")
    rPr.append(lang)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    hl.append(r)
    p._p.append(hl)


def set_cell_width(cell, width_emu):
    cell.width = width_emu
    tcPr = cell._tc.get_or_add_tcPr()
    tcW = get_or_add(tcPr, "w:tcW")
    tcW.set(qn("w:w"), str(int(width_emu.twips)))
    tcW.set(qn("w:type"), "dxa")
    sort_xml_children(tcPr, TCPR_SEQ)


def set_table_rtl(table):
    tblPr = table._tbl.tblPr
    get_or_add(tblPr, "w:bidiVisual")
    sort_xml_children(tblPr, TBLPR_SEQ)


def set_cell_margins(cell, top_dxa=0, bottom_dxa=0, left_dxa=0, right_dxa=0):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = get_or_add(tcPr, "w:tcMar")
    for side, val in (("top", top_dxa), ("left", left_dxa), ("bottom", bottom_dxa), ("right", right_dxa)):
        el = get_or_add(tcMar, f"w:{side}")
        el.set(qn("w:w"), str(int(val)))
        el.set(qn("w:type"), "dxa")
    sort_xml_children(tcPr, TCPR_SEQ)


def set_cell_borders(cell, **sides):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = get_or_add(tcPr, "w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        if side in sides:
            val, sz, col = sides[side]
            el = get_or_add(tcBorders, f"w:{side}")
            el.set(qn("w:val"), val)
            if val not in ("nil", "none"):
                el.set(qn("w:sz"), str(sz))
                el.set(qn("w:space"), "0")
                el.set(qn("w:color"), col)
    sort_xml_children(tcPr, TCPR_SEQ)


def set_table_borders_none(table):
    tblPr = table._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    tblBorders = parse_xml(f'''
      <w:tblBorders {nsdecls("w")}>
        <w:top w:val="none"/><w:left w:val="none"/>
        <w:bottom w:val="none"/><w:right w:val="none"/>
        <w:insideH w:val="none"/><w:insideV w:val="none"/>
      </w:tblBorders>
    ''')
    tblPr.append(tblBorders)
    sort_xml_children(tblPr, TBLPR_SEQ)


def convert_inline_cover_to_full_bleed_anchor(drawing_el):
    """Converts <wp:inline> cover picture into full-bleed <wp:anchor> anchored at page (0, 0)."""
    inline = drawing_el.find(qn("wp:inline"))
    if inline is None:
        return
    extent = inline.find(qn("wp:extent"))
    docPr = inline.find(qn("wp:docPr"))
    graphic = inline.find(qn("a:graphic"))
    cx = extent.get("cx")
    cy = extent.get("cy")
    doc_id = docPr.get("id")
    doc_name = docPr.get("name")

    anchor = parse_xml(f'''
      <wp:anchor {nsdecls("wp", "a", "pic", "r")}
        distT="0" distB="0" distL="0" distR="0"
        simplePos="0" relativeHeight="251658240" behindDoc="1"
        locked="0" layoutInCell="1" allowOverlap="1">
        <wp:simplePos x="0" y="0"/>
        <wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>
        <wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>
        <wp:extent cx="{cx}" cy="{cy}"/>
        <wp:effectExtent l="0" t="0" r="0" b="0"/>
        <wp:wrapNone/>
        <wp:docPr id="{doc_id}" name="{doc_name}"/>
        <wp:cNvGraphicFramePr>
          <a:graphicFrameLocks noChangeAspect="1"/>
        </wp:cNvGraphicFramePr>
      </wp:anchor>
    ''')
    anchor.append(graphic)
    drawing_el.remove(inline)
    drawing_el.append(anchor)


def configure_running_header(hdr, center_title: str, side: str, start_pg_num: int, pal: dict):
    hdr.is_linked_to_previous = False
    for p in list(hdr.paragraphs):
        p._element.getparent().remove(p._element)
    tbl = hdr.add_table(rows=1, cols=3, width=Mm(125))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    set_table_rtl(tbl)
    set_table_borders_none(tbl)

    widths = [Mm(18), Mm(89), Mm(18)]
    row = tbl.rows[0]
    for idx, cell in enumerate(row.cells):
        set_cell_width(cell, widths[idx])
        set_cell_margins(cell, top_dxa=0, bottom_dxa=60, left_dxa=0, right_dxa=0)
        set_cell_borders(cell, bottom=("single", 5, pal["rule_ink"]))

    p_r = row.cells[0].paragraphs[0]
    set_para_rtl(p_r, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=13.5, sb_pt=0, sa_pt=0)
    if side == "right":
        add_page_field(p_r, to_e(start_pg_num), 10.5, pal["accent"], bold=True)

    p_c = row.cells[1].paragraphs[0]
    set_para_rtl(p_c, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=13.5, sb_pt=0, sa_pt=0)
    add_run(p_c, center_title, 10.5, pal["ink"], bold=False)

    p_l = row.cells[2].paragraphs[0]
    set_para_rtl(p_l, align=WD_ALIGN_PARAGRAPH.LEFT, line_pt=13.5, sb_pt=0, sa_pt=0)
    if side == "left":
        add_page_field(p_l, to_e(start_pg_num), 10.5, pal["accent"], bold=True)


def set_section_page_start(section, start_num: int):
    sectPr = section._sectPr
    for old in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(old)
    el = OxmlElement("w:pgNumType")
    el.set(qn("w:start"), str(start_num))
    el.set(qn("w:fmt"), "decimal")
    sectPr.append(el)
    sort_xml_children(sectPr, SECTPR_SEQ)


def configure_page_size(section, top_mm, bottom_mm, left_mm, right_mm,
                        hdr_mm=10.0, ftr_mm=8.0, rtl_section=True):
    section.page_width = Mm(162)
    section.page_height = Mm(234)
    section.top_margin = Mm(top_mm)
    section.bottom_margin = Mm(bottom_mm)
    section.left_margin = Mm(left_mm)
    section.right_margin = Mm(right_mm)
    section.header_distance = Mm(hdr_mm)
    section.footer_distance = Mm(ftr_mm)
    section.different_first_page_header_footer = False
    sectPr = section._sectPr
    if rtl_section:
        get_or_add(sectPr, "w:bidi")
    sort_xml_children(sectPr, SECTPR_SEQ)


def render_inline_html_runs(p, el, base_size_pt: float, pal: dict, is_matn: bool = False):
    def walk(node, bold=False, font_name="Amiri", color_hex=None, superscript=False):
        if color_hex is None:
            color_hex = pal["matn_ink"] if is_matn else pal["ink"]
        if node.text:
            add_run(p, node.text, base_size_pt, color_hex, bold=bold,
                    font_name=font_name, superscript=superscript)
        for ch in node:
            tag = ch.tag.lower() if isinstance(ch.tag, str) else ""
            cls = (ch.get("class") or "").split()
            ch_bold = bold or (tag in ("strong", "b"))
            ch_font = font_name
            ch_col = color_hex
            ch_sup = superscript or (tag == "sup" or "fn-ref" in cls)
            if "ayah" in cls:
                ch_font = "Amiri Quran"
                ch_col = pal["ayah_ink"]
            elif "fn-ref" in cls or tag == "sup":
                ch_col = pal["fn_num_ink"]
                ch_bold = True
            elif tag in ("strong", "b"):
                ch_col = pal["strong_ink"] if not is_matn else pal["matn_ink"]
            walk(ch, bold=ch_bold, font_name=ch_font, color_hex=ch_col, superscript=ch_sup)
            if ch.tail:
                add_run(p, ch.tail, base_size_pt, color_hex, bold=bold,
                        font_name=font_name, superscript=superscript)

    walk(el)


def build_framed_table(doc, pal: dict, height_mm: float = 204.0):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    set_table_rtl(tbl)
    tblPr = tbl._tbl.tblPr
    tblW = get_or_add(tblPr, "w:tblW")
    tblW.set(qn("w:w"), str(int(Mm(134).twips)))
    tblW.set(qn("w:type"), "dxa")
    sort_xml_children(tblPr, TBLPR_SEQ)

    row = tbl.rows[0]
    trPr = row._tr.get_or_add_trPr()
    trH = get_or_add(trPr, "w:trHeight")
    trH.set(qn("w:val"), str(int(Mm(height_mm).twips)))
    trH.set(qn("w:hRule"), "exact")

    cell = row.cells[0]
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    set_cell_width(cell, Mm(134))
    set_cell_margins(cell, top_dxa=340, bottom_dxa=340, left_dxa=480, right_dxa=480)
    set_cell_borders(
        cell,
        top=("thickThinSmallGap", 18, pal["accent"]),
        left=("thickThinSmallGap", 18, pal["accent"]),
        bottom=("thickThinSmallGap", 18, pal["accent"]),
        right=("thickThinSmallGap", 18, pal["accent"]),
    )
    return cell


def build_docx(edition: str):
    in_html = ASSETS_HTML[edition]
    out_docx = OUT_PATHS[edition]
    pal = get_palette(edition)

    raw_html = open(in_html, encoding="utf-8").read()
    tree = lhtml.fromstring(raw_html)
    pages = tree.xpath('//div[@id="book-root"]/div[contains(concat(" ", normalize-space(@class), " "), " page ")]')
    total_pages = len(pages)
    print(f"[{edition}] Parsed {total_pages} DOM pages from {in_html}")

    doc = Document()

    # Global Normal style RTL Amiri
    norm = doc.styles["Normal"]
    norm.font.name = "Amiri"
    norm.font.size = Pt(11.0)
    norm.font.color.rgb = RGBColor.from_string(pal["ink"])
    npPr = norm.paragraph_format._element.get_or_add_pPr()
    get_or_add(npPr, "w:bidi")
    sort_xml_children(npPr, PPR_SEQ)
    nrPr = norm.font._element.get_or_add_rPr()
    rF = get_or_add(nrPr, "w:rFonts")
    for a in ("ascii", "hAnsi", "cs", "eastAsia"):
        rF.set(qn(f"w:{a}"), "Amiri")
    get_or_add(nrPr, "w:rtl")
    nlang = get_or_add(nrPr, "w:lang")
    nlang.set(qn("w:val"), "ar-SA")
    nlang.set(qn("w:bidi"), "ar-SA")

    doc.settings.odd_and_even_pages_header_footer = True
    sett = doc.settings.element
    if sett.find(qn("w:defaultTabStop")) is None:
        dt = OxmlElement("w:defaultTabStop")
        dt.set(qn("w:val"), "720")
        sett.append(dt)

    bm = BookmarkGen()

    # ==================== SECTION 0: pg-1 FRONT COVER ====================
    sec0 = doc.sections[0]
    configure_page_size(sec0, top_mm=0, bottom_mm=0, left_mm=0, right_mm=0, hdr_mm=0, ftr_mm=0)
    p_cov = doc.add_paragraph()
    set_para_rtl(p_cov, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=1.0, sb_pt=0, sa_pt=0, mark_size_pt=1.0)
    bm.add_bookmark(p_cov, "pg-1")
    r_cov = p_cov.add_run()
    r_cov.add_picture(COVER_IMG, width=Mm(162), height=Mm(234))
    drawing = r_cov._r.find(qn("w:drawing"))
    if drawing is not None:
        convert_inline_cover_to_full_bleed_anchor(drawing)

    # ==================== SECTION 1: pg-2..pg-4 FRAMED PLATES ====================
    sec1 = doc.add_section(WD_SECTION.NEW_PAGE)
    shrink_section_break_para(sec0)
    configure_page_size(sec1, top_mm=12.5, bottom_mm=12.5, left_mm=14.0, right_mm=14.0, hdr_mm=5.0, ftr_mm=5.0)
    sec1.header.is_linked_to_previous = False
    sec1.even_page_header.is_linked_to_previous = False

    # pg-2 Title Plate
    c2 = build_framed_table(doc, pal, height_mm=204.0)
    p = c2.paragraphs[0]
    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=36, sb_pt=12, sa_pt=2)
    bm.add_bookmark(p, "pg-2")
    add_run(p, "تَيْسِيرُ الانْتِفَاعِ\n", 23.0, pal["accent"], bold=True)
    add_run(p, "بِشَرْحِ\n", 16.5, pal["accent"], bold=False)
    add_run(p, "مُخْتَصَرِ أَبِي شُجَاعٍ", 24.0, pal["accent"], bold=True)

    p2 = c2.add_paragraph()
    set_para_rtl(p2, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=22, sb_pt=6, sa_pt=4)
    add_run(p2, "( الْمُسَمَّى بِـ « غَايَةِ الاِخْتِصَارِ وَالتَّقْرِيبِ » )", 13.5, pal["ink"])

    p3 = c2.add_paragraph()
    set_para_rtl(p3, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=28, sb_pt=4, sa_pt=20)
    add_run(p3, "التَّفْرِيغُ الْحَرْفِيُّ الْكَامِلُ لِدُرُوسِ شَرْحِ مَتْنِ أَبِي شُجَاعٍ", 16.5, pal["ink"], bold=True)

    p4 = c2.add_paragraph()
    set_para_rtl(p4, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=24, sb_pt=10, sa_pt=2)
    add_run(p4, "لِفَضِيلَةِ الشَّيْخِ ", 13.0, pal["ink"])
    add_run(p4, "أَحْمَدَ الْجَوْهَرِيِّ عَبْدِ الْجَوَادِ\n", 13.0, pal["accent"], bold=True)
    add_run(p4, "( حَفِظَهُ اللهُ تَعَالَى وَنَفَعَ بِعِلْمِهِ )", 10.5, pal["ink"])

    p5 = c2.add_paragraph()
    set_para_rtl(p5, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=20, sb_pt=8, sa_pt=24)
    set_para_top_border(p5, pal["rule_ink"], sz_eighths=4, ind_left_twips=360, ind_right_twips=360)
    add_run(p5, "وَالْمَتْنُ لِلْقَاضِي أَبِي شُجَاعٍ أَحْمَدَ بْنِ الْحُسَيْنِ الأَصْفَهَانِيِّ (٤٣٣ – ٥٩٣ هـ)", 11.0, pal["ink"])

    p6 = c2.add_paragraph()
    set_para_rtl(p6, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=18, sb_pt=14, sa_pt=0)
    add_run(p6, "كِتَابُ الطَّهَارَةِ وَكِتَابُ الصَّلاَةِ     •     ٢٥ لِقَاءً صَوْتِيًّا كَامِلاً", 10.5, pal["accent"], bold=True)

    # Page Break to pg-3
    p_brk3 = doc.add_paragraph()
    set_para_rtl(p_brk3, line_pt=1.0, sb_pt=0, sa_pt=0, page_break_before=True, mark_size_pt=2.0)

    # pg-3 Colophon Plate
    c3 = build_framed_table(doc, pal, height_mm=204.0)
    p = c3.paragraphs[0]
    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=24, sb_pt=2, sa_pt=6)
    bm.add_bookmark(p, "pg-3")
    add_run(p, "تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ\n", 14.5, pal["accent"], bold=True)
    add_run(p, "تَفْرِيغٌ حَرْفِيٌّ كَامِلٌ مُرَاجَعٌ لِدُرُوسِ السِّلْسِلَةِ الْفِقْهِيَّةِ الشَّافِعِيَّةِ\n", 11.0, pal["ink"])
    add_run(p, "( اللِّقَاءَاتُ : ١ – ٢٥ )", 10.5, pal["ink"])

    p_box = c3.add_paragraph()
    set_para_rtl(p_box, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=20.5, sb_pt=5, sa_pt=8)
    set_para_box_border(p_box, pal["accent"], sz_eighths=8, space_pt=7, ind_lr_mm=5.0)
    add_run(
        p_box,
        "أُعِدَّ هَذَا الْكِتَابُ بِإِثْبَاتِ كَلاَمِ الشَّيْخِ الشَّارِحِ كَامِلاً كَمَا أُلْقِيَ دُونَ حَذْفٍ أَوْ اخْتِصَارٍ ،\n"
        "مَعَ إِثْبَاتِ مَتْنِ أَبِي شُجَاعٍ مَضْبُوطاً بِالشَّكْلِ أَعْلَى الصَّفْحَةِ مَفْصُولاً بِخَطٍّ أُفُقِيٍّ عَنِ الشَّرْحِ أَسْفَلَهُ",
        11.5, pal["ink"], bold=True
    )

    p_src = c3.add_paragraph()
    set_para_rtl(p_src, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=17.5, sb_pt=6, sa_pt=5)
    set_para_top_border(p_src, pal["rule_ink"], sz_eighths=4, ind_left_twips=360, ind_right_twips=360)
    add_run(p_src, "مَنْهَجُ الحَوَاشِي وَتَفْسِيرِ غَرِيبِ الْمَتْنِ :\n", 10.0, pal["accent"], bold=True)
    add_run(
        p_src,
        "أُلْحِقَتْ بِالحَوَاشِي أَسْفَلَ الصَّفَحَاتِ مَعَانِي الأَلْفَاظِ الْغَرِيبَةِ وَبَعْضِ الْمُصْطَلَحَاتِ الَّتِي لَمْ يَتَعَرَّضْ الشَّيْخُ الشَّارِحُ لِبَيَانِهَا فِي مَوْضِعِهَا، مُنْتَقَاةً مِنْ رِسَالَةِ :\n",
        10.0, pal["ink"]
    )
    add_run(p_src, "«الأَنوَارُ عَلَى غَايَةِ الاِخْتِصَارِ» لِجَامِعِهِ عَبْدِ الرَّحْمَنِ مُحَمَّدٍ نُورِ الدِّينِ\n", 10.5, pal["accent"], bold=True)
    add_run(p_src, "بِتَرْقِيمٍ مُسْتَقِلٍّ لِكُلِّ صَفْحَةٍ يَبْدَأُ بِـ ", 10.0, pal["ink"])
    add_run(p_src, "(١)", 10.0, pal["accent"], bold=True)
    add_run(p_src, " دُونَ تَكْرَارٍ لِلْمَعْنَى فِي الصَّفْحَةِ الْوَاحِدَةِ.", 10.0, pal["ink"])

    p_sym = c3.add_paragraph()
    set_para_rtl(p_sym, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=17.5, sb_pt=5, sa_pt=8)
    add_run(p_sym, "رُمُوزُ الضَّبْطِ وَالتَّنْسِيقِ :\n", 10.0, pal["accent"], bold=True)
    add_run(p_sym, "الْخَطُّ الْعَرِيضُ دَاخِلَ الشَّرْحِ", 9.5, pal["strong_ink"], bold=True)
    add_run(p_sym, " يُمَيِّزُ أَلْفَاظَ الْمَتْنِ الَّتِي يَسْتَشْهِدُ بِهَا الشَّارِحُ\n", 9.5, pal["ink"])
    add_run(p_sym, "﴿ ... ﴾ لِلآيَاتِ الْقُرْآنِيَّةِ  •  « ... » لِلأَحَادِيثِ  •  (١) لِغَرِيبِ الْمَتْنِ  •  (*) لِبَيَانِ اللِّقَاءِ الصَّوْتِيِّ", 9.5, pal["ink"])

    p_cf = c3.add_paragraph()
    set_para_rtl(p_cf, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=17.5, sb_pt=6, sa_pt=0)
    set_para_top_border(p_cf, pal["rule_ink"], sz_eighths=5, ind_left_twips=480, ind_right_twips=480)
    add_run(p_cf, "تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ — لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ", 10.0, pal["accent"], bold=True)

    # Page Break to pg-4
    p_brk4 = doc.add_paragraph()
    set_para_rtl(p_brk4, line_pt=1.0, sb_pt=0, sa_pt=0, page_break_before=True, mark_size_pt=2.0)

    # pg-4 Basmalah Plate
    c4 = build_framed_table(doc, pal, height_mm=204.0)
    p = c4.paragraphs[0]
    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=48, sb_pt=0, sa_pt=8)
    bm.add_bookmark(p, "pg-4")
    add_run(p, "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ", 25.0, pal["accent"], font_name="Amiri Quran")
    p4b = c4.add_paragraph()
    set_para_rtl(p4b, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=16, sb_pt=4, sa_pt=0)
    add_run(p4b, "✽      ✽      ✽", 10.5, pal["accent"])

    # Identify index section boundaries
    ayah_start_pg = None
    toc_start_pg = None
    for pg in pages:
        pnum = int(pg.get("id").replace("pg-", ""))
        if pg.xpath('.//*[@id="ayah-list-box"]') and ayah_start_pg is None:
            ayah_start_pg = pnum
        if pg.xpath('.//*[contains(@class,"toc-two-col")]') and toc_start_pg is None:
            toc_start_pg = pnum

    body_end_pg = (ayah_start_pg - 1) if ayah_start_pg else total_pages
    ayah_end_pg = (toc_start_pg - 1) if (toc_start_pg and ayah_start_pg) else (total_pages if not toc_start_pg else ayah_start_pg)

    # ==================== SECTION 2: pg-5 .. body_end_pg BODY PAGES ====================
    sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
    shrink_section_break_para(sec1)
    configure_page_size(sec2, top_mm=21.2, bottom_mm=16.0, left_mm=18.5, right_mm=18.5, hdr_mm=13.0, ftr_mm=8.0)
    set_section_page_start(sec2, 5)
    configure_running_header(sec2.header, "لِفَضِيلَةِ الشَّيْخِ أَحْمَدَ الْجَوْهَرِيِّ", "left", 5, pal)
    configure_running_header(sec2.even_page_header, "« تَيْسِيرُ الانْتِفَاعِ بِشَرْحِ مُخْتَصَرِ أَبِي شُجَاعٍ »", "right", 6, pal)

    for pg in pages[4:]:
        pnum = int(pg.get("id").replace("pg-", ""))
        if pnum > body_end_pg:
            break
        first_para_of_page = (pnum > 5)

        bf = pg.xpath('.//*[contains(@class,"body-frame")]')[0]
        matn_zones = bf.xpath('./div[contains(@class,"matn-zone")]')
        sharh_zones = bf.xpath('./div[contains(@class,"sharh-zone")]')
        fn_areas = bf.xpath('./div[contains(@class,"footnote-area")]')

        placed_pg_bookmark = False
        attached_units = set()
        pending_unit_ids = [el.get("id") for el in bf.xpath('.//*[@id[starts-with(., "unit-")]]') if el.get("id")]

        def attach_page_bookmarks(para, explicit_uid=None):
            nonlocal placed_pg_bookmark
            if not placed_pg_bookmark:
                bm.add_bookmark(para, f"pg-{pnum}")
                for u_id in pending_unit_ids:
                    if u_id not in attached_units:
                        bm.add_bookmark(para, u_id)
                        attached_units.add(u_id)
                placed_pg_bookmark = True
            elif explicit_uid and explicit_uid not in attached_units:
                bm.add_bookmark(para, explicit_uid)
                attached_units.add(explicit_uid)

        if matn_zones:
            mz = matn_zones[0]
            for child in mz:
                cls = (child.get("class") or "").split()
                uid = child.get("id")
                if "matn-book-title" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=26.5,
                                 sb_pt=0, sa_pt=3.5, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, child.text_content().strip(), 17.0, pal["accent"], bold=True)
                elif "matn-bracket-title" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=21.5,
                                 sb_pt=0, sa_pt=3.5, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, child.text_content().strip(), 14.0, pal["accent"], bold=True)
                elif "matn-basmalah" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=26.5,
                                 sb_pt=1.0, sa_pt=2.5, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, child.text_content().strip(), 15.0, pal["matn_ink"], font_name="Amiri Quran")
                elif "matn-cont-dots" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=17.5,
                                 sb_pt=1.0, sa_pt=2.5, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, child.text_content().strip(), 13.0, pal["accent"])
                elif "matn-p" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_pt=23.8,
                                 sb_pt=0, sa_pt=1.0, indent_first_pt=16.5,
                                 page_break_before=first_para_of_page)
                    first_para_of_page = False
                    render_inline_html_runs(p, child, 13.0, pal, is_matn=True)
                elif "stars-row" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=12.0,
                                 sb_pt=1.0, sa_pt=2.0, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, "✽      ✽      ✽", 9.5, pal["accent"])
                else:
                    continue

                attach_page_bookmarks(p, uid)

            p_rule = doc.add_paragraph()
            set_para_rtl(p_rule, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=2.0, sb_pt=3.0, sa_pt=3.5, mark_size_pt=2.0)
            set_para_top_border(p_rule, pal["rule_ink"], sz_eighths=6)

        if sharh_zones:
            sz = sharh_zones[0]
            for child in sz:
                cls = (child.get("class") or "").split()
                uid = child.get("id")
                if "preface-h" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=26.5,
                                 sb_pt=2.0, sa_pt=6.0, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, child.text_content().strip(), 16.5, pal["accent"], bold=True)
                elif "sharh-p" in cls:
                    is_cont = ("cont" in cls)
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_pt=19.4,
                                 sb_pt=0, sa_pt=1.0, indent_first_pt=(0 if is_cont else 15.5),
                                 page_break_before=first_para_of_page)
                    first_para_of_page = False
                    render_inline_html_runs(p, child, 11.0, pal, is_matn=False)
                elif "stars-row" in cls:
                    p = doc.add_paragraph()
                    set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=12.0,
                                 sb_pt=2.0, sa_pt=1.0, page_break_before=first_para_of_page)
                    first_para_of_page = False
                    add_run(p, "✽      ✽      ✽", 9.5, pal["accent"])
                else:
                    continue

                attach_page_bookmarks(p, uid)

        # Page-level Bottom Footnotes
        if fn_areas and fn_areas[0].get("style", "") != "display:none;":
            fn_text_div = fn_areas[0].xpath('./div[contains(@class,"footnote-text")]')
            rows = fn_text_div[0].xpath('./div') if fn_text_div else []
            if rows:
                p_frule = doc.add_paragraph()
                set_para_rtl(p_frule, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=2.0, sb_pt=4.0, sa_pt=1.5, mark_size_pt=2.0)
                set_para_top_border(p_frule, pal["rule_ink"], sz_eighths=4, ind_left_twips=int(Mm(91).twips))

                for row_el in rows:
                    r_cls = (row_el.get("class") or "").split()
                    p_fn = doc.add_paragraph()
                    if "fn-lesson-note" in r_cls:
                        set_para_rtl(p_fn, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=12.2, sb_pt=0, sa_pt=0.5)
                        add_run(p_fn, row_el.text_content().strip(), 8.0, pal["subtle_ink"])
                    else:
                        set_para_rtl(p_fn, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=13.0, sb_pt=0, sa_pt=0.5)
                        num_el = row_el.xpath('./*[contains(@class,"fn-gloss-num")]')
                        term_el = row_el.xpath('./*[contains(@class,"fn-gloss-term")]')
                        if num_el:
                            add_run(p_fn, num_el[0].text_content().strip() + " ", 8.5, pal["fn_num_ink"], bold=True)
                        if term_el:
                            add_run(p_fn, term_el[0].text_content().strip(), 8.5, pal["ink"], bold=True)
                            rest_txt = (term_el[0].tail or "").strip()
                            if rest_txt:
                                add_run(p_fn, " " + rest_txt, 8.5, pal["ink"])
                        else:
                            add_run(p_fn, row_el.text_content().strip(), 8.5, pal["ink"])

        if not placed_pg_bookmark:
            p_anc = doc.add_paragraph()
            set_para_rtl(p_anc, line_pt=1.0, sb_pt=0, sa_pt=0, page_break_before=first_para_of_page, mark_size_pt=2.0)
            attach_page_bookmarks(p_anc)

    # ==================== SECTION 3: AYAH INDEX (pg-360..364) ====================
    if ayah_start_pg:
        sec3 = doc.add_section(WD_SECTION.NEW_PAGE)
        shrink_section_break_para(sec2)
        configure_page_size(sec3, top_mm=21.2, bottom_mm=16.0, left_mm=18.5, right_mm=18.5, hdr_mm=13.0, ftr_mm=8.0)
        set_section_page_start(sec3, ayah_start_pg)
        configure_running_header(sec3.header, "فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ", "left", ayah_start_pg, pal)
        configure_running_header(sec3.even_page_header, "فَهْرَسُ الآيَاتِ الْقُرْآنِيَّةِ", "right", ayah_start_pg, pal)

        for pg in pages[ayah_start_pg - 1:ayah_end_pg]:
            pnum = int(pg.get("id").replace("pg-", ""))
            first_of_ay = (pnum > ayah_start_pg)
            title_el = pg.xpath('.//*[contains(@class,"toc-page-title")]')[0]
            p_t = doc.add_paragraph()
            t_sz = 13.0 if "تَابِعُ" in title_el.text_content() else 16.5
            set_para_rtl(p_t, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=t_sz * 1.45,
                         sb_pt=1.0, sa_pt=4.0, page_break_before=first_of_ay)
            bm.add_bookmark(p_t, f"pg-{pnum}")
            add_run(p_t, title_el.text_content().strip(), t_sz, pal["accent"], bold=True)

            rows_el = pg.xpath('.//*[@id="ayah-list-box"]/div[contains(@class,"ayah-idx-row")]')
            tbl = doc.add_table(rows=1 + len(rows_el), cols=2)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = False
            set_table_rtl(tbl)
            set_table_borders_none(tbl)

            w_r, w_l = Mm(107), Mm(18)
            hrow = tbl.rows[0]
            for ci, (txt, al, wd) in enumerate((("الآيَةُ الْكَرِيمَةُ", WD_ALIGN_PARAGRAPH.RIGHT, w_r), ("الصَّفْحَةُ", WD_ALIGN_PARAGRAPH.LEFT, w_l))):
                c = hrow.cells[ci]
                set_cell_width(c, wd)
                set_cell_margins(c, top_dxa=20, bottom_dxa=40)
                set_cell_borders(c, bottom=("single", 5, pal["rule_ink"]))
                cp = c.paragraphs[0]
                set_para_rtl(cp, align=al, line_pt=14.0, sb_pt=0, sa_pt=0)
                add_run(cp, txt, 10.0, pal["accent"], bold=True)

            for idx, r_el in enumerate(rows_el, start=1):
                ay_txt = r_el.xpath('./*[contains(@class,"ayah-idx-text")]')[0].text_content().strip()
                a_links = r_el.xpath('./*[contains(@class,"ayah-idx-pages")]/a')
                trow = tbl.rows[idx]

                c0 = trow.cells[0]
                set_cell_width(c0, w_r)
                set_cell_margins(c0, top_dxa=35, bottom_dxa=35, left_dxa=60)
                set_cell_borders(c0, bottom=("single", 2, "CCCCCC"))
                cp0 = c0.paragraphs[0]
                set_para_rtl(cp0, align=WD_ALIGN_PARAGRAPH.RIGHT, line_pt=14.8, sb_pt=0, sa_pt=0)
                add_run(cp0, ay_txt, 9.5, pal["ink"], font_name="Amiri Quran")

                c1 = trow.cells[1]
                set_cell_width(c1, w_l)
                set_cell_margins(c1, top_dxa=35, bottom_dxa=35)
                set_cell_borders(c1, bottom=("single", 2, "CCCCCC"))
                cp1 = c1.paragraphs[0]
                set_para_rtl(cp1, align=WD_ALIGN_PARAGRAPH.LEFT, line_pt=14.8, sb_pt=0, sa_pt=0)
                for li, a in enumerate(a_links):
                    if li > 0:
                        add_run(cp1, " ، ", 9.5, pal["accent"], bold=True)
                    anc = (a.get("href") or "#")[1:]
                    add_hyperlink_run(cp1, anc, a.text_content().strip(), 9.5, pal["accent"], bold=True)

    # ==================== SECTION 4: GENERAL TOC (pg-365+) ====================
    if toc_start_pg:
        sec4 = doc.add_section(WD_SECTION.NEW_PAGE)
        shrink_section_break_para(sec3 if ayah_start_pg else sec2)
        configure_page_size(sec4, top_mm=21.2, bottom_mm=16.0, left_mm=18.5, right_mm=18.5, hdr_mm=13.0, ftr_mm=8.0)
        set_section_page_start(sec4, toc_start_pg)
        configure_running_header(sec4.header, "اَلْفَهْرَسُ الْعَامُّ", "left", toc_start_pg, pal)
        configure_running_header(sec4.even_page_header, "اَلْفَهْرَسُ الْعَامُّ", "right", toc_start_pg, pal)

        for pg in pages[toc_start_pg - 1:]:
            pnum = int(pg.get("id").replace("pg-", ""))
            first_of_toc = (pnum > toc_start_pg)
            title_el = pg.xpath('.//*[contains(@class,"toc-page-title")]')[0]
            p_t = doc.add_paragraph()
            set_para_rtl(p_t, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=24.0,
                         sb_pt=1.0, sa_pt=6.0, page_break_before=first_of_toc)
            bm.add_bookmark(p_t, f"pg-{pnum}")
            add_run(p_t, title_el.text_content().strip(), 16.5, pal["accent"], bold=True)

            col_r = pg.xpath('.//*[contains(@class,"toc-col-right")]')[0]
            col_l = pg.xpath('.//*[contains(@class,"toc-col-left")]')[0]

            tbl = doc.add_table(rows=1, cols=2)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = False
            set_table_rtl(tbl)
            set_table_borders_none(tbl)

            col_w = Mm(62.5)
            tab_pos_twips = int(Mm(57.2).twips)

            def fill_toc_col(cell, col_el, has_left_divider: bool):
                set_cell_width(cell, col_w)
                set_cell_margins(cell, top_dxa=0, bottom_dxa=0,
                                 left_dxa=(260 if has_left_divider else 0),
                                 right_dxa=(0 if has_left_divider else 260))
                if has_left_divider:
                    set_cell_borders(cell, left=("single", 5, pal["rule_ink"]))

                first = True
                for item in col_el:
                    cls = (item.get("class") or "").split()
                    p = cell.paragraphs[0] if first else cell.add_paragraph()
                    first = False
                    if "toc-section-center" in cls:
                        set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.CENTER, line_pt=15.0, sb_pt=4.0, sa_pt=1.5)
                        add_run(p, item.text_content().strip(), 10.5, pal["accent"], bold=True)
                    else:
                        is_book = ("toc-book-row" in cls)
                        set_para_rtl(p, align=WD_ALIGN_PARAGRAPH.RIGHT,
                                     line_pt=(13.5 if is_book else 12.6),
                                     sb_pt=(3.5 if is_book else 0.3),
                                     sa_pt=(1.0 if is_book else 0.3))
                        pPr = p._p.get_or_add_pPr()
                        tabs = get_or_add(pPr, "w:tabs")
                        tab = OxmlElement("w:tab")
                        tab.set(qn("w:val"), "right")
                        tab.set(qn("w:leader"), "dot")
                        tab.set(qn("w:pos"), str(tab_pos_twips))
                        tabs.append(tab)
                        sort_xml_children(pPr, PPR_SEQ)

                        a_tags = item.xpath('.//a')
                        if len(a_tags) >= 2:
                            lbl = a_tags[0].text_content().strip()
                            pg_txt = a_tags[-1].text_content().strip()
                            anc = (a_tags[0].get("href") or "#")[1:]
                            if is_book:
                                add_hyperlink_run(p, anc, "  " + lbl, 9.5, pal["accent"], bold=True)
                                add_run(p, "\t", 9.5, pal["accent"], bold=True)
                                add_hyperlink_run(p, anc, pg_txt, 9.0, pal["accent"], bold=True)
                            else:
                                add_hyperlink_run(p, anc, lbl, 8.5, pal["ink"], bold=False)
                                add_run(p, "\t", 8.5, pal["ink"])
                                add_hyperlink_run(p, anc, pg_txt, 8.5, pal["accent"], bold=True)

            fill_toc_col(tbl.rows[0].cells[0], col_r, has_left_divider=True)
            fill_toc_col(tbl.rows[0].cells[1], col_l, has_left_divider=False)

    # Ensure every section-break-holding paragraph in the document is minimal (1pt tall)
    for pPr in doc._body._body.xpath(".//w:p/w:pPr[w:sectPr]"):
        configure_ppr_rtl(
            pPr, align_val="right", line_pt=1.0, sb_tw=0, sa_tw=0,
            indent_first_tw=0, mark_size_pt=1.0
        )

    os.makedirs(os.path.dirname(out_docx), exist_ok=True)
    doc.save(out_docx)
    sz_mb = os.path.getsize(out_docx) / (1024 * 1024)
    print(f"[{edition}] Successfully saved editable Word DOCX: {out_docx} ({sz_mb:.2f} MB)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", choices=("classic", "two-color", "all"), default="all")
    args = parser.parse_args()
    editions = ("classic", "two-color") if args.edition == "all" else (args.edition,)
    for ed in editions:
        build_docx(ed)


if __name__ == "__main__":
    main()
