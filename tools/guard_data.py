#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main-এ ঢুকে পড়া ছোট/ভাঙা ডেটা ফিরিয়ে আনা (নিজে থেকেই)।

কেন: ২০২৬-১১-০৪-এ রাতের রান নীরবে অনুবাদ মুছেছিল (গরুড় ১০৫ → ২১ শ্লোক)।
ফেচার ও বিল্ডে বলয় বসানোর পরও পুরনো রানে চলা বট-ব্রাঞ্চ থেকে এমন কিছু
main-এ ঢুকে যেতে পারে। এই স্ক্রিপ্টটা প্রতিটি push-এ main-এর index.json
`_baseline.json`-এর সঙ্গে মিলিয়ে দেখে, আর কোনো গ্রন্থ ১৫%-এর বেশি ছোট হলে
বেসলাইন-কমিট থেকে সেই গ্রন্থের ডেটা ফিরিয়ে এনে পাতা আবার বানায়।

বেসলাইন হালনাগাদ: ডেটা স্বেচ্ছায় ছোট/বদলালে
    python3 tools/guard_data.py --set-baseline
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data"
BASE_FILE = DATA / "_baseline.json"
TOL = 0.85          # ১৫%-এর বেশি কমলেই সন্দেহ

# সাইটে কেবল এই দুটি গ্রন্থ থাকবে (ব্যবহারকারীর সিদ্ধান্ত, ২০২৬-১১-০৫)।
ACTIVE = ("gita", "rigveda", "yajurveda-shukla")
KEEP_PAGES = {"gita.html", "rigveda.html", "veda.html", "yajurveda-shukla.html"}


def load_json(p, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def site_total(idx):
    """সাইটে দেখানো মোট মন্ত্র = প্রতি মণ্ডলের count যোগফল।

    index.json-এর `total` কেবল শেষ রানে যা নামানো হলো তার হিসাব হতে পারে
    (মণ্ডল ১০ যোগ হওয়ার পরেও total পুরনো ৯ মণ্ডলের সংখ্যা দেখাচ্ছিল)।
    """
    chs = idx.get("chapters") or []
    s = sum(int(c.get("count") or 0) for c in chs)
    return s or int(idx.get("total") or 0)


def indices():
    for p in sorted(DATA.glob("*/index.json")):
        idx = load_json(p)
        if idx and idx.get("chapters"):
            yield p.parent.name, idx


def git(*args, check=False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {args[0]} ব্যর্থ: {r.stderr.strip()}")
    return r


def head_sha():
    return git("rev-parse", "HEAD", check=True).stdout.strip()


def set_baseline():
    sha = head_sha()
    base = {"_commit": sha, "_note": "এটি ভালো-জানা ডেটার হিসাব; এর চেয়ে "
            "১৫%-এর বেশি ছোট হলে guard_data.py ফিরিয়ে আনে।", "slugs": {}}
    for slug, idx in indices():
        base["slugs"][slug] = {"total": site_total(idx),
                               "withBn": idx.get("withBn", 0),
                               "chapters": len(idx["chapters"])}
    BASE_FILE.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    print(f"বেসলাইন লেখা হলো ({len(base['slugs'])} গ্রন্থ, কমিট {sha[:8]})")
    return 0


def main():
    if "--set-baseline" in sys.argv:
        return set_baseline()

    base = load_json(BASE_FILE)
    if not base or not base.get("slugs"):
        print("বেসলাইন নেই — কিছুই করার নেই")
        return 0

    bcommit = base.get("_commit")

    # ১) পরিধি-রক্ষা: পুরনো ব্রাঞ্চের রান main-এ বাদ-দেওয়া গ্রন্থ ফিরিয়ে আনতে পারে
    #    (২০২৬-১১-০৪-এ ঠিক তাই হয়েছিল)। সেগুলো এখানেই সরিয়ে দিই।
    removed = []
    for d in sorted(DATA.iterdir()):
        if d.is_dir() and d.name not in ACTIVE and d.name != "_debug":
            import shutil
            shutil.rmtree(d)
            removed.append(d.name)
    for f in sorted((ROOT / "grantho/hindu").glob("*.html")):
        if f.name not in KEEP_PAGES:
            f.unlink()
            removed.append("পাতা " + f.name)
    for f in sorted(DATA.glob("_fetch_report_*.txt")):
        f.unlink()
    if removed:
        print("🧹 পরিধির বাইরের জিনিস সরানো হলো:", ", ".join(removed[:6]),
              "…" if len(removed) > 6 else "")

    broken = []
    for slug, idx in indices():
        b = base["slugs"].get(slug)
        if not b or not b.get("total"):
            continue
        cur, was = site_total(idx), b["total"]
        if cur < was * TOL:
            broken.append((slug, was, cur))

    if not broken:
        print("✓ সব গ্রন্থের ডেটা অটুট (বেসলাইনের ৮৫%-এর উপরে)")
        if not removed:
            return 0
        return rebuild_and_push("পরিধি-রক্ষা: অননুমোদিত গ্রন্থ সরানো")

    print("⛔ ছোট/ভাঙা ডেটা ধরা পড়েছে:")
    for slug, was, cur in broken:
        print(f"   · {slug}: {was} → {cur}")
    if not bcommit:
        print("বেসলাইন-কমিট নেই — ফেরানো গেল না")
        return 1

    for slug, _, _ in broken:
        r = git("checkout", bcommit, "--", f"assets/grantho/data/{slug}")
        if r.returncode:
            print(f"   ⚠ {slug} ফেরানো গেল না: {r.stderr.strip()}")
        else:
            print(f"   ↩ {slug} বেসলাইন ({bcommit[:8]}) থেকে ফিরিয়ে আনা হলো")

    return rebuild_and_push("ডেটা-রক্ষা: ছোট হয়ে যাওয়া গ্রন্থ বেসলাইন থেকে "
                            f"ফিরিয়ে আনা ({', '.join(s for s, _, _ in broken)})")


def rebuild_and_push(msg):
    env = dict(os.environ, GRANTHO_ALLOW_SHRINK="1")
    subprocess.run([sys.executable, "-u", "tools/build_pages.py"], cwd=ROOT, env=env)
    git("add", "-A", "grantho", "assets/grantho/data")
    if git("commit", "-m", msg).returncode:
        print("কমিট করার মতো পরিবর্তন নেই")
        return 0
    if git("push", "origin", "HEAD:main").returncode:
        print("⛔ push ব্যর্থ")
        return 1
    print("✓ main-এ push হলো —", msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
