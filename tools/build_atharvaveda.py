#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""অথর্ববেদ (শৌনক সংহিতা) ডেটা-নির্মাতা — assets/grantho/data/atharvaveda/

উৎস ও নীতি (অনুমানভিত্তিক পাঠ বর্জন):
  ১. সংস্কৃত মূল পাঠ (সস্বর দেবনাগরী): vishvAsa/vedAH (`sarva-prastutiH`) —
     ২০ কাণ্ড, ৭৩৬ সূক্ত, ৫,৯৭৬ মন্ত্রের সবগুলোতে `मूलम् (VS)` থেকে।
  ২. ইংরেজি অনুবাদ (`en/ch1..20.json`): Ralph T.H. Griffith (১৮৯৫–৯৬,
     sacred-texts / vishvAsa/vedAH) ও W.D. Whitney (১৯০৫, কেবল যেখানে
     Griffith নেই বা দেবনাগরী মিশে গেছে) এবং হুবহু পুনরাবৃত্ত একই মন্ত্রের
     নিরীক্ষিত মিল; যেখানে উভয়েই অনুপস্থিত সেখানে ফাঁকা রাখা হয়।
  ৩. বাংলা অনুবাদ (`bn`): পূর্বে সংগৃহীত ebanglalibrary.com-এর JSON (`f4726c4`)
     থেকে কেবল যে সূক্ত/মন্ত্রগুলো সংস্কৃত ও শ্লোকসংখ্যার সাথে হুবহু মিলেছে —
     সমান দৈর্ঘ্য, কাণ্ড ৭ (`sid >= ৬৭ → sid+১`) ও কাণ্ড ১৯ (`sid >= ৮ → sid-১`)
     সূক্ত-ক্রম, কাণ্ড ১১.১–২ ও ১৯.৬, এবং কগনেট-যাচাইকৃত ছাঁটা সূক্ত।
     বাংলা-লিপি সংস্কৃত (কাণ্ড ৫ ও ২০.৩৮–৪৭), অসম্পূর্ণ খণ্ডিত সূক্ত
     (কাণ্ড ৮, ১১.৩–১০, ১৭, ১৮) ও লগইন/টীকা-দূষিত পঙক্তি বাদ রাখা হয়েছে।
