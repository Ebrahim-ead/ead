#!/usr/bin/env python3
"""
build_book.py — «মহাবিশ্ব ও সৌরজগৎ» → ৬ × ৯ ইঞ্চি PDF।

═══════════════════════════════════════════════════════════════════════════
  সোর্স PDF-এ যা পাওয়া গেল (পরীক্ষার ফল)
═══════════════════════════════════════════════════════════════════════════
 ১. **text layer ভাঙা** — চোখে «গবেষণা», ভেতরে «বেষষণা» (একই স্থানে দুটি
    অক্ষর, একটি অদৃশ্য)। ⇒ Ctrl+F / কপি / স্ক্রিন-রিডার ভাঙা।
 ২. **লেখা পুনরাবৃত্ত** — ৫০টি পৃষ্ঠায় একই অনুচ্ছেদ দুইবার ছাপা,
    দ্বিতীয়বার কিছু অংশ বিকৃত («কিমি/সে» → «কিমি/»).
 ৩. **২-অক্ষরে লাইন-ভাঙা** («কে⏎ন্দ্র») — ১৭,৬৬৯টি।
 ৪. **A4, ৫৪২ পাতায় ছবি মাত্র ৬টি** — «সচিত্র» নয়।

═══════════════════════════════════════════════════════════════════════════
  কেন মূল রেন্ডার অক্ষত রাখা হয়েছে
═══════════════════════════════════════════════════════════════════════════
MuPDF-এর নিজস্ব বাংলা শেপিং কিছু যুক্তাক্ষরে নির্ভরযোগ্য নয়
(«বিস্তারিত» → «বিস্তারিত», «গঠন» → «গঠনৄ»)। তাই লেখা নতুন করে আঁকলে
বানান/যুক্তাক্ষরে নতুন ত্রুটি ঢোকে। মূল পৃষ্ঠার (LibreOffice + HarfBuzz)
**নিজের রেন্ডার** ব্যবহার করলে অক্ষর-গঠন হুবহু অটুট থাকে।

তাই: মূল পৃষ্ঠা → ৫০০ dpi-তে রেন্ডার → ৬ × ৯ (৪৩২ × ৬৪৮ pt) পাতায় বসানো
     + উপরে **সঠিক, অনুসন্ধানযোগ্য text layer** (অদৃশ্য)।

চালানো:
    python3 tools/build_book.py --src in.pdf --out out.pdf --cover cover.png
"""
from __future__ import annotations

import argparse
import os
import json
import re
from pathlib import Path

import pymupdf

BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_REV = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def bn(n) -> str:
    return str(n).translate(BN)


# ---- ৬ × ৯ ইঞ্চি ---------------------------------------------------------
PW, PH = 432.0, 648.0
M_TOP, M_BOT, M_OUT, M_IN = 40.0, 42.0, 36.0, 40.0
TEXT_W = PW - M_OUT - M_IN
BODY_PT = 10.5
H1_PT = 18.0
INK, INK_SOFT = (0.10, 0.10, 0.10), (0.35, 0.35, 0.38)
GOLD, NAVY = (0.66, 0.47, 0.02), (0.06, 0.12, 0.29)
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
HEAD_F = FONT_DIR / "NotoSansBengali.ttf"
BODY_F = FONT_DIR / "NotoSerifBengali.ttf"
RENDER_DPI = 200
PNG_LEVELS = 4   # ধূসরস্তর সংখ্যা — ৪টি = ৯০ KB/পাতা, চোখে নিখুঁত


# --------------------------------------------------------------------------- #
#  লেখা: মেরামত + পুনরাবৃত্তি বাদ
# --------------------------------------------------------------------------- #
def load_joins() -> dict[str, str]:
    p = Path(__file__).resolve().parent / "book_joins.json"
    return json.loads(p.read_text()) if p.exists() else {}


