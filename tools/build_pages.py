import datetime
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
ACTIVE = ("gita", "rigveda", "yajurveda-shukla", "bible")

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

# বাইবেল — খ্রিস্টান অংশের প্রথম গ্রন্থ। পাতা grantho/christian/ ফোল্ডারে,
# তাই hub-লিংক এক ধাপ ওপরে (../christian.html) আর ক্রাম্ব থেকে টেমপ্লেটের
# «হিন্দু» অ্যাংকরটি বাদ দিতে হয় (crumbDrop)।
BOOKS["bible"] = dict(
    kind="bible", dir="christian", title=("বাংলা বাইবেল", ""),
    hub="../christian.html", hubname="খ্রিস্টান", crumbDrop="হিন্দু",
    kicker="খ্রিস্টান · বাইবেল", crumb="বাংলা বাইবেল",
    intro=("বাংলা বাইবেলের সম্পূর্ণ পাঠ — পুরাতন ও নতুন নিয়মের পুস্তকগুলো "
           "অধ্যায় ও পদ ধরে সাজানো (ebanglalibrary.com)।"),
    word="পদ", chword="পুস্তক", groupword="অধ্যায়",
    src=("বাংলা পাঠ — ebanglalibrary.com («বাংলা বাইবেল»); ইংরেজি পাশে — "
         "The New American Bible, vatican.va। উৎসে যে পদ পাওয়া যায়নি তা অনুমান করে "
         "বসানো হয় না — সেগুলো রিপোর্টে নথিভুক্ত থাকে।"),
    excerpt="সৃষ্টি থেকে নতুন নিয়ম পর্যন্ত — পুস্তক, অধ্যায় ও পদ-নম্বরসহ সম্পূর্ণ বাংলা পাঠ।")

