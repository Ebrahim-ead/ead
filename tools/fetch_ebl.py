#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ebanglalibrary.com — বাংলা বেদ/উপনিষদ/পুরাণ ব্যাচ-ডাউনলোডার।

কেন এটা: সাইটের টপিক/লেসন স্লাগ WP কেটে ফেলে (৫০ অক্ষরে), তাই URL আন্দাজ করা
চলে না। বদলে সাইটম্যাপ (wp-sitemap-posts-sfwd-topic-N.xml / sfwd-lessons-N.xml)
থেকে সব URL এনে কীওয়ার্ড মিলিয়ে নামানো হয়। সব পাতা লগইন ছাড়াই খোলা।

পাতার গঠন (যাচাই করা):
    ### পঞ্চম খণ্ড – শিরোনাম
    ৪৬৯. <সংস্কৃত শ্লোক> ॥ ১॥
    অন্বয় : ...
    সরলার্থ : <বাংলা>        ← bn
    মন্তব্য : <টীকা>          ← bnNote

বিধি:
    --discover ছান্দোগ্য          → কেবল URL-তালিকা দেখাও
    --slug chandogya --match ছান্দোগ্য --by-ordinal   → অধ্যায়-ক্রমে নামাও
    --slug bhabishya --match "ভবিষ্য পুরাণ" --chain    → «Next Lesson» ধরে ক্রমে নামাও
    --dump 2                      → প্রথম ২ পাতার কাঁচা পাঠ _debug/ তে রাখো
    --auto                         → কাঠামো নিজেই ঠিক করে এক রানে সব নামায়
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.ebanglalibrary.com"
UA = "Mozilla/5.0 (compatible; ead-grantho/1.0; +https://github.com/Ebrahim-ead/ead)"
SRC = "বাংলা অনুবাদ — ebanglalibrary.com"

TOPIC_SITEMAPS = [f"{BASE}/wp-sitemap-posts-sfwd-topic-{i}.xml" for i in range(1, 17)]
LESSON_SITEMAPS = [f"{BASE}/wp-sitemap-posts-sfwd-lessons-{i}.xml" for i in range(1, 30)]
COURSE_SITEMAPS = [f"{BASE}/wp-sitemap-posts-sfwd-courses-{i}.xml" for i in range(1, 6)]

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
DEV_RE = re.compile("[\u0900-\u0963\u0966-\u0970\u0971-\u097F]")  # দাঁড়ি/॥ বাদ
DEV_DIGITS = "०१२३४५६७८९"
ORD = {"প্রথম": 1, "দ্বিতীয়": 2, "দ্বিতীয়ো": 2, "তৃতীয়": 3, "চতুর্থ": 4,
       "পঞ্চম": 5, "ষষ্ঠ": 6, "সপ্তম": 7, "অষ্টম": 8, "নবম": 9, "দশম": 10,
       "একাদশ": 11, "দ্বাদশ": 12}
NUM_LINE = re.compile(r"^([০-৯]{1,3})\s*[\.।]\s*(.*)$")
MARK = re.compile("[।॥]{2}\\s*([\u09e6-\u09ef\u0966-\u096f]{1,3})\\s*[।॥]{2}")
TAIL_MARK = re.compile("[।॥]{1,2}\\s*([\u09e6-\u09ef\u0966-\u096f]{1,3})\\s*[।॥]{0,2}\\s*$")


def to_int(s):
    s = str(s).strip()
    if not s:
        return None
    if all(c in BN_DIGITS for c in s):
        return int("".join(str(BN_DIGITS.index(c)) for c in s))
    if all(c in DEV_DIGITS for c in s):
        return int("".join(str(DEV_DIGITS.index(c)) for c in s))
    try:
        return int(s)
    except Exception:
        return None


_CACHE = {}


def safe_url(u):
    """URL-এ বাংলা/দেবনাগরী থাকলে percent-encode করি (http.client ASCII চায়)।"""
    if not u:
        return u
    parts = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((
        parts.scheme or "https", parts.netloc,
        urllib.parse.quote(parts.path, safe="/%"),
        urllib.parse.quote_plus(parts.query, safe="=&%") if parts.query else "",
        ""))


_DOWN = {"n": 0}
_ALL = []          # এই রানে সাইটম্যাপে দেখা সব URL


def get(url, tries=4, timeout=60):
    url = safe_url(url)
    if url in _CACHE:
        return _CACHE[url]
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "bn,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read().decode("utf-8", "replace")
                _CACHE[url] = data
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (403, 429, 503):
                _DOWN["n"] += 1          # সাইট ব্লক/লোড — বেশিবার হলে থামি
            print(f"   ! HTTP {e.code} — {url[-50:]} (চেষ্টা {i+1})")
            time.sleep(min(30, 4 * (i + 1)))
        except Exception as e:
            # URLError বেশিরভাগ সময় সাময়িক নেটওয়ার্ক-ঝাঁকুনি; পুরো সীমা
            # একে দিয়ে ভরালে ভালো রানও মাঝপথে থেমে যেত (২০২৬-১১-০৫-এ তাই
            # হয়েছে)। তাই আসল সাইট-ব্যর্থতার (403/429/503) সীমা আলাদা।
            print(f"   ! {type(e).__name__} — {url[-50:]} (চেষ্টা {i+1})")
            time.sleep(min(30, 4 * (i + 1)))
        if _DOWN["n"] >= 60:
            print("\n⛔ উৎস সাইট বারবার ব্যর্থ (৬০ বার) — এই রান থামানো হলো "
                  "যাতে ঘণ্টার পর ঘণ্টা নষ্ট না হয়।", flush=True)
            raise SystemExit(4)
    return None