"""
import html as htmllib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "grantho" / "data" / "atharvaveda"
EN_DIR = OUT_DIR / "en"

CROOT = pathlib.Path(os.environ.get(
    "AV_CONTENT_ROOT",
    "/tmp/av_test/vedah_content/atharva/shaunakam/rUDha-saMhitA/sarva-prastutiH",
))
TROOT = pathlib.Path(os.environ.get(
    "AV_TIKA_ROOT",
    "/tmp/av_test/vishvasa/atharva/shaunakam/rUDha-saMhitA/sarvASh_TIkAH",
))
ST_AV_DIR = pathlib.Path(os.environ.get(
    "AV_SACRED_TEXTS",
    "/tmp/av_test/hinduism-sacred-texts-main/sacred-texts/raw/hin/av",
))
BN_SRC_DIR = pathlib.Path(os.environ.get("AV_BN_DIR", "/tmp/av_test/bn"))

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
DEVA_RE = re.compile(r"[\u0900-\u097F]")
ASCII_LOGIN_RE = re.compile(
    r"(Lost your password|confirmation will be emailed|"
    r"Username or Email|Register|Log In|mation will be emailed)",
    re.I,
)
MANTRARTHA_RE = re.compile(
    r"^[\[\(\s]*মন্ত[্\u09cd\u09b0]?[াী]?[র]?্থ[-–:\s]*আলোচনা|^[\[\(\s]*মন্ত্ৰার্থ",
)

DEITY_RULES = [
    (r"(?:अग्नि|agni|jātaved|जातवेद|वैश्वानर|आग्नेय|द्रविणोद|draviṇod)", "অগ্নি"),
    (r"(?:इन्द्र|indra|śakra|maghavan|मघवन्|ऐन्द्र|आइन्द्र)", "ইন্দ্র"),
    (r"(?:सोम|soma|pavamān|पवमान|सौम)", "সোম"),
    (r"(?:वरुण|varuṇa|varuna|वारुण)", "বরুণ"),
    (r"(?:मरुत्|marut|मारुत)", "মরুৎগণ"),
    (r"(?:द्यावापृथिवी|dyāvāpṛthiv|Heaven and Earth|रोदसी)", "দ্যাবা-পৃথিবী"),
    (r"(?:पृथिवी|भूमि|pṛthiv|prithiv|bhūmi|\bearth\b|मही)", "পৃথিবী"),
    (r"(?:सूर्य|sūrya|surya|आदित्य|āditya|सवितृ|savitar|सविता|रोहित|विवस्व)", "সূর্য"),
    (r"(?:बृहस्पति|ब्रह्मणस्पति|bṛhaspati|brihaspati|brahmaṇaspati|bārhaspat)", "বৃহস্পতি"),
    (r"(?:रुद्र|भव.?शर्व|rudra|bhava|śarva|sarva|mahādeva|पशुपति)", "রুদ্র"),
    (r"(?:सरस्वती|sarasvat)", "সরস্বতী"),
    (r"(?:अश्विन्|अश्विनौ|aśvin|asvin)", "অশ্বিদ্বয়"),
    (r"(?:आपः|अप्सु|apām|waters|\bअपः|अपांनपा)", "জলদেবী অপ্"),
    (r"(?:वायु|वात|vāyu|vāta|\bwind\b|मातरिश्व)", "বায়ু"),
    (r"(?:विष्णु|viṣṇu|vishnu)", "বিষ্ণু"),
    (r"(?:यम|yama|पितृ|pitṛ|\bfathers\b)", "যম ও পিতৃগণ"),
    (r"(?:प्रजापति|prajāpati|prajapati|धातृ|विश्वकर्मा|vāiśvakarm)", "প্রজাপতি"),
    (r"(?:काल|kāla|\btime\b)", "কাল"),
    (r"(?:काम|kāma|\blove\b|\bdesire\b)", "কাম"),
    (r"(?:ब्रह्म|brahma|adhyātma|अध्यात्म|व्रात्य|vrātya|पुरुष|puruṣa|स्कम्भ|प्राण|वेन|विराट्|virāṭ|virāj)", "ব্রহ্ম ও অধ্যাত্ম"),
    (r"(?:ओषधि|वनस्पति|oṣadhi|vanaspati|vānaspat|मणि|दर्भ|कुष्ठ|अञ्जन|शङ्ख|पर्ण|जङ्गिड|अश्वत्थ)", "ওষধি ও মণি"),
    (r"(?:उषस्|uṣas|\bdawn\b|रात्रि|rātri|\bnight\b)", "উষা ও রাত্রি"),
    (r"(?:विश्वे.*देवा|viśve.*dev|all[- ]gods)", "বিশ্বদেবগণ"),
    (r"(?:मन्यु|manyu|\bwrath\b)", "মন্যু"),
    (r"(?:वाचस्पति|वाक्|vāc|\bspeech\b|मेधा)", "বাক্ ও মেধা"),
    (r"(?:अर्यमन्|aryaman|भग|bhaga|पूषन्|pūṣan|मित्र|mitra|त्वष्टृ|आदित्य)", "আদিত্যগণ"),
    (r"(?:गो|वशा|धेनु|ब्रह्मौदन|ओदन|odana|\bcow\b)", "গো ও ব্রহ্মৌদন"),
    (r"(?:चन्द्र|cāndram|चन्द्रम)", "চন্দ্র"),
    (r"(?:विद्युत्|vaidyut|पर्जन्य|parjanya)", "পর্জন্য ও বিদ্যুৎ"),
    (r"(?:धन्वन्तरि|भैषज्य|आयुः|dhanvantari|bhaiṣaj|यक्ष्म|ज्वर|कृत्या|kṛtyā)", "ভৈষজ্য ও শান্তি"),
    (r"(?:वास्तोष्पति|vāstoṣpat|शाला|आशापाला|स्वस्ति)", "বাস্তু ও স্বস্তি"),
    (r"(?:सीता|sītā)", "সীতা ও কৃষি"),
    (r"(?:गन्धर्व|अप्सर|gandharv)", "গন্ধর্ব ও অপ্সরা"),
    (r"(?:पशवः|paśav)", "পশুসম্পদ"),
]

DEVA_TO_BN = {
    "अ": "অ", "आ": "আ", "इ": "ই", "ई": "ঈ", "उ": "উ", "ऊ": "উ",
    "ऋ": "ঋ", "ॠ": "ঋ", "ए": "এ", "ऐ": "ঐ", "ओ": "ও", "औ": "ঔ",
    "ा": "া", "ि": "ি", "ी": "ী", "ु": "ু", "ू": "ু", "ृ": "ৃ",
    "े": "ে", "ै": "ৈ", "ो": "ো", "ौ": "ৌ", "्": "্", "ं": "ং",
    "ः": "ঃ", "ँ": "ঁ",
    "क": "ক", "ख": "খ", "ग": "গ", "घ": "ঘ", "ङ": "ঙ",
    "च": "চ", "छ": "ছ", "ज": "জ", "झ": "ঝ", "ञ": "ঞ",
    "ट": "ট", "ठ": "ঠ", "ड": "ড", "ढ": "ঢ", "ण": "ণ",
    "त": "ত", "थ": "থ", "द": "দ", "ध": "ধ", "न": "ন",
    "प": "প", "फ": "ফ", "ब": "ব", "भ": "ভ", "म": "ম",
    "य": "য", "र": "র", "ल": "ল", "ळ": "ল", "व": "ব",
    "श": "শ", "ष": "ষ", "स": "স", "ह": "হ",
}


def bn_dig(n: int) -> str:
    return str(n).translate(BN_DIGITS)


def to_phon_sk(s: str) -> str:
    out = []
    for ch in s:
        if 0x0951 <= ord(ch) <= 0x0954 or ch in "।॥०१२३४५६७८९0123456789ऽ":
            continue
        out.append(DEVA_TO_BN.get(ch, ch if ch == " " else ""))
    t = re.sub(r"\s+", " ", "".join(out)).strip()
    return t.replace("ী", "ি").replace("ূ", "ু").replace("ণ", "ন").replace("শ", "স").replace("ষ", "স").replace("ৎ", "ত")


def norm_bn_txt(s: str) -> str:
    s = re.sub(r"[^অ-ঔক-হংঃঁা-ৌ্\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("য়", "য").replace("ী", "ি").replace("ূ", "ু").replace("ণ", "ন").replace("শ", "স").replace("ষ", "স").replace("ড়", "ড").replace("ৎ", "ত")


def ngrams(s: str, n: int = 4) -> set[str]:
    s = s.replace(" ", "")
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def sim(bn_t: str, sk_t: str) -> float:
    g1 = ngrams(norm_bn_txt(bn_t), 4)
    g2 = ngrams(to_phon_sk(sk_t), 4)
    if not g1 or not g2:
        return 0.0
    return len(g1 & g2) / max(1, len(g2))


def norm_sk_key(s: str) -> str:
    return re.sub(r"[\u0951-\u0954\u0964\u0965०-९0-9\s।॥]", "", s)


def parse_sacred_texts() -> dict[tuple[int, int, int], str]:
    """sacred-texts/raw/hin/av/av*.htm থেকে Griffith অনুবাদ (anchor টাইপোসহ)।"""
    out: dict[tuple[int, int, int], str] = {}
    if not ST_AV_DIR.is_dir():
        return out
    for path in sorted(ST_AV_DIR.glob("av*.htm")):
        mfn = re.fullmatch(r"av(\d{2})(\d{3})\.htm", path.name)
        if not mfn:
            continue
        fk, fs = int(mfn.group(1)), int(mfn.group(2))
        raw = path.read_text(encoding="utf-8", errors="ignore")
        raw = re.sub(r'<a\s+name="page_[^"]+"[^>]*>.*?</a>', " ", raw, flags=re.S | re.I)
        raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
        if "<hr" in raw.lower():
            parts_hr = re.split(r"<hr\b", raw, flags=re.I)
            raw = max(parts_hr, key=lambda p: p.count("an_"))
        anchors = list(re.finditer(
            r'<span\s+class="margnote"[^>]*>.*?<A\s+NAME="an_(\d{2})(\d{3})(\d{2})">([^<]*)</A>.*?</span>',
            raw, re.S | re.I,
        ))
        if not anchors:
            anchors = list(re.finditer(r'<A\s+NAME="an_(\d{2})(\d{3})(\d{2})">([^<]*)</A>', raw, re.S | re.I))
        for i, m in enumerate(anchors):
            ak, a_s, av = int(m.group(1)), int(m.group(2)), int(m.group(3))
            shown_v = int(m.group(4).strip()) if m.group(4).strip().isdigit() else av
            # single-hymn HTML-এ ভুল anchor ID (যেমন av03029 -> an_0302708 >8<, av20068 -> an_2006841 >11<) ঠিক করা
            if ak == fk and a_s != fs and shown_v == av:
                a_s = fs
            elif ak == fk and a_s == fs and shown_v != av:
                av = shown_v
            seg = raw[m.end():anchors[i + 1].start() if i + 1 < len(anchors) else len(raw)]
            seg = re.split(r"<h[1-6]\b|<hr\b|<div\b", seg, flags=re.I)[0]
            seg = htmllib.unescape(re.sub(r"<[^>]+>", " ", seg))
            seg = re.sub(r"\[p\.\s*[a-z]?\d+\]", " ", seg, flags=re.I)
            seg = re.sub(r"\s+", " ", seg).strip()
            seg = re.sub(r"([a-zA-Z])-\s+([a-z])", r"\1\2", seg)
            if seg and not DEVA_RE.search(seg):
                out[(ak, a_s, av)] = seg
    return out


def clean_griffith(g: str) -> str:
    g = re.sub(r"\[p\.\s*[a-z]?\d+\]", " ", g, flags=re.I)
    g = re.sub(r"\s+", " ", g).strip()
    g = re.sub(r"([a-zA-Z])-\s+([a-z])", r"\1\2", g)
    g = re.sub(r"^\d+\.\s+", "", g)
    return g


def clean_whitney(w: str) -> str:
    w = w.replace("\\[", "[").replace("\\]", "]")
    w = re.sub(r"\*\*[a-z]\.\*\*\s*", "", w)
    w = re.sub(r"⌊\s*\d+\.?\s*⌋\s*", "", w)
    w = w.replace("⌊", "").replace("⌋", "")
    w = re.sub(r"^\d+\.\s*", "", w)
    w = re.sub(r"\*([^*]+)\*", r"\1", w)
    return re.sub(r"\s+", " ", w).strip()


def extract_deity(raw_sukta: str, raw_idx: str) -> str:
    blob = raw_sukta + "\n" + raw_idx
    deity_str = ""
    mwa = re.search(r"<details><summary>Whitney anukramaṇī</summary>(.*?)</details>", blob, re.S)
    if mwa and "—" in mwa.group(1):
        deity_str += " " + mwa.group(1).split("—", 1)[1].split(".")[0]
    mvh = re.search(r"<details><summary>VH anukramaṇī</summary>(.*?)</details>", blob, re.S)
    if mvh:
        txt_vh = re.sub(r"\s+", " ", mvh.group(1)).strip()
        segs = [x.strip() for x in txt_vh.split("।") if x.strip()]
        # প্রথম যে অংশে ছন্দ ছাড়া সংখ্যা-চিহ্নিত ঋষি তালিকা আছে (যেমন '१-४ विश्वामित्रः'), তার পরের অংশই দেবতা
        picked_vh = ""
        for idx_s, seg in enumerate(segs):
            if re.search(r"[\(]?[०-९]+[-–,]|[०-९]+\s+[अ-ह]", seg) and idx_s + 1 < len(segs):
                picked_vh = segs[idx_s + 1]
                break
        if not picked_vh and len(segs) >= 3:
            picked_vh = segs[2]
        elif not picked_vh and len(segs) == 2:
            picked_vh = segs[0]
        deity_str += " " + picked_vh
    for tag in ("Whitney subject", "Griffith"):
        m = re.search(rf"<details><summary>{tag}</summary>(.*?)</details>", blob, re.S)
        if m and not re.search(r"|".join(p for p, _ in DEITY_RULES), deity_str, re.I):
            deity_str += " " + m.group(1)
    for pat, label in DEITY_RULES:
        if re.search(pat, deity_str, re.I):
            return label
    return ""


def clean_bn_verses(svs: list[dict]) -> list[str]:
    out = []
    for v in svs:
        t = (v.get("bn") or "").strip()
        if ASCII_LOGIN_RE.search(t):
            t = ASCII_LOGIN_RE.split(t)[0].strip()
        if MANTRARTHA_RE.match(t):
            continue
        if not t:
            continue
        if out and t.startswith(")"):
            out[-1] = out[-1] + " " + t
        else:
            out.append(t)
    return out


def ensure_bn_source() -> None:
    """যদি `/tmp/av_test/bn` না থাকে, git commit `f4726c4` থেকে extract করি।"""
    if (BN_SRC_DIR / "ch1.json").exists():
        return
    BN_SRC_DIR.mkdir(parents=True, exist_ok=True)
    for k in range(1, 21):
        res = subprocess.run(
            ["git", "show", f"f4726c4:assets/grantho/data/atharvaveda/ch{k}.json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if res.returncode == 0 and res.stdout.strip():
            (BN_SRC_DIR / f"ch{k}.json").write_text(res.stdout, encoding="utf-8")


def main() -> int:
    if not CROOT.is_dir() or not TROOT.is_dir():
        raise SystemExit(f"vedAH উৎস পাওয়া যায়নি: {CROOT} / {TROOT}")
    ensure_bn_source()

    st_en = parse_sacred_texts()

    # ১) সব ২০ কাণ্ডের ৭৩৬ সূক্ত ও ৫,৯৭৬ মন্ত্র পড়ি (মূল Sanskrit + এন + দেবতা)
    kandas: dict[int, dict] = {}
    sk_norm_en: dict[str, str] = {}
    ved_sk: dict[tuple[int, int, int], str] = {}
    ved_len: dict[tuple[int, int], int] = {}

    for k in range(1, 21):
        ck = CROOT / f"{k:02d}"
        tk = TROOT / f"{k:02d}"
        sdirs = {
            int(d.name.split("_")[0]): d
            for d in tk.iterdir()
            if d.is_dir()
        }
        sukta_files = sorted(
            (f for f in ck.iterdir() if f.suffix == ".md" and f.name != "_index.md"),
            key=lambda p: int(p.stem.split("_")[0]),
        )
        k_suktas = []
        for sf in sukta_files:
            s = int(sf.stem.split("_")[0])
            raw = sf.read_text(encoding="utf-8")
            sd = sdirs[s]
            idx_md = sd / "_index.md"
            raw_idx = idx_md.read_text(encoding="utf-8") if idx_md.exists() else ""
            deity = extract_deity(raw, raw_idx)
            vfiles = {
                int(f.stem.split("_")[0]): f
                for f in sd.iterdir()
                if f.suffix == ".md" and f.name != "_index.md"
            }
            parts = re.split(r"(?m)^## (\d+) ", raw)
            verses = []
            for i in range(1, len(parts), 2):
                vn = int(parts[i])
                m_sk = re.search(r"<details><summary>मूलम् \(VS\)</summary>(.*?)</details>", parts[i + 1], re.S)
                if not m_sk:
                    raise ValueError(f"সংস্কৃত অনুপস্থিত: {k}.{s}.{vn}")
                # মূল লাইন-ব্রেক পঙক্তি অনুযায়ী রাখি; অতিরিক্ত স্পেস পরিষ্কার
                sk_lines = [re.sub(r"\s+", " ", ln).strip() for ln in m_sk.group(1).strip().splitlines() if ln.strip()]
                sk = "\n".join(sk_lines)
                assert not re.search(r"[<>]", sk), f"HTML ট্যাগ পাওয়া গেছে: {k}.{s}.{vn}"
                ved_sk[(k, s, vn)] = sk.replace("\n", " ")

                g_raw = w_raw = ""
                if vn in vfiles:
                    ttxt = vfiles[vn].read_text(encoding="utf-8")
                    mg = re.search(r"<details><summary>Griffith</summary>(.*?)</details>", ttxt, re.S)
                    mw = re.search(r"<details><summary>Whitney</summary>(.*?)</details>", ttxt, re.S)
                    if mg:
                        g_raw = mg.group(1).strip()
                    if mw:
                        mt = re.search(r"### Translation\s*(.*?)(?:\n### |\Z)", mw.group(1), re.S)
                        w_raw = (mt.group(1) if mt else mw.group(1)).strip()

                en = ""
                if g_raw and not DEVA_RE.search(g_raw):
                    en = clean_griffith(g_raw)
                elif (k, s, vn) in st_en:
                    en = st_en[(k, s, vn)]
                elif w_raw and not DEVA_RE.search(w_raw):
                    en = clean_whitney(w_raw)

                if en:
                    assert not DEVA_RE.search(en), f"ইংরেজিতে দেবনাগরী ঢুকেছে: {k}.{s}.{vn}"
                    nsk = norm_sk_key(sk)
                    if nsk and nsk not in sk_norm_en:
                        sk_norm_en[nsk] = en

                verses.append({"vn": vn, "sk": sk, "en": en, "bn": ""})

            ved_len[(k, s)] = len(verses)
            k_suktas.append({"id": s, "deity": deity, "verses": verses})
        kandas[k] = {"id": k, "suktas": k_suktas}

    # দ্বিতীয় পাস: হুবহু অভিন্ন পুনরাবৃত্ত মন্ত্র (যেমন ১৫.২.১৫-১৬, ২৩-২৪, ৩১-৩২ এবং ১৫.৫.৬..১৮)
    for k in range(1, 21):
        for su in kandas[k]["suktas"]:
            for v in su["verses"]:
                if not v["en"]:
                    nsk = norm_sk_key(v["sk"])
                    if nsk in sk_norm_en:
                        v["en"] = sk_norm_en[nsk]

    # ২) বাংলা অনুবাদ (f4726c4) — কঠোরভাবে নিরীক্ষিত সূক্ত/মন্ত্র ম্যাপিং
    bn_map: dict[tuple[int, int, int], str] = {}

    # (ক) কাণ্ড ১-৪, ৬, ৭ (<=৬৬ -> id, >=৬৭ -> id+১), ১৯ (<=৫ -> id, >=৮ -> id-১), ২০ (১..৩৭ -> id)
    for k in (1, 2, 3, 4, 6, 7, 19, 20):
        bf = BN_SRC_DIR / f"ch{k}.json"
        if not bf.exists():
            continue
        bd = json.loads(bf.read_text(encoding="utf-8"))
        for bsu in bd.get("suktas", []):
            sid = int(bsu["id"])
            if k == 7 and sid >= 67:
                ts = sid + 1
            elif k == 19 and sid in (6, 7):
                continue
            elif k == 19 and sid >= 8:
                ts = sid - 1
            elif k == 20 and sid >= 38:
                continue
            else:
                ts = sid
            tl = ved_len.get((k, ts), -1)
            if tl <= 0:
                continue
            raw_vs = [x for x in bd["verses"] if bsu["from"] <= x["n"] <= bsu["to"]]
            rep = clean_bn_verses(raw_vs)
            if not rep:
                continue
            # কোনো রেঞ্জ-সমন্বয় (-৪।) বা মন্ত্রার্থ-নোট থাকলে বর্জন
            if any(re.match(r"^[-–][০-৯0-9]+", x) or len(x) < 20 for x in rep):
                continue

            if len(rep) == tl:
                for idx, txt in enumerate(rep):
                    bn_map[(k, ts, idx + 1)] = txt
            elif 1 <= len(rep) < tl:
                # কেবল কগনেট ডায়াগোনাল যাচাই উত্তীর্ণ ও সূচনা-টীকাহীন সূক্তই গৃহীত
                if re.match(r"^[\(\[]\s*(এই|এখানে|পূর্ব|ইখং|সম্পূর্ণ)", rep[0]):
                    continue
                scores = []
                off_beats = 0
                for idx, bt in enumerate(rep):
                    sd = sim(bt, ved_sk[(k, ts, idx + 1)])
                    scores.append(sd)
                    s_nxt = sim(bt, ved_sk[(k, ts, idx + 2)]) if idx + 2 <= tl else 0.0
                    if s_nxt > sd + 0.03:
                        off_beats += 1
                if off_beats == 0 and min(scores) > 0.02 and (sum(scores) / len(scores)) >= 0.08:
                    for idx, txt in enumerate(rep):
                        bn_map[(k, ts, idx + 1)] = txt

    # (খ) কাণ্ড ১১.১ (chunks 1..4 = ৩৭), ১১.২ (chunks 5..7 = ৩১), এবং ১৯.৬ (chunks 6+7 = ১..১৩)
    if (BN_SRC_DIR / "ch11.json").exists():
        b11 = json.loads((BN_SRC_DIR / "ch11.json").read_text(encoding="utf-8"))
        k11_1 = clean_bn_verses([v for su in b11["suktas"][:4] for v in b11["verses"] if su["from"] <= v["n"] <= su["to"]])
        k11_2 = clean_bn_verses([v for su in b11["suktas"][4:7] for v in b11["verses"] if su["from"] <= v["n"] <= su["to"]])
        assert len(k11_1) == ved_len[(11, 1)] == 37
        assert len(k11_2) == ved_len[(11, 2)] == 31
        for idx, txt in enumerate(k11_1):
            bn_map[(11, 1, idx + 1)] = txt
        for idx, txt in enumerate(k11_2):
            bn_map[(11, 2, idx + 1)] = txt

    if (BN_SRC_DIR / "ch19.json").exists():
        b19 = json.loads((BN_SRC_DIR / "ch19.json").read_text(encoding="utf-8"))
        k19_6 = clean_bn_verses([v for su in b19["suktas"][5:7] for v in b19["verses"] if su["from"] <= v["n"] <= su["to"]])
        assert len(k19_6) == 13
        for idx, txt in enumerate(k19_6):
            bn_map[(19, 6, idx + 1)] = txt

    # ৩) চূড়ান্ত JSON আউটপুট তৈরি (index.json + ch1..20.json + en/ch1..20.json)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    chapters_meta = []
    tot_v = tot_sk = tot_bn = tot_en = tot_su = 0

    for k in range(1, 21):
        kd = kandas[k]
        ch_verses = []
        ch_suktas = []
        en_verses = {}
        deity_har = {}
        seq_n = 0
        k_bn = k_sk = k_en = 0

        for su in kd["suktas"]:
            sid = su["id"]
            s_from = seq_n + 1
            for v in su["verses"]:
                seq_n += 1
                vn = v["vn"]
                sk = v["sk"]
                en = v["en"]
                bn_txt = bn_map.get((k, sid, vn), "")
                row = {
                    "n": seq_n,
                    "ch": sid,
                    "vn": vn,
                    "sk": sk,
                    "bn": bn_txt,
                }
                ch_verses.append(row)
                if sk:
                    k_sk += 1
                if bn_txt:
                    k_bn += 1
                if en:
                    en_verses[str(seq_n)] = en
                    k_en += 1
            s_to = seq_n
            su_entry = {
                "id": sid,
                "from": s_from,
                "to": s_to,
                "vfrom": 1,
                "vto": len(su["verses"]),
                "mantra": len(su["verses"]),
            }
            if su["deity"]:
                su_entry["deity"] = su["deity"]
                deity_har[str(sid)] = su["deity"]
            ch_suktas.append(su_entry)

        ch_title = f"কাণ্ড {bn_dig(k)}"
        ch_obj = {
            "id": k,
            "bn": ch_title,
            "count": seq_n,
            "from": 1,
            "to": seq_n,
            "withBn": k_bn,
            "suktaCount": len(ch_suktas),
            "groupWord": "সূক্ত",
            "suktas": ch_suktas,
            "verses": ch_verses,
        }
        (OUT_DIR / f"ch{k}.json").write_text(
            json.dumps(ch_obj, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        en_obj = {"id": k, "verses": en_verses}
        (EN_DIR / f"ch{k}.json").write_text(
            json.dumps(en_obj, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        # কোনো কাণ্ডে কয়টি সূক্তে ইংরেজি আছে (enNote নিয়ন্ত্রণ)
        s_with_en = sum(
            1 for s_m in ch_suktas
            if any(str(nn) in en_verses for nn in range(s_m["from"], s_m["to"] + 1))
        )
        ch_meta = {
            "id": k,
            "bn": ch_title,
            "count": seq_n,
            "from": 1,
            "to": seq_n,
            "withBn": k_bn,
            "suktaCount": len(ch_suktas),
            "aligned": s_with_en,
            "grid": {"count": len(ch_suktas)},
        }
        if deity_har:
            ch_meta["deityHar"] = deity_har
        chapters_meta.append(ch_meta)

        tot_v += seq_n
        tot_sk += k_sk
        tot_bn += k_bn
        tot_en += k_en
        tot_su += len(ch_suktas)

    def commas_bn(num: int) -> str:
        return f"{num:,}".translate(BN_DIGITS)

    idx_obj = {
        "slug": "atharvaveda",
        "bn": "অথর্ববেদ সংহিতা",
        "en": "Atharvaveda (Śaunaka)",
        "total": tot_v,
        "withBn": tot_bn,
        "withSk": tot_sk,
        "withEn": tot_en,
        "suktaTotal": tot_su,
        "verseWord": "মন্ত্র",
        "groupWord": "সূক্ত",
        "chword": "কাণ্ড",
        "skSrc": "संस्कृत मूलम् (VS) — vishvAsa/vedAH (शौनक-संहिता)",
        "enSrc": "Ralph T.H. Griffith (1895–96) & W.D. Whitney (1905)",
        "bnSrc": "বাংলা অনুবাদ — ebanglalibrary.com (যাচাইকৃত সূক্তসমূহ)",
        "note": (
            f"শৌনক শাখার পূর্ণ সংস্কৃত মূল পাঠ ({commas_bn(tot_sk)}/{commas_bn(tot_v)} মন্ত্র, "
            "বৈদিক স্বরচিহ্নসহ — vishvAsa/vedAH); ইংরেজি অনুবাদ R.T.H. Griffith ও "
            f"W.D. Whitney ({commas_bn(tot_en)} মন্ত্র); বাংলা অনুবাদ ebanglalibrary.com থেকে "
            f"কেবল নিরীক্ষিত ও শ্লোক-মিলে যাওয়া {commas_bn(tot_bn)}টি মন্ত্রেই যুক্ত করা হয়েছে — "
            "অসংলগ্ন অংশে অনুমান করে বাংলা বসানো হয়নি।"
        ),
        "chapters": chapters_meta,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(idx_obj, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    print(f"✓ {OUT_DIR.relative_to(ROOT)}: {len(chapters_meta)} কাণ্ড, {tot_su} সূক্ত, {tot_v} মন্ত্র")
    print(f"  Sanskrit: {tot_sk}/{tot_v} · English: {tot_en}/{tot_v} · Bengali: {tot_bn}/{tot_v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
