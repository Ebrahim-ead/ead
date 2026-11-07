#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO ধাপ: og:image, canonical, sitemap.xml, robots.txt — বারবার চালানো নিরাপদ।

কেন:
  * কোনো পাতায় `og:image` ছিল না — Facebook/X/WhatsApp-এ লিংক শেয়ার করলে ছবি আসত না,
    যদিও `assets/og-cover.jpg` (১২০০×৬৩০) আগে থেকেই ছিল।
  * `rel="canonical"` একটিতেও ছিল না — একই কনটেন্ট একাধিক URL-এ (index.html ও /,
    grantho/… vs …) ধরা পড়ার ঝুঁকি।
  * sitemap.xml ছিল না, robots.txt-এ sitemap-এর ঠিকানা ছিল না।

চালানো: python3 tools/seo.py [--base URL] [--dry-run]
"""
from __future__ import annotations

import argparse
import glob
import pathlib
import re
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://ebrahim-ead.github.io/ead/"

# গভীরতা বুঝে আপেক্ষিক পথ
PRIORITY = {
    "index.html": ("1.0", "weekly"),
    "hadith.html": ("0.9", "weekly"),
    "quran.html": ("0.9", "weekly"),
    "atheism.html": ("0.8", "monthly"),
    "books.html": ("0.8", "monthly"),
    "grantho.html": ("0.8", "monthly"),
    "topics.html": ("0.7", "monthly"),
    "ask.html": ("0.6", "monthly"),
    "about.html": ("0.6", "yearly"),
    "contact.html": ("0.5", "yearly"),
}


def pages() -> list[pathlib.Path]:
    return sorted(ROOT.glob("*.html")) + sorted((ROOT / "grantho").rglob("*.html"))


def url_of(p: pathlib.Path, base: str) -> str:
    rel = p.relative_to(ROOT).as_posix()
    return base if rel == "index.html" else base + rel


def add_meta(s: str, base: str, p: pathlib.Path) -> tuple[str, list[str]]:
    notes = []
    # 404 পাতা ইচ্ছে করেই noindex ও canonical-হীন (audit_site.mjs সেটিই আশা করে);
    # আগে seo.py এখানে canonical বসিয়ে দিত, ফলে অডিট ❌ হতো।
    if p.name == "404.html":
        return s, notes
    og = base + "assets/og-cover.jpg"
    if 'property="og:image"' not in s:
        anchor = re.search(r'<meta property="og:title"[^>]*>', s)
        block = (f'<meta property="og:image" content="{og}">\n'
                 f'<meta property="og:image:width" content="1200">\n'
                 f'<meta property="og:image:height" content="630">\n')
        if anchor:
            i = s.find("\n", anchor.end()) + 1
            s = s[:i] + block + s[i:]
        else:
            s = s.replace("</head>", block + "</head>", 1)
        notes.append("og:image")

    if 'rel="canonical"' not in s:
        s = s.replace("</head>", f'<link rel="canonical" href="{url_of(p, base)}">\n</head>', 1)
        notes.append("canonical")
    return s, notes


def build_sitemap(base: str) -> str:
    today = date.today().isoformat()
    rows = []
    for p in pages():
        rel = p.relative_to(ROOT).as_posix()
        # noindex পাতা (রিডাইরেক্ট/অস্থায়ী) sitemap-এ রাখা উচিত নয় —
        # সার্চ-ইঞ্জিন সেগুলো ক্রল করে অকারণে।
        try:
            head = p.read_text(encoding="utf-8")[:4000]
        except OSError:
            head = ""
        if 'content="noindex' in head or "content='noindex" in head:
            continue
        pr, ch = PRIORITY.get(rel, ("0.7" if "/" not in rel else "0.6", "monthly"))
        rows.append(f"  <url><loc>{url_of(p, base)}</loc><lastmod>{today}</lastmod>"
                    f"<changefreq>{ch}</changefreq><priority>{pr}</priority></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    base = a.base if a.base.endswith("/") else a.base + "/"

    changed = 0
    for p in pages():
        s = p.read_text(encoding="utf-8")
        s2, notes = add_meta(s, base, p)
        if notes:
            changed += 1
            print(f"{p.relative_to(ROOT)}: {', '.join(notes)}")
            if not a.dry_run:
                p.write_text(s2, encoding="utf-8")
    print(f"meta: {changed} pages updated")

    sm = ROOT / "sitemap.xml"
    new = build_sitemap(base)
    if not sm.exists() or sm.read_text(encoding="utf-8") != new:
        print(f"sitemap.xml: {len(pages())} URLs")
        if not a.dry_run:
            sm.write_text(new, encoding="utf-8")

    robots = ROOT / "robots.txt"
    r = robots.read_text(encoding="utf-8") if robots.exists() else "User-agent: *\nAllow: /\n"
    line = f"Sitemap: {base}sitemap.xml"
    if line not in r:
        print("robots.txt: Sitemap নির্দেশ যোগ")
        if not a.dry_run:
            robots.write_text(r.rstrip() + "\n" + line + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
