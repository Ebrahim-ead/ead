#!/usr/bin/env python3
"""বাংলা বাইবেল (ebanglalibrary.com) → assets/grantho/data/bible/

কেন আলাদা যন্ত্র (fetch_ebl.py-এর বদলে):
  উৎসের গঠন বেদের মতো নয়। এখানে বই-পাতার ভেতরে ৬৬টি পুস্তক (lessons),
  আর প্রতিটি পুস্তকের অধ্যায়গুলো আলাদা topics পাতায়। বেদের ক্ষেত্রে একটি
  লেসন = একটি অধ্যায় ছিল; এখানে একটি টপিক = বাইবেলের একটি অধ্যায়।

ডেটা-কাঠামো (ব্যবহারকারীর সিদ্ধান্ত ২০২১-১১-০৬: শুধু বাংলা, ইংরেজি নয়):
  এক স্লাগ `bible`; index.json-এর ৬৬টি অধ্যায় = ৬৬টি পুস্তক।
  প্রতিটি পুস্তকে বাইবেলের অধ্যায়গুলো ঋগ্বেদের `suktas`-এর মতো গ্রুপ,
  আর পদগুলোতে দুটি নম্বর:
    n  — পুস্তকের ভেতরে অনন্য ক্রম (১..N) — অ্যাংকর/গ্রুপ-সীমার জন্য
    vn — বাইবেলের পদ-নম্বর (প্রতি অধ্যায়ে ১ থেকে শুরু) — ব্যাজে দেখা যায়
  অর্থাৎ পাঠক «অধ্যায় ৩» শিরোনামের নিচে পদ ১, ২, ৩… দেখেন।

নীতি (পুরোনো নির্দেশ মেনে): উৎসে যা নেই তা অনুমান করে বসানো হয় না।
  কোনো পদ উৎসে না মিললে সেটি তৈরি করা হয় না — শুধু রিপোর্টে লেখা থাকে।

চালানো:
  python3 tools/fetch_bible.py --discover        # ৬৬ পুস্তকের তালিকা → _debug
  python3 tools/fetch_bible.py --probe           # দুটি নমুনা পাতার গঠন যাচাই
  python3 tools/fetch_bible.py --fetch --from 1 --to 20   # অংশে অংশে নামানো
  python3 tools/fetch_bible.py --fetch                    # সব (রিজিউম করে)
"""

import argparse
import html as htmllib
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_ebl as F  # noqa: E402  — get()/page_text()/to_int() পুনর্ব্যবহার

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "grantho" / "data"
SLUG = "bible"
OUT = DATA / SLUG
DBG = DATA / "_debug"

BOOK_URL = ("https://www.ebanglalibrary.com/books/"
            "%e0%a6%ac%e0%a6%be%e0%a6%82%e0%a6%b2%e0%a6%be-%e0%a6%ac%e0%a6%be"
            "%e0%a6%87%e0%a6%ac%e0%a7%87%e0%a6%b2/")
MANIFEST = DBG / "bible_books.json"

BN = "০১২৩৪৫৬৭৮৯"
# পার্সারের সংস্করণ। ছাঁকনি/বিভাজন বদলালে এটি বাড়ানো হয় — তখন পুরোনো
# নামানো ডেটা আর "সম্পূর্ণ" গণ্য হয় না ও পরের রানে নতুন করে নামে
# (নইলে পুরোনো বাগে কাটা পাঠ থেকেই যেত)। প্রতি চ্যাপ্টার-ফাইলে `pv` হিসেবে ছাপ থাকে।
PARSER_VERSION = 3   # v3: উৎসের ফাঁকা পদ-নম্বরগুলোও রাখা হয় (`srcEmpty` চিহ্নসহ)
# নেভিগেশন/ব্রেডক্রাম্বের লাইন — পাঠ নয়
NAV_LINE = re.compile(
    r"^(Bookmark|Menu|Previous (Lesson|Page)|Next (Lesson|Page|Topic)|"
    r"Back to (Lesson|Book)|Login|Register|Search|Expand|"
    r"বাংলা বাইবেল|\d+\s*Topics|\d+% Complete|0/\d+ Steps)$")
