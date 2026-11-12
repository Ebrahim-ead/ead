#!/usr/bin/env python3
"""
render_book.py — «মহাবিশ্বের পাঠশালা» কন্টেন্ট → ৬ × ৯ ইঞ্চি PDF

MuPDF-এর বাংলা শেপিং যাচাইকৃত (যুক্তাক্ষর নিখুঁত)। লেখা সরাসরি PDF-এ
সেট করা হয় — ছবি হিসেবে রেন্ডার নয়, তাই অনুসন্ধানযোগ্য ও হালকা।

কন্টেন্ট-ফরম্যাট (content/chNN.md):
  #  অধ্যায়-শিরোনাম        → নতুন অধ্যায় (নতুন পৃষ্ঠায়, বড় লেখায়)
  ## উপ-শিরোনাম            → সেকশন-ব্রেক (নতুন পৃষ্ঠায়, রঙিন)
  ### ছোট-শিরোনাম          → ইনলাইন বোল্ড
  ***ছবি-বর্ণনা***          → পূর্ণপৃষ্ঠা চিত্র-স্থান
  > গবেষণা ...             → রঙিন বাক্স
  | টেবিল |               → টেবিল
  - তালিকা
  **বোল্ড**               → বোল্ড
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf

# ── পৃষ্ঠা-মাপ ───────────────────────────────────────────────────────────
PW, PH = 432, 648          # ৬ × ৯ ইঞ্চি
M_TOP, M_BOT = 62, 58      # pt
M_IN, M_OUT = 52, 46       # ভেতরের(ডান) ও বাইরের(বাম) মার্জিন
TEXT_W = PW - M_IN - M_OUT

# ── ফন্ট ─────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONT_DIR = ROOT / "assets" / "fonts"
CONTENT_DIR = HERE / "pathshala_content"
IMG_DIR = HERE / "pathshala_img"
BODY_F = FONT_DIR / "NotoSansBengali.ttf"
HEAD_F = FONT_DIR / "NotoSerifBengali.ttf"
DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

# ── রং (সাইটের ব্র্যান্ড) ────────────────────────────────────────────────
NAVY = (0.043, 0.094, 0.184)
INK = (0.106, 0.118, 0.141)
INK_SOFT = (0.353, 0.376, 0.408)
GOLD = (0.788, 0.635, 0.235)
BLUE = (0.129, 0.325, 0.529)
PANEL = (0.957, 0.965, 0.976)
PANEL_BD = (0.851, 0.878, 0.914)

# ── টাইপোগ্রাফি স্কেল ────────────────────────────────────────────────────
FS_BODY = 10.6
LEAD = 16.6
FS_H1 = 23.0
FS_H2 = 15.0
FS_H3 = 11.2
FS_SMALL = 8.8

CHAPTER_PB = 0.0   # অধ্যায়-শুরু পৃষ্ঠা-নম্বর भरण হবে


# ══════════════════════════════════════════════════════════════════════════
#  অক্ষর-মাপ (ফন্ট থেকে সত্যিকারের প্রস্থ)
# ══════════════════════════════════════════════════════════════════════════
class Measurer:
    """ফন্টের প্রকৃত গ্লিফ-প্রস্থ দিয়ে লেখা মাপি — লাইন-ভাঙার জন্য।"""

    def __init__(self, fontfile: Path):
        from fontTools.ttLib import TTFont
        self._f = TTFont(str(fontfile), fontNumber=0)
        self._cmap = self._f.getBestCmap()
        self._upm = self._f["head"].unitsPerEm
        self._hmtx = self._f["hmtx"]
        self._cache: dict[str, float] = {}

    def width(self, ch: str) -> float:
        if ch in self._cache:
            return self._cache[ch]
        g = self._cmap.get(ord(ch))
        w = 0.0
        if g is not None:
            try:
                w = self._hmtx[g][0] / self._upm
            except KeyError:
                w = 0.0
        else:
            w = 0.5
        self._cache[ch] = w
        return w

    def text_w(self, s: str, size: float) -> float:
        return sum(self.width(c) for c in s) * size


BODY_M = Measurer(BODY_F)
HEAD_M = Measurer(HEAD_F)


# ══════════════════════════════════════════════════════════════════════════
#  লেখা আঁকা — অক্ষর-রূটার (গ্লিফহীন অক্ষর বাদ)
# ══════════════════════════════════════════════════════════════════════════
_BN_COVER: set[int] = set()
_FA_COVER: set[int] = set()


def _load_covers() -> None:
    global _BN_COVER, _FA_COVER
    if _BN_COVER:
        return
    from fontTools.ttLib import TTFont
    try:
        with TTFont(str(BODY_F), fontNumber=0) as t:
            _BN_COVER = set(t.getBestCmap())
        with TTFont(str(HEAD_F), fontNumber=0) as t:
            _BN_COVER |= set(t.getBestCmap())
    except Exception:
        pass
    try:
        with TTFont(str(DEJAVU), fontNumber=0) as t:
            _FA_COVER = set(t.getBestCmap())
    except Exception:
        pass


def _runs(text: str):
    """একই ফন্টে পরপর অক্ষর ⇒ (ফন্ট-নাম, টুকরা)।"""
    out, cur, fn = [], "", None
    for ch in text:
        o = ord(ch)
        if ch.isspace():
            f = "FB"
        elif o in _BN_COVER:
            f = "FB"
        elif o in _FA_COVER:
            f = "FA"
        else:
            continue                       # কোনো ফন্টে নেই — বাদ
        if fn is None or f == fn:
            cur += ch
        else:
            out.append((fn, cur))
            cur, fn = ch, f
        fn = f
    if cur:
        out.append((fn, cur))
    return out


def put_line(page, x: float, y: float, text: str, size: float,
             color=INK, head: bool = False, italic: bool = False) -> None:
    """এক লাইন আঁকি — প্রতি টুকরা নিজের ফন্টে, প্রকৃত প্রস্থে এগিয়ে।"""
    cx = x
    m = HEAD_M if head else BODY_M
    for fn, chunk in _runs(text):
        ff = str(DEJAVU) if fn == "FA" else str(HEAD_F if head else BODY_F)
        try:
            page.insert_text((cx, y), chunk, fontname=fn, fontfile=ff,
                             fontsize=size, color=color)
        except Exception:
            pass
        cx += m.text_w(chunk, size)


# ══════════════════════════════════════════════════════════════════════════
#  লাইন-ভাঙা (বাংলার জন্য স্পেস-ভিত্তিক)
# ══════════════════════════════════════════════════════════════════════════
def wrap(text: str, max_w: float, size: float, head: bool = False) -> list[str]:
    """শব্দ ধরে লাইন ভাঙি; খুব লম্বা শব্দ হলে অক্ষর ধরে।"""
    m = HEAD_M if head else BODY_M
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if m.text_w(trial, size) <= max_w or not cur:
            if m.text_w(trial, size) <= max_w:
                cur = trial
            else:
                # একক শব্দই বড় — অক্ষর ধরে ভাঙি
                part = ""
                for ch in w:
                    if m.text_w(part + ch, size) > max_w and part:
                        lines.append(part)
                        part = ch
                    else:
                        part += ch
                cur = part
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


# ══════════════════════════════════════════════════════════════════════════
#  পৃষ্ঠা-ব্যবস্থাপনা
# ══════════════════════════════════════════════════════════════════════════
class Book:
    def __init__(self):
        self.doc = pymupdf.open()
        self.page = None
        self.y = 0.0
        self._new_page()

    # -- পৃষ্ঠা তৈরি ----------------------------------------------------
    def _new_page(self, footer: bool = True):
        self.doc.new_page(width=PW, height=PH)
        self.page = self.doc[-1]
        self.y = M_TOP
        self.footer = footer
        self.just_chapter = False

    def ensure(self, need: float) -> None:
        """পর্যাপ্ত জায়গা নেই ⇒ নতুন পৃষ্ঠা।"""
        if self.y + need > PH - M_BOT:
            self._new_page()

    def space(self) -> float:
        return PH - M_BOT - self.y

    # -- অনুচ্ছেদ ------------------------------------------------------
    def para(self, text: str, size: float = FS_BODY, lead: float = LEAD,
             color=INK, head: bool = False, indent: float = 0.0,
             space_after: float = 4.2) -> None:
        m = HEAD_M if head else BODY_M
        lines = wrap(text, TEXT_W - indent, size, head)
        for i, ln in enumerate(lines):
            self.ensure(lead)
            x = M_OUT + (indent if i else 0)
            put_line(self.page, x, self.y + size * 0.86, ln, size, color, head)
            self.y += lead
        self.y += space_after

    # -- শিরোনাম ------------------------------------------------------
    def h1(self, text: str) -> None:
        """অধ্যায়-শিরোনাম — নতুন পৃষ্ঠা, বড় সোনালি রেখা।"""
        if self.y > M_TOP + 10:
            self._new_page()
        # উপরের লেবেল
        self.y += 26
        put_line(self.page, M_OUT, self.y, "মহাবিশ্বের পাঠশালা",
                 FS_SMALL, GOLD, head=True)
        self.y += 12
        self.page.draw_line((M_OUT, self.y), (M_OUT + 34, self.y),
                            color=GOLD, width=2.2)
        self.y += 26
        for ln in wrap(text, TEXT_W, FS_H1, True):
            put_line(self.page, M_OUT, self.y + FS_H1 * 0.86, ln, FS_H1,
                     NAVY, head=True)
            self.y += FS_H1 * 1.30
        self.y += 6
        self.page.draw_line((M_OUT, self.y), (PW - M_IN, self.y),
                            color=PANEL_BD, width=0.9)
        self.y += 20
        self.just_chapter = True          # প্রথম h2 আর পৃষ্ঠা ভাঙবে না

    def h2(self, text: str) -> None:
        """সেকশন-শিরোনাম — নীল বার; জায়গা কম হলে নতুন পৃষ্ঠা।"""
        self.just_chapter = False
        self.ensure(FS_H2 * 2.6 + LEAD * 3)   # শিরোনাম + অন্তত ৩ লাইন
        self.y += 8
        # বাঁ পাশে নীল বার
        for ln in wrap(text, TEXT_W - 14, FS_H2, True):
            self.page.draw_rect(
                pymupdf.Rect(M_OUT, self.y + 1, M_OUT + 3.5, self.y + FS_H2 * 1.18),
                color=None, fill=BLUE)
            put_line(self.page, M_OUT + 14, self.y + FS_H2 * 0.86, ln,
                     FS_H2, BLUE, head=True)
            self.y += FS_H2 * 1.30
        self.y += 14

    def h3(self, text: str) -> None:
        self.ensure(FS_H3 * 2.2)
        self.y += 6
        put_line(self.page, M_OUT, self.y + FS_H3 * 0.86, text, FS_H3,
                 NAVY, head=True)
        self.y += FS_H3 * 1.45

    # -- বোল্ড-রেখাযুক্ত প্যারা -----------------------------------------
    def bold_para(self, text: str) -> None:
        """**শুরু** বাকি… — প্রথম অংশ বোল্ড, বাকিটা সাধারণ।"""
        m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", text, re.S)
        if not m:
            self.para(text)
            return
        head, rest = m.group(1), m.group(2).strip()
        head = head.replace("**", "")        # ভেতরের অবশিষ্ট ** সরাই
        full = head + (" " + rest if rest else "")
        lines = wrap(full, TEXT_W, FS_BODY)
        # প্রথম লাইনে বোল্ড অংশ
        self.ensure(LEAD)
        put_line(self.page, M_OUT, self.y + FS_BODY * 0.86, head, FS_BODY, NAVY, head=True)
        hw = BODY_M.text_w(head, FS_BODY)
        if rest:
            first_rest_w = TEXT_W - hw - BODY_M.width(" ") * FS_BODY
            rlines = wrap(rest, first_rest_w, FS_BODY)
            if rlines and BODY_M.text_w(rlines[0], FS_BODY) <= first_rest_w:
                put_line(self.page, M_OUT + hw + BODY_M.width(" ") * FS_BODY,
                         self.y + FS_BODY * 0.86, rlines[0], FS_BODY, INK)
                self.y += LEAD
                remain = " ".join(rlines[1:])
                if remain:
                    self.para(remain, space_after=6)
            else:
                self.y += LEAD
                self.para(rest, space_after=6)
        else:
            self.y += LEAD + 6

    # -- তালিকা --------------------------------------------------------
    def bullet(self, text: str) -> None:
        self.ensure(LEAD)
        put_line(self.page, M_OUT + 2, self.y + FS_BODY * 0.86, "•", FS_BODY, GOLD)
        m = Measurer(BODY_F)
        indent = 14.0
        lines = wrap(text, TEXT_W - indent, FS_BODY)
        for i, ln in enumerate(lines):
            if i:
                self.ensure(LEAD)
            put_line(self.page, M_OUT + indent, self.y + FS_BODY * 0.86,
                     ln, FS_BODY, INK)
            self.y += LEAD
        self.y += 3

    def num(self, n: str, text: str) -> None:
        self.ensure(LEAD)
        put_line(self.page, M_OUT + 2, self.y + FS_BODY * 0.86, n,
                 FS_BODY, BLUE, head=True)
        indent = 20.0
        lines = wrap(text, TEXT_W - indent, FS_BODY)
        for i, ln in enumerate(lines):
            if i:
                self.ensure(LEAD)
            put_line(self.page, M_OUT + indent, self.y + FS_BODY * 0.86,
                     ln, FS_BODY, INK)
            self.y += LEAD
        self.y += 3

    # -- গবেষণা-বাক্স --------------------------------------------------
    def quote_box(self, lines_text: list[str]) -> None:
        """হালকা নীল বাক্সে গবেষণার ফল।"""
        # মাপ আগে
        inner_w = TEXT_W - 26
        plan: list[tuple[str, float, bool, tuple]] = []
        for raw in lines_text:
            t = raw.strip()
            if not t:
                plan.append(("", 4.0, False, INK))
                continue
            if t.startswith("**") and t.endswith("**"):
                for ln in wrap(t.strip("*"), inner_w, 10.4, True):
                    plan.append((ln, 15.0, True, NAVY))
            elif t.startswith("|"):
                plan.append((t, 13.0, False, INK))       # টেবিল-ASCII সরল
            elif t.startswith("- "):
                for ln in wrap("• " + t[2:], inner_w - 10, 9.6):
                    plan.append((ln, 14.0, False, INK))
            else:
                for ln in wrap(t, inner_w, 9.6):
                    plan.append((ln, 14.0, False, INK))

        total = sum(p[1] for p in plan) + 22
        pad = 12
        # এক পৃষ্ঠায় না ধরলে ভাগ করি
        avail = self.space()
        if total > avail:
            self._new_page()

        y0 = self.y + 4
        y1 = min(y0 + total, PH - M_BOT)
        self.page.draw_rect(pymupdf.Rect(M_OUT, y0, PW - M_IN, y1),
                            color=PANEL_BD, fill=PANEL, width=0.8)
        self.page.draw_rect(pymupdf.Rect(M_OUT, y0, M_OUT + 3, y1),
                            color=None, fill=GOLD)

        yy = y0 + pad + 4
        for txt, h, bold, col in plan:
            if not txt:
                yy += h
                continue
            if yy + h > y1 - 4:
                break
            put_line(self.page, M_OUT + 16, yy + 8.6, txt, 9.6 if not bold else 10.4,
                     col, bold)
            yy += h
        self.y = y1 + 14


    # -- টেবিল ----------------------------------------------------------
    def table(self, rows: list[str]) -> None:
        """| … | টেবিল — শিরোনাম-সারি, রঙিন ব্যাকগ্রাউন্ড, লাইন-ভাঙা।"""
        parsed: list[list[str]] = []
        header_idx = -1
        for raw in rows:
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                header_idx = len(parsed) - 1
                continue
            parsed.append(cells)
        if not parsed:
            return
        ncol = max(len(r) for r in parsed)
        parsed = [r + [""] * (ncol - len(r)) for r in parsed]

        fs = 8.5
        lead = 11.8
        padx = 5.0
        # কলামের প্রস্থ — বিষয়বস্তুর দৈর্ঘ্য অনুপাতে, ন্যূনতম/সর্বোচ্চ সীমা
        want = []
        for c in range(ncol):
            w = max(BODY_M.text_w(r[c], fs) for r in parsed)
            want.append(min(max(w, 34.0), TEXT_W * 0.62))
        tot = sum(want)
        widths = [max(38.0, w / tot * TEXT_W) for w in want]
        scale = TEXT_W / sum(widths)
        widths = [w * scale for w in widths]

        # সারি-উচ্চতা আগে মাপি
        layout = []
        for ri, r in enumerate(parsed):
            is_head = (ri <= header_idx) or (header_idx < 0 and ri == 0)
            bold = is_head
            cell_lines = [wrap(r[c], widths[c] - 2 * padx, fs, head=bold)
                          for c in range(ncol)]
            h = max(len(cl) for cl in cell_lines) * lead + 7.0
            layout.append((cell_lines, h, is_head))

        def draw_block():
            x_end = M_OUT + sum(widths)
            y0 = self.y
            yy = y0
            for cell_lines, h, is_head in layout:
                if yy + h > PH - M_BOT:
                    self._new_page()
                    yy = self.y
                    y0 = yy
                    x_end = M_OUT + sum(widths)
                fill = PANEL if is_head else None
                if fill:
                    self.page.draw_rect(pymupdf.Rect(M_OUT, yy, x_end, yy + h),
                                        color=None, fill=fill)
                elif (yy - y0) // max(h, 1) % 2 == 0:
                    self.page.draw_rect(pymupdf.Rect(M_OUT, yy, x_end, yy + h),
                                        color=None, fill=(0.984, 0.988, 0.992))
                cx = M_OUT
                for c in range(ncol):
                    for li, ln in enumerate(cell_lines[c]):
                        put_line(self.page, cx + padx,
                                 yy + 5.0 + fs * 0.86 + li * lead,
                                 ln, fs, NAVY if is_head else INK, head=is_head)
                    cx += widths[c]
                # নিচের রেখা
                self.page.draw_line(pymupdf.Point(M_OUT, yy + h),
                                    pymupdf.Point(x_end, yy + h),
                                    color=PANEL_BD, width=0.5)
                yy += h
            # বাইরের সীমারেখা
            self.page.draw_rect(pymupdf.Rect(M_OUT, y0, x_end, yy),
                                color=INK_SOFT, width=0.6)
            self.y = yy + 10.0

        # পুরো টেবিল এক পৃষ্ঠায় না ধরলে ভাগ করি (শিরোনাম পুনরাবৃত্তি)
        total_h = sum(h for _, h, _ in layout)
        avail = self.space()
        if total_h <= avail:
            draw_block()
            return
        # ভাগ: যত সারি একটি পৃষ্ঠায় ধরে
        head_rows = [l for l in layout[:max(header_idx + 1, 1)]]
        head_h = sum(h for _, h, _ in head_rows)
        body = layout[len(head_rows):]
        while body:
            self.ensure(40)
            self.y += 2
            cap = self.space() - head_h - 6
            take = []
            used = 0.0
            for item in body:
                if used + item[1] <= cap:
                    take.append(item); used += item[1]
                else:
                    break
            if not take:
                take = [body[0]]
            layout = head_rows + take
            draw_block()
            body = body[len(take):]

    # -- ছবির পাতা -----------------------------------------------------
    def image_page(self, caption: str, path: str | None = None,
                   full: bool = True) -> None:
        """পূর্ণ পৃষ্ঠার ছবি + নিচে ক্যাপশন (ছবি না থাকলে ছোট ব্লক)।"""
        from pathlib import Path as _P
        has_img = bool(path) and _P(path).exists()
        if not has_img:
            # ছবি এখনো নেই — লেখার মাঝে ছোট প্লেসহোল্ডার (ফাঁকা পাতা নয়)
            h = 132.0
            if self.space() < h + 26:
                self._new_page()          # পৃষ্ঠার একদম শেষে ঝুলতে দিই না
            self.ensure(h + 26)
            box = pymupdf.Rect(M_OUT, self.y, PW - M_IN, self.y + h)
            self.page.draw_rect(box, color=PANEL_BD, fill=PANEL, width=0.8)
            self.page.draw_rect(pymupdf.Rect(box.x0, box.y0, box.x0 + 3,
                                             box.y1), color=None, fill=GOLD)
            put_line(self.page, box.x0 + 14, box.y0 + 18, "চিত্র", 8.4, GOLD, head=True)
            cy = box.y1 + 15
            for ln in wrap(caption, TEXT_W - 10, 9.0):
                put_line(self.page, M_OUT, cy, ln, 9.0, INK_SOFT)
                cy += 13
            self.y = cy + 10
            return

        if self.y > M_TOP + 10:
            self._new_page()
        top = M_TOP + 10
        cap_lines = wrap(caption, TEXT_W - 20, 9.4)
        cap_h = len(cap_lines) * 14 + 16
        box = pymupdf.Rect(M_OUT, top, PW - M_IN, PH - M_BOT - cap_h)
        if path and Path(path).exists():
            self.page.insert_image(box, filename=path, keep_proportion=True)
        else:
            # ছবি নেই ⇒ সুন্দর প্লেসহোল্ডার
            self.page.draw_rect(box, color=PANEL_BD, fill=PANEL, width=0.8)
            cy = (box.y0 + box.y1) / 2
            put_line(self.page, M_OUT + 20, cy, "চিত্র",
                     FS_SMALL, GOLD, head=True)
        cy = box.y1 + 22
        for ln in cap_lines:
            put_line(self.page, PW / 2 - BODY_M.text_w(ln, 9.4) / 2, cy,
                     ln, 9.4, INK_SOFT)
            cy += 14
        self._new_page()

    # -- শেষ -----------------------------------------------------------
    def save(self, out: Path) -> int:
        n = self.doc.page_count
        # ফুটার (প্রচ্ছদ বাদে)
        for i in range(1, n):
            p = self.doc[i]
            txt = f"{i + 1}"
            put_line(p, PW / 2 - 6, PH - 30, txt, 8.6, INK_SOFT)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(out), garbage=4, deflate=True)
        return n


# ══════════════════════════════════════════════════════════════════════════
#  মার্কডাউন → পৃষ্ঠা
# ══════════════════════════════════════════════════════════════════════════
# ক্যাপশন-কীওয়ার্ড → ছবি (বাংলা শব্দে মিলানো)
IMG_KEYS: list[tuple[tuple[str, ...], str]] = [
    (("স্পুটনিক", "কৃত্রিম উপগ্রহ"),                 "10_iss.jpg"),
    (("প্রক্সিমা", "কাছের তারা"),                    "13_milkyway.jpg"),
    (("মঙ্গলের পৃষ্ঠ", "মঙ্গল —", "লাল ধুলি"),      "03_mars.jpg"),
    (("বৃহস্পতি",),                                "04_jupiter.jpg"),
    (("শনি",),                                     "05_saturn.jpg"),
    (("ইউরেনাস",),                                 "06_uranus.jpg"),
    (("নেপচুন",),                                  "07_neptune.jpg"),
    (("প্লুটো",),                                  "08_pluto.jpg"),
    (("ধূমকেতু",),                                 "09_comet.jpg"),
    (("Space Station", "ISS", "কৃত্রিম"),          "10_iss.jpg"),
    (("JWST", "জেমস ওয়েব"),                        "11_jwst.jpg"),
    (("M87", "কৃষ্ণগহ্বর"),                          "12_blackhole.jpg"),
    (("HR", "হার্টজস্প্রুং", "লেখচিত্র"),            "17_hr.jpg"),
    (("সুপারনোভা", "বিস্ফোরণ"),                      "18_supernova.jpg"),
    (("Bennu", "গ্রহাণু"),                          "19_bennu.jpg"),
    (("সূর্যের গঠন", "সূর্য", "Parker"),             "20_sun.jpg"),
    (("শুক্র",),                                    "21_venus.jpg"),
    (("চাঁদ",),                                     "22_moon.jpg"),
    (("Gaia", "স্যাটেলাইট", "মানচিত্র"),             "14_gaia.jpg"),
    (("সৌরজগতের স্থান", "মিল্কিওয়ে গ্যালাক্সির"),   "15_cosmicweb.jpg"),
    (("কৃষ্ণগহ্বরের মিলন", "মহাকর্ষীয় তরঙ্গ"),      "16_merger.jpg"),
    (("বিগ ব্যাং", "প্রসারণ", "সময়রেখা"),          "02_bigbang.jpg"),
    (("দুধসাগর", "রাতের আকাশ", "ছাদ"),            "01_night.jpg"),
]


def _img_path(caption: str) -> str | None:
    """ক্যাপশনে বাংলা কীওয়ার্ড মিলিয়ে ছবি বাছি; না পেলে None।"""
    d = IMG_DIR
    for keys, name in IMG_KEYS:
        if any(k in caption for k in keys):
            f = d / name
            if f.exists():
                return str(f)
    return None


def render_md(book: Book, md: str) -> None:
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()

        if not s:
            i += 1
            continue

        if s.startswith("# "):
            book.h1(s[2:].strip())
        elif s.startswith("## "):
            book.h2(s[3:].strip())
        elif s.startswith("### "):
            book.h3(s[4:].strip())
        elif s.startswith("***") and s.endswith("***"):
            cap = s.strip("*").strip()
            book.image_page(cap, _img_path(cap))
        elif s.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            book.quote_box(block)
            continue
        elif s.startswith("- "):
            book.bullet(s[2:])
        elif re.match(r"^[০-৯]+\.\s", s):
            n, _, rest = s.partition(". ")
            book.num(n + ".", rest)
        elif s.startswith("**") and "**" in s[2:]:
            book.bold_para(s)
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            book.table(rows)
            continue
        else:
            book.para(s)
        i += 1


def build(chapter_files: list[Path], out: Path) -> int:
    _load_covers()
    # প্রচ্ছদ-পাতা
    b = Book()
    b.page.insert_image(pymupdf.Rect(0, 0, PW, PH),
                        filename=str(ROOT / "assets" / "img" / "book-pathshala-cover.jpg"), keep_proportion=False)
    b._new_page()
    # শিরোনাম-পাতা
    put_line(b.page, M_OUT, 150, "মহাবিশ্বের পাঠশালা", 30, NAVY, head=True)
    put_line(b.page, M_OUT, 190, "বৈজ্ঞানিক তথ্য, গবেষণা ও রেফারেন্স", 12, GOLD)
    b._new_page()

    for f in chapter_files:
        render_md(b, f.read_text(encoding="utf-8"))
    return b.save(out)


if __name__ == "__main__":
    files = sorted(CONTENT_DIR.glob("ch*.md")) + [CONTENT_DIR / "appendix.md"]
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "book.pdf"
    n = build(files, out)
    print(f"✓ {out} — {n} পৃষ্ঠা")
