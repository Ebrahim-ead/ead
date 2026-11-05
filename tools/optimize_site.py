#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""সাইট হালকা ও স্মুথ করা — একক, বারবার চালানো-নিরাপদ (idempotent) স্ক্রিপ্ট।

ধাপ:
  css     প্রতিটি পাতায় inline ঢোকানো ২৫০ KB শেয়ার্ড CSS বের করে assets/site.css-এ
          একবার রাখা হয় (৩১ পাতায় পুনরাবৃত্তি বন্ধ, দ্বিতীয় পাতা থেকে ক্যাশ)।
  img     <img> ট্যাগে base64 গাঁথা ছবি → assets/img/<sha1>.<ext> ফাইল, সাথে
          width/height (লেআউট লাফ বন্ধ) ও lazy/async।
  bg      CSS-এর url(data:…webp) ব্যাকগ্রাউন্ড ছবি → assets/img/bg-<sha1>.webp ফাইল।
  mobile  ফোনে ভারী স্তর (blur/orb/grid/sparks/backdrop-filter) বন্ধ, ১৬px input,
          ৪৪px টাচ-টার্গেট, content-visibility দিয়ে লম্বা পাতা মসৃণ।
  fonts   Hind Siliguri `display=swap`।

চালানো: python3 tools/optimize_site.py [--step css] [--step img] … [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DATA_URI = re.compile(r"data:image/([a-z+]+);base64,([A-Za-z0-9+/=]+)")
STYLE_BLOCK = re.compile(r"<style(?:\s[^>]*)?>([\s\S]*?)</style>")
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
SITE_CSS_MARK = "/* --- optimized site rules"

MOBILE_CSS = r"""
/* --- optimized site rules: mobile & touch --------------------------------
   ফোনে সবচেয়ে ব্যয়বহুল স্তরগুলো বন্ধ/হালকা করা হয়, চেহারা একই থাকে। */

@media (max-width:820px){
  .orb,.grid-tex,.motion-sparks{display:none!important}
  .aura{animation:none!important}
  header.top,.nav,.badge,.card,.qcard{backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
  header.top{background:rgba(4,12,16,.985)!important}
  html[data-theme="light"] header.top{background:rgba(247,250,252,.99)!important}
  input,select,textarea{font-size:16px!important}   /* iOS ফোকাসে zoom বন্ধ */
  ::-webkit-scrollbar{width:8px;height:8px}
}

@media (hover:none) and (pointer:coarse){
  .h-btn,.theme-toggle,.burger,.h-drawer-btn,.h-icon{min-height:44px}
  .h-btn{padding:10px 16px}
  .nav a{min-height:44px;display:flex;align-items:center}
  .card:hover,.qcard:hover,.hero-photo:hover{transform:none!important}
}

@media (max-width:760px){
  .logo-copy small,.badge,.h-badge,.h-note{font-size:13px}
}

/* লম্বা শব্দ/টেবিল ফোনে স্ক্রল ভাঙে না */
.article-body,.h-v-text,.q-v{overflow-wrap:anywhere}
.article-body img,.article-body table{max-width:100%;height:auto}
.article-body table{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}

/* দৃশ্যের বাইরের কার্ড আঁকা হয় না → খুব লম্বা পাতায় স্ক্রল মসৃণ */
.article-body>section{content-visibility:auto;contain-intrinsic-size:auto 320px}

/* ছবি সবসময় অনুপাত ধরে ছোট হবে */
.article-body img,.h-item img{height:auto}
"""


def pages() -> list[pathlib.Path]:
    out = sorted(ROOT.glob("*.html")) + sorted((ROOT / "grantho").rglob("*.html"))
    return out


def rel(p: pathlib.Path) -> str:
    return "../" * (len(p.relative_to(ROOT).parts) - 1)


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: pathlib.Path, s: str, dry: bool) -> None:
    if not dry:
        p.write_text(s, encoding="utf-8")


def _save(raw: bytes, ext: str, stem: str, dry: bool) -> pathlib.Path:
    dest = ASSETS / "img" / f"{stem}.{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() and not dry:
        dest.write_bytes(raw)
    return dest


