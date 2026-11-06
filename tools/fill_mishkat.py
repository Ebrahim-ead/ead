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
import collections
import html as html_mod
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
# «হাদীস নং:২» / «হাদীস নং ২» / «হাদিস নম্বর: 2» — বাংলা ও ইংরেজি অঙ্ক দুটোই
NO_LABEL_RE = re.compile(r"হাদ[ীি]স\s*(?:নং|নম্বর|নম্বার)\s*[:：]?\s*([০-৯0-9]+)")
PROBE_DIR = os.path.join(DATA, "_debug", "mishkat", "probe")
FAILED_DIR = os.path.join(DATA, "_debug", "mishkat", "failed")
ZERO_W = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
TITLE_RE = re.compile(r"মিশকাতুল\s*মাসাব")        # «মিশকাতুল মাসাবীহ» (ZWNJ-সহও)


def norm(s: str) -> str:
    return ZERO_W.sub("", s)


def bn_digits(n: int) -> str:
    """৫৮৮ → '৫৮৮' (বাংলা অঙ্কে)।"""
    return "".join(BN[int(c)] for c in str(n))


def page_numbers(html_src: str) -> list[int]:
    """পাতায় লেখা সব «হাদীস নং …» নম্বর (বাংলা/ইংরেজি অঙ্ক)।"""
    return [bn2num(m.group(1)) for m in NO_LABEL_RE.finditer(norm(html_src))]


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


def _obj_before(payload: str, idx: int) -> dict | None:
    """idx-এর আগের '{' থেকে পূর্ণ JSON অবজেক্ট পড়া (ভেতরের থেকে বাইরের দিকে)।"""
    start = payload.rfind("{", 0, idx)
    for _ in range(8):
        if start < 0:
            return None
        try:
            obj, _ = JSON_VAL.raw_decode(payload, start)
        except Exception:                            # noqa: BLE001
            start = payload.rfind("{", 0, start)
            continue
        if isinstance(obj, dict) and "hadith_number" in obj:
            return obj
        start = payload.rfind("{", 0, start)
    return None


def _walk_dicts(obj, out: list, depth: int = 0) -> None:
    """JSON-এর ভেতরে থাকা সব অবজেক্ট বের করা (হাদিস-অবজেক্ট যেখানেই থাকুক)।"""
    if depth > 14:
        return
    if isinstance(obj, dict):
        out.append(obj)
        for v in obj.values():
            _walk_dicts(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:400]:
            _walk_dicts(v, out, depth + 1)


def find_hadith_items(payload: str, rows: dict | None = None) -> list[dict]:
    """হাদিস-অবজেক্ট খোঁজে — গঠন যাই হোক।

    আগে শুধু `"hadiths": [ … ]` নেস্টেড অ্যারে দেখা হতো। একক-হাদিস পাতায়
    (`/hadith/<id>`) গঠন আলাদা হওয়ায় কিছুই মিলত না — ফলে ১,৩৫১টি পাতাই বাদ
    পড়েছিল। এখন তিন পথে খোঁজা হয়:
      ১. rows-এর পার্স করা JSON-এ `hadith_number`-ওয়ালা অবজেক্ট
      ২. `"hadiths": [` নেস্টেড অ্যারে (পুরোনো পথ)
      ৩. কাঁচা পেলোডে `"hadith_number"`-এর আশপাশের অবজেক্ট
    """
    out: list[dict] = []
    seen: set = set()

    def add(o) -> None:
        if not isinstance(o, dict) or "hadith_number" not in o:
            return
        key = (str(o.get("hadith_number")), str(o.get("description"))[:24],
               str(o.get("description_ar"))[:24])
        if key in seen:
            return
        seen.add(key)
        out.append(o)

    if rows:
        found: list = []
        for v in rows.values():
            _walk_dicts(v, found)
        for o in found:
            add(o)
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
                for item in arr:
                    if isinstance(item, dict):
                        for x in (item.get("hadiths") or []):
                            add(x)
                        add(item)
            pos = payload.rfind("[", 0, pos)
    for m in re.finditer(r'"hadith_number"\s*:', payload):
        add(_obj_before(payload, m.start()))
    return out


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


