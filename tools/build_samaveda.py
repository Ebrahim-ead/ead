#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""সামবেদ (কৌথুমী সংহিতা) ডেটা-নির্মাতা — assets/grantho/data/samaveda/

উৎস ও নীতি (অনুমানভিত্তিক পাঠ বর্জন):
  ১. সংস্কৃত মূল পাঠ (সস্বর দেবনাগরী): sanchaya/Samaveda/Kauthuma Samhita saswara.txt —
     ২৮ অধ্যায়, ৪৬৮ দশতি/সূক্ত, ১,৮৭৫ মন্ত্রের সবগুলোতে। প্রতীক/পুনরাবৃত্ত মন্ত্রে
     প্রথম প্রামাণিক উচ্চারণের সস্বর মূল দিয়ে সম্পূর্ণ করা হয়েছে (কোনো কল্পিত পাঠ নয়)।
  ২. বাংলা অনুবাদ (`bn`): ebanglalibrary.com-এর দুর্গাদাস লাহিড়ী অনূদিত ১,৮৭৫/১,৮৭৫
     মন্ত্র (/tmp/sv_test/bn_raw/ — ১.১–১.৬, ২.০ ও ৩.০১–৩.২১)।
  ৩. ইংরেজি অনুবাদ (`en/ch1..28.json`): Ralph T.H. Griffith (১৮৯৩, DharmicData /
     sacred-texts)-এর ১,৭৯৪টি প্রত্যক্ষ মন্ত্র + হুবহু অভিন্ন পুনরাবৃত্ত মন্ত্রের
     নিরীক্ষিত মিল; যেখানে Griffith অনুবাদ করেননি (যেমন আরণ্যক ও মহানাম্নীর
     অপুনরাবৃত্ত মন্ত্র এবং কয়েকটি ছাঁটা মন্ত্র) সেখানে অনুমান করে বসানো হয়নি।
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "grantho" / "data" / "samaveda"
EN_DIR = OUT_DIR / "en"

SANCHAYA_TXT = pathlib.Path(os.environ.get(
    "SV_SANCHAYA",
    "/tmp/sv_test/sanchaya/Samaveda/Kauthuma Samhita saswara.txt",
))
DD_JSON = pathlib.Path(os.environ.get(
    "SV_DD_JSON",
    "/tmp/sv_test/DharmicData/Samaveda/Samaveda.json",
))
BN_RAW_DIR = pathlib.Path(os.environ.get(
    "SV_BN_DIR",
    "/tmp/sv_test/bn_raw",
))

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
DEVA_RE = re.compile(r"[\u0900-\u097F]")

DEITY_MAP = {
    "Agni": "অগ্নি",
    "Indra": "ইন্দ্র",
    "Soma Pavamana": "পবমান সোম",
    "Mitra-Varuna": "মিত্র ও বরুণ",
    "Mitra Varuna": "মিত্র ও বরুণ",
    "Mitra-Varuva": "মিত্র ও বরুণ",
    "Asvins": "অশ্বিদ্বয়",
    "Dawn": "ঊষা",
    "Maruts": "মরুৎগণ",
    "Vishnu": "বিষ্ণু",
    "Surya": "সূর্য",
    "Sarasvati": "সরস্বতী",
    "Sarasvan": "সরস্বান",
    "Indra-Agni": "ইন্দ্র ও অগ্নি",
    "Indra Agni": "ইন্দ্র ও অগ্নি",
    "Agni Indra": "ইন্দ্র ও অগ্নি",
    "Gods": "বিশ্বদেবগণ",
    "Visvedevas": "বিশ্বদেবগণ",
    "Heaven and Earth": "দ্যাবাপৃথিবী",
    "Vata": "বায়ু",
    "Vayu, Indra and Vayu": "বায়ু ও ইন্দ্র-বায়ু",
    "The Waters": "জলদেবী অপ্",
    "Vena": "বেন",
    "Pusan": "পূষা",
    "Varuna": "বরুণ",
    "Visvakarman": "বিশ্বকর্মা",
    "Adityas": "আদিত্যগণ",
    "Indra Adityas": "ইন্দ্র ও আদিত্যগণ",
    "Brihaspati. Indra": "বৃহস্পতি ও ইন্দ্র",
    "Indra. Brihaspati": "বৃহস্পতি ও ইন্দ্র",
    "Indra. All-Gods": "ইন্দ্র ও বিশ্বদেবগণ",
    "Indra. Dadhikravan": "ইন্দ্র ও দধিক্রাবা",
    "Indra.Maruts": "ইন্দ্র ও মরুৎগণ",
    "Indra and others": "ইন্দ্র প্রমুখ",
    "Agni and others": "অগ্নি প্রমুখ",
    "Mitra, Varuna, Aryaman": "মিত্র, বরুণ ও অর্যমা",
    "Oblations": "হবি",
    "Soma Vaisvanara": "সোম ও বৈশ্বানর",
    "Soma, Varuna": "সোম ও বরুণ",
    "Svitar. Brahmapaspati. Agni": "সবিতা, ব্রহ্মণস্পতি ও অগ্নি",
    "Agha": "অপ্বা ও ইন্দ্র",
}