def _ext(fmt: str) -> str:
    return {"jpeg": "jpg", "jpg": "jpg", "webp": "webp", "png": "png",
            "svg+xml": "svg", "gif": "gif"}.get(fmt, fmt)


# --------------------------------------------------------------------------- #
# 1. shared CSS out of every page
# --------------------------------------------------------------------------- #
def step_css(dry: bool) -> None:
    """প্রতিটি পাতার <style> ব্লক → এক ক্যাশড assets/site.css, বড় ব্লকটি বাদ।

    * সব ব্লকের নিয়ম একত্রে রাখা হয় (কোনো নিয়ম হারায় না)।
    * ভিত্তি-ক্রম আসে সবচেয়ে বেশি পাতায় থাকা সংস্করণ থেকে; বাকিরা শুধু
      নতুন নিয়ম যোগ করে — তাই cascade অটুট থাকে।
    * পাতার ছোট ব্লকগুলো (মোবাইল মেনু, পেজার, পোস্ট-স্টাইল) থেকে যায়,
      ফলে সেই নিয়মগুলো শীটের পরেই বসে আগের মতোই জেতে।
    * যে পাতায় ইতিমধ্যে site.css লিংক আছে, সেটি আর ছোঁয়া হয় না।
    """
    html: dict[pathlib.Path, str] = {}
    targets: dict[pathlib.Path, re.Match] = {}
    for p in pages():
        s = read(p)
        if 'assets/site.css"' in s:
            continue                     # আগেই রূপান্তরিত
        blocks = list(STYLE_BLOCK.finditer(s))
        if not blocks:
            continue
        html[p], targets[p] = s, max(blocks, key=lambda m: len(m.group(1)))

    if not targets:
        print("  সব পাতা ইতিমধ্যে site.css ব্যবহার করছে (skipped)")
        return

    # ভিত্তি-পাতা: যে পাতার (সব ব্লকের) নিয়ম-তালিকা সবচেয়ে সাধারণ
    all_rules: dict[pathlib.Path, list[str]] = {}
    for p in targets:
        rs: list[str] = []
        for m in STYLE_BLOCK.finditer(html[p]):
            rs.extend(_split_rules(m.group(1)))
        all_rules[p] = rs
    sig = {p: hashlib.sha1("\n".join(_rule_key(r) for r in rs).encode()).hexdigest()
           for p, rs in all_rules.items()}
    common = max(set(sig.values()), key=list(sig.values()).count)
    base_page = next(p for p in targets if sig[p] == common)

    seen: set[str] = set()
    ordered: list[str] = []
    for r in all_rules[base_page] + [r for p in targets for r in all_rules[p]]:
        k = _rule_key(r)
        if k in seen:
            continue
        seen.add(k)
        ordered.append(r)

    css_parts = [r for r in ordered if not r.lstrip().startswith("@") or True]
    sheet = "\n".join(css_parts)
    before = sum(len(m.group(1)) for m in targets.values())
    write(ASSETS / "site.css", "/* shared site sheet — tools/optimize_site.py */\n" + sheet + "\n" + MOBILE_CSS, dry)
    print(f"  {len(targets)} pages × inline styles ({before:,} bytes) → assets/site.css "
          f"({len(sheet) + len(MOBILE_CSS):,} bytes, {len(ordered)} rules)")

    for p, m in targets.items():
        s = html[p]
        link = f'<link rel="stylesheet" href="{rel(p)}assets/site.css">'
        s2 = s[: m.start()] + link + s[m.end():]
        write(p, s2, dry)
    print("  shared link injected; page-specific blocks kept in place")


# --------------------------------------------------------------------------- #
# 2. inline <img> base64 → files
# --------------------------------------------------------------------------- #
def _attr(tag: str, name: str):
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def _size(raw: bytes):
    try:
        from PIL import Image  # type: ignore
        with Image.open(io.BytesIO(raw)) as im:
            return im.size
    except Exception:
        return None


