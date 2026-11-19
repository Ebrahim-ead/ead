#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""বৃহদারণ্যক উপনিষদ ডেটা-নির্মাতা — assets/grantho/data/brihadaranyaka/

উৎস ও নীতি (অনুমানভিত্তিক পাঠ বর্জন):
  ১. মূল সংস্কৃত পাঠ (কাণ্ব শাখা, দেবনাগরী): বহুমূল নিরীক্ষিত —
     sa_bu_viswara.txt, GRETIL (Limaye & Vadekar) ও dharma-granth
     দেবনাগরী পাঠ মিলিয়ে অধ্যায়সমাপ্তি কোলফন ও মুদ্রণ-দ্বিরুক্তি সংশোধিত
     (৬ অধ্যায়, ৪৭ ব্রাহ্মণ, ৪৩৫ মন্ত্র)।
  ২. বাংলা সরলার্থ (`bn`): স্বামী গম্ভীরানন্দ — «উপনিষদ গ্রন্থাবলী (তৃতীয় ভাগ):
     বৃহদারণ্যকোপনিষদ্‌» (উদ্বোধন কার্যালয়), ৪৩৫/৪৩৫ মন্ত্র + শান্তিপাঠ ও ভূমিকা
     (যে ১০-১২টি ৬.৪ মন্ত্রে উদ্বোধন সংস্করণে পৃথক সরলার্থ স্থলে কেবল বাংলা অন্বয়ার্থ
     রয়েছে, সেগুলোতে স্বয়ং স্বামী গম্ভীরানন্দের বাংলা অন্বয়ার্থ অনুসৃত)।
  ৩. ইংরেজি অনুবাদ (`en/ch1..6.json`): F. Max Müller — Sacred Books of the
     East, Vol. 15 (1884) ৪৬/৪৭ ব্রাহ্মণ (৪০৭ মন্ত্র) + Robert E. Hume —
     The Thirteen Principal Upanishads (1921) VI.4 ব্রাহ্মণ (২৮ মন্ত্র) = ৪৩৫/৪৩৫।
