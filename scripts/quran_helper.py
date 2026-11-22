#!/usr/bin/env python3
"""
Quran Uthmani lookup & verification helper using quran_uthmani.json.
Normalizes Arabic text (handling Uthmani alef wasla, dagger alef, etc.)
to match any ayah or ayah slice reliably and return exact Uthmani Rasm + [السورة: الآية].
"""
import json
import os
import re

EASTERN = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

def to_eastern(n) -> str:
    return str(n).translate(EASTERN)

def norm_quran(s: str) -> str:
    # Remove basmalah prefix if attached, diacritics, small letters, pause marks
    s = s.replace("\u0671", "ا")  # alef wasla -> alef
    s = s.replace("\u0670", "ا")  # superscript alef (dagger alef) -> alef for imlaei matching? Wait: keep optional
    # Actually let's handle dagger alef specially in norm_imlaei
    s = re.sub(r"[\u064B-\u065F\u06D6-\u06ED\u0640]", "", s)
    s = re.sub(r"[أإآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^\u0621-\u064A ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def norm_uthmani_for_imlaei_match(s: str) -> str:
    # In Uthmani script: 'سَمَٰوَٰتِ' has dagger alef \u0670, 'أُنثَىٰ' has ى+\u0670, 'صَلَوٰةَ' has و+\u0670
    s = s.replace("\u0671", "ا")
    s = re.sub(r"و\u0670", "و", s)
    s = re.sub(r"ى\u0670", "ي", s)
    s = s.replace("\u0670", "ا")
    # Remove other diacritics and quranic marks
    s = re.sub(r"[\u064B-\u065F\u06D6-\u06ED\u0640]", "", s)
    s = re.sub(r"[أإآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[^\u0621-\u064A ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def clean_surah_name(name: str) -> str:
    # e.g. "سُورَةُ ٱلْفَاتِحَةِ" -> "الفاتحة"
    name = re.sub(r"^سُورَةُ\s+", "", name)
    name = name.replace("\u0671", "ا").replace("\u0670", "ا")
    name = re.sub(r"[\u064B-\u065F\u06D6-\u06ED\u0640]", "", name)
    # Clean specific Uthmani spellings in surah names
    repls = {
        "التغابن": "التغابن",
        "اال عمران": "آل عمران",
        "ال عمران": "آل عمران",
        "الااعراف": "الأعراف",
        "الاعراف": "الأعراف",
        "الانفال": "الأنفال",
        "الانعام": "الأنعام",
        "الانبياء": "الأنبياء",
        "الاسراء": "الإسراء",
        "الاخلاص": "الإخلاص",
        "الاحزاب": "الأحزاب",
        "الاحقاف": "الأحقاف",
        "الاعلى": "الأعلى",
        "الانسان": "الإنسان",
        "الانشقاق": "الانشقاق",
        "المومنين": "المؤمنون",
        "الشعراء": "الشعراء",
        "الجاثيه": "الجاثية",
        "السجده": "السجدة",
        "المائده": "المائدة",
        "المجادله": "المجادلة",
        "البقره": "البقرة",
        "التوبه": "التوبة",
        "النحل": "النحل",
        "الزمر": "الزمر",
        "الشوري": "الشورى",
        "الشورى": "الشورى",
        "غافر": "غافر",
        "الممتحنه": "الممتحنة",
        "المطففين": "المطففين",
        "القيامه": "القيامة",
        "النبإ": "النبأ",
        "النبا": "النبأ",
        "طه": "طه",
    }
    return repls.get(name, name)

SURAH_NAMES = {
    1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
    6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
    11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
    16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
    21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
    26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
    31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
    36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
    41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
    46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
    51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
    56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
    61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
    66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
    71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
    76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
    81: "التكوير", 82: "الانفطار", 83: "المطففين", 84: "الانشقاق", 85: "البروج",
    86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
    91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
    96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
    101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
    106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
    111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس",
}

class QuranIndex:
    def __init__(self, json_path="/home/antigravity/wasitiyyah/quran_uthmani.json"):
        raw = json.load(open(json_path, encoding="utf-8"))["data"]["surahs"]
        self.surahs = {}
        self.ayahs = []  # list of dicts
        for s in raw:
            snum = s["number"]
            sname = SURAH_NAMES[snum]
            self.surahs[snum] = []
            for a in s["ayahs"]:
                txt = a["text"]
                # Strip leading Basmalah on ayah 1 except Fatiha (1:1) and Naml (27:30)
                if snum not in (1, 9) and a["numberInSurah"] == 1:
                    bsm = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ "
                    if txt.startswith(bsm):
                        txt = txt[len(bsm):]
                entry = {
                    "s": snum,
                    "a": a["numberInSurah"],
                    "name": sname,
                    "uthmani": txt.strip(),
                    "norm": norm_uthmani_for_imlaei_match(txt),
                    "norm_no_alef": norm_quran(txt),
                }
                self.surahs[snum].append(entry)
                self.ayahs.append(entry)

    def get(self, snum: int, a_start: int, a_end: int = None, ref: bool = True) -> str:
        if a_end is None:
            a_end = a_start
        parts = [self.surahs[snum][i - 1]["uthmani"] for i in range(a_start, a_end + 1)]
        # Strip trailing/internal sajdah/hizb symbols if unwanted, or keep clean
        joined = " ".join(p.replace("۞", "").replace("۩", "").strip() for p in parts)
        joined = re.sub(r"\s+", " ", joined).strip()
        if ref:
            if a_end > a_start:
                r = f"[{SURAH_NAMES[snum]}: {to_eastern(a_start)}-{to_eastern(a_end)}]"
            else:
                r = f"[{SURAH_NAMES[snum]}: {to_eastern(a_start)}]"
            return f"﴿{joined}﴾ {r}"
        return f"﴿{joined}﴾"

    def search(self, query_arabic: str, top_k: int = 5):
        q = norm_uthmani_for_imlaei_match(query_arabic)
        q2 = norm_quran(query_arabic)
        hits = []
        for e in self.ayahs:
            if q in e["norm"] or q2 in e["norm_no_alef"]:
                hits.append(e)
        return hits[:top_k]

if __name__ == "__main__":
    qi = QuranIndex()
    print("Loaded ayahs:", len(qi.ayahs))
    print("Test 42:11 ->", qi.get(42, 11))
    print("Test search 'ليس كمثله شيء' ->", [(h["s"], h["a"], h["uthmani"]) for h in qi.search("ليس كمثله شيء")])
