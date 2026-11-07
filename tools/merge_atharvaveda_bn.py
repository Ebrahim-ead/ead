#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""অথর্ববেদ: ebanglalibrary-র বাংলা অনুবাদ সংস্কৃত মন্ত্রের সঙ্গে জোড়া লাগানো।

কেন আলাদা স্ক্রিপ্ট: সংস্কৃত মূল (২০ কাণ্ড, Vedic Heritage Portal) আর বাংলা
(ebanglalibrary — এই মুহূর্তে কাণ্ড ১–৭, ৫০টি অনুবাক) দুই ভিন্ন উৎস, ভিন্ন
কাঠামোয়। সংস্কৃত ডেটা সর্বদা অটুট থাকে; বাংলা যেটুকু পাওয়া যায় সেটুকু জোড়া
হয়, বাকি মন্ত্রে `bn` ফাঁকা থাকে — অনুমান করে কিছু বসানো হয় না।

মিলানোর নিয়ম (গুরুত্বপূর্ণ):
    ebanglalibrary-র একক «অনুবাক» আর শৌনক সংহিতার «সূক্ত» এক জিনিস নয় —
    সংস্কৃত সংস্করণে সূক্ত-সংখ্যা ভিন্ন (যেমন কাণ্ড ১: ৩৫ সূক্ত, বাংলায় ৬ অনুবাক)।
    তাই সূক্ত-নম্বর ধরে মেলানো ভুল হতো; মেলানো হয় ক্রমিক অবস্থানে —
    অনুবাক-পাঠের মন্ত্রগুলো একের পর এক কাণ্ডের মন্ত্র-ক্রমে বসে। উৎসে
    মন্ত্রের মোট সংখ্যা সমান হলে এটাই সঠিক জোড়া।

ইনপুট (না থাকলে কিছুই হয় না):
    assets/grantho/data/atharvaveda/_bn/atharvaveda/ch<k>.json
        {id, bn, verses:[{n, bn, sk, …}]}   ← fetch_ebl.py --group-by-num

আউটপুট (আলাদা, যাতে বারবার চালালেও মূল ডেটা নষ্ট না হয়):
    assets/grantho/data/atharvaveda/_bn_merged/index.json
    assets/grantho/data/atharvaveda/_bn_merged/ch<k>.json

চালানো:
    python3 tools/merge_atharvaveda_bn.py           # জোড়া লাগাও
    python3 tools/merge_atharvaveda_bn.py --install # মূল ডেটায় বসাও (বিল্ডের পর)
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "assets", "grantho", "data", "atharvaveda")
SRC = os.path.join(OUT, "_bn", "atharvaveda")
DST = os.path.join(OUT, "_bn_merged")

DEV = re.compile(r"[\u0900-\u097F]")
BN_SRC = "বাংলা অনুবাদ — ebanglalibrary.com (অথর্ববেদ সংহিতা, দিলীপ মুখোপাধ্যায় সম্পাদনা)"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def clean_bn(txt):
    """বাংলা পাঠ পরিষ্কার — শুধু ভাষা বাংলা কি না দেখে রাখা/বাদ দেওয়া।"""
    t = re.sub(r"\s+", " ", str(txt or "")).strip()
    if not t or len(t) < 3:
        return ""
    # ইংরেজি/IAST মূল মিশে থাকলে বাদ (সাইটের নিয়ম: বিদেশি পাঠ নয়)
    latin = len(re.findall(r"[A-Za-z]", t))
    if latin > max(6, len(t) // 4):
        return ""
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true",
                    help="জোড়া লাগানো ফল মূল ডেটায় বসাও")
    a = ap.parse_args()

    if not os.path.isdir(SRC):
        print("বাংলা-ফোল্ডার নেই:", os.path.relpath(SRC, REPO))
        print("  (সংস্কৃত পাঠ অটুট আছে — জোড়া লাগানোর কিছু নেই)")
        return 0

    src_idx_p = os.path.join(SRC, "index.json")
    src_idx = load(src_idx_p) if os.path.exists(src_idx_p) else {}
    src_chs = {c["id"]: c for c in (src_idx.get("chapters") or [])}

    merged, grand_bn, grand_tot = [], 0, 0
    for k in range(1, 21):
        fp = os.path.join(OUT, f"ch{k}.json")
        if not os.path.exists(fp):
            print(f"⛔ কাণ্ড {k}: মূল ফাইল নেই — থামানো হলো")
            return 1
        cj = load(fp)
        bn_fp = os.path.join(SRC, f"ch{k}.json")
        added = 0
        if os.path.exists(bn_fp) and cj["verses"]:
            bj = load(bn_fp)
            bn_vs = [v for v in (bj.get("verses") or []) if clean_bn(v.get("bn"))]
            if bn_vs:
                # সূক্ত-নম্বর নয় — ক্রমিক অবস্থান (উপরে ব্যাখ্যা)
                for i, bv in enumerate(bn_vs):
                    if i >= len(cj["verses"]):
                        break
                    v = cj["verses"][i]
                    if not (v.get("bn") or "").strip():
                        v["bn"] = clean_bn(bv["bn"])
                        v["bnSrc"] = BN_SRC
                        added += 1
        with_bn = sum(1 for v in cj["verses"] if (v.get("bn") or "").strip())
        if added:
            cj["withBn"] = with_bn
            if with_bn < len(cj["verses"]):
                cj["note"] = ("বাংলা অনুবাদ ebanglalibrary.com থেকে যেখানে পাওয়া গেছে "
                              "সেখানে যোগ করা হয়েছে; বাকি মন্ত্রে সংস্কৃত মূল পাঠ।")
        ch = {"id": k, "bn": cj.get("bn"), "count": len(cj["verses"]),
              "from": 1, "to": len(cj["verses"]), "withBn": with_bn,
              "suktaCount": cj.get("suktaCount")}
        merged.append(ch)
        grand_bn += with_bn
        grand_tot += len(cj["verses"])
        if added:
            print(f"  কাণ্ড {k}: +{added} মন্ত্রে বাংলা ({with_bn}/{len(cj['verses'])})")
        save(os.path.join(DST, f"ch{k}.json"), cj)

    old = {}
    old_p = os.path.join(OUT, "index.json")
    if os.path.exists(old_p):
        old = load(old_p)
    idx = dict(old)
    idx.update({"slug": "atharvaveda", "total": grand_tot, "withBn": grand_bn,
                "chapters": merged, "bnSrc": BN_SRC if grand_bn else old.get("bnSrc")})
    if grand_bn:
        idx["note"] = (f"{grand_bn:,}".translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
                       + f"/{grand_tot:,}".translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
                       + " মন্ত্রে বাংলা অনুবাদ (ebanglalibrary.com)। "
                       "বাকি মন্ত্রে সংস্কৃত মূল পাঠ — অনুমান করে কিছু বসানো হয় না।")
    save(os.path.join(DST, "index.json"), idx)
    print(f"\n✓ জোড়া লাগানো: {grand_bn}/{grand_tot} মন্ত্রে বাংলা → {os.path.relpath(DST, REPO)}")

    if a.install:
        import shutil
        for name in os.listdir(DST):
            shutil.copy2(os.path.join(DST, name), os.path.join(OUT, name))
        print("✓ মূল ডেটায় বসানো হয়েছে")
    else:
        print("   (মূল ডেটায় বসাতে: --install)")
    return 0


if __name__ == "__main__":
    ap2 = argparse.ArgumentParser(add_help=False)
    sys.exit(main())