"""
from __future__ import annotations

import html as htmllib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "grantho" / "data" / "brihadaranyaka"
EN_DIR = OUT_DIR / "en"

DG_BU_JSON = pathlib.Path(os.environ.get("BU_DG_JSON", "/tmp/dg/public/data/scriptures-full/brihadaranyaka.json"))
SBE_DIR = pathlib.Path(os.environ.get("BU_SBE_DIR", "/tmp/dg/scripts/cache/brihadaranyaka-sbe"))
RAW_DIR = pathlib.Path(os.environ.get("BU_RAW_DIR", "/tmp/upanishads/raw"))
BN_TXT = RAW_DIR / "brihad_bn_gambh.txt"
HUME_TXT = RAW_DIR / "brihad_vi4_hume_en.txt"
PRE_TXT = RAW_DIR / "brihad_preface_bn.txt"

CHAPTER_NAMES = {
    1: "প্রথম অধ্যায় · মধুকাণ্ড (অশ্বমেধ ও উদ্‌গীথ)",
    2: "দ্বিতীয় অধ্যায় · মধুকাণ্ড (অজাতশত্রু ও মধুবিদ্যা)",
    3: "তৃতীয় অধ্যায় · যাজ্ঞবল্ক্যকাণ্ড (জনকসভার বিচার)",
    4: "চতুর্থ অধ্যায় · যাজ্ঞবল্ক্যকাণ্ড (জ্যোতি ও মৈত্রেয়ী-নিগমন)",
    5: "পঞ্চম অধ্যায় · খিলকাণ্ড (পূর্ণমদঃ, দম-দান-দয়া ও গায়ত্রী)",
    6: "ষষ্ঠ অধ্যায় · খিলকাণ্ড (প্রাণ-সংবাদ, পঞ্চাগ্নি ও বংশ)",
}

BRAHMANA_TITLES = {
    (1, 1): "প্রথম ব্রাহ্মণ · অশ্বমেধ-উপাসনা",
    (1, 2): "দ্বিতীয় ব্রাহ্মণ · বিরাট্‌ ও কালসৃষ্টি",
    (1, 3): "তৃতীয় ব্রাহ্মণ · উদ্‌গীথ-প্রকরণ ও প্রাণোপাসনা",
    (1, 4): "চতুর্থ ব্রাহ্মণ · প্রজাপতির সৃষ্টি ও «অহং ব্রহ্মাস্মি»",
    (1, 5): "পঞ্চম ব্রাহ্মণ · সপ্তান্ন-প্রকরণ ও প্রাণব্রত",
    (1, 6): "ষষ্ঠ ব্রাহ্মণ · নাম-রূপ-কর্ম ও ব্রহ্মস্বরূপ",
    (2, 1): "প্রথম ব্রাহ্মণ · গার্গ্য-অজাতশত্রু সংবাদ ও সত্যের সত্য",
    (2, 2): "দ্বিতীয় ব্রাহ্মণ · সপ্তর্ষিপূজিত প্রাণ",
    (2, 3): "তৃতীয় ব্রাহ্মণ · ব্রহ্মের মূর্ত ও অমূর্ত রূপ («নেতি নেতি»)",
    (2, 4): "চতুর্থ ব্রাহ্মণ · মৈত্রেয়ী-ব্রাহ্মণ (আত্মাই পরম প্রেমাস্পদ)",
    (2, 5): "পঞ্চম ব্রাহ্মণ · মধুবিদ্যা",
    (2, 6): "ষষ্ঠ ব্রাহ্মণ · মধুকাণ্ডের বংশাবলি",
    (3, 1): "প্রথম ব্রাহ্মণ · অশ্বল-প্রশ্ন (মুক্তি ও অতিমুক্তি)",
    (3, 2): "দ্বিতীয় ব্রাহ্মণ · আর্তভাগ-প্রশ্ন (গ্রহ, অতিগ্রহ ও কর্ম)",
    (3, 3): "তৃতীয় ব্রাহ্মণ · ভুজ্যু-প্রশ্ন (পারীক্ষিতদের গতি)",
    (3, 4): "চতুর্থ ব্রাহ্মণ · উষস্ত-প্রশ্ন (সাক্ষাৎ অপরোক্ষ ব্রহ্ম)",
    (3, 5): "পঞ্চম ব্রাহ্মণ · কহোল-প্রশ্ন (অশনায়া-অতীত আত্মা ও সন্ন্যাস)",
    (3, 6): "ষষ্ঠ ব্রাহ্মণ · গার্গী-প্রশ্ন (ব্রহ্মলোক পর্যন্ত ওতপ্রোত)",
    (3, 7): "সপ্তম ব্রাহ্মণ · উদ্দালক-প্রশ্ন (সূত্র ও অন্তর্যামী ব্রাহ্মণ)",
    (3, 8): "অষ্টম ব্রাহ্মণ · গার্গী-প্রশ্ন (অক্ষর-ব্রহ্মতত্ত্ব)",
    (3, 9): "নবম ব্রাহ্মণ · শাকল্য-প্রশ্ন (দেবতা-নির্ণয় ও বিজ্ঞানানন্দ ব্রহ্ম)",
    (4, 1): "প্রথম ব্রাহ্মণ · ষড়াচার্য-মত ও বাগাদি-উপাসনা",
    (4, 2): "দ্বিতীয় ব্রাহ্মণ · কূর্চ-ব্রাহ্মণ (বৈশ্বানর, তৈজস ও তুরীয় অভয়)",
    (4, 3): "তৃতীয় ব্রাহ্মণ · জ্যোতি-ব্রাহ্মণ (অবস্থাত্রয় ও পরম আনন্দ)",
    (4, 4): "চতুর্থ ব্রাহ্মণ · শারীরক-ব্রাহ্মণ (জন্মান্তর, নির্বাণ ও ব্রহ্মজ্ঞান)",
    (4, 5): "পঞ্চম ব্রাহ্মণ · মৈত্রেয়ী-ব্রাহ্মণ (নিগমন)",
    (4, 6): "ষষ্ঠ ব্রাহ্মণ · যাজ্ঞবল্ক্যকাণ্ডের বংশাবলি",
    (5, 1): "প্রথম ব্রাহ্মণ · পূর্ণমদঃ ও খং ব্রহ্ম",
    (5, 2): "দ্বিতীয় ব্রাহ্মণ · দম, দান ও দয়া",
    (5, 3): "তৃতীয় ব্রাহ্মণ · হৃদয়ব্রহ্ম",
    (5, 4): "চতুর্থ ব্রাহ্মণ · সত্যব্রহ্ম",
    (5, 5): "পঞ্চম ব্রাহ্মণ · সত্যব্রহ্মের স্তুতি ও ব্যাহৃতি-পুরুষ",
    (5, 6): "ষষ্ঠ ব্রাহ্মণ · মনোময় ভাস্বর পুরুষ",
    (5, 7): "সপ্তম ব্রাহ্মণ · বিদ্যুৎ ব্রহ্ম",
    (5, 8): "অষ্টম ব্রাহ্মণ · বাগ্ধেনু-উপাসনা",
    (5, 9): "নবম ব্রাহ্মণ · জাঠরাগ্নি বৈশ্বানর",
    (5, 10): "দশম ব্রাহ্মণ · উপাসকের ঊর্ধ্বগতি",
    (5, 11): "একাদশ ব্রাহ্মণ · ব্যাধি ও অন্ত্যেষ্টিতে তপস্যাদৃষ্টি",
    (5, 12): "দ্বাদশ ব্রাহ্মণ · অন্ন ও প্রাণের একীভাব",
    (5, 13): "ত্রয়োদশ ব্রাহ্মণ · উক্থাদি-দৃষ্টিতে প্রাণোপাসনা",
    (5, 14): "চতুর্দশ ব্রাহ্মণ · গায়ত্রী-ব্রাহ্মণ",
    (5, 15): "পঞ্চদশ ব্রাহ্মণ · হিরণ্ময়েন পাত্রেণ (মুমূর্ষু-প্রার্থনা)",
    (6, 1): "প্রথম ব্রাহ্মণ · প্রাণ ও ইন্দ্রিয়গণের সংবাদ",
    (6, 2): "দ্বিতীয় ব্রাহ্মণ · প্রবাহণ-গৌতম সংবাদ ও পঞ্চাগ্নিবিদ্যা",
    (6, 3): "তৃতীয় ব্রাহ্মণ · মন্থকর্ম",
    (6, 4): "চতুর্থ ব্রাহ্মণ · পুত্রমন্থ ও গার্হস্থ্য বিধান",
    (6, 5): "পঞ্চম ব্রাহ্মণ · সমগ্র উপনিষদের বংশাবলি",
}

SK_PATCHES = {
    "1.5.2": [("धिया धिया", "धिया")],
    "1.6.3": [("॥ ॥ इति बृहदारण्यकोपनिषदि प्रथमोऽध्यायः ॥", "॥")],
    "2.4.12": [
        ("न हास्योद्ग्रहणायेव न हास्योद्ग्रहणायैव स्याद्", "न हास्योद्ग्रहणायैव स्याद्"),
        ("समुत्थाय एतेभ्यस्भूतेभ्यस्समुत्थाय तान्येवानुविनश्यति", "समुत्थाय तान्येवानुविनश्यति"),
    ],
    "2.5.16": [("दध्यङ्ङाथर्वणोऽश्विभ्यामुवाच । उवाच तदेतदृषिः", "दध्यङ्ङाथर्वणोऽश्विभ्यामुवाच । तदेतदृषिः")],
    "2.6.3": [
        ("पारशर्यायणः", "पाराशर्यायणः"),
        ("यास्काच्च्- ऽऽसुरायण", "यास्काच्चासुरायण"),
        ("रासुरासुरिर्", "रासुरेरासुरिर्"),
        ("आत्रेयादत्रेयो", "आत्रेयादात्रेयो"),
        ("॥ ॥ इति बृहदारण्यकोपनिषदि द्वितीयोऽध्यायः ॥", "॥"),
    ],
    "3.5.1": [
        ("पप्रच्छ पप्रच्छ", "पप्रच्छ"),
        ("एवातोऽन्यदार्तम् । य एवं वेद एवातोऽन्यदार्तम् । ", "एवातोऽन्यदार्तम् । "),
    ],
    "3.8.8": [
        ("तदक्षरऽ गार्गि", "तदक्षरं गार्गि"),
        ("मतमो- ऽवाय्वनाकाशमसङ्गं", "मतमोऽवाय्वनाकाशमसङ्गम्"),
    ],
    "3.9.1": [("याज्ञवल्क्येत्य्द्वावित्योमिति", "याज्ञवल्क्येति । द्वावित्योमिति")],
    "3.9.28": [("॥ ॥ ॥ इति बृहदारण्यकोपनिषदि तृतीयोऽध्यायः ॥", "॥")],
    "4.2.4": [(
        "नेति नेत्याऽत्मागृह्यो न हि गृह्यतेऽशीर्यो न हि शीर्यतेऽसङ्गो न हि सज्यतेऽसितो न व्यथते न रिष्यत्य्व्यथते असङ्गस्न हि सज्यते असितस्न व्यथते न रिष्यति अभयं",
        "नेति नेत्यात्माऽगृह्यो न हि गृह्यतेऽशीर्यो न हि शीर्यतेऽसङ्गो न हि सज्यतेऽसितो न व्यथते न रिष्यत्यभयं",
    )],
    "4.3.1": [("स मेने न वदिष्य इति स मेने न वदिष्य", "स मेने न वदिष्य")],
    "4.3.7": [(
        "योऽयं विज्ञानमयः प्राणेषु हृद्यन्तर्ज्योतिः विज्ञानमयः प्राणेषु हृद्यन्तर्ज्योतिः पुरुषः पुरुषस्स समानः",
        "योऽयं विज्ञानमयः प्राणेषु हृद्यन्तर्ज्योतिः पुरुषः । स समानः",
    )],
    "4.3.33": [
        ("सम्पन्नतमः अन्येषां सम्पन्नतमस्स मनुष्याणां", "सम्पन्नतमः स मनुष्याणां"),
        ("बिभयांचकारः", "बिभयांचकार"),
    ],
    "4.4.5": [(
        "सर्वमयस्श्रोत्रमयसाकाशमयस्वायुमयस्तेजोमय- सापोमयस्पृथिवीमयस्क्रोधमयसक्रोधमय- शर्षमयसहर्षमयस् ",
        "सर्वमयः ",
    )],
    "4.4.22": [("मुनिर्भवत्य्विदित्वा मुनिस्भवति एतमेव", "मुनिर्भवति । एतमेव")],
    "4.5.13": [(
        "रसघन एवै वं वा अरेऽयमात्मानन्तरोऽबाह्यः कृत्स्नः प्रज्ञानघन एवैतेभ्यो भूतेभ्यः समुत्थाय तान्येवानुविनयष्यतिति प्रज्ञानघनसेव एतेभ्यस्भूतेभ्यस्समुत्थाय तानि एव अनुविनयति",
        "रसघन एवैवं वा अरेऽयमात्मानन्तरोऽबाह्यः कृत्स्नः प्रज्ञानघन एवैतेभ्यो भूतेभ्यः समुत्थाय तान्येवानुविनश्यति",
    )],
    "4.6.3": [
        ("ऽव्श्विभ्यामश्विनौ", "ऽश्विभ्यामश्विनौ"),
        ("॥ ॥ इति बृहदारण्यकोपनिषदि चतुर्थोऽध्यायः ॥", "॥"),
    ],
    "5.13.1": [("त्थापयत्युद्धास्मा धस्मादुक्थविद्वीर", "त्थापयत्युद्धास्मादुक्थविद्वीर")],
    "5.15.1": [("॥ ॥ इति बृहदारण्यकोपनिषदि पञ्चमोऽध्यायः ॥", "॥")],
    "6.2.4": [("तत्तुभमवोचम्", "तत्तुभ्यमवोचम्")],
    "6.4.4": [("एतद् ध स्म वै तद् विद्वान् कुमारहारितसाह ", "")],
    "6.5.4": [
        ("सञ्जिवीपुत्रो", "साञ्जीवीपुत्रो"),
        ("॥ इति बृहदारण्यकोपनिषदि षष्ठोऽध्यायः ॥", "॥"),
    ],
}

EN_MACRONS = str.maketrans({"â": "ā", "î": "ī", "û": "ū", "Â": "Ā", "Î": "Ī", "Û": "Ū"})
ORDINALS = [
    "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH",
    "NINTH", "TENTH", "ELEVENTH", "TWELFTH", "THIRTEENTH", "FOURTEENTH", "FIFTEENTH",
]


def clean_sk(k: str, s: str) -> str:
    for old, new in SK_PATCHES.get(k, []):
        assert old in s, f"{k} expected {old!r} in {s!r}"
        s = s.replace(old, new)
    s = re.sub(r"[ \t]+", " ", s).strip()
    if not s.endswith("॥"):
        s = s.rstrip("।").strip() + " ॥"
    return s


def clean_bn(s: str) -> str:
    s = s.replace("\u09f0", "র").replace("\u200c", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def clean_en(s: str) -> str:
    s = s.translate(EN_MACRONS)
    s = re.sub(r"\s*Next: .*?Sacred Texts \| Hinduism.*$", "", s)
    s = re.sub(r"\s*\[paragraph continues\]\s*", " ", s)
    s = re.sub(r"(^|\s)p\.\s*\d+[a-z]?(?=\s|$)", " ", s)
    s = re.sub(r"(?<=[A-Za-zāīūĀĪŪ)\]])\s+\d+\s*(?=[.,;:!?'\"])", "", s)
    s = re.sub(r"\s*[,;]\s*--\s*", " — ", s)
    s = re.sub(r"\s*--\s*", " — ", s)
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def ordinal(h: str, word: str) -> int:
    for i, o in enumerate(ORDINALS, 1):
        if re.search(rf"\b{o} {word}\b", h):
            return i
    return 0


def strip_sbe(fragment: str) -> str:
    t = re.sub(r'<a[^>]*href="#fn[^"]*"[^>]*>.*?</a>', "", fragment, flags=re.I | re.S)
    t = re.sub(r'<a[^>]*name="fr_[^"]*"[^>]*>\s*</a>', "", t, flags=re.I | re.S)
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<i>([^<]*)</i>", r"\1", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return htmllib.unescape(htmllib.unescape(t))


def load_sbe15_map() -> dict[tuple[int, int, int], str]:
    misprints = {"3.1:3": "1"}
    splits = {"2.4": ["'For when there is as it were duality"]}
    sbe: dict[str, dict[int, str]] = {}
    preface: dict[str, list[str]] = {}
    adhyaya = brahmana = mantra = 0
    carry: list[str] | None = None

    for fn in sorted(p for p in SBE_DIR.iterdir() if re.match(r"^sbe150\d\d\.htm$", p.name)):
        raw = fn.read_text(encoding="utf-8", errors="replace")
        m_body = re.search(r"<BODY[^>]*>(.*?)(?:</BODY>|$)", raw, flags=re.I | re.S)
        body = m_body.group(1) if m_body else raw
        html_clean = re.sub(
            r'<h3[^>]*>\s*Footnotes\s*</h3>.*?(?=<p>\s*<a name="page_|$)', "", body, flags=re.I | re.S
        )
        html_clean = re.sub(
            r'<p>\s*<a name="fn_.*?(?=<p[\s>]|<hr|<h[123][\s>]|$)', "", html_clean, flags=re.I | re.S
        )
        heading_on_page = False
        for m in re.finditer(
            r"<h[123][^>]*>(.*?)</h[123]>|<p[^>]*>(.*?)(?=<p[\s>]|</p>|<h[123][\s>])",
            html_clean,
            flags=re.I | re.S,
        ):
            if m.group(1) is not None:
                h = strip_sbe(m.group(1)).upper().replace("Â", "A")
                a = ordinal(h, "ADHYAYA")
                b = ordinal(h, "BRAHMANA")
                if a:
                    adhyaya = a
                if b:
                    brahmana = b
                    mantra = 0
                    carry = None
                    heading_on_page = True
                    sbe.setdefault(f"{adhyaya}.{brahmana}", {})
                continue
            text = re.sub(r"\s+", " ", strip_sbe(m.group(2) or "")).strip()
            if not text or re.fullmatch(r"(p\. \d+ ?)+", text) or "sacred-texts.com" in text or not brahmana:
                continue
            ab = f"{adhyaya}.{brahmana}"
            mantras = sbe[ab]
            num_m = re.match(r"^(\d[\d ]*)\.,?\s+(.*)$", text, flags=re.S)
            num_str = num_m.group(1) if num_m else None
            rest = num_m.group(2) if num_m else None
            if num_m and misprints.get(f"{ab}:{mantra + 1}") == num_str:
                num_str = str(mantra + 1)
            if not num_m and any(text.startswith(st) for st in splits.get(ab, [])):
                num_str, rest = str(mantra + 1), text
            if adhyaya == 1 and brahmana == 3 and text.startswith("Next follows the Abhy"):
                carry = []
            if carry is not None and num_str is None:
                carry.append(text)
                continue
            if num_str is not None and int(num_str.replace(" ", "")) == mantra + 1:
                mantra += 1
                mantras[mantra] = " ".join([*(carry or []), rest or ""]).strip()
                carry = None
            elif mantra > 0:
                mantras[mantra] = f"{mantras[mantra]} {text}"
            elif not heading_on_page:
                keys = list(sbe.keys())
                if len(keys) >= 2 and sbe[keys[-2]]:
                    prev = sbe[keys[-2]]
                    lk = len(prev)
                    prev[lk] = f"{prev[lk]} {text}"
            else:
                preface.setdefault(ab, []).append(text)

    for ab, texts in preface.items():
        if len(sbe.get(ab, {})) == 0:
            sbe[ab][1] = " ".join(texts)

    vi5 = sbe.get("6.5", {})
    joined = f"{vi5.get(1, '')} {vi5.get(2, '')}"
    at = joined.find(" 2. from Âtreyîputra")
    assert at > 0
    vi5[1] = joined[:at].strip()
    vi5[2] = joined[at + len(" 2. ") :].strip()

    for ref, pat in [
        ("1.3.17", "The Devas said: 'Verily, thus far"),
        ("1.3.21", "He (breath) is also Sâman"),
        ("3.9.18", "Sâkalya said: 'Yâgñavalkya, because thou hast decried"),
    ]:
        a, b, n_s = ref.split(".")
        ab, n = f"{a}.{b}", int(n_s)
        t = sbe[ab][n]
        i = t.find(pat)
        assert i >= 0, ref
        sbe[ab][n] = t[:i].strip()
        sbe[ab][n + 1] = f"{t[i:]} {sbe[ab].get(n + 1, '')}".strip()

    if len(sbe.get("5.15", {})) > 1:
        sbe["5.15"] = {1: " ".join(sbe["5.15"][k] for k in sorted(sbe["5.15"]))}

    out: dict[tuple[int, int, int], str] = {}
    for ab, mantras in sbe.items():
        if ab == "6.4":
            continue
        a, b = map(int, ab.split("."))
        for c, val in mantras.items():
            out[(a, b, c)] = clean_en(val)
    return out


def load_hume_6_4() -> dict[tuple[int, int, int], str]:
    out: dict[tuple[int, int, int], str] = {}
    for ln in HUME_TXT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[(6\.4\.(\d+))\]\s*(.+)$", ln)
        if m:
            out[(6, 4, int(m.group(2)))] = clean_en(m.group(3))
    assert len(out) == 28
    return out


def load_bn_map() -> dict[tuple[int, int, int], str]:
    out: dict[tuple[int, int, int], str] = {}
    for ln in BN_TXT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[(\d+)\.(\d+)\.(\d+)\]\s*(.+)$", ln)
        if m:
            out[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = clean_bn(m.group(4))
    return out


def build_preface(raw: str) -> tuple[str, str]:
    m_sk = re.search(r"##\s*শান্তিপাঠঃ\s*\n(.+?)\nসরলার্থ\s*:", raw, re.S)
    m_sar = re.search(r"সরলার্থ\s*:\s*(.+?)\n##\s*ভূমিকা", raw, re.S)
    m_bhu = re.search(r"##\s*ভূমিকা[^\n]*\n(.+)$", raw, re.S)
    assert m_sk and m_sar and m_bhu, "বৃহদারণ্যক ভূমিকা অসম্পূর্ণ"
    parts = [
        "শান্তিপাঠঃ\n" + m_sk.group(1).strip() + "\n" + clean_bn(m_sar.group(1)),
        "ভূমিকা (স্বামী গম্ভীরানন্দ)\n" + "\n\n".join(
            clean_bn(p) for p in re.split(r"\n\s*\n", m_bhu.group(1).strip()) if p.strip()
        ),
    ]
    return "শান্তিপাঠ ও ভূমিকা", "\n\n".join(parts)


def main() -> int:
    for p in (DG_BU_JSON, SBE_DIR, BN_TXT, HUME_TXT, PRE_TXT):
        if not p.exists():
            raise SystemExit(f"উৎস নেই: {p}")

    bu = json.loads(DG_BU_JSON.read_text(encoding="utf-8"))
    sk_map: dict[tuple[int, int, int], str] = {}
    for ch in bu["chapters"]:
        for v in ch["verses"]:
            a, b, c = map(int, v["number"].split("."))
            sk_map[(a, b, c)] = clean_sk(v["number"], v["sanskrit"])

    bn_map = load_bn_map()
    en_map = {**load_sbe15_map(), **load_hume_6_4()}

    assert len(sk_map) == 435
    assert set(bn_map) == set(sk_map), f"BN vs SK diff: {set(bn_map) ^ set(sk_map)}"
    assert set(en_map) == set(sk_map), f"EN vs SK diff: {set(en_map) ^ set(sk_map)}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    heading, preface = build_preface(PRE_TXT.read_text(encoding="utf-8"))
    ch_metas = []
    total = 0
    total_brahmanas = 0

    for ch in range(1, 7):
        ch_brs = sorted({b for (a, b, _) in sk_map if a == ch})
        assert ch_brs == list(range(1, len(ch_brs) + 1))

        suktas = []
        verses = []
        en_verses = {}
        seq = 0

        for br in ch_brs:
            mantra_nums = sorted(c for (a, b, c) in sk_map if a == ch and b == br)
            assert mantra_nums == list(range(1, len(mantra_nums) + 1))
            s_from = seq + 1
            for vn in mantra_nums:
                seq += 1
                sk = sk_map[(ch, br, vn)]
                bn = bn_map[(ch, br, vn)]
                en = en_map[(ch, br, vn)]

                assert sk and sk.endswith("॥"), f"{ch}.{br}.{vn} sk invalid: {sk!r}"
                assert not re.search(r"[\u0980-\u09FFa-zA-Z0-9]", sk), f"{ch}.{br}.{vn} leak in sk: {sk!r}"
                assert bn and "\u09f0" not in bn and not re.search(r"[\u0900-\u0963\u0966-\u097F]", bn), f"{ch}.{br}.{vn} bn invalid"
                assert en and "_" not in en and not re.search(r"[âîûÂÎÛ\u0900-\u09FF]", en), f"{ch}.{br}.{vn} en invalid: {en!r}"

                v_obj: dict = {"n": seq, "ch": br, "vn": vn, "sk": sk, "bn": bn}
                if vn == 1 and (ch, br) in BRAHMANA_TITLES:
                    v_obj["hd"] = BRAHMANA_TITLES[(ch, br)]
                verses.append(v_obj)
                en_verses[str(seq)] = en

            suktas.append({
                "id": br,
                "from": s_from,
                "to": seq,
                "vfrom": 1,
                "vto": len(mantra_nums),
                "mantra": len(mantra_nums),
            })

        total += seq
        total_brahmanas += len(ch_brs)

        ch_obj: dict = {
            "id": ch,
            "bn": CHAPTER_NAMES[ch],
            "count": seq,
            "from": 1,
            "to": seq,
            "withBn": seq,
            "suktaCount": len(ch_brs),
            "groupWord": "ব্রাহ্মণ",
        }
        if ch == 1:
            ch_obj["heading"] = heading
            ch_obj["preface"] = preface
        ch_obj["suktas"] = suktas
        ch_obj["verses"] = verses

        (OUT_DIR / f"ch{ch}.json").write_text(
            json.dumps(ch_obj, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        (EN_DIR / f"ch{ch}.json").write_text(
            json.dumps({"id": ch, "verses": en_verses}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        meta: dict = {
            "id": ch,
            "bn": CHAPTER_NAMES[ch],
            "count": seq,
            "from": 1,
            "to": seq,
            "withBn": seq,
            "suktaCount": len(ch_brs),
            "aligned": len(ch_brs),
            "grid": {"count": len(ch_brs)},
        }
        if ch == 1:
            meta["prefaceCount"] = 1
        ch_metas.append(meta)

    assert total == 435 and total_brahmanas == 47

    index_obj = {
        "slug": "brihadaranyaka",
        "bn": "বৃহদারণ্যক উপনিষদ",
        "en": "Brihadaranyaka Upanishad",
        "total": total,
        "withBn": total,
        "withSk": total,
        "withEn": total,
        "suktaTotal": total_brahmanas,
        "verseWord": "মন্ত্র",
        "groupWord": "ব্রাহ্মণ",
        "chword": "অধ্যায়",
        "skSrc": "মূল সংস্কৃত পাঠ (কাণ্ব শাখা) — বহুমূল নিরীক্ষিত (sa_bu_viswara, GRETIL ও dharma-granth দেবনাগরী)",
        "bnSrc": "বাংলা সরলার্থ — স্বামী গম্ভীরানন্দ («উপনিষদ গ্রন্থাবলী ৩: বৃহদারণ্যকোপনিষদ্‌», উদ্বোধন)",
        "enSrc": "ইংরেজি অনুবাদ — F. Max Müller (SBE Vol. 15, 1884: ৪৬ ব্রাহ্মণ) ও Robert E. Hume (1921: ষষ্ঠ অধ্যায় ৪র্থ ব্রাহ্মণ)",
        "note": "৬ অধ্যায় ও ৪৭ ব্রাহ্মণের সম্পূর্ণ ৪৩৫ মন্ত্র মূল সংস্কৃত, বাংলা সরলার্থ ও ইংরেজি অনুবাদসহ; শুরুতে শান্তিপাঠ ও ভূমিকা আলাদা ব্লকে রাখা হয়েছে।",
        "chapters": ch_metas,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index_obj, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"✓ brihadaranyaka: 6 অধ্যায়, {total_brahmanas} ব্রাহ্মণ, {total} মন্ত্র (সংস্কৃত+বাংলা+ইংরেজি)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
