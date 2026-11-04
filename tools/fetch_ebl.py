#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ebanglalibrary.com — বাংলা বেদ/উপনিষদ/পুরাণ ব্যাচ-ডাউনলোডার।

কেন এটা: সাইটের টপিক/লেসন স্লাগ WP কেটে ফেলে (৫০ অক্ষরে), তাই URL আন্দাজ করা
চলে না। বদলে সাইটম্যাপ (wp-sitemap-posts-sfwd-topic-N.xml / sfwd-lessons-N.xml)
থেকে সব URL এনে কীওয়ার্ড মিলিয়ে নামানো হয়। সব পাতা লগইন ছাড়াই খোলা।

পাতার গঠন (যাচাই করা):
    ### পঞ্চম খণ্ড – শিরোনাম
    ৪৬৯. <সংস্কৃত শ্লোক> ॥ ১॥
    অন্বয় : ...
    সরলার্থ : <বাংলা>        ← bn
    মন্তব্য : <টীকা>          ← bnNote

বিধি:
    --discover ছান্দোগ্য          → কেবল URL-তালিকা দেখাও
    --slug chandogya --match ছান্দোগ্য --by-ordinal   → অধ্যায়-ক্রমে নামাও
    --slug bhabishya --match "ভবিষ্য পুরাণ" --chain    → «Next Lesson» ধরে ক্রমে নামাও
    --dump 2                      → প্রথম ২ পাতার কাঁচা পাঠ _debug/ তে রাখো
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.ebanglalibrary.com"
UA = "Mozilla/5.0 (compatible; ead-grantho/1.0; +https://github.com/Ebrahim-ead/ead)"
SRC = "বাংলা অনুবাদ — ebanglalibrary.com"

TOPIC_SITEMAPS = [f"{BASE}/wp-sitemap-posts-sfwd-topic-{i}.xml" for i in range(1, 17)]
LESSON_SITEMAPS = [f"{BASE}/wp-sitemap-posts-sfwd-lessons-{i}.xml" for i in range(1, 30)]

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
DEV_RE = re.compile("[\u0900-\u0963\u0966-\u097F]")  # দাঁড়ি (।॥) বাদ
DEV_DIGITS = "०१२३४५६७८९"
ORD = {"প্রথম": 1, "দ্বিতীয়": 2, "দ্বিতীয়ো": 2, "তৃতীয়": 3, "চতুর্থ": 4,
       "পঞ্চম": 5, "ষষ্ঠ": 6, "সপ্তম": 7, "অষ্টম": 8, "নবম": 9, "দশম": 10,
       "একাদশ": 11, "দ্বাদশ": 12}
NUM_LINE = re.compile(r"^([০-৯]{1,3})\s*[\.।]\s*(.*)$")
MARK = re.compile("[।॥]{2}\\s*([\u09e6-\u09ef\u0966-\u096f]{1,3})\\s*[।॥]{2}")
TAIL_MARK = re.compile("[।॥]{1,2}\\s*([\u09e6-\u09ef\u0966-\u096f]{1,3})\\s*[।॥]{0,2}\\s*$")


def to_int(s):
    s = str(s).strip()
    if not s:
        return None
    if all(c in BN_DIGITS for c in s):
        return int("".join(str(BN_DIGITS.index(c)) for c in s))
    if all(c in DEV_DIGITS for c in s):
        return int("".join(str(DEV_DIGITS.index(c)) for c in s))
    try:
        return int(s)
    except Exception:
        return None


def get(url, tries=3, timeout=45):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "bn,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


