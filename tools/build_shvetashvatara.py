#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""শ্বেতাশ্বতর উপনিষদ ডেটা-নির্মাতা — assets/grantho/data/shvetashvatara/

উৎস ও নীতি (অনুমানভিত্তিক পাঠ বর্জন):
  ১. মূল সংস্কৃত পাঠ (দেবনাগরী): পাঁচ-সূত্র নিরীক্ষিত —
     rampsuthar1999-arch/smarana_v2 (ভিত্তি কাঠামো), संस्कृत विकिस्रोत
     (sa.wikisource.org), sanskritdocuments.org (shveta.itx),
     divine-books@0.5.0, ও ebanglalibrary.com-এর মূল পাঠ মিলিয়ে
     ছাপাখানা/OCR-ত্রুটি ও লুপ্ত পাদসমূহ সংশোধিত (৬ অধ্যায়, ১১৩ মন্ত্র)।
  ২. বাংলা সরলার্থ (`bn`): স্বামী লোকেশ্বরানন্দ — ebanglalibrary.com
     («শ্বেতাশ্বতর উপনিষদ», ১১৩/১১৩ মন্ত্র + শান্তিপাঠ, মঙ্গলাচরণ ও ভূমিকা)।
  ৩. ইংরেজি অনুবাদ (`en/ch1..6.json`): F. Max Müller — Sacred Books of the
     East, Vol. 15 (1884), ১১৩/১১৩ মন্ত্র (SBE ডায়াক্রিটিক মার্কআপ পরিষ্কার করা)।
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "grantho" / "data" / "shvetashvatara"
EN_DIR = OUT_DIR / "en"

SM_JSON = pathlib.Path(os.environ.get("SHV_SM_JSON", "/tmp/su_test/smarana_v2/shveta.json"))
EBL_JSON = pathlib.Path(os.environ.get("SHV_EBL_JSON", "/tmp/su_test/ebl_saralartha.json"))
ENM_JSON = pathlib.Path(os.environ.get("SHV_ENM_JSON", "/tmp/su_test/en_maxmuller_raw.json"))

EXPECTED_COUNTS = {1: 16, 2: 17, 3: 21, 4: 22, 5: 14, 6: 23}

CHAPTER_NAMES = {
    1: "প্রথম অধ্যায় · ব্রহ্মজিজ্ঞাসা",
    2: "দ্বিতীয় অধ্যায় · যোগাভ্যাস",
    3: "তৃতীয় অধ্যায় · রুদ্র ও পরমপুরুষ",
    4: "চতুর্থ অধ্যায় · মায়া ও জীবাত্মা",
    5: "পঞ্চম অধ্যায় · বিদ্যা ও অবিদ্যা",
    6: "ষষ্ঠ অধ্যায় · ঈশ্বর ও মুক্তি",
}

