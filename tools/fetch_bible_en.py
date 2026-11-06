#!/usr/bin/env python3
"""বাংলা বাইবেলের পাশে ইংরেজি অনুবাদ: vatican.va-র The New American Bible।

উৎস: https://www.vatican.va/archive/ENG0839/_INDEX.HTM (IntraText) — প্রতিটি
অধ্যায়ের আলাদা পাতা, পাতার কোড পরপর base36-এ বাড়ে (__P3, __P4 … __PZ, __P10 …)।
সূচি-পাতার HTML গঠন নিয়ে ভাগ্য পরীক্ষা না করে আমরা কোডগুলো পরপর হেঁটে যাই:
প্রতিটি পাতা নিজেই বলে দেয় সে কোন পুস্তকের কততম অধ্যায় (ব্রেডক্রাম্ব:
«The Pentateuch › Genesis › Chapter 1»), তাই ম্যাপিং ভুল হওয়ার সুযোগ কম।

নীতি (বাংলা অংশের মতোই):
  ▸ উৎসে যা নেই তা অনুমান করে বসানো হয় না;
  ▸ ইংরেজি বসে কেবল তখনই যখন পদ-সংখ্যা ও পদ-নম্বর বাংলার সঙ্গে হুবহু মেলে
    (ব্যবহারকারীর সিদ্ধান্ত: «মিললেই ইংরেজি, না মিললে ফাঁকা + রিপোর্ট»);
  ▸ অমিল হলে পুরো অধ্যায়ে ইংরেজি বাদ, কারণসহ তালিকা _debug/bible_en_mismatch.txt;
  ▸ কৃতিত্ব: «The New American Bible — vatican.va»।

বাংলা উৎস ৬৬ পুস্তকের (প্রোটেস্ট্যান্ট ক্যানন); NAB ৭৩ পুস্তকের। অতিরিক্ত
৭টি পুস্তক (Tobit, Judith, Wisdom, Sirach, Baruch, 1–2 Maccabees) বাংলা সূচিতে
নেই বলে বাদ পড়ে (ব্যবহারকারীর সিদ্ধান্ত)।
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_ebl as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SLUG = "bible"
OUT = ROOT / "assets/grantho/data" / SLUG
EN = OUT / "en"
RAW = EN / "raw"
DBG = OUT.parent / "_debug"   # fetch_bible.py-এর সাথে একই ফোল্ডার
MANIFEST = DBG / "bible_books.json"          # fetch_bible.py-র discover-এর লেখা
EN_SRC = "The New American Bible — vatican.va"
# ইংরেজি পার্সারের সংস্করণ — ৪: প্রথম ব্যবহারযোগ্য সমন্বিত পার্সার
# (একা-সংখ্যা লাইন, পাঠান্তর্গত [n] টীকা-কাটা, পদ-ক্রম-যাচাই, সামসঙ্গীত alias)।
# CI থেকে PV_EN env দিয়ে বদলানো যায় — কিছু বদলালে তবেই বাড়াতে হয়, নইলে
# প্রতিটি রানে অকারণ রি-ওয়াক হতো।
PV_EN = int(os.environ.get("PV_EN") or 4)

BASE = "https://www.vatican.va/archive/ENG0839/"
ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# NAB-এর ব্রেডক্রাম্ব-নাম → আমাদের পুস্তক-ক্রম (১..৬৬)। ebl-পাতার ইংরেজি
# লেবেল ভরসা নয় (সেখানে «রোমীয় (Acts)»-এর মতো ভুল ছাপা আছে), তাই ম্যাপিং
# প্রচলিত ক্যানন-ক্রমে এই স্থির তালিকা থেকে — ক্যাথলিক অতিরিক্ত ৭টি পুস্তক
# তালিকায় নেই বলে আপনা থেকে বাদ পড়ে।
NAB_ORDER = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts of the Apostles", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
    "Revelation",
]
NAB_ID = {}
for _i, _n in enumerate(NAB_ORDER, 1):
    NAB_ID[_n.lower()] = _i
    if _n == "Song of Songs":
        # NAB-পাতার ব্রেডক্রাম্বে নামটি «Song of Songs»-ই, তবে তালিকার
        # কিছু সংস্করণে «Song of Solomon» — দুটোই এক পুস্তক (গীতসংহিতা ২২)।
        # আগে এই alias না থাকায় ইংরেজি অংশে সামসঙ্গীতের ৮টি অধ্যায়ই
        # «বাংলা সূচিতে নেই» ভেবে বাদ পড়ছিল।
        NAB_ID["song of solomon"] = _i
    if _n == "Acts of the Apostles":
        NAB_ID["acts"] = _i
    if _n == "Psalms":
        NAB_ID["psalm"] = _i

NAV_SKIP = re.compile(
    r"^(the new american bible|new american bible|intratext.*|\d{4}\s*\d{2}\s*\d{2}|"
    r"help|previous|next|click here.*|table of contents|statistics.*|back|up)$", re.I)
CHAPTER_LINE = re.compile(r"^chapter\s+(\d+)$", re.I)
INTRO_LINE = re.compile(r"^introduction$", re.I)
NUM_LINE = re.compile(r"^(\d{1,3})$")
FOOT_MARK = re.compile(r"^\[\d+\]\s*")


def tok_next(tok: str) -> str:
    """পাতা-কোডের পরের মান: 9→A, Z→10, 1Z→20 …

    সাবধান: বাড়াতে হয় শুধু সংখ্যা-অংশটুকু। আগে «P»-উপসর্গসহ পুরো টোকেন
    base36-এ বাড়ানো হতো — তাই «PZ» (আদিপুস্তক ৩৩)-এর পরে «P10»-এর বদলে
    «Q0» তৈরি হতো, আর হাঁটা বাইবেল ছেড়ে অন্য ডকুমেন্টের হাজারো পাতায়
    বাজেট পুড়িয়ে দিত (২,১০৯ পাতায় মাত্র ৩ অধ্যায়)।
    """
    n = 0
    for ch in tok:
        n = n * 36 + ALPHA.index(ch)
    n += 1
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = ALPHA[r] + out
    return out or "0"


def page_identity(lines):
    """পাতার নিজের পরিচয়: (পুস্তক-নাম, অধ্যায়-নম্বর) বা (নাম, None) ভূমিকা হলে।

    পুস্তক-নাম = «Chapter N» (বা «Introduction») লাইনের ঠিক আগের অখালি লাইন —
    ব্রেডক্রাম্বের শেষ ধাপ। আগে উপর থেকে প্রথম অ-ন্যাভ লাইন নেওয়া হতো, তাই
    পাতার নিজের শিরোনাম-লাইন («The New American Bible - IntraText») পুস্তক
    সেজে যেত আর সব পাতা এক নামের নিচে জমা হয়ে বাদ পড়ত।
    """
    idx = None
    for i, ln in enumerate(lines):
        if CHAPTER_LINE.match(ln) or INTRO_LINE.match(ln):
            idx = i
            break
    if idx is None:
        return None, None
    ch = int(CHAPTER_LINE.match(lines[idx]).group(1)) if CHAPTER_LINE.match(lines[idx]) else None
    for j in range(idx - 1, -1, -1):
        ln = lines[j]
        if not ln or NAV_SKIP.match(ln) or NUM_LINE.match(ln):
            continue
        if ln.lower().startswith("the pentateuch") or ln.lower().startswith(
                "the new american bible") or ln.lower() in (
                "old testament", "new testament"):
            continue
        return ln, ch
    return None, ch


def _en_parts(lines):
    """পাতার লাইন → [(পদ-নম্বর, পাঠ)] — IntraText-এর আসল গঠন অনুযায়ী।

    উৎস-পাতার (যেমন রোমীয় ২) গঠন: প্রতিটি পদ শুরু হয় **একা একটি সংখ্যা-লাইন**ে
    («1», «2» …), তারপর পাঠ — যার ভেতরে টীকা-নম্বর «[2]» আকারে লিংক হয়ে বসে
    («…you pass judgment. [2] For by the standard…»)। শেষে আবার «[1]» দিয়ে
    টীকা-তালিকা — পুনরাবৃত্ত পদ-নম্বরেই থামতে হয়।

    আগের পার্সার পাঠের ভেতরের «[2]» টীকা-চিহ্ন তুলত না (FOOT_MARK কেবল
    লাইনের শুরুতে লাগত), তাই ইংরেজি পাঠে টীকা-নম্বর জমে থাকত — লাইভে সেই
    দূষণই দেখা গিয়েছিল।

    তবে সব পাতা সমান নয় (পুরোনো রি-ফেচে রোমীয় ২-এর ৬টি পদই জমেছিল): কখনো
    «1 2 Paul…»-এর মতো **এক-লাইন** রূপও আসে। তাই দুই রূপই মেলানো হয় —
    ওই সংখ্যাগুলো §মধ্যে-পাঠ্য টীকা বা পদ-নম্বর, দুটোই হতে পারে; খাঁটি
    নম্বর-লাইনই একমাত্র ভরসা।
    """
    pure = []            # [(num, [lines])]
    for raw in lines:
        ln = FOOT_MARK.sub("", raw.strip())          # লাইন-শুরুর [n] কাটা
        if not ln or NAV_SKIP.match(ln):
            continue
        m = NUM_LINE.match(ln)
        if m:
            pure.append([int(m.group(1)), []])
            continue
        # পাঠের ভেতরের টীকা-লিংক [n] — শুধু সংখ্যা, তাই বাদ
        ln = re.sub(r"\[\d{1,3}\]", " ", ln)
        li = re.match(r"^(\d{1,3})\s+(\S.*)$", ln)   # ইনলাইন রূপের বাকিটা
        if li and not pure:                          # পাতা-শুরুই «1 2 Paul…» রূপে
            pure.append([int(li.group(1)), [li.group(2)]])
            continue
        if not pure:
            continue                                 # নম্বরের আগের অংশ = পরিচয়/ভূমিকা
        if li:
            ln = li.group(2)
        ln = re.sub(r"\s{2,}", " ", ln).strip()
        if ln:
            pure[-1][1].append(ln)
    return [(n, " ".join(t).strip()) for n, t in pure if n]


def parse_en_verses(lines):
    """পদ-তালিকা — নম্বর-ক্রম ধরে; বাদ পড়া পদ ফাঁকা (অনুমান নয়)।

    টীকা-তালিকা শুরু হয় পদ-নম্বর আবার ১-এ ফেরার পর (বা পিছিয়ে গেলে) —
    সেখানেই থামা হয়। এর আগে কোনো ছোট নম্বর এলে সেটিও টীকা (আন্তঃপাঠ্য
    ক্রস-রেফারেন্স), বাদ।
    """
    verses, expect = [], 1
    for num, en in _en_parts(lines):
        if num < expect:              # চিহ্ন/টীকা-নম্বর — পাঠ নয়
            if num == 1 and verses:   # টীকা-তালিকা শুরু
                break
            continue
        if num > expect:              # মাঝের পদ উৎসে নেই — অনুমান করি না
            for miss in range(expect, num):
                verses.append({"vn": miss, "en": "", "srcEmpty": True})
        verses.append({"vn": num, "en": en})
        expect = num + 1
    for v in verses:
        if not v["en"].strip():
            v["srcEmpty"] = True      # নম্বর ছাপা, পাঠ উৎসেই নেই
    return [v for v in verses if v["en"] or v.get("srcEmpty")]


def book_for(name):
    """NAB-নাম → {"i", "bn"}; বাংলা নাম আমাদের index.json থেকে (প্রতিবেদনের জন্য)।"""
    if not name:
        return None
    i = NAB_ID.get(name.strip().lower())
    if not i:
        return None
    bn = NAB_ORDER[i - 1]
    try:
        idx = json.loads((OUT / "index.json").read_text(encoding="utf-8"))
        for c in idx.get("chapters", []):
            if c.get("id") == i:
                bn = c.get("bn", bn)
                break
    except Exception:  # noqa: BLE001
        pass
    return {"i": i, "bn": bn}


def cmd_fetch(args):
    DBG.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    prog_p = DBG / "bible_en_progress.json"
    prog = json.loads(prog_p.read_text(encoding="utf-8")) if prog_p.exists() else {}
    if prog.get("pvEn") != PV_EN:      # পার্সার বদলেছে — পুরোনো হাঁটা বাতিল
        prog = {}
    tok = prog.get("token", "3")
    pend_name = prog.get("pendName")
    pend = {int(k): v for k, v in (prog.get("pendCh") or {}).items()}
    t0 = time.time()
    misses = 0
    pages = saved = 0
    unknown_seen = 0
    report = []
    while misses < 3:
        url = BASE + "__P" + tok + ".HTM"
        try:
            h = F.get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {tok}: {e}", flush=True)
            misses += 1
            tok = tok_next(tok)
            continue
        misses = 0
        pages += 1
        lines = [x.strip() for x in F.page_text(h).split("\n")]
        name, ch = page_identity(lines)
        if name is None and ch is None and unknown_seen < 3:
            unknown_seen += 1
            (DBG / "bible_en_unknown.txt").write_text(
                f"--- টোকেন {tok} ({url}) ---\n" + "\n".join(lines[:40]) + "\n",
                encoding="utf-8")
        if name and name != pend_name:
            # আগের পুস্তকের জমা পাঠ লিখে দিই
            if pend_name and pend:
                saved += save_raw(pend_name, pend, report)
            pend_name, pend = name, {}
        if name and ch:
            vs = parse_en_verses(lines)
            if vs:
                pend[ch] = vs
        prog = {"token": tok, "pendName": pend_name,
                "pendCh": {str(k): v for k, v in pend.items()},
                "pvEn": PV_EN, "when": int(time.time())}
        prog_p.write_text(json.dumps(prog, ensure_ascii=False), encoding="utf-8")
        if pages % 25 == 0:
            print(f"  … {pages} পাতা · এখন: {pend_name} অধ্যায় {ch} "
                  f"({int(time.time() - t0)}সে)", flush=True)
        if args.budget and (time.time() - t0) > args.budget * 60:
            print(f"⏱ বাজেট {args.budget} মিনিট শেষ — থামছি; পরের রানে চলবে।",
                  flush=True)
            break
        tok = tok_next(tok)
        time.sleep(args.delay)
    if pend_name and pend:
        saved += save_raw(pend_name, pend, report)
        prog["pendName"], prog["pendCh"] = None, {}
        prog_p.write_text(json.dumps(prog, ensure_ascii=False), encoding="utf-8")
    if misses >= 3 and saved:   # কর্পাসের শেষ পর্যন্ত হাঁটা + কিছু পেয়েছি
        (DBG / "bible_en_done.txt").write_text(
            f"পাতা {pages} · পুস্তক-ফাইল {saved} · {time.strftime('%d/%m %H:%M')} UTC\n",
            encoding="utf-8")
    txt = (f"=== ইংরেজি (NAB) ফেচ ===\nপাতা: {pages} · পুস্তক-ফাইল: {saved}\n"
           + "\n".join(report) + "\n=== শেষ ===\n")
    (DBG / "bible_en_report.txt").write_text(txt, encoding="utf-8")
    print(txt)
    return 0


def save_raw(name, chapters, report):
    book = book_for(name)
    if not book:
        report.append(f"  · বাদ (বাংলা সূচিতে নেই): {name} — অধ্যায় {len(chapters)}")
        return 0
    # পুরোনো ফাইলের অধ্যায় হারানো চলবে না: ছোট বাজেটে বইটি মাঝপথে থামলে কেবল
    # এই রানের অধ্যায় দিয়ে ফাইল লিখলে আগের নামানো অধ্যায়গুলো (সামসঙ্গীতের ৬১টি)
    # চিরতরে মুছে যেত। তাই আগের অধ্যায় + নতুনের ওভাররাইড।
    prev = {}
    fp = RAW / f"raw{book['i']}.json"
    if fp.exists():
        try:
            old = json.loads(fp.read_text(encoding="utf-8"))
            # কেবল একই পার্সারে বানানো অধ্যায় ধরে রাখা — পুরোনো (PV_EN≠বর্তমান)
            # অধ্যায় মাসানো মানে দূষণ জায়গায় পাকা হয়ে যাওয়া। নতুন পার্সার
            # সব অধ্যায় আবার পড়বে, তাই পুরোনোটা বাদ দেওয়াই নিরাপদ।
            if old.get("pvEn") == PV_EN:
                prev = old.get("chapters", {})
        except Exception:  # noqa: BLE001
            prev = {}
    allch = {**prev, **{str(k): v for k, v in chapters.items()}}
    obj = {"book": book["i"], "bn": book["bn"], "enName": name, "pvEn": PV_EN,
           "chapters": {k: allch[k] for k in sorted(allch, key=int)}}
    (RAW / f"raw{book['i']}.json").write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    report.append(f"  ✓ {book['i']:>2}. {book['bn']} ← {name}: অধ্যায় {len(chapters)}"
                  + (f" (আগের {len(prev)} ধরে মোট {len(allch)})" if len(allch) > len(chapters) else ""))
    return 1


def join_bookkeeping():
    """বাংলা পদের সঙ্গে ইংরেজি মেলানো — কেবল হুবহু মিললে।"""
    if not (OUT / "index.json").exists():
        print("⛔ বাংলা ডেটা নেই")
        return 2
    bad_pv = [p.name for p in RAW.glob("raw*.json")
              if json.loads(p.read_text(encoding="utf-8")).get("pvEn") != PV_EN][:5]
    if bad_pv:
        # পুরোনো পার্সারে জমানো পাঠের সঙ্গে নতুন পার্সারের ফল মেশানো বিপজ্জনক —
        # কিন্তু অচলও নয়: গঠন একই। তাই থামি না, চোখে আঙুল দিই।
        print(f"⚠ {len(bad_pv)}+ পুরোনো পার্সারের raw-ফাইল (pvEn≠{PV_EN}) — "
              f"যেমন {', '.join(bad_pv)}; মেলানোর আগে রি-ওয়াক দরকার")
    EN.mkdir(parents=True, exist_ok=True)
    idx = json.loads((OUT / "index.json").read_text(encoding="utf-8"))
    aligned = skipped = 0
    mismatch = []
    joined = {"slug": SLUG, "src": EN_SRC, "pvEn": PV_EN, "books": []}
    for c in idx["chapters"]:
        raw_p = RAW / f"raw{c['id']}.json"
        bp = OUT / f"ch{c['id']}.json"
        en_out = {"id": c["id"], "pvEn": PV_EN, "src": EN_SRC,
                  "verses": {}, "aligned": [], "skipped": []}
        if raw_p.exists() and bp.exists():
            raw = json.loads(raw_p.read_text(encoding="utf-8"))
            beng = json.loads(bp.read_text(encoding="utf-8"))
            ench = {int(k): v for k, v in raw["chapters"].items()}
            for g in beng.get("suktas", []):
                evs = ench.get(g["id"])
                bvs = [v for v in beng["verses"] if v["ch"] == g["id"]]
                if evs is None:
                    en_out["skipped"].append({"ch": g["id"], "why": "ইংরেজি উৎসে অধ্যায়টি মেলেনি"})
                    continue
                bnums = [v["vn"] for v in bvs]
                enums = [v["vn"] for v in evs]
                if bnums != enums:
                    skipped += 1
                    miss = sorted(set(bnums) ^ set(enums))[:6]
                    mismatch.append(
                        f"{c['bn']} অ{g['id']}: বাংলা {len(bnums)} পদ · ইংরেজি "
                        f"{len(enums)} পদ · নম্বর-অমিল {miss}")
                    en_out["skipped"].append({
                        "ch": g["id"],
                        "why": f"পদ-মিল নেই (বাংলা {len(bnums)} · ইংরেজি {len(enums)})"})
                    continue
                for v, e in zip(bvs, evs):
                    if e["en"]:
                        en_out["verses"][str(v["n"])] = e["en"]
                en_out["aligned"].append(g["id"])
                aligned += 1
        (EN / f"ch{c['id']}.json").write_text(
            json.dumps(en_out, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        joined["books"].append({"id": c["id"], "bn": c["bn"],
                                "aligned": len(en_out["aligned"]),
                                "skipped": len(en_out["skipped"])})
    joined["enVerses"] = sum(len(json.loads((EN / f"ch{b['id']}.json")
                                  .read_text(encoding="utf-8"))["verses"])
                             for b in joined["books"])
    (EN / "joined.json").write_text(
        json.dumps(joined, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    (DBG / "bible_en_mismatch.txt").write_text(
        ("=== বাংলা–ইংরেজি পদ-অমিল (ইংরেজি বাদ দেওয়া অধ্যায়) ===\n"
         + "\n".join(mismatch) + "\n=== শেষ ===\n") if mismatch
        else "সব অধ্যায়ে পদ হুবহু মিলেছে — কোনো অমিল নেই।\n",
        encoding="utf-8")
    print(f"মেলানো: অধ্যায় {aligned} · বাদ {skipped} · ইংরেজি পদ {joined['enVerses']}")
    if mismatch:
        print(f"⚠ {len(mismatch)}টি অধ্যায়ে পদ-অমিল — তালিকা _debug/bible_en_mismatch.txt")
    return 0


def cmd_verify(args):
    """মেলানো ইংরেজির স্বাস্থ্য-পরীক্ষা: যেসব লক্ষণ লাইভে দেখা গিয়েছিল।

    (ক) পদের ভেতরে টীকা/ক্রস-রেফের চিহ্ন («[12]», «⇒») — পাঠ নয়;
    (খ) পদের শুরুতে জমে থাকা সংখ্যা («2 বার্তা…») — পদ-নম্বরের অবশিষ্ট;
    (গ) পুস্তক-ভিত্তিক মিল-হার, যাতে কোন বই পিছিয়ে আছে চোখে পড়ে।
    """
    EN.mkdir(parents=True, exist_ok=True)
    rep, dirty = [], 0
    total = 0
    for fp in sorted(EN.glob("ch*.json"), key=lambda x: int(re.sub(r"\D", "", x.stem))):
        e = json.loads(fp.read_text(encoding="utf-8"))
        vs = e.get("verses") or {}
        total += len(vs)
        bad = [(k, v) for k, v in vs.items()
               if re.search(r"\[\d{1,3}\]|⇒", v)
               or re.match(r"^\d{1,3}\s+\S", v)]
        if bad:
            dirty += len(bad)
            rep.append(f"⚠ ch{fp.stem[2:]}: {len(bad)}টি পদে দূষণ — "
                       + " | ".join(f"{k}: {v[:60]}" for k, v in bad[:2]))
        rep.append(f"  · ch{fp.stem[2:]} ({e.get('id')}): মিলিত অধ্যায় "
                   f"{len(e.get('aligned') or [])} · বাদ {len(e.get('skipped') or [])} · "
                   f"ইংরেজি পদ {len(vs)}")
    txt = (f"=== ইংরেজি যাচাই ===\nইংরেজি পদ: {total} · দূষিত পদ: {dirty}\n"
           + "\n".join(rep) + "\n=== শেষ ===\n")
    (DBG / "bible_en_verify.txt").write_text(txt, encoding="utf-8")
    print(f"ইংরেজি যাচাই: পদ {total} · দূষিত {dirty}")
    return 0 if not dirty else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--join", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--delay", type=float, default=0.7)
    ap.add_argument("--budget", type=int, default=40)
    args = ap.parse_args()
    if args.fetch:
        return cmd_fetch(args)
    if args.join:
        return join_bookkeeping()
    if args.verify:
        return cmd_verify(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
