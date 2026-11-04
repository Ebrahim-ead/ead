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


def load_json(p, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


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
        base["slugs"][slug] = {"total": idx.get("total", 0),
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
    broken = []
    for slug, idx in indices():
        b = base["slugs"].get(slug)
        if not b or not b.get("total"):
            continue
        cur, was = idx.get("total", 0), b["total"]
        if cur < was * TOL:
            broken.append((slug, was, cur))

    if not broken:
        print("✓ সব গ্রন্থের ডেটা অটুট (বেসলাইনের ৮৫%-এর উপরে)")
        return 0

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

    env = dict(os.environ, GRANTHO_ALLOW_SHRINK="1")
    subprocess.run([sys.executable, "-u", "tools/build_pages.py"], cwd=ROOT, env=env)
    git("add", "grantho", "assets/grantho/data")
    msg = ("ডেটা-রক্ষা: ছোট হয়ে যাওয়া গ্রন্থ বেসলাইন থেকে ফিরিয়ে আনা "
           f"({', '.join(s for s, _, _ in broken)})")
    if git("commit", "-m", msg).returncode:
        print("কমিট করার মতো পরিবর্তন নেই")
        return 0
    if git("push", "origin", "HEAD:main").returncode:
        print("⛔ push ব্যর্থ")
        return 1
    print("✓ মেরামত main-এ push হলো")
    return 0


if __name__ == "__main__":
    sys.exit(main())
