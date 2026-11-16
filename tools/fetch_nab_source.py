#!/usr/bin/env python3
"""English Bible — vatican.va থেকে আনা New American Bible (2002) পাঠ।

কেন এই স্ক্রিপ্ট: vatican.va-র IntraText আর্কাইভ (ENG0839) থেকে এক-এক করে
অধ্যায় নামানো মানে ১,১৮৯টি HTTP অনুরোধ — এবং কিছু পরিবেশে (এই স্যান্ডবক্স
সহ) TLS হ্যান্ডশেক নেটওয়ার্ক-স্তরে ব্লকড। তাই **একই উৎস থেকে** স্ক্র্যাপ করা
একটি সর্বজনীন আয়না ব্যবহার করি (bytewired9/FreeNAB, `vatican.py` দিয়ে
vatican.va/ENG0839/_INDEX.HTM থেকেই নামানো), তারপর নিজের পার্সার দিয়ে
পদ ও পাদটীকা আলাদা করি।

পূর্ণ কর্মপ্রবাহ (মাত্র দুই নির্দেশ):
    python3 tools/fetch_nab_source.py         # উৎস-আয়না নামায়
    python3 tools/parse_nab.py                # JSON তৈরি করে (~৫ সেকেন্ড)

তারপর: DATA_VERSION বাড়ান → node tools/test_cache_version.mjs --update

নীতিমালা:
  ▸ পাঠ বদলানো হয় না; শুধু লাইন-জোড়া ও সাদা জায়গা ঠিক হয়;
  ▸ উৎসে যে পদ নেই তা **অনুমান করে বসানো হয় না** — রিপোর্টে যায়
    (assets/grantho/data/_debug/nab_parse.txt);
  ▸ ক্যাথলিক ৭টি পুস্তক (তোবিত, যুদিথ, প্রজ্ঞা, সিরাখ, বারুক, ১–২ মাক্কাবি)
    বাংলা অংশে নেই, কিন্তু ইংরেজি অংশে আছে — ব্যবহারকারীর সিদ্ধান্ত।
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = Path("/tmp/FreeNAB")
MIRROR = "https://github.com/bytewired9/FreeNAB.git"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(TMP), help="ক্লোন রাখার জায়গা")
    ap.add_argument("--keep", action="store_true", help="আগের ক্লোন থাকলে আবার না নামাও")
    args = ap.parse_args()

    dest = Path(args.dir)
    books = dest / "public/nabre_books"
    if books.is_dir() and args.keep:
        n = len(list(books.rglob("*.txt")))
        print(f"আগের ক্লোন ব্যবহার করছি — {n} ফাইল · {books}")
        return 0

    if dest.exists():
        shutil.rmtree(dest)

    print(f"নামাচ্ছি: {MIRROR}")
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "-q", MIRROR, str(dest)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("ক্লোন ব্যর্থ:\n" + (r.stderr or ""), file=sys.stderr)
        return 1

    if not books.is_dir():
        print(f"প্রত্যাশিত ফোল্ডার নেই: {books}", file=sys.stderr)
        return 1

    txts = list(books.rglob("*.txt"))
    print(f"✓ {len(txts)} ফাইল · {sum(f.stat().st_size for f in txts) / 1e6:.1f} MB")
    print(f"  উৎস: vatican.va/archive/ENG0839/_INDEX.HTM (FreeNAB-আয়না)")
    print("\nপরবর্তী ধাপ:  python3 tools/parse_nab.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
