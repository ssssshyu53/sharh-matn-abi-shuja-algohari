#!/usr/bin/env python3
"""
Curates unexplained gharib / technical Matn terms strictly from:
  «الأنوار على غاية الاختصار» لجامعه عبد الرحمن محمد نور الدين
only for words that Sheikh Ahmad Al-Gohari did NOT already explain in that unit's Sharh.

Outputs /home/antigravity/book_engine/glossary_data.json mapping each unit_id -> list of:
  { "id": str, "term": str, "pattern": str, "gloss": str }
where `pattern` matches the exact vocalized target word/phrase inside `u['matn_lines']`.
"""
import json
import os
import re

SOURCE_CREDIT = "«الأَنوَارُ عَلَى غَايَةِ الاِخْتِصَارِ» لِجَامِعِهِ عَبْدِ الرَّحْمَنِ مُحَمَّدٍ نُورِ الدِّينِ"

CURATED_GLOSSES = [
    # L01_U02 — خطبة الكتاب (مقدمة القاضي أبي شجاع)
    {
        "unit_id": "L01_U02",
        "id": "g_aalihi",
        "term": "آلِهِ",
        "pattern": r"وَآلِهِ",
        "gloss": "آلِهِ: أقاربُه المؤمنون من بني هاشمٍ وبني المُطَّلِب.",
    },
    {
        "unit_id": "L01_U02",
        "id": "g_mukhtasaran",
        "term": "مُخْتَصَراً",
        "pattern": r"مُخْتَصَراً",
        "gloss": "مُخْتَصَراً: ما قلَّ لفظُه وكثُرَ معناهُ.",
    },
    {
        "unit_id": "L01_U02",
        "id": "g_fiqh",
        "term": "الْفِقْهِ",
        "pattern": r"الْفِقْهِ",
        "gloss": "الْفِقْهِ: العلمُ بالأحكامِ الشرعيةِ العمليةِ المكتسَبُ من أدلتِها التفصيليةِ.",
    },
    {
        "unit_id": "L01_U02",
        "id": "g_hasr",
        "term": "حَصْرِ",
        "pattern": r"وَحَصْرِ",
        "gloss": "حَصْرِ: ضَبطٍ وعَدٍّ.",
    },
    {
        "unit_id": "L01_U02",
        "id": "g_khisal",
        "term": "الْخِصَالِ",
        "pattern": r"الْخِصَالِ",
        "gloss": "الْخِصَالِ: المرادُ بيانُ وعَدُّ الأركانِ والشروطِ والمندوباتِ.",
    },

    # L01_U07 — الماء المتغير بمخالط طاهر
    {
        "unit_id": "L01_U07",
        "id": "g_khalatahu",
        "term": "خَالَطَهُ",
        "pattern": r"خَالَطَهُ",
        "gloss": "خَالَطَهُ: أي ذابَ فيه، بخلافِ المُجاوِرِ: فهو ما لا يذوبُ فيه.",
    },

    # L04_U07 — تخليل اللحية الكثة
    {
        "unit_id": "L04_U07",
        "id": "g_kaththa",
        "term": "الْكَثَّةِ",
        "pattern": r"الْكَثَّةِ",
        "gloss": "الْكَثَّةِ: أي الكثيفةُ، وهي التي لا تُرى البشرةُ من تحتها في مجلسِ التخاطُبِ.",
    },

    # L09_U01 — المسح على الخفين
    {
        "unit_id": "L09_U01",
        "id": "g_khuffayn",
        "term": "الْخُفَّيْنِ",
        "pattern": r"الْخُفَّيْنِ",
        "gloss": "الْخُفَّينِ: ما يُلبَسُ في الرِّجلِ من جِلدٍ رقيقٍ، ويكونُ ساتراً للقدمِ والكعبينِ.",
    },

    # L10_U01 — إعواز الماء في التيمم
    {
        "unit_id": "L10_U01",
        "id": "g_iwazuhu",
        "term": "إِعْوَازُهُ",
        "pattern": r"وَإِعْوَازُهُ",
        "gloss": "إِعْوَازُهُ: احتياجُه للماءِ، أو عدمُ القدرةِ على تحصيلِه.",
    },

    # L11_U04 — القيح وما لا نفس له سائلة
    {
        "unit_id": "L11_U04",
        "id": "g_qayh",
        "term": "الْقَيْحِ",
        "pattern": r"وَالْقَيْحِ",
        "gloss": "الْقَيْحِ: الصَّديدُ.",
    },
    {
        "unit_id": "L11_U04",
        "id": "g_nafs_saila",
        "term": "مَا لاَ نَفْسَ لَهُ سَائِلَةٌ",
        "pattern": r"مَا لاَ نَفْسَ لَهُ سَائِلَةٌ",
        "gloss": "مَا لاَ نَفْسَ لَهُ سَائِلَةٌ: الذي ليسَ له دَمٌ سائلٌ؛ كالحشراتِ ونحوِها.",
    },

    # L11_U07 — ولوغ وسائر
    {
        "unit_id": "L11_U07",
        "id": "g_wulugh",
        "term": "وُلُوغِ",
        "pattern": r"وُلُوغِ",
        "gloss": "وُلُوغِ: الشُّربُ بطَرَفِ اللِّسانِ.",
    },
    {
        "unit_id": "L11_U07",
        "id": "g_sair",
        "term": "سَائِرِ",
        "pattern": r"سَائِرِ",
        "gloss": "سَائِرِ: بَاقِي.",
    },

    # L13_U04 — الشفق الأحمر
    {
        "unit_id": "L13_U04",
        "id": "g_shafaq_ahmar",
        "term": "الشَّفَقُ الأَحْمَرُ",
        "pattern": r"الشَّفَقُ الأَحْمَرُ",
        "gloss": "الشَّفَقُ الأَحْمَرُ: الحُمرةُ التي تظهرُ في الأُفقِ بعد الغروبِ متبقِّيةً من آثارِ ضوءِ الشمسِ.",
    },

    # L14_U06 — نوافل مؤكدات
    {
        "unit_id": "L14_U06",
        "id": "g_nawafil_muakkadat",
        "term": "نَوَافِلَ مُؤَكَّدَاتٌ",
        "pattern": r"نَوَافِلَ مُؤَكَّدَاتٌ",
        "gloss": "نَوَافِلَ مُؤَكَّدَاتٌ: صلواتٌ مستحبةٌ غيرُ تابعةٍ للفرائضِ، وهي دونَ المسنونةِ والرَّواتبِ.",
    },

    # L16_U02 — تكبيرة الإحرام
    {
        "unit_id": "L16_U02",
        "id": "g_ihram",
        "term": "الإِحْرَامِ",
        "pattern": r"الإِحْرَامِ",
        "gloss": "الإِحْرَامِ: سُمِّيت به لأنه يَحرُمُ بها ما كانَ مُباحاً قبل الدخولِ في الصَّلاةِ.",
    },

    # L19_U02 — ينوب عنه، بنى عليه
    {
        "unit_id": "L19_U02",
        "id": "g_yanubu",
        "term": "يَنُوبُ عَنْهُ",
        "pattern": r"يَنُوبُ عَنْهُ",
        "gloss": "يَنُوبُ عَنْهُ: يقومُ مَقامَهُ.",
    },
    {
        "unit_id": "L19_U02",
        "id": "g_bana_alayhi",
        "term": "بَنَى عَلَيْهِ",
        "pattern": r"وَبَنَى عَلَيْهِ",
        "gloss": "بَنَى عَلَيْهِ: أتمَّ صلاتَه عليهِ ولم يُعِدْها.",
    },

    # L19_U03 — التلبس بالفرض
    {
        "unit_id": "L19_U03",
        "id": "g_talabbus",
        "term": "التَّلَبُّسِ",
        "pattern": r"التَّلَبُّسِ",
        "gloss": "التَّلَبُّسِ: الشُّروعُ والدُّخولُ في فِعلِه.",
    },

    # L22_U02 — مصراً أو قرية
    {
        "unit_id": "L22_U02",
        "id": "g_misran",
        "term": "مِصْراً",
        "pattern": r"مِصْراً",
        "gloss": "مِصْراً: البلدُ التي فيها قاضٍ وأميرٌ وشُرطيٌّ وسوقٌ، والقريةُ: ما خَلا عن ذلك.",
    },

    # L24_U05 — دعاء الاستسقاء (ما لم يشرحه الشيخ في الدرس)
    {
        "unit_id": "L24_U05",
        "id": "g_akam",
        "term": "الآكَامِ",
        "pattern": r"وَالآكَامِ",
        "gloss": "الآكَامِ: التُّرابُ المجتمِعُ أو الهَضَباتُ الضَّخمةُ.",
    },
    {
        "unit_id": "L24_U05",
        "id": "g_haniian",
        "term": "هَنِيئاً",
        "pattern": r"هَنِيئاً",
        "gloss": "هَنِيئاً: طيِّباً لا ينغِّصُه شيءٌ.",
    },
    {
        "unit_id": "L24_U05",
        "id": "g_mariian",
        "term": "مَرِيئاً",
        "pattern": r"مَرِيئاً",
        "gloss": "مَرِيئاً: مُنمِياً ومحمودَ العاقبةِ.",
    },
    {
        "unit_id": "L24_U05",
        "id": "g_adirra",
        "term": "أَدِرَّ",
        "pattern": r"وَأَدِرَّ",
        "gloss": "أَدِرَّ: أكثِرْ وأجرِ.",
    },
    {
        "unit_id": "L24_U05",
        "id": "g_darr",
        "term": "الضَّرْعَ",
        "pattern": r"الضَّرْعَ",
        "gloss": "الضَّرْعَ: المرادُ كثرةُ لبنِ الأنعامِ، كنايةً عن الخِصبِ والرَّخاءِ.",
    },

    # L25_U05 — دعاء صلاة الجنازة (ما لم يفسره الشيخ في الدرس)
    {
        "unit_id": "L25_U05",
        "id": "g_rawh",
        "term": "رَوْحِ",
        "pattern": r"رَوْحِ",
        "gloss": "رَوْحِ: اتِّساعٍ وطِيبٍ.",
    },
    {
        "unit_id": "L25_U05",
        "id": "g_nazala_bika",
        "term": "نَزَلَ بِكَ",
        "pattern": r"نَزَلَ بِكَ",
        "gloss": "نَزَلَ بِكَ: حلَّ ضيفاً عليكَ.",
    },
    {
        "unit_id": "L25_U05",
        "id": "g_raghibin",
        "term": "رَاغِبِينَ إِلَيْكَ",
        "pattern": r"رَاغِبِينَ إِلَيْكَ",
        "gloss": "رَاغِبِينَ إِلَيْكَ: مُبتَهلينَ ومُتضرِّعينَ إليكَ.",
    },
    {
        "unit_id": "L25_U05",
        "id": "g_laqqihi",
        "term": "لَقِّهِ",
        "pattern": r"وَلَقِّهِ",
        "gloss": "لَقِّهِ: أعطِه وأنعِمْ عليهِ.",
    },
    {
        "unit_id": "L25_U05",
        "id": "g_qihi",
        "term": "قِهِ",
        "pattern": r"وَقِهِ",
        "gloss": "قِهِ: اجعَلْ له وِقايةً.",
    },
    {
        "unit_id": "L25_U05",
        "id": "g_jafi",
        "term": "جَافِ",
        "pattern": r"وَجَافِ",
        "gloss": "جَافِ: باعِدْ.",
    },
]


