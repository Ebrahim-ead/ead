#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""প্রশ্ন উপনিষদ ডেটা-নির্মাতা — assets/grantho/data/prashna/

উৎস ও নীতি (অনুমানভিত্তিক পাঠ বর্জন):
  ১. মূল সংস্কৃত পাঠ (দেবনাগরী): চার-সূত্র নিরীক্ষিত —
     rampsuthar1999-arch/smarana_v2/prashna.json (ভিত্তি কাঠামো),
     sanskritdocuments.org (prashna.itx), divine-books@0.5.0
     (prasna_upanishad.json), ও ebanglalibrary.com-এর মূল পাঠ মিলিয়ে
     ছাপাখানা/OCR-ত্রুটি সংশোধিত (৬ প্রশ্ন, ৬৭ মন্ত্র)।
  ২. বাংলা সরলার্থ (`bn`): স্বামী লোকেশ্বরানন্দ — ebanglalibrary.com
     («প্রশ্ন উপনিষদ», ৬৭/৬৭ মন্ত্র + মঙ্গলাচরণ ও ভূমিকা)।
  ৩. ইংরেজি অনুবাদ (`en/ch1..6.json`): F. Max Müller — Sacred Books of the
     East, Vol. 15 (1884), ৬৭/৬৭ মন্ত্র (SBE ডায়াক্রিটিক পরিষ্কার করা)।
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "grantho" / "data" / "prashna"
EN_DIR = OUT_DIR / "en"

SM_JSON = pathlib.Path(os.environ.get("PRA_SM_JSON", "/tmp/upanishads/smarana_v2/prashna.json"))
BN1_TXT = pathlib.Path(os.environ.get("PRA_BN1", "/tmp/upanishads/raw/prashna_bn_part1.txt"))
BN2_TXT = pathlib.Path(os.environ.get("PRA_BN2", "/tmp/upanishads/raw/prashna_bn_part2.txt"))
PRE_TXT = pathlib.Path(os.environ.get("PRA_PRE", "/tmp/upanishads/raw/prashna_preface_bn.txt"))
EN_TXT = pathlib.Path(os.environ.get("PRA_EN", "/tmp/upanishads/raw/prashna_en.txt"))

EXPECTED_COUNTS = {1: 16, 2: 13, 3: 12, 4: 11, 5: 7, 6: 8}

CHAPTER_NAMES = {
    1: "প্রথম প্রশ্ন · কবন্ধীর প্রশ্ন (রয়ি ও প্রাণ)",
    2: "দ্বিতীয় প্রশ্ন · ভার্গবের প্রশ্ন (মুখ্য প্রাণ)",
    3: "তৃতীয় প্রশ্ন · কৌসল্যের প্রশ্ন (প্রাণতত্ত্ব)",
    4: "চতুর্থ প্রশ্ন · গার্গ্যের প্রশ্ন (স্বপ্ন ও সুষুপ্তি)",
    5: "পঞ্চম প্রশ্ন · সত্যকামের প্রশ্ন (ওঙ্কার-ধ্যান)",
    6: "ষষ্ঠ প্রশ্ন · সুকেশার প্রশ্ন (ষোড়শকল পুরুষ)",
}

# চার-সূত্র নিরীক্ষিত সংস্কৃত সংশোধনী (smarana_v2-তে থাকা OCR/টাইপো ঠিক করা)
WORD_FIXES = {
    (1, 3): [("भगवन्कुते", "भगवन्कुतो")],
    (1, 12): [("प्रणस्तस्मादेत", "प्राणस्तस्मादेत")],
    (2, 4): [
        ("तस्मिंष्च", "तस्मिंश्च"),
        ("वाङ्मनष्चक्षुः", "वाङ्मनश्चक्षुः"),
        ("प्रातिष्टन्त", "प्रातिष्ठन्त"),
    ],
    (2, 11): [("प्राणैकर्षरत्ता", "प्राणैकर्षिरत्ता")],
    (3, 4): [("एतन्ग्रामानोतान्", "एतान्ग्रामानेतान्")],
    (3, 10): [("तथासङ्कल्पितं", "यथासङ्कल्पितं")],
    (4, 7): [("सोभ्य", "सोम्य"), ("वसोवृक्षं", "वासोवृक्षं")],
    (4, 8): [("यादौ च गन्तव्यं", "पादौ च गन्तव्यं")],
    (5, 4): [("विभुतिमनुभूय", "विभूतिमनुभूय")],
    (6, 2): [("यस्मिन्नताः", "यस्मिन्नेताः")],
    (6, 3): [("ईक्षाचक्रे", "ईक्षाञ्चक्रे")],
    (6, 6): [("यथ मा वो मृत्युः", "यथा मा वो मृत्युः")],
}

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
EN_MACRONS = str.maketrans({"â": "ā", "î": "ī", "û": "ū", "Â": "Ā", "Î": "Ī", "Û": "Ū"})


def clean_sk(s: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines)