# পাঁচ-সূত্র নিরীক্ষিত সংস্কৃত সংশোধনী — smarana_v2-তে থাকা ৭টি লুপ্ত পাদ ও OCR/টাইপো ঠিক করা:
SANSKRIT_PATCHES = {
    (1, 1): (
        "ब्रह्मवादिनो वदन्ति ।\n"
        "किं कारणं ब्रह्म कुतः स्म जाता जीवाम केन क्व च सम्प्रतिष्ठा ।\n"
        "अधिष्ठिताः केन सुखेतरेषु वर्तामहे ब्रह्मविदो व्यवस्थाम् ॥"
    ),
    (1, 14): (
        "स्वदेहमरणिं कृत्वा प्रणवं चोत्तरारणिम् ।\n"
        "ध्याननिर्मथनाभ्यासाद्देवं पश्येन्निगूढवत् ॥"
    ),
    (1, 15): (
        "तिलेषु तैलं दधिनीव सर्पिरापः स्रोतःस्वरणीषु चाग्निः ।\n"
        "एवमात्माऽत्मनि गृह्यतेऽसौ सत्येनैनं तपसा योऽनुपश्यति ॥"
    ),
    (2, 10): (
        "समे शुचौ शर्करावह्निवालुकाविवर्जिते शब्दजलाश्रयादिभिः ।\n"
        "मनोनुकूले न तु चक्षुपीडने गुहानिवाताश्रयणे प्रयोजयेत् ॥"
    ),
    (2, 13): (
        "लघुत्वमारोग्यमलोलुपत्वं वर्णप्रसादं स्वरसौष्ठवं च ।\n"
        "गन्धः शुभो मूत्रपुरीषमल्पं योगप्रवृत्तिं प्रथमां वदन्ति ॥"
    ),
    (2, 15): (
        "यदात्मतत्त्वेन तु ब्रह्मतत्त्वं दीपोपमेनेह युक्तः प्रपश्येत् ।\n"
        "अजं ध्रुवं सर्वतत्त्वैर्विशुद्धं ज्ञात्वा देवं मुच्यते सर्वपाशैः ॥"
    ),
    (3, 4): (
        "यो देवानां प्रभवश्चोद्भवश्च विश्वाधिपो रुद्रो महर्षिः ।\n"
        "हिरण्यगर्भं जनयामास पूर्वं स नो बुद्ध्या शुभया संयुनक्तु ॥"
    ),
    (3, 6): (
        "यामिषुं गिरिशन्त हस्ते बिभर्ष्यस्तवे ।\n"
        "शिवां गिरित्र तां कुरु मा हिंसीः पुरुषं जगत् ॥"
    ),
    (3, 9): (
        "यस्मात् परं नापरमस्ति किञ्चिद्यस्मान्नाणीयो न ज्यायोऽस्ति कश्चित् ।\n"
        "वृक्ष इव स्तब्धो दिवि तिष्ठत्येकस्तेनेदं पूर्णं पुरुषेण सर्वम् ॥"
    ),
    (3, 10): (
        "ततो यदुत्तरतरं तदरूपमनामयम् ।\n"
        "य एतद्विदुरमृतास्ते भवन्त्यथेतरे दुःखमेवापियन्ति ॥"
    ),
    (3, 12): (
        "महान् प्रभुर्वै पुरुषः सत्त्वस्यैष प्रवर्तकः ।\n"
        "सुनिर्मलामिमां प्राप्तिमीशानो ज्योतिरव्ययः ॥"
    ),
    (3, 13): (
        "अङ्गुष्ठमात्रः पुरुषोऽन्तरात्मा सदा जनानां हृदये सन्निविष्टः ।\n"
        "हृदा मनीषा मनसाभिक्लृप्तो य एतद् विदुरमृतास्ते भवन्ति ॥"
    ),
    (4, 1): (
        "य एकोऽवर्णो बहुधा शक्तियोगाद् वर्णाननेकान् निहितार्थो दधाति ।\n"
        "विचैति चान्ते विश्वमादौ च देवः स नो बुद्ध्या शुभया संयुनक्तु ॥"
    ),
    (4, 10): (
        "मायां तु प्रकृतिं विद्यान्मायिनं च महेश्वरम् ।\n"
        "तस्यावयवभूतैस्तु व्याप्तं सर्वमिदं जगत् ॥"
    ),
    (4, 12): (
        "यो देवानां प्रभवश्चोद्भवश्च विश्वाधिपो रुद्रो महर्षिः ।\n"
        "हिरण्यगर्भं पश्यत जायमानं स नो बुद्ध्या शुभया संयुनक्तु ॥"
    ),
    (4, 14): (
        "सूक्ष्मातिसूक्ष्मं कलिलस्य मध्ये विश्वस्य स्रष्टारमनेकरूपम् ।\n"
        "विश्वस्यैकं परिवेष्टितारं ज्ञात्वा शिवं शान्तिमत्यन्तमेति ॥"
    ),
    (4, 16): (
        "घृतात् परं मण्डमिवातिसूक्ष्मं ज्ञात्वा शिवं सर्वभूतेषु गूढम् ।\n"
        "विश्वस्यैकं परिवेष्टितारं ज्ञात्वा देवं मुच्यते सर्वपाशैः ॥"
    ),
    (4, 17): (
        "एष देवो विश्वकर्मा महात्मा सदा जनानां हृदये सन्निविष्टः ।\n"
        "हृदा मनीषा मनसाभिक्लृप्तो य एतद् विदुरमृतास्ते भवन्ति ॥"
    ),
    (4, 18): (
        "यदाऽतमस्तन्न दिवा न रात्रिर्न सन्नचासच्छिव एव केवलः ।\n"
        "तदक्षरं तत् सवितुर्वरेण्यं प्रज्ञा च तस्मात् प्रसृता पुराणी ॥"
    ),
    (5, 3): (
        "एकैकं जालं बहुधा विकुर्वन्नस्मिन् क्षेत्रे संहरत्येष देवः ।\n"
        "भूयः सृष्ट्वा पतयस्तथेशः सर्वाधिपत्यं कुरुते महात्मा ॥"
    ),
    (5, 10): (
        "नैव स्त्री न पुमानेष न चैवायं नपुंसकः ।\n"
        "यद्यच्छरीरमादत्ते तेन तेन स युज्यते ॥"
    ),
    (5, 13): (
        "अनाद्यनन्तं कलिलस्य मध्ये विश्वस्य स्रष्टारमनेकरूपम् ।\n"
        "विश्वस्यैकं परिवेष्टितारं ज्ञात्वा देवं मुच्यते सर्वपाशैः ॥"
    ),
    (6, 3): (
        "तत्कर्म कृत्वा विनिवर्त्य भूयस्तत्त्वस्य तत्त्वेन समेत्य योगम् ।\n"
        "एकेन द्वाभ्यां त्रिभिरष्टभिर्वा कालेन चैवात्मगुणैश्च सूक्ष्मैः ॥"
    ),
    (6, 11): (
        "एको देवः सर्वभूतेषु गूढः सर्वव्यापी सर्वभूतान्तरात्मा ।\n"
        "कर्माध्यक्षः सर्वभूताधिवासः साक्षी चेता केवलो निर्गुणश्च ॥"
    ),
    (6, 19): (
        "निष्कलं निष्क्रियं शान्तं निरवद्यं निरञ्जनम् ।\n"
        "अमृतस्य परं सेतुं दग्धेन्धनमिवानलम् ॥"
    ),
    (6, 23): (
        "यस्य देवे परा भक्तिः यथा देवे तथा गुरौ ।\n"
        "तस्यैते कथिता ह्यर्थाः प्रकाशन्ते महात्मनः ॥\n"
        "प्रकाशन्ते महात्मनः ॥"
    ),
}

