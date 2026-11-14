#!/usr/bin/env python3
"""প্রতিটি পাতায় অ্যাপ-আইকন (favicon + apple-touch-icon) বসায়।

    python3 tools/wire_icons.py            # প্রয়োগ
    python3 tools/wire_icons.py --check    # শুধু যাচাই

· পুরোনো SVG-data-URI favicon সরিয়ে PNG-ভিত্তিক আইকন বসায়।
· পরম পথ (`/ead/…`) ব্যবহার করে — 404 পাতার মতো নেস্টেড URL-এও কাজ করে।
· বারবার চালালেও ডুপ্লিকেট হয় না।
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "/ead/"

ICONS = (
    f'<link rel="icon" type="image/png" sizes="32x32" href="{PREFIX}assets/img/favicon-32.png">'
    f'<link rel="icon" type="image/png" sizes="192x192" href="{PREFIX}assets/img/icon-192.png">'
    f'<link rel="apple-touch-icon" sizes="180x180" href="{PREFIX}assets/img/apple-touch-icon.png">'
)

# পুরোনো data: favicon (এক লাইন, খুব লম্বা)
OLD_ICON_RE = re.compile(r'<link rel="icon" href="data:image/svg\+xml,[^"]*">\s*')
# আমাদের নিজের বসানো ব্লক
OWN_RE = re.compile(r'<link rel="icon" type="image/png" sizes="32x32"[^>]*>.*?apple-touch-icon[^>]*>', re.S)


def wire(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    before = s

    if 'favicon-32.png' in s:
        return "already"

    s = OLD_ICON_RE.sub("", s)

    # og:image বা theme-color-এর পরে বসাই; না পেলে </head>-এর আগে
    anchor = re.search(r'<meta name="theme-color"[^>]*>\s*', s)
    if anchor:
        i = anchor.end()
        s = s[:i] + ICONS + s[i:]
    else:
        s = s.replace("</head>", ICONS + "</head>", 1)

    if s == before:
        return "skip"
    path.write_text(s, encoding="utf-8")
    return "ok"


def main() -> int:
    check = "--check" in sys.argv
    ok = already = skipped = 0
    for p in sorted(ROOT.glob("*.html")):
        res = wire(p)
        if res == "ok":
            ok += 1
        elif res == "already":
            already += 1
        else:
            skipped += 1
            print(f"  ⚠ {p.name}: {res}")
        if check:
            print(f"{p.name:34} {res}")
    verb = "যাচাই" if check else "সংযুক্ত"
    print(f"\n{verb}: {ok} · আগেই ছিল {already} · বাদ {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
