#!/usr/bin/env python3
"""সাইট-সার্চের সূচি বানায় — assets/search-index.js

কোনো HTML চেঞ্জ করলেই এই স্ক্রিপ্ট চালাতে হবে:

    python3 tools/build_search_index.py

সূচিতে যা ঢোকে:
  * প্রতিটি HTML পাতার মূল-বিষয়বস্তু (main) — path, শিরোনাম, সারাংশ
  * কুরআনের ১১৪টি সূরা — নাম, অর্থ, আয়াত-সংখ্যা
  * কুরআনের ৬,২৩৬টি আয়াত — ভেতরের বাংলা লেখাতেও সার্চ হয়
  * হাদিসের ৭টি কিতাব ও ৩৬১টি অধ্যায় — কর্তৃপক্ষ, হাদিস-সংখ্যা
  * ধর্মীয় গ্রন্থের অধ্যায় — গীতা, বাইবেল, বেদ ইত্যাদি

ফলাফল: একটি JS ফাইল (window.SITE_SEARCH = …) — fetch ছাড়াই লোড হয়,
তাই file:// থেকেও সার্চ কাজ করে।
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "search-index.js"

# ── HTML পাতা → মূল-বিষয়বস্তু ──────────────────────────────────
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style|nav|header|footer)\b.*?</\1>", re.S | re.I)
MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="([^"]*)"', re.I)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)

# সাইট-নেভিগেশনে যেসব পাতা আছে — সেগুলোর নাম বাংলায়
PAGE_NAMES = {
    "index.html": "হোম",
    "topics.html": "বিষয়সমূহ",
    "atheism.html": "প্রবন্ধ",
    "books.html": "বই লাইব্রেরি",
    "grantho.html": "ধর্মীয় গ্রন্থ",
    "quran.html": "কুরআন",
    "hadith.html": "হাদিস",
    "ask.html": "মতবিনিময়",
    "about.html": "পরিচিতি",
    "contact.html": "যোগাযোগ",
}

SKIP_PAGES = {"404.html", "atheism-2.html"}  # রিডাইরেক্ট/noindex


def clean_html(fragment: str) -> str:
    fragment = SCRIPT_RE.sub(" ", fragment)
    fragment = TAG_RE.sub(" ", fragment)
    fragment = (
        fragment.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return re.sub(r"\s+", " ", fragment).strip()


# বাংলায় একই শব্দের একাধিক প্রচলিত বানান — সার্চে সব মিলতে হবে।
# যেমন «ইয়াসীন» লিখলে «ইয়াসিন»-ও ধরা পড়বে।
_FOLD = str.maketrans({
    "\u09c0": "\u09bf",   # ী → ি  (দীর্ঘ ই → হ্রস্ব ই)
    "\u09c2": "\u09c1",   # ূ → ু  (দীর্ঘ উ → হ্রস্ব উ)
    "\u09bc": "",          # ়  নুকতা বাদ (ড়/র মিল)
    "\u09df": "\u09af",   # য় → য
    "\u09ce": "\u09a4",   # ৎ → ত
    "\u200c": "",          # ZWNJ
    "\u200d": "",          # ZWJ
})


def norm(text: str) -> str:
    """সার্চের জন্য লেখা স্বাভাবিক করি — বানান-ভিন্নতাও মিলবে।"""
    t = unicodedata.normalize("NFC", text).lower()
    return t.translate(_FOLD)


def build_pages() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(ROOT.glob("*.html")):
        if path.name in SKIP_PAGES:
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        title = clean_html(TITLE_RE.search(raw).group(1)) if TITLE_RE.search(raw) else path.stem
        title = title.split("|")[0].strip()
        m = MAIN_RE.search(raw)
        body = clean_html(m.group(1) if m else raw)
        desc = ""
        dm = DESC_RE.search(raw)
        if dm:
            desc = clean_html(dm.group(1))
        # কার্ড-শিরোনামগুলো আলাদা করে রাখি — সার্চে এগুলো ভালো ফল দেয়
        heads = [clean_html(h) for h in H1_RE.findall(m.group(1) if m else raw)]
        rows.append(
            {
                "t": "page",
                "u": path.name,
                "n": title or PAGE_NAMES.get(path.name, path.stem),
                "d": (desc or body)[:150],
                "k": norm(" ".join([title, desc, body[:2600]])),
            }
        )
    return rows


def build_quran() -> list[dict]:
    idx = ROOT / "assets" / "quran" / "data" / "index.json"
    if not idx.exists():
        return []
    data = json.loads(idx.read_text(encoding="utf-8"))
    out = []
    for s in data.get("suras", []):
        n = s.get("n")
        name = s.get("bn") or s.get("translit") or f"সূরা {n}"
        out.append(
            {
                "t": "quran",
                "u": f"quran.html#{n}",
                "n": f"সূরা {name}",
                "d": f"{s.get('count', '?')} আয়াত · {s.get('translit', '')}".strip(" ·"),
                "k": norm(f"সূরা {name} {s.get('translit','')} {s.get('name','')} কুরআন quran sura {n}"),
            }
        )
    return out


AYAH_OUT = ROOT / "assets" / "search-ayahs.js"


def build_ayah_file() -> int:
    """কুরআনের সব আয়াত — আলাদা ফাইলে, শুধু সার্চ করলে লোড হয়।

    ৬,২৩৬ আয়াত · ~২.৫ MB (বাংলা লেখা ৩ বাইট/অক্ষর) — তাই মূল সূচির
    সঙ্গে রাখা যায় না। এন্ট্রি সংক্ষিপ্ত অ্যারে: [সূরা, আয়াত, লেখা]।
    """
    idx_path = ROOT / "assets" / "quran" / "data" / "index.json"
    if not idx_path.exists():
        return 0
    rows: list[list] = []
    for f in sorted((ROOT / "assets" / "quran" / "data" / "suras").glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        sn = data.get("n") or int(f.stem)
        for v in data.get("verses", []):
            an = v.get("a")
            bn = (v.get("bn") or "").strip()
            if an is None or not bn:
                continue
            text = re.sub(r"^\s*[০-৯0-9]+\s*[.।]\s*", "", bn)      # শুরুর নম্বর
            text = re.sub(r"\s*\[\s*[০-৯0-9]+\s*\]", "", text)     # টীকা-চিহ্ন [১]
            text = re.sub(r"\s+", " ", text).strip()
            rows.append([sn, an, text])
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    AYAH_OUT.write_text(
        "/* স্বয়ংক্রিয়ভাবে তৈরি — হাতে সম্পাদনা করবেন না।\n"
        "   সার্চ করলে তবেই লোড হয়। নতুন করে বানাতে: python3 tools/build_search_index.py */\n"
        f"window.SITE_AYAHS={payload};\n",
        encoding="utf-8",
    )
    return len(rows)


def build_hadith() -> list[dict]:
    idx = ROOT / "assets" / "hadith" / "data" / "index.json"
    if not idx.exists():
        return []
    data = json.loads(idx.read_text(encoding="utf-8"))
    out = []
    for b in data.get("books", []):
        slug = b.get("slug")
        bname = b.get("bn") or slug
        out.append(
            {
                "t": "hadith",
                "u": f"hadith.html#{slug}:1",
                "n": bname,
                "d": f"{b.get('count', '?')}টি হাদিস · {len(b.get('chapters') or [])} অধ্যায়",
                "k": norm(f"{bname} {b.get('ar','')} {b.get('short','')} হাদিস hadith {slug}"),
            }
        )
    return out


GRANTH_LABELS = {
    "gita": "ভগবদ্গীতা",
    "bible": "বাইবেল",
    "rigveda": "ঋগ্বেদ",
    "veda": "বেদ",
    "yajurveda-shukla": "শুক্ল যজুর্বেদ",
}

# কোন গ্রন্থ-পাতা কোন ফোল্ডারে — grantho.js `data-granth` পড়ে `#ch<N>` hash-এ
GRANTH_PAGE = {
    "gita": "grantho/hindu/gita.html",
    "rigveda": "grantho/hindu/rigveda.html",
    "veda": "grantho/hindu/veda.html",
    "yajurveda-shukla": "grantho/hindu/yajurveda-shukla.html",
    "bible": "grantho/christian/bible.html",
}


def build_grantho() -> list[dict]:
    base = ROOT / "assets" / "grantho" / "data"
    if not base.is_dir():
        return []
    out = []
    for granth_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        gslug = granth_dir.name
        glabel = GRANTH_LABELS.get(gslug, gslug)
        for f in sorted(granth_dir.glob("ch*.json"), key=lambda x: int(re.sub(r"\D", "", x.stem) or 0)):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            # ফাঁকা ফাইল বাদ (বাইবেলে ৫৪টি ডুপ্লিকেট শেল আছে — count=0, কোনো শ্লোক নেই)
            if not d.get("verses") or d.get("count", 0) == 0:
                continue
            cid = d.get("id") or f.stem.replace("ch", "")
            cname = d.get("bn") or f"অধ্যায় {cid}"
            testament = d.get("testament") or ""
            # খোঁজার জন্য প্রথম কয়েক শ্লোকের লেখাও কী-তে রাখি (ভারসাম্যরক্ষা)
            sample = " ".join((v.get("bn") or "")[:160] for v in (d.get("verses") or [])[:2])
            unit = d.get("groupWord") or "অধ্যায়"
            out.append(
                {
                    "t": "grantho",
                    "u": f"{GRANTH_PAGE.get(gslug, 'grantho.html')}#ch{cid}",
                    "n": f"{glabel} — {cname}",
                    "d": f"{d.get('count', '?')}টি শ্লোক · {unit} {cid}"
                         + (f" · {testament}" if testament else ""),
                    "k": norm(f"{glabel} {cname} {gslug} {cid} {testament} {sample}"),
                }
            )
    return out


def main() -> int:
    rows = build_pages() + build_quran() + build_hadith() + build_grantho()
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(
        "/* স্বয়ংক্রিয়ভাবে তৈরি — হাতে সম্পাদনা করবেন না।\n"
        "   নতুন করে বানাতে: python3 tools/build_search_index.py */\n"
        f"window.SITE_SEARCH={payload};\n",
        encoding="utf-8",
    )
    kb = OUT.stat().st_size / 1024
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["t"]] = counts.get(r["t"], 0) + 1
    print(f"✓ {OUT.relative_to(ROOT)} — {len(rows)} এন্ট্রি, {kb:.0f} KB")
    for k, v in sorted(counts.items()):
        print(f"   {k:12} {v}")

    n_ayah = build_ayah_file()
    if n_ayah:
        akb = AYAH_OUT.stat().st_size / 1024
        print(f"✓ {AYAH_OUT.relative_to(ROOT)} — {n_ayah} আয়াত, {akb:.0f} KB (শুধু সার্চে লোড হয়)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