EN_REPS = [
    ("vi _g_ _ñ_ ânâtmâ", "vijñānātmā"),
    ("gu _n_ a", "guṇa"),
    ("Gu _n_ as", "Guṇas"),
    ("î _s_ a", "īśa"),
    ("î _s_ vara", "īśvara"),
    (" _g_ îva", "jīva"),
    ("pra _n_ ava", "praṇava"),
    ("Savit _ri_", "Savitṛ"),
    ("Hira _n_ yagarbha", "Hiraṇyagarbha"),
    ("_S_ iva", "Śiva"),
    (" _s_ akti", "śakti"),
    ("_K_ andramas", "Chandramas"),
    ("Pra _g_ âpati", "Prajāpati"),
    ("Virâ _g_", "Virāj"),
    ("an-î _s_ â", "an-īśā"),
    ("_Ri_ g-Veda", "Ṛg-Veda"),
    ("Prak _ri_ ti", "Prakṛti"),
    ("_S_ âṅkhya", "Sāṅkhya"),
    ("_S_ vetâ _s_ vatara", "Śvetāśvatara"),
    ("_Ri_ shis", "Ṛṣis"),
]
EN_MACRONS = str.maketrans({"â": "ā", "î": "ī", "û": "ū", "Â": "Ā", "Î": "Ī", "Û": "Ū"})


def clean_sk(s: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines)


def clean_bn(s: str) -> str:
    # অকারণে ঢুকে পড়া অসমীয়া 'ৰ' (U+09F0) বাংলা 'র'-তে স্বাভাবিক করা
    s = s.replace("\u09f0", "র")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(lines).strip()


