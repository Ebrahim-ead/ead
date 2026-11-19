#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""মহাভারতের সম্পূর্ণ ১৮ পর্বের ডেটা তৈরি (৩টি স্বতন্ত্র সংস্করণ):
  · bn — বাংলা (কালীপ্রসন্ন সিংহ অনূদিত; kali_all/parba_{1..18}.db)
  · en — ইংরেজি (Kisari Mohan Ganguli; Internet Sacred Text Archive m01..m18)
  · sa — সংস্কৃত মূল (কুম্ভকোণম্ / corpus_ws + অনুপস্থিত অধ্যায় ও শ্লোক vishvAsa/kumbhakoNam থেকে পূরণ)

নীতি:
  · প্রতিটি সংস্করণের নিজস্ব অধ্যায়-বিন্যাস অটুট রাখা হয় (পর্ব-ভিত্তিক পার্থক্য থাকায়
    জোর করে ভুল অধ্যায় মেলানো হয় না)।
  · কোনো অধ্যায় বা শ্লোক উৎসে না থাকলে অনুমান করে বানানো হয় না — স্পষ্টভাবে নথিভুক্ত থাকে।
  · প্রতিটি JSON খণ্ড ৫০ অধ্যায়ের মধ্যে রাখা হয় যাতে মোবাইলেও দ্রুত ও অফলাইন ক্যাশবান্ধব থাকে।