# --------------------------------------------- রেন্ডার-করা HTML থেকে পাঠ (ফলব্যাক)
SCRIPT_RE = re.compile(r"(?is)<(script|style|noscript|template|svg)[^>]*>.*?</\1>")
BLOCK_RE = re.compile(r"(?i)</?(?:p|div|br|li|h[1-6]|section|article|tr|td|blockquote|pre|figure|figcaption|header|footer)[^>]*>")
TAG_RE = re.compile(r"(?s)<[^>]+>")
AR_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff]")
STOP_MARKERS = (
    "পূর্ববর্তী", "পরবর্তী", "আরবী দেখুন", "হাদীসের ব্যাখ্যা", "মুসলিম বাংলা",
    "কপিরাইট", "সব হাদীস", "হোমপেজ", "অনুসন্ধান", "শেয়ার করুন", "মন্তব্য",
    "সূচিপত্র", "পরবর্তী পৃষ্ঠা", "পূর্ববর্তী পৃষ্ঠা",
)


CODE_RE = re.compile(r"(?s)self\.__next_f\.push\(.*?\)\s*(?=<|$)")
CODE_HINTS = ("self.__next_f", "__NEXT_", "function(", "=>", "undefined",
              '\\"', '{"', "window.", "document.")
CODE_PUNCT = set('{}[]\\":;|<>=$')


def looks_like_code(ln: str) -> bool:
    """JS/JSON-এর টুকরো কি না — হাদিসের পাঠ বলে ভুল করে ঢুকিয়ে দেওয়া চলবে না।"""
    if any(h in ln for h in CODE_HINTS):
        return True
    letters = [c for c in ln if not c.isspace()]
    if not letters:
        return False
    punct = sum(1 for c in letters if c in CODE_PUNCT)
    return punct / len(letters) > 0.08


def html_text(html_src: str) -> str:
    """রেন্ডার-করা পাতার দৃশ্যমান টেক্সট, লাইনে লাইনে (সার্ভার-সাইড রেন্ডার হওয়ায়
    হাদিসের পাঠ HTML-এই থাকে — RSC না মিললে এখান থেকে তোলা যায়)।"""
    t = SCRIPT_RE.sub("\n", html_src)
    t = CODE_RE.sub("\n", t)          # <script>-এর বাইরে থাকা RSC-পুশও বাদ
    t = BLOCK_RE.sub("\n", t)
    t = TAG_RE.sub(" ", t)
    t = html_mod.unescape(norm(t))
    t = t.replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def is_arabic(ln: str) -> bool:
    letters = [c for c in ln if not c.isspace()]
    if len(letters) < 8:
        return False
    return sum(1 for c in letters if AR_RE.match(c)) / len(letters) > 0.5


def parse_from_html(html_src: str, n: int) -> tuple[dict | None, str]:
    """রেন্ডার-করা টেক্সট থেকে একক হাদিস তোলা (শেষ উপায়)।"""
    lines = html_text(html_src).split("\n")
    lead = bn_digits(n)
    li = next((i for i, ln in enumerate(lines)
               if any(bn2num(m.group(1)) == n for m in NO_LABEL_RE.finditer(ln))), None)
    if li is None:
        return None, "html:লেবেল-নেই"
    sec = ""
    for ln in lines[max(0, li - 10):li + 10]:
        m = re.match(r"^অধ্যায়[ঃ:]\s*(.+)$", ln.strip())
        if m:
            sec = clean(m.group(1))
            break
    start_i = None
    for i in range(li, min(len(lines), li + 30)):     # «৫৮৮। …» দিয়ে শুরু হলে নিশ্চিত
        ln = lines[i].strip()
        if ln.startswith(lead + "।") or ln.startswith(lead + "."):
            start_i = i
            break
    if start_i is None:
        for i in range(li, min(len(lines), li + 30)):
            ln = lines[i].strip()
            if (len(ln) > 150 and not is_arabic(ln) and not looks_like_code(ln)
                and not any(mk in ln for mk in STOP_MARKERS)):
                start_i = i
                break
    if start_i is None:
        return None, "html:পাঠ-শুরু-মেলেনি"
    bn_lines, i = [], start_i
    while i < len(lines) and sum(map(len, bn_lines)) < 30000:
        ln = lines[i].strip()
        if is_arabic(ln) or looks_like_code(ln) or any(mk in ln for mk in STOP_MARKERS):
            break
        if ln:
            bn_lines.append(ln)
        i += 1
    ar_lines = []
    while i < len(lines) and sum(map(len, ar_lines)) < 30000:
        ln = lines[i].strip()
        if not is_arabic(ln):
            break
        # «كتاب الإيمان» / «الفصل الاول» শিরোনাম — মূল পাঠ নয়
        if not (len(ln) < 60 and re.match(r"^(كتاب|الفصل|باب)", ln)):
            ar_lines.append(ln)
        i += 1
    bn_txt = LEAD_NUM_RE.sub("", clean("\n".join(bn_lines)))
    ar_txt = clean("\n".join(ar_lines))
    if len(bn_txt) < 40 and len(ar_txt) < 40:
        return None, "html:পাঠ-খালি"
    v = {"i": n, "b": bn_txt, "a": ar_txt, "n": ""}
    if sec:
        v["s"] = sec
    return v, "html"


