#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""অথর্ববেদ: ebanglalibrary-র বাংলা অনুবাদ সংস্কৃত মন্ত্রের সঙ্গে জোড়া লাগানো।

কেন আলাদা স্ক্রিপ্ট: সংস্কৃত মূল (২০ কাণ্ড, Vedic Heritage Portal) আর বাংলা
(ebanglalibrary — কেবল কাণ্ড ১–৬) দুই ভিন্ন উৎস, ভিন্ন কাঠামোয়। সংস্কৃত ডেটা
সর্বদা সম্পূর্ণ থাকে; বাংলা যেটুকু পাওয়া যায় সেটুকু জোড়া হয়, বাকি মন্ত্রে
`bn` ফাঁকা থাকে — অনুমান করে কিছু বসানো হয় না।

ইনপুট (ঐচ্ছিক, না থাকলে কিছুই হয় না):
    assets/grantho/data/atharvaveda/_bn/<k>/<s>.json   {sukta, verses:[{n,bn}]}

চালানো:
    python3 tools/merge_atharvaveda_bn.py              # জোড়া লাগাও
    python3 tools/merge_atharvaveda_bn.py --report      # কতটা হয়েছে দেখাও
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "assets", "grantho", "data", "atharvaveda")
BNIN = os.path.join(OUT, "_bn")


def main():
    if not os.path.isdir(BNIN):
        print("বাংলা-ফোল্ডার নেই:", os.path.relpath(BNIN, REPO))
        print("  (কিছু জোড়া লাগানোর দরকার নেই — সংস্কৃত পাঠ অটুট আছে)")
        return 0

    idxp = os.path.join(OUT, "index.json")
    with open(idxp, encoding="utf-8") as f:
        idx = json.load(f)
    grand_bn = 0
    for ch in idx.get("chapters", []):
        k = ch["id"]
        d = os.path.join(BNIN, str(k))
        if not os.path.isdir(d):
            continue
        fp = os.path.join(OUT, f"ch{k}.json")
        with open(fp, encoding="utf-8") as f:
            cj = json.load(f)
        # সূক্ত → মন্ত্র-অবস্থান
        pos = {}
        for sk in cj.get("suktas", []):
            for n in range(sk["from"], sk["to"] + 1):
                pos[n] = sk["s"]
        by_n = {v["n"]: v for v in cj["verses"]}
        added = 0
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(d, name), encoding="utf-8") as f:
                bj = json.load(f)
            s = int(bj.get("sukta") or 0)
            hits = [n for n, sn in pos.items() if sn == s]
            for i, bv in enumerate(bj.get("verses") or []):
                if i >= len(hits):
                    break
                v = by_n.get(hits[i])
                txt = (bv.get("bn") or "").strip()
                if v and txt and not v.get("bn"):
                    v["bn"] = txt
                    added += 1
        if added:
            cj["withBn"] = sum(1 for v in cj["verses"] if (v.get("bn") or "").strip())
            ch["withBn"] = cj["withBn"]
            cj["note"] = "বাংলা অনুবাদ ebanglalibrary.com থেকে যেখানে পাওয়া গেছে সেখানে যোগ করা হয়েছে।"
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(cj, f, ensure_ascii=False)
            grand_bn += added
            print(f"  কাণ্ড {k}: +{added} মন্ত্রে বাংলা")
    idx["withBn"] = sum(c.get("withBn") or 0 for c in idx["chapters"])
    with open(idxp, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print(f"✓ বাংলাসহ মোট: {idx['withBn']}/{idx['total']} মন্ত্র")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    sys.exit(main())
