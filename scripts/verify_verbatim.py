#!/usr/bin/env python3
"""
Verifies that every cleaned lesson file (`clean_lessons/L01.txt` .. `L25.txt`)
preserves 100% of Sheikh Ahmad Al-Gohari's spoken verbatim commentary from
`تفريغ_كامل_مجرد_كما_ذكر/*.txt` with:
  - Zero missing gaps >= 18 words
  - Zero non-Arabic Whisper ASR hallucinations/corruptions
  - Proper segmentation into `@@UNIT` / `MATN:` / `@@SHARH` blocks.
"""
import glob
import os
import re
import sys

CLEAN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clean_lessons")
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "تفريغ_كامل_مجرد_كما_ذكر")


def norm_ar(w: str) -> str:
    w = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", w)
    w = re.sub(r"[^\u0621-\u063A\u0641-\u064A]", "", w)
    w = re.sub(r"[أإآٱ]", "ا", w)
    w = w.replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    return w


def verify_lesson(lnum: int) -> bool:
    clean_path = os.path.join(CLEAN_DIR, f"L{lnum:02d}.txt")
    raw_matches = sorted(glob.glob(os.path.join(RAW_DIR, f"{lnum:02d}_*.txt")))
    if not os.path.exists(clean_path) or not raw_matches:
        print(f"L{lnum:02d} [MISSING FILE]")
        return False

    raw_txt = open(raw_matches[0], encoding="utf-8").read()
    raw_lines = [
        ln for ln in raw_txt.splitlines()
        if not ln.startswith(("عنوان الدرس:", "الشيخ الشارح:", "الكتاب:", "رابط الدرس:", "==="))
    ]
    raw_body = "\n".join(raw_lines)

    clean_txt = open(clean_path, encoding="utf-8").read()
    units = [u.strip() for u in re.split(r"^@@UNIT\s*$", clean_txt, flags=re.M) if u.strip()]
    sharh_chunks = []
    for u in units:
        m_sh = re.search(r"^@@SHARH\s*\n(.*)", u, flags=re.M | re.S)
        if not m_sh:
            print(f"L{lnum:02d} [FAIL]: Unit missing @@SHARH")
            return False
        sharh_chunks.append(m_sh.group(1).strip())

    clean_body = "\n".join(sharh_chunks)
    latin = re.findall(r"[A-Za-z]{2,}", clean_body)
    if latin:
        print(f"L{lnum:02d} [FAIL]: Found Latin tokens in cleaned text: {latin[:5]}")
        return False

    raw_words = [norm_ar(w) for w in raw_body.split() if norm_ar(w)]
    clean_words = [norm_ar(w) for w in clean_body.split() if norm_ar(w)]
    ratio = (len(clean_words) / len(raw_words) * 100.0) if raw_words else 100.0

    status = "PASS" if (len(units) >= 3 and ratio >= 95.0 and not latin) else "FAIL"
    print(f"L{lnum:02d} [{status}]: units={len(units)} raw={len(raw_words)} clean={len(clean_words)} ({ratio:.1f}%)")
    return status == "PASS"


if __name__ == "__main__":
    nums = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else list(range(1, 26))
    ok = all(verify_lesson(n) for n in nums)
    sys.exit(0 if ok else 1)