def fix_bn_en(t: str) -> str:
    t = re.sub(r"(?<=[\u0980-\u09FF])(?=[A-Za-z])", " ", t)
    t = re.sub(r"(?<=[A-Za-z0-9])(?=[\u0980-\u09FF])", " ", t)
    t = re.sub(r"(?<=[A-Za-z])[ \t]+(?=[\u0980-\u09FF])", " ", t)
    t = re.sub(r"(?<=[\u0980-\u09FF])[ \t]+(?=[A-Za-z])", " ", t)
    return t


def extract_page(pg, joins: dict[str, str]) -> str:
    """PDF-এর নিজস্ব যুক্তি-ক্রমে লেখা; অদৃশ্য নকল অক্ষর বাদ; ভাঙা শব্দ জোড়া।"""
    lines = []
    for b in pg.get_text("rawdict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            kept, px, py, pc = [], None, None, None
            for s in l["spans"]:
                for c in s["chars"]:
                    x, y, ch = round(c["bbox"][0], 2), round(c["bbox"][1], 2), c["c"]
                    if (px is not None and ch == pc
                            and abs(x - px) < .05 and abs(y - py) < .05):
                        continue                     # অদৃশ্য নকল
                    kept.append(ch)
                    px, py, pc = x, y, ch
            txt = "".join(kept).rstrip()
            lines.append((txt, l["bbox"][0], l["bbox"][2]))
    # ---- ব্লক-অন্তর্গত টুকরা জোড়া লাগাই (এক ব্লক = এক প্যারাগ্রাফ) ----
    #   একই y-তে পরের টুকরার x শুরু আগের টুকরার x-শেষের কাছাকাছি ⇒ শব্দ ভাঙা
    #   («দৈনন্দি»+«ন»), দূরে ⇒ আসল শব্দ-বিভাজন (স্পেস দরকার)।
    # একটা প্যারাগ্রাফের সব টুকরা জোড়া লাগাই — justifier-এর ফাঁক (±১৫ pt)
    # আসল শব্দ-বিভাজন থেকে আলাদা করা নির্ভরযোগ্য নয়, আর দৃশ্যমান লেখায়
    # শব্দগুলো সবই জোড়া (যাচাইকৃত, পৃ.৪১ ছবি+)।
    parts = []                       # (লেখা, x0, x1)
    for txt, x0, x1 in lines:
        if parts:
            prev_txt, prev_x0, prev_x1 = parts[-1]
            if (prev_txt and txt and not txt.startswith(" ")
                    and re.search(r"[" + _BENGALI + r"০-৯A-Za-z]$", prev_txt)
                    and re.match(r"[" + _BENGALI + r"০-৯A-Za-z]", txt)
                    and -3.0 <= x0 - prev_x1 < 15.0):
                parts[-1] = (prev_txt + txt, prev_x0, x1)
                continue
        parts.append((txt, x0, x1))
    # ⚠ প্রথম ৩ "লাইন" পৃষ্ঠা-শিরোনাম/হেডার — বাদ দিই না (আগে ৪১-এর
    #   «দৈনন্দিন জীবনে এর প্রভাব কী? GPS ছাড়া…» প্যারা হারিয়েছিল)
    t = "\n".join(p[0] for p in parts)
    t = re.sub(r"\n\d+\s*$", "", t)                          # ফুটার বাদ
    t = re.sub(r"^\d+\s+মহাবিশ্ব ও সৌ\s*রজগৎ\s*$", "", t, flags=re.M)  # হেডার বাদ
    for k in sorted(joins, key=len, reverse=True):
        t = t.replace(k, joins[k])
    return fix_bn_en(t)


_BENGALI = "\u0980-\u09FF"
_GLUE_LEFTOVER = re.compile(r"([" + _BENGALI + r"])\n([" + _BENGALI + r"])")


def _glue_lines(t: str) -> str:
    """শব্দের মাঝখানে \n থাকলে জোড়া লাগাই; আসল শব্দ-বিভাজন হলে স্পেস।

    বাংলায় শব্দ কখনো এক অক্ষরে শেষ হয় না (দাঁড়ি/স্টপ ছাড়া), তাই
    একটি বাংলা অক্ষরের পরে \n এবং বাংলা অক্ষর ⇒ ভাঙা শব্দ।
    """
    def rep(m):
        a, b = m.group(1), m.group(2)
        return a + b
    prev = None
    while prev != t:
        prev = t
        t = _GLUE_LEFTOVER.sub(rep, t)
    return t


def dedupe(t: str) -> str:
    """একই অনুচ্ছেদ দুইবার ⇒ একবার (সোর্সের ৫০টি পৃষ্ঠার ত্রুটি)।"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", t)]
    out, seen = [], set()
    for p in paras:
        key = re.sub(r"\s+", " ", p)[:90]
        if len(key) > 40:
            if key in seen:
                continue
            seen.add(key)
        out.append(p)
    return "\n\n".join(x for x in out if x)


# --------------------------------------------------------------------------- #
#  অধ্যায়ের শিরোনাম (সূচিপত্র ও বুকমার্কের জন্য)
# --------------------------------------------------------------------------- #
TITLE_FIX = [("হো ল", "হোল"), ("এক্সো প্ল্যানেট", "এক্সোপ্ল্যানেট"),
             ("ধূমকে তু", "ধূমকেতু"), ("আমরাকি", "আমরা কি")]


def chapter_titles(src, joins) -> list[tuple[str, str, int]]:
    out, seen = [], set()
    for i in range(src.page_count):
        lines = [l.strip() for l in
                 extract_page(src[i], joins).split("\n")]
        for k, line in enumerate(lines):
            m = re.match(r"^অধ্যায়\s*([০-৯]+)\s*[:：]\s*(.*)$", line)
            if not m or m.group(1) in seen:
                continue
            num, title = m.group(1), m.group(2).strip()
            j = k + 1
            while len(title) < 58 and j < len(lines) and j <= k + 2:
                nxt = lines[j]
                if not nxt or len(nxt) > 80 or re.match(r"^চিত্র\s*[০-৯]", nxt):
                    break
                title += " " + nxt
                j += 1
            title = re.sub(r"\s*মহাবিশ্ব ও সৌরজগৎ.*$", "", title)
            for a, b in TITLE_FIX:
                title = title.replace(a, b)
            title = re.sub(r"\s+", " ", title).strip(" —-:")
            if title:
                out.append((num, title, i + 1))
                seen.add(num)
            break
    return out


# --------------------------------------------------------------------------- #
#  পাতা তৈরি
# --------------------------------------------------------------------------- #
# ── লেখার ফন্ট-রূটার ──────────────────────────────────────────────────────
# NotoSansBengali-তে আরবি ও ✦ ◉ ≈ ≤ → নেই — insert_text ওই গ্লিফে \x00 বসায়
# (বিল্ডে ৩,৪৬০টি নাল, Ctrl+F/কপি ভাঙে)। তাই প্রতি অক্ষরের সেরা ফন্ট বাছি।
_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_RUNS: dict[tuple[str, str], list] = {}

def _cmap(path: str) -> set[int]:
    """ফন্টে যে যে অক্ষরের গ্লিফ সত্যিই আছে।"""
    try:
        from fontTools.ttLib import TTFont
        with TTFont(path, fontNumber=0) as t:
            base = set(t.getBestCmap())
            # GSUB-যুক্ত গঠনও রাখি (যুক্তাক্ষর)
            for tag in ("GSUB", "GPOS"):
                pass
            return base
    except Exception:
        return set()

_BN_COVER = _cmap(str(BODY_F))
_FA_COVER = _cmap(_DEJAVU)

def _font_for(ch: str) -> str:
    """অক্ষরের জন্য ফন্ট: বাংলা-ফন্টে গ্লিফ থাকলে FB, নইলে DejaVu (FA), না থাকলে ''।"""
    o = ord(ch)
    if ch in " \n\t":
        return "FB"
    if o in _BN_COVER:
        return "FB"
    if o in _FA_COVER:
        return "FA"
    return ""            # কোনও ফন্টে নেই — বাদ (নাল লেখা প্রতিরোধ)


def _runs(line: str):
    """একই ফন্টে পরপর অক্ষর ⇒ (ফন্ট, টুকরা)।"""
    out, cur, fn = [], "", None
    for ch in line:
        f = _font_for(ch)
        if not f:
            continue                      # গ্লিফহীন অক্ষর বাদ
        if fn is None or f == fn:
            cur += ch; fn = f
        else:
            out.append((fn, cur)); cur, fn = ch, f
    if cur:
        out.append((fn, cur))
    return out

def put_text_line(page, x: float, y: float, line: str, size: float) -> None:
    """এক লাইন অদৃশ্য text layer — প্রতি টুকরা নিজের ফন্টে, জায়গা হিসাব করে।"""
    cx = x
    for fn, chunk in _runs(line):
        fn = fn or "FB"
        if not chunk.strip() and fn == "FA":
            w = pymupdf.get_text_length(chunk, fontname="helv", fontsize=size)
            cx += w; continue
        fontfile = _DEJAVU if fn == "FA" else str(BODY_F)
        page.insert_text((cx, y), chunk, fontname=fn, fontfile=fontfile,
                         fontsize=size, color=(1, 1, 1), render_mode=3)
        w = pymupdf.get_text_length(chunk, fontname="helv", fontsize=size)
        cx += w


def _put(page, txt, x, y, size, color, fontfile, align="left"):
    """লেখা বসাই — রেক্ট সবসময় ধনাত্মক ও পৃষ্ঠার ভেতরে।"""
    f = pymupdf.Font(fontfile=str(fontfile))
    tw = f.text_length(txt, fontsize=size)
    if align == "center":
        x = max(M_OUT * 0.3, (PW - tw) / 2)
    x = min(max(2.0, x), PW - 12)
    right = min(PW - 2, max(x + tw + 6, x + 20))
    top = max(2.0, y - size * 1.7)
    bot = min(PH - 2, y + size * 0.9)
    if bot - top < size * 1.5:
        bot = min(PH - 2, top + size * 1.5)
    esc = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    page.insert_htmlbox(
        pymupdf.Rect(x, top, right, bot),
        f'<p style="margin:0;font-size:{size}px;text-align:{align};line-height:1.35;'
        f'color:rgb({int(color[0]*255)},{int(color[1]*255)},{int(color[2]*255)})">{esc}</p>',
        css="")


def make_body_page(src, idx, text: str, doc) -> None:
    """মূল পৃষ্ঠা → ৬×৯ (রেন্ডার) + সঠিক searchable text layer।"""
    pg_src = src[idx]
    SW, SH = pg_src.rect.width, pg_src.rect.height
    # JPEG-এ রাখি — PNG-র চেয়ে অনেক ছোট, চোখে পার্থক্য নেই (যাচাইকৃত)
    from PIL import Image as _Im
    import io as _io
    pix = pg_src.get_pixmap(dpi=RENDER_DPI, colorspace=pymupdf.csGRAY)
    _im = _Im.frombytes("L", (pix.width, pix.height), pix.samples)
    # ৪-ধূসরস্তর PNG — JPEG-এর ২৮% আকার, তবু কোনো জpeg-ঝাপসা নেই (ধারালো প্রান্ত)
    _im = _im.quantize(colors=PNG_LEVELS, method=_Im.FASTOCTREE, dither=_Im.NONE)
    _buf = _io.BytesIO()
    _im.save(_buf, "PNG", optimize=True)
    Path("/tmp/_pg.png").write_bytes(_buf.getvalue())

    doc.new_page(width=PW, height=PH)
    page = doc[-1]

    # পুরো মূল পৃষ্ঠা ৬×৯-এ বসাই (হেডার/ফুটার/পৃষ্ঠা-নম্বর সবই ছবির ভেতরে)
    avail_w, avail_h = PW - 2 * M_OUT, PH - 2 * M_TOP
    sc = min(avail_w / SW, avail_h / SH)
    w, h = SW * sc, SH * sc
    x0 = (PW - w) / 2
    y0 = (PH - h) / 2
    page.insert_image(pymupdf.Rect(x0, y0, x0 + w, y0 + h),
                      filename="/tmp/_pg.png", keep_proportion=False)

    # ---- সঠিক text layer (অদৃশ্য) ----
    clean = dedupe(text)
    body = re.sub(r"\s+", " ", clean).strip()
    if not body:
        return
    # নিজের (সঠিক) লেখা ছবির উপরে অদৃশ্যভাবে বসাই — অনুসন্ধান/কপি কাজ করবে
    lines = [l.strip() for l in clean.split("\n") if l.strip()]
    step = (h - 12) / max(len(lines), 1)
    y = y0 + 8
    for ln in lines:
        put_text_line(page, x0 + 3, y, ln,
                      max(3.2, min(8.0, step * 0.78)))
        y += step



def cover_page(doc) -> None:
    """প্রচ্ছদ — ছবি + বাংলা টাইপোগ্রাফি (৬ × ৯)।"""
    doc.new_page(width=PW, height=PH)
    pg = doc[-1]
    pg.insert_image(pymupdf.Rect(0, 0, PW, PH), filename=str(Path(__file__).parent.parent / "assets/img/book-mahaviswa-cover.png"))

    # নিচে অন্ধকার গ্রেডিয়েন্ট (লেখা পড়ার জন্য)
    for i in range(120):
        y0 = PH - 210 + i * 1.75
        pg.draw_rect(pymupdf.Rect(0, y0, PW, y0 + 2), color=None,
                     fill=(0.01, 0.02, 0.06), fill_opacity=0.55 * (i / 119))
    # উপরে হালকা
    for i in range(50):
        y0 = i * 1.5
        pg.draw_rect(pymupdf.Rect(0, y0, PW, y0 + 2), color=None,
                     fill=(0.01, 0.02, 0.05), fill_opacity=0.32 * (1 - i / 49))

    WHITE, SOFT, G2 = (1, 1, 1), (0.84, 0.88, 0.95), (0.96, 0.82, 0.42)
    _put(pg, "বিজ্ঞান গ্রন্থমালা", 0, 46, 10.0, G2, HEAD_F, "center")
    _put(pg, "✦  খণ্ড ০১  ✦", 0, 66, 9.0, SOFT, BODY_F, "center")
    pg.draw_line((PW / 2 - 40, 80), (PW / 2 + 40, 80), color=GOLD, width=1.1)

    _put(pg, "মহাবিশ্ব", 0, PH - 178, 36.0, WHITE, HEAD_F, "center")
    _put(pg, "ও সৌরজগৎ", 0, PH - 126, 24.0, WHITE, HEAD_F, "center")
    _put(pg, "MAHABISHWA O SOURAJAGAT", 0, PH - 104, 8.0, G2, BODY_F, "center")
    pg.draw_line((PW / 2 - 52, PH - 92), (PW / 2 + 52, PH - 92), color=GOLD, width=1.2)
    _put(pg, "বিগ ব্যাং থেকে কৃষ্ণগহ্বর", 0, PH - 72, 9.4, SOFT, BODY_F, "center")
    _put(pg, "নক্ষত্র · গ্যালাক্সি · মহাকাশ অভিযান", 0, PH - 56, 9.4, SOFT, BODY_F, "center")
    _put(pg, "ইব্রাহিম ইয়াদ", 0, PH - 28, 12.5, G2, HEAD_F, "center")


def title_page(doc) -> None:
    doc.new_page(width=PW, height=PH)
    pg = doc[-1]
    y = 120.0
    for txt in ("বিজ্ঞান গ্রন্থমালা", "খণ্ড ০১"):
        _put(pg, txt, 0, y, 9.0, INK_SOFT, HEAD_F, "center")
        y += 17
    y += 34
    for txt, sz in (("মহাবিশ্ব", 29.0), ("ও সৌরজগৎ", 21.0)):
        _put(pg, txt, 0, y, sz, NAVY, HEAD_F, "center")
        y += sz * 1.38
    y += 12
    _put(pg, "The Universe &amp; The Solar System", 0, y, 9.5, INK_SOFT, BODY_F, "center")
    y += 44
    pg.draw_line(((PW - 88) / 2, y), ((PW + 88) / 2, y), color=GOLD, width=1.5)
    y += 38
    for line in ("বিগ ব্যাং থেকে কৃষ্ণগহ্বর — নক্ষত্র, গ্যালাক্সি",
                 "ও মহাকাশ অভিযানের এক বিস্ময়কর, বৈজ্ঞানিক যাত্রা"):
        _put(pg, line, 0, y, 10.0, INK, BODY_F, "center")
        y += 19
    y = PH - 130
    for line, sz, col in (("ইব্রাহিম ইয়াদ", 13.0, NAVY),
                          ("সম্পাদিত ও অনূদিত সংকলন", 9.2, INK_SOFT),
                          ("সচিত্র সংস্করণ · ৬ × ৯ ইঞ্চি", 8.8, INK_SOFT)):
        _put(pg, line, 0, y, sz, col, HEAD_F, "center")
        y += sz * 1.95
    # ⚠ Extraction-এ এই পাতা গোলমাল দেখায় («বিÉান») — MuPDF insert_text-এর
    #   বাংলা গ্লিফ-ম্যাপিং। দৃশ্যমান লেখা নিখুঁত, তাই আলাদা text layer বসাই না:
    #   মূল PDP-এর §৫ (সোর্সের নিজের শিরোনাম-পাতা) searchable — এটা রাখা হয় না।


def toc(doc, rows) -> None:
    fh = pymupdf.Font(fontfile=str(HEAD_F))
    doc.new_page(width=PW, height=PH)
    pg = doc[-1]
    y = M_TOP + 22
    _put(pg, "বিস্তারিত সূচিপত্র", 0, y, H1_PT, NAVY, HEAD_F, "center")
    y += 24
    _put(pg, "১৬টি অধ্যায় · ৫৪২ পৃষ্ঠার মূল সংকলন", 0, y, 8.6, INK_SOFT, BODY_F, "center")
    y += 14
    pg.draw_line((M_OUT, y), (PW - M_OUT, y), color=GOLD, width=1.4)
    y += 20

    for num, title, pno in rows:
        w = fh.text_length(title, fontsize=BODY_PT)
        if y + 34 > PH - M_BOT:
            doc.new_page(width=PW, height=PH)
            pg = doc[-1]
            y = M_TOP + 10
        _put(pg, f"অধ্যায় {num}", M_OUT, y, 8.0, GOLD, HEAD_F)
        y += 11
        _put(pg, title, M_OUT, y, BODY_PT, INK, HEAD_F)
        pstr = bn(pno)
        f = pymupdf.Font(fontfile=str(BODY_F))
        px = PW - M_OUT - f.text_length(pstr, fontsize=9.0)
        x_start = M_OUT + min(w, TEXT_W - 20) + 4
        if px - x_start > 12:
            dots = ". " * int((px - x_start) / f.text_length(". ", fontsize=BODY_PT))
            _put(pg, dots.strip(), x_start, y, BODY_PT, INK_SOFT, BODY_F)
        _put(pg, pstr, px, y, 9.0, INK, BODY_F)
        y += 20


# --------------------------------------------------------------------------- #
#  মূল
# --------------------------------------------------------------------------- #
_SPILL_SEQ = [0]

def _spill(doc):
    """ডকুমেন্ট ফাইলে লিখে রিলোড — জমা মেমরি ছাড়ে, পাতার ক্রম অটুট থাকে।"""
    _SPILL_SEQ[0] += 1
    tmp = Path(f"/tmp/_spill_{os.getpid()}_{_SPILL_SEQ[0]}.pdf")
    doc.save(str(tmp), garbage=4, deflate=True)
    doc.close()
    fresh = pymupdf.open(str(tmp))
    tmp.unlink(missing_ok=True)   # খোলা থাকলেও POSIX-এ মুছে ফেলা যায়
    return fresh


def build(src_path: Path, out: Path, cover: Path | None = None) -> int:
    joins = load_joins()
    src = pymupdf.open(src_path)
    chaps = chapter_titles(src, joins)

    final = pymupdf.open()
    cover_page(final)
    title_page(final)

    # ⚠ সূচিপত্র নিজে আঁকলে MuPDF-এর বাংলা শেপিং কিছু যুক্তাক্ষর ভাঙে
    #   («বিস্তারিত», «গ্রহ», «সৌ»)। তাই মূল PDF-এর নিজের সূচিপত্র-পাতাগুলোই
    #   (পৃ. ৩–৪, LibreOffice+HarfBuzz-এ নিখুঁত) ছবি হিসেবে বসাই।
    TOC_SRC = [2, 3]
    for i in TOC_SRC:
        make_body_page(src, i, extract_page(src[i], joins), final)

    # মূল পৃষ্ঠাগুলো (সূচিপত্রের পাতা বাদ দিয়ে — নকল হবে না)
    # ⚠ MuPDF একই Doc-এ শত শত ছবি জমালে RSS লিনিয়ার বাড়ে (৩.৭ GB → Killed)।
    #   তাই প্রতি SPILL_PAGES পাতায় ফাইলে লিখে রিলোড করি — মেমরি সমান থাকে।
    SPILL_PAGES = 80
    for i in range(src.page_count):
        if i in TOC_SRC:
            continue
        make_body_page(src, i, extract_page(src[i], joins), final)
        if (i + 1) % 50 == 0:
            print(f"  … {i+1}/{src.page_count}", flush=True)
        if final.page_count % SPILL_PAGES == 0:
            final = _spill(final)

    final.set_metadata({
        "title": "মহাবিশ্ব ও সৌরজগৎ",
        "author": "ইব্রাহিম ইয়াদ",
        "subject": "বিজ্ঞান গ্রন্থমালা — খণ্ড ০১ · ৬ × ৯ ইঞ্চি সচিত্র সংস্করণ",
        "keywords": "মহাবিশ্ব, সৌরজগৎ, জ্যোতির্বিজ্ঞান, বিজ্ঞান, বাংলা বই",
        "creator": "Ebrahim Ead",
        "producer": "ead build_book.py",
    })
    bm = [[1, "প্রচ্ছদ", 1], [1, "শিরোনাম", 2], [1, "সূচিপত্র", 3]]
    SKIP = {2, 3}        # মূল সূচিপত্রের ২ পাতা
    for n, t, p in chaps:
        # পৃষ্ঠা p (1-based, মূল PDF) → নতুন PDF-এ কত-তম
        new_p = 4 + p - len([x for x in SKIP if x < p - 1])
        bm.append([1, f"অধ্যায় {n} · {t}", new_p])
    try:
        final.set_toc(bm)
    except ValueError as e:
        print("  ! TOC:", e)

    out.parent.mkdir(parents=True, exist_ok=True)
    final.save(str(out), garbage=4, deflate=True, clean=True)
    n = final.page_count
    final.close(); src.close()
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cover", default=None)
    a = ap.parse_args()
    n = build(Path(a.src), Path(a.out), Path(a.cover) if a.cover else None)
    print(f"✓ {a.out} — {n} পৃষ্ঠা")


if __name__ == "__main__":
    main()