def clean_bn(s: str) -> str:
    s = s.replace("\u09f0", "র").replace("\u200c", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def clean_en(s: str) -> str:
    s = s.translate(EN_MACRONS)
    s = re.sub(r"\s*[,;]\s*--\s*", " — ", s)
    s = re.sub(r"\s*--\s*", " — ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_smarana_map(sm: dict) -> dict[tuple[int, int], str]:
    out = {}
    for item in sm["v"][1:]:
        a, b = map(int, item[0].split("."))
        out[(a, b)] = "\n".join(item[1])
    return out


def parse_bn_sections(raw: str) -> dict[tuple[int, int], str]:
    out = {}
    cur = None
    buf: list[str] = []
    for ln in raw.splitlines():
        m = re.match(r"^([১-৬]\.[০-৯]+)\s*$", ln.strip())
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            a, b = map(int, m.group(1).translate(BN_DIGITS).split("."))
            cur = (a, b)
            buf = []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()

    cleaned: dict[tuple[int, int], str] = {}
    for k, block in out.items():
        m = re.search(r"সরলার্থ\s*[:ঃ]\s*(.+)$", block, re.S)
        assert m, f"সরলার্থ পাওয়া যায়নি: {k}"
        cleaned[k] = clean_bn(m.group(1))
    return cleaned


def parse_en_sections(raw: str) -> dict[tuple[int, int], str]:
    out = {}
    cur = None
    buf: list[str] = []
    for ln in raw.splitlines():
        m = re.match(r"^([1-6]\.\d+)\s*$", ln.strip())
        if m:
            if cur is not None:
                out[cur] = clean_en(" ".join(buf))
            a, b = map(int, m.group(1).split("."))
            cur = (a, b)
            buf = []
        elif cur is not None and ln.strip():
            buf.append(ln.strip())
    if cur is not None:
        out[cur] = clean_en(" ".join(buf))
    if (6, 8) in out and "Adoration to the highest" not in out[(6, 8)]:
        out[(6, 8)] += " Adoration to the highest Rishis! Adoration to the highest Rishis!"
    return out


def build_preface(raw: str) -> tuple[str, str]:
    m_sar = re.search(r"সরলার্থ\s*:\s*(.+?)\n##\s*ভূমিকা", raw, re.S)
    m_bhu = re.search(r"##\s*ভূমিকা[^\n]*\n(.+)$", raw, re.S)
    assert m_sar and m_bhu, "প্রশ্ন উপনিষদের ভূমিকা অংশ অসম্পূর্ণ"
    shanti_sk = (
        "ॐ भद्रं कर्णेभिः शृणुयाम देवा भद्रं पश्येमाक्षभिर्यजत्राः ।\n"
        "स्थिरैरङ्गैस्तुष्टुवांसस्तनूभिर्व्यशेम देवहितं यदायुः ॥\n"
        "ॐ शान्तिः शान्तिः शान्तिः ॥"
    )
    parts = [
        "মঙ্গলাচরণঃ\n" + shanti_sk + "\n" + clean_bn(m_sar.group(1)),
        "ভূমিকা (স্বামী লোকেশ্বরানন্দ)\n" + "\n\n".join(
            clean_bn(p) for p in re.split(r"\n\s*\n", m_bhu.group(1).strip()) if p.strip()
        ),
    ]
    return "মঙ্গলাচরণ ও ভূমিকা", "\n\n".join(parts)


def main() -> int:
    for p in (SM_JSON, BN1_TXT, BN2_TXT, PRE_TXT, EN_TXT):
        if not p.exists():
            raise SystemExit(f"উৎস-ফাইল নেই: {p}")

    sm = json.loads(SM_JSON.read_text(encoding="utf-8"))
    sm_map = load_smarana_map(sm)
    bn_map = parse_bn_sections(
        BN1_TXT.read_text(encoding="utf-8") + "\n" + BN2_TXT.read_text(encoding="utf-8")
    )
    en_map = parse_en_sections(EN_TXT.read_text(encoding="utf-8"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    heading, preface = build_preface(PRE_TXT.read_text(encoding="utf-8"))
    ch_metas = []
    total = 0

    for ch in range(1, 7):
        want_n = EXPECTED_COUNTS[ch]
        verses = []
        en_verses = {}

        for n in range(1, want_n + 1):
            sk = sm_map[(ch, n)]
            for old, new in WORD_FIXES.get((ch, n), []):
                assert old in sk, f"{ch}.{n} expected {old!r} in {sk!r}"
                sk = sk.replace(old, new)
            sk = clean_sk(sk)
            bn = bn_map[(ch, n)]
            en = en_map[(ch, n)]

            assert sk and sk.endswith("॥"), f"{ch}.{n} sk invalid: {sk!r}"
            assert not re.search(r"[\u0980-\u09FF]", sk), f"{ch}.{n} Bengali leak in sk"
            assert bn and "\u09f0" not in bn, f"{ch}.{n} bn invalid"
            assert en and "_" not in en and not re.search(r"[âîûÂÎÛ]", en), f"{ch}.{n} en invalid: {en!r}"

            verses.append({"n": n, "sk": sk, "bn": bn})
            en_verses[str(n)] = en

        assert len(verses) == want_n
        total += want_n

        ch_obj: dict = {
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

        meta: dict = {
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
        "slug": "prashna",
        "bn": "প্রশ্ন উপনিষদ",
        "en": "Prashna Upanishad",
        "total": total,
        "withBn": total,
        "withSk": total,
        "withEn": total,
        "verseWord": "মন্ত্র",
        "chword": "প্রশ্ন",
        "skSrc": "মূল সংস্কৃত পাঠ — চার-সূত্র নিরীক্ষিত (smarana_v2, sanskritdocuments.org prashna.itx, divine-books ও ebanglalibrary.com)",
        "bnSrc": "বাংলা সরলার্থ — স্বামী লোকেশ্বরানন্দ (ebanglalibrary.com)",
        "enSrc": "ইংরেজি অনুবাদ — F. Max Müller (Sacred Books of the East, Vol. 15, 1884)",
        "note": "শুরুতে মঙ্গলাচরণ ও ভূমিকা আলাদা ব্লকে (মন্ত্র-গণনার বাইরে) রাখা হয়েছে।",
        "chapters": ch_metas,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index_obj, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"✓ prashna: 6 প্রশ্ন, {total} মন্ত্র (সংস্কৃত+বাংলা+ইংরেজি)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
