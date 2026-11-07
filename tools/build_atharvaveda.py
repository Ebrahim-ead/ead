#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""অথর্ববেদ সংহিতা (শৌনক) — উৎস থেকে সাইটের ডেটা তৈরি।

উৎস: bhavykhatri/DharmicData (GitHub), অথর্ববেদ — ODC Open Database License।
      মূল উৎস: Vedic Heritage Portal (vedicheritage.gov.in), ভারত সরকার।
      ২০টি কাণ্ড, শৌনক সংহিতা — বৈদিক স্বরচিহ্নসহ সংস্কৃত পাঠ।

        https://api.github.com/repos/bhavykhatri/DharmicData/contents/AtharvaVeda/
            atharvaveda_kaanda_<k>.json

        প্রতিটি ফাইল: [{veda, samhita, kaanda, sukta, text}, …]
        text-এর গঠন (সূক্ত-ধরে):
            <সূক্তের নাম>।            ←有時 থাকে
            १-४ ऋषिः। देवता। छन्दः।      ← মেটা (এক বা একাধিক লাইন)
            <মন্ত্র> ॥१॥ <মন্ত্র> ॥२॥ …

অথর্ববেদের নিজস্ব বৈশিষ্ট্য: এখানে «সূক্ত»ই একক, আর তার ভেতরে মন্ত্র —
অধ্যায়/শ্লোক নয়। তাই আউটপুট:
    assets/grantho/data/atharvaveda/index.json   {slug, bn, en, total, withBn, chapters, …}
    assets/grantho/data/atharvaveda/ch<N>.json   {id, bn, count, verses:[{n, sk, bn, hd, …}], …}

বাংলা অনুবাদ: ebanglalibrary.com-এ কাণ্ড ১–৭ আছে (৮–২০ লেসন-পাতায় নেই —
সাইটেরই মন্তব্যে অ্যাডমিন «চুরি গেছে» লিখেছেন)। তাই এখানে বাংলা বসানো হয় না;
`bn` ফাঁকা রাখা হয় — অনুমান করে কিছু লেখা হয় না। পরে বাংলা এলে
tools/merge_atharvaveda_bn.py দিয়ে জোড়া যাবে।

চালানো:
    python3 tools/build_atharvaveda.py            # ডেটা থাকলে বিল্ড
    python3 tools/build_atharvaveda.py --fetch    # GitHub থেকে নামিয়ে বিল্ড
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "assets", "grantho", "data", "atharvaveda")
CACHE = os.path.join(REPO, "assets", "grantho", "data", "_src", "atharvaveda")

SLUG = "atharvaveda"
BN_NAME = "অথর্ববেদ সংহিতা"
EN_NAME = "Atharvaveda"
VERSE_WORD = "মন্ত্র"
CHAPTER_WORD = "কাণ্ড"

GH_REPO = "bhavykhatri/DharmicData"
GH_PATH = "AtharvaVeda/atharvaveda_kaanda_{k}.json"

BN_SRC = ("সংস্কৃত মূল পাঠ (বৈদিক স্বরচিহ্নসহ) — Vedic Heritage Portal, সুত্রে "
          "DharmicData সংগ্রহ (ODbL)।")

# ---------------------------------------------------------------- সংখ্যা
BN = "০১২৩৪৫৬৭৮৯"
DEV = "०१२३४५६७८९"


def bn(n):
    return str(n).translate(str.maketrans("0123456789", BN))


def dev2int(s):
    return int(str(s).translate(str.maketrans(DEV, "0123456789")))


# ---------------------------------------------------------------- উৎস
def fetch_source():
    """GitHub থেকে ২০টি কাণ্ডের কাঁচা JSON নামায় (ক্যাশে রাখে)।"""
    os.makedirs(CACHE, exist_ok=True)
    have = []
    for k in range(1, 21):
        fp = os.path.join(CACHE, f"k{k}.json")
        if os.path.exists(fp) and os.path.getsize(fp) > 500:
            have.append(k)
            continue
        url = (f"https://api.github.com/repos/{GH_REPO}/contents/"
               + urllib.parse.quote(GH_PATH.format(k=k)))
        print(f"  ↓ কাণ্ড {k} …", end="", flush=True)
        try:
            raw = subprocess.run(["gh", "api", url, "--jq", ".content"],
                                 capture_output=True, text=True, timeout=120)
            if raw.returncode != 0 or not raw.stdout.strip():
                raise RuntimeError(raw.stderr.strip()[:200] or "খালি উত্তর")
            import base64
            data = base64.b64decode(raw.stdout)
            if len(data) < 500:
                raise RuntimeError("অতি ছোট")
            with open(fp, "wb") as f:
                f.write(data)
            json.loads(data.decode("utf-8"))       # বৈধ JSON তো?
            have.append(k)
            print(f" {len(data)//1024} KB")
        except Exception as e:
            print(f" ✗ {e}")
    return have


