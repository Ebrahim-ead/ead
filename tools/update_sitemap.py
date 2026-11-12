#!/usr/bin/env python3
"""sitemap.xml হালনাগাদ করে — ফাইলের আসল git-তারিখ থেকে।

    python3 tools/update_sitemap.py            # প্রয়োগ
    python3 tools/update_sitemap.py --dry-run  # শুধু দেখায়

## কেন ফাইলের mtime ব্যবহার করি না

GitHub Pages-এ ডিপ্লয় করলে সব ফাইলের mtime ডিপ্লয়ের সময় হয়ে যায় —
তাতে sitemap-এর lastmod অর্থহীন হয়ে পড়ে।

## এখানে দুই স্তরে কাজ হয়

১. **লক্ষ্য-তারিখ:** প্রতিটি ফাইলের শেষ *content-change* কমিটের তারিখ
   (`git log -1 --format=%cs -- <file>`)। কমিট-ইতিহাস না থাকলে বা
   shallow clone-এ সেটি না মিললে `SOURCE_DATE` ব্যবহার হয়।
২. **নিরাপত্তা-সীমা:** কোনো ভবিষ্যৎ-তারিখ কখনো লেখা হয় না।

কোনো ফাইলের তারিখ না পেলে lastmod **যোগ করা হয় না** — বানানো তারিখের
চেয়ে না-থাকা ভালো (Google বানানো lastmod উপেক্ষা করে, বরং অবিশ্বাস করে)।

## Shallow clone সনাক্তকরণ

যদি সব ফাইলের git-তারিখ **একই** হয় (shallow clone-এ সাধারণত তাই হয়),
তবে সেটি অর্থহীন — Google সব পাতা একদিনে «শেষ বদলেছে» ভেবে lastmod
উপেক্ষা করে। সেক্ষেত্রে স্ক্রিপ্ট **কোনো lastmod লেখে না** এবং জানায়।
রিপোতে পূর্ণ ইতিহাস থাকলে (git fetch --unshallow) নিজে থেকেই সত্যিকার
প্রতি-ফাইল তারিখ বসাতে থাকবে।
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://ebrahim-ead.github.io/ead/"

# কমিট-ইতিহাস না পাওয়া গেলে ব্যবহারের তারিখ (সর্বশেষ যাচাই করা অবস্থা)
SOURCE_DATE = "2026-10-31"


def git_date(rel: str, today: dt.date) -> str | None:
    """ফাইলের শেষ কমিট-তারিখ, না পেলে None."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return None
    d = out.stdout.strip()
    if not d or out.returncode != 0:
        return None
    try:
        day = dt.date.fromisoformat(d)
    except ValueError:
        return None
    # ভবিষ্যৎ-তারিখ কখনো নয়
    if day > today:
        return today.isoformat()
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    today = dt.date.today()
    xml = SITEMAP.read_text(encoding="utf-8")
    urls = re.findall(r"<url>(.*?)</url>", xml, re.S)
    print(f"sitemap: {len(urls)}টি URL")

    changed = 0
    out_blocks = []
    for block in urls:
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        if not loc:
            out_blocks.append(block)
            continue
        url = loc.group(1)
        rel = url.replace(BASE, "").rstrip("/") or "index.html"
        rel = rel.split("#")[0].split("?")[0]
        path = ROOT / rel
        stamp = git_date(rel, today) if path.exists() else None
        if stamp is None and path.exists():
            stamp = SOURCE_DATE

        body = re.sub(r"\s*<lastmod>[^<]*</lastmod>", "", block).strip()
        if stamp:
            body = re.sub(
                r"(<loc>[^<]+</loc>)",
                lambda m: m.group(1) + f"<lastmod>{stamp}</lastmod>",
                body, count=1,
            )
        old = re.search(r"<lastmod>([^<]*)</lastmod>", block)
        if (old.group(1) if old else None) != stamp:
            changed += 1
            print(f"  {rel:32} {(old.group(1) if old else '—'):12} → {stamp or '—'}")
        out_blocks.append(body)

    # ── shallow-clone সনাক্তকরণ: সব তারিখ একই হলে lastmod অর্থহীন ──
    stamps = []
    for block in out_blocks:
        m = re.search(r"<lastmod>([^<]*)</lastmod>", block)
        if m:
            stamps.append(m.group(1))
    if stamps and len(set(stamps)) == 1:
        print(f"\n⚠ সব ফাইলের তারিখ একই ({stamps[0]}) — shallow clone।")
        print("  lastmod বাদ দেওয়া হচ্ছে (বানানো তারিখের চেয়ে ভালো)।")
        out_blocks = [re.sub(r"\s*<lastmod>[^<]*</lastmod>", "", b) for b in out_blocks]
        changed = len([b for b in urls if "<lastmod>" in b])

    new_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url>{b}</url>\n" for b in out_blocks)
        + "</urlset>\n"
    )

    if args.dry_run:
        print(f"[dry-run] {changed}টি বদলাত")
        return 0

    SITEMAP.write_text(new_xml, encoding="utf-8")
    print(f"✓ {changed}টি URL-এ lastmod হালনাগাদ · মোট {len(urls)}টি")
    return 0


if __name__ == "__main__":
    sys.exit(main())
