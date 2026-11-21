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
import html as _html
import json
import subprocess
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
    "policy.html": ("0.6", "yearly"),
}


def pages() -> list[pathlib.Path]:
    return [p for p in sorted(ROOT.glob("*.html")) if not re.fullmatch(r"google[0-9a-f]+\.html", p.name, re.I)] + sorted((ROOT / "grantho").rglob("*.html"))


def url_of(p: pathlib.Path, base: str) -> str:
    rel = p.relative_to(ROOT).as_posix()
    return base if rel == "index.html" else base + rel


def _extract_title_desc(s: str, rel: str) -> tuple[str, str]:
    tm = re.search(r"<title>(.*?)</title>", s, re.S | re.I)
    title = _html.unescape(re.sub(r"<[^>]+>", "", tm.group(1)).strip()) if tm else rel
    dm = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', s, re.I)
    desc = _html.unescape(dm.group(1).strip()) if dm else title
    return title, desc


def _breadcrumbs(rel: str, title: str, base: str) -> list[dict]:
    items = [{"@type": "ListItem", "position": 1, "name": "হোম", "item": base}]
    parts = rel.split("/")
    if rel == "index.html":
        return items
    if parts[0] == "grantho" and len(parts) >= 2:
        items.append({"@type": "ListItem", "position": 2, "name": "ধর্মীয় গ্রন্থ", "item": base + "grantho.html"})
        hub_names = {
            "hindu": ("হিন্দু ধর্মগ্রন্থ", "grantho/hindu.html"),
            "christian": ("খ্রিস্টান ধর্মগ্রন্থ", "grantho/christian.html"),
            "buddhist": ("বৌদ্ধ ধর্মগ্রন্থ", "grantho/buddhist.html"),
            "islam": ("ইসলাম ধর্মগ্রন্থ", "grantho/islam.html"),
        }
        sub = parts[1].replace(".html", "")
        if len(parts) == 3 and sub in hub_names:
            hname, hurl = hub_names[sub]
            items.append({"@type": "ListItem", "position": 3, "name": hname, "item": base + hurl})
            items.append({"@type": "ListItem", "position": 4, "name": title.split("—")[0].strip(), "item": base + rel})
        else:
            items.append({"@type": "ListItem", "position": 3, "name": title.split("—")[0].strip(), "item": base + rel})
        return items
    items.append({"@type": "ListItem", "position": 2, "name": title.split("—")[0].strip(), "item": base + rel})
    return items