PURVA_TITLES = {
    1: "১.১ আগ্নেয় পর্ব — প্রথম অধ্যায়",
    2: "১.২ ঐন্দ্র পর্ব — দ্বিতীয় অধ্যায়",
    3: "১.৩ ঐন্দ্র পর্ব — তৃতীয় অধ্যায়",
    4: "১.৪ ঐন্দ্র পর্ব — চতুর্থ অধ্যায়",
    5: "১.৫ পবমান পর্ব — পঞ্চম অধ্যায়",
    6: "১.৬ আরণ্যক পর্ব — ষষ্ঠ অধ্যায়",
    7: "২.০ মহানাম্নী আর্চিক",
}

BN_ORD = {
    1: "প্রথম", 2: "দ্বিতীয়", 3: "তৃতীয়", 4: "চতুর্থ", 5: "পঞ্চম",
    6: "ষষ্ঠ", 7: "সপ্তম", 8: "অষ্টম", 9: "নবম", 10: "দশম",
    11: "একাদশ", 12: "দ্বাদশ", 13: "ত্রয়োদশ", 14: "চতুর্দশ", 15: "পঞ্চদশ",
    16: "ষোড়শ", 17: "সপ্তদশ", 18: "অষ্টাদশ", 19: "ঊনবিংশ", 20: "বিংশ",
    21: "একবিংশ",
}

ARANYAKA_DEITIES = {
    1: "ইন্দ্র, বরুণ ও সোম",
    2: "অগ্নি ও পুরুষ",
    3: "পুরুষ ও বিরাট",
    4: "দ্যাবাপৃথিবী ও ইন্দ্র",
    5: "অগ্নি ও সূর্য",
}


def bn_dig(n: int) -> str:
    return str(n).translate(BN_DIGITS)


def norm_sk(s: str) -> str:
    return re.sub(r"[\u0951-\u0954\u1CD0-\u1CFF\uA8E0-\uA8FF\u0964\u0965०-९0-9\s।॥ॐऽ.*()?\-]", "", s)


