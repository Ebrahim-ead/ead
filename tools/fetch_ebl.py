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
            print(f"   ! HTTP {e.code} — {url[-50:]} (চেষ্টা {i+1})")
            time.sleep(min(30, 4 * (i + 1)))
        except Exception as e:
            print(f"   ! {type(e).__name__} — {url[-50:]} (চেষ্টা {i+1})")
            time.sleep(min(30, 4 * (i + 1)))
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

VERSE_TAIL = re.compile(r"[॥|]{1,2}\s*([০-৯०-९]{1,3})\s*[॥|]{0,2}\s*$")
NUMHEAD = re.compile(r"^([০-৯]{1,3})\s*[।\.]\s*(.+)$")
LBL = re.compile(r"^(অন্বয়|সরলার্থ|মন্তব্য|ভাষ্য|টীকা|ব্যাখ্যা)\s*[:\-–—]?\s*")
MTRA = re.compile(r"^মন্ত্র\s*[:\-–—]?\s*")
ARTH = re.compile(r"^অর্থ\s*[:ঃ]?\s*[\-–—]*\s*")
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


def parse_verses(txt, bn_meaning=False):
    """পাতার পাঠ → [{'n','sk','anv','bn','bnNote'}]।

    গঠন:
      ক. 업নিষদ/ছান্দোগ্য: সংস্কৃত-ব্লক → «অন্বয়:» → «সরলার্থ:» → «ব্যাখ্যা:»
      খ. সামবেদ: «মন্ত্র : …» → «অর্থ : …»
      গ. পুরাণ: সংস্কৃত প্যারা → বাংলা প্যারা (লেবেলহীন)
      ঘ. ঋগ্বেদ: সংখ্যাযুক্ত বাংলা অনুচ্ছেদ
    """
    if not bn_meaning:
        dev = len(re.findall(r"[\u0900-\u0963\u0966-\u097F]", txt))
        multiline = len([x for x in txt.splitlines() if len(x.strip()) > 12])
        if dev < 200 and multiline > 30:
            bn_meaning = True          # সংস্কৃত মূল নেই ⇒ বাংলা-লিপিতেই পাঠ
    txt = txt.replace("।।", "॥").replace("||", "॥")
    if "অন্বয়" not in txt and "সরলার্থ" not in txt:
        txt = re.sub(r"\s+(?=[০-৯]{1,3}\s*।\s)", "\n", txt)
    labelled = ("অন্বয়" in txt or "সরলার্থ" in txt or "মন্ত্র :" in txt
                or "মন্ত্র:" in txt or "অর্থ" in txt)

    out, cur = [], None

    def split_by_danda(lines):
        """«॥১২॥» / «॥৩-৪॥» চিহ্ন ধরে শ্লোক-ব্লক ভাগ।"""
        groups, acc = [], []
        for ln in lines:
            acc.append(ln)
            m = re.search(r"[॥]\s*([০-৯०-९]{1,3})(?:\s*[-–]\s*[০-৯०-९]{1,3})?\s*[॥]\s*$", ln)
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

    def flush_pending(pend, verse_label):
        """pending লাইন: শেষের সংস্কৃত-ব্লক = শ্লোক, তার আগেরটা ব্যাখ্যা-ধারাবাহিকতা।"""
        if not pend:
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

    if labelled:
        pend = []
        for raw in txt.split("\n"):
            ln = raw.strip()
            if not ln or ln in (",", "|") or ln.startswith("## ") or "||" in ln:
                continue
            m = MTRA.match(ln)
            if m:
                flush_pending(pend, False)
                pend = []
                rest = re.sub(r"^\(\s*[০-৯]{1,3}\s*\)\s*", "", ln[m.end():]).strip()
                add_verse([rest])
                continue
            a = ARTH.match(ln)
            if a:
                flush_pending(pend, False)
                pend = []
                if cur is None or cur["bn"]:
                    add_verse([])
                cur["part"] = "bn"
                r = re.sub(r"^\(\s*[০-৯]{1,3}\s*\)\s*", "", ln[a.end():]).strip()
                if r:
                    cur["bn"].append(r)
                continue
            l = LBL.match(ln)
            if l:
                g = l.group(1)
                rest = ln[l.end():].strip()
                if g == "অন্বয়":
                    if pend:
                        flush_pending(pend, True)
                        pend = []
                    elif cur is None:
                        add_verse([])
                    cur["part"] = "anv"
                else:
                    if pend:
                        flush_pending(pend, True)
                        pend = []
                    if cur is None:
                        add_verse([])
                    if g == "সরলার্থ" and cur["bn"]:
                        add_verse([])
                    cur["part"] = {"সরলার্থ": "bn"}.get(g, "note")
                if rest:
                    cur[cur["part"]].append(rest)
                continue
            pend.append(ln)
        flush_pending(pend, False)
    else:
        started = False
        for raw in txt.split("\n"):
            ln = raw.strip()
            if not ln or ln in (",", "|") or ln.startswith("## ") or "||" in ln:
                continue
            nm = NUMHEAD.match(ln)
            is_dev = bool(DEV_RE.search(ln))
            is_bn_sk = (not is_dev) and _is_bn_verse(ln)
            if is_bn_sk and bn_meaning:
                if cur is None or cur["bn"]:
                    add_verse([])
                cur["part"] = "bn"
                cur["bn"].append(ln)
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
                if cur is not None and cur["bn"]:
                    add_verse([])
                add_verse([])
                cur["part"] = "bn"
                cur["n"] = to_int(nm.group(1))
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
    res, auto = [], 0
    for v in out:
        bn = re.sub(r"\s+", " ", " ".join(v["bn"])).strip()
        bn = re.sub(r"^\(\s*[০-৯०-९]{1,3}\s*\)\s*", "", bn)
        bn = re.sub(r"\s*Bookmark\s*$", "", bn)
        if len(bn) < 8:
            continue
        sk = re.sub(r"[ \t]+", " ", " ".join(v["sk"])).strip()
        if labelled and not sk:
            continue                     # সংস্কৃতহীন ভূমিকা/অনুচ্ছেদ বাদ
        n = v["n"] or last_of(v["sk"])
        if n:
            auto = n
        else:
            auto += 1
            n = auto
        res.append({"n": n, "sk": sk, "anv": " ".join(v["anv"]).strip(),
                    "bn": bn, "bnNote": " ".join(v["note"]).strip()})
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
            dec = norm(urllib.parse.unquote(u))
            if pat in dec and u not in seen:
                seen.add(u)
                urls.append(u)
    return urls