def step_img(dry: bool) -> None:
    files: dict[str, tuple[str, int, int]] = {}   # sha1 → (filename, w, h)
    n = 0
    bytes_in = bytes_out = 0
    for p in pages():
        s = read(p)
        pre = rel(p)

        def sub(m: re.Match) -> str:
            nonlocal n, bytes_in, bytes_out
            tag = m.group(0)
            src = (_attr(tag, "src") or "").strip()
            d = DATA_URI.fullmatch(src)
            if not d:
                return tag
            raw = base64.b64decode(d.group(2))
            h = hashlib.sha1(raw).hexdigest()[:10]
            if h not in files:
                dims = _size(raw) or (0, 0)
                files[h] = (f"{h}.{_ext(d.group(1))}", dims[0], dims[1])
                _save(raw, _ext(d.group(1)), h, dry)
            fname, w, hh = files[h]
            url = f"{pre}assets/img/{fname}"
            out = tag.replace(src, url, 1)
            cls = _attr(out, "class") or ""
            small = "avatar" in cls or "logo" in cls
            if w and hh and not small and "width=" not in out:
                out = out[:-1] + f' width="{w}" height="{hh}" style="height:auto"' + ">"
            if "decoding=" not in out:
                out = out[:-1] + ' decoding="async"' + ">"
            if "loading=" not in out and not small:
                out = out[:-1] + ' loading="lazy"' + ">"
            n += 1
            bytes_in += len(src)
            bytes_out += len(url)
            return out

        s2 = IMG_TAG.sub(sub, s)
        if s2 != s:
            write(p, s2, dry)
    print(f"  {n} inline <img> → {len(files)} files: HTML {bytes_in/1e6:.2f} MB → {bytes_out/1e3:.0f} B")


# --------------------------------------------------------------------------- #
# 3. CSS background images → files
# --------------------------------------------------------------------------- #
def _dims_from_webp(raw: bytes):
    return None


URL_URI = re.compile(r'url\(\s*["\']?(data:image/([a-z+]+);base64,([A-Za-z0-9+/=]+))["\']?\s*\)')


def step_bg(dry: bool) -> None:
    made: dict[str, str] = {}          # sha1 → filename
    n = 0
    # CSS-এর url(data:…) এখন assets/site.css-এ থাকে; সেখান থেকে url আপেক্ষিক (img/…)
    targets = [(p, rel(p) + "assets/img/") for p in pages()]
    if (ASSETS / "site.css").exists():
        targets.append((ASSETS / "site.css", "img/"))
    for p, pre in targets:
        s = read(p)

        def sub(m: re.Match) -> str:
            nonlocal n
            fmt, b64 = m.group(2), m.group(3)
            raw = base64.b64decode(b64)
            h = hashlib.sha1(raw).hexdigest()[:10]
            if h not in made:
                name = f"bg-{h}.{_ext(fmt)}"
                _save(raw, _ext(fmt), "bg-" + h, dry)
                made[h] = name
            n += 1
            return f'url("{pre}{made[h]}")' 

        s2 = URL_URI.sub(sub, s)
        if s2 != s:
            write(p, s2, dry)
    print(f"  {n} CSS data-URI backgrounds → {len(made)} files")


# --------------------------------------------------------------------------- #
# 4. mobile rules
# --------------------------------------------------------------------------- #
def step_mobile(dry: bool) -> None:
    sheet = ASSETS / "site.css"
    if not sheet.exists():
        print("  ! assets/site.css নেই — আগে --step css চালান")
        return
    css = read(sheet)
    if SITE_CSS_MARK in css:
        css = css[: css.index(SITE_CSS_MARK)].rstrip() + "\n"
    else:
        css = css.rstrip() + "\n"
    write(sheet, css + MOBILE_CSS, dry)
    print(f"  mobile rules written into assets/site.css ({len(MOBILE_CSS)} bytes)")


# --------------------------------------------------------------------------- #
# 5. font-display
# --------------------------------------------------------------------------- #
def step_fonts(dry: bool) -> None:
    n = 0
    for p in pages():
        s = read(p)
        s2 = s if "Hind+Siliguri:wght@" in s and "display=swap" in s and "&display=swap0" not in s else re.sub(r"family=Hind\+Siliguri:wght@([0-9;]+?)(?:0)?(?:&display=swap)?(?=[&\"'])",
                    lambda m: "family=Hind+Siliguri:wght@" + m.group(1) + "&display=swap", s)
        if s2 != s:
            write(p, s2, dry)
            n += 1
    print(f"  display=swap added on {n} pages")


