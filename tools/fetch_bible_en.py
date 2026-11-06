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
PV_EN = 1                                    # ইংরেজি পার্সারের সংস্করণ

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
        NAB_ID["song of solomon"] = _i
    if _n == "Acts of the Apostles":
        NAB_ID["acts"] = _i
    if _n == "Psalms":
        NAB_ID["psalm"] = _i

NAV_SKIP = re.compile(
    r"^(new american bible|intratext.*|\d{4}\s*\d{2}\s*\d{2}|help|previous|next|"
    r"click here.*|table of contents|statistics.*|back|up)$", re.I)
CHAPTER_LINE = re.compile(r"^chapter\s+(\d+)$", re.I)
INTRO_LINE = re.compile(r"^introduction$", re.I)
NUM_LINE = re.compile(r"^(\d{1,3})$")
FOOT_MARK = re.compile(r"^\[\d+\]\s*")


def tok_next(tok: str) -> str:
    """base36-এ পরের পাতা-কোড: 9→A, Z→10, 1Z→20 …"""
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
    """পাতার নিজের পরিচয়: (পুস্তক-নাম, অধ্যায়-নম্বর) বা (নাম, None) ভূমিকা হলে।"""
    book, ch, intro = None, None, False
    for ln in lines:
        if CHAPTER_LINE.match(ln):
            ch = int(CHAPTER_LINE.match(ln).group(1))
            break
        if INTRO_LINE.match(ln):
            intro = True
            break
    if ch is None and not intro:
        return None, None
    for ln in lines:
        if NAV_SKIP.match(ln) or NUM_LINE.match(ln) or not ln:
            continue
        if CHAPTER_LINE.match(ln) or INTRO_LINE.match(ln):
            continue
        if ln.lower().startswith("the pentateuch") or ln.lower() in (
                "old testament", "new testament"):
            continue
        book = ln
        break
    return book, ch


def parse_en_verses(lines):
    """পদ-তালিকা: নম্বর-লাইন + পরের পাঠ। টীকা-অংশ কাটা হয় «নম্বর কমলে»।

    IntraText-এ পদ-নম্বর আলাদা লাইনে; যাদের টীকা আছে তাদের পাঠের শুরুতে
    «[n]» চিহ্ন; শেষে টীকা-তালিকা, যার নম্বরগুলো আবার ছোট থেকে শুরু —
    «নম্বর ≥ প্রত্যাশিত» নিয়মে তাই টীকা আপনা থেকেই বাদ পড়ে।
    """
    verses, expect = [], 1
    for raw in lines:
        ln = FOOT_MARK.sub("", raw.strip())
        if not ln or NAV_SKIP.match(ln):
            continue
        m = NUM_LINE.match(ln)
        if m:
            num = int(m.group(1))
            if num < expect:          # টীকা-অংশ শুরু
                break
            if num > expect:          # মাঝের পদ উৎসে নেই — অনুমান করি না
                for miss in range(expect, num):
                    verses.append({"vn": miss, "en": "", "srcEmpty": True})
            verses.append({"vn": num, "en": ""})
            expect = num + 1
            continue
        if verses and not verses[-1]["en"]:
            verses[-1]["en"] = ln
        elif verses:
            verses[-1]["en"] += " " + ln
    for v in verses:
        if not v["en"].strip():
            v["srcEmpty"] = True     # নম্বর ছাপা, পাঠ উৎসেই নেই
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
    tok = prog.get("token", "P3")
    pend_name = prog.get("pendName")
    pend = {int(k): v for k, v in (prog.get("pendCh") or {}).items()}
    t0 = time.time()
    misses = 0
    pages = saved = 0
    report = []
    while misses < 3:
        url = BASE + "__" + tok + ".HTM"
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
                "when": int(time.time())}
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
    if misses >= 3:   # কর্পাসের শেষ পর্যন্ত হাঁটা হয়েছে — পরের রানে নেটওয়ার্ক লাগবে না
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
    obj = {"book": book["i"], "bn": book["bn"], "enName": name, "pvEn": PV_EN,
           "chapters": {str(k): v for k, v in sorted(chapters.items())}}
    (RAW / f"raw{book['i']}.json").write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    report.append(f"  ✓ {book['i']:>2}. {book['bn']} ← {name}: অধ্যায় {len(chapters)}")
    return 1


def cmd_join(args):
    """বাংলা পদের সঙ্গে ইংরেজি মেলানো — কেবল হুবহু মিললে।"""
    if not (OUT / "index.json").exists():
        print("⛔ বাংলা ডেটা নেই")
        return 2
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--join", action="store_true")
    ap.add_argument("--delay", type=float, default=0.7)
    ap.add_argument("--budget", type=int, default=40)
    args = ap.parse_args()
    if args.fetch:
        return cmd_fetch(args)
    if args.join:
        return cmd_join(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
