#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ঋগ্বেদের মন্ত্র → সূক্তে সাজানো, আর প্রতিটি শ্লোক আলাদা করা।

সমস্যা: ebanglalibrary থেকে নামানো ঋগ্বেদে মন্ত্রগুলো মণ্ডলভিত্তিক এক ফাইলে
একটানা নম্বরে (১…২২৯৯) — সূক্তের সীমানা নেই, শ্লোকও একসঙ্গে জোড়া লাগা।

সমাধান:
  ১. **সূক্ত-ভাগ** — মোট মন্ত্র ÷ মোট সূক্ত ধরে (সূক্ত-সংখ্যা ঋগ্বেদের জানা
     তালিকা থেকে)। উৎসে সূক্তের শিরোনাম নেই, তাই এটি আনুমানিক — পাতায়
     স্পষ্ট লেখা থাকে। মণ্ডল ১০-এ URL থেকে সূক্ত-পরিচয় এলে সেটাই নির্ভুল।
  ২. **শ্লোক-ভাগ** — এক মন্ত্রে কয়েকটি পঙক্তি/শ্লোক জোড়া লাগা থাকলে দাঁড়ি
     (।॥) ধরে ভাগ, প্রতিটি টুকরো যথেষ্ট বড় হলে তবেই।

লেখা হয় শুধু *সীমানা* — bn লেখা দুইবার কপি করি না (ফাইল ফুলে যেত):
    sutkas: [{id, from, to, mantra, shloka, cuts: {"<মন্ত্র-নং>": [অংশ, …]}}]
এবং index.json-এ suktaTotal / shlokaTotal।
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data/rigveda"

# ঋগ্বেদের মণ্ডলভিত্তিক সূক্ত-সংখ্যা (মোট ১০২৮ সূক্ত)
SUKTAS = {1: 191, 2: 43, 3: 62, 4: 58, 5: 87, 6: 75, 7: 104,
          8: 103, 9: 114, 10: 191}

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

DANDA = re.compile(r"(?<=[।॥])\s+")
MIN_PADA = 22          # এর চেয়ে ছোট টুকরো আলাদা শ্লোক হিসেবে গড়ি না


def split_padas(text):
    """এক মন্ত্রের ভেতরের পঙক্তি — দাঁড়ি ধরে, ছোট টুকরো আগেরটার সঙ্গে জুড়ে।"""
    parts = [p.strip() for p in DANDA.split(text or "") if p.strip()]
    if len(parts) <= 1:
        return [text.strip()] if text and text.strip() else []
    merged = []
    for p in parts:
        if merged and len(p) < MIN_PADA:
            merged[-1] = (merged[-1] + " " + p).strip()
        else:
            merged.append(p)
    return merged


def plan_bounds(total, nsukta):
    """মোট মন্ত্রকে nsukta ভাগে সমান-সমান — বাকিটা প্রথমগুলোতে একটি করে।"""
    if nsukta <= 0 or total <= 0:
        return []
    base, rem = divmod(total, nsukta)
    out, cur = [], 1
    for i in range(nsukta):
        n = base + (1 if i < rem else 0)
        if n <= 0:
            continue
        out.append((cur, cur + n - 1))
        cur += n
    return out


def main(apply=False):
    idx_p = DATA / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8"))
    g_sukta = g_shloka = g_split = 0
    for ch in idx["chapters"]:
        m = ch["id"]
        p = DATA / f"ch{m}.json"
        if not p.exists():
            continue
        obj = json.loads(p.read_text(encoding="utf-8"))
        verses = {v["n"]: v for v in obj.get("verses", [])}
        order = [v["n"] for v in obj.get("verses", [])]
        ns = SUKTAS.get(m, 0)
        bounds = plan_bounds(len(order), ns)
        # সূক্ত-পরিচয় মন্ত্রেই থাকলে («১.» … «৭.» বা seg ফিল্ড) সেটাই আসল সীমানা।
        # নইলে আগের মতো মোট মন্ত্র ÷ সূক্ত-সংখ্যা ধরে আনুমানিক।
        ids = []
        for n in order:
            sg = verses[n].get("seg")
            if sg:
                ids.append(int(sg))
                continue
            t = (verses[n].get("bn") or "")[:6]
            mm = re.match(r"^\s*([০-৯0-9]{1,3})\s*[।.]", t)
            ids.append(int(mm.group(1).translate(BN_DIGITS)) if mm else None)
        groups, cur_g, ok = [], [], True
        for n, i in zip(order, ids):
            if i is None:
                ok = False
                break
            if i == 1 and cur_g:
                groups.append(cur_g)
                cur_g = []
            cur_g.append(i)
        if cur_g:
            groups.append(cur_g)
        real = ok and len(groups) >= 2 and all(
            g == list(range(1, len(g) + 1)) for g in groups)
        if real:
            bounds, pos = [], 0
            for g in groups:
                bounds.append((order[pos], order[pos + len(g) - 1]))
                pos += len(g)
            print(f"   · মণ্ডল {m}: সূক্ত-পরিচয় মন্ত্রেই পাওয়া গেল → "
                  f"{len(bounds)} সূক্ত (অনুমান লাগেনি)")
        suktas, shl_total = [], 0
        # পুরনো সূক্তের অতিরিক্ত ক্ষেত্র (যেমন `deity` — সূক্তের দেবতা) যেন
        # হারিয়ে না যায়: একই id-র পুরনো এন্ট্রি থেকে বাকি সব কী ধরে রাখি।
        old_by_id = {s.get("id"): s for s in (obj.get("suktas") or [])}
        for k, (a, b) in enumerate(bounds, 1):
            cuts, shl = {}, 0
            for n in order:
                if not (a <= n <= b):
                    continue
                parts = split_padas(verses[n].get("bn") or "")
                if len(parts) > 1:
                    cuts[str(n)] = parts
                    shl += len(parts)
                else:
                    shl += 1
            ent = dict(old_by_id.get(k) or {})
            ent.update({"id": k, "from": a, "to": b,
                        "mantra": sum(1 for n in order if a <= n <= b),
                        "shloka": shl, "cuts": cuts})
            suktas.append(ent)
            shl_total += shl
            g_split += len(cuts)
        obj["suktas"] = suktas
        obj["suktaCount"] = len(suktas)
        obj["shlokaCount"] = shl_total
        if apply:
            p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")
        ch["suktaCount"] = len(suktas)
        ch["shlokaCount"] = shl_total
        g_sukta += len(suktas)
        g_shloka += shl_total
        print(f"মণ্ডল {m}: {len(order)} মন্ত্র → {len(suktas)} সূক্ত · "
              f"{shl_total} শ্লোক")
    idx["suktaTotal"] = g_sukta
    idx["shlokaTotal"] = g_shloka
    idx["note"] = ("সূক্ত-সীমানা মোট মন্ত্র ÷ সূক্ত-সংখ্যা ধরে আনুমানিক (উৎসে "
                   "সূক্তের শিরোনাম নেই); শ্লোক-ভাগ দাঁড়ি ধরে, তাই পড়ার সময় "
                   "প্রতিটি শ্লোক আলাদা দেখা যায়।")
    if apply:
        idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    print(f"\nমোট: {g_sukta} সূক্ত · {g_shloka} শ্লোক · "
          f"{g_split} মন্ত্র ভাগ করা হয়েছে")
    if not apply:
        print("(পরীক্ষা মোড — লিখতে: --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