BOOKS["yajurveda-shukla"] = dict(
    kind="veda", title=("শুক্ল যজুর্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · শুক্ল যজুর্বেদ", crumb="শুক্ল যজুর্বেদ সংহিতা",
    intro="শুক্ল যজুর্বেদের বাংলা অনুবাদ — দুর্গাদাস লাহিড়ী (ebanglalibrary.com)।",
    word="মন্ত্র", chword="অধ্যায়",
    # সতর্কতা: এই সংস্করণে সংস্কৃত মূল পাঠ নেই, তাই «মূল পাঠ» দাবি করা যাবে না
    src="বাংলা অনুবাদ — দুর্গাদাস লাহিড়ী; ebanglalibrary.com থেকে সংগৃহীত।",
    excerpt="যজ্ঞের বিধি ও মন্ত্রের বেদ — শুক্ল শাখার বাংলা অনুবাদসহ।")
BOOKS["yajurveda-krishna"] = dict(
    kind="veda", title=("কৃষ্ণ যজুর্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · কৃষ্ণ যজুর্বেদ", crumb="কৃষ্ণ যজুর্বেদ সংহিতা",
    intro="কৃষ্ণ যজুর্বেদের বাংলা অনুবাদসহ পাঠ — ebanglalibrary.com।",
    word="মন্ত্র", chword="অধ্যায়",
    src="বাংলা অনুবাদ ebanglalibrary.com থেকে সংগৃহীত।",
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


def normalize(slug: str, html: str, sub: str = "hindu") -> str:
    """new/পুরোনো নির্বিশেষে প্রতিটি বানানো পাতায় একই head ও ফুটার।

    `sub` = grantho/-এর নিচে কোন ফোল্ডারে পাতাটি থাকে (হিন্দু গ্রন্থে "hindu",
    বাইবেলে "christian") — ক্যানোনিকাল ঠিকানা এর ওপরেই দাঁড়ায়।
    """
    href = f"{SITE}/grantho/{sub}/{slug}.html"
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
    # ১.৫) শেয়ার-ট্যাগের শিরোনাম/বিবরণ সবসময় নিজের পাতার <title>/description থেকেই।
    #      পুরোনো টেমপ্লেট থেকে «Ebrahim Ead সম্পর্কে» কপি হয়ে শেয়ার-প্রিভিউতে
    #      ভুল শিরোনাম যেত — রি-বিল্ডেও যেন না ফেরে।
    _t = re.search(r"<title>(.*?)</title>", html, re.S)
    _d = re.search(r'<meta name="description" content="([^"]*)"', html)
    if _t:
        _title, _desc = _t.group(1).strip(), (_d.group(1) if _d else "")
        for _attr in ("property", "name"):
            html = re.sub(rf'(<meta {_attr}="og:title" content=")[^"]*(")',
                          lambda m, v=_title: m.group(1) + v + m.group(2), html, count=1)
            html = re.sub(rf'(<meta {_attr}="twitter:title" content=")[^"]*(")',
                          lambda m, v=_title: m.group(1) + v + m.group(2), html, count=1)
        html = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                      lambda m, v=_desc: m.group(1) + v + m.group(2), html, count=1)
        html = re.sub(r'(<meta name="twitter:description" content=")[^"]*(")',
                      lambda m, v=_desc: m.group(1) + v + m.group(2), html, count=1)
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


def _apply_identity(h, slug, meta, main, sub):
    """পাতার নিজস্ব পরিচয় বসানো — টেমপ্লেট যেকোনো গ্রন্থের পাতাই হোক।

    আগে এখানে হার্ডকোডেড "সামবেদ …" স্ট্রিং বদলানো হতো; কিন্তু _pick_template()
    samaveda.html না পেয়ে rigveda.html ফলব্যাক করায় সেই বদলিগুলো মিলত না — ফলে
    শুক্ল যজুর্বেদের পাতায় data-base ঋগ্বেদের ফোল্ডারেই থেকে গিয়েছিল এবং
    পাঠকে ঋগ্বেদের মন্ত্র দেখাত। তাই সব বদলি এখন রেগেক্স-ভিত্তিক।
    """
    label = f"{main} {sub}".strip()
    crumb = meta.get("crumb") or label
    # ডেটা-উৎস: রিডার-JS এখান থেকেই গ্রন্থের ফোল্ডার ধরে — এটি ভুল হলে অন্য গ্রন্থের পাঠ দেখায়
    h = re.sub(r'data-granth="[^"]*"', f'data-granth="{slug}"', h, count=1)
    h = re.sub(r'data-base="[^"]*"', f'data-base="../../assets/grantho/data/{slug}/"', h, count=1)
    # কিকার (g-kicker / g-kicker2 দুই রূপই টেমপ্লেটে থাকতে পারে)
    if meta.get("kicker"):
        h = re.sub(r'(<span class="g-kicker2?">)[^<]*(</span>)',
                   lambda m: m.group(1) + meta["kicker"] + m.group(2), h)
    # শিরোনাম <h1> (অ্যাট্রিবিউট থাকলেও অটুট রাখা হয়)
    inner = f"{main} <span>{sub}</span>" if sub else main
    h = re.sub(r'(<h1[^>]*>).*?(</h1>)', lambda m: m.group(1) + inner + m.group(2),
               h, count=1, flags=re.S)
    # ব্রেডক্রাম্ব: «ধর্মীয় গ্রন্থ › হিন্দু ›» অংশ অটুট রেখে হাব-লিংক ও গ্রন্থের নাম বদলানো
    cm = re.search(r'(<p class="g-crumb">)(.*?)(</p>)', h, re.S)
    if cm:
        mid = cm.group(2)
        anchors = list(re.finditer(r'<a href="[^"]*"[^>]*>.*?</a>', mid, re.S))
        if anchors:
            last = anchors[-1]
            hub = f'<a href="{meta["hub"]}">{meta["hubname"]}</a>'
            mid = mid[:last.start()] + hub + mid[last.end():]
        if meta.get("crumbDrop"):
            # টেমপ্লেট হিন্দু পাতার, তাই ক্রাম্বে «হিন্দু» অ্যাংকর থেকে যায় —
            # অন্য ধর্মের পাতায় সেটি ভুল পরিচয়, তাই অ্যাংকর+বিভাজকসহ বাদ।
            for a in list(re.finditer(r'<a href="[^"]*"[^>]*>.*?</a>\s*(?:<span>›</span>)?',
                                      mid, re.S)):
                if meta["crumbDrop"] in a.group(0):
                    mid = mid[:a.start()] + mid[a.end():]
                    break
        sep = '<span>›</span>'
        k = mid.rfind(sep)
        if k >= 0:
            mid = mid[:k + len(sep)] + crumb
        h = h[:cm.start()] + cm.group(1) + mid + cm.group(3) + h[cm.end():]
    # টেমপ্লেটের অন্য গ্রন্থের নাম শিরোনাম-জুড়ে ছড়িয়ে থাকলে তাও বদলানো
    h = h.replace("সামবেদ সংহিতা", label).replace("ঋগ্বেদ সংহিতা", label)
    return h


def make_page(slug, idx, meta):
    main, sub = meta["title"]
    outdir = OUT.parent / meta.get("dir", "hindu")   # হিন্দু বা খ্রিস্টান ফোল্ডার
    nch = len(idx["chapters"])
    total, withbn = idx["total"], idx.get("withBn", 0)
    withsk = count_with_sk(slug, idx)
    h = TEMPLATE

    h = _apply_identity(h, slug, meta, main, sub)
    h = re.sub(r'(<div class="g-intro">.*?<p>)[^<]*(</p>)',
               lambda m: m.group(1) + meta["intro"] + m.group(2), h, count=1, flags=re.S)

    facts = f'<span class="g-fact"><b>{commas(withbn)}</b> {meta["word"]} (বাংলাসহ)</span>'
    if total != withbn:
        facts += f'<span class="g-fact"><b>{commas(total)}</b> মোট {meta["word"]}</span>'
    facts += f'<span class="g-fact"><b>{commas(nch)}</b> {meta["chword"]}</span>'
    nsuk = idx.get("suktaTotal") or sum(c.get("suktaCount", 0) for c in idx["chapters"])
    nshl = idx.get("shlokaTotal") or sum(c.get("shlokaCount", 0) for c in idx["chapters"])
    if nsuk:
        # ঋগ্বেদে «সূক্ত», বাইবেলে «অধ্যায়» — ডেটার groupWord থেকে
        gw = idx.get("groupWord") or meta.get("groupword") or "সূক্ত"
        facts += f'<span class="g-fact"><b>{commas(nsuk)}</b> {gw}</span>'
    if nshl:
        facts += f'<span class="g-fact"><b>{commas(nshl)}</b> শ্লোক</span>'
    # ইংরেজি অনুবাদ (বাইবেল): কত পদে মিলেছে তা ডেটা থেকেই
    enj = OUT / slug / "en" / "joined.json"
    en_n = 0
    if enj.exists():
        en_n = json.loads(enj.read_text(encoding="utf-8")).get("enVerses", 0)
    if en_n:
        facts += f'<span class="g-fact"><b>{commas(en_n)}</b> পদে ইংরেজি</span>'
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
    # সব খণ্ডেই বাংলা অনুবাদ থাকলে «কেবল যেগুলোর অনুবাদ আছে» ছাঁকনিটি অকেজো —
    # অথচ বোতামটি দেখলে মনে হয় কিছু পাঠ বাদ পড়ছে। তাই তখন মার্কআপই বাদ দেওয়া হয়
    # (grantho.js-ও রানটাইমে একই কাজ করে, যাতে পুরোনো পাতাতেও ঠিক থাকে)।
    if withbn and withbn >= total:
        h = re.sub(r'\s*<label[^>]*>\s*<input[^>]*id="g-only-bn"[^>]*>[^<]*</label>',
                   '', h, count=1, flags=re.S)

    # রিডারের নতুন গঠন (পুস্তক → অধ্যায় → পদ): টেমপ্লেটে ব্লকগুলো হাতে বসানো
    # থাকে, কিন্তু গ্রুপ-তথ্য (testament/অধ্যায়-সংখ্যা/ইংরেজি-কভারেজ) ডেটা
    # থেকে এখানেই বসানো হয় — পুরোনো টেমপ্লেটেও কার্যকর।
    # প্যানেলের শিরোনাম ডেটার chword থেকেই («পুস্তক») — হার্ডকোডেড «অধ্যায়» ভুল ছিল
    if meta.get("kind") == "bible":
        h = h.replace('<b id="g-side-title">অধ্যায়</b>',
                      f'<b id="g-side-title">{meta.get("chword") or "পুস্তক"}</b>')
        # প্যানেলের id — ভাঁজ-নিয়ন্ত্রণ ও স্ক্রলযোগ্য বডি এর ওপরেই দাঁড়িয়ে
        h = h.replace('<aside class="g-side">', '<aside class="g-side" id="g-side">', 1)
    if meta.get("kind") == "bible" and 'id="g-book-list"' not in h:
        # পুরোনো টেমপ্লেটে কেবল খণ্ড-তালিকা ছিল — নতুন স্তরগুলোর কনটেইনার বসাই,
        # সাথে মোবাইলে ভাঁজ-বোতাম ও গুটিয়ে রাখা যায় এমন বডি।
        # হেডে আর কিছু নয়: বাঁয়ে পুস্তকের শব্দ (এটিই ভাঁজ-বোতাম), ডানে
        # বড় করে «তালিকা»। আগের «অধ্যায় / ৪৬ পুস্তক · ২৪,০৮৭ পদ» ফোনের
        # মোটা লাইনে জায়গা নিত, আর সহজে চোখেও পড়ত না।
        _HEAD = ('<div class="g-side-head">'
                 '<button class="g-side-toggle" id="g-side-toggle" type="button" '
                 'aria-expanded="true" aria-controls="g-side-body">'
                 '<b id="g-side-title">পুস্তক</b>'
                 '<span class="g-side-word">তালিকা '
                 '<span class="g-side-chev" aria-hidden="true"></span></span>'
                 '</button></div>')
        # পুরো হেড-div একবারে বদলাই (পুরোনো গঠনে ভেতরে «অধ্যায়»+গণনা ছিল,
        # তাই শুধু বোতাম বসিয়ে দিলে ওই দুটো বাইরে পড়ে থাকত)।
        h, n = re.subn(r'<div class="g-side-head">.*?</div>', _HEAD, h, count=1, flags=re.S)
        if not n:
            # হেড-div না থাকলে তালিকার গোড়ায় বসাই
            h = h.replace('<div id="g-book-list">', _HEAD + '<div id="g-book-list">', 1)

        h = h.replace('<div id="g-chapter-list"></div>',
                      '<div class="g-side-now" id="g-side-now" aria-live="polite"></div>'
                      '<div class="g-side-body" id="g-side-body">'
                      '<div id="g-testament" class="g-tset" role="group" '
                      'aria-label="নিয়ম" hidden></div>'
                      '<div id="g-book-list"></div>'
                      '<div id="g-chapter-list" hidden></div>'
                      '</div>', 1)
        h = h.replace('<div id="g-bn-note"',
                      '<div id="g-crumb2" class="g-crumb2" hidden></div>'
                      '<div id="g-chapter-grid" class="g-chgrid" role="group" '
                      'aria-label="অধ্যায়"></div>'
                      '<div id="g-en-note" class="g-en-note" hidden></div>'
                      '<div id="g-bn-note"', 1)

    src = meta["src"]
    # সংস্কৃত পাঠের প্রাপ্যতা — আগে হার্ডকোডেড দাবি ছিল যা ডেটার সাথে মিলত না।
    # বাইবেলের ক্ষেত্রে এই টীকা অর্থহীন (সেখানে সংস্কৃতের প্রশ্নই নেই)।
    if meta.get("kind") == "bible":
        pass
    elif withsk == 0:
        src += (f' এই সংস্করণে সংস্কৃত মূল পাঠ ছাপা হয়নি, তাই {meta["word"]}ে কেবল বাংলা অনুবাদ আছে'
                ' — কোনো অনুমানভিত্তিক সংস্কৃত পাঠ বসানো হয় না।')
    elif withsk < total:
        src += (f' সংস্কৃত মূল পাঠ আংশিক — {commas(total)}টি {meta["word"]}ের মধ্যে কেবল {commas(withsk)}টিতে'
                f' উৎসে সংস্কৃত পাওয়া গেছে, সেগুলোতেই তা ছাপা হয়েছে; বাকিগুলোতে কেবল বাংলা অনুবাদ আছে।'
                ' কোনো অনুমানভিত্তিক সংস্কৃত পাঠ বসানো হয় না।')
    if withbn < total:
        src += (f' {commas(total - withbn)}টি {meta["word"]}র বাংলা পাঠ উৎসে পাওয়া যায়নি'
                ' — সংখ্যাটি গোনা আছে, পাঠ বসানো হয়নি')
        # উপরের বাক্যে হাজার-কমা + «পদ»র যোগ হয়ে দাঁড়াত «৩৫১টি পদর» —
        # বিশুদ্ধ বানান রক্ষা: meta["word"]-এর পরে সরাসরি «র» নয়, মিলিয়ে।
        src = re.sub(re.escape(meta["word"]) + r"র বাংলা পাঠ",
                     meta["word"] + "ের বাংলা পাঠ", src)
    if idx.get("note"):   # ডেটার টীকা সবার শেষে (আগে দুবার যোগ হতো)
        src += " " + idx["note"]
    if en_n:
        src += (" ইংরেজি অনুবাদ: The New American Bible — vatican.va। যেসব অধ্যায়ে বাংলার সঙ্গে "
                "পদ-সংখ্যা ও পদ-নম্বর হুবহু মিলেছে, সেখানেই ইংরেজি দেখানো হয়; যে অধ্যায়ে দুই "
                "সংস্করণের পদ-বিন্যাস আলাদা, সেখানে ইংরেজি বাদ রাখা হয়েছে (অনুমান করে বসানো হয় না)।")
    h = re.sub(r'<div class="g-src"><b>পাঠ সম্পর্কে।</b>.*?</div>',
               f'<div class="g-src"><b>পাঠ সম্পর্কে।</b> {src}</div>', h, count=1, flags=re.S)

    label = f"{main} {sub}".strip()
    fulldesc = f'{label}-র {commas(withbn)}টি {meta["word"]} বাংলা অনুবাদসহ — ebanglalibrary.com।'
    # সতর্কতা: দশার-অভাবে হঠাৎ বড় পতন (যেমন ৯২২২ → ২১ শ্লোক) সাইটে বসিয়ে দেব না।
    env = os.environ.get("GRANTHO_ALLOW_SHRINK", "").strip().lower() in ("1", "true", "yes")
    if not env and (outdir / f"{slug}.html").exists():
        old_html = (outdir / f"{slug}.html").read_text(encoding="utf-8")
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
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{slug}.html").write_text(
        normalize(slug, h, meta.get("dir", "hindu")), encoding="utf-8")
    return dict(slug=slug, total=total, withbn=withbn, nch=nch)


def refresh_sitemap(entries):
    """বানানো পাতাগুলোর ঠিকানা sitemap.xml-এ আছে কি না দেখে, না থাকলে যোগ।

    কেন: সাইটম্যাপ হাতে রাখা হয়, তাই নতুন গ্রন্থ-পাতা (যেমন বাইবেল) যোগ হলে
    সেটি বাদ পড়ে যেত — সার্চ-ইঞ্জিন তখন পাতাটি খুঁজে পেত না।
    """
    f = ROOT / "sitemap.xml"
    if not f.exists():
        return 0
    s = f.read_text(encoding="utf-8")
    added = 0
    for slug, sub in entries:
        url = f"{SITE}/grantho/{sub}/{slug}.html"
        if url in s:
            continue
        # বিদ্যমান এন্ট্রির সাথে একই ফরম্যাট (এক লাইনে, lastmod সহ)
        today = datetime.date.today().isoformat()
        block = (f'  <url><loc>{url}</loc><lastmod>{today}</lastmod>'
                 f'<changefreq>weekly</changefreq><priority>0.7</priority></url>\n')
        s = s.replace("</urlset>", block + "</urlset>", 1)
        added += 1
    if added:
        f.write_text(s, encoding="utf-8")
        print(f"  সাইটম্যাপে যোগ: {added}টি পাতা")
    return added


def card(href, kicker, title, sub, excerpt="", soon=False):
    """হাবের কার্ড — ছোট, শুধু নাম আর এক লাইনের হিসাব।

    কেন: আগে প্রতিটি কার্ডে ট্যাগ, বড় শিরোনাম, দুই লাইনের বিবরণ আর
    «পড়ুন →» বাটন ছিল — ফোনে ইসলামের ভেতরে কুরআন/হাদিস দেখতে অনেক
    স্ক্রল করতে হত। এখন ট্যাগ ও বড় বিবরণ বাদ (`excerpt` আর ব্যবহার হয়
    না, শুধু interface মিলিয়ে রাখতে আছে); নামের নিচে ছোট মিউটেড লাইনে
    সংখ্যা (`sub`), ডানে সরু তির।
    """
    if soon:
        return (f'<article class="article-card rv cmp-card is-soon">'
                f'<a class="article-card-link" href="#" aria-disabled="true" tabindex="-1">'
                f'<span class="cmp-body"><h2 class="cmp-title">{title}</h2>'
                f'<span class="cmp-meta">{sub}</span></span>'
                f'<span class="cmp-go" aria-hidden="true">→</span></a></article>')
    return (f'<article class="article-card rv cmp-card">'
            f'<a class="article-card-link" href="{href}">'
            f'<span class="cmp-body"><h2 class="cmp-title">{title}</h2>'
            f'<span class="cmp-meta">{sub}</span></span>'
            f'<span class="cmp-go" aria-hidden="true">→</span></a></article>')


def replace_grid(page, inner, sub="hindu"):
    p = (OUT if sub == "hindu" else OUT.parent / sub) / page
    if not p.exists():
        print("  (পাতা নেই)", page)
        return
    s = p.read_text(encoding="utf-8")
    # গ্রিডের শেষে সব পাতায় g-note/g-back থাকে না (হিন্দু-হাবে নেই) —
    # তাই ওগুলো থাকলে সেখানেই থামি, নাহলে বন্ধ-ট্যাগের আগেই।
    m = re.search(r'<div class="g-grid">.*?</div>\s*(?=<div class="g-note"|<a class="g-back"|</section>|</main>)',
                  s, re.S)
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
            # «বাংলা অনুবাদসহ» বাদ: কার্ড ছোট রাখার চাহিদা — সংখ্যাটাই যথেষ্ট
            grid += card(f"{slug}.html", k, t,
                         f'{commas(r["withbn"])} {m["word"]} · {commas(r["nch"])} {m["chword"]}',
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

    # ---- হিন্দু-হাব: কার্ডগুলো ডেটা থেকেই বানাই
    #   আগে এই পাতা হাতে লেখা কার্ড ধরে সংখ্যা আপডেট করত, ফলে কার্ডের
    #   গঠন (বড় বিবরণ/বাটন) বদলাতে গেলে হাতে-এডিট ছাড়া উপায় ছিল না —
    #   রি-বিল্ডে সেটা ফিরেও যেত। এখন বেদের মতোই replace_grid দিয়ে তৈরি।
    if made or puranas or upa_cards:
        hp_cards = ""
        g = load("gita")
        if g:
            hp_cards += card("hindu/gita.html", "হিন্দু · গীতা", "শ্রীমদ্ভগবদ্গীতা",
                             f'{commas(g["withBn"])} শ্লোক · {commas(len(g["chapters"]))} অধ্যায়')
        rv = next((r for sl, r, _ in vedas if sl == "rigveda"), None)
        if rv:
            hp_cards += card("hindu/rigveda.html", "হিন্দু · বেদ", "ঋগ্বেদ সংহিতা",
                             f'{commas(rv["withbn"])} মন্ত্র · {commas(rv["nch"])} মণ্ডল')
        yv = next((r for sl, r, _ in vedas if sl == "yajurveda-shukla"), None)
        if yv:
            hp_cards += card("hindu/yajurveda-shukla.html", "হিন্দু · বেদ", "শুক্ল যজুর্বেদ সংহিতা",
                             f'{commas(yv["withbn"])} মন্ত্র · {commas(yv["nch"])} অধ্যায়')
        if hp_cards:
            replace_grid("hindu.html", hp_cards, sub="")
        print("হিন্দু-হাব:", sum(r["withbn"] for _, r, _ in vedas), "/",
              sum(r["withbn"] for _, r, _ in puranas))

    # ---- ইসলাম-হাব: কুরআন ও হাদিসের কার্ড (হাতে লেখা নয়)
    #   সংখ্যা ডেটা থেকেই — পাঠ বাড়লে/কমলে কার্ড নিজেই ঠিক হয়।
    isl = ""
    qf = ROOT / "assets/quran/data/index.json"
    hf = ROOT / "assets/hadith/data/index.json"
    if qf.exists():
        q = json.loads(qf.read_text(encoding="utf-8"))
        n_sura = len(q.get("suras") or [])
        isl += card("../quran.html", "ইসলাম · কুরআন", "আল-কুরআনুল কারীম",
                    f'{commas(n_sura)} সূরা · {commas(q.get("total") or 0)} আয়াত')
    if hf.exists():
        h = json.loads(hf.read_text(encoding="utf-8"))
        isl += card("../hadith.html", "ইসলাম · হাদিস", "হাদিস",
                    f'সিহাহ সিত্তাহ — {commas(h.get("total") or 0)} হাদিস')
    if isl:
        replace_grid("islam.html", isl, sub="")
        print("ইসলাম-হাব: কার্ড তৈরি")

    # ---- বৌদ্ধ-হাব: পাঠ এখনো নেই, তবু কার্ডটাও একই ছোট গঠনে
    replace_grid("buddhist.html",
                 card("", "বৌদ্ধ · গ্রন্থ", "ত্রিপিটক ও বৌদ্ধ সাহিত্য",
                      "ধাপে ধাপে যোগ হচ্ছে", soon=True), sub="")

    # ---- খ্রিস্টান: বাংলা বাইবেল
    built = [(r["slug"], "hindu") for r in made]
    if "bible" in ACTIVE:
        idx = load("bible")
        meta = BOOKS.get("bible")
        if idx and meta:
            r = make_page("bible", idx, meta)
            if r:
                built.append(("bible", "christian"))
                chs = idx["chapters"]
                old = sum(1 for c in chs if c.get("testament") == "old")
                part = sum(1 for c in chs if c.get("missing"))
                # কার্ড ছোট রাখার চাহিদা — নিয়ম-ভাগ বাদ, শুধু পদ/পুস্তক/অধ্যায়
                sub = f'{commas(r["withbn"])} পদ · {commas(r["nch"])} পুস্তক'
                replace_grid("christian.html",
                             card("christian/bible.html", "খ্রিস্টান · বাইবেল",
                                  "বাংলা বাইবেল", sub, meta["excerpt"]), sub="")
                print(f"bible: {r['withbn']}/{r['total']} · {r['nch']} পুস্তক · "
                      f"{idx.get('suktaTotal') or sum(c.get('suktaCount', 0) for c in chs)} অধ্যায়")
    refresh_sitemap(built)
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