# ------------------------------------------------------------------ parse
TAG_DROP_RE = re.compile(r"(?i)<(?!br\s*/?>)[^>]{0,120}>")
TAG_BLOCK_DROP_RE = re.compile(
    r"(?is)<(script|style|iframe|object|embed|svg)[^>]*>.*?</\1\s*>")


def safe_text(s: str) -> str:
    """<br> অটুট রাখি (রিডার innerHTML-এ লাইন-ব্রেক দেখায়, বিদ্যমান ৪,৬৮৭টি
    হাদিসেও তাই আছে); অন্য যেকোনো ট্যাগ বাদ — পাঠে HTML ঢোকা চলবে না।"""
    if not isinstance(s, str):
        return s
    return TAG_DROP_RE.sub("", TAG_BLOCK_DROP_RE.sub("", s))


def section_of(item: dict) -> str:
    """অনুচ্ছেদ-শিরোনাম: chapter-পাতায় titles.title, একক পাতায় title/sub_title।"""
    t = item.get("titles")
    if isinstance(t, dict):
        v = clean(t.get("title"))
        if v:
            return v
    head, sub = clean(item.get("title")), clean(item.get("sub_title"))
    if head and sub:
        return f"{head} - {sub}"
    return head or sub


def item_to_verse(rows: dict, item: dict, n: int) -> dict | None:
    bn = safe_text(clean(deref(rows, item.get("description"))))
    ar = safe_text(clean(deref(rows, item.get("description_ar"))))
    if not (bn or ar):
        return None
    v = {"i": n, "b": LEAD_NUM_RE.sub("", bn), "a": ar, "n": ""}
    g = clean((item.get("type") or {}).get("title"))
    if g:
        v["g"] = g
        v["gc"] = grade_class(g)
    sec = section_of(item)
    if sec:
        v["s"] = sec
    tah = safe_text(clean(deref(rows, item.get("tahqeeq_explanation"))))
    if tah:
        v["tah"] = tah
    return v


def parse_hadith_page_ex(html_src: str, n: int) -> tuple[dict | None, str]:
    """এক পাতার একক হাদিস → (রিডার-ফরম্যাট, কীভাবে পাওয়া গেল)।

    যাচাই কড়া: পাতার «হাদীস নং» লেবেলে n মিলতেই হবে, নয়তো বাদ —
    অনুমান-পাঠ নয়। ফল না মিললে দ্বিতীয় উপাদানে কারণ ফেরে (রিপোর্টের জন্য)।
    """
    nums = page_numbers(html_src)
    payload = flight_payload(html_src)
    rows = flight_rows(payload)
    items = find_hadith_items(payload, rows)
    if n not in nums:
        # লেবেল না মিললে পাতাটাই অন্য হাদিসের (বা নামেনি) — RSC-তে মিললেও নয়
        if not any(bn2num(h.get("hadith_number")) == n for h in items):
            return None, "ব্যর্থ:নম্বর-মেলেনি(লেবেল %s)" % (nums[:3] or "নেই")
    exact = [h for h in items if bn2num(h.get("hadith_number")) == n]
    if exact:
        v = item_to_verse(rows, exact[0], n)
        if v:
            return v, "payload:নম্বর-মিল"
    if len(items) == 1 and n in nums:
        v = item_to_verse(rows, items[0], n)
        if v:
            return v, "payload:একক"
    if n in nums:
        return parse_from_html(html_src, n)
    return None, "ব্যর্থ:হাদিস-অবজেক্ট-নেই(items=%d)" % len(items)


def parse_hadith_page(html_src: str, n: int) -> dict | None:
    return parse_hadith_page_ex(html_src, n)[0]


def _keysets(obj, census: collections.Counter, depth: int = 0) -> None:
    """JSON-গঠনের আদমশুমারি — হাদিস-অবজেক্টের ফিল্ড-নাম আসলে কী, তা দেখায়।"""
    if depth > 12:
        return
    if isinstance(obj, dict):
        census[tuple(sorted(obj.keys()))] += 1
        for v in obj.values():
            _keysets(v, census, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:200]:
            _keysets(v, census, depth + 1)


