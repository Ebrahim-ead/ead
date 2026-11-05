#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""মিশকাত — তালিকায় না-থাকা হাদিসগুলো আলাদা পাতায় পূরণ + নম্বর-ক্রমে সাজানো।

কেন: muslimbangla-র অধ্যায়/পরিচ্ছেদ-তালিকায় মিশকাতের ১,৩৫১টি নম্বর লিংক করা নেই,
কিন্তু প্রতিটি হাদিসের নিজের পাতা আছে:
    https://muslimbangla.com/hadith/<page>   (page = 34945 + হাদিস নম্বর)
যেমন «হাদীস নং ৩» → /hadith/34948, «হাদীস নং ৫৮৮» → /hadith/35533 (যাচাই করা)।

ধাপ:
    --plan                 → কোন নম্বরগুলো নেই, তার তালিকা
    --fill [--limit N]     → ফাঁকা নম্বরগুলোর পাতায় গিয়ে হাদিস নামাও (ক্যাশ, পুনরায় চালালে বাকিটা)
    --build                → ফাঁকা-হাদিস জুড়ে প্রতিটি অধ্যায় নম্বর-ক্রমে সাজিয়ে index হালনাগাদ
    --verify               → ক্রম ও সংখ্যা যাচাই

নিরাপত্তা: প্রতি পাতায় যাচাই হয় শিরোনামে «মিশকাতুল মাসাবীহ» আছে কি না এবং
«হাদীস নং: <n>» মিলছে কি না; না মিললে কিছুই লেখা হয় না।
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_mishkat as F                            # noqa: E402

PAGE0 = 34945          # sid = হাদিস নম্বর + 34945  (যাচাই করা)
FILLED = os.path.join(F.OUT, "filled")


# ---------------------------------------------------------------- plan
def missing_numbers():
    idx = json.load(open(os.path.join(F.DATA, "index.json"), encoding="utf-8"))
    book = next(b for b in idx["books"] if b["slug"] == F.BOOK_META["slug"])
    have = set()
    for c in book["chapters"]:
        p = os.path.join(F.DATA, F.BOOK_META["slug"], f"{c['id']}.json")
        for v in json.load(open(p, encoding="utf-8"))["verses"]:
            have.add(v["i"])
    plan = []
    for c in book["chapters"]:
        for n in range(c["from"], c["to"] + 1):
            if n not in have:
                plan.append({"n": n, "chapter": c["id"], "bn": c["bn"]})
    return plan


# ---------------------------------------------------------------- এক পাতার হাদিস
TITLE_RE = re.compile(r"হাদীস নং\s*[:：]?\s*([০-৯0-9]+)")
CHAP_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)


def parse_hadith_page(html, expect_n):
    """একক হাদিস-পাতা → dict | None (যাচাই ফেল হলে None)"""
    text = F.clean(re.sub(r"<[^>]+>", " ", html))
    if "মিশকাতুল মাসাবীহ" not in text and "مشكاة المصابيح" not in html:
        return None
    m = TITLE_RE.search(text) or TITLE_RE.search(html)
    if not m or F.bn2num(m.group(1)) != expect_n:
        return None
    chap = ""
    cm = CHAP_RE.search(html)
    if cm:
        chap = F.name_only(F.clean(re.sub(r"<[^>]+>", " ", cm.group(1))))
    items = F.extract(html)                 # RSC-পথ (বাংলা+আরবি+মান+তাহকীক)
    if items:
        h = items[0]
        h["chap"] = chap or h.get("chap", "")
        return h
    return None