def clean_en(s: str) -> str:
    s = re.sub(r"^\d+\.\s*", "", s.strip())
    for a, b in EN_REPS:
        s = s.replace(a, b)
    s = s.translate(EN_MACRONS)
    s = s.replace("with a thousand heads. a thousand eyes", "with a thousand heads, a thousand eyes")
    s = re.sub(r"\s*[,;]\s*--\s*", " — ", s)
    s = re.sub(r"\s*--\s*", " — ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_smarana_map(sm: dict) -> dict[tuple[int, int], str]:
    out = {}
    secs = sm["sec"]
    for si, (_name, start) in enumerate(secs):
        if si == 0:
            continue
        end = secs[si + 1][1] if si + 1 < len(secs) else len(sm["v"])
        for vi in range(start, end):
            item = sm["v"][vi]
            vn = int(item[0])
            out[(si, vn)] = "\n".join(item[1])
    return out


def build_preface(ebl: dict) -> tuple[str, str]:
    p = ebl["preface"]
    shanti_sk = (
        "ॐ सह नाववतु । सह नौ भुनक्तु । सह वीर्यं करवावहै ।\n"
        "तेजस्वि नावधीतमस्तु । मा विद्विषावहै ॥\n"
        "ॐ शान्तिः शान्तिः शान्तिः ॥"
    )
    mangal_sk = (
        "ॐ पूर्णमदः पूर्णमिदं पूर्णात् पूर्णमुदच्यते ।\n"
        "पूर्णस्य पूर्णमादाय पूर्णमेवावशिष्यते ॥\n"
        "ॐ शान्तिः शान्तिः शान्तिः ॥"
    )
    parts = [
        "শান্তিপাঠঃ\n" + shanti_sk + "\n" + clean_bn(p["shantipatha_bn"]),
        "মঙ্গলাচরণঃ\n" + mangal_sk + "\n" + clean_bn(p["mangalacharana_1_bn"]),
        "ভূমিকা (স্বামী লোকেশ্বরানন্দ)\n" + clean_bn(p["intro_bn"]),
    ]
    return "শান্তিপাঠ ও ভূমিকা", "\n\n".join(parts)


def main() -> int:
    for p in (SM_JSON, EBL_JSON, ENM_JSON):
        if not p.exists():
            raise SystemExit(f"উৎস-ফাইল নেই: {p}")

    sm = json.loads(SM_JSON.read_text(encoding="utf-8"))
    ebl = json.loads(EBL_JSON.read_text(encoding="utf-8"))
    enm = json.loads(ENM_JSON.read_text(encoding="utf-8"))

    sm_map = load_smarana_map(sm)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    heading, preface = build_preface(ebl)
    ch_metas = []
    total = 0

    for ch in range(1, 7):
        want_n = EXPECTED_COUNTS[ch]
        verses = []
        en_verses = {}

        for n in range(1, want_n + 1):
            sk = clean_sk(SANSKRIT_PATCHES.get((ch, n), sm_map[(ch, n)]))
            bn = clean_bn(ebl["chapters"][str(ch)][str(n)]["bn"])
            en = clean_en(enm[str(ch)][str(n)])

            assert sk and sk.endswith("॥"), f"{ch}.{n} sk invalid: {sk!r}"
            assert not re.search(r"[\u0980-\u09FF]", sk), f"{ch}.{n} Bengali leak in sk"
            assert bn and "\u09f0" not in bn, f"{ch}.{n} bn invalid"
            assert en and "_" not in en and not re.search(r"[âîûÂÎÛ]", en), f"{ch}.{n} en invalid: {en!r}"

            verses.append({"n": n, "sk": sk, "bn": bn})
            en_verses[str(n)] = en

        assert len(verses) == want_n
        total += want_n

        ch_obj = {
            "id": ch,
            "bn": CHAPTER_NAMES[ch],
            "count": want_n,
            "from": 1,
            "to": want_n,
            "withBn": want_n,
        }
        if ch == 1:
            ch_obj["heading"] = heading
            ch_obj["preface"] = preface
        ch_obj["verses"] = verses

        (OUT_DIR / f"ch{ch}.json").write_text(
            json.dumps(ch_obj, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        (EN_DIR / f"ch{ch}.json").write_text(
            json.dumps({"id": ch, "verses": en_verses}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        meta = {
            "id": ch,
            "bn": CHAPTER_NAMES[ch],
            "count": want_n,
            "from": 1,
            "to": want_n,
            "withBn": want_n,
            "aligned": want_n,
        }
        if ch == 1:
            meta["prefaceCount"] = 1
        ch_metas.append(meta)

    index_obj = {
        "slug": "shvetashvatara",
        "bn": "শ্বেতাশ্বতর উপনিষদ",
        "en": "Shvetashvatara Upanishad",
        "total": total,
        "withBn": total,
        "withSk": total,
        "withEn": total,
        "verseWord": "মন্ত্র",
        "chword": "অধ্যায়",
        "skSrc": "মূল সংস্কৃত পাঠ — পাঁচ-সূত্র নিরীক্ষিত (संस्कृत विकिस्रोत, sanskritdocuments.org, smarana_v2, divine-books ও ebanglalibrary.com)",
        "bnSrc": "বাংলা সরলার্থ — স্বামী লোকেশ্বরানন্দ (ebanglalibrary.com)",
        "enSrc": "ইংরেজি অনুবাদ — F. Max Müller (Sacred Books of the East, Vol. 15, 1884)",
        "note": "শুরুতে শান্তিপাঠ, মঙ্গলাচরণ ও ভূমিকা আলাদা ব্লকে (মন্ত্র-গণনার বাইরে) রাখা হয়েছে।",
        "chapters": ch_metas,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index_obj, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"✓ shvetashvatara: 6 অধ্যায়, {total} মন্ত্র (সংস্কৃত+বাংলা+ইংরেজি)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