def _long_strings(rows: dict, out: list, depth: int = 0) -> None:
    """দীর্ঘ টেক্সট কোন পাথে (JSON-path) বসে আছে — বাংলা/আরবি পাঠের ঠিকানা।"""
    for key, val in rows.items():
        stack = [(f"${key}", val, 0)]
        while stack:
            path, v, d = stack.pop()
            if d > 10:
                continue
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    stack.append((f"{path}.{k2}", v2, d + 1))
            elif isinstance(v, list):
                for i2, v2 in enumerate(v[:60]):
                    stack.append((f"{path}[{i2}]", v2, d + 1))
            elif isinstance(v, str) and len(v) > 200:
                ar = sum(1 for c in v[:400] if AR_RE.match(c))
                out.append((path, len(v), "ar" if ar > 40 else "bn", v[:50]))


def probe(sample=None) -> str:
    """কয়েকটি পাতা নামিয়ে পার্সার কী দেখছে — বিস্তারিত রিপোর্ট + কাঁচা নমুনা।

    রিপোর্ট: `_debug/mishkat/fill_probe.txt` (commit-comment-এও ওঠে)
    কাঁচা নমুনা: `_debug/mishkat/probe/<n>.html` ও `<n>.flight.txt` — ব্র্যাঞ্চ থেকে
    পড়া যায়, তাই পাতার আসল গঠন দেখে পার্সার ঠিক করা সম্ভব।
    """
    gaps = missing_numbers()
    picks = list(sample or [])
    for ch, g in gaps.items():
        for a, b in g:
            for n in range(a, min(b, a + 1) + 1):
                if n not in picks:
                    picks.append(n)
        if len(picks) >= 3:
            break
    picks = picks[:3]
    os.makedirs(PROBE_DIR, exist_ok=True)
    lines = [f"probe: {len(picks)} পাতা · "
             f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}"]
    for n in picks:
        url = f"{BASE}/hadith/{PAGE0 + n}"
        try:
            html_src = get(url, sleep=0.4)
        except Exception as e:                       # noqa: BLE001
            lines.append(f"\n[{n}] ✗ নামানো যায়নি: {e}")
            continue
        payload = flight_payload(html_src)
        rows = flight_rows(payload)
        items = find_hadith_items(payload, rows)
        lines.append(f"\n[{n}] {url}")
        lines.append(f"  html {len(html_src)}B · flight {len(payload)}B · "
                     f"rows {len(rows)} · items {len(items)}")
        m = re.search(r"(?is)<title>(.*?)</title>", html_src)
        lines.append(f"  <title>: {clean(m.group(1))[:90] if m else '(নেই)'}")
        lines.append(f"  পাতার নম্বর-লেবেল: {page_numbers(html_src)[:6]}")
        lines.append("  items-এর hadith_number: %s"
                     % [str(i.get('hadith_number'))[:12] for i in items[:6]])
        census: collections.Counter = collections.Counter()
        for v in rows.values():
            _keysets(v, census)
        interesting = [k for k in census
                       if any(w in " ".join(k).lower() for w in
                              ("hadith", "description", "number", "title", "type"))]
        lines.append(f"  ফিল্ড-সেট (সংশ্লিষ্ট {len(interesting)}):")
        for k in sorted(interesting, key=lambda k: -census[k])[:8]:
            lines.append(f"    ×{census[k]} {list(k)[:12]}")
        longs: list = []
        _long_strings(rows, longs)
        lines.append(f"  দীর্ঘ টেক্সটের পাথ ({len(longs)}টি, প্রথম ৮):")
        for path, ln, kind, head in longs[:8]:
            lines.append(f"    {kind} {ln:>6}B {path[:60]} · {head[:36]!r}")
        v, how = parse_hadith_page_ex(html_src, n)
        if v:
            lines.append(f"  parse ✓ [{how}] বাংলা {len(v['b'])}B · আরবি {len(v['a'])}B"
                         + (f" · g={v.get('g', '')[:24]}" if v.get("g") else "")
                         + (f" · s={v.get('s', '')[:24]}" if v.get("s") else ""))
            lines.append(f"    b[:70]: {v['b'][:70]!r}")
        else:
            lines.append(f"  parse ✗ [{how}]")
        # কাঁচা নমুনা (প্রতিটি ৭০০ KB-এর বেশি নয়) — ব্র্যাঞ্চ থেকে পড়া যাবে
        open(os.path.join(PROBE_DIR, f"{n}.html"), "w",
             encoding="utf-8").write(html_src[:400_000])
        open(os.path.join(PROBE_DIR, f"{n}.flight.txt"), "w",
             encoding="utf-8").write(payload[:300_000])
    report = "\n".join(lines)
    os.makedirs(os.path.dirname(PROBE_DIR), exist_ok=True)
    open(os.path.join(os.path.dirname(PROBE_DIR), "fill_probe.txt"), "w",
         encoding="utf-8").write(report + "\n")
    print(report, flush=True)
    return report