def _rule_key(css: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"data:[^)\"']+", "DATA", css)).strip()


def _split_rules(css: str) -> list[str]:
    """Top-level rules; braces are balanced, @media keeps its nested block."""
    out, depth, cur = [], 0, ""
    for ch in css:
        cur += ch
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                if cur.strip():
                    out.append(cur.strip())
                cur = ""
    return out


def step_imgsize(dry: bool) -> None:
    try:
        from PIL import Image
    except Exception:
        print("  ! Pillow নেই — pip install pillow")
        return
    d = ASSETS / "img"
    saved = 0
    for p in sorted(d.glob("*")):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        before = p.stat().st_size
        try:
            with Image.open(p) as im:
                im.load()
                w, h = im.size
                fmt = im.format
                icc = im.info.get("icc_profile")
                if p.name.startswith("bg-"):
                    # ব্যাকগ্রাউন্ড: blur হয়ে যায়, ছোট রাখাই যথেষ্ট
                    target = min(w, 1400)
                else:
                    target = min(w, MAX_W)
                if target < w:
                    im = im.resize((target, round(h * target / w)), Image.LANCZOS)
                out = io.BytesIO()
                if p.suffix.lower() == ".png":
                    im.save(out, "PNG", optimize=True)
                elif p.suffix.lower() == ".webp" or p.name.startswith("bg-"):
                    im.convert("RGB").save(out, "WEBP", quality=WEBP_Q, method=6, icc_profile=icc)
                else:
                    im.convert("RGB").save(out, "JPEG", quality=JPEG_Q, optimize=True,
                                           progressive=True, icc_profile=icc)
                data = out.getvalue()
                if len(data) < before * 0.92:   # স্পষ্ট লাভ থাকলেই বদল
                    if not dry:
                        p.write_bytes(data)
                    saved += before - len(data)
        except Exception as e:
            print(f"  ! {p.name}: {e}")
    print(f"  image budget: {saved / 1024:.0f} KB কমেছে")


def step_imgattrs(dry: bool) -> None:
    """ফাইল হওয়া ছবির width/height বাস্তব ফাইলের মাপে ঠিক করা (অনুপাত অটুট)।"""
    try:
        from PIL import Image
    except Exception:
        print("  ! Pillow নেই")
        return
    fixed = 0
    for page in pages():
        s = read(page)
        pre = rel(page)

        def sub(m: re.Match) -> str:
            nonlocal fixed
            tag = m.group(0)
            src = _attr(tag, "src") or ""
            if not src.startswith(pre + "assets/img/"):
                return tag
            path = ROOT / src
            if not path.exists():
                return tag
            try:
                with Image.open(path) as im:
                    w, h = im.size
            except Exception:
                return tag
            if _attr(tag, "width") == str(w) and _attr(tag, "height") == str(h):
                return tag
            out = re.sub(r'\bwidth="\d+"', f'width="{w}"', tag)
            out = re.sub(r'\bheight="\d+"', f'height="{h}"', out)
            fixed += 1
            return out

        s2 = IMG_TAG.sub(sub, s)
        if s2 != s:
            write(page, s2, dry)
    print(f"  {fixed}টি <img>-এ ফাইলের আসল মাপ বসানো হলো")


STEPS = {"css": step_css, "img": step_img, "bg": step_bg, "imgsize": step_imgsize, "imgattrs": step_imgattrs,
         "mobile": step_mobile, "fonts": step_fonts}
ORDER = ["css", "img", "bg", "imgsize", "imgattrs", "mobile", "fonts"]


# --------------------------------------------------------------------------- #
# 6. image budget: resize + recompress what is served as files
# --------------------------------------------------------------------------- #
MAX_W = 900          # ছবি কোনোদিন তার নিজের ঘরের চেয়ে বড় আঁকা হয় না
JPEG_Q = 78
WEBP_Q = 76


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", action="append", choices=ORDER, help="default: all")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for name in (a.step or ORDER):
        print(f"[{name}]")
        STEPS[name](a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())


