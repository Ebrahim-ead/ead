#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assets/grantho/data/<slug>/index.json → grantho/hindu/<slug>.html + হাব-কার্ড।

নীতি: ডেটায় যতটুকু বাংলা আছে ঠিক ততটুকুই দেখাই, বাড়িয়ে নয়।
কোনো index.json না থাকলে বা শূন্য হলে সেই গ্রন্থের পাতা/কার্ড তৈরি হয় না।
"""
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data"
OUT = ROOT / "grantho/hindu"

# ---- সাইটে এখন কোন গ্রন্থ থাকবে -------------------------------------------
# ব্যবহারকারীর সিদ্ধান্ত (২০২৬-১১-০৫): «শুধুমাত্র ভগবত গীতা আর চারটা বেদের
# ভিতর শুধুমাত্র ঋগ্বেদ রাখো; বাকি সবগুলো বাদ দাও।» তাই ডেটা/কার্ড কেবল
# এই দুটিরই তৈরি হয় — অন্য কোনো index.json পড়া হয় না।
ACTIVE = ("gita", "rigveda", "yajurveda-shukla")

BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


class Shrink(Exception):
    """ডেটা হঠাৎ অনেক ছোট হয়ে গেছে — পাতা বানিয়ে সাইট খারাপ করব না।"""


def bn(n):
    return str(n).translate(BN)


def commas(n):
    return bn(f"{int(n):,}")


# ---- প্রতিটি গ্রন্থের রূপকথা -------------------------------------------------
BOOKS = {
    "rigveda": dict(
        kind="veda", title=("ঋগ্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
        kicker="হিন্দু · বেদ · ঋগ্বেদ", crumb="ঋগ্বেদ সংহিতা",
        intro="ঋগ্বেদের বাংলা অনুবাদ — রমেশচন্দ্র দত্তের অনুবাদ (ebanglalibrary.com)।",
        word="মন্ত্র", chword="মণ্ডল",
        src="বাংলা অনুবাদ ebanglalibrary.com থেকে (অনুবাদ: রমেশচন্দ্র দত্ত)।",
        excerpt="দেবতাদের স্তবসমূহ — রমেশচন্দ্র দত্তের বাংলা অনুবাদে ১০ মণ্ডলের ১০,৪৫৬ মন্ত্র।",
    ),
    "samaveda": dict(
        kind="veda", title=("সামবেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
        kicker="হিন্দু · বেদ · সামবেদ", crumb="সামবেদ সংহিতা",
        intro="সামবেদের বাংলা অনুবাদসহ পাঠ — পরিতোষ ঠাকুরের অনুবাদ (ebanglalibrary.com)।",
        word="মন্ত্র", chword="অধ্যায়",
        src="সংস্কৃত মূল ও বাংলা অনুবাদ — ebanglalibrary.com (অনুবাদ: পরিতোষ ঠাকুর)।",
        excerpt="গানের বেদ — পরিতোষ ঠাকুরের বাংলা অনুবাদসহ ২৬ অধ্যায়ের মন্ত্র।",
    ),
    "atharvaveda": dict(
        kind="veda", title=("অথর্ববেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
        kicker="হিন্দু · বেদ · অথর্ববেদ", crumb="অথর্ববেদ সংহিতা",
        intro="অথর্ববেদের বাংলা অনুবাদসহ পাঠ — দিলীপ মুখোপাধ্যায় সম্পাদিত সংস্করণ (ebanglalibrary.com)।",
        word="মন্ত্র", chword="খণ্ড",
        src="সংস্কৃত মূল ও «বঙ্গানুবাদ» — ebanglalibrary.com (সম্পাদনা: দিলীপ মুখোপাধ্যায়)।",
        excerpt="দৈনন্দিন জীবনের মন্ত্র — দিলীপ মুখোপাধ্যায় সম্পাদিত সংস্করণে মূল ও বঙ্গানুবাদসহ।",
    ),
    "garuda": dict(
        kind="purana", title=("গরুড় পুরাণ", ""), hub="purana.html", hubname="পুরাণ",
        kicker="হিন্দু · পুরাণ · গরুড়", crumb="গরুড় পুরাণ",
        intro="গরুড় পুরাণের বাংলা অনুবাদ — অষ্টাদশ পুরাণ সমগ্র (পৃথ্বীরাজ সেন)।",
        word="শ্লোক", chword="অধ্যায়",
        src="বাংলা অনুবাদ ebanglalibrary.com থেকে (অষ্টাদশ পুরাণ সমগ্র, সম্পাদনা: পৃথ্বীরাজ সেন)। এই সংস্করণে সংস্কৃত শ্লোক দেবনাগরী লিপিতে ছাপা হয়নি — তাই কেবল বাংলা পাঠ দেওয়া হচ্ছে, অনুমান করে সংস্কৃত বসানো হয় না।",
        excerpt="বিষ্ণুর বাহন গরুড়ের জন্ম, অমৃতাহরণ ও ভক্তির কাহিনি — পৃথ্বীরাজ সেন সম্পাদিত অনুবাদ।",
    ),
    "bhabishya": dict(
        kind="purana", title=("ভবিষ্য পুরাণ", ""), hub="purana.html", hubname="পুরাণ",
        kicker="হিন্দু · পুরাণ · ভবিষ্য", crumb="ভবিষ্য পুরাণ",
        intro="ভবিষ্য পুরাণের বাংলা অনুবাদ — অষ্টাদশ পুরাণ সমগ্র (পৃথ্বীরাজ সেন)।",
        word="শ্লোক", chword="অধ্যায়",
        src="বাংলা অনুবাদ ebanglalibrary.com থেকে (অষ্টাদশ পুরাণ সমগ্র, সম্পাদনা: পৃথ্বীরাজ সেন)। সংস্কৃত মূল দেবনাগরীতে ছাপা হয়নি — কেবল বাংলা পাঠ দেওয়া হচ্ছে।",
        excerpt="ভবিষ্যৎ-কথা ও ব্রত-মাহাত্ম্যের পুরাণ — বাংলা অনুবাদসহ।",
    ),
}

BOOKS["yajurveda-shukla"] = dict(
    kind="veda", title=("শুক্ল যজুর্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · শুক্ল যজুর্বেদ", crumb="শুক্ল যজুর্বেদ সংহিতা",
    intro="শুক্ল যজুর্বেদের বাংলা অনুবাদসহ পাঠ — ebanglalibrary.com।",
    word="মন্ত্র", chword="অধ্যায়",
    src="বাংলা অনুবাদ ও মূল পাঠ ebanglalibrary.com থেকে।",
    excerpt="যজ্ঞের বিধি ও মন্ত্রের বেদ — শুক্ল শাখার বাংলা অনুবাদসহ।")
BOOKS["yajurveda-krishna"] = dict(
    kind="veda", title=("কৃষ্ণ যজুর্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · কৃষ্ণ যজুর্বেদ", crumb="কৃষ্ণ যজুর্বেদ সংহিতা",
    intro="কৃষ্ণ যজুর্বেদের বাংলা অনুবাদসহ পাঠ — ebanglalibrary.com।",
    word="মন্ত্র", chword="অধ্যায়",
    src="বাংলা অনুবাদ ও মূল পাঠ ebanglalibrary.com থেকে।",
    excerpt="যজ্ঞের বিধি ও মন্ত্রের বেদ — কৃষ্ণ শাখার বাংলা অনুবাদসহ।")
BOOKS["brahma"] = dict(
    kind="purana", title=("ব্রহ্ম পুরাণ", ""), hub="purana.html", hubname="পুরাণ",
    kicker="হিন্দু · পুরাণ · ব্রহ্ম", crumb="ব্রহ্ম পুরাণ",
    intro="ব্রহ্ম পুরাণের বাংলা অনুবাদ — অষ্টাদশ পুরাণ সমগ্র (পৃথ্বীরাজ সেন)।",
    word="শ্লোক", chword="অধ্যায়",
    src="বাংলা অনুবাদ ebanglalibrary.com থেকে (অষ্টাদশ পুরাণ সমগ্র, সম্পাদনা: পৃথ্বীরাজ সেন)।",
    excerpt="সৃষ্টি, ব্রহ্মাণ্ড ও তীর্থ-মাহাত্ম্যের পুরাণ — বাংলা অনুবাদসহ।")

UPA = {
    "upanishad-aitareya": ("ঐতরেয় উপনিষদ", "জগৎসৃষ্টি, আত্মার প্রবেশ ও «প্রজ্ঞানং ব্রহ্ম» — ঐতরেয় আরণ্যকের উপনিষদ।"),
    "upanishad-brihadaranyaka": ("বৃহদারণ্যক উপনিষদ", "«অহং ব্রহ্মাস্মি» — বৃহত্তম প্রধান উপনিষদ, যাজ্ঞবল্ক্য-মৈত্রেয়ীর সংলাপ।"),
    "upanishad-isha": ("ঈশ উপনিষদ", "ব্রহ্মেই জগৎ পরিব্যাপ্ত — কর্ম, জ্ঞান ও মৃত্যুর পরে গতির প্রশ্নে অষ্টাদশ মন্ত্রের সংক্ষিপ্ততম প্রধান উপনিষদ।"),
    "upanishad-kena": ("কেন উপনিষদ", "«কার ইচ্ছায় মন চলে?» — ব্রহ্মকে ইন্দ্রিয়ের অতীত বলে চিনিয়ে দেওয়া চার খণ্ডের উপনিষদ।"),
    "upanishad-prashna": ("প্রশ্ন উপনিষদ", "ছয় প্রশ্নকর্তা শিষ্যের ছয় প্রশ্নে প্রাণ, রশ্মি ও ওঁ-তত্ত্বের উত্তর।"),
    "upanishad-mundaka": ("মুণ্ডক উপনিষদ", "পরাবিদ্যা ও অপরাবিদ্যার পার্থক্য, এবং «সত্যেই জয়» — তিন মুণ্ডকের উপনিষদ।"),
    "upanishad-mandukya": ("মাণ্ডূক্য উপনিষদ", "ওঁ-কারের চার পদ ও চেতনার চার অবস্থা (জাগ্রত, স্বপ্ন, সুষুপ্তি, তুরীয়)।"),
    "upanishad-taittiriya": ("তৈত্তিরীয় উপনিষদ", "শিক্ষাবল্লী ও ব্রহ্মানন্দবল্লী — অন্ন, প্রাণ ও আনন্দের স্তরে ব্রহ্মানুসন্ধান।"),
    "upanishad-aitareya": ("ঐতরেয় উপনিষদ", "জগৎসৃষ্টি, আত্মার প্রবেশ ও «প্রজ্ঞানং ব্রহ্ম» — ঐতরেয় আরণ্যকের উপনিষদ।"),
}

# টেমপ্লেট: আগে সামবেদ-পাতা (মূল নকশা), না থাকলে যেকোনো বানানো গ্রন্থ-পাতা।
# সামবেদ সাইট থেকে সরানো হয়েছে, তাই এখানেও নির্ভরতা রাখা যাবে না।
#
# ▸ নতুন পাতা বানানোর *পরে* আনকন্ডিশনালি normalize() চালানো হয় (নিচে), কারণ
#   টেমপ্লেট-পাতাটাই পুরোনো হতে পারে: নতুন পাতা থেকে আধুনিক ফুটার/SEO/ক্লাস
#   টেনে নিয়ে সেগুলো বসানো হয়। ফলে build_pages.py দিয়ে rebuild করলেও
#   ফুটার-সংক্ষেপ, og:image ও canonical হারে না (আগে ফিরে যেত)।
def _pick_template():
    for cand in ("samaveda.html", "rigveda.html", "gita.html"):
        p = OUT / cand
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise SystemExit("টেমপ্লেট-পাতা পাওয়া গেল না (samaveda/rigveda/gita)")


TEMPLATE = _pick_template()

SITE = "https://ebrahim-ead.github.io/ead"
OG_CARD = SITE + "/assets/og-cover.jpg"


def _ref_page() -> str:
    """আধুনিক (হাতে ঠিক করা) পাতা — ফুটার ও head-এর জন্য সবচেয়ে ভালো নমুনা।"""
    for cand in ("rigveda.html", "gita.html", "islam.html"):
        p = OUT / cand
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


REF = _ref_page()
FOOTER = (re.search(r"<footer\b.*?</footer>", REF, re.S).group(0)
          if REF and re.search(r"<footer\b.*?</footer>", REF, re.S) else "")
EXTRA_CSS = re.compile(
    r'<link[^>]*href="(?:\.\./\.\./|\.\./|\.){0,3}assets/site-extra\.css"[^>]*>'
    r'(?:\s*<link[^>]*\?v=\d+"[^>]*>)?')


def normalize(slug: str, html: str) -> str:
    """new/পুরোনো নির্বিশেষে প্রতিটি বানানো পাতায় একই head ও ফুটার।"""
    href = f"{SITE}/grantho/hindu/{slug}.html"
    # ১) SEO ট্যাগ — আগে থাকলে হালনাগাদ, না থাকলে যোগ (canonical বারবার যোগ হয় না)
    if 'property="og:image"' in html:
        html = re.sub(r'(<meta property="og:image" content=")[^"]*(")', lambda m: m.group(1) + OG_CARD + m.group(2), html, count=1)
        html = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + href + m.group(2), html, count=1)
        if 'rel="canonical"' not in html:
            html = html.replace("</head>", f'<link rel="canonical" href="{href}">\n</head>', 1)
    else:
        lines = [f'<meta property="og:image" content="{OG_CARD}">',
                 '<meta property="og:image:width" content="1200">',
                 '<meta property="og:image:height" content="630">']
        if 'name="twitter:card"' in html:          # কার্ড-লাইন থাকলে মান ঠিক করি
            html = re.sub(r'<meta name="twitter:card"[^>]*>',
                          '<meta name="twitter:card" content="summary_large_image">', html, count=1)
        else:
            lines.append('<meta name="twitter:card" content="summary_large_image">')
        lines.append(f'<link rel="canonical" href="{href}">')
        html = html.replace("</head>", "\n".join(lines) + "\n</head>", 1)
    # ২) site-extra.css (মোবাইল/সূত্র/কম্প্যাক্ট ফুটার) — নতুনরা এটা পায় না
    if "site-extra.css" not in html:
        html = html.replace("</head>", '<link rel="stylesheet" href="../../assets/site-extra.css">\n</head>', 1)
    # ৩) ফুটার — পুরোনো টেমপ্লেটের ফুটার বদলে আধুনিক (সংক্ষিপ্ত) ফুটার
    if FOOTER:
        m = re.search(r"<footer\b.*?</footer>", html, re.S)
        if m and m.group(0) != FOOTER:
            html = html[:m.start()] + FOOTER + html[m.end():]
    return html


def load(slug):
    p = DATA / slug / "index.json"
    if not p.exists():
        return None
    try:
        idx = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not idx.get("chapters") or not idx.get("total"):
        return None
    return idx


# দেবনাগরী *অক্ষর* — দাঁড়ি (U+0964) ও অঙ্ক বাদ: সেগুলো বাংলা লেখাতেও বসে,
# তাই শুধু তাদের উপস্থিতিতে পাঠকে সংস্কৃত ধরলে ভুল দাবি ছাপা হয়।
DEVANAGARI_LETTERS = re.compile(r"[\u0904-\u0939\u093D\u0950\u0958-\u0961\u0972-\u097F]")


def count_with_sk(slug: str, idx: dict) -> int:
    """কতটি শ্লোক/মন্ত্রে আসলেই সংস্কৃত (দেবনাগরী) পাঠ আছে — পাতার দাবি যেন ডেটার সাথে মেলে।"""
    n = 0
    for c in idx.get("chapters", []):
        fp = DATA / slug / f"ch{c['id']}.json"
        if not fp.exists():
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        n += sum(1 for v in d.get("verses", []) if DEVANAGARI_LETTERS.search(str(v.get("sk") or "")))
    return n


def make_page(slug, idx, meta):
    main, sub = meta["title"]
    nch = len(idx["chapters"])
    total, withbn = idx["total"], idx.get("withBn", 0)
    withsk = count_with_sk(slug, idx)
    h = TEMPLATE

    h = h.replace("সামবেদ সংহিতা", f"{main} {sub}".strip())
    h = h.replace("হিন্দু · বেদ · সামবেদ", meta["kicker"])
    h = h.replace('<a href="veda.html">বেদ</a>',
                  f'<a href="{meta["hub"]}">{meta["hubname"]}</a>')
    h = h.replace('<h1>সামবেদ <span>সংহিতা</span></h1>',
                  f'<h1>{main} <span>{sub}</span></h1>' if sub else f'<h1>{main}</h1>')
    h = re.sub(r'(<div class="g-intro">.*?<p>)[^<]*(</p>)',
               lambda m: m.group(1) + meta["intro"] + m.group(2), h, count=1, flags=re.S)

    facts = f'<span class="g-fact"><b>{commas(withbn)}</b> {meta["word"]} (বাংলাসহ)</span>'
    if total != withbn:
        facts += f'<span class="g-fact"><b>{commas(total)}</b> মোট {meta["word"]}</span>'
    facts += f'<span class="g-fact"><b>{commas(nch)}</b> {meta["chword"]}</span>'
    nsuk = idx.get("suktaTotal") or sum(c.get("suktaCount", 0) for c in idx["chapters"])
    nshl = idx.get("shlokaTotal") or sum(c.get("shlokaCount", 0) for c in idx["chapters"])
    if nsuk:
        facts += f'<span class="g-fact"><b>{commas(nsuk)}</b> সূক্ত</span>'
    if nshl:
        facts += f'<span class="g-fact"><b>{commas(nshl)}</b> শ্লোক</span>'
    h = re.sub(r'<div class="g-facts">.*?</div>', '<div class="g-facts">' + facts + '</div>',
               h, count=1, flags=re.S)

    # সার্চ-বাক্স: টেমপ্লেটের লেবেল অন্য গ্রন্থে ভুল হতো, আর সংস্কৃত না থাকলে "(সংস্কৃত)" বিভ্রান্তিকর
    ph = f'{meta["word"]}ে খুঁজুন'
    if withsk and withsk == total:
        ph += " (সংস্কৃত বা বাংলা)"
    elif withsk == 0:
        ph += " (বাংলা)"
    h = re.sub(r'(<input id="g-search"[^>]*placeholder=")[^"]*(")', lambda m: m.group(1) + ph + m.group(2), h, count=1)
    h = re.sub(r'(<input id="g-search"[^>]*aria-label=")[^"]*(")',
               lambda m: m.group(1) + f'{meta["word"]}ে খুঁজুন' + m.group(2), h, count=1)
    if withsk == 0:
        h = re.sub(r'\s*<button[^>]*id="g-sk-btn".*?</button>', '', h, count=1, flags=re.S)

    h = h.replace('data-granth="samaveda"', f'data-granth="{slug}"').replace(
        'data-base="../../assets/grantho/data/samaveda/"',
        f'data-base="../../assets/grantho/data/{slug}/"')
    src = meta["src"]
    # সংস্কৃত পাঠের প্রাপ্যতা — আগে হার্ডকোডেড দাবি ছিল যা ডেটার সাথে মিলত না
    if withsk == 0:
        src += (f' এই সংস্করণে সংস্কৃত মূল পাঠ ছাপা হয়নি, তাই {meta["word"]}ে কেবল বাংলা অনুবাদ আছে'
                ' — কোনো অনুমানভিত্তিক সংস্কৃত পাঠ বসানো হয় না।')
    elif withsk < total:
        src += (f' সংস্কৃত মূল পাঠ আংশিক — {commas(total)}টি {meta["word"]}ের মধ্যে কেবল {commas(withsk)}টিতে'
                f' উৎসে সংস্কৃত পাওয়া গেছে, সেগুলোতেই তা ছাপা হয়েছে; বাকিগুলোতে কেবল বাংলা অনুবাদ আছে।'
                ' কোনো অনুমানভিত্তিক সংস্কৃত পাঠ বসানো হয় না।')
    if withbn < total:
        src += f' {commas(total - withbn)}টি {meta["word"]}র বাংলা উৎসে পাওয়া যায়নি — সেগুলো পরে যোগ হবে।'
    if idx.get("note"):   # ডেটার টীকা সবার শেষে (আগে দুবার যোগ হতো)
        src += " " + idx["note"]
    h = re.sub(r'<div class="g-src"><b>পাঠ সম্পর্কে।</b>.*?</div>',
               f'<div class="g-src"><b>পাঠ সম্পর্কে।</b> {src}</div>', h, count=1, flags=re.S)

    label = f"{main} {sub}".strip()
    fulldesc = f'{label}-র {commas(withbn)}টি {meta["word"]} বাংলা অনুবাদসহ — ebanglalibrary.com।'
    # সতর্কতা: দশার-অভাবে হঠাৎ বড় পতন (যেমন ৯২২২ → ২১ শ্লোক) সাইটে বসিয়ে দেব না।
    env = os.environ.get("GRANTHO_ALLOW_SHRINK", "").strip().lower() in ("1", "true", "yes")
    if not env and (OUT / f"{slug}.html").exists():
        old_html = (OUT / f"{slug}.html").read_text(encoding="utf-8")
        m = re.search(r'<span class="g-fact"><b>([০-৯,]+)</b>\s*' + re.escape(meta["word"]),
                      old_html)
        if m:
            prev = int(m.group(1).replace(",", "").translate(BN_MAP))
            if prev and withbn < prev * 0.85:
                raise Shrink(f"{slug}: পুরনো পাতায় {prev}, নতুন ডেটায় {withbn} — "
                             f"হঠাৎ বড় পতন")

    h = re.sub(r'<title>[^<]*</title>', f'<title>{label} — {commas(withbn)} {meta["word"]}, বাংলা অনুবাদসহ | Ebrahim Ead</title>', h, count=1)
    for pat, val in ((r'(<meta name="description" content=")[^"]*(")', fulldesc),
                     (r'(<meta property="og:title" content=")[^"]*(")',
                      f'{label} — {commas(withbn)} {meta["word"]}, বাংলা অনুবাদসহ | Ebrahim Ead'),
                     (r'(<meta property="og:description" content=")[^"]*(")', fulldesc),
                     (r'(<meta name="twitter:title" content=")[^"]*(")',
                      f'{label} — {commas(withbn)} {meta["word"]}'),
                     (r'(<meta name="twitter:description" content=")[^"]*(")', fulldesc)):
        h = re.sub(pat, lambda m, v=val: m.group(1) + v + m.group(2), h, count=1)
    (OUT / f"{slug}.html").write_text(normalize(slug, h), encoding="utf-8")
    return dict(slug=slug, total=total, withbn=withbn, nch=nch)


def card(href, kicker, title, sub, excerpt, soon=False):
    if soon:
        return (f'<article class="article-card rv is-soon"><a class="article-card-link" href="#" '
                f'aria-disabled="true" tabindex="-1"><span class="article-card-kicker">{kicker}</span>'
                f'<h3>{title}<span class="g-soon">শীঘ্রই আসছে</span></h3>'
                f'<p class="article-card-subtitle">{sub}</p><p class="article-card-excerpt">{excerpt}</p>'
                f'<span class="article-card-more">শীঘ্রই আসছে</span></a></article>')
    return (f'<article class="article-card rv"><a class="article-card-link" href="{href}">'
            f'<span class="article-card-kicker">{kicker}</span><h3>{title}</h3>'
            f'<p class="article-card-subtitle">{sub}</p><p class="article-card-excerpt">{excerpt}</p>'
            f'<span class="article-card-more">পড়ুন <b aria-hidden="true">→</b></span></a></article>')


def replace_grid(page, inner):
    p = OUT / page
    if not p.exists():
        print("  (পাতা নেই)", page)
        return
    s = p.read_text(encoding="utf-8")
    m = re.search(r'<div class="g-grid">.*?</div>\s*(?=<div class="g-note"|<a class="g-back")', s, re.S)
    if not m:
        print("  (গ্রিড খুঁজে পাইনি)", page)
        return
    s = s[:m.start()] + '<div class="g-grid">' + inner + '</div>\n  ' + s[m.end():]
    p.write_text(s, encoding="utf-8")
    print("  গ্রিড আপডেট:", page)


def refresh_rigveda_layout():
    """ঋগ্বেদে সূক্ত/শ্লোক-ভাগ হালনাগাদ করি (নতুন মণ্ডল নামলে দরকার হয়)।"""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import rigveda_suktas
    except Exception as e:
        print("  (সূক্ত-ভাগ বাদ:", e, ")")
        return
    try:
        rigveda_suktas.main(apply=True)
    except Exception as e:
        print("  (সূক্ত-ভাগ ব্যর্থ:", e, ")")


def main():
    made = []
    if (DATA / "rigveda" / "index.json").exists():
        refresh_rigveda_layout()
    # ---- বেদ
    vedas = []
    for slug in [x for x in ("rigveda", "samaveda", "yajurveda-shukla",
                             "yajurveda-krishna", "atharvaveda") if x in ACTIVE]:
        meta = BOOKS.get(slug)
        idx = load(slug)
        if not meta or not idx:
            if slug in ("rigveda", "samaveda", "atharvaveda"):
                pass
            continue
        r = make_page(slug, idx, meta)
        made.append(r)
        vedas.append((slug, r, meta))
        print(f"{slug}: {r['withbn']}/{r['total']} · {r['nch']}")

    grid = ""
    order = ["rigveda", "samaveda", "yajurveda-shukla", "yajurveda-krishna", "atharvaveda"]
    byslug = {s: (r, m) for s, r, m in vedas}
    labels = {"rigveda": ("বেদ · ঋগ্বেদ", "ঋগ্বেদ"), "samaveda": ("বেদ · সামবেদ", "সামবেদ"),
              "yajurveda-shukla": ("বেদ · শুক্ল যজুর্বেদ", "শুক্ল যজুর্বেদ"),
              "yajurveda-krishna": ("বেদ · কৃষ্ণ যজুর্বেদ", "কৃষ্ণ যজুর্বেদ"),
              "atharvaveda": ("বেদ · অথর্ববেদ", "অথর্ববেদ")}
    for slug in order:
        if slug in byslug:
            r, m = byslug[slug]
            k, t = labels[slug]
            grid += card(f"{slug}.html", k, t,
                         f'{commas(r["withbn"])} {m["word"]} · {commas(r["nch"])} {m["chword"]} · বাংলা অনুবাদসহ',
                         m["excerpt"])
        elif slug in ACTIVE and slug in ("yajurveda-shukla", "yajurveda-krishna"):
            k, t = labels[slug]
            grid += card("", k, t, "শুক্ল ও কৃষ্ণ — দুই শাখা",
                         "যজ্ঞের বিধি ও মন্ত্রের বেদ — উৎস থেকে পাঠ নামানো হচ্ছে।", soon=True)
    replace_grid("veda.html", grid)

    # ---- পুরাণ
    puranas = []
    for slug in (x for x in ("garuda", "bhabishya", "brahma") if x in ACTIVE):
        meta = BOOKS[slug]
        idx = load(slug)
        if not idx:
            continue
        if not idx.get("withBn"):
            print(f"{slug}: বাংলা নেই — বাদ")
            continue
        r = make_page(slug, idx, meta)
        puranas.append((slug, r, meta))
        print(f"{slug}: {r['withbn']}/{r['total']}")
    pg = ""
    for slug, r, m in puranas:
        name = m["title"][0]
        pg += card(f"{slug}.html", f'পুরাণ · {name.replace(" পুরাণ","")}', name,
                   f'{commas(r["withbn"])} শ্লোক বাংলাসহ', m["excerpt"])
    pg += card("", "পুরাণ · ১৮ মহাপুরাণ", "বাকি পুরাণ",
               "ব্রহ্ম · পদ্ম · বিষ্ণু · শিব…", "বাকি পুরাণগুলোর পাঠ ও অনুবাদ ধাপে ধাপে যোগ হবে।", soon=True)
    if puranas:
        replace_grid("purana.html", pg)

    # ---- উপনিষদ
    upa_cards, upa_total = "", 0
    for slug in list(UPA):
        idx = load(slug) if slug in ACTIVE else None
        if not idx:
            continue
        name, ex = UPA[slug]
        r = make_page(slug, idx, dict(
            kind="upanishad", title=(name, ""), hub="upanishad.html", hubname="উপনিষদ",
            kicker="হিন্দু · উপনিষদ · " + name.replace(" উপনিষদ", ""),
            crumb=name,
            intro=f"{name} — সংস্কৃত মূল, অন্বয়, সরলার্থ ও ব্যাখ্যা; বাংলা ebanglalibrary.com থেকে (স্বামী লোকেশ্বরানন্দ)।",
            word="মন্ত্র", chword="খণ্ড",
            src="সংস্কৃত মূল বাংলা অক্ষরে (উৎস-সংস্করণ অনুসারে); বাংলা অনুবাদ ও ব্যাখ্যা ebanglalibrary.com (স্বামী লোকেশ্বরানন্দ, «উপনিষদ – প্রথম ভাগ»)।",
            excerpt=ex))
        upa_total += r["withbn"]
        upa_cards += card(f'{slug}.html', f'উপনিষদ · {name.replace(" উপনিষদ","")}', name,
                          f'{commas(r["withbn"])} মন্ত্র · {commas(r["nch"])} খণ্ড', ex)
        print(f"{slug}: {r['withbn']}")
    # শ্বেতাশ্বতর/কঠ/ছান্দোগ্য হাতে-বানানো পাতা — সেগুলো আগে রাখি
    if upa_cards and (OUT / "upanishad.html").exists():
        s = (OUT / "upanishad.html").read_text(encoding="utf-8")
        fixed = []
        for href in ("shvetashvatara.html", "katha.html", "chandogya.html"):
            m = re.search(r'<article class="article-card rv"><a class="article-card-link" href="' + href + r'">.*?</article>', s, re.S)
            if m:
                fixed.append(m.group(0))
                fn = href.replace(".html", "")
                idx = load(fn)
                if idx:
                    upa_total += idx.get("withBn", 0)
        replace_grid("upanishad.html", "".join(fixed) + upa_cards +
                     card("", "উপনিষদ · প্রধান ১৩", "বাকি প্রধান উপনিষদ",
                          "বৃহদারণ্যক · কৌষীতমি · মৈত্রায়ণী",
                          "উৎসে যেগুলো পূর্ণ পাওয়া যায়নি সেগুলো পরে যোগ হবে।", soon=True))
    print("উপনিষদ মোট:", upa_total)

    # ---- হিন্দু-হাব সারাংশ
    if made or puranas or upa_cards:
        hp = ROOT / "grantho/hindu.html"
        s = hp.read_text(encoding="utf-8")
        ved = sum(r["withbn"] for _, r, _ in vedas)
        pur = sum(r["withbn"] for _, r, _ in puranas)
        g = load("gita")
        if g and 'href="hindu/gita.html"' in s:
            s = re.sub(r'(href="hindu/gita\.html">.*?<p class="article-card-subtitle">)[^<]*',
                       lambda m: m.group(1) + f'{commas(g["withBn"])} শ্লোক · '
                       f'{commas(len(g["chapters"]))} অধ্যায়', s, count=1, flags=re.S)
        if ved and 'href="hindu/rigveda.html"' in s:
            rv = next((r for sl, r, _ in vedas if sl == "rigveda"), None)
            if rv:
                s = re.sub(r'(href="hindu/rigveda\.html">.*?<p class="article-card-subtitle">)[^<]*',
                           lambda m: m.group(1) + f'{commas(rv["withbn"])} মন্ত্র · '
                           f'{commas(rv["nch"])} মণ্ডল', s, count=1, flags=re.S)
        hp.write_text(s, encoding="utf-8")
        print("হিন্দু-হাব:", ved, "/", pur)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Shrink as e:
        print("\n" + "=" * 60)
        print(f"⛔ বিল্ড থামানো হলো — {e}")
        print("ডেটা যাচাই না করে কিছু কমিট/প্রকাশ হবে না। জোর করে বিল্ড করতে:")
        print("   GRANTHO_ALLOW_SHRINK=1 python3 tools/build_pages.py")
        print("=" * 60)
        sys.exit(1)