def main():
    eng = os.path.dirname(os.path.abspath(__file__))
    book_data = json.load(open(os.path.join(eng, "book_data.json"), encoding="utf-8"))
    umap = {u["id"]: u for u in book_data["units"]}

    by_unit = {}
    for entry in CURATED_GLOSSES:
        uid = entry["unit_id"]
        assert uid in umap, f"Unknown unit_id: {uid}"
        u = umap[uid]
        matn_joined = "\n".join(u["matn_lines"])
        # Ensure pattern matches uniquely at least once inside matn_lines
        # Careful: in L19_U02 "عَنْهُ" could match "يَنُوبُ عَنْهُ" — let's require exact phrase "يَنُوبُ عَنْهُ" when ambiguous!
        m = re.search(entry["pattern"], matn_joined)
        assert m, f"Pattern {entry['pattern']} did NOT match Matn of {uid}:\n{matn_joined}"
        by_unit.setdefault(uid, []).append({
            "id": entry["id"],
            "term": entry["term"],
            "pattern": entry["pattern"],
            "gloss": entry["gloss"],
        })

    # Verify strict pattern specificity on L19_U02
    assert "يَنُوبُ عَنْهُ" in umap["L19_U02"]["matn_raw"]
    out_obj = {
        "source_credit": SOURCE_CREDIT,
        "count": len(CURATED_GLOSSES),
        "units_covered": len(by_unit),
        "by_unit": by_unit,
    }
    out_path = os.path.join(eng, "glossary_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}: {len(CURATED_GLOSSES)} curated glosses across {len(by_unit)} units.")


if __name__ == "__main__":
    main()