# লেসন-লেবেল: «১. আদিপুস্তক (Genesis)» — ইংরেজি নাম বন্ধনীতে থাকেই
LESSON_LABEL = re.compile(r"^\d{1,3}\.\s*\S.*\([^)]+\)\s*$")
VERSE_START = re.compile(r"^([০-৯]{1,3})[\s\u00a0]+(.*)$", re.S)
VERSE_MID = re.compile(r"(?<=[।”\"?\u0964])\s*([০-৯]{1,3})[\s\u00a0]+")
BN_NUM = re.compile(r"[০-৯]")


def bn_digits(n):
    return "".join(BN[int(c)] for c in str(n))


# ---------------------------------------------------------------- সূচি
def BN_DIGITS_2(n):
    return "".join(BN[int(d)] for d in f"{n:02d}")


def discover(book_url=BOOK_URL, save=True):
    """বই-পাতার সম্পূর্ণ বৃক্ষ: ৬৬ পুস্তক ও তাদের অধ্যায়-পাতার ঠিকানা।

    পাতাটিতে পুরো কোর্স-ট্রি একসাথে থাকে (প্রতি পুস্তকের লেসন-লিংক, তার নিচে
    টপিক-লিংক) — তাই একটিমাত্র অনুরোধেই সব পাওয়া যায়। ক্রম অপরিবর্তিত রাখা হয়,
    কারণ টেস্টামেন্ট-বিভাজন ও পুস্তক-ক্রম এই ক্রমের ওপরই দাঁড়িয়ে।
    """
    books = []
    for attempt in range(1, 4):
        h = F.get(book_url)
        if not h:
            raise SystemExit("বই-পাতা নামানো যায়নি — উৎস কি ব্লক করছে?")
        books, cur, seen = [], None, set()
        # প্রতিটি লিংকের ঠিকানা + লেবেল (ক্রমে)
        pat = re.compile(
            r'<a[^>]+href="(https://www\.ebanglalibrary\.com/(lessons|topics)/[^"#?]+)"'
            r'[^>]*>(.*?)</a>', re.S | re.I)
        for m in pat.finditer(h):
            url = htmllib.unescape(m.group(1))
            kind = m.group(2)
            label = F.text_of(m.group(3)).strip()
            label = re.sub(r"\s+", " ", label)
            # উৎসের লেবেলে পদের সংখ্যাও ছাপা থাকে («১. আদিপুস্তক (Genesis) 50
            # Topics») — সেটি বাদ না দিলে নাম-রেগেক্স ভেঙে bn-এ আবর্জনা ঢুকত।
            label = re.sub(r"\s*\d+\s*Topics\s*$", "", label).strip()
            if kind == "lessons":
                mm = re.match(r"^(\d+)\.\s*(.+?)\s*\(([^)]+)\)\s*$", label)
                if mm:
                    num, bname, ename = int(mm.group(1)), mm.group(2).strip(), mm.group(3).strip()
                else:
                    num, bname, ename = len(books) + 1, label, ""
                cur = dict(i=len(books) + 1, num=num, bn=bname, en=ename,
                           lesson=url, topics=[], topicLabels=[])
                books.append(cur)
                seen.add(url)
            elif cur is not None and url not in seen:
                seen.add(url)
                cur["topics"].append(url)
                cur["topicLabels"].append(label)
        if len(books) >= 66:
            break
        # উৎসের বই-পাতা বিশাল; মাঝে মাঝে প্রতিক্রিয়া অসম্পূর্ণ এসে পুস্তক তালিকা
        # মাঝপথে থেমে যেত (৫০/৬৬) — ফলে ১৬টি পুস্তক কখনোই নামত না। তাই
        # ৬৬ না পাওয়া পর্যন্ত আবার নামানো হয়।
        print(f"⚠ বই-পাতা অসম্পূর্ণ মনে হচ্ছে ({len(books)} পুস্তক) — আবার নামাই "
              f"(চেষ্টা {attempt + 1}/৩)", flush=True)
        time.sleep(2)
    if len(books) != 66:
        print(f"⚠ সতর্ক: বই-পাতায় {len(books)}টি পুস্তক মিলল (প্রত্যাশা ৬৬) — "
              f"উৎসের সূচি বদলেছে কি না দেখা দরকার", flush=True)
    # ভাঙা টপিক-লিংক সারাই: উৎসে মাঝে মাঝে href অসম্পূর্ণ থাকে (জাখারিয়া ১৩ →
    # «topics/চ/»)। একই বইয়ের প্রতিবেশী লিংকের slug-নিয়ম আর লেবেল থেকে সঠিক
    # ঠিকানা নিশ্চিতভাবে গড়া যায়, তাই পাঠ না হারিয়ে লিংক সারানো হয়।
    for b in books:
        if len(b["topics"]) < 2:
            continue
        prefix = b["topics"][0].rstrip("/").rsplit("/", 1)[0]
        base_slug = b["topics"][0].rstrip("/").rsplit("/", 1)[-1].rsplit("-", 1)[0]
        for k in range(1, len(b["topics"])):
            want = f"-{BN_DIGITS_2(k + 1)}/"
            if not b["topics"][k].endswith(want):
                fixed = f"{prefix}/{base_slug}-{BN_DIGITS_2(k + 1)}/"
                print(f"  ℹ ভাঙা লিংক সারানো হলো: {b['bn']} · টপিক {k + 1} → "
                      f"{fixed.rsplit('/', 2)[-2]}/{fixed.rsplit('/', 1)[-1]}", flush=True)
                b["topics"][k] = fixed
    # টেস্টামেন্ট: পাতায় «ওল্ড টেস্টামেন্ট»/«নিউ টেস্টামেন্ট» বিভাজন থাকে।
    # লিংক-ক্রমে কোন পুস্তক কোন বিভাগে তা ধরা যায় বিভাজক-শব্দের অবস্থান থেকে।
    marks = []
    for key, tag in (("ওল্ড টেস্টামেন্ট", "old"), ("নিউ টেস্টামেন্ট", "new"),
                     ("পুরাতন নিয়ম", "old"), ("নূতন নিয়ম", "new"),
                     ("নতুন নিয়ম", "new"), ("Old Testament", "old"),
                     ("New Testament", "new")):
        for m in re.finditer(re.escape(key), h, re.I):
            marks.append((m.start(), tag))
    marks.sort()
    if marks:
        for b in books:
            # পুস্তকের লেসন-লিংকের আগে যে বিভাজক, সেই বিভাগই তার প্রযোজ্য
            pos = h.find(b["lesson"])
            if pos < 0:
                pos = h.find(urllib.parse.quote(b["lesson"], safe=":/"))
            if pos < 0 and b["topics"]:
                pos = h.find(b["topics"][0])
            tag = "old"
            if pos >= 0:
                for mp, mt in marks:
                    if mp < pos:
                        tag = mt
            else:
                tag = "old" if b["num"] <= 39 else "new"
            b["testament"] = tag
    else:
        for b in books:
            b["testament"] = "old" if b["num"] <= 39 else "new"
    nold = sum(1 for b in books if b["testament"] == "old")
    if books and (nold, len(books) - nold) != (39, 27):
        # উৎসের সূচিতে বিভাজক থাকলে সেটাই প্রমাণ — প্রচলিত ৩৯/২৭ ধারণা দিয়ে
        # তাকে বদলানো হয় না (উৎসে অতিরিক্ত পুস্তকও থাকতে পারে)। শুধু জানিয়ে রাখি।
        print(f"ℹ টেস্টামেন্ট-বিভাজন: পুরাতন {nold} / নতুন {len(books) - nold} "
              f"(প্রচলিত ৩৯/২৭ থেকে আলাদা — উৎসের সূচিই মানা হলো)"
              if marks else
              f"⚠ বিভাজক-চিহ্ন মেলেনি — প্রচলিত ক্রম ধরে পুরাতন {nold} / "
              f"নতুন {len(books) - nold}", flush=True)
    for b in books:
        b["ntopics"] = len(b["topics"])
    if save:
        DBG.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(books, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        print(f"ম্যানিফেস্ট লেখা হলো: {MANIFEST.relative_to(ROOT)} "
              f"({len(books)} পুস্তক · মোট অধ্যায় {sum(b['ntopics'] for b in books)})")
    return books


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return discover()


# ---------------------------------------------------------------- পাঠ-পার্শিং
def bold_headings(h):
    """পাতায় <strong>/<b>/<h2-4>-এ ছাপা অনুচ্ছেদ-শিরোনাম («সৃষ্টির কথা»)।

    কেন মার্কআপ থেকে: পাঠের লাইন দেখে অনুমান করলে ছোট পদকে শিরোনাম ভাবার
    ঝুঁকি ছিল। উৎসে শিরোনামগুলো বোল্ড করায় চেনা নির্ভরযোগ্য।
    """
    out = []
    for m in re.finditer(r"<(strong|b|h[2-4])\b[^>]*>(.*?)</\1>", h, re.S | re.I):
        t = F.text_of(m.group(2)).strip()
        if 1 < len(t) < 90 and not BN_NUM.match(t) and t not in out:
            out.append(t)
    return out


CONTENT_MARKERS = (
    r'<div[^>]+class="[^"]*ld-topic-content[^"]*"[^>]*>',
    r'<div[^>]+class="[^"]*sfwd-topic-content[^"]*"[^>]*>',
    r'<div[^>]+class="[^"]*entry-content[^"]*"[^>]*>',
    r'<div[^>]+id="ld-topic-content[^"]*"[^>]*>',
    r'<div[^>]+class="[^"]*ld-tabs-content[^"]*"[^>]*>',
    r'<article\b[^>]*>',
)


def _region_candidates(h):
    """পাঠের সম্ভাব্য এলাকা, সবচেয়ে নির্ভরযোগ্যটি আগে — (এলাকা, কৌশল)।

    কেন একাধিক কৌশল: থিমে পাঠ কখনো `ld-topic-content`, কখনো `entry-content`
    বাক্সে থাকে, আবার কখনো কোনো ক্লাসই ধরা পড়ে না। ভুল এলাকা ধরলে পুরো
    অধ্যায় হারাত — তাই সব কৌশলের ফল মিলিয়ে যেটিতে পদ মেলে সেটিই নেওয়া হয়।
    """
    out = []
    for pat in CONTENT_MARKERS:
        m = re.search(pat, h, re.I)
        if not m:
            continue
        tag = re.match(r"<(\w+)", m.group(0)).group(1).lower()
        depth, i = 1, len(h)
        for mm in re.finditer(r"<(/?)%s\b" % tag, h[m.end():], re.I):
            if mm.group(1):
                depth -= 1
                if depth == 0:
                    i = m.end() + mm.start()
                    break
            else:
                depth += 1
        out.append((h[m.start():i], f"marker:{tag}"))
    hs = list(re.finditer(r"<h1[^>]*>.*?</h1>", h, re.S | re.I))
    if hs:
        start = hs[-1].end()
        stop = len(h)
        for mark in ("Bookmark", "Previous Lesson", "Back to Lesson",
                     "Next Topic", "<footer", "Post a comment"):
            k = h.find(mark, start)
            if k > start:
                stop = min(stop, k)
        out.append((h[start:stop], "h1-region"))
    out.append((h, "page_text"))
    return out


def parse_chapter(h, url, title, expect_first=1):
    """একটি অধ্যায়-পাতা → (পদ-তালিকা, নোট, কোন কৌশলে পাঠ মিলল)।"""
    best = ([], ["একটিও পদ পার্স হয়নি"], "none")
    for region, how in _region_candidates(h):
        vs, notes = _parse_region(region, h, title, expect_first)
        if vs and not best[0]:
            best = (vs, notes, how)
        elif vs and len(vs) > len(best[0]):
            best = (vs, notes, how)
    return best


def _parse_region(region, h, title, expect_first=1):
    heads = bold_headings(region)
    txt = F.page_text(h) if region is h else F.text_of(region)
    body, pending_head = [], None
    for raw in txt.split("\n"):
        ln = raw.strip()
        if not ln or NAV_LINE.match(ln):
            continue
        # text_of() শিরোনাম-ট্যাগকে «## …» করে দেয় — সেগুলো পাঠ নয়
        if ln.startswith("## "):
            t = ln[3:].strip()
            if t and not VERSE_START.match(t):
                pending_head = t
                continue
            ln = t
        if ln in heads:
            pending_head = ln
            continue
        # ব্রেডক্রাম্ব/সূচির পরিচয়-লাইন — পাঠ নয়। সতর্কতা: আগে এখানে
        # «ছোট ও দাঁড়িবিহীন» যেকোনো লাইন বাদ পড়ত, ফলে পদের ভাঙা অংশ হারাত
        # (নমুনা: «তাঁরই প্রতিরূপে»)। তাই এখন কেবল সুনির্দিষ্ট পরিচয়-লাইন বাদ:
        # বইয়ের নাম, লেসন-লেবেল «১. আদিপুস্তক (Genesis)», আর টপিকের নিজের শিরোনাম।
        if (ln == title or "বাংলা বাইবেল" in ln or LESSON_LABEL.match(ln)):
            continue
        body.append((ln, pending_head))
        pending_head = None

    verses, notes, expect = [], [], expect_first
    tail = ""
    for ln, hd in body:
        expect = _split_line(ln, verses, expect, notes, hd)
    # নম্বরহীন লেজ প্রথম পদের আগে বসে (উৎসে ভূমিকা-জাতীয় অংশ থাকলে)
    if tail:
        notes.append("নম্বরহীন অগ্রভাগ মিলেছে")
    # উৎসে কখনো পদ-নম্বর ছাপা থাকে কিন্তু পাঠ থাকে না (আদিপুস্তক ৩৬-এর ৭, ৮,
    # ৪১-৪৩ — উৎস-পাতা দেখে নিশ্চিত হওয়া)। আগে এগুলো চুপচাপ বাদ পড়ত, ফলে
    # পাঠকের কাছে পদ-সংখ্যা গোনা অবস্থায় থেকে যেত। এখন নম্বরগুলো থাকে, কেবল
    # `srcEmpty` চিহ্ন লাগে — পাঠ তৈরি করা হয় না, লুকানোও হয় না।
    for v in verses:
        if not v["bn"].strip():
            v["srcEmpty"] = True
    return verses, notes


def _split_line(ln, verses, expect, notes, hd):
    """একটি লাইন থেকে পদ কেটে আলাদা করা; নতুন প্রত্যাশিত নম্বর ফেরায়।

    উৎসে কখনো কখনো দুই-তিনটি পদ একই প্যারাগ্রাফে ছাপা হয় (আদিপুস্তক ১:২২-২৩),
    আবার পদের ভেতরেই সংখ্যা থাকে («১০০ বছর»)। তাই:
      ▸ লাইনের শুরুর নম্বর প্রত্যাশার সমান বা বড় হলে নতুন পদ (বড় হলে মাঝের
        পদগুলো উৎসে নেই বলে নোট হয় — অনুমান করে বসানো হয় না);
      ▸ লাইনের মাঝের নম্বর কেবল বাক্য-শেষের পরে এবং ঠিক প্রত্যাশিত হলেই কাটা হয়।
    """
    pos = 0
    while True:
        m, num = None, None
        if pos == 0:
            mm = VERSE_START.match(ln)
            if mm:
                cand = F.to_int(mm.group(1))
                if cand is not None and cand >= expect:
                    m, num = (mm.start(1), mm.end(1)), cand
        if m is None:
            for mm in VERSE_MID.finditer(ln, pos):
                cand = F.to_int(mm.group(1))
                # মাঝের নম্বর কেবল তখনই পদ-সীমা ধরা হয় যখন তার পরে যথেষ্ট পাঠ
                # থাকে — নইলে «। ৬ জন লোক এল» ধরনের কথা পদ-নম্বর ভাবা হতো।
                if cand == expect and len(ln[mm.end(1):].strip()) >= 8:
                    m, num = (mm.start(1), mm.end(1)), cand
                    break
        if m is None:
            break
        before = ln[pos:m[0]].strip()
        if before:
            if verses:
                verses[-1]["bn"] = (verses[-1]["bn"] + " " + before).strip()
            else:
                notes.append("পদের আগে নম্বরহীন পাঠ")
        if num > expect:
            for miss in range(expect, num):
                notes.append(f"পদ {bn_digits(miss)} উৎসে মেলেনি")
        rest = ln[m[1]:].strip()
        # পরের পদ-নম্বর না পাওয়া পর্যন্ত এই পদের পাঠ পরের লাইনেও চলতে পারে
        nxt = None
        for mm in VERSE_MID.finditer(rest):
            if F.to_int(mm.group(1)) == num + 1:
                nxt = mm.start(1)
                break
        v = {"vn": num, "bn": rest[:nxt].strip() if nxt is not None else rest}
        if hd:
            v["hd"] = hd
            hd = None
        verses.append(v)
        expect = num + 1
        if nxt is None:
            pos = len(ln)
            break
        pos = m[1] + nxt
    if pos < len(ln) and not ln[pos:].strip():
        pass
    elif pos == 0 or (pos < len(ln) and verses and ln[pos:].strip()):
        # কোনো পদ-চিহ্ন মেলেনি — লাইনটি আগের পদেরই অংশ
        left = ln[pos:].strip() if pos else ln.strip()
        if left and verses:
            verses[-1]["bn"] = (verses[-1]["bn"] + " " + left).strip()
    return expect


# ---------------------------------------------------------------- লেখা
def build_book(book, chapters, missing):
    """পার্স-করা অধ্যায়গুলো → রিডারের চ্যাপ্টার-ফাইলের কাঠামো।"""
    verses, groups, n = [], [], 0
    for chno, vs in chapters:
        if not vs:
            continue
        start = n + 1
        for v in vs:
            n += 1
            d = {"n": n, "vn": v["vn"], "ch": chno, "bn": v["bn"],
                 "spk": "", "bnSrc": F.SRC}
            if v.get("hd"):
                d["hd"] = v["hd"]
            if v.get("srcEmpty"):
                d["srcEmpty"] = True
            verses.append(d)
        groups.append({"id": chno, "from": start, "to": n,
                       "vfrom": vs[0]["vn"], "vto": vs[-1]["vn"],
                       "verse": len(vs)})
    return {
        "id": book["i"], "bn": book["bn"], "en": book.get("en", ""),
        "count": len(verses), "from": 1, "to": len(verses),
        "url": book["lesson"], "verses": verses,
        "suktas": groups, "suktaCount": len(groups),
        "groupWord": "অধ্যায়", "withBn": sum(1 for v in verses if v["bn"]),
        "testament": book.get("testament", ""), "pv": PARSER_VERSION,
        **({"missing": missing} if missing else {}),
    }


def _verses_of(obj):
    return obj.get("verses", [])


def write_index(books):
    """সূচি গড়া — ডিস্কে যা আছে তা থেকেই।

    কেন এভাবে: এক রানে সব পুস্তক না নামলে কেবল এই রানের পুস্তক দিয়ে সূচি
    বানালে আগের রানের নামানো পুস্তকগুলো সূচি থেকে হারিয়ে যেত (পাঠক আর
    দেখতই না)। তাই প্রতিটি পুস্তকের ফাইল পড়ে সূচি মেলে-চলে।
    """
    OUT.mkdir(parents=True, exist_ok=True)
    chs, total, withbn = [], 0, 0
    for b in books:
        fp = OUT / f'ch{b["i"]}.json'
        if not fp.exists():
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f'  ! ch{b["i"]}.json পড়া যায়নি ({e}) — সূচিতে নেওয়া হলো না')
            continue
        if not d.get("count"):
            continue
        total += d["count"]
        withbn += d.get("withBn", 0)
        chs.append({"id": d["id"], "bn": d["bn"], "en": d.get("en", ""),
                    "count": d["count"], "from": d["from"], "to": d["to"],
                    "suktaCount": d.get("suktaCount", 0),
                    "testament": d.get("testament", ""), "url": d.get("url", b["lesson"]),
                    **({"missing": d["missing"]} if d.get("missing") else {})})
    idx = {
        "slug": SLUG, "bn": "বাইবেল", "en": "Bangla Bible",
        "total": total, "withBn": withbn,
        "verseWord": "পদ", "chword": "পুস্তক", "groupWord": "অধ্যায়",
        "chapters": chs, "url": BOOK_URL,
        "note": ("বাংলা বাইবেল — ebanglalibrary.com থেকে সংগৃহীত। "
                 f"{len(chs)} পুস্তক, {total} পদ। ইংরেজি অনুবাদ যোগ করা হয়নি "
                 "(ব্যবহারকারীর নির্দেশ: শুধু বাংলা)।"),
    }
    (OUT / "index.json").write_text(
        json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return idx


# ---------------------------------------------------------------- মোড
def cmd_probe(args):
    DBG.mkdir(parents=True, exist_ok=True)
    books = load_manifest()
    print(f"পুস্তক: {len(books)} · মোট অধ্যায়-পাতা: {sum(b['ntopics'] for b in books)}")
    picks = []
    for want in (args.probe_books or [1, 40]):
        if 1 <= want <= len(books):
            picks.append(books[want - 1])
    lines = []
    for b in picks:
        url = b["topics"][0]
        h = F.get(url) or ""
        (DBG / f"bible_sample_{b['i']}.html").write_text(h[:200000], encoding="utf-8")
        region, _ = content_region(h)
        txt = F.text_of(region)
        vs, notes, how = parse_chapter(h, url, b["topicLabels"][0])
        (DBG / f"bible_text_{b['i']}.txt").write_text(F.text_of(content_region(h)[0]),
                                                      encoding="utf-8")
        head = f"=== {b['bn']} ({b['en']}) · অধ্যায় {b['topicLabels'][0]} ==="
        info = (f"{head}\n"
                f"html বাইট: {len(h)} · পাঠ-অক্ষর: {len(txt)} · কৌশল: {how}\n"
                f"বোল্ড-শিরোনাম: {bold_headings(h)[:6]}\n"
                f"পার্স: পদ {len(vs)} · প্রথম vn {vs[0]['vn'] if vs else '-'} · "
                f"শেষ vn {vs[-1]['vn'] if vs else '-'} · নোট {notes[:5]}\n"
                f"page_text প্রথম ৪০০: {txt[:400]}\n"
                f"প্রথম পদ: {(vs[0]['bn'][:160] if vs else '')}\n")
        print(info)
        lines.append(info)
        time.sleep(args.delay)
    (DBG / "bible_probe.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"প্রোব-রিপোর্ট: {(DBG / 'bible_probe.txt').relative_to(ROOT)}")


def cmd_fetch(args):
    books = load_manifest()
    lo, hi = args.from_book, (args.to_book or len(books))
    OUT.mkdir(parents=True, exist_ok=True)
    DBG.mkdir(parents=True, exist_ok=True)
    prog_path = DBG / "bible_progress.json"
    prog = json.loads(prog_path.read_text(encoding="utf-8")) if prog_path.exists() else {}
    made, report, done, skipped = [], [], 0, 0
    t0 = time.time()
    for b in books:
        if not (lo <= b["i"] <= hi):
            continue
        fp = OUT / f"ch{b['i']}.json"
        # রিজিউম: সব অধ্যায় আগেই নেমে থাকলে আবার নামানো হয় না
        if args.resume and fp.exists():
            try:
                old = json.loads(fp.read_text(encoding="utf-8"))
                if old.get("count") and old.get("suktaCount") == b["ntopics"] \
                        and not old.get("missing") \
                        and old.get("pv") == PARSER_VERSION:
                    made.append(old)
                    skipped += 1
                    continue
            except Exception:
                pass
        chapters, missing, notes = [], [], []
        for k, url in enumerate(b["topics"], start=1):
            h = F.get(url)
            if not h:
                missing.append(k)
                notes.append(f"অধ্যায় {bn_digits(k)}: পাতা নামেনি")
                time.sleep(args.delay)
                continue
            label = b["topicLabels"][k - 1] if k - 1 < len(b["topicLabels"]) else ""
            vs, nts, how = parse_chapter(h, url, label, expect_first=1)
            if how.endswith(("raw", "whole")):
                notes.append(f"অধ্যায় {bn_digits(k)}: কনটেন্ট-এলাকা {how} (সন্দেহজনক)")
            if not vs:
                missing.append(k)
                notes.append(f"অধ্যায় {bn_digits(k)}: একটিও পদ পার্স হয়নি")
            chapters.append((k, vs))
            notes += [f"অধ্যায় {bn_digits(k)}: {x}" for x in nts[:4]]
            time.sleep(args.delay)
        obj = build_book(b, chapters, missing)
        fp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
        made.append(obj)
        done += 1
        line = (f"{b['i']:>2}. {b['bn']} ({b.get('en','')}): অধ্যায় {obj['suktaCount']}"
                f"/{b['ntopics']} · পদ {obj['count']}"
                + (f" · ⚠ বাদ {missing}" if missing else ""))
        print(line, flush=True)
        report.append(line)
        if notes:
            report.append("     নোট: " + "; ".join(notes[:8]))
        se = {}
        for v in obj["verses"]:
            if v.get("srcEmpty"):
                se.setdefault(v["ch"], []).append(v["vn"])
        if se:
            report.append("     উৎসে ফাঁকা পদ (নম্বর ছাপা, পাঠ নেই): " +
                          "; ".join(f"অ{c}: " + ",".join(map(str, ns)) for c, ns in se.items()))
        prog[str(b["i"])] = {"count": obj["count"], "groups": obj["suktaCount"],
                             "missing": missing, "when": int(time.time())}
        prog_path.write_text(json.dumps(prog, ensure_ascii=False), encoding="utf-8")
        if args.budget and (time.time() - t0) > args.budget * 60:
            print(f"⏱ বাজেট {args.budget} মিনিট শেষ — এখানে থামি; পরের রানে "
                  f"বাকি পুস্তকগুলো রিজিউম হবে।", flush=True)
            report.append(f"বাজেটে থেমেছে: {b['i']}-তম পুস্তকের পর")
            break
    idx = write_index(books)
    onfile = idx["chapters"]
    tot_missing = sum(len(x.get("missing", [])) for x in onfile)
    tot_empty = sum(1 for x in onfile for v in _verses_of(x) if v.get("srcEmpty"))
    head = (f"=== বাংলা বাইবেল — ফল ===\n"
            f"পুস্তক: {len(made)} (এই রানে নতুন {done} · আগে থেকে ছিল {skipped}) · "
            f"মোট পদ: {idx['total']} · বাংলাসহ: {idx['withBn']}\n"
            f"অধ্যায় বিল্ডি: {sum(x['suktaCount'] for x in made)} · "
            f"নামেনি এমন অধ্যায়: {tot_missing}\n"
            f"উৎসে ফাঁকা পদ (নম্বর আছে, পাঠ উৎসেই নেই): {tot_empty}\n")
    txt = head + "\n".join(report) + "\n=== শেষ ===\n"
    (DBG / "bible_report.txt").write_text(txt, encoding="utf-8")
    print(head)
    if tot_missing:
        print(f"⚠ {tot_missing}টি অধ্যায় নামেনি — আবার চালালে (রিজিউম) বাকিগুলো নামবে।")
    return 0 if not tot_missing else 3


def main():
    ap = argparse.ArgumentParser(description="বাংলা বাইবেল নামানো")
    ap.add_argument("--discover", action="store_true", help="পুস্তক-তালিকা বের করা")
    ap.add_argument("--probe", action="store_true", help="নমুনা পাতার গঠন যাচাই")
    ap.add_argument("--probe-books", type=int, nargs="*", help="প্রোবের পুস্তক-নম্বর")
    ap.add_argument("--fetch", action="store_true", help="পাঠ নামানো")
    ap.add_argument("--from", dest="from_book", type=int, default=1)
    ap.add_argument("--to", dest="to_book", type=int, default=0)
    ap.add_argument("--resume", action="store_true", help="যা নেমেছে তা এড়িয়ে যাওয়া")
    ap.add_argument("--delay", type=float, default=0.7, help="অনুরোধের মাঝে বিরতি")
    ap.add_argument("--budget", type=float, default=0,
                    help="সর্বোচ্চ কত মিনিট নামাবে (০ = সীমা নেই); পরের রান রিজিউম করে")
    a = ap.parse_args()
    if a.discover:
        books = discover()
        old = sum(1 for b in books if b.get("testament") == "old")
        print(f"পুস্তক: {len(books)} · ওল্ড টেস্টামেন্ট {old} · নিউ {len(books) - old}")
        print("প্রথম ৩:", [f"{b['bn']} ({b['ntopics']})" for b in books[:3]])
        print("শেষ ৩:", [f"{b['bn']} ({b['ntopics']})" for b in books[-3:]])
        return
    if a.probe:
        cmd_probe(a)
        return
    if a.fetch:
        raise SystemExit(cmd_fetch(a))
    ap.print_help()


if __name__ == "__main__":
    main()