def clean_sk(s: str) -> str:
    s = s.replace(".?.", "").replace("??", "").replace("?", "")
    s = re.sub(r"ð[^(\s]*\(स्वाः\)", "स्वाः", s)
    s = re.sub(r"\(शि\)", "", s)
    s = re.sub(r"1\s+5\s+1\s+0305c", "", s)
    s = re.sub(r"\b\d\.\d+\.\d+\.\d+\s*", "", s)
    s = re.sub(r"।\s*\d+\s*\(?[\u0905-\u094F]+\)?\s*।\s*।", "", s)
    s = re.sub(r"\(([^)]*?)\)\*?", r"\1", s)
    s = re.sub(r"([^\s।॥०-९0-9])[12456789]\b", r"\1", s)
    s = re.sub(r"([अ-ह][\u0900-\u097F\uA8E0-\uA8FF]*)3", r"\1३", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_bn(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def split_mahanamni_bn(grouped: dict[str, str]) -> list[str]:
    """02_00.json-এর [1-3], [4-6], [7-9], [10] কে হুবহু ১০টি একক মন্ত্রে পৃথক করা।"""
    out: list[str] = []

    # [1-3]: ; দিয়ে ৩ মন্ত্র পৃথক (৩য় মন্ত্রটি "(মন্ত্রটি ...)"-এ শেষ হয়)
    t13 = grouped["1-3"]
    # ১ম: "... প্রদান করুন;" ; ২য়: "সর্বজ্ঞ হে দেব! ... সিদ্ধি প্রদান করুন;" ; ৩য়: "রক্ষাস্ত্রধারী ...।"
    m1 = re.split(r"(?=সর্বজ্ঞ হে দেব! দিব্যজ্যোতিঃসম্পন্ন)|(?=রক্ষাস্ত্রধারী হে দেব! আমাদের ধনদান)", t13)
    m1 = [clean_bn(x) for x in m1 if clean_bn(x)]
    assert len(m1) == 3, f"Mahanamni 1-3 split failed: {len(m1)}"
    # প্রথম দুটি পাদ শেষে ";" → "।" করা (শুদ্ধ পাঠবিভাজন)
    for x in m1:
        out.append(re.sub(r";\s*$", "।", x))

    # [4-6] ও [7-9]: প্রতিটি উপমন্ত্রে "(মন্ত্রটি ... )।" চিহ্ন রয়েছে
    for key in ("4-6", "7-9"):
        blk = grouped[key]
        parts = re.findall(r".*?\(মন্ত্রটি [^)]+\)\।", blk)
        parts = [clean_bn(x) for x in parts if clean_bn(x)]
        assert len(parts) == 3, f"Mahanamni {key} split failed: {len(parts)}"
        out.extend(parts)

    out.append(clean_bn(grouped["10"]))
    assert len(out) == 10
    return out


def parse_sanchaya() -> tuple[dict[int, str], list[list[str]]]:
    lines = SANCHAYA_TXT.read_text(encoding="utf-8", errors="ignore").splitlines()
    u_start = next(i for i, l in enumerate(lines) if l.strip().startswith("2.1.1"))
    hdr_idxs = [i for i, l in enumerate(lines) if i >= u_start and re.match(r"^\s*\d\.\d+\.\d+", l.strip())]

    # পূর্বার্চিক + আরণ্যক + মহানাম্নী (১..৬৫০)
    p_clean = []
    for l in lines[:u_start]:
        s = l.strip()
        if not s or "/" in s or re.match(r"^(सामवेद|पूर्वार्चिक|उत्तरार्चिक|इति\s|आरण्यक|महान|\[|1\.|2\.|\(|@|॥)", s):
            continue
        s = re.sub(r"(।\s*।\s*\d{1,3})\d\.\d+\.\d+\.\d+\s*$", r"\1", s)
        p_clean.append(s)
    p_chunks = re.split(r"।\s*।\s*(\d+)\s*(?:।\s*।)?", " ".join(p_clean))
    p_verses = {int(p_chunks[i + 1]): clean_sk(p_chunks[i]) for i in range(0, len(p_chunks) - 1, 2)}
    missing_p = [n for n in range(1, 651) if n not in p_verses]
    assert not missing_p, f"Missing Purvarchika verses: {missing_p}"

    # উত্তরার্চিক (২২ অর্ধ-প্রপাঠক → ১,২২৫ মন্ত্র)
    u_ardhas: list[list[str]] = []
    for h_i, start in enumerate(hdr_idxs):
        end = hdr_idxs[h_i + 1] if h_i + 1 < len(hdr_idxs) else len(lines)
        hdr = lines[start].strip()
        m_rng = re.search(r"\((\d+)\s*-\s*(\d+)\s*\)", hdr)
        a, b = int(m_rng.group(1)), int(m_rng.group(2))
        if hdr.startswith("2.6.1"):
            a = 1347
        exp = b - a + 1
        sec = []
        for l in lines[start + 1:end]:
            s = l.strip()
            if not s or s.startswith("उत्तरार्चिक") or s.startswith("[") or s.startswith("इति "):
                continue
            s = re.sub(r"\[[^\]]*\]", "", s)
            if "।।8 (हा)।।" in s and not re.search(r"।\s*।\s*\d+\s*।\s*।\s*।\s*।\s*8", s):
                s = s.replace("।।8 (हा)।।", "।।3 ।। ।।8 (हा)।।")
            s = re.sub(r"।\s*।\s*\d+(?:\s+\d+)?\s*(?:\([^)]+\)|[\u0905-\u094F]+)\s*।\s*।(?:\s*\d{3,4})?\s*$", "", s)
            s = re.sub(r"(।\s*।\s*\d+\s*।\s*।)\s*।\s*।\s*\d+\s*।\s*।(?:\s*\d{3,4})?\s*$", r"\1", s)
            s = re.sub(r"\(([^)]{10,}?)(?:।\s*।)?\s*\)\*?", r"__ABBR__\1", s)
            s = re.sub(r"।\s*(\d+)\s*।\s*(?=।\s*।)", r"।।\1 ", s)
            s = re.sub(r"(।\s*।\s*\d+\s*।\s*।)\s*\d{3,4}\s*$", r"\1", s)
            sec.append(s)
        parts = re.split(r"।\s*।\s*(\d+)\s*(?:।\s*।)?", " ".join(sec))
        vs = [clean_sk(parts[i]) for i in range(0, len(parts) - 1, 2) if parts[i].strip()]
        assert len(vs) == exp, f"{hdr}: got {len(vs)} vs expected {exp}"
        u_ardhas.append(vs)

    # হুবহু স্বর-সমৃদ্ধ পাঠ দিয়ে প্রতীক (__ABBR__) পুনরাবৃত্ত মন্ত্রগুলোর স্বর পুনরুদ্ধার
    accented_pool: dict[str, str] = {}
    for gid in range(1, 651):
        accented_pool[norm_sk(p_verses[gid])] = p_verses[gid]
    for ardha in u_ardhas:
        for i, txt in enumerate(ardha):
            if "__ABBR__" in txt:
                unwrapped = txt.replace("__ABBR__", "")
                key = norm_sk(unwrapped)
                ardha[i] = accented_pool.get(key, unwrapped)
            else:
                accented_pool.setdefault(norm_sk(txt), txt)

    return p_verses, u_ardhas


def load_bn() -> tuple[dict[int, dict], dict[int, dict]]:
    """বাংলা সংগ্রহ লোড: পূর্বার্চিক+আরণ্যক+মহানাম্নী (১..৭) ও উত্তরার্চিক (১..২১)।"""
    purva_chs: dict[int, dict] = {}

    for ch in range(1, 7):
        dv: dict[int, dict[int, str]] = {}
        hdr = None
        for f in sorted(BN_RAW_DIR.glob(f"01_{ch:02d}*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("header") and not hdr:
                hdr = d["header"]
            for dk, dval in (d.get("dasati") or {}).items():
                for vk, vt in (dval or {}).items():
                    if vt and str(vt).strip():
                        dv.setdefault(int(dk), {})[int(vk)] = clean_bn(str(vt))
        purva_chs[ch] = {"dasatis": dv, "header": hdr}

    d2 = json.loads((BN_RAW_DIR / "02_00.json").read_text(encoding="utf-8"))
    h2 = json.loads((BN_RAW_DIR / "02_00_header.json").read_text(encoding="utf-8")).get("header")
    mahanamni_vs = split_mahanamni_bn(d2["grouped"])
    purva_chs[7] = {
        "dasatis": {
            1: {1: mahanamni_vs[0], 2: mahanamni_vs[1], 3: mahanamni_vs[2]},
            2: {1: mahanamni_vs[3], 2: mahanamni_vs[4], 3: mahanamni_vs[5]},
            3: {1: mahanamni_vs[6], 2: mahanamni_vs[7], 3: mahanamni_vs[8]},
            4: {1: mahanamni_vs[9]},
        },
        "header": h2,
    }

    uttara_chs: dict[int, dict] = {}
    for ch in range(1, 22):
        su: dict[int, dict[int, str]] = {}
        p2: dict[int, dict[int, str]] = {}
        hdr = None
        p2_hdr = None
        for f in sorted(BN_RAW_DIR.glob(f"03_{ch:02d}_*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("header") and not hdr:
                hdr = d["header"]
            if d.get("part2_header") and not p2_hdr:
                p2_hdr = d["part2_header"]
            if d.get("rishi_tail") and hdr and "পরবর্তী খণ্ডে" in (hdr.get("rishi") or ""):
                hdr["rishi"] = hdr["rishi"].split("১৪..")[0].rstrip() + " " + d["rishi_tail"]
            for sk, sv in (d.get("suktas") or {}).items():
                for vk, vt in (sv or {}).items():
                    if vt and str(vt).strip():
                        su.setdefault(int(sk), {})[int(vk)] = clean_bn(str(vt))
            for sk, sv in (d.get("part2_suktas") or {}).items():
                for vk, vt in (sv or {}).items():
                    if vt and str(vt).strip():
                        p2.setdefault(int(sk), {})[int(vk)] = clean_bn(str(vt))
        uttara_chs[ch] = {"suktas": su, "part2_suktas": p2, "header": hdr, "part2_header": p2_hdr}

    return purva_chs, uttara_chs


def translate_deity(en_d: str | None) -> str:
    if not en_d or en_d == "None":
        return ""
    return DEITY_MAP.get(en_d, en_d)


def format_preface(hdr: dict | None, extra_hdr: dict | None = None) -> tuple[str, str]:
    if not hdr:
        return "", ""
    parts = []
    if hdr.get("deity"):
        parts.append(f"দেবতা: {clean_bn(hdr['deity'])}")
    if hdr.get("chhandas"):
        parts.append(f"ছন্দ: {clean_bn(hdr['chhandas'])}")
    if hdr.get("rishi"):
        parts.append(f"ঋষি: {clean_bn(hdr['rishi'])}")
    if extra_hdr:
        parts.append("— দ্বিতীয়াংশ —")
        if extra_hdr.get("deity"):
            parts.append(f"দেবতা: {clean_bn(extra_hdr['deity'])}")
        if extra_hdr.get("chhandas"):
            parts.append(f"ছন্দ: {clean_bn(extra_hdr['chhandas'])}")
        if extra_hdr.get("rishi"):
            parts.append(f"ঋষি: {clean_bn(extra_hdr['rishi'])}")
    preface = "\n\n".join(parts)
    return ("অনুক্রমণিকা (দেবতা · ছন্দ · ঋষি)" if preface else ""), preface


def main() -> int:
    for p in (SANCHAYA_TXT, DD_JSON, BN_RAW_DIR):
        if not p.exists():
            raise SystemExit(f"উৎস পাওয়া যায়নি: {p}")

    p_verses, u_ardhas = parse_sanchaya()
    purva_chs, uttara_chs = load_bn()
    dd = json.loads(DD_JSON.read_text(encoding="utf-8"))["verses"]
    dd1 = [v for v in dd if v["part"] == "FIRST PART"]
    dd2 = [v for v in dd if v["part"] != "FIRST PART"]

    # ১) ইংরেজি ম্যাপিং — পূর্বার্চিক (১..৫৮৫ এর ৫৭৭)
    dd1_decs: list[tuple[str, str, str, int]] = []
    dd1_by_dec: dict[tuple[str, str, str, int], list[dict]] = {}
    for v in dd1:
        k = (v["book"], v["chapter"], v["section"], v["hymn"])
        if k not in dd1_by_dec:
            dd1_decs.append(k)
            dd1_by_dec[k] = []
        dd1_by_dec[k].append(v)

    purva_dec_gids: list[tuple[int, int, list[int]]] = []
    pos = 1
    for ch in range(1, 6):
        for dk in sorted(purva_chs[ch]["dasatis"]):
            n = len(purva_chs[ch]["dasatis"][dk])
            purva_dec_gids.append((ch, dk, [pos + i for i in range(n)]))
            pos += n
    assert pos == 586 and len(purva_dec_gids) == len(dd1_decs) == 59

    en_by_gid: dict[int, str] = {}
    deity_by_purva_dec: dict[tuple[int, int], str] = {}
    for (ch, dk, gids), k in zip(purva_dec_gids, dd1_decs):
        d_names = []
        for v in dd1_by_dec[k]:
            gid = gids[v["verse"] - 1]
            en_by_gid[gid] = v["text"].strip()
            if v.get("deity"):
                td = translate_deity(v["deity"])
                if td and td not in d_names:
                    d_names.append(td)
        if d_names:
            deity_by_purva_dec[(ch, dk)] = ", ".join(d_names)

    # ২) ইংরেজি ম্যাপিং — উত্তরার্চিক (২২ অর্ধ-প্রপাঠক → ১,২২৫-এ ১,২১৭)
    dd2_bcs: list[tuple[str, str]] = []
    dd2_by_bc: dict[tuple[str, str], dict[int, list[dict]]] = {}
    for v in dd2:
        bc = (v["book"], v["chapter"])
        if bc not in dd2_by_bc:
            dd2_bcs.append(bc)
            dd2_by_bc[bc] = {}
        dd2_by_bc[bc].setdefault(v["hymn"], []).append(v)
    assert len(dd2_bcs) == 22

    # বাংলা থেকে উত্তরার্চিকের ২২ অর্ধ-প্রপাঠকের [(sukta_id, verse_no, bn_text)] গঠন
    u_bn_ardhas: list[list[tuple[int, int, str]]] = []
    for ch in range(1, 22):
        su = uttara_chs[ch]["suktas"]
        p2 = uttara_chs[ch]["part2_suktas"]
        if ch == 20:
            a1 = [(s, v, su[s][v]) for s in range(1, 19) for v in sorted(su[s])]
            a2 = [(1, v, su[19][v]) for v in sorted(su[19])] + [
                (s + 1, v, p2[s][v]) for s in sorted(p2) for v in sorted(p2[s])
            ]
            u_bn_ardhas.append(a1)
            u_bn_ardhas.append(a2)
        else:
            u_bn_ardhas.append([(s, v, su[s][v]) for s in sorted(su) for v in sorted(su[s])])

    # প্রতিটি অর্ধ-প্রপাঠকের প্রতিটি মন্ত্রে (sk, bn, en, deity) জোড়া লাগানো
    u_ardha_rows: list[list[dict]] = []
    for idx_a, (sk_vs, bn_vs, bc) in enumerate(zip(u_ardhas, u_bn_ardhas, dd2_bcs)):
        assert len(sk_vs) == len(bn_vs), f"ardha {idx_a} mismatch {len(sk_vs)}!={len(bn_vs)}"
        hmap = dd2_by_bc[bc]
        flat_dd = [v for h in sorted(hmap) for v in hmap[h]]
        rows = []
        if len(sk_vs) == len(flat_dd):
            for sk_t, (s_id, v_no, bn_t), dv in zip(sk_vs, bn_vs, flat_dd):
                rows.append({
                    "s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t,
                    "en": dv["text"].strip(), "deity": translate_deity(dv.get("deity")),
                })
        elif idx_a == 0:  # 2.1.1 (3.01): H10.3 বাদ
            for sk_t, (s_id, v_no, bn_t) in zip(sk_vs, bn_vs):
                dv_list = [x for x in hmap.get(s_id, []) if x["verse"] == v_no]
                en_t = dv_list[0]["text"].strip() if dv_list else ""
                dt = translate_deity(hmap[s_id][0].get("deity")) if s_id in hmap else ""
                rows.append({"s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t, "en": en_t, "deity": dt})
        elif idx_a == 2:  # 2.2.1 (3.03): H1.3 বাদ
            for sk_t, (s_id, v_no, bn_t) in zip(sk_vs, bn_vs):
                dv_list = [x for x in hmap.get(s_id, []) if x["verse"] == v_no]
                en_t = dv_list[0]["text"].strip() if dv_list else ""
                dt = translate_deity(hmap[s_id][0].get("deity")) if s_id in hmap else ""
                rows.append({"s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t, "en": en_t, "deity": dt})
        elif idx_a == 6:  # 2.4.1 (3.07): H24.2, H24.3 বাদ
            for sk_t, (s_id, v_no, bn_t) in zip(sk_vs, bn_vs):
                dv_list = [x for x in hmap.get(s_id, []) if x["verse"] == v_no]
                en_t = dv_list[0]["text"].strip() if dv_list else ""
                dt = translate_deity(hmap[s_id][0].get("deity")) if s_id in hmap else ""
                rows.append({"s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t, "en": en_t, "deity": dt})
        elif idx_a == 12:  # 2.6.3 (3.13): S10..12 = H10[1..3], S13..15 = H11..13, S16 = H14[1, _, 3], S17..20 = H15..18
            for sk_t, (s_id, v_no, bn_t) in zip(sk_vs, bn_vs):
                if s_id <= 9:
                    h_id, h_v = s_id, v_no
                elif s_id in (10, 11, 12):
                    h_id, h_v = 10, s_id - 9
                elif s_id in (13, 14, 15):
                    h_id, h_v = s_id - 2, v_no
                elif s_id == 16:
                    h_id, h_v = 14, v_no
                else:
                    h_id, h_v = s_id - 2, v_no
                dv_list = [x for x in hmap.get(h_id, []) if x["verse"] == h_v]
                en_t = dv_list[0]["text"].strip() if dv_list else ""
                dt = translate_deity(hmap[h_id][0].get("deity")) if h_id in hmap else ""
                if s_id == 10:
                    dt = "সবিতা"
                elif s_id == 11:
                    dt = "ব্রহ্মণস্পতি"
                elif s_id == 12:
                    dt = "অগ্নি"
                rows.append({"s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t, "en": en_t, "deity": dt})
        elif idx_a == 14:  # 2.7.2 (3.15): H4 skipped, H6[1,2], H8[1,(2+3)], H9 empty -> S9..14 = H10..15 (সকলই অগ্নি)
            for sk_t, (s_id, v_no, bn_t) in zip(sk_vs, bn_vs):
                if s_id <= 3:
                    en_t = hmap[s_id][v_no - 1]["text"].strip()
                elif s_id == 4:
                    en_t = ""
                elif s_id == 5:
                    en_t = hmap[5][v_no - 1]["text"].strip()
                elif s_id == 6:
                    en_t = hmap[6][v_no - 1]["text"].strip() if v_no <= 2 else ""
                elif s_id == 7:
                    en_t = hmap[7][v_no - 1]["text"].strip()
                elif s_id == 8:
                    en_t = hmap[8][0]["text"].strip() if v_no == 1 else (
                        hmap[8][1]["text"].strip() + " " + hmap[8][2]["text"].strip()
                    )
                else:
                    h_id = s_id + 1  # S9->H10, S10->H11, S11->H12, S12->H13, S13->H14, S14->H15
                    en_t = hmap[h_id][v_no - 1]["text"].strip()
                rows.append({"s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t, "en": en_t, "deity": "অগ্নি"})
        elif idx_a == 18:  # 2.8.3 (3.19): H1[2,3]
            for sk_t, (s_id, v_no, bn_t) in zip(sk_vs, bn_vs):
                dv_list = [x for x in hmap.get(s_id, []) if x["verse"] == v_no]
                en_t = dv_list[0]["text"].strip() if dv_list else ""
                dt = translate_deity(hmap[s_id][0].get("deity")) if s_id in hmap else ""
                rows.append({"s": s_id, "v": v_no, "sk": sk_t, "bn": bn_t, "en": en_t, "deity": dt})
        else:
            raise AssertionError(f"অপ্রত্যাশিত পার্থক্য অর্ধ-প্রপাঠক {idx_a}")
        u_ardha_rows.append(rows)

    # ৩) অভিন্ন সংস্কৃত পুনরাবৃত্তিতে ইংরেজি পুল সমৃদ্ধ করা (অনুমান নয় — হুবহু অভিন্ন মূল পাঠ)
    sk_en_pool: dict[str, str] = {}
    for gid, en_t in en_by_gid.items():
        if en_t:
            sk_en_pool.setdefault(norm_sk(p_verses[gid]), en_t)
    for rows in u_ardha_rows:
        for r in rows:
            if r["en"]:
                sk_en_pool.setdefault(norm_sk(r["sk"]), r["en"])

    # ৪) ২৮টি অধ্যায় চূড়ান্ত বিন্যাস
    chapters_out: list[dict] = []

    # চ্যাপ্টার ১..৭ (পূর্বার্চিক ১..৫, আরণ্যক ৬, মহানাম্নী ৭)
    gid_cursor = 1
    for ch in range(1, 8):
        pinfo = purva_chs[ch]
        das = pinfo["dasatis"]
        verses = []
        suktas = []
        en_verses = {}
        deity_har = {}
        seq_n = 0
        for dk in sorted(das):
            s_from = seq_n + 1
            vdict = das[dk]
            for vk in sorted(vdict):
                seq_n += 1
                sk_t = p_verses[gid_cursor]
                bn_t = vdict[vk]
                en_t = en_by_gid.get(gid_cursor) or sk_en_pool.get(norm_sk(sk_t), "")
                gid_cursor += 1
                assert not DEVA_RE.search(en_t), f"ইংরেজিতে দেবনাগরী: ch{ch} {seq_n}"
                verses.append({"n": seq_n, "ch": dk, "vn": vk, "sk": sk_t, "bn": bn_t})
                if en_t:
                    en_verses[str(seq_n)] = en_t
            s_to = seq_n
            if ch <= 5:
                deity = deity_by_purva_dec.get((ch, dk), "")
                if not deity:
                    if (ch, dk) == (2, 11):
                        deity = "ইন্দ্র"
                    elif (ch, dk) == (3, 8):
                        deity = "ঊষা ও অশ্বিদ্বয়"
                    elif (ch, dk) == (3, 9):
                        deity = "ইন্দ্র"
            elif ch == 6:
                deity = ARANYAKA_DEITIES.get(dk, "")
            else:
                deity = "ইন্দ্র (ত্রৈলোক্য-আত্মা)"
            su_entry = {"id": dk, "from": s_from, "to": s_to, "vfrom": 1, "vto": len(vdict), "mantra": len(vdict)}
            if deity:
                su_entry["deity"] = deity
                deity_har[str(dk)] = deity
            suktas.append(su_entry)
        heading, preface = format_preface(pinfo.get("header"))
        chapters_out.append({
            "id": ch, "bn": PURVA_TITLES[ch], "verses": verses, "suktas": suktas,
            "en": en_verses, "deityHar": deity_har, "heading": heading, "preface": preface,
        })
    assert gid_cursor == 651

    # চ্যাপ্টার ৮..২৮ (উত্তরার্চিক ৩.০১..৩.২১ — ২৩তম অধ্যায় ৩.২০-তে প্রথমাংশ+দ্বিতীয়াংশ একত্র)
    ardha_idx = 0
    for uch in range(1, 22):
        ch_id = 7 + uch
        bn_title = f"৩.{bn_dig(uch).zfill(2) if uch < 10 else bn_dig(uch)} উত্তরার্চিক — {BN_ORD[uch]} অধ্যায়"
        if uch < 10:
            bn_title = f"৩.০{bn_dig(uch)} উত্তরার্চিক — {BN_ORD[uch]} অধ্যায়"
        else:
            bn_title = f"৩.{bn_dig(uch)} উত্তরার্চিক — {BN_ORD[uch]} অধ্যায়"

        if uch == 20:
            r1 = u_ardha_rows[ardha_idx]
            r2 = u_ardha_rows[ardha_idx + 1]
            ardha_idx += 2
            merged_rows = list(r1) + [{**r, "s": r["s"] + 18} for r in r2]
            heading, preface = format_preface(uttara_chs[uch]["header"], uttara_chs[uch]["part2_header"])
        else:
            merged_rows = u_ardha_rows[ardha_idx]
            ardha_idx += 1
            heading, preface = format_preface(uttara_chs[uch]["header"])

        by_su: dict[int, list[dict]] = {}
        for r in merged_rows:
            by_su.setdefault(r["s"], []).append(r)

        verses = []
        suktas = []
        en_verses = {}
        deity_har = {}
        seq_n = 0
        for s_id in sorted(by_su):
            s_from = seq_n + 1
            items = by_su[s_id]
            s_deity = ""
            for r in items:
                seq_n += 1
                en_t = r["en"] or sk_en_pool.get(norm_sk(r["sk"]), "")
                if not s_deity and r["deity"]:
                    s_deity = r["deity"]
                verses.append({"n": seq_n, "ch": s_id, "vn": r["v"], "sk": r["sk"], "bn": r["bn"]})
                if en_t:
                    en_verses[str(seq_n)] = en_t
            s_to = seq_n
            su_entry = {"id": s_id, "from": s_from, "to": s_to, "vfrom": 1, "vto": len(items), "mantra": len(items)}
            if s_deity:
                su_entry["deity"] = s_deity
                deity_har[str(s_id)] = s_deity
            suktas.append(su_entry)

        chapters_out.append({
            "id": ch_id, "bn": bn_title, "verses": verses, "suktas": suktas,
            "en": en_verses, "deityHar": deity_har, "heading": heading, "preface": preface,
        })
    assert ardha_idx == 22

    # ৫) আউটপুট লেখা
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    chapters_meta = []
    tot_v = tot_sk = tot_bn = tot_en = tot_su = 0

    for ch in chapters_out:
        cid = ch["id"]
        cnt = len(ch["verses"])
        k_bn = sum(1 for v in ch["verses"] if v["bn"])
        k_sk = sum(1 for v in ch["verses"] if v["sk"])
        k_en = len(ch["en"])
        ch_obj = {
            "id": cid,
            "bn": ch["bn"],
            "count": cnt,
            "from": 1,
            "to": cnt,
            "withBn": k_bn,
            "suktaCount": len(ch["suktas"]),
            "groupWord": "সূক্ত",
            "suktas": ch["suktas"],
            "verses": ch["verses"],
        }
        if ch["preface"]:
            ch_obj["heading"] = ch["heading"]
            ch_obj["preface"] = ch["preface"]

        (OUT_DIR / f"ch{cid}.json").write_text(
            json.dumps(ch_obj, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        (EN_DIR / f"ch{cid}.json").write_text(
            json.dumps({"id": cid, "verses": ch["en"]}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        s_with_en = sum(
            1 for s_m in ch["suktas"]
            if any(str(nn) in ch["en"] for nn in range(s_m["from"], s_m["to"] + 1))
        )
        ch_meta = {
            "id": cid,
            "bn": ch["bn"],
            "count": cnt,
            "from": 1,
            "to": cnt,
            "withBn": k_bn,
            "suktaCount": len(ch["suktas"]),
            "aligned": s_with_en,
            "grid": {"count": len(ch["suktas"])},
        }
        if ch["preface"]:
            ch_meta["prefaceCount"] = 1
        if ch["deityHar"]:
            ch_meta["deityHar"] = ch["deityHar"]
        chapters_meta.append(ch_meta)

        tot_v += cnt
        tot_sk += k_sk
        tot_bn += k_bn
        tot_en += k_en
        tot_su += len(ch["suktas"])

    def commas_bn(num: int) -> str:
        return f"{num:,}".translate(BN_DIGITS)

    idx_obj = {
        "slug": "samaveda",
        "bn": "সামবেদ সংহিতা",
        "en": "Samaveda (Kauthuma)",
        "total": tot_v,
        "withBn": tot_bn,
        "withSk": tot_sk,
        "withEn": tot_en,
        "suktaTotal": tot_su,
        "verseWord": "মন্ত্র",
        "groupWord": "সূক্ত",
        "chword": "অধ্যায়",
        "skSrc": "संस्कृत मूलम् (सस्वरा कौथुमीया संहिता) — sanchaya",
        "enSrc": "Ralph T.H. Griffith (1893)",
        "bnSrc": "বাংলা অনুবাদ ও মন্ত্রার্থ — দুর্গাদাস লাহিড়ী (ebanglalibrary.com)",
        "note": (
            f"কৌথুমী শাখার পূর্ণ সস্বর সংস্কৃত মূল পাঠ ({commas_bn(tot_sk)}/{commas_bn(tot_v)} মন্ত্র, "
            f"sanchaya); দুর্গাদাস লাহিড়ীর সম্পূর্ণ বাংলা অনুবাদ ({commas_bn(tot_bn)}/{commas_bn(tot_v)} মন্ত্র, "
            f"ebanglalibrary.com); ইংরেজি অনুবাদ R.T.H. Griffith ({commas_bn(tot_en)}/{commas_bn(tot_v)} মন্ত্র) — "
            "আরণ্যক ও মহানাম্নীর অপুনরাবৃত্ত যেসব মন্ত্রে Griffith-এর অনুবাদ নেই সেখানে অনুমান করে ইংরেজি বসানো হয়নি।"
        ),
        "chapters": chapters_meta,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(idx_obj, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    print(f"✓ {OUT_DIR.relative_to(ROOT)}: {len(chapters_meta)} অধ্যায়, {tot_su} সূক্ত, {tot_v} মন্ত্র")
    print(f"  Sanskrit: {tot_sk}/{tot_v} · English: {tot_en}/{tot_v} · Bengali: {tot_bn}/{tot_v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