def _write_stats(todo_n: int, ok: int, bad: int, hows: collections.Counter,
                 fails: dict, bonus: int = 0) -> None:
    """ফলের সারসংক্ষেপ `_debug/mishkat/fill_stats.txt`-এ (কমেন্টেও ওঠে)।"""
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    lines = [f"fill: চেষ্টা {todo_n} · সফল {ok} · ব্যর্থ {bad} · বোনাস {bonus} · "
             f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
             "কীভাবে পাওয়া গেল / কেন ব্যর্থ:"]
    for how, c in hows.most_common():
        lines.append(f"  {c:>5} × {how}")
    for reason, nums in sorted(fails.items(), key=lambda kv: -len(kv[1])):
        head = ", ".join(str(x) for x in nums[:12])
        lines.append(f"  উদাহরণ [{reason}] ({len(nums)}টি): {head}")
    txt = "\n".join(lines)
    open(os.path.join(os.path.dirname(CACHE), "fill_stats.txt"), "w",
         encoding="utf-8").write(txt + "\n")
    print(txt, flush=True)


# ------------------------------------------------- পাতা-ID খোঁজা (নম্বর → URL)
# উৎসের পাতা-ID সব জায়গায় 34945+n নয়: শেষ অধ্যায়গুলোতে (৫,৩৭৯+) হিসাব ১–২ ঘর
# সরে যায়, তাই ২৪০টি পাতা «নম্বর-মেলেনি» বলে বাদ পড়েছিল। এখন তিন ধাপে খোঁজা হয় —
# জানা ম্যাপ, আশপাশের অফসেট, আর পাতার নিজস্ব prev/next লিংক ধরে হাঁটা।
# যাচাই সবসময় কড়া: পাতার নিজস্ব নম্বর n হতে হবে, অন্য পাতা n বলে চলবে না।
PAGEMAP = os.path.join(DATA, "_debug", "mishkat", "pagemap.json")
OFFSETS = (0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6, -8, 8)


def load_pagemap() -> dict[int, int]:
    if os.path.exists(PAGEMAP):
        try:
            with open(PAGEMAP, encoding="utf-8") as f:
                return {int(k): int(v) for k, v in json.load(f).items()}
        except Exception:                            # noqa: BLE001
            return {}
    return {}


def save_pagemap(pm: dict[int, int]) -> None:
    os.makedirs(os.path.dirname(PAGEMAP), exist_ok=True)
    with open(PAGEMAP, "w", encoding="utf-8") as f:
        json.dump({str(k): pm[k] for k in sorted(pm)}, f, separators=(",", ":"))


def page_facts(html_src: str) -> tuple[list[int], int | None, int | None]:
    """পাতার নিজস্ব হাদিস-নম্বর, পরের ও আগের পাতার ID।"""
    payload = flight_payload(html_src)
    items = find_hadith_items(payload, flight_rows(payload))
    own = [bn2num(i.get("hadith_number")) for i in items] or page_numbers(html_src)
    nxt = prv = None
    for it in items:
        nxt = nxt or it.get("nextHadithId")
        prv = prv or it.get("prevHadithId")
        if nxt and prv:
            break
    for key, val in (("nextHadithId", nxt), ("prevHadithId", prv)):
        if val is None:
            m = re.search(r'"%s"\s*:\s*"?(\d+)' % key, html_src)
            if m:
                if key == "nextHadithId":
                    nxt = int(m.group(1))
                else:
                    prv = int(m.group(1))
    return [x for x in own if x], nxt, prv


