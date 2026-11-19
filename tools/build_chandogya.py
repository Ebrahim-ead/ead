#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ছান্দোগ্য উপনিষদ ডেটা-নির্মাতা — assets/grantho/data/chandogya/

উৎস ও নীতি (অনুমানভিত্তিক পাঠ বর্জন):
  ১. মূল সংস্কৃত পাঠ (দেবনাগরী): বহুমূল নিরীক্ষিত —
     sanskritdocuments.org (chhaandogya.itx), GRETIL (Limaye & Vadekar),
     vishvAsa, ও dharma-granth দেবনাগরী পাঠ মিলিয়ে ৫.১৭ বিভাজন, ৬.৬.৫
     পুনঃসংখ্যা, ৩.১৩.৭-৮ একত্রীকরণ ও ছাপাখানা-ত্রুটি সংশোধিত
     (৮ অধ্যায়, ১৫৪ খণ্ড, ৬২৮ মন্ত্র)।
  ২. বাংলা সরলার্থ (`bn`): ebanglalibrary.com («ছান্দোগ্য উপনিষদ», ১৫৪/১৫৪ খণ্ড,
     ৬২৮/৬২৮ মন্ত্র + শান্তিপাঠ ও সূচনা)।
  ৩. ইংরেজি অনুবাদ (`en/ch1..8.json`): F. Max Müller — Sacred Books of the
     East, Vol. 1 (1879), মূল HTML পৃষ্ঠা (sbe01022..sbe01175) সরাসরি পার্স করে
     বহু-অনুচ্ছেদ ও পাদটীকা-বিভ্রাট মুক্ত করা (৬২৮/৬২৮ মন্ত্র; ২.১৩-তে
     SBE-বর্জিত ২ মন্ত্র মূল সংস্কৃত-সম্মত অনুবাদ)।
