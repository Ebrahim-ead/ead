#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vivekavani.com থেকে বাংলা বঙ্গানুবাদ ব্যাচে নামিয়ে ডেটা-ফাইলে বসায়।

উৎস: vivekavani.com (রামকৃষ্ণ মঠ ও মিশনের বঙ্গানুবাদ) — WP REST API।

ব্যবহার:
    python3 tools/fetch_bengali.py --target chandogya --out assets/grantho/data
    python3 tools/fetch_bengali.py --target katha

নীতি:
  • পোস্টের slug থেকে (ch, upach, mantra) বের করে ঠিক ওই মন্ত্রে বাংলা বসানো হয়।
  • জোড়া-পোস্ট (এক পোস্টে দুই মন্ত্র) হলে ব্যাখ্যার ভেতরের «॥ n ॥» চিহ্ন ধরে ভাগ করা হয়।
  • ৪০৪/অনুপস্থিত পোস্ট বাদ যায়; কোনটি বাদ গেল তা রিপোর্টে লেখা হয়।
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error, urllib.parse

UA = "ead-grantho-fetcher/1.0 (+https://github.com/Ebrahim-ead/ead)"
API = "https://vivekavani.com/wp-json/wp/v2/posts"
SRC_NAME = "বঙ্গানুবাদ (রামকৃষ্ণ মঠ ও মিশন)"

BN = "০১২৩৪৫৬৭৮৯"


BN_LABEL = {1: "প্রথম", 2: "দ্বিতীয়", 3: "তৃতীয়", 4: "চতুর্থ", 5: "পঞ্চম", 6: "ষষ্ঠ",
            7: "সপ্তম", 8: "অষ্টম", 9: "নবম", 10: "দশম", 11: "একাদশ", 12: "দ্বাদশ",
            13: "ত্রয়োদশ", 14: "চতুর্দশ", 15: "পঞ্চদশ", 16: "ষোড়শ", 17: "সপ্তদশ", 18: "অষ্টাদশ"}


def pstr(n, label="অধ্যায়"):
    return f"{BN_LABEL.get(n, str(n))} {label}"


LAYOUT = {
    "chandogya": {"bn": "ছান্দোগ্য উপনিষদ", "en": "Chandogya Upanishad",
                  "word": "মন্ত্র", "label": "অধ্যায়"},
    "katha": {"bn": "কঠ উপনিষদ", "en": "Katha Upanishad",
              "word": "মন্ত্র", "label": "বল্লী"},
}


def bn2int(s):
    return int("".join(str(BN.index(c)) for c in s))


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def clean_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>\s*<p[^>]*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&#8217;", "’")
          .replace("&#8216;", "‘").replace("&#8220;", "“").replace("&#8221;", "”")
          .replace("&#8212;", "—").replace("&#8211;", "–"))
    return s.strip()