# ---------------- পাঠ নিষ্কাশন ----------------
def text_of(frag):
    s = re.sub(r"<script.*?</script>", " ", frag, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<h[1-6][^>]*>", "\n\n## ", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    for a, b in (("\u00a0", " "), ("\u200b", ""), ("\ufeff", ""), ("\\[", "["),
                 ("\\]", "]"), ("\\", "")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t]+", " ", s)
    s = "\n".join(x.strip() for x in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def page_text(h):
    if not h:
        return ""
    m = re.search(r"<h1[^>]*>.*?</h1>", h, flags=re.S | re.I)
    if m:
        h = h[m.end():]
    # book/lesson-এর পাশের সূচি-ব্লক বাদ
    cut = min([i for i in (h.find('id="ld-lesson-toc'), h.find("Bookmark"),
                           h.find("Post a comment")) if i > 500] or [len(h)])
    h = h[:cut]
    txt = text_of(h)
    out = []
    for ln in txt.split("\n"):
        low = ln.lower()
        if not ln:
            continue
        if low.startswith(("skip to", "menu", "search", "লাইব্রেরি »", "home »",
                           "continue with", "username", "password", "register",
                           "accessing this", "table of contents", "expand",
                           "previous lesson", "next lesson", "back to book")):
            continue
        out.append(ln)
    return "\n".join(out)


def parse_verses(txt):
    verses, cur, counter = [], None, 0
    # পাতায় «অন্বয়/সরলার্থ» লেবেল থাকলে কঠোর লেবেল-ভিত্তিক পাঠ;
    # না থাকলে (ঋগ্বেদ-ধাঁচ) অনুচ্ছেদই অনুবাদ।
    has_labels = ("অন্বয়" in txt) or ("সরলার্থ" in txt)

    def close():
        nonlocal cur
        if cur and cur["bn"]:
            verses.append(cur)
        cur = None

    for raw in txt.split("\n"):
        ln = raw.strip()
        if not ln or ln in (",", "|"):
            continue
        if ln.startswith("## "):
            continue
        m = NUM_LINE.match(ln)
        if m and (cur is None or cur["bn"] or cur["part"] in ("bn", "note")):
            close()
            counter += 1
            cur = {"n": counter, "gidx": to_int(m.group(1)), "sk": [], "anv": [],
                   "bn": [], "note": [], "part": "sk"}
            if m.group(2):
                rest = m.group(2)
                if not has_labels and not DEV_RE.search(rest) and len(rest) > 25:
                    cur["part"] = "bn"      # সংখ্যার পরেই বাংলা (ঋগ্বেদ-ধাঁচ)
                cur[cur["part"]].append(rest)
            continue
        if cur is None:
            continue
        lbl = re.match(r"^(অন্বয়|সরলার্থ|মন্তব্য|ভাষ্য|টীকা)\s*[:\-–—]\s*", ln)
        if lbl:
            cur["part"] = {"অন্বয়": "anv", "সরলার্থ": "bn", "মন্তব্য": "note",
                           "ভাষ্য": "note", "টীকা": "note"}[lbl.group(1)]
            rest = ln[lbl.end():].strip()
            if rest:
                cur[cur["part"]].append(rest)
            continue
        if (not has_labels and cur["part"] == "sk"
                and not DEV_RE.search(ln) and len(ln) > 25):
            cur["part"] = "bn"          # সংস্কৃতহীন পাতা: সরল অনুচ্ছেদই অনুবাদ
        cur[cur["part"]].append(ln)
    close()

    out, last = [], 0
    for v in verses:
        sk = " ".join(v["sk"]).strip()
        bn = " ".join(v["bn"]).strip()
        if not bn or len(bn) < 15:
            continue
        # স্থানীয় মন্ত্র-সংখ্যা: সংস্কৃতের শেষ «॥ ১॥»
        n = None
        tail = TAIL_MARK.search(sk[-40:]) if sk else None
        if tail:
            n = to_int(tail.group(1))
        if not n or (last and n <= last):
            n = last + 1
        last = n
        bn = re.sub(r"^\s*(Bookmark|Previous|Next)\s+", "", bn)
        bn = re.sub(r"\s*Bookmark\s*$", "", bn)
        note = re.sub(r"\s*Bookmark\s*$", "", " ".join(v["note"]).strip())
        out.append({"n": n, "sk": sk, "anv": " ".join(v["anv"]).strip(),
                    "bn": bn, "bnNote": note})
    return out


def next_link(h):
    m = re.search(r'href="([^"]+)"[^>]*>\s*Next Lesson', h, flags=re.I)
    if not m:
        m = re.search(r'Next Lesson[^<]*</a>', h)
        return None
    return htmllib.unescape(m.group(1))


def lesson_next(h):
    m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*Next Lesson', h, re.I)
    return htmllib.unescape(m.group(1)) if m else None


# ---------------- সংগ্রহ ----------------
def norm(x):
    """স্পেস ও হাইফেন বাদ দিয়ে মেলানোর রূপ।"""
    return re.sub(r"[\s\-–—/]+", "", x.lower())


def sitemap_urls(sitemaps, keyword, want=("topics", "lessons", "books")):
    pat = norm(keyword)
    urls, seen = [], set()
    for sm in sitemaps:
        x = get(sm)
        if not x:
            continue
        for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x):
            u = htmllib.unescape(loc).strip()
            if not any(w in u for w in want):
                continue
            dec = norm(urllib.parse.unquote(u))
            if pat in dec and u not in seen:
                seen.add(u)
                urls.append(u)
    return urls