def find_page(n: int, sleep: float, pagemap: dict[int, int], harvest=None,
              max_tries: int = 22) -> tuple[str | None, int | None, str]:
    """n-এর পাতা খোঁজে → (html, পাতা-ID, কীভাবে মিলল)।"""
    guess = PAGE0 + n
    queue = ([pagemap[n]] if n in pagemap else []) + [guess + d for d in OFFSETS]
    links: list[int] = []
    tried: set[int] = set()
    while (queue or links) and len(tried) < max_tries:
        pid = queue.pop(0) if queue else links.pop(0)
        if pid in tried or pid <= PAGE0:
            continue
        tried.add(pid)
        try:
            html_src = get(f"{BASE}/hadith/{pid}", sleep=sleep)
        except Exception:                            # noqa: BLE001
            continue
        own, nxt, prv = page_facts(html_src)
        if n in own:
            return html_src, pid, ("ম্যাপ" if pid == pagemap.get(n) else
                                   "সরাসরি" if pid == guess else
                                   f"অফসেট{pid - guess:+d}" if abs(pid - guess) <= 8 else "লিংক-হাঁটা")
        if harvest:
            for other in own:
                if other != n:
                    harvest(other, html_src, pid)
        if nxt:
            links.append(int(nxt))
        if prv:
            links.append(int(prv))
    return None, None, f"ব্যর্থ:পাতা-মেলেনি({len(tried)}টি-দেখা)"


def fill(limit: int = 0, sleep: float = 0.8) -> None:
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)
    gaps = missing_numbers()
    needed: set[int] = set()
    todo: list[tuple[int, int]] = []
    for ch, gl in gaps.items():
        for a, b in gl:
            for n in range(a, b + 1):
                needed.add(n)
                if not os.path.exists(cache_path(n)):
                    todo.append((ch, n))
    if limit:
        todo = todo[:limit]
    pagemap = load_pagemap()
    print(f"নামাতে হবে {len(todo)} হাদিস-পাতা (ক্যাশে আছে {len(os.listdir(CACHE))}"
          f" · পাতা-ম্যাপে {len(pagemap)})", flush=True)
    ok = bad = bonus = 0
    hows: collections.Counter = collections.Counter()
    fails: dict[str, list[int]] = {}

    def store(num: int, v: dict) -> None:
        json.dump(v, open(cache_path(num), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))

    def harvest(other: int, html_src: str, pid: int) -> None:
        """হাঁটার পথে অন্য কোনো ফাঁকা নম্বরের পাতা মিলে গেলে সেটাও তুলে রাখি।"""
        nonlocal bonus
        if other not in needed or os.path.exists(cache_path(other)):
            return
        v, _how = parse_hadith_page_ex(html_src, other)
        if v:
            store(other, v)
            pagemap[other] = pid
            bonus += 1

    for i, (ch, n) in enumerate(todo, 1):
        if os.path.exists(cache_path(n)):          # হাঁটার পথে আগেই জুটে গেছে
            continue
        how, v = "ব্যর্থ:নেটওয়ার্ক", None
        try:
            html_src, pid, fhow = find_page(n, sleep, pagemap, harvest)
            if html_src:
                v, phow = parse_hadith_page_ex(html_src, n)
                how = f"{phow} · পাতা {pid} ({fhow})" if v else f"{phow} · পাতা {pid}"
                if v:
                    pagemap[n] = pid
            else:
                how = fhow
        except Exception as e:                       # noqa: BLE001
            how = f"ব্যর্থ:এক্সেপশন({type(e).__name__})"
            print(f"  ✗ {n} ({ch}) {e}", flush=True)
        hows[how.split(" · ")[0]] += 1
        if not v:
            bad += 1
            fails.setdefault(how, []).append(n)
            if len(os.listdir(FAILED_DIR)) < 2:
                try:
                    open(os.path.join(FAILED_DIR, f"{n}.html"), "w",
                         encoding="utf-8").write(get(f"{BASE}/hadith/{PAGE0 + n}",
                                                     sleep=0.2)[:400_000])
                except Exception:                    # noqa: BLE001
                    pass
            print(f"  ⚠ {n} ({ch}) {how} — বাদ", flush=True)
        else:
            store(n, v)
            ok += 1
        if i % 25 == 0 or i < 4:
            print(f"  ✓ {i}/{len(todo)} · শেষ {n} · সফল {ok} · ব্যর্থ {bad} · বোনাস {bonus}",
                  flush=True)
            _write_stats(len(todo), ok, bad, hows, fails, bonus)
            save_pagemap(pagemap)
    print(f"শেষ: নামানো {ok} · ব্যর্থ {bad} · বোনাস {bonus}", flush=True)
    _write_stats(len(todo), ok, bad, hows, fails, bonus)
    save_pagemap(pagemap)


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