def fill(limit=0, sleep=1.0):
    plan = missing_numbers()
    os.makedirs(FILLED, exist_ok=True)
    todo = [p for p in plan if not os.path.exists(os.path.join(FILLED, f"{p['n']}.json"))]
    if limit:
        todo = todo[:limit]
    print(f"ফাঁকা {len(plan)} · এবার নামাবে {len(todo)}", flush=True)
    ok = bad = 0
    for p in todo:
        url = f"{F.BASE}/hadith/{PAGE0 + p['n']}"
        try:
            html, how = F.get(url, sleep=sleep, tries=2)
        except Exception as e:                       # noqa: BLE001
            bad += 1
            print(f"  ✗ {p['n']} — {e}", flush=True)
            continue
        h = parse_hadith_page(html, p["n"])
        if not h:
            bad += 1
            print(f"  ✗ {p['n']} — পাতা মিলল না ({url})", flush=True)
            continue
        h["n"] = p["n"]
        h["chapter"] = p["chapter"]
        h["chap"] = h.get("chap") or p["bn"]
        with open(os.path.join(FILLED, f"{p['n']}.json"), "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False)
        ok += 1
        print(f"  ✓ {p['n']:>4} {str(h.get('sec',''))[:34]:<34} {str(h.get('bn',''))[:40]}",
              flush=True)
    print(f"শেষ: পেলাম {ok} · ব্যর্থ {bad}", flush=True)


# ---------------------------------------------------------------- build
LEAD_NUM = re.compile(r"^\s*[০-৯0-9]+\s*[।.)]\s*")


def build():
    os.makedirs(F.OUT, exist_ok=True)
    idx_p = os.path.join(F.DATA, "index.json")
    idx = json.load(open(idx_p, encoding="utf-8"))
    book = next(b for b in idx["books"] if b["slug"] == F.BOOK_META["slug"])

    # ১) ফাঁকা-হাদিসগুলো অধ্যায় ধরে জড়ো করি
    added = 0
    per_ch = {c["id"]: [] for c in book["chapters"]}
    if os.path.isdir(FILLED):
        for fn in os.listdir(FILLED):
            if not fn.endswith(".json"):
                continue
            h = json.load(open(os.path.join(FILLED, fn), encoding="utf-8"))
            if h.get("chapter") in per_ch:
                per_ch[h["chapter"]].append(h)
                added += 1
    print(f"ফাঁকা থেকে যোগ হচ্ছে {added} হাদিস")

    grades = {}
    for c in book["chapters"]:
        p = os.path.join(F.DATA, F.BOOK_META["slug"], f"{c['id']}.json")
        d = json.load(open(p, encoding="utf-8"))
        verses = list(d["verses"])
        have = {v["i"] for v in verses}
        for h in per_ch.get(c["id"], []):
            if h["n"] in have:
                continue
            v = {"i": int(h["n"]), "b": LEAD_NUM.sub("", h.get("bn") or ""),
                 "a": h.get("ar") or "", "n": ""}
            if h.get("sec"):
                v["s"] = F.clean(h["sec"])
            if h.get("g"):
                v["g"] = F.clean(h["g"])
                v["gc"] = F.grade_class(v["g"])
            if h.get("tah"):
                v["tah"] = F.clean(h["tah"])
            verses.append(v)
        # ২) নম্বর-ক্রমে সাজাও — «২-এর পর ১৯» ভুলটা এখানেই ঠিক হয়
        verses.sort(key=lambda v: v["i"])
        for v in verses:
            if v.get("g"):
                grades[v["g"]] = grades.get(v["g"], 0) + 1
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"book": F.BOOK_META["slug"], "chapter": c["id"], "verses": verses},
                      f, ensure_ascii=False, separators=(",", ":"))
        nums = [v["i"] for v in verses]
        c["count"] = len(verses)
        c["from"], c["to"] = min(nums), max(nums)
        c["range"] = f"{c['from']} - {c['to']}"

    book["count"] = sum(c["count"] for c in book["chapters"])
    book["grades"] = dict(sorted(grades.items(), key=lambda kv: -kv[1]))
    idx["total"] = sum(b["count"] for b in idx["books"])
    allg = {}
    for b in idx["books"]:
        for k, v in (b.get("grades") or {}).items():
            allg[k] = allg.get(k, 0) + v
    idx["grades"] = dict(sorted(allg.items(), key=lambda kv: -kv[1]))
    json.dump(idx, open(idx_p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    left = len(missing_numbers())
    print(f"মিশকাত: {book['count']} হাদিস · {len(book['chapters'])} অধ্যায় · "
          f"সাইটে মোট {idx['total']} · তবুও ফাঁকা {left}")
    with open(os.path.join(F.OUT, "fill_build.txt"), "w", encoding="utf-8") as f:
        f.write(f"যোগ {added} · মিশকাত {book['count']} · মোট {idx['total']} · ফাঁকা {left}\n")


def verify():
    os.makedirs(F.OUT, exist_ok=True)
    idx = json.load(open(os.path.join(F.DATA, "index.json"), encoding="utf-8"))
    book = next(b for b in idx["books"] if b["slug"] == F.BOOK_META["slug"])
    bad = 0
    out = []
    for c in book["chapters"]:
        d = json.load(open(os.path.join(F.DATA, F.BOOK_META["slug"], f"{c['id']}.json"),
                           encoding="utf-8"))
        ns = [v["i"] for v in d["verses"]]
        disorder = sum(1 for a, b in zip(ns, ns[1:]) if b <= a)
        gap = len(set(range(ns[0], ns[-1] + 1)) - set(ns))
        if disorder:
            bad += 1
        out.append(f"  {c['id']:>2}. {len(ns):>4} · {ns[0]}–{ns[-1]} · "
                   f"ক্রম-ভাঙা {disorder} · ফাঁক {gap}")
    txt = "\n".join([f"মিশকাত {book['count']} · অধ্যায় {len(book['chapters'])} · "
                     f"ক্রম-ভাঙা অধ্যায় {bad} · সাইটে মোট {idx['total']}", *out])
    print(txt)
    with open(os.path.join(F.OUT, "verify2.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")


def main():
    ap = argparse.ArgumentParser()
    for flag in ("plan", "fill", "build", "verify"):
        ap.add_argument("--" + flag, action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.2)
    a = ap.parse_args()
    if a.plan:
        plan = missing_numbers()
        print(f"ফাঁকা {len(plan)}")
        print([p["n"] for p in plan[:40]])
    elif a.fill:
        fill(a.limit, a.sleep)
    elif a.build:
        build()
    elif a.verify:
        verify()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