"""
from __future__ import annotations

import html as htmllib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "grantho" / "data" / "chandogya"
EN_DIR = OUT_DIR / "en"

DG_CH_JSON = pathlib.Path(os.environ.get("CH_DG_JSON", "/tmp/dg/public/data/scriptures-full/chandogya.json"))
SBE_DIR = pathlib.Path(os.environ.get("CH_SBE_DIR", "/tmp/dg/scripts/cache/chandogya-sbe"))
BN_DIR = pathlib.Path(os.environ.get("CH_BN_DIR", "/tmp/upanishads/raw"))
PRE_TXT = BN_DIR / "chandogya_preface_bn.txt"

EXPECTED_CH_COUNTS = {
    1: (13, 104),
    2: (24, 82),
    3: (19, 94),
    4: (17, 78),
    5: (24, 88),
    6: (16, 69),
    7: (26, 51),
    8: (15, 62),
}

CHAPTER_NAMES = {
    1: "প্রথম অধ্যায় · ওঙ্কার ও উদ্‌গীথ-উপাসনা",
    2: "দ্বিতীয় অধ্যায় · সামোপাসনা ও ওঙ্কার-মহিমা",
    3: "তৃতীয় অধ্যায় · মধুবিদ্যা ও শাণ্ডিল্য-বিদ্যা",
    4: "চতুর্থ অধ্যায় · সংবর্গ-বিদ্যা ও সত্যকাম-কথা",
    5: "পঞ্চম অধ্যায় · প্রাণ-সংবাদ ও পঞ্চাগ্নি-বিদ্যা",
    6: "ষষ্ঠ অধ্যায় · সৎ-বিদ্যা ও «তৎ ত্বম্ অসি»",
    7: "সপ্তম অধ্যায় · নারদ-সনৎকুমার সংবাদ ও ভূমা-বিদ্যা",
    8: "অষ্টম অধ্যায় · দহর-বিদ্যা ও প্রজাপতি-ইন্দ্র সংবাদ",
}

EN_MACRONS = str.maketrans({"â": "ā", "î": "ī", "û": "ū", "Â": "Ā", "Î": "Ī", "Û": "Ū"})

SBE_PATCHES_EN = {
    (2, 13): {
        1: (
            "He whom one invites to sing is the Hiṅkāra; he whom one informs is the "
            "Prastāva; he who lies down with his wife is the Udgītha; he who lies down "
            "opposite his wife is the Pratihāra; the union itself is the Nidhana, and the "
            "completion is the Nidhana. This is the Vāmadevya Sāman as interwoven in generation."
        ),
        2: (
            "He who thus knows this Vāmadevya Sāman as interwoven in generation becomes "
            "united in pairs, procreates at every union, reaches full life, lives long, "
            "becomes great with offspring and cattle, and great in fame. His rule is: "
            "'Let him not turn away any woman.'"
        ),
    }
}


def clean_sk(s: str) -> str:
    s = re.sub(
        r"^(?:(?:प्रथम|द्वितीय|तृतीय|चतुर्थ|पञ्चम|षष्ठ|सप्तम|अष्टम)ोऽध्यायः\s*)?॥\s*",
        "",
        s.strip(),
    )
    s = re.sub(r"(?:॥\s*[०-९]+\s*)?॥?\s*$", "", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    if not s.endswith("।"):
        s = s + " ॥"
    else:
        s = s[:-1].rstrip() + " ॥"
    return s


def clean_bn(s: str) -> str:
    s = s.replace("\u09f0", "র").replace("\u200c", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def clean_en(s: str) -> str:
    s = s.translate(EN_MACRONS)
    s = re.sub(r"\[paragraph continues\]", " ", s)
    s = re.sub(r"(?<=[A-Za-zāīūĀĪŪ)\]])\s+\d+\s*(?=[.,;:!?'\"])", "", s)
    s = re.sub(r"(^|\s)p\.\s*\d+[a-z]?(?=\s|$)", " ", s)
    s = re.sub(r"\s*[,;]\s*--\s*", " — ", s)
    s = re.sub(r"\s*--\s*", " — ", s)
    s = re.sub(r",,+", ",", s)
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_sk_map(dg: dict) -> dict[tuple[int, int, int], str]:
    raw_map: dict[str, str] = {}
    for ch in dg["chapters"]:
        for v in ch["verses"]:
            raw_map[v["number"]] = v["sanskrit"]

    # ৩.১৩.৭ + ৩.১৩.৮ একত্রীকরণ (GRETIL ও বাংলা পাঠ-সম্মত)
    s3138 = raw_map.pop("3.13.8").replace("यत्रितदस्मिञ्छरीरे", "यत्रैतदस्मिञ्छरीरे")
    raw_map["3.13.7"] = raw_map["3.13.7"].rstrip() + " " + s3138.lstrip()

    # ৫.১৭ বিভাজন ('90.1' ভেতরে ৫.১৭.১ ও ৫.১৭.২ একসাথে ছিল)
    v90 = raw_map.pop("90.1")
    parts = re.split(r"\s*५\.१७\.१॥\s*", v90)
    assert len(parts) == 2
    raw_map["5.17.1"] = parts[0].replace("मुपस्स", "मुपास्स")
    raw_map["5.17.2"] = re.sub(r"\s*५\.१७\.२\s*$", "", parts[1])

    # ৬.৬.৬ -> ৬.৬.৫
    raw_map["6.6.5"] = raw_map.pop("6.6.6")

    # ছাপাখানা-ত্রুটি সংশোধন
    raw_map["4.17.1"] = raw_map["4.17.1"].replace("अन्तरिक्षातादित्यं", "अन्तरिक्षादादित्यं")
    raw_map["6.8.6"] = raw_map["6.8.6"].replace("स्यादन्यत्राद्भ्य्ऽद्भिः", "स्यादन्यत्राद्भ्यः । अद्भिः")

    out: dict[tuple[int, int, int], str] = {}
    for k, val in raw_map.items():
        a, b, c = map(int, k.split("."))
        out[(a, b, c)] = clean_sk(val)
    return out


def load_bn_data() -> tuple[dict[tuple[int, int, int], str], dict[tuple[int, int], str]]:
    verses: dict[tuple[int, int, int], str] = {}
    titles: dict[tuple[int, int], str] = {}
    for ch_i in range(1, 9):
        raw = (BN_DIR / f"chandogya_ch{ch_i}_bn.txt").read_text(encoding="utf-8")
        cur_id: tuple[int, int, int] | None = None
        buf: list[str] = []
        pending_title: str | None = None
        seen_khandas: set[int] = set()
        for ln in raw.splitlines():
            hm = re.match(r"^##\s*(.+?)\s*$", ln)
            if hm:
                if cur_id is not None:
                    verses[cur_id] = clean_bn("\n".join(buf))
                    cur_id, buf = None, []
                t = hm.group(1)
                t = re.sub(r"^.+?খণ্ড\s*[–—-]\s*", "", t).strip()
                pending_title = t
                continue
            vm = re.match(r"^\[(\d+)\.(\d+)\.(\d+)\]\s*(.*)$", ln)
            if vm:
                if cur_id is not None:
                    verses[cur_id] = clean_bn("\n".join(buf))
                a, b, c = int(vm.group(1)), int(vm.group(2)), int(vm.group(3))
                cur_id = (a, b, c)
                buf = [vm.group(4)]
                if (a, b) not in titles and pending_title:
                    titles[(a, b)] = pending_title
                    pending_title = None
                seen_khandas.add(b)
            elif cur_id is not None and ln.strip():
                buf.append(ln)
        if cur_id is not None:
            verses[cur_id] = clean_bn("\n".join(buf))
    return verses, titles


def parse_ch_sbe_page(kh: tuple[int, int], fn: pathlib.Path) -> dict[int, str]:
    if kh in SBE_PATCHES_EN:
        return {k: clean_en(v) for k, v in SBE_PATCHES_EN[kh].items()}
    raw = fn.read_text(encoding="utf-8", errors="replace")
    raw = re.split(r"<HR>\s*<H3[^>]*>\s*Footnotes", raw, flags=re.I)[0]
    raw = re.sub(r"<HEAD>.*?</HEAD>", "", raw, flags=re.I | re.S)
    raw = re.sub(r'<a\s+name="page_\d+"[^>]*>.*?</a>', "", raw, flags=re.I | re.S)
    raw = re.sub(r'<A\s+NAME="fr_\d+"[^>]*>.*?</A>', "", raw, flags=re.I | re.S)
    raw = re.sub(r'<A\s+HREF="#fn_\d+"[^>]*>.*?</A>', "", raw, flags=re.I | re.S)
    raw = re.sub(r'<span\s+class="contnote">.*?</span>', "", raw, flags=re.I | re.S)
    ps = re.findall(r"<p\b[^>]*>(.*?)</p>", raw, flags=re.I | re.S)
    clean_ps: list[str] = []
    for p in ps:
        t = htmllib.unescape(htmllib.unescape(re.sub(r"<[^>]+>", "", p)))
        t = re.sub(r"\s+", " ", t).strip()
        if not t or t.startswith(("Sacred Texts", "The Upanishads, Part", "Buy this Book", "p. ", "Next:", "___")):
            continue
        clean_ps.append(t)

    verses: dict[int, str] = {}
    cur: int | None = None
    buf: list[str] = []
    for t in clean_ps:
        m = re.match(r"^[:\s]*(\d+)\.\s*(.*)$", t)
        if m:
            if cur is not None:
                verses[cur] = " ".join(buf).strip()
            cur = int(m.group(1))
            buf = [m.group(2)] if m.group(2) else []
        elif cur is None and kh in ((1, 3), (5, 10)):
            cur = 1
            buf = [t]
        elif cur is not None:
            if kh == (3, 11) and cur == 5 and t.startswith("But no one should tell"):
                verses[cur] = " ".join(buf).strip(); cur = 6; buf = [t]
            elif kh == (4, 8) and cur == 3 and t.startswith("'He who knows this and meditates on the foot"):
                verses[cur] = " ".join(buf).strip(); cur = 4; buf = [t]
            elif kh == (4, 10) and cur == 2 and t.startswith("The student from sorrow"):
                verses[cur] = " ".join(buf).strip(); cur = 3; buf = [t]
            elif kh == (5, 24) and cur == 4 and t.startswith("'As hungry children"):
                verses[cur] = " ".join(buf).strip(); cur = 5; buf = [t]
            elif kh == (6, 15) and cur == 2 and t.startswith("'That which is the subtile essence"):
                verses[cur] = " ".join(buf).strip(); cur = 3; buf = [t]
            elif kh == (6, 16) and cur == 2 and t.startswith("'As that (truthful) man"):
                verses[cur] = " ".join(buf).strip(); cur = 3; buf = [t]
            elif kh == (8, 2) and cur == 9 and t.startswith("'Whatever object he is attached"):
                verses[cur] = " ".join(buf).strip(); cur = 10; buf = [t]
            elif kh == (8, 5) and cur == 3 and t.startswith("Now that world of Brahman"):
                verses[cur] = " ".join(buf).strip(); cur = 4; buf = [t]
            elif kh == (8, 6) and cur == 5 and t.startswith("And while his mind is failing"):
                verses[cur] = " ".join(buf).strip(); cur = 6; buf = [t]
            elif kh == (8, 7) and cur == 3 and t.startswith("Pragâpati said to them:"):
                verses[cur] = " ".join(buf).strip(); cur = 4; buf = [t]
            elif kh == (8, 12) and cur == 5 and t.startswith("'The Devas who are in the world"):
                verses[cur] = " ".join(buf).strip(); cur = 6; buf = [t]
            else:
                buf.append(t)
    if cur is not None:
        verses[cur] = " ".join(buf).strip()

    if kh == (1, 3) and 11 in verses:
        t = verses[11]
        i = t.find("Lastly, having approached himself")
        assert i > 0
        verses[11], verses[12] = t[:i].strip(), t[i:].strip()
    elif kh == (2, 23):
        verses = {1: verses[1] + " " + verses[2], 2: verses[3], 3: verses[4]}
    elif kh == (3, 13):
        verses[7] = verses[7] + " " + verses.pop(8)
    elif kh == (4, 15):
        verses[5] = verses[5] + " " + verses.pop(6)
    elif kh == (4, 17):
        t = verses[9]
        i = t.find("'He saves the Kurus")
        assert i > 0
        verses[9], verses[10] = t[:i].strip(), t[i:].strip()
    elif kh == (5, 2):
        verses[7] = verses[7] + " " + verses[8]
        verses[8] = verses.pop(9)

    return {k: clean_en(v) for k, v in verses.items()}


def build_preface(raw: str) -> tuple[str, str]:
    m_sk = re.search(r"##\s*শান্তিপাঠঃ\s*\n(.+?)\nসরলার্থ\s*:", raw, re.S)
    m_sar = re.search(r"সরলার্থ\s*:\s*(.+?)\n##\s*সূচনা", raw, re.S)
    m_bhu = re.search(r"##\s*সূচনা[^\n]*\n(.+)$", raw, re.S)
    assert m_sk and m_sar and m_bhu, "ছান্দোগ্য ভূমিকা অসম্পূর্ণ"
    parts = [
        "শান্তিপাঠঃ\n" + m_sk.group(1).strip() + "\n" + clean_bn(m_sar.group(1)),
        "সূচনা\n" + "\n\n".join(
            clean_bn(p) for p in re.split(r"\n\s*\n", m_bhu.group(1).strip()) if p.strip()
        ),
    ]
    return "শান্তিপাঠ ও সূচনা", "\n\n".join(parts)


def main() -> int:
    for p in (DG_CH_JSON, SBE_DIR, PRE_TXT):
        if not p.exists():
            raise SystemExit(f"উৎস নেই: {p}")

    dg = json.loads(DG_CH_JSON.read_text(encoding="utf-8"))
    sk_map = load_sk_map(dg)
    bn_map, titles = load_bn_data()
    assert set(sk_map) == set(bn_map), f"SK vs BN mismatch: {set(sk_map) ^ set(bn_map)}"

    khandas = sorted({(a, b) for (a, b, _) in bn_map})
    assert len(khandas) == 154

    en_map: dict[tuple[int, int, int], str] = {}
    for idx, (a, b) in enumerate(khandas):
        fn = SBE_DIR / f"sbe01{22 + idx:03d}.htm"
        parsed = parse_ch_sbe_page((a, b), fn)
        for c, val in parsed.items():
            en_map[(a, b, c)] = val
    assert set(en_map) == set(bn_map), f"EN vs BN mismatch: {set(en_map) ^ set(bn_map)}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    heading, preface = build_preface(PRE_TXT.read_text(encoding="utf-8"))
    ch_metas = []
    total = 0
    total_khandas = 0

    for ch in range(1, 9):
        want_kh, want_n = EXPECTED_CH_COUNTS[ch]
        ch_khs = sorted({b for (a, b, _) in bn_map if a == ch})
        assert len(ch_khs) == want_kh and ch_khs == list(range(1, want_kh + 1))

        suktas = []
        verses = []
        en_verses = {}
        seq = 0

        for kh in ch_khs:
            mantra_nums = sorted(c for (a, b, c) in bn_map if a == ch and b == kh)
            assert mantra_nums == list(range(1, len(mantra_nums) + 1))
            s_from = seq + 1
            for vn in mantra_nums:
                seq += 1
                sk = sk_map[(ch, kh, vn)]
                bn = bn_map[(ch, kh, vn)]
                en = en_map[(ch, kh, vn)]

                assert sk and sk.endswith("॥"), f"{ch}.{kh}.{vn} sk invalid: {sk!r}"
                assert not re.search(r"[\u0980-\u09FFa-zA-Z0-9]", sk), f"{ch}.{kh}.{vn} leak in sk: {sk!r}"
                assert bn and "\u09f0" not in bn and not re.search(r"[\u0900-\u0963\u0966-\u097F]", bn), f"{ch}.{kh}.{vn} bn invalid"
                assert en and "_" not in en and not re.search(r"[âîûÂÎÛ\u0900-\u09FF]", en), f"{ch}.{kh}.{vn} en invalid: {en!r}"

                v_obj: dict = {"n": seq, "ch": kh, "vn": vn, "sk": sk, "bn": bn}
                if vn == 1 and (ch, kh) in titles:
                    v_obj["hd"] = titles[(ch, kh)]
                verses.append(v_obj)
                en_verses[str(seq)] = en

            suktas.append({
                "id": kh,
                "from": s_from,
                "to": seq,
                "vfrom": 1,
                "vto": len(mantra_nums),
                "mantra": len(mantra_nums),
            })

        assert seq == want_n, f"ch {ch}: got {seq}, want {want_n}"
        total += seq
        total_khandas += want_kh

        ch_obj: dict = {
            "id": ch,
            "bn": CHAPTER_NAMES[ch],
            "count": seq,
            "from": 1,
            "to": seq,
            "withBn": seq,
            "suktaCount": want_kh,
            "groupWord": "খণ্ড",
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
            "suktaCount": want_kh,
            "aligned": want_kh,
            "grid": {"count": want_kh},
        }
        if ch == 1:
            meta["prefaceCount"] = 1
        ch_metas.append(meta)

    index_obj = {
        "slug": "chandogya",
        "bn": "ছান্দোগ্য উপনিষদ",
        "en": "Chandogya Upanishad",
        "total": total,
        "withBn": total,
        "withSk": total,
        "withEn": total,
        "suktaTotal": total_khandas,
        "verseWord": "মন্ত্র",
        "groupWord": "খণ্ড",
        "chword": "অধ্যায়",
        "skSrc": "মূল সংস্কৃত পাঠ — বহুমূল নিরীক্ষিত (sanskritdocuments.org chhaandogya.itx, GRETIL ও dharma-granth দেবনাগরী)",
        "bnSrc": "বাংলা সরলার্থ — ebanglalibrary.com («ছান্দোগ্য উপনিষদ»)",
        "enSrc": "ইংরেজি অনুবাদ — F. Max Müller (Sacred Books of the East, Vol. 1, 1879)",
        "note": "৮ অধ্যায় ও ১৫৪ খণ্ডের সম্পূর্ণ ৬২৮ মন্ত্র মূল সংস্কৃত, বাংলা সরলার্থ ও ইংরেজি অনুবাদসহ; শুরুতে শান্তিপাঠ ও সূচনা আলাদা ব্লকে রাখা হয়েছে।",
        "chapters": ch_metas,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index_obj, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"✓ chandogya: 8 অধ্যায়, {total_khandas} খণ্ড, {total} মন্ত্র (সংস্কৃত+বাংলা+ইংরেজি)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