def parse_post(html):
    """পোস্টের HTML → (সংস্কৃত-অংশ, [(মন্ত্র-নং?, বাংলা-ব্যাখ্যা)], টীকা)।"""
    txt = clean_html(html)
    if "Additional menu" in txt:
        txt = txt.split("Additional menu", 1)[1]
    # শেয়ার-ব্লক বাদ
    for cut in ("Share this on:", "Copy link", "Thanks for sharing!"):
        i = txt.find(cut)
        if i > 0:
            txt = txt[:i]

    m = re.search(r"ব্যাখ্যা\s*[—\-–]\s*", txt)
    if not m:
        return "", [], ""
    # সংস্কৃত শ্লোক = ব্যাখ্যার আগের অংশ (সম্বন্ধ— বাদ দিয়ে)
    sk = txt[:m.start()].strip()
    k = sk.find("সম্বন্ধ—")
    if k >= 0:
        nl = sk.find("\n", k)
        sk = (sk[nl + 1:] if nl > 0 else "").strip()
    # শিরোনাম/নেভিগেশন-জাত প্রথম লাইন বাদ
    lines = [l.strip() for l in sk.split("\n") if l.strip()]
    if lines and len(lines[0]) < 25 and not re.search(r"[।॥]", lines[0]):
        lines = lines[1:]
    sk = "\n".join(lines).strip()
    body = txt[m.end():]

    # সম্বন্ধ— (পরবর্তী মন্ত্রের সূচনা) বাদ
    j = body.find("সম্বন্ধ—")
    if j > 0:
        body = body[:j]

    # টীকা: «(১)…» বাক্য-মধ্যে থাকলে আলাদা করি
    notes = re.findall(r"\(\s*[০-৯]+\s*\)[^()]{40,}", body)
    for n in notes:
        body = body.replace(n, "")
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{2,}", "\n\n", body).strip()

    # এক পোস্টে একাধিক মন্ত্র? «॥ n ॥» চিহ্ন ধরে ভাগ
    parts = []
    marks = list(re.finditer(r"॥\s*([০-৯]+)\s*॥", body))
    if len(marks) >= 2:
        prev = 0
        for k, mm in enumerate(marks):
            seg = body[prev:mm.end()].strip()
            prev = mm.end()
            if len(seg) > 80:
                parts.append((bn2int(mm.group(1)), seg))
    if not parts:
        parts = [(None, body)]
    return sk, parts, " ".join(n.strip() for n in notes)


def chapter_files(out, slug):
    """গ্রন্থের ch{n}.json ফাইলগুলির পাঠ ও তাদের মন্ত্র-তালিকা।"""
    d = os.path.join(out, slug)
    if not os.path.isdir(d):
        return {}
    res = {}
    for f in sorted(os.listdir(d)):
        m = re.match(r"ch(\d+)\.json$", f)
        if not m:
            continue
        try:
            obj = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        res[int(m.group(1))] = (os.path.join(d, f), obj)
    return res


# --- গ্রন্থ-বিন্যাস ----------------------------------------------------------
# slug থেকে (ch, upach, mantra) বের করার রেগেক্স
PATTERNS = {
    "chandogya": re.compile(r"^chu(\d+)c(\d+)v(\d+)b$"),
    "katha":     re.compile(r"^kau(\d+)c(\d+)v(\d+)b$"),
    "shvetashvatara": re.compile(r"^svu(\d+)v(\d+)b$"),
    "kena":      re.compile(r"^keu(\d+)b$"),
}


def target_spec(name):
    """(গ্রন্থ-slug, সার্চ-কোয়েরি, slug-regex, upach-নির্দেশিকা)"""
    if name == "chandogya":
        return ("chandogya", "Chandogya Upanishad Bengali",
                re.compile(r"^chu(\d+)c(\d+)v(\d+)b$"), True)
    if name == "katha":
        return ("katha", "Katha Upanishad Bengali",
                re.compile(r"^kau(\d+)c(\d+)v(\d+)b$"), True)
    if name == "shvetashvatara":
        return ("shvetashvatara", "Svetasvatara Upanishad Bengali",
                re.compile(r"^svu(\d+)v(\d+)b$"), False)
    raise SystemExit("অজানা টার্গেট: " + name)


