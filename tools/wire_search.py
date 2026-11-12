#!/usr/bin/env python3
"""প্রতিটি HTML পাতায় সাইট-সার্চের বোতাম ও স্ক্রিপ্ট বসায়।

    python3 tools/wire_search.py            # প্রয়োগ
    python3 tools/wire_search.py --check    # শুধু যাচাই

· `header-actions`-এর শুরুতে সার্চ-বোতাম যোগ করে (থিম-টগলের আগে)।
· `</body>`-এর ঠিক আগে search-index.js + site-search.js যোগ করে।
· বারবার চালালেও ডুপ্লিকেট হয় না।
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BUTTON = (
    '<button class="search-btn" type="button" data-search-open '
    'aria-label="সাইটে খুঁজুন (Ctrl+K)" title="সাইটে খুঁজুন — Ctrl+K">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/>'
    '<path d="m20 20-3.6-3.6"/></svg>'
    '<span class="search-label">খুঁজুন</span>'
    '<span class="search-kbd" aria-hidden="true">Ctrl K</span>'
    "</button>"
)

SCRIPTS = (
    '<script src="assets/search-index.js" defer></script>'
    '<script src="assets/site-search.js" defer></script>'
)


def wire(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    before = s

    # পরম পথ ব্যবহারকারী পাতা (404) আলাদা করে সামলাই
    if 'data-search-open' not in s:
        if '<div class="header-actions">' in s:
            s = s.replace(
                '<div class="header-actions">',
                '<div class="header-actions">' + BUTTON,
                1,
            )
        else:
            return "skip (header-actions নেই)"

    if "assets/site-search.js" not in s:
        if "</body>" in s:
            s = s.replace("</body>", SCRIPTS + "</body>", 1)
        else:
            return "skip (</body> নেই)"

    if s == before:
        return "already"
    path.write_text(s, encoding="utf-8")
    return "ok"


def main() -> int:
    check = "--check" in sys.argv
    ok = skipped = already = 0
    for p in sorted(ROOT.glob("*.html")):
        if p.name in {"atheism-2.html"}:  # রিডাইরেক্ট পাতা
            continue
        res = wire(p)
        if check:
            print(f"{p.name:34} {res}")
        if res == "ok":
            ok += 1
        elif res == "already":
            already += 1
        else:
            skipped += 1
            print(f"  ⚠ {p.name}: {res}")
    print(f"\n{'রুটিন চেক' if check else 'সংযুক্ত'}: {ok} · আগেই ছিল {already} · বাদ {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