def book_lessons(book_url):
    """বই-পাতার সূচি থেকে লেসন-সংযোগ (ক্রম অপরিবর্তিত)।"""
    h = get(book_url)
    if not h:
        return []
    out, seen = [], set()
    for m in re.finditer(r'href="(https://www\.ebanglalibrary\.com/lessons/[^"#?]+)"', h):
        u = htmllib.unescape(m.group(1))
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def ordinal_of(url):
    t = urllib.parse.unquote(url)
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


def fetch_paged(url, max_pages=40):
    """এক পাতার সব পৃষ্ঠা («Next Page» ধরে) জোড়া দেয়।"""
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
        nu = next_page_link(h)
        if not nu or nu in seen:
            break
        u = nu
        time.sleep(0.25)
    return "\n\n".join(parts)


def write_chapter(out_dir, idx, title, verses, url):
    vs = []
    for v in verses:
        d = {"n": v["n"], "sk": v["sk"], "bn": v["bn"], "spk": "", "bnSrc": SRC}
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


def main_run(args):
    if getattr(args, "auto", False):
        return run_auto(args)

    if args.discover:
        urls = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        print(f"মিলেছে {len(urls)}")
        for u in urls:
            print(" ", urllib.parse.unquote(u))
        return

    out_dir = os.path.join(args.out, args.slug) if args.slug else ""

    if args.url and not (args.book or args.chain or args.group_by_num):
        # একক পাতা (পরীক্ষা/ডাম্প)
        h = get(args.url)
        txt = fetch_paged(args.url)
        vs = parse_verses(txt)
        print(f"মন্ত্র: {len(vs)}")
        for v in vs[: args.dump or 3]:
            print(f" {v['n']} | sk: {v['sk'][:80]}")
            print(f"    bn: {v['bn'][:100]}")
            if v["bnNote"]:
                print(f"    note: {v['bnNote'][:60]}")
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
            pairs, seen_o = [], set()
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

    print(f"নামানো হবে {len(items)}টি পাতা")
    chapters = []

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
            idx = build_index(out_dir, args.slug, args.title or args.slug,
                              chapters, args.word)
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
        chapters.append(write_chapter(out_dir, idx, title, vs, u))
        print(f"   ✓ {len(vs)} {args.word}")
        time.sleep(0.4)

    if args.slug and chapters:
        idx = build_index(out_dir, args.slug, args.title or args.slug, chapters, args.word)
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
