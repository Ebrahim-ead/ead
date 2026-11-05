#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ঋগ্বেদের ডেটা থেকে বিদেশি পাঠ ছেঁটে ফেলা (ব্যবহারকারীর নির্দেশ, ২০২৬-১১-০৫)।

কেন: উৎস-সাইট মন্ত্রের বাংলা অনুবাদের পরেই Griffith-এর ইংরেজি অনুবাদ, দেবনাগরী
সংস্কৃত মূল ও IAST প্রতিলিপি একই কার্ডে জোড়া লাগিয়ে দেয়। সাইটে তখন বাংলার
পাশে ইংরেজি প্যারা আর সংস্কৃত অক্ষর দেখা যায় — ব্যবহারকারী চান না।

নিয়ম:
  · যে মন্ত্রে বাংলার সঙ্গে ইংরেজি/দেবনাগরী/IAST মিশে আছে (অথবা বাংলাই নেই,
    কেবল সংস্কৃত মূল) — সেই মন্ত্রটা **বাদ**।
  · যেগুলো পুরোপুরি বাংলা — হুবহু অটুট, এক অক্ষরও বদলায় না।
  · বাদ পড়া মন্ত্রের তথ্য `_dropped.json`-এ রাখা হয় (কোনটা কেন, কী ছিল) —
    পরে দরকার হলে ফেরানো যাবে; চাইলে `--no-log` দিয়ে বন্ধ।
  · `index.json`-এর মোট সংখ্যা, সূক্ত-সংখ্যা আবার হিসাব হয়
    (rigveda_suktas.main(apply=True))।

ব্যবহার:
    python3 tools/clean_rigveda.py            # করে দেখাও, কিছু লেখো না
    python3 tools/clean_rigveda.py --apply    # সত্যিই পরিষ্কার করো
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data/rigveda"

# দেবনাগরী (দাঁড়ি/॥ বাদ — ওগুলো বাংলা লেখাতেও আসতে পারে)
DEV = re.compile(r"[\u0900-\u0963\u0966-\u0970\u0971-\u097F]")
# IAST-এর বৈশিষ্ট্যপূর্ণ অক্ষর (রোমান হরফে সংস্কৃত)
IAST = re.compile(r"[āīūṛṣṭḍṇṃśṅñĀĪŪṚṢṬḌṆṂŚṄÑ]")
# Griffith-এর শিরোনাম-ধাঁচ
HYMN = re.compile(r"\bHYMN\b|Rig Veda Book")
# পরপর ল্যাটিন শব্দ
LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z'’\-]{2,}")
BN = re.compile(r"[\u0980-\u09FF]")
SRC_LINE = re.compile(r"^অনুবাদ\s*:\s*বাংলা অনুবাদ\s*—\s*ebanglalibrary\.com$")


def why_foreign(text):
    """কেন এই মন্ত্র বিদেশি-মিশ্রিত — কারণের তালিকা; খালি মানে পরিষ্কার বাংলা।"""
    if not text:
        return ["বাংলা নেই"]
    out = []
    if HYMN.search(text):
        out.append("Griffith-ইংরেজি")
    if DEV.search(text):
        out.append("দেবনাগরী")
    if IAST.search(text):
        out.append("IAST")
    run = 0
    for t in LATIN_RUN.finditer(text):
        run += 1
        if run >= 3:
            out.append("ইংরেজি প্যারা")
            break
    else:
        run = 0
    # মূলত বিদেশি পাঠ (বাংলা অক্ষর খুব কম)
    total = len(re.sub(r"\s", "", text))
    if total and len(BN.findall(text)) / total < 0.35:
        out.append("মূলত বিদেশি পাঠ")
    return out


