#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""সাইটের ছোটখাটো বাগ সারানো — বারবার চালানো-নিরাপদ।

`--report` ছাড়া কিছু লেখে না (আগে দেখে নেওয়ার জন্য), `--fix` দিলে সারায়।

যেগুলো সারায়:
  head      hadith.html ও quran.html-এ `<body>` ট্যাগ নেই, `</head>`-এর পরে
            সরাসরি <header> — HTML অসম্পূর্ণ (ডেটা-পাতা বানানোর সময় হারিয়েছে)।
            ব্রাউজার ঠিকই ধরে নেয়, তবু মেরামত করা হয়।
  meta      hadith.html-এ og/twitter-এর শিরোনাম-বর্ণনা কুরআনের পাতা থেকে
            কপি হয়ে আছে (শেয়ারে ভুল তথ্য যায়)।
  theme     যে পাতায় data-theme="dark" হার্ডকোড করা, অথচ Θইম-টগল বোতাম
            আছে — আগের পছন্দ/OS-পছন্দ আর কাজ করে না, পাতা সবসময় গাঢ় থাকে।
  skip      hadith.html-এ কীবোর্ডের «মূল কনটেন্টে যান» লিংক নেই।
  type      <button> ছাড়া type — form-এর ভেতরে থাকলে অতি-জটিল সাবমিট বাগ।
  aria      অচল (is-soon) কার্ডে href="#" রাখা হয় — এতে ক্লিকে পাতা উপরে লাফায়।
  dead      ফুটারের মতো জায়গায় মৃত লিংক।
  font      ভাঙা Google Fonts URL (display=swap জোড়া লেগে `70&display=swap0&display=swap`)।
  space     দৃশ্যমান লেখায় ডাবল স্পেস।
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def pages() -> list[pathlib.Path]:
    return sorted(ROOT.glob("*.html")) + sorted((ROOT / "grantho").rglob("*.html"))


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: pathlib.Path, s: str, fix: bool) -> None:
    if fix:
        p.write_text(s, encoding="utf-8")


# --------------------------------------------------------------------------- #
def fix_body(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    if "<body" in s:
        return s, None
    i = s.find("</head>")
    if i == -1:
        return s, None
    s = s[: i + len("</head>")] + "\n<body>" + s[i + len("</head>"):]
    return s, "`<body>` ট্যাগ যোগ"


def fix_meta(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    title = re.search(r"<title>([^<]*)</title>", s)
    desc = re.search(r'<meta name="description" content="([^"]*)"', s)
    if p.name != "hadith.html":
        return s, None
    if not title:
        return s, None
    t = title.group(1)
    d = desc.group(1) if desc else ""
    def put(text: str, value: str, attr: str) -> str:
        pat = re.compile(rf'(<meta {attr}="{text}" content=")[^"]*(">)')
        if not pat.search(s):
            return s
        return pat.sub(lambda m: m.group(1) + value + m.group(2), s)

    before = s
    for attr in ("property", "name"):
        s = put("og:title", t, attr)
        s = put("twitter:title", t, attr)
        s = put("og:description", d, attr)
        s = put("twitter:description", d, attr)
    changed = s != before
    if 'name="twitter:title"' not in s:
        s = s.replace(
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="twitter:card" content="summary_large_image">\n'
            f'<meta name="twitter:title" content="{t}">\n'
            f'<meta name="twitter:description" content="{d}">',
        )
        changed = True
    return (s, "og/twitter mata ঠিক করা") if changed else (s, None)


def fix_theme(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    if 'data-theme="dark"' not in s:
        return s, None
    if "data-theme-toggle" not in s:
        return s, None
    s = s.replace('data-theme="dark"', "", 1)
    s = re.sub(r'<html lang="bn" >', '<html lang="bn">', s)
    return s, "হার্ডকোড dark সরানো (টগল/OS পছন্দ কাজ করবে)"


def fix_skip(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    if "skip-link" in s or 'id="main-content"' not in s:
        return s, None
    m = re.search(r"<main[^>]*id=\"main-content\"", s)
    if not m:
        return s, None
    link = '<a class="skip-link" href="#main-content">মূল কনটেন্টে যান</a>\n'
    # just before <main> (fallback: right after </header>)
    s = s[: m.start()] + link + s[m.start():]
    return s, "কীবোর্ড skip-link যোগ"


def fix_button_type(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    if "<form" not in s:
        return s, None
    head, sep, rest = s.partition("<form")
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return '<button type="button"' if "type=" not in m.group(0) else m.group(0)

    rest = re.sub(r"<button\b[^>]*>", sub, rest)
    return (head + sep + rest, f"{n}টি <button> এ type যোগ") if n else (s, None)


def fix_nodead(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    """`is-soon` কার্ডের `href="#"` → ক্লিক-নিষ্ক্রিয় <span> (পাতা লাফায় না)।"""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        block = m.group(0)
        if 'href="#"' not in block:
            return block
        n += 1
        return re.sub(r'<a\b([^>]*?)href="#"([^>]*?)>([\s\S]*?)</a>',
                      r'<span class="is-soon-static"\1\2>\3</span>', block, count=1)

    s2 = re.sub(r'<article[^>]*is-soon[\s\S]{0,600}?</article>', sub, s)
    s2 = re.sub(r'<a class="article-card-link" href="#" aria-disabled="true" tabindex="-1">',
                '<span class="article-card-link" aria-disabled="true">', s2)
    s2 = s2.replace("</a></article>", "</span></article>") if s2 != s else s2
    return (s2, f"{n}টি অচল কার্ডের মৃত লিংক সরানো") if s2 != s else (s, None)


FONT_OK = 'family=Hind+Siliguri:wght@400;500;600;700&display=swap'


def fix_font(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    s2 = re.sub(r"family=Hind\+Siliguri:wght@[0-9;]+[^\"']*", FONT_OK, s)
    return (s2, "ভাঙা Google Fonts URL ঠিক") if s2 != s else (s, None)


def fix_space(p: pathlib.Path, s: str) -> tuple[str, str | None]:
    """<body>-এর ভেতরে, <script>/<style> বাদ দিয়ে, দৃশ্যমান লেখায় ডাবল স্পেস।"""
    head, sep, body = s.partition("</head>")
    if not sep:
        return s, None
    keep = []

    def stash(m: re.Match) -> str:
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    body = re.sub(r"<(script|style)\b[\s\S]*?</\1>", stash, body)
    parts = re.split(r"(<[^>]*>)", body)
    changed = False
    for i, part in enumerate(parts):
        if part.startswith("<") or "\x00" in part:
            continue
        new = re.sub(r"(?<=\S)  +(?=\S)", " ", part)
        if new != part:
            parts[i] = new
            changed = True
    body = "".join(parts)
    body = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], body)
    return (head + sep + body, "দৃশ্যমান লেখায় ডাবল স্পেস সরানো") if changed else (s, None)


CHECKS = [fix_body, fix_meta, fix_theme, fix_skip, fix_button_type,
          fix_nodead, fix_font, fix_space]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="সারিয়ে ফেলো (নাহলে শুধু রিপোর্ট)")
    a = ap.parse_args()
    total = 0
    for p in pages():
        s = read(p)
        notes = []
        for fn in CHECKS:
            s2, note = fn(p, s)
            if note:
                notes.append(note)
                s = s2
        if notes:
            total += len(notes)
            print(f"{p.relative_to(ROOT)}")
            for n in notes:
                print(f"   • {n}")
            write(p, s, a.fix)
    print(f"\n{total}টি সমস্যা" + (" সারানো হয়েছে" if a.fix else " (শুধু রিপোর্ট; --fix দিলে সারবে)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