def build_jsonld(s: str, base: str, p: pathlib.Path) -> str:
    rel = p.relative_to(ROOT).as_posix()
    title, desc = _extract_title_desc(s, rel)
    url = url_of(p, base)
    og = base + "assets/og-cover.jpg"
    author = {
        "@type": "Person",
        "name": "Ebrahim Ead",
        "url": base,
    }
    graph: list[dict] = []
    if rel == "index.html":
        graph.append({
            "@type": "WebSite",
            "name": "Ebrahim Ead",
            "url": base,
            "inLanguage": "bn",
            "description": desc,
            "potentialAction": {
                "@type": "SearchAction",
                "target": base + "?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        })
        graph.append({
            "@type": "Person",
            "name": "Ebrahim Ead",
            "url": base,
            "image": og,
            "sameAs": [
                "https://www.facebook.com/ebrahim.rahul",
                "https://www.instagram.com/ead2212/",
                "https://www.threads.com/@ead2212",
                "https://www.reddit.com/user/Zealousideal_Dig2819/",
                "https://x.com/ebrahimn23o",
            ],
        })
    else:
        if re.search(r'class="[^"]*\barticle-body\b', s):
            graph.append({
                "@type": "Article",
                "headline": title.split("|")[0].strip(),
                "description": desc,
                "url": url,
                "inLanguage": "bn",
                "image": og,
                "author": author,
                "publisher": author,
            })
        elif rel in ("quran.html", "hadith.html") or rel.startswith("book-") or (
            rel.startswith("grantho/") and rel.count("/") == 2 and rel != "grantho/hindu/veda.html"
        ):
            lang = "en" if rel == "grantho/christian/english-bible.html" else "bn"
            graph.append({
                "@type": "Book",
                "name": title.split("|")[0].strip(),
                "description": desc,
                "url": url,
                "inLanguage": lang,
                "image": og,
            })
        elif rel in ("books.html", "topics.html", "atheism.html", "grantho.html") or rel.startswith("grantho/"):
            graph.append({
                "@type": "CollectionPage",
                "name": title.split("|")[0].strip(),
                "description": desc,
                "url": url,
                "inLanguage": "bn",
            })
        else:
            graph.append({
                "@type": "WebPage",
                "name": title.split("|")[0].strip(),
                "description": desc,
                "url": url,
                "inLanguage": "bn",
            })
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": _breadcrumbs(rel, title, base),
        })

    payload = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json" id="ead-schema">{payload}</script>'


def add_meta(s: str, base: str, p: pathlib.Path) -> tuple[str, list[str]]:
    notes = []
    # 404 আর offline পাতা ইচ্ছে করেই noindex ও canonical-হীন (audit_site.mjs
    # সেটিই আশা করে); আগে seo.py এখানে canonical বসিয়ে দিত, ফলে অডিট ❌ হতো।
    # offline.html সার্ভিস-ওয়ার্কার-নির্দিষ্ট, কোনো URL-এর প্রতিনিধি নয়।
    if p.name in ("404.html", "offline.html") or 'content="noindex' in s[:4000]:
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

    # og:url — শেয়ার-লিংকের প্রামাণিক ঠিকানা (একই কনটেন্ট একাধিক URL-এ নয়)
    if 'property="og:url"' not in s:
        url = url_of(p, base)
        anchor = re.search(r'<meta property="og:title"[^>]*>', s)
        line = f'<meta property="og:url" content="{url}">\n'
        if anchor:
            i = s.find("\n", anchor.end()) + 1
            s = s[:i] + line + s[i:]
        else:
            s = s.replace("</head>", line + "</head>", 1)
        notes.append("og:url")

    # twitter:image — X/Twitter কার্ডে ছবি (og:image X পড়ে না)
    if 'name="twitter:image"' not in s:
        line = f'<meta name="twitter:image" content="{og}">\n'
        anchor = re.search(r'<meta name="twitter:card"[^>]*>', s)
        if anchor:
            i = s.find("\n", anchor.end()) + 1
            s = s[:i] + line + s[i:]
        else:
            s = s.replace("</head>", line + "</head>", 1)
        notes.append("twitter:image")

    if 'rel="canonical"' not in s:
        s = s.replace("</head>", f'<link rel="canonical" href="{url_of(p, base)}">\n</head>', 1)
        notes.append("canonical")

    ld_tag = build_jsonld(s, base, p)
    existing_ld = re.search(r'<script type="application/ld\+json" id="ead-schema">[\s\S]*?</script>', s)
    if existing_ld:
        if existing_ld.group(0) != ld_tag:
            s = s[:existing_ld.start()] + ld_tag + s[existing_ld.end():]
            notes.append("json-ld")
    else:
        s = s.replace("</head>", ld_tag + "\n</head>", 1)
        notes.append("json-ld")
    return s, notes


def _all_same_commit_date() -> bool:
    """shallow clone-এ সব ফাইলের git-তারিখ একই হয় — সনাক্ত করি।

    তখন lastmod লেখা অর্থহীন (Google বানানো lastmod উপেক্ষা করে),
    তাই বাদ দেওয়া হয়।
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        depth = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        return depth.stdout.strip() == "1" and bool(out.stdout.strip())
    except Exception:
        return False


def build_sitemap(base: str) -> str:
    today = date.today().isoformat()
    # shallow clone হলে lastmod বাদ — বানানো তারিখের চেয়ে না-থাকা ভালো
    skip_lastmod = _all_same_commit_date()
    if skip_lastmod:
        print("⚠ shallow clone (১টি কমিট) — sitemap-এ lastmod বাদ দেওয়া হচ্ছে")
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
        stamp = "" if skip_lastmod else f"<lastmod>{today}</lastmod>"
        rows.append(f"  <url><loc>{url_of(p, base)}</loc>{stamp}"
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
        print(f"sitemap.xml: {new.count(chr(60) + 'url' + chr(62))} URLs")
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
