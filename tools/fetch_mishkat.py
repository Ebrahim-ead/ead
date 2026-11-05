#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""মিশকাতুল মাসাবিহ — muslimbangla.com (বই ১৩) থেকে বাংলা+আরবি হাদিস নামিয়ে
সাইটের নিজের রিডার-ফরম্যাটে ঢালার যন্ত্র।

কাঠামো (যাচাই করা, ২০২৬-১১-০৫):
    /hadith-book/13/chapters              → ৩১টি অধ্যায়ের কার্ড
    /hadith-book/13/chapter/<c>/titles    → ওই অধ্যায়ের পরিচ্ছেদ-তালিকা
    /hadith-book/13/chapter/<c>/title/<t> → এক বা একাধিক হাদিস (প্রতি হাদিস = এক কার্ড)

পাতা Next.js-এর RSC ফ্লাইট-স্ট্রিম (self.__next_f.push) — আসল ডেটা ওখানেই
JSON আকারে আছে: hadith_number, description (বাংলা), description_ar (আরবি),
type.title (মান), tahqeeq_explanation (তাহকীক), titles.title (পরিচ্ছেদ)।
DOM ঘাঁটার চেয়ে এটাই নির্ভুল, তাই এটাই ব্যবহার করা হয়।

ধাপ:
    --probe                  → কাঠামো যাচাই
    --discover               → অধ্যায় + পরিচ্ছেদের তালিকা (toc.json)
    --fetch [--chapters 498] → পরিচ্ছেদ ধরে ধরে হাদিস নামাও (ক্যাশ; পুনরায় চালালে বাকিটা)
    --build                  → assets/hadith/data/mishkat/*.json + index.json হালনাগাদ
    --verify                 → নামানো ডেটার অখণ্ডতা যাচাই

নিয়ম: শুধু muslimbangla.com; একই পাতা দুবার নামে না (ডিস্ক-ক্যাশ); ধীরে (বিরতি);
robots.txt মানা — কেবল পাবলিক পাতা, /api/ নয়।
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from json import JSONDecoder

BASE = "https://muslimbangla.com"
BOOK = 13                        # সাইটে ১৩ = মিশকাতুল মাসাবিহ
UA = "Mozilla/5.0 (compatible; ead-hadith/1.0; +https://github.com/Ebrahim-ead/ead)"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "assets", "hadith", "data")
OUT = os.path.join(DATA, "_debug", "mishkat")
RAW = os.path.join(OUT, "raw")
PARSED = os.path.join(OUT, "parsed")
SRC_URL = f"{BASE}/hadith-book/{BOOK}/chapters"

BOOK_META = {
    "slug": "mishkat",
    "ar": "مشكاة المصابيح",
    "bn": "মিশকাতুল মাসাবিহ",
    "short": "মিশকাত",
    "author": "ইমাম ওয়ালিউদ্দিন মুহাম্মদ ইবনে আব্দুল্লাহ আল-খতীব আত-তিবরিজি",
}

BN_DIGITS = "০১২৩৪৫৬৭৮৯"


# ---------------------------------------------------------------- ছোট হেল্পার
def bn2num(s):
    digits = "".join(str(BN_DIGITS.index(ch)) if ch in BN_DIGITS else ch for ch in str(s))
    digits = re.sub(r"[^\d]", "", digits)
    return int(digits) if digits else 0


def clean(s):
    if not isinstance(s, str):
        return ""
    s = s.replace("\u00a0", " ").replace("\u200f", "").replace("\u200e", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def cache_key(url):
    key = re.sub(r"[^A-Za-z0-9]+", "_", url.replace(BASE, ""))[:120]
    return os.path.join(RAW, key + ".html")


def get(url, tries=4, timeout=70, sleep=1.0, force=False):
    """একই URL দুবার নামায় না — ডিস্ক-ক্যাশ।"""
    p = cache_key(url)
    os.makedirs(RAW, exist_ok=True)
    if not force and os.path.exists(p) and os.path.getsize(p) > 2000:
        with open(p, encoding="utf-8") as f:
            return f.read(), "cache"
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "bn,ar;q=0.8,en;q=0.6",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if len(body) < 2000:
                raise ValueError(f"খুব ছোট উত্তর ({len(body)} বাইট)")
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
            time.sleep(sleep)
            return body, "net"
        except Exception as e:                       # noqa: BLE001
            last = e
            time.sleep(min(30, 3 * (i + 1)))
    raise RuntimeError(f"{url} — {tries} বারে ব্যর্থ: {last}")


# ---------------------------------------------------------------- RSC ফ্লাইট
PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
ROW_RE = re.compile(r"([0-9a-f]{1,3}):")
TEXT_RE = re.compile(r"T([0-9a-f]+),")
JSON_VAL = JSONDecoder()
REF_RE = re.compile(r"\$([0-9a-f]{1,3})\b")


def flight_payload(html):
    chunks = PUSH_RE.findall(html)
    return "".join(json.loads(c) for c in chunks)


def flight_rows(payload):
    """'id:মান' সারি — T<hex>, আকারের টেক্সট-সারি সহ (বাংলা পাঠ ওখানেই থাকে)।"""
    rows = {}
    i = 0
    while True:
        m = ROW_RE.search(payload, i)
        if not m:
            break
        s = m.end()
        tm = TEXT_RE.match(payload, s)
        if tm:
            size = int(tm.group(1), 16)
            start = tm.end()
            raw = payload[start:].encode("utf-8", "surrogatepass")[:size]
            text = raw.decode("utf-8", "replace")
            rows[m.group(1)] = text
            i = start + len(text)
            continue
        try:
            val, end = JSON_VAL.raw_decode(payload, s)
        except Exception:                            # noqa: BLE001
            i = m.start() + 1
            continue
        rows.setdefault(m.group(1), val)
        i = end
    return rows


def deref(rows, v, depth=8):
    while depth and isinstance(v, str):
        m = REF_RE.fullmatch(v.strip())
        if not m:
            break
        v = rows.get(m.group(1))
        depth -= 1
    return v


def find_hadith_array(payload):
    """RSC-র ভেতরে যেখানে {'hadiths': [...]} আছে — সেই অ্যারে খুঁজে আনি।"""
    for m in re.finditer(r'"hadiths":\s*\[', payload):
        pos = payload.rfind("[", 0, m.start())
        for _ in range(8):
            if pos < 0:
                break
            try:
                arr, _end = JSON_VAL.raw_decode(payload, pos)
            except Exception:                        # noqa: BLE001
                pos = payload.rfind("[", 0, pos)
                continue
            if isinstance(arr, list) and any(isinstance(x, dict) and x.get("hadiths")
                                             for x in arr):
                return arr
            pos = payload.rfind("[", 0, pos)
    return []


def extract(html):
    """এক পাতার সব হাদিস — [{n,bn,ar,g,tah,foot,sec,chap,sid}]"""
    payload = flight_payload(html)
    rows = flight_rows(payload)
    out = []
    for item in find_hadith_array(payload):
        if not isinstance(item, dict):
            continue
        for h in item.get("hadiths") or []:
            if not isinstance(h, dict):
                continue
            out.append({
                "n": h.get("hadith_number") or 0,
                "bn": clean(deref(rows, h.get("description"))),
                "ar": clean(deref(rows, h.get("description_ar"))),
                "g": clean((h.get("type") or {}).get("title")),
                "tah": clean(h.get("tahqeeq_explanation")),
                "foot": clean(deref(rows, h.get("foot_note"))),
                "sec": clean((h.get("titles") or {}).get("title")),
                "chap": clean((h.get("chapter") or {}).get("title")),
                "sid": h.get("id"),
            })
    return out


# ---------------------------------------------------------------- discover
def discover():
    body, how = get(SRC_URL)
    chapters = []
    for m in re.finditer(r'href="/hadith-book/%d/chapter/(\d+)/titles"' % BOOK, body):
        cid = int(m.group(1))
        if any(c["site"] == cid for c in chapters):
            continue
        seg = re.sub(r"(?is)<script.*?</script>", " ", body[m.end():m.end() + 1400])
        txt = clean(re.sub(r"<[^>]+>", " ", seg))
        head = txt.split("মোট হাদীস")[0]
        nums = re.search(r"(\d+)\s*-\s*(\d+)", txt)
        cnt = re.search(r"মোট হাদীস\s*-?\s*(\d+)", txt)
        chapters.append({
            "site": cid,
            "bn": re.sub(r"^\s*\d+\s*[-–.]\s*", "", head).strip(" •·-–"),
            "claimed": int(cnt.group(1)) if cnt else 0,
            "from": int(nums.group(1)) if nums else 0,
            "to": int(nums.group(2)) if nums else 0,
            "sections": [],
        })
    for i, c in enumerate(chapters, 1):
        c["id"] = i                              # আমাদের রিডারের অধ্যায়-আইডি
        url = f"{BASE}/hadith-book/{BOOK}/chapter/{c['site']}/titles"
        try:
            ch_body, _ = get(url)
        except Exception as e:                   # noqa: BLE001
            c["error"] = str(e)
            print(f"  ✗ অধ্যায় {c['site']}: {e}")
            continue
        secs = []
        for m in re.finditer(r'href="/hadith-book/%d/chapter/(\d+)/title/(\d+)"' % BOOK, ch_body):
            tid = int(m.group(2))
            if any(s["title"] == tid for s in secs):
                continue
            seg = re.sub(r"(?is)<script.*?</script>", " ", ch_body[m.end():m.end() + 1000])
            txt = clean(re.sub(r"<[^>]+>", " ", seg))
            cnt = re.search(r"মোট হাদীস\s*[:：]?\s*(\d+)", txt)
            nums = re.search(r"(\d+)\s*-\s*(\d+)", txt)
            secs.append({
                "title": tid,
                "bn": clean(txt.split("মোট হাদীস")[0]).strip(" •·-–"),
                "claimed": int(cnt.group(1)) if cnt else 0,
                "from": int(nums.group(1)) if nums else 0,
                "to": int(nums.group(2)) if nums else 0,
            })
        c["sections"] = secs
        print(f"  {c['id']:>2}. {c['bn'][:48]:<48} পরিচ্ছেদ {len(secs):>3} "
              f"· দাবি {sum(s['claimed'] for s in secs):>4}")
    os.makedirs(OUT, exist_ok=True)
    toc = {"book": BOOK, "source": SRC_URL, "fetched": time.strftime("%Y-%m-%d"),
           "chapters": chapters}
    with open(os.path.join(OUT, "toc.json"), "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=1)
    print(f"অধ্যায় {len(chapters)} · পরিচ্ছেদ {sum(len(c['sections']) for c in chapters)} "
          f"· দাবিকৃত হাদিস {sum(c['claimed'] for c in chapters)}")


# ---------------------------------------------------------------- fetch
def load_toc():
    p = os.path.join(OUT, "toc.json")
    if not os.path.exists(p):
        raise SystemExit("toc.json নেই — আগে --discover চালান")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def section_path(cid, tid):
    return os.path.join(PARSED, f"{cid:02d}_{tid}.json")


def fetch(chapters=None, limit=0, sleep=1.0):
    toc = load_toc()
    os.makedirs(PARSED, exist_ok=True)
    jobs = []
    for c in toc["chapters"]:
        if chapters and c["site"] not in chapters and c["id"] not in chapters:
            continue
        for s in c.get("sections", []):
            if os.path.exists(section_path(c["id"], s["title"])):
                continue
            jobs.append((c, s))
    if limit:
        jobs = jobs[:limit]
    print(f"নামাতে হবে {len(jobs)} পরিচ্ছেদ", flush=True)
    done = fail = 0
    for c, s in jobs:
        url = f"{BASE}/hadith-book/{BOOK}/chapter/{c['site']}/title/{s['title']}"
        try:
            body, how = get(url, sleep=sleep)
        except Exception as e:                   # noqa: BLE001
            fail += 1
            print(f"  ✗ {c['id']}.{s['title']} — {e}", flush=True)
            continue
        items = [x for x in extract(body)
                 if x["n"] and (x["bn"] or x["ar"])]
        with open(section_path(c["id"], s["title"]), "w", encoding="utf-8") as f:
            json.dump({"chapter": c["id"], "site_chapter": c["site"],
                       "title": s["title"], "url": url,
                       "claimed": s["claimed"], "hadiths": items},
                      f, ensure_ascii=False)
        done += 1
        flag = "" if len(items) == s["claimed"] else f"  ⚠ দাবি {s['claimed']}, পেলাম {len(items)}"
        print(f"  ✓ {c['id']:>2}.{s['title']} {len(items):>3} হাদিস ({how}){flag}", flush=True)
    print(f"শেষ: নতুন {done} · ব্যর্থ {fail}", flush=True)


# ---------------------------------------------------------------- build
def grade_class(g):
    if not g:
        return "other"
    if any(w in g for w in ("জাল", "বাতিল", "موضوع")):
        return "fake"
    if any(w in g for w in ("দুর্বল", "যঈফ", "জঈফ", "মুনকার", "মাতরুক", "শায",
                            "মুরসাল", "মুনকাতি", "মুযতারিব", "মাকতু", "মাওকুফ")):
        return "weak"
    if any(w in g for w in ("সহীহ", "সহিহ", "বিশুদ্ধ", "হাসান", "صحيح", "حسن")):
        return "ok"
    return "other"


LEAD_NUM_RE = re.compile(r"^\s*[০-৯0-9]+\s*[।.)]\s*")


def build(chapters=None):
    toc = load_toc()
    out_dir = os.path.join(DATA, BOOK_META["slug"])
    os.makedirs(out_dir, exist_ok=True)
    index_p = os.path.join(DATA, "index.json")
    with open(index_p, encoding="utf-8") as f:
        index = json.load(f)

    book = dict(BOOK_META)
    book["count"] = 0
    book["chapters"] = []
    grades = {}
    problems = []
    total = 0
    for c in toc["chapters"]:
        if chapters and c["site"] not in chapters and c["id"] not in chapters:
            continue
        verses, seen = [], {}
        for s in c.get("sections", []):
            p = section_path(c["id"], s["title"])
            if not os.path.exists(p):
                problems.append(f"অধ্যায় {c['id']} ({c['bn']}) · পরিচ্ছেদ {s['title']} নামানো হয়নি")
                continue
            with open(p, encoding="utf-8") as f:
                payload = json.load(f)
            if not payload.get("hadiths"):
                problems.append(f"অধ্যায় {c['id']} · পরিচ্ছেদ {s['title']} ফাঁকা")
            for h in payload["hadiths"]:
                n = int(h["n"])
                v = {
                    "i": n,
                    "b": LEAD_NUM_RE.sub("", h.get("bn") or ""),
                    "a": h.get("ar") or "",
                    "n": "",          # রাবির নাম বাংলা পাঠেই আছে — আলাদা করলে পাঠ বদলাত
                }
                if n in seen:
                    v["dup"] = 1                       # উৎসে একই নম্বরে দ্বিতীয় সংস্করণ
                seen[n] = seen.get(n, 0) + 1
                g = clean(h.get("g"))
                if g:
                    v["g"] = g
                    v["gc"] = grade_class(g)
                    grades[g] = grades.get(g, 0) + 1
                if h.get("sec") and h["sec"] != clean(s["bn"]):
                    v["s"] = h["sec"]                  # পরিচ্ছেদের নাম
                if h.get("tah"):
                    v["tah"] = h["tah"]                # তাহকীক (মূল সূত্রের রেফারেন্স)
                verses.append(v)
        if not verses:
            problems.append(f"অধ্যায় {c['id']}: কোনো হাদিস নেই")
            continue
        nums = [v["i"] for v in verses]
        with open(os.path.join(out_dir, f"{c['id']}.json"), "w", encoding="utf-8") as f:
            json.dump({"book": BOOK_META["slug"], "chapter": c["id"], "verses": verses},
                      f, ensure_ascii=False, separators=(",", ":"))
        book["chapters"].append({
            "id": c["id"],
            "bn": c["bn"],
            "range": f"{nums[0]} - {nums[-1]}",
            "count": len(verses),
            "from": nums[0],
            "to": nums[-1],
        })
        book["count"] += len(verses)
        total += len(verses)
        gaps = len(set(range(nums[0], nums[-1] + 1)) - set(nums))
        print(f"  {c['id']:>2}. {c['bn'][:42]:<42} {len(verses):>4} হাদিস · "
              f"{nums[0]}–{nums[-1]} · ফাঁক {gaps}", flush=True)

    if not book["count"]:
        raise SystemExit("কোনো হাদিস পাওয়া যায়নি — বিল্ড বাতিল")

    book["grades"] = dict(sorted(grades.items(), key=lambda kv: -kv[1]))
    books = [b for b in index["books"] if b["slug"] != BOOK_META["slug"]]
    books.append(book)
    index["books"] = books
    index["total"] = sum(b["count"] for b in books)
    allg = {}
    for b in books:
        for k, v in (b.get("grades") or {}).items():
            allg[k] = allg.get(k, 0) + v
    index["grades"] = dict(sorted(allg.items(), key=lambda kv: -kv[1]))
    index.setdefault("note", "সব ডেটা এই সাইটের ভেতরেই; কোনো বাইরের অনুরোধ নেই।")
    with open(index_p, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "build.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join([
            f"মিশকাত: {book['count']} হাদিস · {len(book['chapters'])} অধ্যায়",
            f"নতুন মোট: {index['total']} · কিতাব {len(books)}",
            f"উৎস: {SRC_URL}",
            f"নতুন হাদিস (এই রানে) {total}",
            "সমস্যা:" if problems else "সমস্যা নেই",
            *problems,
        ]) + "\n")
    print(f"\nমিশকাত: {book['count']} হাদিস · {len(book['chapters'])} অধ্যায়")
    print(f"নতুন মোট: {index['total']} · কিতাব {len(books)}")
    if problems:
        print(f"⚠ সমস্যা {len(problems)}টি:")
        for p in problems[:20]:
            print("   - " + p)


# ---------------------------------------------------------------- verify
def verify():
    idx = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
    book = next((b for b in idx["books"] if b["slug"] == BOOK_META["slug"]), None)
    if not book:
        raise SystemExit("index-এ মিশকাত নেই")
    out = [f"index: {book['bn']} · {book['count']} হাদিস · {len(book['chapters'])} অধ্যায় "
           f"· সাইটে মোট {idx['total']} · কিতাব {len(idx['books'])}"]
    bad = total = 0
    for c in book["chapters"]:
        p = os.path.join(DATA, BOOK_META["slug"], f"{c['id']}.json")
        d = json.load(open(p, encoding="utf-8"))
        vs = d["verses"]
        total += len(vs)
        no_bn = sum(1 for v in vs if not v.get("b"))
        no_ar = sum(1 for v in vs if not v.get("a"))
        dup = sum(1 for v in vs if v.get("dup"))
        nums = [v["i"] for v in vs]
        gaps = len(set(range(min(nums), max(nums) + 1)) - set(nums)) if nums else 0
        if len(vs) != c["count"] or no_bn or no_ar:
            bad += 1
        out.append(f"  {c['id']:>2}. {len(vs):>4} (index {c['count']:>4}) · বাংলা-হীন {no_bn} "
                   f"· আরবি-হীন {no_ar} · পুনরাবৃত্তি {dup} · ফাঁক {gaps} · {nums[0]}–{nums[-1]}")
    out.insert(1, f"ফাইল-যোগফল {total} · অসঙ্গত অধ্যায় {bad}")
    txt = "\n".join(out)
    print(txt)
    with open(os.path.join(OUT, "verify.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")


# ---------------------------------------------------------------- probe
def probe():
    os.makedirs(OUT, exist_ok=True)
    pages = {
        "chapters": SRC_URL,
        "sections_498": f"{BASE}/hadith-book/{BOOK}/chapter/498/titles",
        "title_12308": f"{BASE}/hadith-book/{BOOK}/chapter/498/title/12308",
        "title_12306": f"{BASE}/hadith-book/{BOOK}/chapter/499/title/12306",
    }
    log = []
    for name, url in pages.items():
        body, how = get(url)
        log.append(f"### {name} ({how}) — {len(body):,} বাইট")
        if name.startswith("title_"):
            rows = extract(body)
            log.append(f"   হাদিস {len(rows)} · নম্বর {[r['n'] for r in rows][:12]}")
            for r in rows[:2]:
                log.append(f"   {r['n']} · মান={r['g']} · পরিচ্ছেদ={r['sec']} · "
                           f"তাহকীক={r['tah'][:40]!r}")
                log.append(f"      বাংলা({len(r['bn'])}): {r['bn'][:100]}")
                log.append(f"      আরবি({len(r['ar'])}): {r['ar'][:80]}")
    txt = "\n".join(log)
    print(txt)
    with open(os.path.join(OUT, "probe.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")


def main():
    ap = argparse.ArgumentParser()
    for flag in ("probe", "discover", "fetch", "build", "verify"):
        ap.add_argument("--" + flag, action="store_true")
    ap.add_argument("--chapters", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()
    ch = [int(x) for x in re.findall(r"\d+", a.chapters)] if a.chapters else None
    if a.probe:
        probe()
    elif a.discover:
        discover()
    elif a.fetch:
        fetch(ch, a.limit, a.sleep)
    elif a.build:
        build(ch)
    elif a.verify:
        verify()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