"""
from __future__ import annotations

import html as htmllib
import json
import pathlib
import re
import shutil
import sqlite3
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/grantho/data/mahabharata"
PROBE = pathlib.Path("/tmp/gh_probe")
KALI_DIR = PROBE / "kali_all"
SACRED_DIR = PROBE / "sacred_mbh"
CW = PROBE / "telugu-purana-rag-main/corpus_ws"
PATCH_DIR = PROBE / "mbh_sa_patch"

CHUNK_SIZE = 50
BN_DIG = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def bn_n(n: int) -> str:
    return str(n).translate(BN_DIG)


# ---- নির্ণয়যোগ্য IAST → দেবনাগরী (speaker_iast এর জন্য) --------------------
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


def iast_to_deva(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"^[|।॥\s]+|[|।॥\s]+$", "", s.strip().lower())
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
            if ch in ("-", "–"):
                w.append("-"); after_c = False; i += 1; continue
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
                w.append(matra if after_c else indep)
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


PARVAS = [
    (1, "আদিপর্ব", "Adi Parva", "आदिपर्व"),
    (2, "সভাপর্ব", "Sabha Parva", "सभापर्व"),
    (3, "বনপর্ব", "Vana Parva", "वनपर्व"),
    (4, "বিরাটপর্ব", "Virata Parva", "विराटपर्व"),
    (5, "উদ্যোগপর্ব", "Udyoga Parva", "उद्योगपर्व"),
    (6, "ভীষ্মপর্ব", "Bhishma Parva", "भीष्मपर्व"),
    (7, "দ্রোণপর্ব", "Drona Parva", "द्रोणपर्व"),
    (8, "কর্ণপর্ব", "Karna Parva", "कर्णपर्व"),
    (9, "শল্যপর্ব", "Shalya Parva", "शल्यपर्व"),
    (10, "সৌপ্তিকপর্ব", "Sauptika Parva", "सौप्तिकपर्व"),
    (11, "স্ত্রীপর্ব", "Stri Parva", "स्त्रीपर्व"),
    (12, "শান্তিপর্ব", "Shanti Parva", "शान्तिपर्व"),
    (13, "অনুশাসনপর্ব", "Anushasana Parva", "अनुशासनपर्व"),
    (14, "অশ্বমেধিকপর্ব", "Ashvamedhika Parva", "आश्वमेधिकपर्व"),
    (15, "আশ্রমবাসিকপর্ব", "Ashramavasika Parva", "आश्रमवासिकपर्व"),
    (16, "মৌসলপর্ব", "Mausala Parva", "मौसलपर्व"),
    (17, "মহাপ্রস্থানিকপর্ব", "Mahaprasthanika Parva", "महाप्रस्थानिकपर्व"),
    (18, "স্বর্গারোহণপর্ব", "Svargarohanika Parva", "स्वर्गारोहणपर्व"),
]


def write_json(fp: pathlib.Path, obj):
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ==============================================================================
# ১) বাংলা সংস্করণ — কালীপ্রসন্ন সিংহ
# ==============================================================================
def build_bn_parva(p: int) -> tuple[list[dict], dict]:
    db = sqlite3.connect(KALI_DIR / f"parba_{p}.db")
    ads = db.execute("SELECT id, chapter_no, title FROM adhyayas ORDER BY chapter_no").fetchall()
    upas = db.execute(
        "SELECT adhyay_id, seq, bishoy, content FROM upakhyanas ORDER BY adhyay_id, seq"
    ).fetchall()
    db.close()

    by_ad = defaultdict(list)
    for aid, seq, bishoy, content in upas:
        txt = (content or "").replace("\r\n", "\n").strip()
        if not txt and not (bishoy or "").strip():
            continue
        paras = [re.sub(r"[ \t]+", " ", x).strip() for x in re.split(r"\n{2,}", txt) if x.strip()]
        if not paras:
            continue
        entry = {"p": paras}
        b_clean = re.sub(r"\s+", " ", bishoy or "").strip()
        if b_clean:
            entry["b"] = b_clean
        by_ad[aid].append(entry)

    chs = []
    upa_total = 0
    for aid, ch_no, title in ads:
        u_list = by_ad.get(aid, [])
        if not u_list:
            continue
        t_clean = re.sub(r"\s+", " ", title or "").strip()
        # Strip redundant leading numeric prefix `০০১.` when duplicating chapter number
        t_clean = re.sub(r"^[০-৯0-9]+\s*\.\s*", "", t_clean).strip()
        chs.append({"c": int(ch_no), "t": t_clean, "u": u_list})
        upa_total += len(u_list)

    # Known missing / truncated chapters in digitized Kaliprasanna source
    present = {x["c"] for x in chs}
    max_c = max(present) if present else 0
    missing = [n for n in range(1, max_c + 1) if n not in present]
    note = ""
    if p == 9 and max_c == 45:
        note = "ডিজিটাল বাংলা উৎসে (কালীপ্রসন্ন সিংহ) শল্যপর্বের পাঠ অধ্যায় ৪৫ পর্যন্তই পাওয়া যায় — অধ্যায় ৪৬–৬৫ অনুপস্থিত; সম্পূর্ণ পাঠ ইংরেজি (৬৫) ও সংস্কৃত (৬৬) সংস্করণে পড়া যাবে।"
    elif missing:
        note = f"ডিজিটাল বাংলা উৎসে (কালীপ্রসন্ন সিংহ) অধ্যায় {', '.join(bn_n(x) for x in missing)} অনুপস্থিত — অনুমান করে কিছু বসানো হয়নি।"

    chunks = []
    for k in range(0, len(chs), CHUNK_SIZE):
        sl = chs[k : k + CHUNK_SIZE]
        idx = k // CHUNK_SIZE + 1
        rel = f"bn/p{p}_{idx}.json"
        write_json(OUT / rel, {"p": p, "ed": "bn", "chs": sl})
        chunks.append({
            "f": rel,
            "s": sl[0]["c"],
            "e": sl[-1]["c"],
            "ids": [x["c"] for x in sl],
        })

    meta = {
        "chCount": len(chs),
        "maxCh": max_c,
        "upaCount": upa_total,
        "missing": missing,
        "chunks": chunks,
    }
    if note:
        meta["note"] = note
    return chs, meta


# ==============================================================================
# ২) ইংরেজি সংস্করণ — Kisari Mohan Ganguli (sacred_mbh)
# ==============================================================================
ROMAN_RE = re.compile(r"^[IVXLCDM]+$", re.I)


def clean_html_inline(frag: str) -> str:
    # Remove footnote anchor wrapper labels like `[1]`? Wait - preserve `[1]`? Actually sacred-texts uses <A NAME="fr_87"></A><A HREF="...#fn_87"><FONT SIZE="1">116:1</FONT></A>
    frag = re.sub(r'<A[^>]*NAME="fr_[^"]*"[^>]*>.*?</A>', "", frag, flags=re.I | re.S)
    frag = re.sub(r'<A[^>]*HREF="[^"]*#fn_(\d+)"[^>]*>(.*?)</A>', r" [\1]", frag, flags=re.I | re.S)
    frag = re.sub(r"<br\s*/?>", " ", frag, flags=re.I)
    frag = re.sub(r"<[^>]+>", "", frag)
    frag = htmllib.unescape(frag)
    return re.sub(r"\s+", " ", frag).strip()


def parse_sacred_htm(fp: pathlib.Path, sec_num: int) -> dict:
    raw = fp.read_text(encoding="utf-8", errors="replace")
    # Body starts after the top navigation <HR>
    top_center = re.search(r"</CENTER>\s*<HR\b[^>]*>", raw, re.I)
    body = raw[top_center.end():] if top_center else raw

    # Extract footnotes section if present
    notes = []
    fn_split = re.split(r"<HR\b[^>]*>\s*<H[1-4][^>]*>\s*Footnotes\s*</H[1-4]>", body, maxsplit=1, flags=re.I)
    if len(fn_split) == 2:
        body, fn_raw = fn_split
        # Stop footnotes before Next/nav footer
        fn_raw = re.split(r"(?:<p>\s*)?<HR\b", fn_raw, maxsplit=1, flags=re.I)[0]
        for m in re.finditer(r"<P[^>]*>(.*?)(?=<P\b|$)", fn_raw, re.I | re.S):
            f_html = m.group(1)
            f_txt = htmllib.unescape(re.sub(r"<[^>]+>", "", f_html))
            f_txt = re.sub(r"\s+", " ", f_txt).strip()
            if f_txt:
                notes.append(f_txt)

    # Strip bottom nav (`<p><HR>` or `<HR><CENTER><A ...Next:` or `<nav role="navigation">`)
    body = re.split(
        r"(?:<p[^>]*>\s*)?<HR\b[^>]*>(?:\s*<CENTER>|\s*<nav\b|\s*<A\b)",
        body,
        maxsplit=1,
        flags=re.I,
    )[0]

    # Extract title / section label
    label = ""
    sub = ""
    ed_note = ""
    is_preface = (fp.name == "m01001.htm")

    m_h = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.I | re.S)
    if m_h:
        h_clean = htmllib.unescape(re.sub(r"<br\s*/?>", " | ", m_h.group(1), flags=re.I))
        h_clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h_clean)).strip()
        if "|" in h_clean:
            label, sub = [x.strip() for x in h_clean.split("|", 1)]
        else:
            label = h_clean
        body = body[: m_h.start()] + body[m_h.end() :]
    else:
        # m08-11, m16-18 use <p align="center"><b>1</b></p>
        m_num_p = re.search(r"<p[^>]*align=[\"']?center[\"']?[^>]*>\s*<b>\s*([^<]+?)\s*</b>\s*</p>", body, re.I)
        if m_num_p:
            label = f"Section {m_num_p.group(1).strip()}"
            body = body[: m_num_p.start()] + body[m_num_p.end() :]
        else:
            label = "Translator's Preface" if is_preface else f"Section {sec_num}"

    # Extract paragraphs cleanly
    paras = []
    # Split on <p ...> tokens (works even with unclosed <P>)
    chunks = re.split(r"<p\b[^>]*>", body, flags=re.I)
    for ch_html in chunks:
        # strip trailing </p>
        ch_html = re.sub(r"</p>\s*$", "", ch_html.strip(), flags=re.I)
        if not ch_html:
            continue
        # Drop pure page-number paragraphs (`<A NAME="page_...">p. 51</A>`)
        if re.match(r'^<A\s+NAME="page_[^"]*"[^>]*>.*?</A>\s*$', ch_html, re.I | re.S):
            continue
        # Drop Sacred Texts header bleed if any
        if "Sacred Texts" in ch_html and "Hinduism" in ch_html:
            continue
        # Detect centered subheading like `(Chaitraratha Parva continued)` or green editorial notes
        is_green = bool(re.search(r'COLOR="?GREEN"?', ch_html, re.I))
        txt = clean_html_inline(ch_html)
        if not txt or re.fullmatch(r"p\.\s*\d+", txt, re.I):
            continue
        if is_green and re.search(r"Sections?\s+[IVXLCDM]+.*not found|John Bruno Hare|--JBH|no section [IVXLCDM]+", txt, re.I):
            ed_note = f"{ed_note} {txt}".strip() if ed_note else txt
            continue
        if is_green and txt.startswith("(This where is the Bhagavad Gita") or (len(txt) < 120 and txt.startswith("(") and txt.endswith(")") and not paras and not sub):
            sub = f"{sub} {txt}".strip() if sub else txt
            continue
        if txt.startswith("[paragraph continues]"):
            cont = txt[len("[paragraph continues]"):].strip()
            if paras and cont:
                paras[-1] = paras[-1].rstrip() + " " + cont
            elif cont:
                paras.append(cont)
            continue
        paras.append(txt)

    if not paras:
        paras = [ed_note or label]

    res = {"c": sec_num, "t": label, "p": paras}
    if sub:
        res["s"] = sub
    if ed_note:
        res["n"] = ed_note
    if notes:
        res["fn"] = notes
    return res


def build_en_parva(p: int) -> tuple[list[dict], dict]:
    p_dir = SACRED_DIR / f"m{p:02d}"
    files = sorted(
        f for f in p_dir.glob("m*.htm")
        if not f.name.endswith("000.htm")
        and "index" not in f.name
        and re.match(r"^m\d\d[a-c]?\d{3}", f.name)
    )
    chs = []
    for idx, fp in enumerate(files):
        sec_num = idx if (p == 1 and fp.name == "m01001.htm") else (idx if p == 1 else idx + 1)
        chs.append(parse_sacred_htm(fp, sec_num))

    chunks = []
    for k in range(0, len(chs), CHUNK_SIZE):
        sl = chs[k : k + CHUNK_SIZE]
        cidx = k // CHUNK_SIZE + 1
        rel = f"en/p{p}_{cidx}.json"
        write_json(OUT / rel, {"p": p, "ed": "en", "chs": sl})
        chunks.append({
            "f": rel,
            "s": sl[0]["c"],
            "e": sl[-1]["c"],
            "ids": [x["c"] for x in sl],
        })

    return chs, {
        "chCount": len(chs),
        "hasPreface": (p == 1),
        "chunks": chunks,
    }


# ==============================================================================
# ৩) সংস্কৃত সংস্করণ — corpus_ws + vishvAsa/kumbhakoNam পূর্ণ পূরণ
# ==============================================================================
def parse_kumbh_md(fp: pathlib.Path) -> tuple[str, list[dict]]:
    lines = fp.read_text(encoding="utf-8").splitlines()
    title = ""
    verses = []  # {"vn": int, "sk": str, "spk": str}
    cur_num = None
    cur_lines: list[str] = []
    cur_spk = ""
    pending_spk = ""

    body_lines = []
    in_meta = False
    for ln in lines:
        s = ln.strip()
        if s == "+++":
            in_meta = not in_meta
            continue
        if in_meta or s.startswith("title ="):
            continue
        body_lines.append(ln)

    for ln in body_lines:
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^अध्यायः\s+\d+$", s):
            continue
        if re.match(r"^इति\s+श्रीमन्महाभारते", s):
            continue
        if re.match(r"^\d+-\d+-\d+", s):
            continue
        if not title and not verses and not cur_lines and "\t" not in ln:
            if "॥ 1 ॥" in s or re.match(r"^\(.*पर्व.*\)$", s):
                title = f"{title} · {s}".strip(" ·") if title else s
                continue

        m_a1 = re.match(r"^(.*?)\t+KK\d+-\d+-\d+-(\d+)([A-Za-z]*)\s*$", ln)
        m_a2 = re.match(r"^(.*?)\t+(\d+)([A-Za-z]*)\s*$", ln)
        m_b = re.match(r"^(\d+)([a-zA-Z]*)\s*\t+(.*)$", ln)
        if m_a1:
            txt_part = m_a1.group(1).strip().replace("\\'", "'")
            vnum = int(m_a1.group(2))
            suf = m_a1.group(3)
        elif m_a2:
            txt_part = m_a2.group(1).strip().replace("\\'", "'")
            vnum = int(m_a2.group(2))
            suf = m_a2.group(3)
        elif m_b:
            vnum = int(m_b.group(1))
            suf = m_b.group(2)
            txt_part = m_b.group(3).strip().replace("\\'", "'")
        else:
            continue

        if not suf and re.match(r"^['\"* ]*[^\t।॥]{2,45}(?:उवाच|ऊचुः)\s*[।॥\s]*$", txt_part):
            if cur_num is not None and vnum != cur_num:
                verses.append({"vno": cur_num, "sk": "\n".join(cur_lines), "spk": cur_spk})
                cur_num = None; cur_lines = []; cur_spk = ""
            pending_spk = txt_part.strip(" '\"*।॥")
            continue

        if vnum != cur_num:
            if cur_num is not None:
                verses.append({"vno": cur_num, "sk": "\n".join(cur_lines), "spk": cur_spk})
            cur_num = vnum
            cur_lines = [txt_part] if txt_part else []
            cur_spk = pending_spk
            pending_spk = ""
        else:
            if txt_part:
                cur_lines.append(txt_part)

    if cur_num is not None:
        verses.append({"vno": cur_num, "sk": "\n".join(cur_lines), "spk": cur_spk})

    return title, verses


def load_mahabharata_sa() -> dict[tuple[int, int], tuple[str, list[dict]]]:
    by_ch: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for fn in ["mahabharata.jsonl", "mahabharata.part2.jsonl"]:
        with (CW / fn).open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                p = int(r["book_no"])
                ch = int(r["adhyaya_no"])
                vno = int(r["verse_no"])
                sk = re.sub(r"\s*<br\s*/?>\s*", "\n", r["sloka_devanagari"], flags=re.I).strip()
                spk = iast_to_deva(r.get("speaker_iast"))

                # Drop the 2 leaked Neelakantha commentary lines verified against kumbhakoNam
                if (p, ch, vno) in ((2, 5, 5), (2, 7, 2)) and re.match(r"^\d+-\d+-", sk):
                    continue

                # Clean the 11 unstripped `\d+-\d+-\d+[a-z]?` prefixes on valid shlokas
                m_pref = re.match(r"^(?:\d+-\d+-\d+[a-z]?\s+)+(.+)$", sk, re.S)
                if m_pref:
                    sk = m_pref.group(1).strip()
                    m_sp = re.match(r"^([^\n।॥]{2,35}(?:उवाच|ऊचुः))\s*x\s*(.+)$", sk, re.S)
                    if m_sp:
                        if not spk:
                            spk = m_sp.group(1).strip()
                        sk = m_sp.group(2).strip()

                by_ch[(p, ch)].append({"vno": vno, "sk": sk, "spk": spk})

    # Apply kumbhakoNam patches:
    # 1) Completely replace the 6 missing chapters + truncated prose chapter (3, 202)
    full_replace = {(1, 1), (3, 202), (8, 99), (12, 188), (12, 190), (12, 227), (12, 290)}
    titles: dict[tuple[int, int], str] = {}
    patched_vs = 0

    for fp in sorted(PATCH_DIR.glob("*.md")):
        p_str, ch_str = fp.stem.split("_")
        key = (int(p_str), int(ch_str))
        title, k_verses = parse_kumbh_md(fp)
        if title:
            titles[key] = title
        if key in full_replace:
            by_ch[key] = k_verses
            patched_vs += len(k_verses)
        elif key in by_ch:
            # Merge any skipped verse numbers from kumbhakoNam that corpus_ws dropped
            existing_vnos = {x["vno"] for x in by_ch[key]}
            added = 0
            for kv in k_verses:
                if kv["vno"] not in existing_vnos:
                    by_ch[key].append(kv)
                    existing_vnos.add(kv["vno"])
                    added += 1
            if added:
                by_ch[key].sort(key=lambda x: x["vno"])
                patched_vs += added

    print(f"✓ mahabharata SA patched: {len(full_replace)} full chs + {patched_vs} total added/replaced shlokas")
    result = {}
    for key in sorted(by_ch):
        rows = by_ch[key]
        result[key] = (titles.get(key, ""), rows)
    return result


def build_sa_parva(p: int, sa_all: dict) -> tuple[list[dict], dict]:
    chs = []
    shloka_total = 0
    for (bno, ch_no), (title, rows) in sorted(sa_all.items()):
        if bno != p:
            continue
        verses_out = []
        for idx, item in enumerate(rows, start=1):
            v = {"vn": idx, "sk": re.sub(r"[ \t]+", " ", item["sk"]).strip()}
            if item.get("spk"):
                v["spk"] = item["spk"]
            verses_out.append(v)
        cobj = {"c": ch_no, "v": verses_out}
        if title:
            cobj["t"] = title
        chs.append(cobj)
        shloka_total += len(verses_out)

    chunks = []
    for k in range(0, len(chs), CHUNK_SIZE):
        sl = chs[k : k + CHUNK_SIZE]
        cidx = k // CHUNK_SIZE + 1
        rel = f"sa/p{p}_{cidx}.json"
        write_json(OUT / rel, {"p": p, "ed": "sa", "chs": sl})
        chunks.append({
            "f": rel,
            "s": sl[0]["c"],
            "e": sl[-1]["c"],
            "ids": [x["c"] for x in sl],
        })

    return chs, {
        "chCount": len(chs),
        "shlokaCount": shloka_total,
        "chunks": chunks,
    }


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    sa_all = load_mahabharata_sa()

    parvas_meta = []
    audit_chapters = []
    tot_bn_ch = tot_bn_upa = tot_en_ch = tot_sa_ch = tot_sa_sl = 0

    for pid, bn_name, en_name, sa_name in PARVAS:
        bn_chs, bn_meta = build_bn_parva(pid)
        en_chs, en_meta = build_en_parva(pid)
        sa_chs, sa_meta = build_sa_parva(pid, sa_all)

        tot_bn_ch += bn_meta["chCount"]
        tot_bn_upa += bn_meta["upaCount"]
        tot_en_ch += en_meta["chCount"]
        tot_sa_ch += sa_meta["chCount"]
        tot_sa_sl += sa_meta["shlokaCount"]

        # Compact per-chapter title tables for quick jump / grid tooltip
        bn_titles = {str(x["c"]): x["t"] for x in bn_chs if x.get("t")}
        en_titles = {str(x["c"]): x["t"] for x in en_chs if x.get("t")}

        parvas_meta.append({
            "id": pid,
            "bn": bn_name,
            "en": en_name,
            "sa": sa_name,
            "editions": {
                "bn": {**bn_meta, "titles": bn_titles},
                "en": {**en_meta, "titles": en_titles},
                "sa": sa_meta,
            },
        })

        # audit_site.mjs compatible chunk manifest (`chapters[i].chapters[].file`)
        ch_files = []
        for ed_m in (bn_meta, en_meta, sa_meta):
            for ck in ed_m["chunks"]:
                ch_files.append({"n": ck["s"], "file": ck["f"]})
        audit_chapters.append({
            "id": pid,
            "bn": bn_name,
            "en": en_name,
            "count": bn_meta["chCount"],
            "chapters": ch_files,
        })
        print(
            f"  P{pid:02d} {bn_name:18s}: bn={bn_meta['chCount']:3d} ch ({bn_meta['upaCount']:3d} upa) | "
            f"en={en_meta['chCount']:3d} sec | sa={sa_meta['chCount']:3d} ch ({sa_meta['shlokaCount']:5,d} sl)"
        )

    index_doc = {
        "slug": "mahabharata",
        "total": tot_sa_sl,
        "withBn": tot_bn_ch,
        "withEn": tot_en_ch,
        "bnChTotal": tot_bn_ch,
        "bnUpaTotal": tot_bn_upa,
        "enSecTotal": tot_en_ch,
        "saChTotal": tot_sa_ch,
        "saShlokaTotal": tot_sa_sl,
        "parvas": parvas_meta,
        "chapters": audit_chapters,
    }
    write_json(OUT / "index.json", index_doc)
    print(
        f"\n✓ mahabharata: 18 পার্ব | বাংলা {tot_bn_ch:,d} অধ্যায় ({tot_bn_upa:,d} উপাখ্যান) | "
        f"ইংরেজি {tot_en_ch:,d} পরিচ্ছেদ | সংস্কৃত {tot_sa_ch:,d} অধ্যায় ({tot_sa_sl:,d} শ্লোক)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
