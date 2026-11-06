#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""শুক্ল যজুর্বেদ (slug: yajurveda-shukla) — নামানো ডেটার পরিষ্কারক।

CI-তে fetch_ebl.py যে ডেটা নামিয়েছে তাতে চারটি গঠনগত সমস্যা ধরা পড়েছে
(প্রমাণ: assets/grantho/data/_debug/yajurveda_probe.txt ও আগের বিশ্লেষণ):

১) প্রতি অধ্যায়ে মন্ত্র-ধারার আগে অনুক্রমণিকা/ভূমিকার অনুবাদ খণ্ড আছে, আর
   পার্সার সেগুলোর নম্বর ধরেছে পাশের সংখ্যা থেকে — ফলে নম্বর দুবার আসে
   (যেমন চ্যাপ্টার ১: ১,২,৩ তারপর আবার ২,৩,৪…৩১)। সমাধান: প্রথম
   নম্বর-রিস্টার্টের আগের খণ্ডগুলোকে «অনুক্রমণিকা» লেবেল দেওয়া; আসল
   মন্ত্র-নম্বর অটুট থাকে, আর উৎসের নম্বর srcN-এ জমা থাকে।

২) কয়েকটি খণ্ডে বাংলা পাঠ ভুল করে `sk` ঘরে গেছে। পুরো বইয়ে একটিতেও আসল
   দেবনাগরী অক্ষর নেই (উৎসে সংস্কৃত মূল ছাপাই নেই), তাই দেবনাগরীবিহীন
   `sk` সবসময়ই ভুল ঘর — পাঠ `bn`-এ ফিরিয়ে `sk` ফাঁকা করা হয়, আর মূল টুকরো
   _debug/yajurveda_sk_moved.json-এ জমা থাকে (কিছু মুছে ফেলা হয় না)।

৩) অধ্যায়ের শিরোনাম ছিল কাটা-ছাঁটা ঠিকানা-টুকরো («০১ শুক্লযজুর্বেদ পূর্বা»)।
   উৎসের লেসন-শিরোনাম অনুযায়ী পূর্ণ রূপ বসানো হয় («প্রথম অধ্যায় · পূর্বার্ধ»)।
   নিরাপত্তার জন্য প্রতিটি শিরোনাম উৎসের সেই কাটা-টুকরোর সাথে মিলিয়ে যাচাই
   করা হয় — না মিললে পুরোনো শিরোনামই থাকে।

৪) index-এর note দাবি করত «মূল সংস্কৃত পাঠ ও বাংলা অনুবাদ», কিন্তু সংস্কৃত
   পাঠ এই সংস্করণে নেই — দাবিটি ডেটার সাথে মেলানো হয়।

সতর্কতা: «হোম», «প্রকাশক», «সূচি», «পরবর্তী»-র মতো শব্দ এখানে সাইটের
নেভিগেশন-ঝুট নয়, অনুবাদকের গদ্যের অংশ (হোম-কৰ্ম্ম, বেদার্থপ্রকাশক, সূচিত,
পরবর্তী কণ্ডিকা) — তাই সেগুলো কাটা হয় না। পাঠ ছাঁটাইয়ের নামে নষ্ট করা যাবে না।

