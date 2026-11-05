#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""মেনুর আইকন একবার — `assets/icons.svg` স্প্রাইট থেকে।

আগে প্রতিটি পাতায় মেনুর ৭টি লিংকের জন্য ৭টি করে inline SVG বসানো ছিল
(প্রায় ২.৩ KB × ৩১ পাতা)। এখন আইকনগুলো এক ফাইলে, পাতায় শুধু
`<svg class="ic"><use href="...#home"/></svg>`।

* `--write-sprite` : index.html-এর লুকানো স্প্রাইট থেকে assets/icons.svg বানায়
* `--apply`        : প্রতিটি পাতার মেনু-আইকন sprite-এ বদলায় (বারবার নিরাপদ)
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPRITE = ROOT / "assets" / "icons.svg"

NAV_ICONS = {
    "index.html": "home",
    "topics.html": "topic",
    "atheism.html": "article",
    "books.html": "books",
    "grantho.html": "grantho",
    "ask.html": "ask",
    "about.html": "about",
    "contact.html": "contact",
}


def pages() -> list[pathlib.Path]:
    return sorted(ROOT.glob("*.html")) + sorted((ROOT / "grantho").rglob("*.html"))


def rel(p: pathlib.Path) -> str:
    return "../" * (len(p.relative_to(ROOT).parts) - 1)


def write_sprite() -> None:
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<svg[^>]*style="display:none"[\s\S]*?</svg>', src)
    if not m:
        m = re.search(r"<svg[^>]*hidden[\s\S]*?</svg>", src)
    if not m:
        sys.exit("index.html-এ লুকানো SVG স্প্রাইট পাওয়া গেল না")
    body = m.group(0)
    # symbol গুলোর ভেতরের আঁকাগুলোই দরকার
    symbols = {
        sid: inner
        for sid, inner in re.findall(r'<symbol[^>]*id="([^"]+)"[^>]*>([\s\S]*?)</symbol>', body)
    }
    # মেনুর ৭টি আইকন: উপরের symbol-এ নেই, inline <path> আকারে আছে
    nav = re.search(r'<nav class="nav" id="site-nav"[\s\S]*?</nav>', src)
    extra = {}
    if nav:
        for href, inner in re.findall(
            r'<a href="([^"]+)"[^>]*><span class="nav-symbol"[^>]*><svg[^>]*>([\s\S]*?)</svg>',
            nav.group(0),
        ):
            sid = NAV_ICONS.get(href.split("#")[0])
            if sid and sid not in symbols:
                extra[sid] = inner
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">']
    for sid, inner in {**symbols, **extra}.items():
        parts.append(f'<symbol id="{sid}" viewBox="0 0 24 24">{inner.strip()}</symbol>')
    parts.append("</svg>\n")
    SPRITE.write_text("\n".join(parts), encoding="utf-8")
    print(f"  assets/icons.svg — {len(symbols) + len(extra)} symbol")


def apply_nav() -> None:
    sprite_ids = set(re.findall(r'<symbol id="([^"]+)"', SPRITE.read_text(encoding="utf-8")))
    changed = 0
    for p in pages():
        s = p.read_text(encoding="utf-8")
        pre = rel(p)
        nav = re.search(r'<nav class="nav" id="site-nav"[\s\S]*?</nav>', s)
        if not nav:
            continue
        block = nav.group(0)
        new = block
        for href, icon in NAV_ICONS.items():
            if icon not in sprite_ids:
                continue
            pat = re.compile(
                r'(<a href="' + re.escape(href) + r'"[^>]*><span class="nav-symbol"[^>]*>)'
                r"<svg[^>]*>[\s\S]*?</svg>"
            )
            new = pat.sub(lambda m: f'{m.group(1)}<svg class="ic" aria-hidden="true"><use href="{pre}assets/icons.svg#{icon}"/></svg>', new)
        if new != block:
            s = s.replace(block, new, 1)
            p.write_text(s, encoding="utf-8")
            changed += 1
    print(f"  {changed}টি পাতায় মেনু-আইকন sprite-এ বদলানো হলো")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-sprite", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.write_sprite:
        write_sprite()
    if a.apply:
        apply_nav()
    if not (a.write_sprite or a.apply):
        write_sprite()
        apply_nav()
    return 0


if __name__ == "__main__":
    sys.exit(main())