def clean_chapter(obj):
    """এক অধ্যায়ের মন্ত্র ছেঁকে (নতুন obj, বাদ-তালিকা) ফেরে।"""
    kept, dropped = [], []
    for v in obj.get("verses", []):
        reasons = why_foreign(v.get("bn") or "")
        if reasons:
            dropped.append({"n": v.get("n"), "seg": v.get("seg"),
                            "why": reasons,
                            "bn": (v.get("bn") or "")[:400]})
            continue
        kept.append(v)
    new = dict(obj)
    new["verses"] = kept
    new["count"] = len(kept)
    new["withBn"] = sum(1 for v in kept if v.get("bn"))
    new["to"] = len(kept)
    if new.get("pages"):
        # কোন পাতা থেকে কিছুই না এলে তালিকা থেকে বাদ
        pages = [p for p in new["pages"] if kept]
        new["pages"] = pages
    return new, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-log", action="store_true")
    a = ap.parse_args()

    if not DATA.exists():
        raise SystemExit("ডেটা পাওয়া গেল না: " + str(DATA))

    total_before = total_after = 0
    log = {"_note": "বাদ পড়া মন্ত্র — বাংলার সঙ্গে ইংরেজি/দেবনাগরী মিশে ছিল "
                    "(ব্যবহারকারীর নির্দেশে সরানো হয়েছে)", "chapters": {}}
    changed = False

    for ch_file in sorted(DATA.glob("ch*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        obj = json.loads(ch_file.read_text(encoding="utf-8"))
        before = len(obj.get("verses", []))
        new, dropped = clean_chapter(obj)
        total_before += before
        total_after += len(new["verses"])
        if dropped:
            changed = True
            log["chapters"][ch_file.stem] = dropped
            print(f"  {ch_file.name}: {before} → {len(new['verses'])} মন্ত্র "
                  f"(বাদ {len(dropped)})")
            if a.apply:
                ch_file.write_text(
                    json.dumps(new, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
        else:
            print(f"  {ch_file.name}: {before} মন্ত্র — পরিষ্কার")

    print(f"\nমোট: {total_before} → {total_after} মন্ত্র "
          f"(বাদ {total_before - total_after})")

    if not a.apply:
        print("(পরীক্ষা মোড — লিখতে --apply)")
        return 0

    if not a.no_log:
        # আগের রানের তালিকা মুছে ফেলি না — বাদ-পড়া মন্ত্রের পূর্ণ ইতিহাস থাকে
        old_p = DATA / "_dropped.json"
        if old_p.exists():
            try:
                prev = json.loads(old_p.read_text(encoding="utf-8"))
                for k, v in (prev.get("chapters") or {}).items():
                    merged = log["chapters"].setdefault(k, [])
                    have = {(d.get("n"), tuple(d.get("why") or [])) for d in merged}
                    for d in v:
                        if (d.get("n"), tuple(d.get("why") or [])) not in have:
                            merged.append(d)
            except Exception:
                pass
        (DATA / "_dropped.json").write_text(
            json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("বাদ-তালিকা:", (DATA / "_dropped.json").relative_to(ROOT))

    # index.json-এর গণনা আসল ফাইল থেকে আবার — মন্ত্র কমলে total/chapters পুরনো
    # থাকলে সাইটে ভুল সংখ্যা (১০,৯৫৪) দেখাত, আর guard-ও ভুল মোটে তুলনা করত।
    idx_p = DATA / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in idx.get("chapters", [])}
    for ch_file in sorted(DATA.glob("ch*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        cid = int(re.sub(r"\D", "", ch_file.stem))
        obj = json.loads(ch_file.read_text(encoding="utf-8"))
        n = len(obj.get("verses", []))
        c = by_id.get(cid, {"id": cid, "bn": obj.get("bn", f"ঋগ্বেদ — {cid}")})
        c["count"] = n
        c["withBn"] = sum(1 for v in obj.get("verses", []) if v.get("bn"))
        c["from"], c["to"] = 1, n
        by_id[cid] = c
    idx["chapters"] = [by_id[k] for k in sorted(by_id)]
    idx["total"] = sum(c["count"] for c in idx["chapters"])
    idx["withBn"] = sum(c["withBn"] for c in idx["chapters"])
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")

    # সূক্ত/শ্লোকের হিসাব আবার — মন্ত্র কমায় সীমানাও বদলায়
    sys.path.insert(0, str(ROOT / "tools"))
    import rigveda_suktas
    rigveda_suktas.DATA = DATA
    rigveda_suktas.main(apply=True)

    # আয়না-ফাইল বিল্ড করে (পাতা-বিল্ড)
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "tools/build_pages.py")],
                       cwd=ROOT, capture_output=True, text=True)
    print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "")
    if r.returncode:
        print("⛔ বিল্ড ব্যর্থ:", (r.stderr or "")[-300:])
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