def collect_slugs(query, rx, pages=8):
    found = {}
    for page in range(1, pages + 1):
        url = f"{API}?search={urllib.parse.quote(query)}&per_page=100&page={page}&_fields=id,slug"
        data = get(url)
        if not data:
            break
        for p in data:
            if rx.match(p["slug"]):
                found[p["slug"]] = p["id"]
        if len(data) < 100:
            break
        time.sleep(0.4)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="chandogya")
    ap.add_argument("--out", default="assets/grantho/data")
    ap.add_argument("--limit", type=int, default=0, help="পরীক্ষার জন্য পোস্ট-সংখ্যা সীমা")
    ap.add_argument("--dump", type=int, default=0, help="প্রথম N পোস্টের পরিষ্কার লেখা _debug/ ফোল্ডারে রাখে")
    args = ap.parse_args()

    slugname, query, rx, has_upach = target_spec(args.target)

    if args.dump:
        dbg = os.path.join(args.out, "_debug")
        os.makedirs(dbg, exist_ok=True)
        slugs = collect_slugs(query, rx)
        print(f"ডাম্প: {len(slugs)} পোস্ট-তালিকা")
        for i, (sl, pid) in enumerate(sorted(slugs.items())[: args.dump]):
            data = get(f"{API}/{pid}?_fields=slug,content")
            raw = (data or {}).get("content", {}).get("rendered", "")
            txt = clean_html(raw)
            open(os.path.join(dbg, f"{sl}.txt"), "w", encoding="utf-8").write(txt[:6000])
            open(os.path.join(dbg, f"{sl}.html"), "w", encoding="utf-8").write(raw[:20000])
        open(os.path.join(dbg, "_list.txt"), "w", encoding="utf-8").write("\n".join(sorted(slugs)))
        return

    files = chapter_files(args.out, slugname)
    build = not files
    if build:
        print("কাঠামো নেই — পোস্ট থেকেই সংস্কৃত পাঠ + কাঠামো গড়া হবে")
        files = {}

    stats = {"পোস্ট": 0, "সংরক্ষিত": 0, "সংস্কৃত": 0, "৪০৪": 0, "অচেনা": 0, "ভাগ-লাগা": 0}

    slugs = collect_slugs(query, rx)
    print(f"পোস্ট-তালিকা: {len(slugs)}")

    # slug → key
    jobs = []
    for s in sorted(slugs):
        m = rx.match(s)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        ch, upach, mn = g[0], (g[1] if has_upach else 1), (g[2] if has_upach else g[1])
        jobs.append((s, slugs[s], ch, mn))

    touched = set()
    if build:
        # প্রথমে সব পোস্ট ঘুরে (ch, mantra) → (সংস্কৃত, বাংলা) জমা করি
        collected = {}
        for s, pid, ch, mn in jobs[: args.limit or None]:
            data = get(f"{API}/{pid}?_fields=slug,content")
            if not data:
                stats["৪০৪"] += 1
                continue
            stats["পোস্ট"] += 1
            sk, parts, notes = parse_post(data.get("content", {}).get("rendered", ""))
            if len(parts) == 1:
                collected.setdefault((ch, mn), {"sk": sk, "bn": parts[0][1], "note": notes})
            else:
                stats["ভাগ-লাগা"] += 1
                for k, (num, seg) in enumerate(parts):
                    n = num if num else mn + k
                    collected.setdefault((ch, n), {"sk": "", "bn": seg, "note": notes})
                if sk:
                    collected.setdefault((ch, mn), {"sk": sk, "bn": "", "note": ""})
            time.sleep(0.25)

        if collected:
            d = os.path.join(args.out, slugname)
            os.makedirs(d, exist_ok=True)
            chapters = sorted({c for c, _ in collected})
            names = LAYOUT.get(slugname, {}).get("names", {})
            idx = {"slug": slugname, "bn": LAYOUT.get(slugname, {}).get("bn", slugname.title()),
                   "en": LAYOUT.get(slugname, {}).get("en", slugname.title()),
                   "total": 0, "withBn": 0, "chapters": [],
                   "note": "মূল সংস্কৃত পাঠ ও বাংলা বঙ্গানুবাদ",
                   "bnSrc": SRC_NAME, "verseWord": LAYOUT.get(slugname, {}).get("word", "মন্ত্র")}
            T = W = 0
            for ch in chapters:
                nums = sorted(n for c, n in collected if c == ch)
                verses = []
                for n in nums:
                    rec = collected[(ch, n)]
                    v = {"n": n, "sk": rec["sk"], "bn": rec["bn"], "spk": ""}
                    if rec["bn"]:
                        v["bnSrc"] = SRC_NAME
                        W += 1
                    if rec.get("note"):
                        v["bnNote"] = rec["note"]
                    if rec["sk"]:
                        stats["সংস্কৃত"] += 1
                    verses.append(v)
                obj = {"id": ch, "bn": names.get(ch, pstr(ch, LAYOUT.get(slugname, {}).get("label", "অধ্যায়"))),
                       "count": len(verses), "from": 1, "to": len(verses), "verses": verses}
                json.dump(obj, open(os.path.join(d, f"ch{ch}.json"), "w", encoding="utf-8"),
                          ensure_ascii=False, separators=(",", ":"))
                idx["chapters"].append({"id": ch, "bn": obj["bn"], "count": obj["count"],
                                        "from": 1, "to": obj["count"], "withBn": sum(1 for v in verses if v["bn"])})
                T += obj["count"]
            idx["total"], idx["withBn"] = T, W
            json.dump(idx, open(os.path.join(d, "index.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            rep = (f"{slugname}: বাংলা {W}/{T}\n"
                   + "\n".join(f"  অধ্যায় {c['id']}: {c['withBn']}/{c['count']}" for c in idx["chapters"])
                   + f"\nপরিসংখ্যান: {stats}\n")
            open(os.path.join(args.out, "_fetch_report.txt"), "w", encoding="utf-8").write(rep)
            print(rep)
        return

    for s, pid, ch, mn in jobs[: args.limit or None]:
        data = get(f"{API}/{pid}?_fields=slug,content")
        if not data:
            stats["৪০৪"] += 1
            print(f"  ✗ {s}")
            continue
        stats["পোস্ট"] += 1
        html = data.get("content", {}).get("rendered", "")
        parts, notes = parse_post(html)
        if not isinstance(parts, list):
            parts = [(None, parts)]

        if ch not in files:
            stats["অচেনা"] += 1
            continue
        path, obj = files[ch]
        byn = {v["n"]: v for v in obj["verses"]}

        if len(parts) == 1:
            target = byn.get(mn)
            if target is not None and len(parts[0][1]) > 40:
                target["bn"] = parts[0][1]
                target["bnSrc"] = SRC_NAME
                if notes:
                    target["bnNote"] = notes
                stats["সংরক্ষিত"] += 1
                touched.add(path)
            else:
                stats["অচেনা"] += 1
        else:
            stats["ভাগ-লাগা"] += 1
            for num, seg in parts:
                n = num if num in byn else mn
                if n in byn and len(seg) > 40:
                    byn[n]["bn"] = seg
                    byn[n]["bnSrc"] = SRC_NAME
                    stats["সংরক্ষিত"] += 1
                    touched.add(path)
        time.sleep(0.25)

    # লেখা + index হালনাগাদ
    for path in touched:
        obj = json.load(open(path, encoding="utf-8"))
        # পুনরায় পড়ে লিখি (মেমরি-অবজেক্ট ইতিমধ্যে বদলানো)
        for ch, (p, o) in files.items():
            if p == path:
                obj = o
        json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    idxp = os.path.join(args.out, slugname, "index.json")
    if os.path.exists(idxp):
        idx = json.load(open(idxp, encoding="utf-8"))
        T = W = 0
        for c in idx.get("chapters", []):
            for ch, (p, o) in files.items():
                if ch == c["id"]:
                    c["withBn"] = sum(1 for v in o["verses"] if v.get("bn"))
                    T += o["count"]
                    W += c["withBn"]
        idx["total"], idx["withBn"] = T, W
        idx["bnSrc"] = SRC_NAME
        json.dump(idx, open(idxp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    rep = (f"{slugname}: বাংলা {W}/{T}\n"
           + "\n".join(f"  অধ্যায় {c['id']}: {c.get('withBn',0)}/{c['count']}"
                       for c in idx.get("chapters", []))
           + f"\nপরিসংখ্যান: {stats}\n")
    open(os.path.join(args.out, "_fetch_report.txt"), "w", encoding="utf-8").write(rep)
    print(rep)


if __name__ == "__main__":
    main()