ব্যবহার:  python3 tools/clean_yajurveda.py [--dry]
আইডেমপোটেন্ট: দুবার চালালে দ্বিতীয়বার কোনো পরিবর্তন হয় না।
"""

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "grantho" / "data"
SLUG = "yajurveda-shukla"
DBG = DATA / "_debug"

DEVA = re.compile("[\u0904-\u0939\u093D\u0950\u0958-\u0961\u0972-\u097F]")
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# উৎসের লেসন-শিরোনাম অনুযায়ী ৪০ অধ্যায়ের ক্রম-নাম ও ভাগ
# (পূর্বার্ধ ১–২০, উত্তরার্ধ ২১–৪০ — প্রোব-রিপোর্টে দেখা সূচি থেকে)
ORDINALS = [
    "প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম", "অষ্টম",
    "নবম", "দশম", "একাদশ", "দ্বাদশ", "ত্রয়োদশ", "চতুর্দশ", "পঞ্চদশ", "ষোড়শ",
    "সপ্তদশ", "অষ্টাদশ", "ঊনবিংশ", "বিংশ", "একবিংশ", "দ্বাবিংশ",
    "ত্রয়োবিংশ", "চতুর্বিশ", "পঞ্চবিংশ", "ষড়বিংশ", "সপ্তবিংশ", "অষ্টাবিংশ",
    "ঊনত্রিংশ", "ত্রিংশ", "একত্রিংশ", "দ্বাত্রিংশ", "ত্রয়স্ত্রিংশ",
    "চতুস্ত্রিংশ", "পঞ্চত্রিংশ", "ষট্ত্রিংশ", "সপ্তত্রিংশ", "অষ্টাত্রিংশ",
    "ঊনচত্বারিংশ", "চত্বারিংশ",
]


def toi(x):
    """'১২' / '12' / 12 → 12; না পারলে None."""
    s = str(x).strip().translate(BN_DIGITS)
    m = re.match(r"([0-9]+)", s)
    return int(m.group(1)) if m else None


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


EN2BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def bn_digits(n):
    return str(n).translate(EN2BN)


def split_preface(verses):
    """প্রথম নম্বর-রিস্টার্টের আগের খণ্ডগুলো = অনুক্রমণিকা/ভূমিকা।

    শর্ত: রিস্টার্ট-বিন্দু ১..৪-এর ভেতরে হতে হবে এবং সেই খণ্ডগুলোতে যথেষ্ট
    গদ্য থাকতে হবে — নইলে এটি ভূমিকা নয়, সংখ্যা-বিভ্রাট; তখন কিছু বদলানো হয় না।

    আইডেমপোটেন্সি: শুরুতে আগে-চিহ্নিত খণ্ড থাকলে সেগুলো বাদ দিয়ে হিসাব হয়,
    তাই দ্বিতীয় রানে লেবেল-বদলে যাওয়া সংখ্যা-ধারাকে রিস্টার্ট ধরে নেয় না।
    """
    skip = 0
    while skip < len(verses) and verses[skip].get("preface"):
        skip += 1
    if skip:
        return 0
    ns = [toi(v.get("n")) for v in verses]
    r = None
    for i in range(1, len(ns)):
        if ns[i] is not None and ns[i - 1] is not None and ns[i] <= ns[i - 1]:
            r = i
            break
    if not r or r > 4:
        return 0
    if sum(len(norm(v.get("bn"))) for v in verses[:r]) < 400:
        return 0
    return r


def chapter_title(cid, old):
    """উৎসের কাটা-টুকরো শিরোনাম থেকে পূর্ণ শিরোনাম, মিল যাচাইসহ।"""
    if cid < 1 or cid > len(ORDINALS):
        return old, "সীমার বাইরে"
    word = ORDINALS[cid - 1]
    half = "পূর্বার্ধ" if cid <= 20 else "উত্তরার্ধ"
    # পুরোনো শিরোনামের টুকরো দিয়ে যাচাই। উৎসের বানান কাটা থাকায় ফলা-চিহ্নে
    # পার্থক্য থাকতে পারে («ষটত্র» বনাম «ষট্ত্রিংশ»), তাই হসন্ত (্) বাদ দিয়ে তুলনা।
    # আর কোনো অধ্যায়ে ক্রম-নামের টুকরোই না থাকলে (যেমন ২১: কেবল «সংহিতা»)
    # সূচিতে তার অবস্থানই যথেষ্ট প্রমাণ — তখন বদল করা হয়, তবে নথিভুক্ত থাকে।
    def key(s):
        return re.sub("[\u09CD]", "", norm(s))

    GENERIC = ("শুক্ল", "যজুর্বেদ", "শুক্লযজুর্বেদ", "সংহিতা", "অন", "অনুবাদ")
    frags = [norm(t) for t in re.findall(r"[^\s—–-]+", str(old or "")) if len(norm(t)) > 2]
    cands = (key(word), key(half))
    named = [f for f in frags if not any(f.startswith(g) or g.startswith(f) for g in GENERIC)
             and not f.translate(BN_DIGITS).isdigit()]
    matched = any(c.startswith(key(f)) or key(f).startswith(c[:3]) or c[:3] == key(f)[:3]
                  for f in named for c in cands)
    if named and not matched:
        return old, f"মিলেনি ({'/'.join(named[-2:])} ≠ {'/'.join(c[:8] for c in cands)})"
    if not named:
        return f"{word} অধ্যায় · {half}", "সাধারণ টুকরো — সূচিতে অবস্থান থেকে নির্ধারিত"
    return f"{word} অধ্যায় · {half}", ""


def clean(dry=False):
    log = []
    d = DATA / SLUG
    idxp = d / "index.json"
    if not idxp.exists():
        print(f"ডেটা নেই: {idxp} — আগে CI ফেচ চালাতে হবে")
        return 1
    idx = json.loads(idxp.read_text(encoding="utf-8"))
    moved = []
    n_preface = n_sk = n_title = n_dup = 0
    n_mantra = n_mantrabn = n_chfile = 0

    for c in idx.get("chapters", []):
        fp = d / f'ch{c["id"]}.json'
        if not fp.exists():
            log.append(f'চ্যাপ্টার {c["id"]}: ফাইল নেই')
            continue
        blob = json.loads(fp.read_text(encoding="utf-8"))
        verses = blob.get("verses", [])

        # ১) ভুল ঘরে থাকা বাংলা পাঠ ফেরানো (দেবনাগরীবিহীন sk সবসময়ই ভুল)
        for v in verses:
            sk = str(v.get("sk") or "").strip()
            if sk and not DEVA.search(sk):
                bn = str(v.get("bn") or "").strip()
                merged = sk if (len(bn) < 100 and norm(bn) in norm(sk)) else (
                    sk if not bn else sk + "\n" + bn)
                moved.append({"chapter": c["id"], "n": v.get("n"),
                              "sk_chars": len(sk), "bn_chars": len(bn), "text": sk})
                v["bn"] = merged
                v["sk"] = ""
                n_sk += 1

        # ২) ভূমিকা/অনুক্রমণিকা খণ্ড আলাদা করা (আসল মন্ত্র-নম্বর অটুট রেখে)
        r = split_preface(verses)
        if r:
            for k, v in enumerate(verses[:r]):
                v["srcN"] = v.get("n")
                v["preface"] = True
                v["n"] = "অনুক্রমণিকা" if k == 0 else f"অনুক্রমণিকা-{bn_digits(k + 1)}"
                if not str(v.get("bnNote") or "").strip():
                    v["bnNote"] = "অনুক্রমণিকার বঙ্গানুবাদ"
            n_preface += r
            log.append(f'চ্যাপ্টার {c["id"]}: প্রথম {r}টি খণ্ড অনুক্রমণিকা হিসেবে চিহ্নিত')

        # ৩) মন্ত্র-ধারায় ভেতরের ডুপ্লিকেট নম্বর থাকলে শুধু নথিভুক্ত করা
        seq = [toi(v.get("n")) for v in verses[r:] if toi(v.get("n")) is not None]
        dups = sorted({x for x in seq if seq.count(x) > 1})
        if dups:
            n_dup += 1
            log.append(f'চ্যাপ্টার {c["id"]}: মন্ত্র-ধারায় ডুপ্লিকেট নম্বর {dups[:6]} '
                       f'(পাঠ অটুট, নম্বর বদলানো হয়নি)')

        # ৪) গণনা ও নম্বর-পরিসর: অনুক্রমণিকা-খণ্ড বাদ দিয়ে আসল মন্ত্র ধরা হয়
        #    (খণ্ডগুলো পাঠে থেকেই যায়, শুধু «মন্ত্র» সংখ্যায় গোনা হয় না)
        mantras = [v for v in verses if not v.get("preface")]
        nums = [toi(v.get("n")) for v in mantras]
        nums = [x for x in nums if x is not None]
        c["count"] = len(mantras)
        c["withBn"] = sum(1 for v in mantras if str(v.get("bn") or "").strip())
        if nums:
            c["from"], c["to"] = min(nums), max(nums)
        n_mantra += len(mantras)
        n_mantrabn += c["withBn"]

        # ৫) শিরোনাম ঠিক করা
        new, why = chapter_title(int(c["id"]), c.get("bn"))
        if new != c.get("bn"):
            c["bn"] = new
            n_title += 1
        elif why:
            log.append(f'চ্যাপ্টার {c["id"]}: শিরোনাম বদলানো হয়নি — {why}')

        # ৬) চ্যাপ্টার-ফাইলের নিজস্ব ঘরগুলো index-এর সাথে মেলানো।
        #    রিডার অধ্যায়-শিরোনাম ও সংখ্যা ch{n}.json থেকেই পড়ে
        #    (grantho.js: titleEl.textContent = chapter.bn) — তাই এগুলো না
        #    মেলানো পর্যন্ত পাতায় পুরোনো কাটা-শিরোনাম ও ভুল সংখ্যা দেখায়।
        for k, v in (("bn", c["bn"]), ("count", c["count"]),
                     ("withBn", c.get("withBn")), ("from", c.get("from")), ("to", c.get("to"))):
            if v is not None and blob.get(k) != v:
                if k == "bn":
                    n_chfile += 1
                blob[k] = v

        if not dry:
            fp.write_text(json.dumps(blob, ensure_ascii=False, indent=1), encoding="utf-8")

    # ৬) index-এর মিথ্যা দাবি ঠিক করা + মন্ত্র-গণনা (অনুক্রমণিকা বাদে)
    idx["total"] = n_mantra
    idx["withBn"] = n_mantrabn
    # কৃতিত্ব পাতার উৎস-লাইনে একবারই থাকে (build_pages-এর src) — এখানে কেবল
    # সেই ব্যাখ্যা যা পাঠককে সংখ্যার হিসাব বুঝতে সাহায্য করে।
    note = ("প্রতি অধ্যায়ে মন্ত্রের আগে উৎসের অনুক্রমণিকা-অনুবাদও যুক্ত আছে, "
            "যা মন্ত্র-গণনার বাইরে।")
    if idx.get("note") != note:
        log.append(f'note বদলালো: {idx.get("note")!r} → {note!r}')
        idx["note"] = note
    if idx.get("bnSrc") and "সংস্কৃত" in str(idx.get("bnSrc")):
        idx["bnSrc"] = "বাংলা অনুবাদ — ebanglalibrary.com"
    if not dry:
        idxp.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
        if moved:
            DBG.mkdir(parents=True, exist_ok=True)
            (DBG / "yajurveda_sk_moved.json").write_text(
                json.dumps(moved, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f'মন্ত্র: {n_mantra} (বাংলাসহ {n_mantrabn}) · অনুক্রমণিকা-খণ্ড: {n_preface} · '
          f'sk থেকে ফেরানো: {n_sk} · শিরোনাম ঠিক: {n_title} · '
          f'চ্যাপ্টার-ফাইল সিঙ্ক: {n_chfile} · ডুপ্লিকেট-নম্বর অধ্যায়: {n_dup}'
          + (" · [dry-run, কিছু লেখা হয়নি]" if dry else ""))
    for line in log[:40]:
        print("  " + line)
    if len(log) > 40:
        print(f"  … আরও {len(log) - 40} লাইন")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="শুধু দেখাও, লেখো না")
    a = ap.parse_args()
    sys.exit(clean(dry=a.dry))
