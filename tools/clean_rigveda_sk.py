#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ঋগ্বেদ-ডেটার `sk` ফিল্ড পরিষ্কার করে।

কেন: উৎস (ebanglalibrary.com) থেকে নামানো পাঠে ২৩টি মন্ত্রের `sk`-ঘরে আসল
সংস্কৃত নয়, বরং উৎসের ভাসা আর্টিফ্যাক্ট ঢুকে গিয়েছিল —
  • ১১টিতে শুধু '?' (খালি ঘরের চিহ্ন)
  • ১২টিতে বাংলা টীকা/ক্রস-রেফারেন্সের বিচ্ছিন্ন টুকরো («সুক্ত ।। অনুবাদঃ»,
    «১১৬ সুক্তের ৭ ঋক দেখুন।», «তোমার জিহ্বা যে কাষ্ঠ সকল» …)
গ্রন্থ-পাতা `sk` থাকলে সেটাকে সংস্কৃত মূল পাঠ ধরে ছাপে (grantho.js:
`if (state.sk && sk)`), ফলে পাঠকের সামনে '?' বা বাংলা টুকরো «সংস্কৃত» হয়ে যেত।

নীতি: কোনো পাঠ মুছে ফেলা হয় না — যে ঘরে আসল দেবনাগরী নেই সে ঘর খালি করা হয়
এবং সরানো টুকরো `_sk_artifacts.json`-এ মণ্ডল/মন্ত্র নম্বর ও কারণসহ জমা থাকে
(`_dropped.json`-এর একই রীতি)। আসল দেবনাগরী পাঠ থাকলে তা অক্ষুণ্ণ থাকে।

ব্যবহার:  python3 tools/clean_rigveda_sk.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "grantho" / "data" / "rigveda"
ART = DATA / "_sk_artifacts.json"

# দেবনাগরী *অক্ষর* — দাঁড়ি (U+0964) ও দেবনাগরী অঙ্ক বাদ, কারণ সেগুলো বাংলা
# লেখাতেও বসে; শুধু তাদের উপস্থিতিতে পাঠকে সংস্কৃত ধরা ভুল।
DEVANAGARI_LETTERS = re.compile(r"[\u0904-\u0939\u093D\u0950\u0958-\u0961\u0972-\u097F]")


def has_sanskrit(text: str) -> bool:
    return bool(DEVANAGARI_LETTERS.search(text or ""))


def reason_for(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "খালি"
    if t in ("?", "।", "-", "--"):
        return "উৎসের ফাঁকা-ঘরের চিহ্ন ('?') — সংস্কৃত পাঠ নয়"
    if re.fullmatch(r"[\u09E6-\u09FF\s।,]+", t):
        return "বাংলা অঙ্ক/দাঁড়ি মাত্র — সংস্কৃত পাঠ নয়"
    return "বাংলা টীকা/ক্রস-রেফারেন্সের বিচ্ছিন্ন টুকরো — দেবনাগরী সংস্কৃত নয়"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="শুধু রিপোর্ট, ফাইল বদলাবে না")
    args = ap.parse_args()

    files = sorted(DATA.glob("ch*.json"), key=lambda p: int(re.findall(r"\d+", p.name)[0]))
    if not files:
        print("⛔ ঋগ্বেদ-ডেটা পাওয়া যায়নি:", DATA)
        return 1

    art = {}
    if ART.exists():
        try:
            art = json.loads(ART.read_text(encoding="utf-8"))
        except Exception:
            art = {}
    store = art.get("verses") if isinstance(art, dict) else None
    if not isinstance(store, list):
        store = []
        art = {
            "_note": ("sk-ঘর থেকে সরানো আর্টিফ্যাক্ট — আসল দেবনাগরী সংস্কৃত নয় "
                      "(উৎসের '?' চিহ্ন ও বাংলা টীকা-টুকরো)। পাঠ হারায়নি, এখানে জমা আছে; "
                      "tools/clean_rigveda_sk.py চালালে তৈরি/হালনাগাদ হয়।"),
            "verses": store,
        }
    known = {(x.get("ch"), x.get("n")) for x in store}

    cleared = kept = verses = 0
    per_ch = []
    for fp in files:
        d = json.loads(fp.read_text(encoding="utf-8"))
        vs = d.get("verses", [])
        ch = int(re.findall(r"\d+", fp.name)[0])
        n_clear = 0
        for v in vs:
            verses += 1
            sk = str(v.get("sk") or "").strip()
            if not sk:
                continue
            if has_sanskrit(sk):
                kept += 1
                continue
            n_clear += 1
            cleared += 1
            key = (ch, v.get("n"))
            if key not in known:
                store.append({"ch": ch, "n": v.get("n"), "sk": sk,
                              "why": reason_for(sk),
                              "bnHasText": bool(str(v.get("bn") or "").strip())})
                known.add(key)
            if not args.dry:
                v["sk"] = ""
        if n_clear:
            per_ch.append((ch, n_clear))
        if not args.dry and n_clear:
            fp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n",
                          encoding="utf-8")

    if not args.dry:
        ART.write_text(json.dumps(art, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"মোট মন্ত্র: {verses}")
    print(f"আসল দেবনাগরী সংস্কৃত রেখে দেওয়া হয়েছে: {kept}")
    print(f"sk-ঘর খালি করা হয়েছে (আর্টিফ্যাক্ট): {cleared}")
    for ch, n in per_ch:
        print(f"   মণ্ডল {ch}: {n}")
    print(f"জমা ফাইল: {ART.relative_to(ROOT)} ({len(store)} এন্ট্রি)"
          + ("  [dry-run — কিছু লেখা হয়নি]" if args.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
