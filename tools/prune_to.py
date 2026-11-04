#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""সাইটে কেবল অনুমোদিত গ্রন্থ রাখে — বাকি সব সরায়।

ব্যবহারকারীর সিদ্ধান্ত (২০২৬-১১-০৫): «শুধুমাত্র ভগবত গীতা আর চারটা বেদের
ভিতর শুধুমাত্র ঋগ্বেদ রাখো; বাকি সবগুলো বাদ দাও»।

    python3 tools/prune_to.py            # কী কী যাবে দেখায় (dry-run)
    python3 tools/prune_to.py --apply    # সত্যিই সরায়

কেন স্ক্রিপ্ট: ১২,০০০+ শ্লোক, ১৭টি গ্রন্থ, ১৯টি পাতা — হাতে মুছলে কোনো
লিংক/কার্ড/হাব-সংখ্যা রয়ে যেতে পারে। এটা একই কাজ প্রতিবার একই ভাবে করে।
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data"
OUT = ROOT / "grantho/hindu"

KEEP = ["gita", "rigveda"]                      # ডেটা থাকবে
KEEP_PAGES = ["gita.html", "rigveda.html", "veda.html"]   # পাতা থাকবে


def plan():
    data_dirs = sorted(p.name for p in DATA.iterdir()
                       if p.is_dir() and p.name not in KEEP and p.name != "_debug")
    pages = sorted(p.name for p in OUT.glob("*.html") if p.name not in KEEP_PAGES)
    return data_dirs, pages


def main():
    apply = "--apply" in sys.argv
    data_dirs, pages = plan()

    print("থাকবে:")
    for s in KEEP:
        p = DATA / s / "index.json"
        if p.exists():
            idx = json.loads(p.read_text(encoding="utf-8"))
            print(f"   ✓ {s:10} {idx['bn'][:24]:26} {idx['withBn']}/{idx['total']} · "
                  f"{len(idx['chapters'])} খণ্ড")
    print("\nসরাতে হবে — ডেটা:")
    for d in data_dirs:
        print("   −", d)
    print("\nসরাতে হবে — সাইট-পাতা:")
    for p in pages:
        print("   −", p)

    if not apply:
        print("\n(dry-run — সত্যি সরাতে: --apply)")
        return 0

    for d in data_dirs:
        shutil.rmtree(DATA / d)
        print("   সরানো:", d)
    for p in pages:
        (OUT / p).unlink()
        print("   সরানো:", p)
    print("\nএখন বিল্ড চালাও: python3 tools/build_pages.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
