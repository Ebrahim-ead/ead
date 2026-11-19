#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""৫টি পুরাণের JSON ডেটা তৈরি: ব্রহ্ম, বিষ্ণু, ভবিষ্য, গরুড় ও ব্রহ্মাণ্ড পুরাণ।

উৎস (/tmp/gh_probe-এ সংরক্ষিত যাচাইকৃত প্রাথমিক ডিজিটাল সংস্করণ):
  · ব্রহ্ম, বিষ্ণু, গরুড়, ব্রহ্মাণ্ড: vishvAsa/purANam & telugu-purana-rag corpus_ws
  · বিষ্ণু পুরাণ ইংরেজি: M.N. Dutt (1896), Project Gutenberg #66208 (১২৬ অধ্যায়, ২৫৯ টীকা)
  · ভবিষ্য পুরাণ: HinduScriptures (sa.wikisource.org) + অনুপস্থিত ৩.২.২১ ও ৩.৪.১২ সরাসরি উইকিসোর্স থেকে

নীতি: পাঠ কখনো অনুমান করে পূরণ করা হয় না; শিরোনাম, বক্তা ও পুষ্পিকা (colophon) আলাদা ক্ষেত্রে
পরিচ্ছন্নভাবে সাজানো হয় যাতে প্রতি অধ্যায়ের শ্লোক-নম্বর ১..N ক্রমে থাকে।
"""
from __future__ import annotations

import html as htmllib
import json
import pathlib
import re
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data"
PROBE = pathlib.Path("/tmp/gh_probe")
CW = PROBE / "telugu-purana-rag-main/corpus_ws"
BH_RAW = PROBE / "bhavishya_raw"
VISHNU_DUTT = PROBE / "vishnu_dutt.txt"

BN_DIG = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def bn(n: int) -> str:
    return str(n).translate(BN_DIG)


# ---- নির্ণয়যোগ্য IAST → দেবনাগরী (কেবল speaker_iast ফিল্ড পরিষ্কার করতে) --------
_VOWELS = {
    "ā": ("अ", "आ", "ा"), "a": ("अ", "अ", ""), "ī": ("इ", "ई", "ी"), "i": ("इ", "इ", "ि"),
    "ū": ("उ", "ऊ", "ू"), "u": ("उ", "उ", "ु"), "ṝ": ("ऋ", "ॠ", "ॄ"), "ṛ": ("ऋ", "ऋ", "ृ"),
    "ḹ": ("ऌ", "ॡ", "ॣ"), "ḷ": ("ऌ", "ऌ", "ॢ"), "ai": ("ए", "ऐ", "ै"), "au": ("ओ", "औ", "ौ"),
    "e": ("ए", "ए", "े"), "o": ("ओ", "ओ", "ो"),
}
_CONS = {
    "kh": "ख", "gh": "घ", "ch": "छ", "jh": "झ", "ṭh": "ठ", "ḍh": "ढ",
    "th": "थ", "dh": "ध", "ph": "फ", "bh": "भ", "k": "क", "g": "ग", "ṅ": "ङ",
    "c": "च", "j": "ज", "ñ": "ञ", "ṭ": "ट", "ḍ": "ड", "ṇ": "ण",
    "t": "त", "d": "द", "n": "न", "p": "प", "b": "ब", "m": "म",
    "y": "य", "r": "र", "l": "ल", "v": "व", "w": "व",
    "ś": "श", "ṣ": "ष", "s": "स", "h": "ह", "ḻ": "ळ",
}
_V_KEYS = sorted(_VOWELS.keys(), key=len, reverse=True)
_C_KEYS = sorted(_CONS.keys(), key=len, reverse=True)


def iast_to_deva(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"^[|।॥\s]+|[|।॥\s]+$", "", s)
    if not s:
        return ""
    out = []
    for word in s.split():
        i, n = 0, len(word)
        w = []
        after_c = False
        while i < n:
            ch = word[i]
            if ch in ("ṃ", "ṁ"):
                w.append("ं"); after_c = False; i += 1; continue
            if ch == "ḥ":
                w.append("ः"); after_c = False; i += 1; continue
            if ch == "'":
                w.append("ऽ"); after_c = False; i += 1; continue
            if ch == "-" or ch == "–":
                w.append("-"); after_c = False; i += 1; continue
            # check consonant first
            ck = next((k for k in _C_KEYS if word.startswith(k, i)), None)
            if ck:
                if after_c:
                    w.append("्")
                w.append(_CONS[ck])
                after_c = True
                i += len(ck)
                continue
            vk = next((k for k in _V_KEYS if word.startswith(k, i)), None)
            if vk:
                _, indep, matra = _VOWELS[vk]
                if after_c:
                    w.append(matra)
                else:
                    w.append(indep)
                after_c = False
                i += len(vk)
                continue
            if after_c:
                w.append("्")
                after_c = False
            w.append(ch)
            i += 1
        if after_c:
            w.append("्")
        out.append("".join(w))
    return " ".join(out)


def clean_sk(s: str) -> str:
    s = re.sub(r"\s*<br\s*/?>\s*", "\n", s or "", flags=re.I)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def clean_spk_iast(raw: str | None) -> str:
    if not raw:
        return ""
    raw = re.sub(r"^[|।॥\s]+|[|।॥\s]+$", "", raw).strip()
    if not raw:
        return ""
    return iast_to_deva(raw)


def write_json(fp: pathlib.Path, obj: dict):
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ==============================================================================
# ১) corpus_ws পুরাণসমূহ (ব্রহ্ম, বিষ্ণু, গরুড়, ব্রহ্মাণ্ড)
# ==============================================================================
COLOPHON_RE = re.compile(r"^(?:इति|एति)\s+श्री(?:ब्राह्मे|गारुडे|ब्रह्माण्डे|वैष्णवे|भविष्ये)")


def load_corpus_ws(fn: str) -> dict[tuple[int, int], list[dict]]:
    by_ch: dict[tuple[int, int], list[dict]] = defaultdict(list)
    with (CW / fn).open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            by_ch[(int(r["book_no"]), int(r["adhyaya_no"]))].append(r)
    return dict(sorted(by_ch.items()))


def build_corpus_ws_purana(
    slug: str,
    fn: str,
    parts: list[tuple[int, str, str, int, int, int]],  # (part_id, bn_name, en_name, book_no, ch_from, ch_to)
    chword: str,
    groupword: str = "অধ্যায়",
    extra_idx: dict | None = None,
):
    by_ch = load_corpus_ws(fn)
    out_dir = DATA / slug
    if out_dir.exists():
        for old in out_dir.glob("ch*.json"):
            old.unlink()

    idx_chapters = []
    total_verses = 0
    total_chs = 0

    for pid, pbn, pen, bno, a_from, a_to in parts:
        verses_out = []
        suktas_out = []
        global_n = 0
        # determine if chapter ids inside this part start at a_from (for split single-book Puranas like Brahma / Garuda Purvakhanda)
        use_start = a_from
        for a_no in range(a_from, a_to + 1):
            rows = by_ch.get((bno, a_no), [])
            if not rows:
                continue
            ch_hd = None
            ch_co = None
            cleaned_rows = []
            for r in rows:
                sk = clean_sk(r["sloka_devanagari"])
                spk = clean_spk_iast(r.get("speaker_iast"))
                if not sk or sk == "श्रीगरुडमहापुराणम्":
                    continue
                # (1,72/82/117/143) Gautami Mahatmya section markers in Brahma
                if re.match(r"^गौतमीमाहात्म्ये\s+\S+ध्यायः?$", sk):
                    ch_co = f"{sk}" if not ch_co else f"{ch_co} · {sk}"
                    continue
                # Colophon row accidentally stored as verse
                if COLOPHON_RE.match(sk):
                    ch_co = sk if not ch_co else f"{ch_co}\n{sk}"
                    continue
                # Brahma (1,1) invocation glued to first verse
                m_b1 = re.match(r"^(श्रीगणेशाय नमः\s*।।?\s*तत्रादौ नैमिषारण्य-वर्णनम्)\s+(.+)$", sk, re.S)
                if m_b1:
                    ch_hd = m_b1.group(1)
                    sk = m_b1.group(2).strip()
                # Garuda (2,1) running header glued to invocation + mangalacharana
                if sk.startswith("श्रीगरुडमहापुराणम् "):
                    sk = sk[len("श्रीगरुडमहापुराणम् "):].strip()
                # Brahma (1,13) extra-path note
                v_hd = None
                m_ext = re.match(r"^\*\*\s*(अतिरिक्त पाठः\s*\([^)]+\))\s+(.+)$", sk, re.S)
                if m_ext:
                    v_hd = m_ext.group(1)
                    sk = m_ext.group(2).strip()
                elif sk.startswith("**"):
                    sk = sk.lstrip("* ").strip()

                cleaned_rows.append({"sk": sk, "spk": spk, "hd": v_hd})

            if not cleaned_rows:
                continue

            v_start = global_n + 1
            for local_i, item in enumerate(cleaned_rows, start=1):
                global_n += 1
                vobj = {
                    "n": global_n,
                    "ch": a_no,
                    "vn": local_i,
                    "sk": item["sk"],
                }
                if item["spk"]:
                    vobj["spk"] = item["spk"]
                if item["hd"]:
                    vobj["hd"] = item["hd"]
                elif local_i == 1 and ch_hd:
                    vobj["hd"] = ch_hd
                verses_out.append(vobj)

            su = {
                "id": a_no,
                "from": v_start,
                "to": global_n,
                "verse": len(cleaned_rows),
                "vfrom": 1,
                "vto": len(cleaned_rows),
            }
            if ch_co:
                su["co"] = ch_co
            suktas_out.append(su)

        ch_doc = {
            "id": pid,
            "bn": pbn,
            "en": pen,
            "count": len(verses_out),
            "suktaCount": len(suktas_out),
            "suktas": suktas_out,
            "verses": verses_out,
        }
        write_json(out_dir / f"ch{pid}.json", ch_doc)

        grid = {"count": len(suktas_out)}
        if use_start != 1:
            grid["start"] = use_start
        idx_chapters.append({
            "id": pid,
            "bn": pbn,
            "en": pen,
            "count": len(verses_out),
            "suktaCount": len(suktas_out),
            "grid": grid,
        })
        total_verses += len(verses_out)
        total_chs += len(suktas_out)

    idx_doc = {
        "slug": slug,
        "verseWord": "শ্লোক",
        "groupWord": groupword,
        "chword": chword,
        "rootLang": "sa",
        "rootWord": "সংস্কৃত",
        "total": total_verses,
        "withBn": 0,
        "withSk": total_verses,
        "suktaTotal": total_chs,
        "chapters": idx_chapters,
    }
    if extra_idx:
        idx_doc.update(extra_idx)
    write_json(out_dir / "index.json", idx_doc)
    print(f"✓ {slug:18s}: {len(idx_chapters):2d} parts · {total_chs:3d} chapters · {total_verses:6,d} shlokas")
    return idx_doc


# ==============================================================================
# ২) বিষ্ণু পুরাণ ইংরেজি — M.N. Dutt (১৮৯৬)
# ==============================================================================
ROMAN_VAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def parse_roman(s: str) -> int:
    s = s.strip().upper().rstrip(".")
    tot = 0
    prev = 0
    for ch in reversed(s):
        v = ROMAN_VAL.get(ch, 0)
        tot += -v if v < prev else v
        prev = v
    return tot


def build_vishnu_english(vishnu_idx: dict):
    txt = VISHNU_DUTT.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    # Locate body PART I. after the Table of Contents (2nd occurrence of ^PART I\.\s*$)
    part1_hits = [m.start() for m in re.finditer(r"^PART I\.\s*$", txt, re.M)]
    body = txt[part1_hits[-1]:]
    body = re.split(r"\*\*\*\s*END OF THE PROJECT GUTENBERG", body, maxsplit=1)[0]

    part_chunks = re.split(r"(?=^PART [IVX]+\.\s*$)", body, flags=re.M)
    part_chunks = [p.strip() for p in part_chunks if re.match(r"^PART [IVX]+\.", p.strip())]
    assert len(part_chunks) == 6, f"Expected 6 parts, found {len(part_chunks)}"

    en_dir = DATA / "vishnu-purana/en"
    if en_dir.exists():
        for f in en_dir.glob("ch*.json"):
            f.unlink()

    total_secs = 0
    total_notes = 0
    for p_idx, p_txt in enumerate(part_chunks, start=1):
        p_txt = re.split(r"^THE END OF PART [IVX]+\.\s*$", p_txt, maxsplit=1, flags=re.M)[0].strip()
        lines = p_txt.splitlines()
        p_head = lines[0].strip().rstrip(".")
        p_body = "\n".join(lines[1:]).strip()
        sec_chunks = re.split(r"(?=^SECTION [IVXLCDM]+\.\s*$)", p_body, flags=re.M)
        sec_chunks = [s.strip() for s in sec_chunks if re.match(r"^SECTION [IVXLCDM]+\.", s.strip())]

        sections = {}
        want_n = vishnu_idx["chapters"][p_idx - 1]["suktaCount"]
        assert len(sec_chunks) == want_n, f"Vishnu Part {p_idx}: {len(sec_chunks)} != {want_n}"

        for s_num, s_txt in enumerate(sec_chunks, start=1):
            s_lines = s_txt.splitlines()
            sec_title = s_lines[0].strip()
            # Handle known Part V Section XXXVIII misprinted as SECTION XXVIII. in Dutt 1896
            if p_idx == 5 and s_num == 38 and sec_title == "SECTION XXVIII.":
                sec_title = "SECTION XXXVIII. (printed as XXVIII. in source)"
            rest = "\n".join(s_lines[1:]).strip()
            # Split footnotes vs body paragraphs
            blocks = [re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n{2,}", rest) if b.strip()]
            paras = []
            notes = []
            for b in blocks:
                m_fn = re.match(r"^\[(\d+)\]\s*(.+)$", b)
                if m_fn:
                    notes.append([int(m_fn.group(1)), m_fn.group(2).strip()])
                elif re.match(r"^FOOTNOTES?:?$", b, re.I):
                    continue
                else:
                    paras.append(b)
            sections[str(s_num)] = {"title": sec_title, "paras": paras, "notes": notes}
            total_secs += 1
            total_notes += len(notes)

        write_json(en_dir / f"ch{p_idx}.json", {"id": p_idx, "bn": p_head, "sections": sections})

    print(f"✓ vishnu-purana EN : 6 parts · {total_secs} sections · {total_notes} footnotes")


# ==============================================================================
# ৩) ভবিষ্য পুরাণ (৫৮৫ অধ্যায়, ৯ খণ্ড / ১৩ অংশ)
# ==============================================================================
SPEAKER_LINE_RE = re.compile(
    r"^[।॥\s]*([^\n।॥]{2,55}?(?:उवाच|ऊचुः|उवाच\s*ह))[।॥\s]*$"
)
INLINE_SPK_RE = re.compile(
    r"^[।॥\s]*((?:श्रीमहादेव|श्रीभगवान|श्रीकृष्ण|श्रीसूत|सुमन्तुर्|शतानीक|बृहस्पतिर्|शङ्कर|सप्ताश्वतिलक|सप्ताश्व|अनूरु|व्यास|सूत|ब्रह्मो|ब्रह्मा|ऋषय|मुनय|सनत्कुमार|नारद|मार्कण्डेय|युधिष्ठिर|अर्जुन|भीष्म|कौथुमि|दक्ष|रुद्र|शिव|इन्द्र|यम|वरुण|सूर्य|मनु|वैशम्पायन|पिता|पितो|लोमश|विदुर|धृतराष्ट्र|सञ्जय|देव|देवी|पार्वती)[^\n।॥]{0,30}?(?:उवाच|ऊचुः|उवाच\s*ह))[।॥\s]+(.+)$",
    re.S,
)
INVOCATION_RE = re.compile(r"^(?:[।॥\s]*(?:श्रीगणेशाय नमः|श्रीसरस्वत्यै नमः|ॐ नमो [^\n]+|श्रीरामचंद्राय)[।॥\s]*)$")
VERSE_NUM_LINE_RE = re.compile(r"(?:[।॥|]\s*[।॥|]|॥)\s*(?:[\d.]+\.)?[०-९0-9]+\s*(?:[।॥|]\s*)*$")


def clean_bhavishya_raw(txt: str) -> str:
    txt = htmllib.unescape(txt)
    txt = re.sub(r"</?poem>", "", txt, flags=re.I)
    txt = re.sub(r"</?i>", "", txt, flags=re.I)
    txt = re.sub(r'<sup class="reference"[^>]*>.*?</sup>', "", txt, flags=re.S | re.I)
    # Remove comparison links cleanly
    txt = re.sub(r"(?:तुलनीय|तु\.)\s*[-–]\s*<a [^>]*>.*?</a>", "", txt, flags=re.S | re.I)
    txt = re.sub(r"<a [^>]*>\s*रथोपरि टिप्पणी\s*</a>", "", txt, flags=re.S | re.I)
    # Unwrap clean inline word anchors
    txt = re.sub(r"<a [^>]*>(.*?)</a>", r"\1", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = re.sub(r"\r\n?", "\n", txt)
    return txt.strip()


def split_bhavishya_chapter(raw_txt: str) -> tuple[str, list[dict], str]:
    """একটি ভবিষ্য পুরাণ অধ্যায়কে (topic_hd, verses, colophon)-এ ভাগ করা।"""
    txt = clean_bhavishya_raw(raw_txt)
    lines = [re.sub(r"\s+", " ", l).strip() for l in txt.splitlines() if l.strip()]
    if not lines:
        return ("", [], "")

    topic_hd = ""
    colophon = ""
    # Extract trailing colophon lines (`इति श्रीभविष्ये ...` + optional `छ`)
    while lines and re.match(r"^[।॥\s]*(?:इति\s+(?:श्री)?भविष्य|इति\s+श्री|छ\s*[।॥]*$|तुलनीय\b)", lines[-1]):
        last = lines.pop()
        if re.match(r"^[।॥\s]*छ\s*[।॥]*$", last) or last.startswith("तुलनीय"):
            continue
        colophon = f"{last}\n{colophon}".strip() if colophon else last

    # Extract leading topic title (single short non-danda line) or invocations before verse 1
    invs = []
    while lines and (
        INVOCATION_RE.match(lines[0])
        or (
            len(invs) == 0
            and not re.search(r"[।॥]", lines[0])
            and not SPEAKER_LINE_RE.match(lines[0])
            and len(lines[0]) < 80
            and len(lines) > 1
        )
    ):
        invs.append(lines.pop(0).strip("।॥ "))
    if invs:
        topic_hd = " · ".join(x for x in invs if x)

    verses = []
    buf: list[str] = []
    cur_spk = ""

    def flush():
        nonlocal cur_spk
        if not buf:
            return
        body = "\n".join(buf).strip()
        buf.clear()
        if not body:
            return
        # Check if first line inside buf starts inline with speaker
        m_sp = INLINE_SPK_RE.match(body)
        if m_sp:
            spk_txt = re.sub(r"[।॥\s]+$", "", m_sp.group(1)).strip()
            body = m_sp.group(2).strip()
            if not cur_spk:
                cur_spk = spk_txt
        v = {"sk": body}
        if cur_spk:
            v["spk"] = cur_spk
            cur_spk = ""
        verses.append(v)

    for ln in lines:
        # Clean stray footnote marker artifacts
        if re.match(r"^[।॥\s]*इति\s+श्रीभविष्ये", ln):
            colophon = f"{colophon}\n{ln}".strip() if colophon else ln
            continue
        m_spk = SPEAKER_LINE_RE.match(ln)
        if m_spk and not VERSE_NUM_LINE_RE.search(ln):
            flush()
            cur_spk = re.sub(r"\s+", " ", m_spk.group(1)).strip()
            continue

        # Check if inline speaker prefix starts a line while previous lines are un-flushed
        if buf and INLINE_SPK_RE.match(ln):
            flush()

        buf.append(ln)
        if VERSE_NUM_LINE_RE.search(ln):
            flush()
        elif len(buf) >= 2 and re.search(r"(?:[।॥]\s*[।॥]|॥)\s*$", ln) and len(buf[-2]) > 15:
            # Handles chapters / passages missing explicit verse digits where every couplet ends in ।।
            # Check if previous line already ended in ।। (then every 2 lines = 1 shloka) or single ।
            if not re.search(r"(?:[।॥]\s*[।॥]|॥)\s*$", buf[-2]) or len(buf) >= 2:
                # Only flush on double-danda if previous line didn't look like a 1-line intro before numbered verses,
                # OR if buffer already reached 2+ full lines of verse
                if len(buf) >= 2:
                    flush()

    flush()
    return (topic_hd, verses, colophon)


BH_PARTS = [
    (1, "ব্রাহ্মপর্ব (অধ্যায় ১–৭৫)", "Brahma Parva (1–75)", "1. Brahma Parva", 1, 75),
    (2, "ব্রাহ্মপর্ব (অধ্যায় ৭৬–১৫০)", "Brahma Parva (76–150)", "1. Brahma Parva", 76, 150),
    (3, "ব্রাহ্মপর্ব (অধ্যায় ১৫১–২১৬)", "Brahma Parva (151–216)", "1. Brahma Parva", 151, 216),
    (4, "মধ্যমপর্ব — প্রথম খণ্ড", "Madhyama Parva I", "2.1. Madhyama Parva", 1, 21),
    (5, "মধ্যমপর্ব — দ্বিতীয় খণ্ড", "Madhyama Parva II", "2.2. Madhyama Parva", 1, 20),
    (6, "মধ্যমপর্ব — তৃতীয় খণ্ড", "Madhyama Parva III", "2.3. Madhyama Parva", 1, 20),
    (7, "প্রতিসর্গপর্ব — প্রথম খণ্ড", "Pratisarga Parva I", "3.1. Pratisarga Parva", 1, 7),
    (8, "প্রতিসর্গপর্ব — দ্বিতীয় খণ্ড", "Pratisarga Parva II", "3.2. Pratisarga Parva", 1, 35),
    (9, "প্রতিসর্গপর্ব — তৃতীয় খণ্ড", "Pratisarga Parva III", "3.3. Pratisarga Parva", 1, 32),
    (10, "প্রতিসর্গপর্ব — চতুর্থ খণ্ড", "Pratisarga Parva IV", "3.4. Pratisarga Parva", 1, 26),
    (11, "উত্তরপর্ব (অধ্যায় ১–৭০)", "Uttara Parva (1–70)", "4. Uttara Parva", 1, 70),
    (12, "উত্তরপর্ব (অধ্যায় ৭১–১৪০)", "Uttara Parva (71–140)", "4. Uttara Parva", 71, 140),
    (13, "উত্তরপর্ব (অধ্যায় ১৪১–২০৮)", "Uttara Parva (141–208)", "4. Uttara Parva", 141, 208),
]


def build_bhavishya():
    slug = "bhavishya-purana"
    out_dir = DATA / slug
    if out_dir.exists():
        for old in out_dir.glob("ch*.json"):
            old.unlink()

    idx_chapters = []
    total_verses = 0
    total_chs = 0
    single_giant = []

    for pid, pbn, pen, subdir, a_from, a_to in BH_PARTS:
        verses_out = []
        suktas_out = []
        global_n = 0

        for a_no in range(a_from, a_to + 1):
            fp = BH_RAW / subdir / f"{a_no}.json"
            arr = json.loads(fp.read_text(encoding="utf-8"))
            raw_txt = "\n".join(x.get("text", "") for x in arr)
            topic_hd, vs, colophon = split_bhavishya_chapter(raw_txt)
            if len(vs) <= 1 and len(raw_txt) > 500:
                single_giant.append((subdir, a_no, len(vs), len(raw_txt)))

            v_start = global_n + 1
            for local_i, item in enumerate(vs, start=1):
                global_n += 1
                vobj = {
                    "n": global_n,
                    "ch": a_no,
                    "vn": local_i,
                    "sk": item["sk"],
                }
                if item.get("spk"):
                    vobj["spk"] = item["spk"]
                verses_out.append(vobj)

            su = {
                "id": a_no,
                "from": v_start,
                "to": global_n,
                "verse": len(vs),
                "vfrom": 1,
                "vto": len(vs),
            }
            if topic_hd:
                su["title"] = topic_hd
            if colophon:
                su["co"] = colophon
            suktas_out.append(su)

        write_json(out_dir / f"ch{pid}.json", {
            "id": pid,
            "bn": pbn,
            "en": pen,
            "count": len(verses_out),
            "suktaCount": len(suktas_out),
            "suktas": suktas_out,
            "verses": verses_out,
        })
        grid = {"count": len(suktas_out)}
        if a_from != 1:
            grid["start"] = a_from
        idx_chapters.append({
            "id": pid,
            "bn": pbn,
            "en": pen,
            "count": len(verses_out),
            "suktaCount": len(suktas_out),
            "grid": grid,
        })
        total_verses += len(verses_out)
        total_chs += len(suktas_out)

    idx_doc = {
        "slug": slug,
        "verseWord": "শ্লোক",
        "groupWord": "অধ্যায়",
        "chword": "খণ্ড",
        "rootLang": "sa",
        "rootWord": "সংস্কৃত",
        "total": total_verses,
        "withBn": 0,
        "withSk": total_verses,
        "suktaTotal": total_chs,
        "chapters": idx_chapters,
    }
    write_json(out_dir / "index.json", idx_doc)
    print(f"✓ {slug:18s}: {len(idx_chapters):2d} parts · {total_chs:3d} chapters · {total_verses:6,d} shlokas | giants={single_giant[:3]}")
    return idx_doc


def main() -> int:
    build_corpus_ws_purana(
        "brahma-purana",
        "brahma.jsonl",
        [
            (1, "প্রথম অংশ (অধ্যায় ১–৫০)", "Chapters 1–50", 1, 1, 50),
            (2, "দ্বিতীয় অংশ (অধ্যায় ৫১–১০০)", "Chapters 51–100", 1, 51, 100),
            (3, "তৃতীয় অংশ (অধ্যায় ১০১–১৫০)", "Chapters 101–150", 1, 101, 150),
            (4, "চতুর্থ অংশ (অধ্যায় ১৫১–২০০)", "Chapters 151–200", 1, 151, 200),
            (5, "পঞ্চম অংশ (অধ্যায় ২০১–২৪৬)", "Chapters 201–246", 1, 201, 246),
        ],
        chword="অংশ",
    )

    v_idx = build_corpus_ws_purana(
        "vishnu-purana",
        "vishnu.jsonl",
        [
            (1, "প্রথম অংশ", "Book I", 1, 1, 22),
            (2, "দ্বিতীয় অংশ", "Book II", 2, 1, 16),
            (3, "তৃতীয় অংশ", "Book III", 3, 1, 18),
            (4, "চতুর্থ অংশ", "Book IV", 4, 1, 24),
            (5, "পঞ্চম অংশ", "Book V", 5, 1, 38),
            (6, "ষষ্ঠ অংশ", "Book VI", 6, 1, 8),
        ],
        chword="অংশ",
        extra_idx={"hasEnProse": True, "enSections": 126, "enNotes": 259},
    )
    build_vishnu_english(v_idx)

    build_bhavishya()

    build_corpus_ws_purana(
        "garuda-purana",
        "garuda.jsonl",
        [
            (1, "পূর্বখণ্ড (আচারকাণ্ড · ১–১২০)", "Purvakhanda 1–120", 1, 1, 120),
            (2, "পূর্বখণ্ড (আচারকাণ্ড · ১২১–২৪০)", "Purvakhanda 121–240", 1, 121, 240),
            (3, "প্রেতখণ্ড (ধর্মকাণ্ড)", "Pretakhanda", 2, 1, 49),
            (4, "ব্রহ্মখণ্ড", "Brahmakhanda", 3, 1, 29),
        ],
        chword="খণ্ড",
    )

    build_corpus_ws_purana(
        "brahmanda-purana",
        "brahmanda.jsonl",
        [
            (1, "পূর্বভাগ (প্রক্রিয়া ও অনুষঙ্গপাদ)", "Purvabhaga", 1, 1, 38),
            (2, "মধ্যমভাগ (উপোদ্ঘাতপাদ)", "Madhyamabhaga", 2, 1, 74),
            (3, "উত্তরভাগ (উপসংহার ও ললিতোপাখ্যান)", "Uttarabhaaga", 3, 1, 44),
        ],
        chword="ভাগ",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