# ---------------------------------------------------------------- পার্স
DEV_LETTER = re.compile(r"[\u0900-\u097F]")
# মন্ত্র-শেষ: ॥१॥ বা ॥१-२॥
MANTRA_END = re.compile(r"॥\s*([०-९]{1,3})(?:\s*[-–]\s*([०-९]{1,3}))?\s*॥")
NUM_RANGE = re.compile(r"^\s*[०-९]{1,3}\s*[-–]\s*[०-९]{1,3}\s")
# ঋষি/দেবতা/ছন্দের সংকেত-শব্দ
META_HINT = re.compile(
    r"ऋषि|देवता|छन्द|छंद|अथर्वा|अङ्गिरा|अंगिरा|ब्रह्मा|प्रजापति|अग्नि|इन्द्र|वायु|"
    r"सूर्य|चन्द्र|चंद्र|वरुण|मरुत|विश्वामित्र|गोतम|विरूप|भृगु|कश्यप|वसिष्ठ|"
    r"गायत्री|त्रिष्टुप्|जगती|अनुष्टुप्|पङ्क्ति|पंक्ति|बृहती|उष्णिक्|शक्वरी|"
    r"विराट्|विराड्|साम्नी|पाद|अध्यात्म|ब्रह्मविद्या")


def split_sukta(text):
    """এক সূক্তের টেক্সট → (নাম, মেটা-লাইন[], [মন্ত্র-টেক্সট])।"""
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    title, meta, i = "", [], 0

    # ১) সূক্তের নাম: প্রথম লাইন — ছোট, দাঁড়ি-শেষ, মন্ত্র-চিহ্ন নেই, মেটা-শব্দ নেই
    if lines:
        first = lines[0]
        if (len(first) <= 60 and not MANTRA_END.search(first)
                and first.endswith(("।", "॥")) and DEV_LETTER.search(first)
                and not META_HINT.search(first)):
            cand = first.rstrip("।॥ ").strip()
            if cand:
                title, i = cand, 1

    # ২) মেটা: মন্ত্র-চিহ্নহীন লাইন যেগুলো ঋষি/দেবতা/ছন্দ বা সংখ্যা-পরিসরে শুরু
    while i < len(lines):
        ln = lines[i]
        if MANTRA_END.search(ln):
            break
        if (NUM_RANGE.match(ln) or META_HINT.search(ln) or "," in ln
                or ";" in ln or (len(ln) < 40 and ln.endswith("।"))):
            meta.append(ln)
            i += 1
            continue
        break

    # ৩) মন্ত্র: «॥N॥» চিহ্ন ধরে ভাগ
    verses, cur = [], []
    for ln in lines[i:]:
        cur.append(ln)
        if MANTRA_END.search(ln):
            verses.append(re.sub(r"\s+", " ", " ".join(cur)).strip())
            cur = []
    if cur:                                   # শেষ অংশ অসম্পূর্ণ হলে আগেরটায় জুড়ি
        tail = re.sub(r"\s+", " ", " ".join(cur)).strip()
        if verses:
            verses[-1] = (verses[-1] + " " + tail).strip()
        elif tail:
            verses.append(tail)
    return title, meta, verses


def parse_kanda(path, k):
    """এক কাণ্ডের JSON → সূক্ত-তালিকা [{sukta, title, meta, verses}]।"""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        raise ValueError(f"কাণ্ড {k}: প্রত্যাশিত তালিকা, পাওয়া গেল {type(d).__name__}")
    out = []
    for x in sorted(d, key=lambda y: int(y.get("sukta") or 0)):
        s = int(x["sukta"])
        title, meta, verses = split_sukta(x.get("text"))
        out.append(dict(sukta=s, title=title, meta=meta, verses=verses))
    return out


# ---------------------------------------------------------------- লেখা
def merged_available():
    """tools/merge_atharvaveda_bn.py-র ফল আছে কি না (বাংলা জোড়া লাগানো ডেটা)।"""
    return os.path.exists(os.path.join(OUT, "_bn_merged", "index.json"))