# ---------------- পাঠ নিষ্কাশন ----------------
def text_of(frag):
    s = re.sub(r"<script.*?</script>", " ", frag, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<h[1-6][^>]*>", "\n\n## ", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    for a, b in (("\u00a0", " "), ("\u200b", ""), ("\ufeff", ""), ("\\[", "["),
                 ("\\]", "]"), ("\\", "")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t]+", " ", s)
    s = "\n".join(x.strip() for x in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def page_text(h):
    if not h:
        return ""
    m = re.search(r"<h1[^>]*>.*?</h1>", h, flags=re.S | re.I)
    if m:
        h = h[m.end():]
    # book/lesson-এর পাশের সূচি-ব্লক বাদ
    cut = min([i for i in (h.find('id="ld-lesson-toc'), h.find("Bookmark"),
                           h.find("Post a comment")) if i > 500] or [len(h)])
    h = h[:cut]
    txt = text_of(h)
    out = []
    for ln in txt.split("\n"):
        low = ln.lower()
        if not ln:
            continue
        if low.startswith(("skip to", "menu", "search", "লাইব্রেরি »", "home »",
                           "continue with", "username", "password", "register",
                           "accessing this", "table of contents", "expand",
                           "previous lesson", "next lesson", "back to book")):
            continue
        out.append(ln)
    return "\n".join(out)



BN2DEV = str.maketrans(
    "অআইঈউঊঋএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহািীুূৃেৈোৌ্ংঃয়ড়ঢ়ৎ",
    "अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलशषसहािीुूृेैोौ्ंःयड़ढ़त्")



def to_devanagari(line):
    """বাংলা অক্ষরে ছাপা সংস্কৃত শ্লোক → দেবনাগরী (সাদৃশ্য-মানচিত্র)।"""
    if not line or DEV_RE.search(line):
        return line
    bn_letters = sum(1 for c in line if "\u0980" <= c <= "\u09FF")
    if bn_letters < 8:
        return line
    return line.translate(BN2DEV)

VERSE_TAIL = re.compile(r"[॥|৷]{1,2}\s*([০-৯०-९]{1,3})\s*[॥|]{0,2}\s*$")
NUMHEAD = re.compile(r"^([০-৯0-9]{1,3})\s*[।\.]\s*(.+)$")
# «১.» / «১২.» / «৭।» — মন্ত্র-ক্রমের সূচক; ইংরেজি ফুলস্টপও চলে
_NUM_SEG = re.compile(r"^[০-৯0-9]{1,3}\s*[।\.]\s*\S")
_NUM_SEG_FULL = re.compile(r"^([০-৯0-9]{1,3})\s*[।\.]\s*(\S.*)$")
_FOOTNOTE = re.compile(r"^\(\s*[০-৯0-9]{1,3}\s*\)")
_DIVIDER = re.compile(r"[—–\-\s]{3,}")
LBL = re.compile(r"^(অন্বয়|সরলার্থ|বঙ্গানুবাদ|অনুবাদ|মন্তব্য|ভাষ্য|টীকা|"
                   r"সূক্তস্য\s*বিনিয়োগ|ব্যাখ্যা)\s*[:ঃ।\-–—]*\s*")
# পাদটীকা-শিরোনাম: «মন্ত্রের দেবতা», «মন্ত্রের ছন্দ», «মন্ত্রের ঋষি», «স্বর :» ইত্যাদি
# সামবেদের পাতা-শিরোনাম — «সামবেদ ০১।০১ (প্রথম অধ্যায় । প্রথম খণ্ড : …)»,
# «প্রথম খণ্ড : মন্ত্র সংখ্যা ১০ ॥», «আগ্নেয় কাণ্ডঃ অগ্নিস্তুতি» ইত্যাদি।
# এগুলোতে দাঁড়ি থাকে, তাই is_heading মেলে না — আর তখন ভুয়া মন্ত্র তৈরি হয়
# (আর তার জেরে মন্ত্র/অর্থ জোড়া এক ধাপ সরে যায়)।
_HEAD_TEXT = re.compile(
    r"^(?:সামবেদ\s*[০-৯]{1,2}\s*।\s*[০-৯]{1,2}\b"
    r"|[^।॥]{0,40}খণ্ড\s*[:ঃ]\s*মন্ত্র\s*সংখ্যা"
    r"|(?:প্রথম|দ্বিতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম)\s*"
    r"(?:অধ্যায়|খণ্ড)\s*[:ঃ]"
    r"|[^।॥]{0,30}কাণ্ড\s*[:ঃ]\s*[^।॥]{0,30}$"
    r"|পুর্বার্চিক|উত্তরার্চিক)")
_META_LINE = re.compile(r"^(?:মন্ত্রের?\s*(?:দেবতা|ছন্দ|ঋষি|স্বর|সংখ্যা)|স্বর\s*[:ঃ]|"
                        r"দেবতা\s*[:ঃ]|ঋষি\s*[:ঃ]|ছন্দ\s*[:ঃ]|"
                        # «দেবতা অগ্নি ॥ ছন্দ গায়ত্রী ॥» — কোলন ছাড়া ধাঁচ
                        # (এটাই ভুয়া মন্ত্র বানিয়ে সব নম্বর এক ধাপ সরিয়ে দিত)
                        r"দেবতা\s+|ছন্দ\s+|ঋষি\s*[:ঃ]?\s*[০-৯0-9])")
# «মন্ত্র :» / «মন্ত্রঃ-» / «মন্ত্র-» — কিন্তু «মন্ত্রের দেবতা», «মন্ত্রসংখ্যা» নয়।
# কোলন/হাইফেন/ফাঁকা কোনোটাই না থাকলে সেটা শিরোনাম-লাইন, মন্ত্রের পাঠ নয়।
MTRA = re.compile(r"^মন্ত্র\s*(?:[:ঃ]\s*[\-–—]*|[\-–—]|\s)\s*")
# «অর্থঃ-» (অধ্যায় ১–২) এবং «অনুবাদঃ» (অধ্যায় ৩+) — দুটোই অনুবাদ-লেবেল;
# তৃতীয় দফায় মন্ত্র-অনুবাদ একসাথে এক প্যারায়, নম্বর ধরে ভাগ করতে হয়।
ARTH = re.compile(r"^(?:অর্থ|অনুবাদ)\s*[:ঃ]\s*[\-–—]*\s*|^(?:অর্থ|অনুবাদ)\s*[\-–—]\s*")
BN_VERB = re.compile(r"হয়|করে|থেকে|জন্য|এবং|উচিত|বললেন|গেল|মধ্যে|দ্বারা|"
                     r"তিনি|তাঁর|ব্যক্তি|হইয়া|করি|নহে|হবে|ছিল|আছে|নাই")


def _is_bn_verse(p):
    """বাংলা অক্ষরে ছাপা সংস্কৃত শ্লোক (ক্রিয়াপদহীন, দাঁড়ি-নম্বর-শেষ)।"""
    if not VERSE_TAIL.search(p):
        return False
    if len(p) > 320 or len(p.split()) < 3:
        return False
    return not BN_VERB.search(p)


BN_STOP = re.compile(r"হয়|হইয়া|করে|করা|থেকে|জন্য|এবং|কিন্তু|কারণ|অর্থাৎ|"
                       r"বলে|হচ্ছে|হলো|তিনি|তাঁর|এই|সেই|নয়|হবে|আছে|ছিল|"
                       r"মাধ্যমে|সাহায্যে|উদ্দেশ্যে|প্রতি।|বলেছেন|করেছেন")


def looks_sanskrit(ln):
    """বাংলা অক্ষরে ছাপা সংস্কৃত শ্লোক-লাইন? (দাঁড়ি আছে, বাংলা ক্রিয়াপদ নেই)"""
    if not ln or len(ln) > 170:
        return False
    if not re.search(r"[।॥]", ln):
        return False
    return not BN_STOP.search(ln)


def is_heading(ln):
    """সূচি/শিরোনাম-জাতীয় ছোট লাইন (দাঁড়ি নেই, ক্রিয়াপদ নেই)।"""
    return len(ln) < 20 and not re.search(r"[।॥,]", ln)


_NUM_INLINE = re.compile(r"[(]\s*([০-৯0-9]{1,4})\s*[)]")

def _merge_to(segs, n):
    """বাক্য-খণ্ড n-এর বেশি হলে কাছাকাছি দৈর্ঘ্যে মিলিয়ে ঠিক n টুকরো করি।

    অনুবাদ-পরায় মন্ত্র-সংখ্যা না থাকলে ভরসা একমাত্র দাঁড়ি; কিন্তু এক
    মন্ত্রে দুই-তিন বাক্য থাকতে পারে। তাই সমান-ভাগে মিলিয়ে নিই — উৎসের
    পাঠ অক্ষত থাকে, কেবল মন্ত্রের সীমানা অনুমান করা হয়।
    """
    if n <= 0:
        return segs
    total = sum(len(x) for x in segs)
    out, acc, cur = [], 0, []
    for x in segs:
        acc += len(x)
        cur.append(x)
        if len(out) < n - 1 and acc >= total * (len(out) + 1) / n:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    while len(out) > n:              # শেষের দুটো জুড়ে দিই
        out[-2] = out[-2] + " " + out[-1]
        out.pop()
    return out
# উৎসের নিজের মন্ত্র-সংখ্যা (২৪৩) — এখানে সেটিই ক্রমের ভিত্তি
def _samaveda_numbered(txt):
    """«মন্ত্রঃ (২৪৩) … (২৪৪) …» + «অনুবাদঃ (২৪৩) …» গঠনের পাতা।

    উৎস-নম্বর (২৪৩) হলো রিগ্বেদ-সংখ্যা, ক্রম নয় — তাই পড়ার নম্বর
    প্রতি সুক্তে ১…n বসানো হয়, আর উৎস-নম্বর `seg` হিসেবে রাখা হয়।
    অনুবাদ-পরায় সংখ্যা না-থাকলে বাংলা ক্রিয়াপদ দেখে নতুন মন্ত্র ধরা হয়,
    নইলে দুই মন্ত্রের অনুবাদ জোড়া লেগে যায়।
    """
    def _lines(raw):
        out = []
        for ln in raw.split("\n"):
            ln = re.sub(r"\s+", " ", ln).strip()
            if ln:
                out.append(ln)
        return out

    lines = _lines(txt)
    sk_raw, bn_raw = [], []
    part = None
    for ln in lines:
        if re.match(r"^মন্ত্র\s*[:ঃ]", ln):
            part = "sk"
            ln = re.sub(r"^মন্ত্র\s*[:ঃ]\s*[\-–—]*\s*", "", ln)
        elif re.match(r"^(?:অনুবাদ|অর্থ)\s*[:ঃ]", ln):
            part = "bn"
            ln = re.sub(r"^(?:অনুবাদ|অর্থ)\s*[:ঃ]\s*[\-–—]*\s*", "", ln)
        elif _HEAD_TEXT.match(ln) or _META_LINE.match(ln):
            continue
        elif part is None:
            continue
        if not ln:
            continue
        if ln.startswith("#"):
            continue
        (sk_raw if part == "sk" else bn_raw).append(ln)

    sk_txt = " ".join(sk_raw)
    bn_txt = " ".join(bn_raw)
    if not sk_txt:
        return None

    # ---- সংস্কৃত: (নম্বর) ধরে ভাগ; দাঁড়ি-সংখ্যাই চূড়ান্ত (॥১॥ … ॥১০॥) ----
    idx = [(m.start(), m.group(1)) for m in _NUM_INLINE.finditer(sk_txt)]
    if not idx:
        return None
    sk_parts = []
    for i, (pos, num) in enumerate(idx):
        end = idx[i + 1][0] if i + 1 < len(idx) else len(sk_txt)
        body = sk_txt[pos:end].strip()
        body = re.sub(r"^[(]\s*[০-৯0-9]{1,4}\s*[)]\s*", "", body).strip()
        body = re.sub(r"\s*[।॥]\s*[০-৯0-9]{1,3}\s*$", "", body).strip()
        # উৎসের শেষ «॥৩॥» = রিগ্বেদ-ক্রম; আমাদের নিজের ১…n আছে ⇒ বাদ
        body = re.sub(r"\s*[|]?\s*[।॥]?\s*[০-৯0-9]{1,3}\s*[।॥]\s*$", "", body).strip()
        body = re.sub(r"\s*[|।॥]+\s*$", "", body).strip()
        if len(body) < 6 or body.lower().startswith("bookmark"):
            continue
        sk_parts.append({"src": num, "sk": body})

    # ---- অনুবাদ: (নম্বর) থাকলে তা দিয়েই; না থাকলে ক্রিয়াপদ-বিরতি ধরে ----
    bidx = [(m.start(), m.group(1)) for m in _NUM_INLINE.finditer(bn_txt)]
    bn_parts = []
    if len(bidx) >= max(3, len(sk_parts) // 2):
        for i, (pos, num) in enumerate(bidx):
            end = bidx[i + 1][0] if i + 1 < len(bidx) else len(bn_txt)
            body = bn_txt[pos:end].strip()
            body = re.sub(r"^[(]\s*[০-৯0-9]{1,4}\s*[)]\s*", "", body).strip()
            body = re.sub(r"\s*Bookmark\s*$", "", body, flags=re.I)
            body = re.sub(r"\s*[|।॥]+\s*$", "", body).strip()
            if len(body) < 6:
                continue
            bn_parts.append({"src": num, "bn": body})
    else:
        # সংখ্যা নেই: «।।» দিয়ে বাক্য-ভাগ করেই মন্ত্র-সংখ্যার সঙ্গে মিলাই
        segs = [x.strip() for x in re.split(r"(?<=[।॥])\s*(?=[^।॥])", bn_txt) if x.strip()]
        if len(segs) > len(sk_parts):
            segs = _merge_to(segs, len(sk_parts))
        for i, body in enumerate(segs):
            body = re.sub(r"\s*Bookmark\s*$", "", body, flags=re.I)
            body = re.sub(r"\s*[|।॥]+\s*$", "", body).strip()
            if len(body) >= 6:
                bn_parts.append({"src": None, "bn": body})

    by_src = {}
    for b in bn_parts:
        if b["src"]:
            by_src.setdefault(b["src"], []).append(b["bn"])

    res = []
    for i, v in enumerate(sk_parts):
        b = by_src.get(v["src"])
        if b is None and len(bn_parts) == len(sk_parts):
            b = [bn_parts[i]["bn"]]          # ক্রমে মিলে যায়
        res.append({
            "src": to_int(v["src"]),
            "n": i + 1,                 # প্রতি সূক্তে ১…n (উৎসের ২৪৩ নয়)
            "seg": to_int(v["src"]),
            "sk": [v["sk"]] if v["sk"] else [],
            "anv": [],
            "bn": [" ".join(b)] if b else [],
            "bnNote": "",
        })
    # ⚠ অন্য পথগুলো list ফেরায় আর write_chapter/main স্ট্রিং আশা করে —
    #   এখানেও list-ই দিই, নইলে নিচের বিল্ড-ধাপে সব মন্ত্র ফাঁকা হয়ে যায়।
    return res



def parse_verses(txt, bn_meaning=False):
    """পাতার পাঠ → [{'n','sk','anv','bn','bnNote'}]।

    গঠন:
      ক. 업নিষদ/ছান্দোগ্য: সংস্কৃত-ব্লক → «অন্বয়:» → «সরলার্থ:» → «ব্যাখ্যা:»
      খ. সামবেদ: «মন্ত্র : …» → «অর্থ : …»
      গ. পুরাণ: সংস্কৃত প্যারা → বাংলা প্যারা (লেবেলহীন)
      ঘ. ঋগ্বেদ: সংখ্যাযুক্ত বাংলা অনুচ্ছেদ
    """
    # ⚠ সামবেদে সংস্কৃত মূলও *বাংলা লিপিতে* ছাপা — তাই দেবনাগরী-গোনায়
    #   «সংস্কৃত নেই» মনে হয় আর bn_meaning ভুল করে True হয়ে যায়; তখন
    #   «মন্ত্রঃ/অর্থঃ» লেবেল-পথ বন্ধ হয়ে লেবেলই পাঠে ঢুকে পড়ে।
    #   লেবেলের উপস্থিতি থাকলে আগেই সিদ্ধান্ত নিই।
    has_labels = bool(re.search(r"(^|\n)\s*মন্ত্র\s*[:ঃ]", txt) and
                      re.search(r"(^|\n)\s*অর্থ\s*[:ঃ]", txt))
    if has_labels:
        bn_meaning = False
    elif re.search(r"বঙ্গানুবাদ\s*[–—\-]|অনুবাদঃ", txt):
        bn_meaning = True              # অথর্ববেদ/ঋগ্বেদ ধাঁচ: অনুবাদই পাঠ
    if not bn_meaning:
        dev = len(re.findall(r"[\u0900-\u0963\u0966-\u097F]", txt))
        multiline = len([x for x in txt.splitlines() if len(x.strip()) > 12])
        # «১. …» ধাঁচে সংখ্যায়িত বাংলা অনুচ্ছেদ = মন্ত্রের অনুবাদ-ই পাঠ
        # (ঋগ্বেদ ১০ম মণ্ডলের পাতাগুলো এমন)
        numbered_bn = len([x for x in txt.splitlines()
                           if _NUM_SEG_FULL.match(x.strip())
                           and re.search(r"[অ-হ]", x)])
        if dev < 200 and (multiline > 30 or numbered_bn >= 3) and not has_labels:
            bn_meaning = True          # সংস্কৃত মূল নেই ⇒ বাংলা-লিপিতেই পাঠ
    # ⚠ নিচের পরিবর্তনগুলো «।।১।।»-এর পরে লাইন ভাঙে — তখন «মন্ত্রঃ» প্যারায়
    #   আর একাধিক (num) থাকে না। তাই সিদ্ধান্ত আসল পাঠ থেকেই নিই।
    _raw_txt = txt
    _mm = re.search(r"(^|\n)[ \t]*মন্ত্র\s*[:ঃ]([^\n]*)", _raw_txt)
    _sama_numbered = bool(
        _mm and len(_NUM_INLINE.findall(_mm.group(2))) >= 2
        and re.search(r"(^|\n)\s*(?:অনুবাদ|অর্থ)\s*[:ঃ]", _raw_txt))
    txt = txt.replace("।।", "॥").replace("||", "॥").replace("\u09f7", "॥")
    txt = re.sub(r"([॥৷]\s*[০-৯०-९]{1,3}\s*[॥৷])\s*(?=\S)", r"\1\n", txt)
    if "অন্বয়" not in txt and "সরলার্থ" not in txt:
        txt = re.sub(r"\s+(?=[০-৯]{1,3}\s*।\s)", "\n", txt)
    labelled = ("অন্বয়" in txt or "সরলার্থ" in txt or "মন্ত্র :" in txt
                or "মন্ত্র:" in txt or "টীকা" in txt
                or bool(re.search(r"(^|\n)\s*অর্থ\s*[:ঃ\-–—]", txt))
                or bool(re.search(r"(বঙ্গানুবাদ|অনুবাদ)\s*[–—\-]", txt)))

    out, cur = [], None

    def split_by_danda(lines):
        """«॥১২॥» / «॥৩-৪॥» চিহ্ন ধরে শ্লোক-ব্লক ভাগ।"""
        groups, acc = [], []
        for ln in lines:
            acc.append(ln)
            m = re.search(r"[॥]\s*([০-৯०-९]{1,3})(?:\s*[-–]\s*[০-৯०-९]{1,3})?\s*[॥]", ln)
            if m:
                groups.append(acc)
                acc = []
        if acc:
            if groups:                      # শেষ অসম্পূর্ণ অংশ আগেরটার সঙ্গে
                groups[-1].extend(acc)
            else:
                groups.append(acc)
        return groups

    def add_verse(sk_lines, n_override=None):
        nonlocal cur
        sk_lines = [x for x in sk_lines
                    if x and not (x.startswith("ইতি") and "সমাপ্ত" in x)]
        parts = split_by_danda(sk_lines)
        if len(parts) > 1:
            for i, g in enumerate(parts):
                add_verse(g, n_override if i == 0 else None)
            return cur
        sk_lines = [re.sub(r"^([০-৯]{1,3})\s*[।\.]\s*", "", x) for x in sk_lines]
        v = {"sk": sk_lines, "anv": [], "bn": [], "note": [],
             "part": "anv", "n": None}
        t = n_override or last_of(v["sk"])
        if t:
            v["n"] = t
        out.append(v)
        cur = v
        return v

    def spill_prose(lines):
        """লেবেল-শুরুর আগে পড়ে থাকা সাধারণ লেখা → আগের শ্লোকের ব্যাখ্যায়।"""
        if not lines:
            return
        if cur is None:
            return                      # ভূমিকা — বাদ
        cur["part"] = "note"
        cur["note"].extend(lines)

    def flush_pending(pend, verse_label, continuation=False):
        """pending লাইন: শেষের সংস্কৃত-ব্লক = শ্লোক, তার আগেরটা ব্যাখ্যা-ধারাবাহিকতা।"""
        if not pend:
            return
        if continuation and cur is not None:
            cur[cur["part"]].extend(pend)   # লেবেলবিহীন ধারাবাহিকতা (বাংলা-পাঠ)
            return
        i = len(pend)
        if not looks_sanskrit(pend[i - 1]):
            # শেষ লাইনে দাঁড়ি না থাকলেও পুরো অনুচ্ছেদই বাংলা-প্রবন্ধ? নাকি শ্লোক-ব্লক?
            j = i - 1
            while j >= 0 and not looks_sanskrit(pend[j]):
                j -= 1
            if j >= 0 and j < i - 1:
                i = j + 1
            else:                        # সংস্কৃত-লাইন নেই ⇒ প্রবন্ধ, শ্লোক নয়
                if cur is not None:
                    cur["part"] = "note"
                    cur["note"].extend(pend)
                return
        while i > 0:
            cand = pend[i - 1]
            if is_heading(cand):
                break
            if looks_sanskrit(cand) or (len(cand) < 170 and not BN_STOP.search(cand)
                                        and re.search(r"[অ-হ]", cand)):
                i -= 1
            else:
                break
        spill_prose(pend[:i])
        tail = pend[i:]
        if tail:
            add_verse(tail)
        elif verse_label and cur is None:
            add_verse([])

    # ---- গঠন: «মন্ত্রঃ (২৪৩) …॥১॥ (২৪৪) …॥২॥» / «অনুবাদঃ (২৪৩) … (২৪৪) …» ----
    # সামবেদের অধ্যায় ৩ থেকে ২৪ পর্যন্ত 페이지গুলো এই ধাঁচে: এক প্যারায়
    # পুরো সুক্ত (নম্বর-তালিকায় প্রতি মন্ত্র), তারপর এক প্যারায় পুরো অনুবাদ।
    # লেবেল-পথ একই লাইনে একাধিক মন্ত্র দেখে বিভ্রান্ত হয় — তাই আগেই ভাগ করি।
    #   • উৎস-নম্বর (২৪৩) ⟵ মন্ত্রের চিহ্ন, কিন্তু ক্রম-সূচক নয় ⇒ পড়ার নম্বর ১…n
    #   • অনুবাদে সংখ্যা না-থাকলে আগের মন্ত্রেই জোড়া লাগে (বাংলা ক্রিয়াপদ দেখে রাখি)
    # ⚠ অধ্যায় ১–২-এও «মন্ত্রঃ- (০১)» আছে, কিন্তু এক লাইনে *একটাই* নম্বর।
    #   তাই শর্ত: একই «মন্ত্রঃ» প্যারায় অন্তত দুইটা (num) একসাথে থাকতে হবে।
    if _sama_numbered:
        _mv = _samaveda_numbered(_raw_txt)
        if _mv:
            return _mv

    if labelled:
        started = False
        pend = []
        for raw in txt.split("\n"):
            ln = raw.strip()
            if not ln or ln in (",", "|", ".") or ln.startswith("## ") or "||" in ln:
                continue
            if ln.startswith("[") or ln[:14].strip().startswith("ঋষি"):
                continue
            # «মন্ত্রের দেবতা … ॥ মন্ত্রের ছন্দ … ॥» — পাদটীকা-শিরোনাম, মন্ত্রের পাঠ নয়।
            # VERSE_TAIL শেষ দাঁড়িতে মিলে যেত, ফলে ভুয়া মন্ত্র তৈরি হতো আর
            # তারপর সব মন্ত্র/অর্থ এক ধাপ সরে যেত (নম্বর ১ হারিয়ে যেত)।
            if _META_LINE.search(ln) or _HEAD_TEXT.match(ln):
                continue
            if _FOOTNOTE.match(ln) or _DIVIDER.fullmatch(ln):
                # «(১) …» ফুটনোট / «————» বিভাজক — মন্ত্রের পাঠ নয়
                if cur is not None:
                    cur["part"] = "note"
                    cur["note"].append(ln)
                    started = True
                continue
            if ln.startswith("#") or _META_LINE.match(ln) or _HEAD_TEXT.match(ln):
                continue                      # মার্কডাউন-শিরোনাম/পাদটীকা-ব্লক
            _lbl = LBL.match(ln)
            if not started and not _lbl and (
                    is_heading(ln) or ln.startswith("[") or "সম্পাদনা" in ln
                    or "কাণ্ড :" in ln and len(ln) < 60):
                continue                      # শিরোনাম/সূচি লাইন
            if bn_meaning and not _lbl:
                # «১.» / «৭।» শুরু = নতুন মন্ত্রের অনুবাদ (ঋগ্বেদ ১০ম মণ্ডল ইত্যাদি)।
                # সংখ্যাটি কেবল ক্রম-সূচক, তাই নিজেই একটি শ্লোক শুরু করে।
                _nm = _NUM_SEG_FULL.match(ln)
                if _nm and not DEV_RE.search(ln) and not VERSE_TAIL.search(ln):
                    if pend:
                        flush_pending(pend, False, True)
                        pend = []
                    add_verse([])
                    cur["n"] = to_int(_nm.group(1))
                    cur["seg"] = to_int(_nm.group(1))   # সূক্ত-পরিচয় (উৎসেই আছে)
                    cur["part"] = "bn"
                    body = _nm.group(2).strip()
                    if body:
                        cur["bn"].append(body)
                    started = True
                    continue
                # সংখ্যায়িত অনুচ্ছেদের ভেতরে «অর্থাৎ/করে» থাকলেই তাকে প্রবন্ধ
                # ধরে ফেলা হতো ⇒ ঋগ্বেদ ১০ম মণ্ডলে সব মন্ত্র চুপচাপ হারিয়ে যেত।
                _bn_prose = (not VERSE_TAIL.search(ln)) or bool(
                    re.search(r"ইত্যাদি|অর্থাৎ|এবং|হয়|করে|করছি|হতে|জন্য|নিমিত্ত|"
                              r"অভিলক্ষ্য|অবলোকন|উদ্দেশ্য", ln)) or ln.startswith("(")
                _bn_prose = _bn_prose and not _nm
                if ((DEV_RE.search(ln) or VERSE_TAIL.search(ln)) and not _bn_prose) or (
                        looks_sanskrit(ln) and not _bn_prose and cur is not None
                        and not cur["bn"] and cur["sk"]):
                    flush_pending(pend, False, False)
                    pend = []
                    # নতুন শ্লোক: আগের শ্লোকে অনুবাদ থাকলে ⇒ নতুন মন্ত্র
                    if cur is not None and cur["sk"] and not cur["bn"]:
                        cur["sk"].append(ln)      # একই শ্লোকের পরের পঙক্তি
                    else:
                        add_verse([ln])
                else:
                    # বাংলা-পাঠ: শ্লোক-লক্ষণহীন বাংলা লাইন ⇒ চলতি শ্লোকের অনুবাদ-ধারাবাহিকতা
                    if cur is not None:
                        cur["part"] = "bn"
                        cur["bn"].append(ln)
                    pend = []
                continue
            m = MTRA.match(ln)
            if m:
                flush_pending(pend, False, bn_meaning)
                pend = []
                rest = re.sub(r"^[\s\-–—]*\(\s*[০-৯0-9]{1,3}\s*\)[\s\-–—]*", "", ln[m.end():]).strip()
                add_verse([rest])
                continue
            a = ARTH.match(ln)
            if a:
                flush_pending(pend, False, bn_meaning)
                pend = []
                if cur is None or cur["bn"]:
                    add_verse([])
                cur["part"] = "bn"
                r = re.sub(r"^[\s\-–—]*\(\s*[০-৯0-9]{1,3}\s*\)[\s\-–—]*", "", ln[a.end():]).strip()
                if r:
                    cur["bn"].append(r)
                continue
            l = LBL.match(ln)
            if not started and not l and not DEV_RE.search(ln) \
                    and not looks_sanskrit(ln) and not bn_meaning:
                continue                      # শিরোনাম/সূচি/ঋষি-ব্লক
            started = True
            if l:
                g = l.group(1)
                rest = ln[l.end():].strip()
                key = {"অন্বয়": "anv",
                       "সরলার্থ": "bn", "বঙ্গানুবাদ": "bn", "অনুবাদ": "bn",
                       "ব্যাখ্যা": "bn"}.get(g, "note")
                if g == "অন্বয়":
                    if pend:
                        flush_pending(pend, True, bn_meaning)
                        pend = []
                    elif cur is None:
                        add_verse([])
                else:
                    if pend:
                        flush_pending(pend, True, bn_meaning)
                        pend = []
                    if cur is None:
                        add_verse([])
                    if key == "bn" and cur["bn"]:
                        add_verse([])
                cur["part"] = key
                if rest:
                    cur[cur["part"]].append(rest)
                continue
            pend.append(ln)
        flush_pending(pend, False, bn_meaning)
    else:
        started = False
        for raw in txt.split("\n"):
            ln = raw.strip()
            if not ln or ln in (",", "|", ".") or ln.startswith("## ") or "||" in ln:
                continue
            if ln.startswith("[") or ln[:14].strip().startswith("ঋষি"):
                continue
            if _FOOTNOTE.match(ln) or _DIVIDER.fullmatch(ln):
                # «(১) …» ফুটনোট / «————» বিভাজক — মন্ত্রের পাঠ নয়
                if cur is not None:
                    cur["part"] = "note"
                    cur["note"].append(ln)
                    started = True
                continue
            if ln.startswith("[") or "ঋষি" in ln[:30] or ln.startswith("লেখক"):
                continue                      # ঋষি/দেবতা/ছন্দ-ব্লক
            nm = NUMHEAD.match(ln)
            is_dev = bool(DEV_RE.search(ln))
            is_bn_sk = (not is_dev) and (not bn_meaning) and _is_bn_verse(ln)
            if (not started) and (not is_dev) and (not nm):
                continue                      # শিরোনাম/ভূমিকা
            if is_bn_sk and bn_meaning:
                if cur is None or cur["bn"]:
                    add_verse([])
                cur["part"] = "bn"
                cur["bn"].append(ln)
                started = True
                continue
            if is_dev and bn_meaning and cur is not None and not cur["bn"] and cur["sk"]:
                cur["sk"].append(ln)          # একই শ্লোকের পরের লাইন
                started = True
                continue
            if is_dev or is_bn_sk:
                if cur is None or cur["bn"]:
                    add_verse([])
                cur["sk"].append(ln)
                if cur["n"] is None:
                    t = VERSE_TAIL.search(ln)
                    if t:
                        cur["n"] = to_int(t.group(1))
                started = True
                continue
            if nm:
                if nm.group(2).strip() in ("সূক্ত", "সূক্ত ।।", "সূক্ত।", "?"):
                    continue
                if cur is not None and cur["bn"]:
                    add_verse([])
                add_verse([])
                cur["part"] = "bn"
                cur["n"] = to_int(nm.group(1))
                cur["seg"] = to_int(nm.group(1))     # সূক্ত-পরিচয়
                cur["bn"].append(nm.group(2).strip())
                started = True
                continue
            if not started:
                continue
            if cur is None:
                add_verse([])
                cur["part"] = "bn"
            if cur["part"] == "sk":
                if not cur["sk"]:
                    continue
                cur["part"] = "bn"
            cur[cur["part"]].append(ln)

    # ---- পরিশোধন ----
    def _flat(x):
        """তালিকা/স্ট্রিং দুটোই নাও।

        ⚠ v["bn"] কখনো তালিকা (প্রতি লাইন আলাদা), কখনো স্ট্রিং (আগেই জোড়া)।
          স্ট্রিং-এ " ".join চালালে *প্রতি অক্ষরের* মাঝে ফাঁকা পড়ে —
          «হে অগ্নি» → «হ ে   অ গ ্ ন ি» — আর পুরো পাঠ অখণ্ডনীয় হয়।
          (সামবেদে ঠিক এটাই হচ্ছিল।)
        """
        if isinstance(x, str):
            return x
        return " ".join(str(y) for y in (x or []))

    res, auto = [], 0
    for v in out:
        bn = re.sub(r"\s+", " ", _flat(v["bn"])).strip()
        bn = re.sub(r"^\(\s*[০-৯०-९]{1,3}\s*\)\s*", "", bn)
        bn = re.sub(r"\s*Bookmark\s*$", "", bn)
        sk = re.sub(r"[ \t]+", " ", _flat(v["sk"])).strip()
        if len(bn) < 8 and not sk:
            continue
        if labelled and not sk and not bn_meaning:
            continue                     # সংস্কৃতহীন ভূমিকা-জাতীয় অনুচ্ছেদ বাদ
        n = v["n"] or last_of(v["sk"])
        if n:
            auto = n
        else:
            auto += 1
            n = auto
        _r = {"n": n, "sk": sk, "anv": _flat(v["anv"]).strip(),
              "bn": bn, "bnNote": _flat(v["note"]).strip()}
        if v.get("seg"):
            _r["seg"] = v["seg"]          # কোন সূক্তের মন্ত্র (উৎস-সংখ্যা)
        res.append(_r)
    return res


def last_of(sk_lines):
    for ln in reversed(sk_lines):
        m = re.search(r"[॥।]\s*([০-৯०-९]{1,3})\s*$", ln)
        if m:
            return to_int(m.group(1))
    return None


def next_link(h):
    m = re.search(r'href="([^"]+)"[^>]*>\s*Next Lesson', h, flags=re.I)
    if not m:
        m = re.search(r'Next Lesson[^<]*</a>', h)
        return None
    return htmllib.unescape(m.group(1))


def lesson_next(h):
    m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*Next Lesson', h, re.I)
    return htmllib.unescape(m.group(1)) if m else None


# ---------------- সংগ্রহ ----------------
def norm(x):
    """স্পেস ও হাইফেন বাদ দিয়ে মেলানোর রূপ।"""
    return re.sub(r"[\s\-–—/]+", "", x.lower())


def sitemap_urls(sitemaps, keyword, want=("topics", "lessons", "books")):
    """সাইটম্যাপ থেকে কীওয়ার্ড-মেলা URL।

    পাশাপাশি সব <loc> জমা রাখি (_ALL)। কারণ সাইটম্যাপ দিনে একবার বদলায়;
    একটা রানে সব URL না পেলে (আংশিক/ক্যাশ) সূচি-পাতার ভেতরের লিংক থেকেও
    খোঁজা যায় — নইলে শূন্য ফল মানেই অর্ধেক রান।
    """
    pat = norm(keyword)
    urls, seen = [], set()
    for sm in sitemaps:
        x = get(sm)
        if not x:
            continue
        for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x):
            u = htmllib.unescape(loc).strip()
            if not any(w in u for w in want):
                continue
            if u not in _ALL:
                _ALL.append(u)
            dec = norm(urllib.parse.unquote(u))
            if pat in dec and u not in seen:
                seen.add(u)
                urls.append(u)
    if not urls:
        # সূচি-পাতার ভেতরের লিংক থেকে চেষ্টা (ld-topic-page / ld-lesson-page)
        base = f"{BASE}/topics/{urllib.parse.quote(keyword.replace(' ', '-'))}/"
        inner = toc_links(base)
        for u in inner:
            if pat in norm(urllib.parse.unquote(u)) and u not in seen:
                seen.add(u)
                urls.append(u)
        if urls:
            print(f"   (সাইটম্যাপে পাওয়া গেল না — সূচি-পাতার ভেতর থেকে "
                  f"{len(urls)}টি লিংক)", flush=True)
    return urls


def book_lessons(book_url, max_pages=60):
    """বই-পাতার সূচি থেকে লেসন/টপিক-সংযোগ (ক্রম অপরিবর্তিত)।

    ⚠ বই-পাতার সূচি পৃষ্ঠায়িত: প্রথম পাতায় কেবল ~৪৮টি লেসন (অধ্যায় ১–৪)
      থাকে, বাকিগুলো «?ld-book-page=2» ইত্যাদিতে। আগে শুধু প্রথম পাতা পড়া
      হতো, তাই অধ্যায় ৫–২৪ কখনো সূচিতেই আসত না — অথচ সেগুলো সাইটে আছে।
    """
    out, seen, seen_p = [], set(), set()

    def _grab(h):
        for m in re.finditer(r'href="(https://www\.ebanglalibrary\.com/'
                             r'(?:lessons|topics)/[^"#?]+)"', h):
            u = htmllib.unescape(m.group(1))
            if u not in seen and u.rstrip("/") != book_url.rstrip("/"):
                seen.add(u)
                out.append(u)
        if len(out) % 48 == 0 and out:
            print(f"   সূচি: {len(out)} লেসন সংগ্রহ (পৃষ্ঠা {len(seen_p)})", flush=True)

    h = get(book_url)
    if not h:
        return []
    _grab(h)

    # পেজিনেশন: «ld-book-page=2» … যতক্ষণ নতুন লেসন মিলছে
    pages, guard = [], 0
    for m in re.finditer(r'href="([^"]*ld-book-page=\d+[^"]*)"', h, re.I):
        pages.append(htmllib.unescape(m.group(1)))
    nxt = next_page_link(h)
    if nxt and "ld-book-page" in nxt:
        pages.append(nxt)
    # পাশাপাশি সরাসরি ?ld-book-page=2… তৈরি করি (লিংক সব সময় না-ও থাকতে পারে)
    base = book_url.split("?")[0]
    for i in range(2, 41):
        pages.append(f"{base}?ld-book-page={i}")
    # ⚠ «Next Page» টপিক/লেসন-পৃষ্ঠারও হতে পারে — বই-পৃষ্ঠাই কেবল নিই
    pages = [p for p in pages
             if "ld-book-page" in p or not re.search(r"ld-(?:topic|lesson)-page", p)]
    for u in pages:
        if guard >= max_pages:
            break
        if u in seen_p:
            continue
        seen_p.add(u)
        guard += 1
        before = len(out)
        hp = get(u)
        if not hp:
            break
        _grab(hp)
        if len(out) == before:      # নতুন কিছু নেই ⇒ পৃষ্ঠা শেষ
            break
        time.sleep(0.3)
    return out



# ঋগ্বেদের মণ্ডল। সাইটে টপিক-পাতা «ঋগ্বেদ-১০।০১» ধাঁচে, কিন্তু মণ্ডলভিত্তিক
# সূচি (১০ম মণ্ডল) সব সময় সাইটম্যাপে/লিংকে ধরা পড়ে না — তাই সরাসরি চেষ্টা করি।
RV_MANDALA_TOC = [
    f"{BASE}/topics/ঋগ্বেদ-{m:02d}।০১/" for m in range(1, 11)
] + [
    f"{BASE}/topics/ঋগ্বেদ-{m:02d}/" for m in range(1, 11)
]


def mandala_links(m):
    """একটি মণ্ডলের সূক্ত-পাতার তালিকা — যত উপায়ে পাওয়া যায় সব চেষ্টা।

    উৎস সাইট ব্লক করলে (TLS/403) কিছুই পাওয়া যায় না — তখন খালি তালিকা
    ফেরে, রান ভেঙে পড়ে না, আর বাকি ধাপ (বিল্ড/প্রকাশ) শুধু নতুন কিছু
    পেলে কাজ করে।
    """
    found = {}
    print(f"   মণ্ডল {m}: সূচি-পাতা খুঁজছি…", flush=True)
    # সাইট একই পাতা বারবার চাইলে ফাঁকা ফেরাতে পারে (রানে ঠিক তাই হয়েছে:
    # প্রথমবার ৩৩৭,০১৭ অক্ষর, পরে ০)। তাই সাইটম্যাপে আগেই পাওয়া সূক্ত-পাতা
    # থাকলে সেগুলোই ব্যবহার করি — আর কোনো অনুরোধ লাগে না।
    pre = []
    for u in _ALL:
        if "/topics/" not in u:
            continue
        t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
        g = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।\s*([০-৯]{1,3})$", t)
        if g and to_int(g.group(1)) == m:
            pre.append(u)
    if pre:
        print(f"   (সাইটম্যাপে আগেই পাওয়া {len(pre)}টি সূক্ত-পাতা ব্যবহার করছি)",
              flush=True)
        return sorted(pre, key=lambda u: ordinal_of(u)[0] or 0)

    # আগে এই মণ্ডলের নিজের সূচি, তারপর অন্য মণ্ডলগুলো — বেশি চেষ্টা = বেশি
    # ব্লক, তাই মোট ৬টি ঠিকানার বেশি নয়।
    def _mine(t):
        mm = re.search(r"ঋগ্বেদ-(\d{2})", urllib.parse.unquote(t))
        return 0 if mm and to_int(mm.group(1)) == m else 1
    for toc in sorted(RV_MANDALA_TOC, key=_mine)[:6]:
        head = urllib.parse.unquote(toc)
        mm = re.search(r"ঋগ্বেদ-(\d{2})", head)
        if not mm or to_int(mm.group(1)) != m:
            continue
        for u in toc_links(toc) + [toc]:
            t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
            g = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।\s*([০-৯]{1,3})$", t)
            if g and to_int(g.group(1)) == m:
                found[to_int(g.group(2))] = u
        # pagina-শৃঙ্খল ধরে বাকি পাতা (ld-topic-page=2,3…)
        seen, nxt = set(), None
        h = get(toc)
        if h:
            nxt = next_page_link(h)
        guard = 0
        while nxt and guard < 40 and nxt not in seen:
            seen.add(nxt)
            guard += 1
            h = get(nxt)
            if not h:
                break
            for g in re.finditer(r'href="([^"]*?/(?:topics|lessons)/[^"#?]+)"', h):
                u = htmllib.unescape(g.group(1))
                t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
                mm2 = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।\s*([০-৯]{1,3})$", t)
                if mm2 and to_int(mm2.group(1)) == m:
                    found[to_int(mm2.group(2))] = u
            nxt = next_page_link(h)
        for u in toc_links(toc):
            t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
            g = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।\s*([০-৯]{1,3})$", t)
            if g and to_int(g.group(1)) == m:
                found.setdefault(to_int(g.group(2)), u)
        if found:
            break
    return [found[k] for k in sorted(found)]


def toc_links(page_url):
    """কোর্স/লেসন পাতার ভেতরের টপিক-তালিকা (ক্রম অপরিবর্তিত)।"""
    h = get(page_url) or ""
    out, seen = [], set()
    for m in re.finditer(r'href="(https://www\.ebanglalibrary\.com/(?:topics|lessons)/[^"#?]+)"', h):
        u = htmllib.unescape(m.group(1))
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def ordinal_of(url):
    """পাতার ক্রম-সংখ্যা: আগে শিরোনামের «০২।০৫» ধাঁচ, নইলে «প্রথম/দ্বিতীয়» শব্দ।"""
    t = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
    m = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।\s*([০-৯]{1,3})", t)
    if m:
        a = to_int(m.group(1))
        b = to_int(m.group(2))
        return (a if a is not None else 0) * 1000 + (b or 0), m.group(0)
    for k, v in ORD.items():
        if k in t:
            return v, k
    return None, None


def next_page_link(h):
    """learnDash-এর «Next Page» লিংক (topic/lesson — দুটোই)।"""
    m = re.search(r'href="([^"]*ld-(?:topic|lesson)-page=[^"]*)"[^>]*>\s*Next Page', h, re.I)
    if not m:
        m = re.search(r'<a[^>]+href="([^"]*ld-(?:topic|lesson)-page=[^"]*)"', h, re.I)
    return htmllib.unescape(m.group(1)) if m else None


def _same_topic(a, b):
    """দুটি ঠিকানা একই টপিকের পৃষ্ঠা কি না (query বাদ দিয়ে)।"""
    pa = urllib.parse.urlsplit(urllib.parse.unquote(a))
    pb = urllib.parse.urlsplit(urllib.parse.unquote(b))
    return pa.path.rstrip("/") == pb.path.rstrip("/") and pa.netloc == pb.netloc


def fetch_paged(url, max_pages=40):
    """এক পাতার সব পৃষ্ঠা («Next Page» ধরে) জোড়া দেয়।

    সাবধানতা: সাইটের পাশের সূচি-ব্লকে অন্য টপিকের «Next Page» থাকতে পারে।
    ভুল ঠিকানায় গেলে সাইট কয়েকবার ব্যর্থ হয় আর পুরো রান থেমে যায় — তাই
    কেবল একই টপিকের পৃষ্ঠাই অনুসরণ করি।
    """
    parts, seen, u = [], set(), url
    for _ in range(max_pages):
        if u in seen:
            break
        seen.add(u)
        h = get(u)
        if not h:
            break
        t = page_text(h)
        if t:
            parts.append(t)
        # আসল পাতার ভেতরের «Next Page» আগে, নইলে পাশের সূচিরটা
        cands = []
        for m in re.finditer(r'href="([^"]*ld-(?:topic|lesson)-page=[^"]*)"', h, re.I):
            cands.append(htmllib.unescape(m.group(1)))
        cands.append(next_page_link(h))
        nu = None
        for c in cands:
            if c and c not in seen:
                if not _same_topic(url, c):
                    continue          # অন্য টপিকের সূচি — এখানে যাব না
                mm = re.search(r"ld-(?:topic|lesson)-page=[\d]+-(\d+)", c)
                if mm and int(mm.group(1)) < 2:
                    continue          # «-1» মানে শুরু থেকে গোনা — লুপ তৈরি করে
                nu = c
                break
        if not nu:
            break
        u = nu
        time.sleep(0.25)
    return "\n\n".join(parts)


# ইংরেজি/দেবনাগরী/IAST মিশে থাকা মন্ত্র বাদ দেওয়ার নিয়ম (clean_rigveda-র সঙ্গে এক)
_DEV_ANY = re.compile(r"[\u0900-\u0963\u0966-\u0970\u0971-\u097F]")
_IAST = re.compile(r"[āīūṛṣṭḍṇṃśṅñĀĪŪṚṢṬḌṆṂŚṄÑ]")
_LAT3 = re.compile(r"[A-Za-z][A-Za-z'’\-]{2,}")
_BNCH = re.compile(r"[\u0980-\u09FF]")


def _flat_text(x):
    """list/str → এক স্ট্রিং (পাঠ যেভাবেই রাখা থাকুক)।"""
    if isinstance(x, (list, tuple)):
        return " ".join(str(y) for y in x).strip()
    return str(x or "").strip()


def foreign_reasons(text):
    """বাংলার সঙ্গে বিদেশি পাঠ মিশে থাকলে কারণের তালিকা (খালি = পরিষ্কার)।"""
    # ⚠ পার্সার এখন কোনো কোনো পথে bn/sk-কে list রাখে (প্রতি লাইন আলাদা),
    #   আবার কোনো পথে str — দুটোই নিরাপদে সামলাতে হবে।
    if isinstance(text, (list, tuple)):
        text = " ".join(str(x) for x in text)
    if not text:
        return ["বাংলা নেই"]
    out = []
    if re.search(r"\bHYMN\b|Rig Veda Book", text):
        out.append("Griffith-ইংরেজি")
    if _DEV_ANY.search(text):
        out.append("দেবনাগরী")
    if _IAST.search(text):
        out.append("IAST")
    run = 0
    for _t in _LAT3.finditer(text):
        run += 1
        if run >= 3:
            out.append("ইংরেজি প্যারা")
            break
    total = len(re.sub(r"\s", "", text))
    if total and len(_BNCH.findall(text)) / total < 0.35:
        out.append("মূলত বিদেশি পাঠ")
    return out


def write_chapter(out_dir, idx, title, verses, url):
    # ব্যবহারকারীর সিদ্ধান্ত (২০২৬-১১-০৫): মন্ত্রের বাংলার পাশে Griffith-এর
    # ইংরেজি, দেবনাগরী মূল বা IAST থাকলে সেই মন্ত্রটা রাখা হয় না।
    kept, dropped, no_bn = [], 0, 0
    for v in verses:
        if foreign_reasons(v.get("bn") or ""):
            dropped += 1
            continue
        # ব্যবহারকারীর শর্ত: পাঠ **শুধু বাংলায়** — অনুবাদহীন মন্ত্র রাখা যায় না।
        # (অনুবাদ-পরা না মিললে আগে শুধু সংস্কৃত-মূল ঢুকে যেত।)
        _bn = v.get("bn")
        _bns = _flat_text(_bn)
        # «(২৪৩) …» = উৎসের রিগ্বেদ-নম্বর; পড়ার নম্বর আলাদা ⇒ পাঠে থাকবে না
        _bns = re.sub(r"^\s*[(]\s*[০-৯0-9]{1,4}\s*[)]\s*", "", _bns).strip()
        if not _bns:
            no_bn += 1
            continue
        v["bn"] = _bns
        kept.append(v)
    if no_bn:
        print(f"   ⚠ অনুবাদহীন {no_bn}টি মন্ত্র বাদ (পাঠ শুধু বাংলায়)", flush=True)
    if dropped:
        print(f"   ⚠ বিদেশি পাঠ মেশানো {dropped}টি মন্ত্র বাদ দেওয়া হলো", flush=True)
    verses = kept
    vs = []
    for v in verses:
        d = {"n": v["n"], "sk": v["sk"], "bn": v["bn"], "spk": "", "bnSrc": SRC}
        if v.get("seg"):
            d["seg"] = v["seg"]
        if v.get("bnNote"):
            d["bnNote"] = v["bnNote"]
        if v.get("anv"):
            d["anv"] = v["anv"]
        vs.append(d)
    os.makedirs(out_dir, exist_ok=True)
    obj = {"id": idx, "bn": title, "count": len(vs), "from": 1, "to": len(vs),
           "verses": vs, "url": url}
    with open(os.path.join(out_dir, f"ch{idx}.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    return {"id": idx, "bn": title, "count": len(vs), "from": 1, "to": len(vs),
            "withBn": sum(1 for v in vs if v["bn"]), "url": url}


def split_oversized(v, limit=4000):
    """এক «শ্লোকে» গোটা অধ্যায় ঠাসা থাকলে দাঁড়ি ধরে ভাগ করি।

    কেন: পুরাণের পাঠে শ্লোকের শেষে «॥১॥» না থাকলে পার্সার পুরো অধ্যায়কে এক
    শ্লোকে ঢুকিয়ে দিত (একটাই «মন্ত্র», ৩২,০০০ অক্ষর) — ফলে শ্লোক-সংখ্যা
    এক-তৃতীয়াংশে নেমে যেত আর পড়াও যেত না।
    """
    def _one(x):
        """sk/bn কখনো list, কখনো str — এক রূপে আনি (নইলে .strip() ভেঙে পড়ে)।"""
        if isinstance(x, (list, tuple)):
            return " ".join(str(y) for y in x).strip()
        return str(x or "").strip()

    bn = _one(v.get("bn"))
    if len(bn) <= limit and len(_one(v.get("sk"))) <= limit:
        return [v]
    parts = [x.strip() for x in re.split(r"(?<=[।॥])\s+", bn) if x.strip()]
    chunks, buf = [], ""
    for x in parts:
        if buf and len(buf) + len(x) > limit:
            chunks.append(buf.strip())
            buf = x
        else:
            buf = (buf + " " + x).strip()
    if buf:
        chunks.append(buf.strip())
    if len(chunks) <= 1:
        cut, chunks = bn, []
        while len(cut) > limit:
            sp = cut.rfind(" ", 0, limit)
            sp = sp if sp > limit // 2 else limit
            chunks.append(cut[:sp].strip())
            cut = cut[sp:].strip()
        if cut:
            chunks.append(cut)
    sk = _one(v.get("sk"))
    out = []
    for i, c in enumerate(chunks, 1):
        nv = dict(v)
        nv["bn"] = c
        nv["sk"] = sk if i == 1 else ""
        out.append(nv)
    if len(out) > 1:
        print(f"   ⚠ এক শ্লোকে ঠাসা পাঠ {len(out)} ভাগে ভাগ করা হলো "
              f"({len(bn)} → ≤{limit} অক্ষর)", flush=True)
    return out


def untangle_books(out_dir, foreign, own, own_words):
    """অন্য গ্রন্থের পাঠ এই slug-এ ঢুকে থাকলে বাদ দিই।

    কেন: `--book-auto` বই-খোঁজায় ভুল মিললে (গরুড় ↔ ভবিষ্য পুরাণের একই
    অধ্যায়-নাম) দুই বইয়ের শ্লোক এক index-এ মিশে যেত।
    """
    n_bad = 0
    keep = []
    for c in own:
        p = os.path.join(out_dir, f"ch{c['id']}.json")
        try:
            with open(p, encoding="utf-8") as f:
                ch = json.load(f)
        except Exception:
            keep.append(c)          # ফাইল নেই ⇒ বিচার করা যায় না, রাখি
            continue
        txt = " ".join((x.get("bn") or "")[:120] for x in ch.get("verses", [])[:3])
        bad = sum(txt.count(w) for w in foreign if w)
        good = sum(txt.count(w) for w in own_words if w)
        if bad and bad >= good:
            n_bad += 1
            continue
        keep.append(c)
    if n_bad:
        print(f"   ⚠ অন্য গ্রন্থের পাঠ ধরা পড়ল {n_bad}টি অধ্যায়ে — বাদ দেওয়া হলো",
              flush=True)
    return keep


def classify(url):
    """URL দেখে গ্রন্থ-ধরন ঠিক করে (slug, শিরোনাম, পদ্ধতি, ম্যাচ-কীওয়ার্ড)।"""
    t = urllib.parse.unquote(url)
    for nm, sl in (("ঈশ", "isha"), ("কেন", "kena"), ("প্রশ্ন", "prashna"),
                   ("মুণ্ডক", "mundaka"), ("মাণ্ডূক্য", "mandukya"),
                   ("তৈত্তিরীয়", "taittiriya"), ("ঐতরেয়", "aitareya"),
                   ("বৃহদারণ্যক", "brihadaranyaka")):
        if nm in t and "উপনিষদ" in t:
            return dict(slug="upanishad-" + sl, title=nm + " উপনিষদ",
                        mode="ordinal", match=nm + " উপনিষদ", word="মন্ত্র")
    if re.search(r"ভবিষ্য[- ]?পুরাণ", t) and "/lessons/" in t:
        return dict(slug="bhabishya", title="ভবিষ্য পুরাণ", mode="book",
                    match="ভবিষ্য পুরাণ পৃথ্বীরাজ", word="শ্লোক")
    if re.search(r"গরুড়[- ]?পুরাণ", t) and "/lessons/" in t:
        return dict(slug="garuda", title="গরুড় পুরাণ", mode="book",
                    match="গরুড় পুরাণ পৃথ্বীরাজ", word="শ্লোক")
    if re.search(r"ব্রহ্ম[- ]?পুরাণ", t) and "/lessons/" in t:
        return dict(slug="brahma", title="ব্রহ্ম পুরাণ", mode="book",
                    match="ব্রহ্ম পুরাণ পৃথ্বীরাজ", word="শ্লোক")
    if re.search(r"অথর্ববেদ", t) and "/books/" in t:
        return dict(slug="atharvaveda", title="অথর্ববেদ সংহিতা", mode="book",
                    match="অথর্ববেদ সংহিতা", word="মন্ত্র")
    if re.search(r"সামবেদ", t) and "/books/" in t:
        return dict(slug="samaveda", title="সামবেদ সংহিতা", mode="book",
                    match="সামবেদ সংহিতা বঙ্গানুবাদ", word="মন্ত্র")
    if re.search(r"সামবেদ", t) and "/lessons/" in t and re.search(r"[০-৯]{2}।[০-৯]{2}", t):
        return dict(slug="samaveda", title="সামবেদ সংহিতা", mode="book",
                    match="সামবেদ সংহিতা পরিতোষ", word="মন্ত্র")
    if re.search(r"ঋগ্বেদ", t) and "/topics/" in t:
        return dict(slug="rigveda", title="ঋগ্বেদ সংহিতা", mode="group",
                    match="ঋগ্বেদ ০", word="সূক্ত")
    if re.search(r"শুক্ল[- ]?যজুর্বেদ", t) and ("/books/" in t or "/lessons/" in t):
        return dict(slug="yajurveda-shukla", title="শুক্ল যজুর্বেদ সংহিতা",
                    mode="book", match="শুক্ল যজুর্বেদ সংহিতা", word="মন্ত্র")
    if re.search(r"কৃষ্ণ[- ]?যজুর্বেদ", t) and ("/books/" in t or "/lessons/" in t):
        return dict(slug="yajurveda-krishna", title="কৃষ্ণ যজুর্বেদ সংহিতা",
                    mode="book", match="কৃষ্ণ যজুর্বেদ সংহিতা", word="মন্ত্র")
    for nm, sl in (("ঈশ", "isha"), ("কেন", "kena"), ("প্রশ্ন", "prashna"),
                   ("মুণ্ডক", "mundaka"), ("মাণ্ডূক্য", "mandukya"),
                   ("তৈত্তিরীয়", "taittiriya"), ("ঐতরেয়", "aitareya"),
                   ("বৃহদারণ্যক", "brihadaranyaka")):
        if re.search(nm + r"\s*উপনিষদ", t) and ("/lessons/" in t or "/topics/" in t):
            return dict(slug="upanishad-" + sl, title=f"{nm} উপনিষদ",
                        mode="ordinal", match=nm + " উপনিষদ", word="মন্ত্র")
    if re.search(r"ছান্দোগ্য", t) and "/topics/" in t:
        return dict(slug="chandogya", title="ছান্দোগ্য উপনিষদ", mode="ordinal",
                    match="ছান্দোগ্য উপনিষদ", word="মন্ত্র")
    return None


def run_auto(args):
    """আবিষ্কার → গ্রন্থ-শনাক্ত → নামানো, এক রানে।"""
    print(">>> run_auto শুরু", flush=True)
    skip = set(x.strip() for x in os.environ.get("EBL_SKIP", "").split(",") if x.strip())
    only = set(x.strip() for x in os.environ.get("EBL_ONLY", "").split(",") if x.strip())
    cache_p = os.path.join(args.out, "_debug", "sitemap.json")
    cands = []
    if os.path.exists(cache_p):
        try:
            cands = json.load(open(cache_p, encoding="utf-8"))
            print(f"সাইটম্যাপ ক্যাশ থেকে {len(cands)} URL")
        except Exception:
            cands = []
    if not cands:
        for sm in TOPIC_SITEMAPS + LESSON_SITEMAPS:
            x = get(sm)
            if not x:
                continue
            cands += [htmllib.unescape(u) for u in
                      re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x)]
            time.sleep(0.4)
        os.makedirs(os.path.dirname(cache_p), exist_ok=True)
        with open(cache_p, "w", encoding="utf-8") as f:
            json.dump(cands, f, ensure_ascii=False)
    print(f"সাইটম্যাপ URL মোট: {len(cands)}")
    seen, targets = set(), {}
    for u in cands:
        c = classify(u)
        if not c:
            continue
        k = c["slug"]
        if k in skip or (only and k not in only):
            continue
        if k not in targets:
            targets[k] = c
            print(f"শনাক্ত: {k} ← {urllib.parse.unquote(u)[-70:]}", flush=True)
        seen.add(k)
    print("লক্ষ্য:", list(targets), flush=True)
    for k, c in targets.items():
        print(f"\n===== {c['title']} ({k}) — {c['mode']} =====", flush=True)
        sub = argparse.Namespace(**vars(args))
        sub.slug = c["slug"]
        sub.title = c["title"]
        sub.match = c["match"]
        sub.word = c["word"]
        sub.ordinal = sub.chain = sub.book = sub.group_by_num = False
        sub.discover = sub.auto = False
        sub.url = ""
        if c["mode"] == "book":
            book = sitemap_urls(LESSON_SITEMAPS + TOPIC_SITEMAPS, c["match"],
                                ("lessons", "books"))
            book = [u for u in book if "/lessons/" in u]
            if not book:
                print("  ✗ বই-পাতা পাওয়া গেল না")
                continue
            sub.book = True
            sub.url = book[0]
            print("  বই:", urllib.parse.unquote(book[0])[-70:])
        elif c["mode"] == "ordinal":
            sub.by_ordinal = True
        elif c["mode"] == "group":
            sub.group_by_num = True
        try:
            main_run(sub)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("  ✗ ভুল:", e, flush=True)


def _source_slug(url):
    """URL থেকে উৎস-পাতার শেষ অংশ — একই পাঠ দুইবার লেখা ঠেকাতে।"""
    u = urllib.parse.unquote(url or "").rstrip("/")
    return u.split("/")[-1] if u else ""


def _existing(out_dir):
    """আগের index.json-এ যা আছে — নতুন ফল এর চেয়ে ছোট হলে তা নয়।"""
    p = os.path.join(out_dir, "index.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _chapters_by_src(out_dir):
    """আগের chapters — উৎস-পাতার নাম ধরে মিলিয়ে দেখার জন্য।"""
    old = _existing(out_dir)
    return (old or {}).get("chapters", []) or []


def write_index_guarded(out_dir, slug, title, chapters, word, own_words=None):
    """ইনডেক্স লেখার আগে সুরক্ষা-বলয়।

    কেন: উৎস-পাতা ধরে ফেচ কখনো অর্ধেক ধরে (সাইট ডাউন, লিংক বদল, ক্রস-গ্রন্থ লিক)।
    তখনই পুরনো ভালো ডেটা মুছে ছোট ডেটা বসে যেত আর কমিট হয়ে যেত — ২০২৬-১১-০৪-এ
    একাধিকবার তাই হয়েছে (গরুড় ১০৫ → ২১ শ্লোক)।

    নিয়ম:
      ১) একই উৎস-পাতা দুইবার নয় (পাঠের পুনরাবৃত্তি)।
      ২) আগের অধ্যায় হারায় না — নতুন ফলে না থাকলে পুরনোটা ধরে রাখা হয়
         (তাই «শুধু ১০ম মণ্ডল নামাও» নিরাপদ)।
      ৩) যে অধ্যায় দুই জায়গাতেই আছে, তার শ্লোক কমলে পুরনোটা জেতে।
      ৪) সব মিলিয়ে মোট শ্লোক আগের চেয়ে কম হলে কিছুই লেখা হয় না।
    """
    seen, uniq = set(), []
    for c in chapters:
        k = _source_slug(c.get("url", ""))
        if k and k in seen:
            continue
        if k:
            seen.add(k)
        uniq.append(c)
    if len(uniq) != len(chapters):
        print(f"   ⚠ একই উৎস-পাতা {len(chapters) - len(uniq)}টি বাদ "
              f"(পাঠের পুনরাবৃত্তি)", flush=True)

    # ক্রস-গ্রন্থ লিক: একই সাইটে গরুড় ও ভবিষ্য পুরাণের অধ্যায়-নাম হুবহু এক,
    # তাই বই-খোঁজায় ভুল হলে দুই বইয়ের পাঠ মিশে যায়।
    foreign = [w for w in (own_words or []) if w and w not in (title or "")]
    if foreign and uniq:
        uniq = untangle_books(out_dir, foreign, uniq, [title] if title else [])

    if not uniq:
        print("   ⛔ বাতিল: কোনো অধ্যায় পাওয়া যায়নি", flush=True)
        return None

    old = _existing(out_dir)
    if old and old.get("chapters"):
        by_id = {c["id"]: c for c in uniq}
        for oc in old["chapters"]:
            nc = by_id.get(oc["id"])
            if nc is None:
                print(f"   ⊕ অধ্যায় {oc['id']} নতুন ফলে নেই — পুরনোটা রাখা হলো "
                      f"({oc['count']} {word})", flush=True)
                by_id[oc["id"]] = oc
            elif nc["count"] < oc["count"]:
                print(f"   ⚠ অধ্যায় {oc['id']}: {oc['count']} → {nc['count']} "
                      f"{word} — কমে গেছে, পুরনোটা রাখা হলো", flush=True)
                by_id[oc["id"]] = oc
        uniq = sorted(by_id.values(), key=lambda c: c["id"])
        new_total = sum(c["count"] for c in uniq)
        old_total = old.get("total", 0)
        if new_total < old_total:
            print(f"   ⛔ বাতিল: নতুন মোট {new_total} < আগের {old_total} — "
                  f"পুরনো index.json অটুট", flush=True)
            return None

    # বাদ-পড়া ch<N>.json ফাইল মুছি না: index-এ না থাকলে সাইটে দেখায় না, কিন্তু
    # ভুলে হারানো ডেটা ফিরিয়ে আনা সহজ থাকে।
    return build_index(out_dir, slug, title, uniq, word)


def build_index(out_dir, slug, title, chapters, word):
    byc = {c["id"]: c for c in chapters}
    chs = [byc[k] for k in sorted(byc)]
    for c in chs:
        c.pop("url", None)
    idx = {"slug": slug, "bn": title, "en": slug.title(),
           "total": sum(c["count"] for c in chs),
           "withBn": sum(c["withBn"] for c in chs), "chapters": chs,
           "verseWord": word, "bnSrc": SRC,
           "note": "মূল সংস্কৃত পাঠ ও বাংলা অনুবাদ — ebanglalibrary.com"}
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return idx


def book_words(args):
    """গ্রন্থ-চেনার শব্দ — ম্যাচ-কীওয়ার্ড ও শিরোনাম থেকে।"""
    ws = []
    for chunk in (args.match or "").split("|"):
        for w in re.split(r"[\s,]+", chunk.strip()):
            if len(w) > 3 and w not in ws:
                ws.append(w)
    for w in re.split(r"[\s—–\-]+", args.title or ""):
        if len(w) > 3 and w not in ws:
            ws.append(w)
    return ws


def main_run(args):
    own_words = book_words(args)
    if getattr(args, "auto", False):
        return run_auto(args)

    if args.discover:
        urls = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        print(f"মিলেছে {len(urls)}")
        for u in urls:
            print(" ", urllib.parse.unquote(u))
        return

    out_dir = os.path.join(args.out, args.slug) if args.slug else ""

    if args.url and not (args.book or args.chain or args.group_by_num or args.toc
                         or args.series or args.prefix or args.book_toc):
        # একক পাতা (পরীক্ষা/ডাম্প)
        h = get(args.url)
        txt = fetch_paged(args.url)
        vs = parse_verses(txt)
        print(f"মন্ত্র: {len(vs)}")
        def _s(x):
            # sk/bn/anv কখনো list, কখনো str — কেটে ছাপার আগে এক রূপে আনি
            return " ".join(x) if isinstance(x, list) else str(x or "")
        for v in vs[: args.dump or 3]:
            print(f" {v['n']} | sk: {_s(v['sk'])[:80]}")
            print(f"    bn: {_s(v['bn'])[:100]}")
            if _s(v.get("bnNote")):
                print(f"    note: {_s(v['bnNote'])[:60]}")
        if args.dump:
            os.makedirs(os.path.join(args.out, "_debug"), exist_ok=True)
            fn = re.sub(r"[^\w]+", "_", urllib.parse.unquote(args.url))[-60:]
            with open(os.path.join(args.out, "_debug", fn + ".txt"), "w",
                      encoding="utf-8") as f:
                f.write(txt)
            print("ডাম্প:", fn + ".txt")
        return

    if args.chain and args.url:
        return

    # ---- তালিকা বানানো ----
    if args.book_auto:
        books = []
        for m in [x.strip() for x in args.match.split("|") if x.strip()]:
            books = [u for u in sitemap_urls(COURSE_SITEMAPS + LESSON_SITEMAPS
                                             + TOPIC_SITEMAPS, m,
                                             ("books", "courses"))
                     if "/books/" in u]
            if books:
                print("কীওয়ার্ড:", m)
                break
        print("বই-পাতা:", [urllib.parse.unquote(b)[-60:] for b in books[:3]])
        if not books:
            sys.exit("বই-পাতা পাওয়া গেল না: " + args.match)
        lessons = []
        for b in books[:1]:
            lessons = book_lessons(b)
        print(f"সূচিতে লেসন: {len(lessons)}")
        items = [(i, u) for i, u in enumerate(lessons, start=args.start)]
        if args.max:
            items = items[: args.max]
    elif args.book:
        items = [(i, u) for i, u in enumerate(book_lessons(args.url), start=args.start)]
        if args.max:
            items = items[: args.max]
    elif args.book_toc:
        # বই/লেসন-পাতার সূচি → প্রতিটি লেসনের ভেতরের টপিক (আসল শ্লোক-পাতা)
        url0 = args.url
        if not url0:
            cands = sitemap_urls(LESSON_SITEMAPS, args.match)
            url0 = sorted(cands, key=lambda x: (len(urllib.parse.unquote(x)), x))[0] if cands else None
        if not url0:
            sys.exit("সূচি-পাতা পাওয়া গেল না: " + args.match)
        lessons = book_lessons(url0) or [url0]
        print("লেসন/টপিক:", len(lessons), flush=True)
        sel, seen = [], set()
        for lu in lessons:
            if "/topics/" in urllib.parse.unquote(lu):
                if lu not in seen:
                    seen.add(lu)
                    sel.append(lu)          # নিজেই শ্লোক-পাতা
                    continue
            for t in toc_links(lu):
                if t not in seen:
                    seen.add(t)
                    sel.append(t)
            time.sleep(0.2)
        if not sel:
            sel = lessons
        print("টপিক:", len(sel), flush=True)
        items = [(i, u) for i, u in enumerate(sel, start=args.start)]
        if args.max:
            items = items[: args.max]
    elif args.prefix:
        # সাইটম্যাপে ঠিকানা-প্রিফিক্স ধরে একই গ্রন্থের সব পাঠ-পাতা
        allu = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.prefix)
        sel = [u for u in allu if norm(args.prefix).replace("", "") in norm(urllib.parse.unquote(u))
               .replace("", "")] if allu else []
        sel = sel or allu

        def _ord(u):
            t = urllib.parse.unquote(u)
            m = re.search(r"([০-৯]{1,3})\s*।?\s*([০-৯]{1,3})?", t)
            return (to_int(m.group(1)) if m and m.group(1) else 999,
                    to_int(m.group(2)) if m and m.group(2) else 0, len(t), t)
        sel = sorted(set(sel), key=_ord)
        print("প্রিফিক্স-মিল:", len(sel), flush=True)
        for u in sel[:3]:
            print("   ·", urllib.parse.unquote(u)[-55:])
        items = [(i, u) for i, u in enumerate(sel, start=args.start)]
        if args.max:
            items = items[: args.max]
    elif args.toc:
        url0 = args.url
        if not url0:
            cands = sitemap_urls(LESSON_SITEMAPS + TOPIC_SITEMAPS, args.match)
            cands = sorted(cands, key=lambda x: (0 if "/lessons/" in x else 1,
                                                 len(urllib.parse.unquote(x)), x))
            url0 = cands[0] if cands else None
        if not url0:
            sys.exit("সূচি-পাতা পাওয়া গেল না: " + args.match)
        print("সূচি:", urllib.parse.unquote(url0)[-60:], flush=True)
        toc = toc_links(url0)
        _k = norm((args.match.split() or [""])[0])
        # ভূমিকা/ইতিহাস-জাতীয় সূচি-টপিক বাদ; পাঠ-পাতা (কাণ্ড/মণ্ডল/অধ্যায়/০৭।০৫) রাখি
        def _is_text_page(u):
            t = urllib.parse.unquote(u)
            if _k and _k in norm(t):
                return True
            return bool(re.search(r"[০-৯]{1,2}\s*।\s*[০-৯]{1,2}", t)
                        or re.search(r"কাণ্ড|মণ্ডল|অধ্যায়|সূক্ত|বল্লী|খণ্ড", t))
        _tp = [u for u in toc if _is_text_page(u)]
        if len(_tp) >= 3:
            toc = _tp
        print("ভেতরের টপিক/লেসন:", len(toc), flush=True)
        items = [(i, u) for i, u in enumerate(toc, start=args.start)]
        if args.max:
            items = items[: args.max]
    elif args.series:
        pre = (args.match.split() or [""])[0].replace(" ", "-")
        allu = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        sel = [u for u in allu
               if ("/lessons/" + pre) in urllib.parse.unquote(u)
               or ("/topics/" + pre) in urllib.parse.unquote(u)]
        if not sel:
            sel = allu
        sel = sorted(set(sel), key=lambda x: (0 if "/lessons/" in urllib.parse.unquote(x) else 1,
                                              len(urllib.parse.unquote(x)), x))
        items = [(i, u) for i, u in enumerate(sel, start=args.start)]
        print("সিরিজ:", len(items), "পাতা")
        for _, u in items:
            print("   ·", urllib.parse.unquote(u)[-55:])
        if args.max:
            items = items[: args.max]
    elif args.chain:
        urls = [args.url] if args.url else []
        key = "/lessons/" + (args.match.split() or [""])[0].replace(" ", "-")
        if not urls:
            cands = sitemap_urls(LESSON_SITEMAPS + TOPIC_SITEMAPS, args.match)
            cands = sorted(cands, key=lambda x: (0 if key in urllib.parse.unquote(x) else 1,
                                                 len(x), x))
            urls = cands[:1]
        # ক্রম: «Next Lesson» শৃঙ্খল (একই গ্রন্থের সিরিজের ভেতরে)
        chain, seen = [], set()
        u = urls[0] if urls else None
        while u and u not in seen and (not args.max or len(chain) < args.max):
            if key and key not in urllib.parse.unquote(u):
                break
            seen.add(u)
            h = get(u)
            if not h:
                break
            chain.append(u)
            nu = lesson_next(h)
            if not nu or nu in seen or not nu.startswith("http"):
                break
            u = nu
            time.sleep(0.4)
        items = [(i, u) for i, u in enumerate(chain, start=args.start)]
    else:
        allu = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        if args.chain or (args.by_ordinal and not any("/topics/" in u for u in allu)):
            # লেসন-পাতার সিরিজ: প্রথম লেসন থেকে «Next Lesson» শৃঙ্খলে সব পাতা
            key = "/lessons/" + (args.match.split() or [""])[0].replace(" ", "-")
            urls = sorted(allu, key=lambda x: (0 if key in urllib.parse.unquote(x) else 1,
                                              len(x), x))
            chain, seen = [], set()
            u = urls[0] if urls else None
            while u and u not in seen and (not args.max or len(chain) < args.max):
                if key and key not in urllib.parse.unquote(u):
                    # অন্য গ্রন্থের সিরিজে ঢুকে পড়া রোধ

                    break
                seen.add(u)
                h = get(u)
                if not h:
                    break
                chain.append(u)
                nu = lesson_next(h)
                if not nu or nu in seen:
                    break
                u = nu
                time.sleep(0.3)
            items = [(i, u) for i, u in enumerate(chain, start=args.start)]
            print("শৃঙ্খল:", len(items), "পাতা")
            for _, u in items:
                print("   ·", urllib.parse.unquote(u)[-55:])
        elif args.by_ordinal:
            # আগে শিরোনামের সংখ্যা («ঋগ্বেদ-০২।০৫») ধরে মিলাই — ওয়েবে
            # «প্রথম/দ্বিতীয়» শব্দ না থাকলে পুরনো পথ কিছুই পেত না।
            num = (args.want or "").split("।")[0].strip()
            pairs, seen_o = [], set()
            if num:
                for u in allu:
                    t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
                    m = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।", t)
                    if m and to_int(m.group(1)) == to_int(num):
                        o, _ = ordinal_of(u)
                        if o and o not in seen_o:
                            seen_o.add(o)
                            pairs.append((o, u))
            if not pairs and num:             # সাইটম্যাপ অসম্পূর্ণ — যা পাওয়া গেছে তা থেকেই
                for u in _ALL:
                    if "/topics/" not in u:
                        continue
                    t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
                    m = re.match(r"^[^০-৯0-9]*?([০-৯]{1,2})\s*।", t)
                    if m and to_int(m.group(1)) == to_int(num):
                        o, _ = ordinal_of(u)
                        if o and o not in seen_o:
                            seen_o.add(o)
                            pairs.append((o, u))
                if pairs:
                    print(f"   (মণ্ডল {num}: সূচি থেকেই {len(pairs)}টি সূক্ত-পাতা)",
                          flush=True)
            if not pairs and num:             # মণ্ডলভিত্তিক সূচি সরাসরি
                for u in mandala_links(to_int(num)):
                    o, _ = ordinal_of(u)
                    if o and o not in seen_o:
                        seen_o.add(o)
                        pairs.append((o, u))
                if pairs:
                    print(f"   (মণ্ডল {num}: সূচি-পাতা থেকে {len(pairs)}টি সূক্ত-পাতা)",
                          flush=True)
            if not pairs:                     # পুরনো পথ (প্রথম/দ্বিতীয়…)
                for u in allu:
                    if "/topics/" not in u:
                        continue
                    o, _ = ordinal_of(u)
                    if o and o not in seen_o:
                        seen_o.add(o)
                        pairs.append((o, u))
            pairs.sort()
            items = [(o, u) for o, u in pairs]
            print("ক্রম:", [o for o, _ in pairs])
        else:
            items = [(i, u) for i, u in enumerate(allu, start=args.start)]
        if args.max:
            items = items[: args.max]

    if args.only_unsaved and not args.into_chapter:
        have = set()
        old = _existing(out_dir)
        for c in (old or {}).get("chapters", []):
            have.add(c.get("id"))
        keep = []
        for i, u in items:
            t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
            m = re.match(r"^[^০-৯0-9]*?[০-৯]{1,2}\s*।\s*([০-৯]{1,3})", t)
            if m and to_int(m.group(1)) in have:
                continue
            keep.append((i, u))
        print(f"আগেই আছে {len(items) - len(keep)}টি; নতুন নামাব "
              f"{len(keep)}টি", flush=True)
        items = keep

    print(f"নামানো হবে {len(items)}টি পাতা")
    chapters = []

    # ---- সব পাতা এক খণ্ডে (যেমন ঋগ্বেদের ১০ম মণ্ডল) ----
    # দত্তের সংস্করণে মণ্ডলভিত্তিক ফাইল; তাই প্রতি সূক্ত আলাদা খণ্ড নয়, সব
    # মন্ত্র একটি ch<N>.json-এ ক্রমে জমা হয়।
    if args.into_chapter:
        n_ch = args.into_chapter
        have = _existing(out_dir) or {}
        prev = next((c for c in have.get("chapters", []) if c["id"] == n_ch), None)
        offset = prev["count"] if prev else 0
        done_pages = set()
        if prev:
            try:
                with open(os.path.join(out_dir, f"ch{n_ch}.json"), encoding="utf-8") as f:
                    done_pages = set(json.load(f).get("pages", []))
            except Exception:
                done_pages = set()
        if args.only_unsaved and done_pages:
            skip = [u for _, u in items
                    if urllib.parse.unquote(u.rstrip("/").split("/")[-1]) in done_pages]
            items = [(i, u) for i, u in items if u not in skip]
            print(f"আগেই আছে {len(skip)}টি সূক্ত-পাতা; নতুন {len(items)}টি", flush=True)
        if not items:
            print("✓ নতুন কিছু নেই — ১০ম মণ্ডল ইতিমধ্যেই হালনাগাদ")
            print(f"   (সাইটম্যাপে দেখা URL: {len(_ALL)})", flush=True)
            return
        verses, done = [], 0
        for idx_, u in items:
            # এক পাতা ব্যর্থ হলে পুরো রান থামে না — বাকিগুলো নামিয়ে রাখি,
            # পরের রানে --only-unsaved ওই পাতাগুলোই আবার চেষ্টা করবে।
            try:
                txt = fetch_paged(u)
                vs = parse_verses(txt)
            except SystemExit:
                print("   ! উৎস বেশি ব্যর্থ — বাকি পাতা পরে নামানো হবে")
                break
            except Exception as e:
                print(f"   ✗ {idx_}: {type(e).__name__} — পরে আবার চেষ্টা হবে")
                continue
            if not vs:
                print(f"   ✗ {idx_}: মন্ত্র পাওয়া যায়নি")
                continue
            label = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
            for v in vs:
                for part in split_oversized(v):
                    part = dict(part)
                    src = part.pop("src", None)      # উৎস-নম্বর (২৪৩) — ক্রম নয়
                    part["n"] = offset + len(verses) + 1
                    if src and not part.get("seg"):
                        part["seg"] = src
                    verses.append(part)
            # ⚠ উৎসের «(২৪৩)» সংখ্যাগুলো রিগ্বেদ-ক্রম, সূক্তের ভেতরের ১…n নয়।
            #   তাই প্রতি সূক্ত-পাতার পরে ক্রম আবার ১ থেকে শুরু করি।
            if args.slug == "samaveda":
                base = offset
                for i, v in enumerate(verses[base:], 1):
                    v["n"] = i          # প্রতি সূক্তে ১…n
            done += 1
            print(f"   ✓ {label}: {len(vs)} মন্ত্র (মোট {len(verses)})", flush=True)
            if args.max and done >= args.max:
                break
            time.sleep(0.4)
        if not verses:
            print("⛔ কোনো মন্ত্র পাওয়া গেল না — কিছু লেখা হবে না")
            sys.exit(3)
        title = args.title or args.slug
        ch = write_chapter(out_dir, n_ch, title, verses, BASE + "/topics/…")
        # কোন কোন উৎস-পাতা থেকে জমানো হলো — পরে যেন একই পাতা দুইবার না নামে
        try:
            pg = os.path.join(out_dir, f"ch{n_ch}.json")
            with open(pg, encoding="utf-8") as f:
                obj = json.load(f)
            obj["pages"] = sorted(done_pages | {
                urllib.parse.unquote(u.rstrip("/").split("/")[-1])
                for _, u in items})
            obj["bn"] = f"{title} — মণ্ডল {n_ch}" if args.slug == "rigveda" else obj["bn"]
            with open(pg, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
            ch["bn"] = obj["bn"]
        except Exception as e:
            print("   ! পাতা-তালিকা রাখা গেল না:", e)
        if args.slug:
            idxd = write_index_guarded(out_dir, args.slug, title, [ch],
                                       args.word, own_words)
            if not idxd:
                print("⛔ ইনডেক্স লেখা হয়নি — পুরনো ডেটা অটুট")
                sys.exit(3)
            print(f"{args.slug}: বাংলা {idxd['withBn']}/{idxd['total']} · "
                  f"{len(idxd['chapters'])} খণ্ড")
        return

    if args.group_by_num:
        # শিরোনাম-সংখ্যা ধরে ভাগ: (অধ্যায়, উপক্রম) অনুসারে সাজিয়ে এক ফাইলে জমা
        pairs = []
        for u in (u for _, u in items):
            t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
            nums = re.findall(r"([০-৯]{1,3})\s*[।.]\s*([০-৯]{1,3})", t)
            if nums:
                a, b = to_int(nums[0][0]), to_int(nums[0][1])
                pairs.append((a, b, u))
        pairs.sort()
        print(f"সংখ্যা-শিরোনাম পাওয়া গেল {len(pairs)}টিতে")
        bucket, curv, curch = {}, None, None
        for a, b, u in pairs:
            if a != curch:
                curch = a
                bucket.setdefault(a, [])
                curv = 0
            vs = parse_verses(fetch_paged(u))
            if not vs:
                print(f"   ✗ {a}.{b}")
                continue
            for v in vs:
                curv += 1
                v = dict(v)
                v["n"] = curv
                bucket[a].append(v)
            print(f"   ✓ {a}.{b}: {len(vs)}")
            time.sleep(0.25)
        for a in sorted(bucket):
            if not bucket[a]:
                continue
            title = f"{args.title} — {a}" if args.title else f"অধ্যায় {a}"
            chapters.append(write_chapter(out_dir, a, title, bucket[a],
                                          BASE + "/topics/…"))
        if args.slug and chapters:
            idx = write_index_guarded(out_dir, args.slug, args.title or args.slug,
                                      chapters, args.word)
            if not idx:
                print("\n" + "=" * 60)
                print("⛔ এই রানে ইনডেক্স লেখা হয়নি — পুরনো ডেটাই অটুট আছে।")
                print("=" * 60)
                return
            rep = [f"{args.slug}: বাংলা {idx['withBn']}/{idx['total']}"]
            rep += [f"  {c['id']}. {c['bn'][:44]}: {c['withBn']}/{c['count']}"
                    for c in idx["chapters"]]
            with open(os.path.join(args.out, f"_fetch_report_{args.slug}.txt"), "w",
                      encoding="utf-8") as f:
                f.write("\n".join(rep) + "\n")
            print("\n".join(rep))
        return

    for idx, u in items:
        print(f"[{idx}] {urllib.parse.unquote(u)[-60:]}")
        txt = fetch_paged(u)
        vs = parse_verses(txt)
        if not vs:
            print("   ✗ মন্ত্র পাওয়া যায়নি")
            continue
        tail_t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
        tail_t = re.sub(r"[-–_]+", " ", tail_t).strip()
        if args.title:
            title = args.title if norm(tail_t) in norm(args.title) else f"{args.title} — {tail_t}"
        else:
            title = tail_t or f"অধ্যায় {idx}"
        print(f"   ✓ {len(vs)} {args.word}")
        # ⚠ পাঠের নম্বর সব সময় ১…n — উৎসের «(২৪৩)» রিগ্বেদ-সংখ্যা `seg`-এ থাকে।
        #   পার্সার নিজেই ১…n দেয়, তবু n_override থাকলে সেটি এখানে ঠিক করে দিই।
        if args.slug == "samaveda":
            for i, v in enumerate(vs, 1):
                v["n"] = i
        chapters.append(write_chapter(out_dir, idx, title, vs, u))
        time.sleep(0.4)

    if args.slug and chapters:
        idx = write_index_guarded(out_dir, args.slug, args.title or args.slug,
                                  chapters, args.word)
        if not idx:
            print("\n" + "=" * 60)
            print("⛔ এই রানে ইনডেক্স লেখা হয়নি — পুরনো ডেটাই অটুট আছে।")
            print("=" * 60)
            sys.exit(3)
        rep = [f"{args.slug}: বাংলা {idx['withBn']}/{idx['total']}"]
        rep += [f"  {c['id']}. {c['bn'][:44]}: {c['withBn']}/{c['count']}"
                for c in idx["chapters"]]
        with open(os.path.join(args.out, f"_fetch_report_{args.slug}.txt"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(rep) + "\n")
        print("\n".join(rep))




def main():  # noqa: F811  (CLI প্রবেশ-বিন্দু)
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--title", default="")
    ap.add_argument("--match", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--out", default="assets/grantho/data")
    ap.add_argument("--word", default="মন্ত্র")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--by-ordinal", action="store_true")
    ap.add_argument("--chain", action="store_true")
    ap.add_argument("--book-toc", action="store_true",
                    help="বই-পাতার প্রতিটি লেসনের ভেতরের টপিক (আসল শ্লোক-পাতা)")
    ap.add_argument("--prefix", default="",
                    help="সাইটম্যাপে এই ঠিকানা-অংশ থাকা সব পাতা (গ্রন্থ-সিরিজ)")
    ap.add_argument("--toc", action="store_true",
                    help="কোর্স-পাতার ভেতরের সব টপিক/লেসন (প্রতিটি = এক অধ্যায়)")
    ap.add_argument("--series", action="store_true",
                    help="একই গ্রন্থের সব লেসন/টপিক পাতা (base, -2, -3 …)")
    ap.add_argument("--book", action="store_true")
    ap.add_argument("--book-auto", action="store_true",
                    help="--match দিয়ে বই-পাতা খুঁজে তার সূচি থেকে সব লেসন")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--group-by-num", action="store_true")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--dump", type=int, default=0)
    ap.add_argument("--only-unsaved", action="store_true",
                    help="কেবল যেসব খণ্ড এখনো ডেটায় নেই সেগুলো নামাও "
                         "(আগের ডেটা অটুট থাকে)")
    ap.add_argument("--into-chapter", type=int, default=0,
                    help="সব নামানো পাতা একটি খণ্ডে (যেমন মণ্ডল ১০) জমা করো")
    ap.add_argument("--want", default="",
                    help='কেবল এই মণ্ডল/পর্বের পাতা, যেমন "১০" বা "১০।০৫"')
    args = ap.parse_args()
    if args.auto:
        return run_auto(args)
    if args.discover:
        urls = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        print(f"মিলেছে {len(urls)}")
        for u in urls:
            print(" ", urllib.parse.unquote(u))
        return
    return main_run(args)


if __name__ == "__main__":
    main()
