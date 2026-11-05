#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""মিশকাতুল মাসাবিহ — muslimbangla.com থেকে বাংলা+আরবি হাদিস নামানোর যন্ত্র।

কেন আলাদা স্ক্রিপ্ট: সাইটটি Next.js; অধ্যায় → পরিচ্ছেদ (title) → হাদিস — এই
তিন ধাপে হাদিসগুলো ছড়ানো, আর এক পাতায় একাধিক হাদিস থাকে। তাই আগে কাঠামো
জেনে (--probe), তারপর অধ্যায় ধরে ধরে নামিয়ে (--fetch), শেষে সাইটের নিজের
ফরম্যাটে ঢেলে (--build) রিডারে বসানো হয়।

ধাপ:
    --probe                 → একটি অধ্যায় + একটি পরিচ্ছেদের কাঁচা HTML _debug/ তে
    --discover              → ৩১ অধ্যায় ও তাদের পরিচ্ছেদের তালিকা (chapters.json)
    --fetch --chapters 498  → ওই অধ্যায়গুলোর সব পরিচ্ছেদের হাদিস নামাও
    --build                 → assets/hadith/data/mishkat/*.json + index হালনাগাদ

নিয়ম: শুধু muslimbangla.com, পুনরাবৃত্তি নয় (ডিস্ক-ক্যাশ), ধীরে (বিরতি),
robots.txt মানা (সাইটে /api/ বন্ধ — তাই শুধু পাবলিক পাতা পড়া হয়)।
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://muslimbangla.com"
BOOK = 13                     # সাইটে ১৩ = মিশকাতুল মাসাবিহ
UA = "Mozilla/5.0 (compatible; ead-hadith/1.0; +https://github.com/Ebrahim-ead/ead)"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "hadith", "data", "_debug", "mishkat")
DATA = os.path.join(ROOT, "assets", "hadith", "data")
RAW = os.path.join(OUT, "raw")
SRC_URL = f"{BASE}/hadith-book/{BOOK}/chapters"

BN_DIGITS = "০১২৩৪৫৬৭৮৯"


# ---------------------------------------------------------------- utils
def bn2num(s):
    """'১,২৩৪' → 1234"""
    s = "".join(BN_DIGITS.index(ch) and str(BN_DIGITS.index(ch)) if ch in BN_DIGITS else ch
                for ch in s)
    s = re.sub(r"[^\d]", "", s)
    return int(s) if s else 0


def num2bn(n):
    return "".join(BN_DIGITS[int(d)] if d.isdigit() else d for d in str(n))


def cache_path(*parts):
    p = os.path.join(RAW, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def get(url, tries=4, timeout=60, sleep=1.2):
    """একই URL দুবার নামায় না — ডিস্ক-ক্যাশ।"""
    key = re.sub(r"[^A-Za-z0-9]+", "_", url.replace(BASE, ""))[:120] + ".html"
    p = cache_path(key)
    if os.path.exists(p) and os.path.getsize(p) > 2000:
        with open(p, encoding="utf-8") as f:
            return f.read(), "cache"
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
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
            time.sleep(sleep)
            return body, "net"
        except Exception as e:                       # noqa: BLE001
            last = e
            time.sleep(min(30, 3 * (i + 1)))
    raise RuntimeError(f"{url} — {tries} বারে ব্যর্থ: {last}")


# ---------------------------------------------------------------- mini-dom
class Node:
    __slots__ = ("tag", "attrs", "kids", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids = []
        self.parent = parent

    def cls(self):
        return (self.attrs.get("class") or "").split()

    def text(self):
        out = []
        stack = [self]
        while stack:
            n = stack.pop()
            if isinstance(n, str):
                out.append(n)
                continue
            if n.tag in ("script", "style"):
                continue
            stack.extend(reversed(n.kids))
        return "".join(out)

    def walk(self):
        stack = [self]
        while stack:
            n = stack.pop()
            if isinstance(n, str):
                continue
            yield n
            stack.extend(reversed(n.kids))


from html.parser import HTMLParser  # noqa: E402  (উপরে রাখলে পড়তে অসুবিধা)


class Tree(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict(attrs), self.cur)
        self.cur.kids.append(n)
        if tag not in self.VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def parse_html(html):
    t = Tree()
    t.feed(html)
    return t.root


def qa(root, tag=None, cls=None):
    out = []
    for n in root.walk():
        if tag and n.tag != tag:
            continue
        if cls and cls not in n.cls():
            continue
        out.append(n)
    return out


def dedup(seq):
    seen, out = set(), []
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


# ---------------------------------------------------------------- probe
def probe():
    os.makedirs(OUT, exist_ok=True)
    log = []
    pages = {
        "chapters": f"{BASE}/hadith-book/{BOOK}/chapters",
        "sections_498": f"{BASE}/hadith-book/{BOOK}/chapter/498/titles",
        "title_12308": f"{BASE}/hadith-book/{BOOK}/chapter/498/title/12308",
        "title_12306": f"{BASE}/hadith-book/{BOOK}/chapter/499/title/12306",
    }
    for name, url in pages.items():
        try:
            body, how = get(url)
        except Exception as e:                        # noqa: BLE001
            log.append(f"### {name} — ব্যর্থ: {e}")
            continue
        with open(os.path.join(OUT, f"probe_{name}.html"), "w", encoding="utf-8") as f:
            f.write(body)
        root = parse_html(body)
        log.append(f"### {name} ({how}) — {len(body):,} বাইট")
        log.append(f"  কাঁচা 'হাদীস নং' = {body.count('হাদীস নং')}, "
                   f"স্ক্রিপ্ট-বাদ টেক্সটে = {root.text().count('হাদীস নং')}")
        # ক্লাস-ঘনত্ব
        freq = {}
        for n in root.walk():
            for c in n.cls():
                freq[c] = freq.get(c, 0) + 1
        top = sorted(freq.items(), key=lambda kv: -kv[1])[:25]
        log.append("  ক্লাস: " + ", ".join(f"{c}×{k}" for c, k in top))
        # 'হাদীস নং' যেসব নোডে
        holders = [n for n in root.walk() if "হাদীস নং" in n.text() and
                   not any("হাদীস নং" in ch.text() for ch in n.kids if isinstance(ch, Node))]
        for h in holders[:3]:
            chain = []
            p = h
            while p is not None and p.tag != "root":
                chain.append(p.tag + ("." + ".".join(p.cls()) if p.cls() else ""))
                p = p.parent
            log.append("  ধারক: " + h.text().strip()[:60].replace("\n", " ") +
                       "  ← " + " < ".join(reversed(chain[-6:])))
        if name.startswith("title_"):
            log.append("  লিংক নমুনা: " + ", ".join(
                dedup([a.attrs.get("href", "") for a in qa(root, "a")
                       if "/hadith-book/" in (a.attrs.get("href") or "")])[:8]))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "probe.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))


# ---------------------------------------------------------------- discover
def discover():
    body, _ = get(SRC_URL)
    root = parse_html(body)
    text = root.text()
    chapters = []
    for a in qa(root, "a"):
        href = a.attrs.get("href") or ""
        m = re.search(rf"/hadith-book/{BOOK}/chapter/(\d+)/titles", href)
        if not m:
            continue
        cid = int(m.group(1))
        # কার্ডের ভেতরের লেখা: নাম + «মোট হাদীস -N টি•হাদীসের ব্যাপ্তি:a -b»
        inner = a.text()
        bn = inner.split("মোট হাদীস")[0].strip()
        bn = re.sub(r"[•·]\s*$", "", bn).strip()
        nums = re.search(r"(\d+)\s*-\s*(\d+)\s*$", inner.strip())
        cnt = re.search(r"(\d+)\s*টি", inner)
        chapters.append({
            "site_chapter": cid,
            "bn": re.sub(r"\s+", " ", bn),
            "ar": "",
            "count_claimed": int(cnt.group(1)) if cnt else 0,
            "from": int(nums.group(1)) if nums else 0,
            "to": int(nums.group(2)) if nums else 0,
        })
    chapters = dedup([c["site_chapter"] for c in chapters]) and chapters
    seen, uniq = set(), []
    for c in chapters:
        if c["site_chapter"] in seen:
            continue
        seen.add(c["site_chapter"])
        uniq.append(c)
    info = {"book": BOOK, "source": SRC_URL, "chapters": uniq,
            "total_claimed": 6295, "pages_text_head": text[:200]}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "chapters.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(f"অধ্যায়: {len(uniq)} · দাবিকৃত যোগফল: {sum(c['count_claimed'] for c in uniq)}")
    for c in uniq:
        print(f"  {c['site_chapter']}  {c['count_claimed']:>4}  {c['from']}-{c['to']}  {c['bn'][:52]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--discover", action="store_true")
    a = ap.parse_args()
    if a.probe:
        probe()
    elif a.discover:
        discover()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