def book_lessons(book_url):
    """বই-পাতার সূচি থেকে লেসন-সংযোগ (ক্রম অপরিবর্তিত)।"""
    h = get(book_url)
    if not h:
        return []
    out, seen = [], set()
    for m in re.finditer(r'href="(https://www\.ebanglalibrary\.com/lessons/[^"#?]+)"', h):
        u = htmllib.unescape(m.group(1))
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def ordinal_of(url):
    t = urllib.parse.unquote(url)
    for k, v in ORD.items():
        if k in t:
            return v, k
    return None, None


def write_chapter(out_dir, idx, title, verses, url):
    vs = []
    for v in verses:
        d = {"n": v["n"], "sk": v["sk"], "bn": v["bn"], "spk": "", "bnSrc": SRC}
        if v.get("bnNote"):
            d["bnNote"] = v["bnNote"]
        if v.get("anv"):
            d["anv"] = v["anv"]
        vs.append(d)
    os.makedirs(out_dir, exist_ok=True)
    obj = {"id": idx, "bn": title, "count": len(vs), "from": 1, "to": len(vs),
           "verses": vs, "url": url}
    with open(os.path.join(out_dir, f"ch{idx}.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    return {"id": idx, "bn": title, "count": len(vs), "from": 1, "to": len(vs),
            "withBn": sum(1 for v in vs if v["bn"]), "url": url}


def build_index(out_dir, slug, title, chapters, word):
    byc = {c["id"]: c for c in chapters}
    chs = [byc[k] for k in sorted(byc)]
    for c in chs:
        c.pop("url", None)
    idx = {"slug": slug, "bn": title, "en": slug.title(),
           "total": sum(c["count"] for c in chs),
           "withBn": sum(c["withBn"] for c in chs), "chapters": chs,
           "verseWord": word, "bnSrc": SRC,
           "note": "মূল সংস্কৃত পাঠ ও বাংলা অনুবাদ — ebanglalibrary.com"}
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--title", default="")
    ap.add_argument("--match", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--out", default="assets/grantho/data")
    ap.add_argument("--word", default="মন্ত্র")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--by-ordinal", action="store_true")
    ap.add_argument("--chain", action="store_true")
    ap.add_argument("--book", action="store_true", help="বই-পাতার সূচি থেকে সব লেসন")
    ap.add_argument("--group-by-num", action="store_true",
                    help="পাতার শিরোনামে «০৬।১৩» থাকলে প্রথম সংখ্যা = অধ্যায়")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--dump", type=int, default=0)
    args = ap.parse_args()

    if args.discover:
        urls = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        print(f"মিলেছে {len(urls)}")
        for u in urls:
            print(" ", urllib.parse.unquote(u))
        return

    out_dir = os.path.join(args.out, args.slug) if args.slug else ""

    if args.url:                                     # একক পাতা (পরীক্ষা/ডাম্প)
        h = get(args.url)
        txt = page_text(h)
        vs = parse_verses(txt)
        print(f"মন্ত্র: {len(vs)}")
        for v in vs[: args.dump or 3]:
            print(f" {v['n']} | sk: {v['sk'][:80]}")
            print(f"    bn: {v['bn'][:100]}")
            if v["bnNote"]:
                print(f"    note: {v['bnNote'][:60]}")
        if args.dump:
            os.makedirs(os.path.join(args.out, "_debug"), exist_ok=True)
            fn = re.sub(r"[^\w]+", "_", urllib.parse.unquote(args.url))[-60:]
            with open(os.path.join(args.out, "_debug", fn + ".txt"), "w",
                      encoding="utf-8") as f:
                f.write(txt)
            print("ডাম্প:", fn + ".txt")
        return

    if args.chain and args.url:
        return

    # ---- তালিকা বানানো ----
    if args.book:
        items = [(i, u) for i, u in enumerate(book_lessons(args.url), start=args.start)]
        if args.max:
            items = items[: args.max]
    elif args.chain:
        urls = [args.url] if args.url else []
        if not urls:
            cands = sitemap_urls(LESSON_SITEMAPS, args.match)
            urls = cands[:1]
        # ক্রম: «Next Lesson» শৃঙ্খল
        chain, seen = [], set()
        u = urls[0]
        while u and u not in seen and (not args.max or len(chain) < args.max):
            seen.add(u)
            h = get(u)
            if not h:
                break
            chain.append(u)
            nu = lesson_next(h)
            if not nu or nu in seen:
                break
            u = nu
            time.sleep(0.4)
        items = [(i, u) for i, u in enumerate(chain, start=args.start)]
    else:
        allu = sitemap_urls(TOPIC_SITEMAPS + LESSON_SITEMAPS, args.match)
        if args.by_ordinal:
            pairs, seen_o = [], set()
            for u in allu:
                if "/topics/" not in u:
                    continue
                o, _ = ordinal_of(u)
                if o and o not in seen_o:
                    seen_o.add(o)
                    pairs.append((o, u))
            pairs.sort()
            items = [(o, u) for o, u in pairs]
            print("ক্রম:", [o for o, _ in pairs])
        else:
            items = [(i, u) for i, u in enumerate(allu, start=args.start)]
        if args.max:
            items = items[: args.max]

    print(f"নামানো হবে {len(items)}টি পাতা")
    chapters = []

    if args.group_by_num:
        # শিরোনাম-সংখ্যা ধরে ভাগ: (অধ্যায়, উপক্রম) অনুসারে সাজিয়ে এক ফাইলে জমা
        pairs = []
        for u in (u for _, u in items):
            t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
            nums = re.findall(r"([০-৯]{1,3})\s*[।.]\s*([০-৯]{1,3})", t)
            if nums:
                a, b = to_int(nums[0][0]), to_int(nums[0][1])
                pairs.append((a, b, u))
        pairs.sort()
        print(f"সংখ্যা-শিরোনাম পাওয়া গেল {len(pairs)}টিতে")
        bucket, curv, curch = {}, None, None
        for a, b, u in pairs:
            if a != curch:
                curch = a
                bucket.setdefault(a, [])
                curv = 0
            h = get(u)
            vs = parse_verses(page_text(h))
            if not vs:
                print(f"   ✗ {a}.{b}")
                continue
            for v in vs:
                curv += 1
                v = dict(v)
                v["n"] = curv
                bucket[a].append(v)
            print(f"   ✓ {a}.{b}: {len(vs)}")
            time.sleep(0.25)
        for a in sorted(bucket):
            if not bucket[a]:
                continue
            title = f"{args.title} — {a}" if args.title else f"অধ্যায় {a}"
            chapters.append(write_chapter(out_dir, a, title, bucket[a],
                                          BASE + "/topics/…"))
        if args.slug and chapters:
            idx = build_index(out_dir, args.slug, args.title or args.slug,
                              chapters, args.word)
            rep = [f"{args.slug}: বাংলা {idx['withBn']}/{idx['total']}"]
            rep += [f"  {c['id']}. {c['bn'][:44]}: {c['withBn']}/{c['count']}"
                    for c in idx["chapters"]]
            with open(os.path.join(args.out, f"_fetch_report_{args.slug}.txt"), "w",
                      encoding="utf-8") as f:
                f.write("\n".join(rep) + "\n")
            print("\n".join(rep))
        return

    for idx, u in items:
        print(f"[{idx}] {urllib.parse.unquote(u)[-60:]}")
        h = get(u)
        txt = page_text(h)
        vs = parse_verses(txt)
        if not vs:
            print("   ✗ মন্ত্র পাওয়া যায়নি")
            continue
        tail_t = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
        tail_t = re.sub(r"[-–_]+", " ", tail_t).strip()
        if args.title:
            title = f"{args.title} — {tail_t}"
        else:
            title = tail_t or f"অধ্যায় {idx}"
        chapters.append(write_chapter(out_dir, idx, title, vs, u))
        print(f"   ✓ {len(vs)} {args.word}")
        time.sleep(0.4)

    if args.slug and chapters:
        idx = build_index(out_dir, args.slug, args.title or args.slug, chapters, args.word)
        rep = [f"{args.slug}: বাংলা {idx['withBn']}/{idx['total']}"]
        rep += [f"  {c['id']}. {c['bn'][:44]}: {c['withBn']}/{c['count']}"
                for c in idx["chapters"]]
        with open(os.path.join(args.out, f"_fetch_report_{args.slug}.txt"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(rep) + "\n")
        print("\n".join(rep))


if __name__ == "__main__":
    main()