def build(fetch=False):
    # বাংলা জোড়া লাগানো ফল থাকলে সেটাই ব্যবহার করি — এতে সাইটে বাংলা দেখায়,
    # আর সংস্কৃত মূল (আলাদা ফোল্ডার) অটুট থাকে। না থাকলে কাঁচা উৎস থেকে।
    if merged_available() and not fetch:
        import shutil
        src = os.path.join(OUT, "_bn_merged")
        n = 0
        for name in os.listdir(src):
            if name.endswith(".json"):
                shutil.copy2(os.path.join(src, name), os.path.join(OUT, name))
                n += 1
        print(f"✓ বাংলা জোড়া লাগানো ডেটা ব্যবহার হলো ({n} ফাইল)")
        return 0

    if fetch:
        have = fetch_source()
    else:
        have = [k for k in range(1, 21)
                if os.path.exists(os.path.join(CACHE, f"k{k}.json"))]
    if len(have) < 20:
        # ক্যাশ (assets/grantho/data/_src/) না থাকলে — যেমন CI-তে, যেখানে কেবল
        # তৈরি ডেটা repo-তে আছে — কিছুই ভাঙি না। build_pages.py বিদ্যমান ডেটা
        # দিয়েই পাতা বানায়, তাই এখানে থামাই নিরাপদ।
        if (OUT / "index.json").exists() if isinstance(OUT, __import__("pathlib").Path) else \
           os.path.exists(os.path.join(OUT, "index.json")):
            print(f"   (উৎস-ক্যাশ নেই — repo-তে থাকা {len(have) or 'আগের'} ডেটাই "
                  f"ব্যবহার হবে, নতুন করে লেখা হচ্ছে না)")
            return 0
        print(f"⛔ কেবল {len(have)}/২০ কাণ্ড পাওয়া গেল — অসম্পূর্ণ ডেটা "
              f"লেখা হবে না (সাইটে ভাঙা গ্রন্থ বসানো চলবে না)।")
        return 1

    os.makedirs(OUT, exist_ok=True)
    chapters, grand, total_no_text = [], 0, 0
    for k in range(1, 21):
        suktas = parse_kanda(os.path.join(CACHE, f"k{k}.json"), k)
        verses, n = [], 0
        sukta_meta = []
        no_text = 0
        for sk_ in suktas:
            if not sk_["verses"]:
                # উৎসেই এই সূক্তের পাঠ নেই (কেবল ঋষি/দেবতা/ছন্দ) — লুকানো চলবে না
                no_text += 1
                print(f"   ⚠ কাণ্ড {k} সূক্ত {sk_['sukta']}: উৎসে পাঠ নেই (মেটা-শুধু)")
                continue
            first = n + 1
            for t in sk_["verses"]:
                n += 1
                # শিরোনাম ও ঋষি/দেবতা/ছন্দ সূক্তের প্রথম মন্ত্রে — তালিকায় দেখানোর জন্য
                v = dict(n=n, sk=t, bn="")
                if sk_["title"]:
                    v["hd"] = sk_["title"]
                if sk_["meta"]:
                    v["meta"] = " ".join(sk_["meta"])
                verses.append(v)
            sukta_meta.append(dict(s=sk_["sukta"], from_=first, to=n,
                                   name=sk_["title"], meta=sk_["meta"]))
        if not verses:
            print(f"⛔ কাণ্ড {k}-এ কোনো মন্ত্র নেই")
            return 1
        ch = dict(
            id=k, bn=f"{CHAPTER_WORD} {bn(k)}", count=n, from_=1, to=n,
            verses=verses, url=f"https://vedicheritage.gov.in/samhitas/atharvaveda/",
            withBn=0, suktaCount=len(sukta_meta), suktas=sukta_meta,
            note=("এই কাণ্ডে বাংলা অনুবাদ এখনো যোগ হয়নি — সংস্কৃত মূল পাঠ দেওয়া হচ্ছে।"
                  + (f" {bn(no_text)}টি সূক্তের পাঠ উৎসেই অনুপস্থিত (কেবল ঋষি/দেবতা/ছন্দ)।"
                     if no_text else "")),
        )
        ch["from"] = 1
        del ch["from_"]
        with open(os.path.join(OUT, f"ch{k}.json"), "w", encoding="utf-8") as f:
            json.dump(ch, f, ensure_ascii=False)
        chapters.append(dict(id=k, bn=ch["bn"], count=n, **{"from": 1, "to": n},
                             withBn=0, suktaCount=len(sukta_meta),
                             noText=no_text or 0))
        total_no_text += no_text
        grand += n
        print(f"  কাণ্ড {k:2d}: {len(sukta_meta):3d} সূক্ত · {n:4d} মন্ত্র")

    idx = dict(
        slug=SLUG, bn=BN_NAME, en=EN_NAME,
        total=grand, withBn=0, verseWord=VERSE_WORD,
        chapters=chapters, bnSrc=BN_SRC,
        suktaTotal=sum(c["suktaCount"] for c in chapters),
        note=("শৌনক সংহিতা — ২০টি কাণ্ড, সূক্ত ও মন্ত্র-সংখ্যাসহ সংস্কৃত মূল পাঠ। "
              "বাংলা অনুবাদ ধাপে ধাপে যোগ হচ্ছে: ebanglalibrary.com-এ কাণ্ড ১–৭ "
              "পাওয়া যায়, কাণ্ড ৮–২০ এখনো কোথাও বাংলায় নেই — "
              "অনুমান করে অনুবাদ বসানো হয় না।"
              + (f" {bn(total_no_text)}টি সূক্তের পাঠ উৎসেই অনুপস্থিত।"
                 if total_no_text else "")),
        noTextSuktas=total_no_text,
    )
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print(f"\n✓ অথর্ববেদ: {grand} মন্ত্র · {len(chapters)} কাণ্ড · "
          f"{idx['suktaTotal']} সূক্ত → {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="GitHub থেকে নামিয়ে বিল্ড")
    a = ap.parse_args()
    sys.exit(build(fetch=a.fetch))
