#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""মিশকাতের ফাঁকা হাদিস পূরণ + প্রতিটি অধ্যায়ে নম্বর-ক্রম ঠিক করা।

সমস্যা (যাচাই করা):
  ১. অধ্যায়ের ভেতরে হাদিস নম্বর-ক্রমে নেই (অধ্যায় ২-এ ৪৪-এর পরে ৩২ …),
     কারণ উৎসের পরিচ্ছেদ-পাতাগুলো আলাদা আলাদা নামানো হয়েছিল।
  ২. তালিকায় যেসব নম্বরের লিংকই নেই (১,৩৫১টি — যেমন ৩, ৪, ৫৮৮) সেগুলো বাদ পড়েছে।
     কিন্তু প্রতিটির নিজস্ব পাতা আছে: https://muslimbangla.com/hadith/<34945+n>
     (যাচাই: 2→34947, 3→34948, 4→34949, 588→35533)

কী করে:
  --plan      কোন নম্বরগুলো নেই, অধ্যায়ভিত্তিক রিপোর্ট
  --fill      ফাঁকা নম্বরগুলোর পাতা নামায় (ডিস্ক-ক্যাশ; পুনরায় চালালে কেবল বাকিটা)
              এবং যাচাই করে: শিরোনামে «মিশকাতুল মাসাবীহ» + «হাদীস নং: n» মিলছে কি না
  --build     data/mishkat/*.json নম্বর-ক্রমে সাজায়, ফাঁকা নম্বর জুড়ে দেয়,
              index.json-এর count/range/from/to/grades/total হালনাগাদ করে
  --verify    ক্রম-ভাঙা, ফাঁক, ডুপ্লিকেট গোনে

নীতি: ডেটা কেবল muslimbangla.com থেকে; কোনো অনুমান-পাঠ নয়। যে নম্বরের পাতা
না মিলে বা যাচাইয়ে ব্যর্থ হয়, সেটি বাদ যায় ও রিপোর্টে ওঠে।

চালানো:
    python3 tools/fill_mishkat.py --plan
    python3 tools/fill_mishkat.py --fill [--limit 200] [--sleep 0.8]
    python3 tools/fill_mishkat.py --build && python3 tools/fill_mishkat.py --verify
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from json import JSONDecoder

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "assets", "hadith", "data")
BOOKDIR = os.path.join(DATA, "mishkat")
INDEX = os.path.join(DATA, "index.json")

BASE = "https://muslimbangla.com"
PAGE0 = 34945                        # /hadith/(PAGE0 + n)
UA = "Mozilla/5.0 (compatible; ead-hadith/1.0; +https://github.com/Ebrahim-ead/ead)"
CACHE = os.path.join(DATA, "_debug", "mishkat", "filled")
RAW = os.path.join(DATA, "_debug", "mishkat", "rawfill")

BN = "০১২৩৪৫৬৭৮৯"
HADITH_NO_RE = re.compile(r"হাদীস\s*নং")
ZERO_W = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
TITLE_RE = re.compile(r"মিশকাতুল\s*মাসাব")        # «মিশকাতুল মাসাবীহ» (ZWNJ-সহও)


def norm(s: str) -> str:
    return ZERO_W.sub("", s)


# ------------------------------------------------------------------ helpers
def bn2num(s) -> int:
    s = "".join(str(BN.index(c)) if c in BN else c for c in str(s))
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else 0


def clean(s) -> str:
    if not isinstance(s, str):
        return ""
    s = s.replace("\u00a0", " ").replace("\u200f", "").replace("\u200e", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def chapters() -> list[int]:
    return sorted(int(p[:-5]) for p in os.listdir(BOOKDIR)
                  if p.endswith(".json") and p[:-5].isdigit())


def load(ch: int) -> dict:
    with open(os.path.join(BOOKDIR, f"{ch}.json"), encoding="utf-8") as f:
        return json.load(f)


def save(ch: int, d: dict) -> None:
    with open(os.path.join(BOOKDIR, f"{ch}.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))


def gaps_of(nums: list[int]) -> list[tuple[int, int]]:
    have, out, cur = set(nums), [], None
    for n in range(min(nums), max(nums) + 1):
        if n in have:
            if cur:
                out.append((cur[0], cur[1]))
                cur = None
        else:
            cur = (cur[0], n) if cur else (n, n)
    if cur:
        out.append((cur[0], cur[1]))
    return out


def missing_numbers() -> dict[int, list[tuple[int, int]]]:
    """অধ্যায় → [(শুরু, শেষ)] ফাঁকা নম্বরের ব্যাপ্তি।"""
    out = {}
    for ch in chapters():
        g = gaps_of([v["i"] for v in load(ch)["verses"]])
        if g:
            out[ch] = g
    return out


# ------------------------------------------------------------------ network
def cache_path(n: int) -> str:
    return os.path.join(CACHE, f"{n}.json")


def get(url: str, tries: int = 4, timeout: int = 70, sleep: float = 1.0) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", url.replace(BASE, ""))[:120]
    raw = os.path.join(RAW, key + ".html")
    os.makedirs(RAW, exist_ok=True)
    if os.path.exists(raw) and os.path.getsize(raw) > 2000:
        return open(raw, encoding="utf-8").read()
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
            open(raw, "w", encoding="utf-8").write(body)
            time.sleep(sleep)
            return body
        except Exception as e:                       # noqa: BLE001
            last = e
            time.sleep(min(25, 3 * (i + 1)))
    raise RuntimeError(f"{url} — {tries} বারে ব্যর্থ: {last}")


# --------------------------------------------- RSC ফ্লাইট-স্ট্রিম (উৎসের ভেতরের ডেটা)
PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
ROW_RE = re.compile(r"([0-9a-f]{1,3}):")
TEXT_RE = re.compile(r"T([0-9a-f]+),")
JSON_VAL = JSONDecoder()
REF_RE = re.compile(r"\$([0-9a-f]{1,3})\b")


def flight_payload(html: str) -> str:
    return "".join(json.loads(c) for c in PUSH_RE.findall(html))


def flight_rows(payload: str) -> dict:
    rows, i = {}, 0
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


def deref(rows: dict, v, depth: int = 8):
    while depth and isinstance(v, str):
        m = REF_RE.fullmatch(v.strip())
        if not m:
            break
        v = rows.get(m.group(1))
        depth -= 1
    return v


def find_hadith_items(payload: str) -> list[dict]:
    for m in re.finditer(r'"hadiths":\s*\[', payload):
        pos = payload.rfind("[", 0, m.start())
        for _ in range(8):
            if pos < 0:
                break
            try:
                arr, _ = JSON_VAL.raw_decode(payload, pos)
            except Exception:                        # noqa: BLE001
                pos = payload.rfind("[", 0, pos)
                continue
            if isinstance(arr, list):
                out = [x for item in arr if isinstance(item, dict)
                       for x in (item.get("hadiths") or []) if isinstance(x, dict)]
                if out:
                    return out
            pos = payload.rfind("[", 0, pos)
    return []


GRADE_CLASS = (
    (("জাল", "বাতিল", "موضوع"), "fake"),
    (("দুর্বল", "যঈফ", "জঈফ", "মুনকার", "মাতরুক", "শায", "মুরসাল", "মুনকাতি",
      "মুযতারিব", "মাকতু", "মাওকুফ"), "weak"),
    (("সহীহ", "সহিহ", "বিশুদ্ধ", "হাসান", "صحيح", "حسن"), "ok"),
)


def grade_class(g: str) -> str:
    for words, cls in GRADE_CLASS:
        if any(w in g for w in words):
            return cls
    return "other"


LEAD_NUM_RE = re.compile(r"^\s*[০-৯0-9]+\s*[।.)]\s*")


def parse_hadith_page(html: str, n: int) -> dict | None:
    """এক পাতার একক হাদিস → রিডার-ফরম্যাট; যাচাই ব্যর্থ হলে None।"""
    if not TITLE_RE.search(norm(html)):
        return None
    payload = flight_payload(html)
    rows = flight_rows(payload)
    items = find_hadith_items(payload)
    item = None
    for h in items:
        num = h.get("hadith_number")
        if num is None or num == "":
            continue
        if bn2num(num) == n:
            item = h
            break
    if item is None:
        # শিরোনামের «হাদীস নং: n» দিয়েও যাচাই (কিছু পাতায় hadith_number খালি)
        if f"হাদীস নং: {n}" not in html and f"হাদীস নং:{n}" not in html:
            return None
        if len(items) != 1:
            return None
        item = items[0]
    bn = clean(deref(rows, item.get("description")))
    ar = clean(deref(rows, item.get("description_ar")))
    if not (bn or ar):
        return None
    v = {"i": n, "b": LEAD_NUM_RE.sub("", bn), "a": ar, "n": ""}
    g = clean((item.get("type") or {}).get("title"))
    if g:
        v["g"] = g
        v["gc"] = grade_class(g)
    sec = clean((item.get("titles") or {}).get("title"))
    if sec:
        v["s"] = sec
    tah = clean(item.get("tahqeeq_explanation"))
    if tah:
        v["tah"] = tah
    return v


def probe(sample=None) -> str:
    """কয়েকটি পাতা নামিয়ে পার্সার কেন চিনছে/চিনছে না — বিস্তারিত রিপোর্ট।

    Actions-এ চালিয়ে _debug/mishkat/fill_probe.txt পড়া যায়।
    """
    gaps = missing_numbers()
    picks = list(sample or [])
    for ch, g in gaps.items():
        for a, b in g:
            for n in range(a, min(b, a + 1) + 1):
                if n not in picks:
                    picks.append(n)
        if len(picks) >= 6:
            break
    picks = picks[:6]
    lines = [f"probe: {len(picks)} পাতা · {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}"]
    for n in picks:
        url = f"{BASE}/hadith/{PAGE0 + n}"
        try:
            html = get(url, sleep=0.3)
        except Exception as e:                       # noqa: BLE001
            lines.append(f"\n[{n}] ✗ নামানো যায়নি: {e}")
            continue
        payload = flight_payload(html)
        items = find_hadith_items(payload)
        rows = flight_rows(payload)
        nums = [str(h.get("hadith_number")) for h in items[:6]]
        lines.append(f"\n[{n}] url={url}")
        lines.append(f"  html {len(html)}B · flight {len(payload)}B · rows {len(rows)}")
        has_num_label = bool(HADITH_NO_RE.search(norm(html)))
        lines.append("  শিরোনাম-মিল: %s · «হাদীস নং» আছে: %s"
                     % (bool(TITLE_RE.search(norm(html))), has_num_label))
        lines.append(f"  hadiths-অ্যারে: {len(items)} · hadith_number: {nums}")
        m = re.search(r'"hadith_number"\s*:\s*[^,}]+', payload)
        lines.append(f"  নমুনা: {m.group(0)[:60] if m else '(নেই)'}")
        for key in ("description", "description_ar", "type", "titles", "tahqeeq_explanation"):
            m2 = re.search(r'"%s"\s*:\s*.{0,50}' % key, payload)
            lines.append(f"  {key}: {(m2.group(0)[:60] if m2 else '(নেই)')}")
        v = parse_hadith_page(html, n)
        lines.append(f"  parse → {'✓ বাংলা ' + str(len(v['b'])) + 'B' if v else '✗ None'}")
    report = "\n".join(lines)
    os.makedirs(CACHE, exist_ok=True)
    open(os.path.join(os.path.dirname(CACHE), "fill_probe.txt"), "w",
         encoding="utf-8").write(report + "\n")
    print(report, flush=True)
    return report


def fill(limit: int = 0, sleep: float = 0.8) -> None:
    os.makedirs(CACHE, exist_ok=True)
    todo = []
    for ch, gaps in missing_numbers().items():
        for a, b in gaps:
            for n in range(a, b + 1):
                if not os.path.exists(cache_path(n)):
                    todo.append((ch, n))
    if limit:
        todo = todo[:limit]
    print(f"নামাতে হবে {len(todo)} হাদিস-পাতা (ক্যাশে আছে {len(os.listdir(CACHE))})", flush=True)
    ok = bad = 0
    for i, (ch, n) in enumerate(todo, 1):
        url = f"{BASE}/hadith/{PAGE0 + n}"
        try:
            v = parse_hadith_page(get(url, sleep=sleep), n)
        except Exception as e:                       # noqa: BLE001
            v = None
            print(f"  ✗ {n} ({ch}) {e}", flush=True)
        if not v:
            bad += 1
            print(f"  ⚠ {n} ({ch}) যাচাইয়ে ব্যর্থ — বাদ", flush=True)
            continue
        json.dump(v, open(cache_path(n), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        ok += 1
        if i % 25 == 0 or i < 4:
            print(f"  ✓ {i}/{len(todo)} · শেষ {n} · বাংলা {len(v['b'])} অক্ষর", flush=True)
    print(f"শেষ: নামানো {ok} · ব্যর্থ {bad}", flush=True)


# ------------------------------------------------------------------ build
def build(dry: bool = False) -> None:
    index = json.load(open(INDEX, encoding="utf-8"))
    book = next(b for b in index["books"] if b["slug"] == "mishkat")
    total_added = 0
    for ch in chapters():
        d = load(ch)
        verses = {v["i"]: v for v in d["verses"]}
        added = 0
        for a, b in gaps_of(sorted(verses)):
            for n in range(a, b + 1):
                p = cache_path(n)
                if not os.path.exists(p):
                    continue
                v = json.load(open(p, encoding="utf-8"))
                if v.get("i") != n:
                    continue
                verses[n] = v
                added += 1
        # পুরো অধ্যায় নম্বর-ক্রমে (উৎসের একই নম্বরের দ্বিতীয় সংস্করণ শেষে থাকে)
        ordered = sorted(verses.values(), key=lambda v: v["i"])
        seen = {}
        for v in ordered:
            seen[v["i"]] = seen.get(v["i"], 0) + 1
            if seen[v["i"]] > 1:
                v["dup"] = 1
            else:
                v.pop("dup", None)
        d["verses"] = ordered
        if not dry:
            save(ch, d)            # ক্রম ঠিক করাটাও এখানেই লেখা হয় (নতুন হাদিস না থাকলেও)
        total_added += added
        print(f"  {ch:>2}. {len(ordered):>4} হাদিস · +{added:>3} · "
              f"{ordered[0]['i']}–{ordered[-1]['i']}", flush=True)

    count, grades = 0, {}
    for ch in chapters():
        vs = load(ch)["verses"]
        count += len(vs)
        nums = [v["i"] for v in vs]
        meta = next((c for c in book["chapters"] if c["id"] == ch), None)
        if meta is not None:
            meta["count"] = len(vs)
            meta["from"], meta["to"] = min(nums), max(nums)
            meta["range"] = f"{min(nums)} - {max(nums)}"
        for v in vs:
            if v.get("g"):
                grades[v["g"]] = grades.get(v["g"], 0) + 1
    book["count"] = count
    book["grades"] = dict(sorted(grades.items(), key=lambda kv: -kv[1]))
    index["total"] = sum(b["count"] for b in index["books"])
    allg = {}
    for b in index["books"]:
        for k, v in (b.get("grades") or {}).items():
            allg[k] = allg.get(k, 0) + v
    index["grades"] = dict(sorted(allg.items(), key=lambda kv: -kv[1]))
    if not dry:
        json.dump(index, open(INDEX, "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
    print(f"\nমিশকাত: {book['count']} হাদিস (নতুন {total_added}) · "
          f"সাইটে মোট {index['total']}")


# ------------------------------------------------------------------ report
def plan() -> None:
    gaps = missing_numbers()
    tot = sum(b - a + 1 for g in gaps.values() for a, b in g)
    print(f"ফাঁকা {tot}টি নম্বর, {len(gaps)}টি অধ্যায়ে")
    for ch, g in gaps.items():
        n = sum(b - a + 1 for a, b in g)
        head = ", ".join(f"{a}–{b}" if a != b else str(a) for a, b in g[:4])
        print(f"  অধ্যায় {ch:>2}: {n:>4} ফাঁকা · {head}{' …' if len(g) > 4 else ''}")


def verify() -> None:
    bad = 0
    for ch in chapters():
        nums = [v["i"] for v in load(ch)["verses"]]
        if nums != sorted(nums):
            bad += 1
            print(f"  ⚠ অধ্যায় {ch}: ক্রম ভাঙা")
    gaps = missing_numbers()
    left = sum(b - a + 1 for g in gaps.values() for a, b in g)
    total = sum(len(load(ch)["verses"]) for ch in chapters())
    print(f"ক্রম-ভাঙা অধ্যায়: {bad} · ফাঁকা নম্বর: {left} · মোট হাদিস: {total}")


def repair() -> None:
    """শুধু ক্রম ঠিক করে (কোনো নেটওয়ার্ক ছাড়া) — --build-এর হালকা রূপ।"""
    fixed = 0
    for ch in chapters():
        d = load(ch)
        nums = [v["i"] for v in d["verses"]]
        if nums != sorted(nums):
            d["verses"] = sorted(d["verses"], key=lambda v: v["i"])
            save(ch, d)
            fixed += 1
    print(f"ক্রম ঠিক করা অধ্যায়: {fixed}")


def main() -> int:
    ap = argparse.ArgumentParser()
    for f in ("plan", "fill", "build", "verify", "repair", "probe"):
        ap.add_argument("--" + f, action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.probe:
        probe()
    if a.plan:
        plan()
    if a.repair:
        repair()
    if a.fill:
        fill(limit=a.limit, sleep=a.sleep)
    if a.build:
        build(dry=a.dry_run)
    if a.verify:
        verify()
    if not any((a.plan, a.fill, a.build, a.verify, a.repair, a.probe)):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
