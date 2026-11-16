#!/usr/bin/env python3
"""The New American Bible (2002) — vatican.va/ENG0839 থেকে কাঁচা পাঠ পার্স করে
সাইটের জন্য JSON তৈরি করে।

কাঁচা পাঠ আসে FreeNAB-এর স্ক্র্যাপ থেকে (public/nabre_books/<Book>/<Book>_<ch>.txt),
যা হুবহু https://www.vatican.va/archive/ENG0839/_INDEX.HTM থেকে নামানো — তাই
এটাই ব্যবহারকারীর চাওয়া উৎস।

ফাইল-গঠন (উদাহরণ):
    1
    [1]
     In the beginning, when God created the heavens
    and the earth,
    2
    [2]
     the earth was a formless wasteland, ...
                     ← পদ শেষ
    1
    [
    ⇒
     1:1-
    ⇒
     2:4a] This section introduces ...
                     ← পাদটীকা ব্লক শুরু (নম্বর = উপরের [n])

নীতি:
  ▸ পাঠ বদলানো বা অনুমান করা হয় না — শুধু শুরু-শেষের সাদা জায়গা ঠিক করা হয়;
  ▸ লাইন-ভাঙা জোড়া লাগে: «শব্দ» + «শব্দ» → «শব্দ শব্দ», কিন্তু before a
    closing punctuation হলে স্পেস বাদ («earth ,» নয় → «earth,»);
  ▸ [n] চিহ্ন পাঠ থেকে সরিয়ে সেই নম্বরের টীকা আলাদা তালিকায় রাখা হয়;
  ▸ অন্যায়ভাবে বড় কোনো অংশ ছাঁটা হয় না — ত্রুটি হলে রিপোর্টে যায়।

ব্যবহার:
    python3 tools/parse_nab.py --src /tmp/FreeNAB/public/nabre_books \
        --out assets/grantho/data/bible/english
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- বইয়ের তালিকা
# সাইটে বাংলার ৬৬ পুস্তক (প্রোটেস্ট্যান্ট ক্রম)। NAB-এর বাংলা-অনুপস্থিত ৭টি
# ক্যাথলিক পুস্তকও (Tobit, Judith, Wisdom, Sirach, Baruch, 1–2 Maccabees)
# অন্তর্ভুক্ত, কারণ ব্যবহারকারী «সবকটা» চেয়েছেন। জায়গা: বাংলা ক্রমে বসিয়ে
# শেষে অতিরিক্ত ৭টি — এতে বাংলা-পাতার সাথে নম্বর মেলে।
#
# (id, bn, en, folder, chapters)
BOOKS = [
    (1, "আদিপুস্তক", "Genesis", "Genesis", 50),
    (2, "যাত্রাপুস্তক", "Exodus", "Exodus", 40),
    (3, "লেবীয় পুস্তক", "Leviticus", "Leviticus", 27),
    (4, "গণনা পুস্তক", "Numbers", "Numbers", 36),
    (5, "দ্বিতীয় বিবরণ", "Deuteronomy", "Deuteronomy", 34),
    (6, "যোশুয়া", "Joshua", "Joshua", 24),
    (7, "বিচারকচরিত", "Judges", "Judges", 21),
    (8, "রুথ", "Ruth", "Ruth", 4),
    (9, "সামুয়েল ১", "1 Samuel", "1_Samuel", 31),
    (10, "সামুয়েল ২", "2 Samuel", "2_Samuel", 24),
    (11, "রাজাবলি ১", "1 Kings", "1_Kings", 22),
    (12, "রাজাবলি ২", "2 Kings", "2_Kings", 25),
    (13, "বংশাবলি ১", "1 Chronicles", "1_Chronicles", 29),
    (14, "বংশাবলি ২", "2 Chronicles", "2_Chronicles", 36),
    (15, "এজরা", "Ezra", "Ezra", 10),
    (16, "নেহেমিয়া", "Nehemiah", "Nehemiah", 13),
    (17, "এস্থার", "Esther", "Esther", 16),      # NAB: 1–10 + A–F → 11–16
    (18, "যোব", "Job", "Job", 42),
    (19, "সামসঙ্গীত", "Psalms", "Psalms", 150),
    (20, "প্রবচন", "Proverbs", "Proverbs", 31),
    (21, "উপদেশক", "Ecclesiastes", "Ecclesiastes", 12),
    (22, "পরম গীত", "Song of Songs", "The_Song_of_Songs", 8),
    (23, "ইসাইয়া", "Isaiah", "Isaiah", 66),
    (24, "যিরমিয়", "Jeremiah", "Jeremiah", 52),
    (25, "বিলাপ-গাথা", "Lamentations", "Lamentations", 5),
    (26, "এজেকিয়েল", "Ezekiel", "Ezekiel", 48),
    (27, "দানিয়েল", "Daniel", "Daniel", 14),     # NAB: 14 অধ্যায়
    (28, "হোসেয়া", "Hosea", "Hosea", 14),
    (29, "যোয়েল", "Joel", "Joel", 4),           # NAB: ৪ অধ্যায়
    (30, "আমোস", "Amos", "Amos", 9),
    (31, "ওবাদিয়া", "Obadiah", "Obadiah", 1),
    (32, "যোনা", "Jonah", "Jonah", 4),
    (33, "মিখা", "Micah", "Micah", 7),
    (34, "নাহুম", "Nahum", "Nahum", 3),
    (35, "হাবাকুক", "Habakkuk", "Habakkuk", 3),
    (36, "জেফানিয়া", "Zephaniah", "Zephaniah", 3),
    (37, "হগয়", "Haggai", "Haggai", 2),
    (38, "জাখারিয়া", "Zechariah", "Zechariah", 14),
    (39, "মালাখি", "Malachi", "Malachi", 3),
    (40, "মথি", "Matthew", "Matthew", 28),
    (41, "মার্ক", "Mark", "Mark", 16),
    (42, "লুক", "Luke", "Luke", 24),
    (43, "যোহন", "John", "John", 21),
    (44, "শিষ্যচরিত", "Acts", "Acts", 28),
    (45, "রোমীয়", "Romans", "Romans", 16),
    (46, "করিন্থীয় ১", "1 Corinthians", "1_Corinthians", 16),
    (47, "করিন্থীয় ২", "2 Corinthians", "2_Corinthians", 13),
    (48, "গালাতীয়", "Galatians", "Galatians", 6),
    (49, "এফেসীয়", "Ephesians", "Ephesians", 6),
    (50, "ফিলিপ্পীয়", "Philippians", "Philippians", 4),
    (51, "কলসীয়", "Colossians", "Colossians", 4),
    (52, "১ থিষলনীকীয়", "1 Thessalonians", "1_Thessalonians", 5),
    (53, "২ থিষলনীকীয়", "2 Thessalonians", "2_Thessalonians", 3),
    (54, "১ তীমথিয়", "1 Timothy", "1_Timothy", 6),
    (55, "২ তীমথিয়", "2 Timothy", "2_Timothy", 4),
    (56, "তীত", "Titus", "Titus", 3),
    (57, "ফিলীমোন", "Philemon", "Philemon", 1),
    (58, "ইব্রীয়", "Hebrews", "Hebrews", 13),
    (59, "যাকোব", "James", "James", 5),
    (60, "১ পিতর", "1 Peter", "1_Peter", 5),
    (61, "২ পিতর", "2 Peter", "2_Peter", 3),
    (62, "১ যোহন", "1 John", "1_John", 5),
    (63, "২ যোহন", "2 John", "2_John", 1),
    (64, "৩ যোহন", "3 John", "3_John", 1),
    (65, "যিহূদা", "Jude", "Jude", 1),
    (66, "প্রকাশিত বাক্য", "Revelation", "Revelation", 22),
    # ── ক্যাথলিক (ডিউটেরোক্যানোনিক্যাল) — বাংলা পাঠ নেই, শুধু ইংরেজি ──
    (67, "তোবিত", "Tobit", "Tobit", 14),
    (68, "যুদিথ", "Judith", "Judith", 16),
    (69, "প্রজ্ঞা", "Wisdom", "The_Book_of_Wisdom", 19),
    (70, "সিরাখ", "Sirach", "Sirach", 51),
    (71, "বারুক", "Baruch", "Baruch", 6),
    (72, "মাক্কাবি ১", "1 Maccabees", "1_Maccabees", 16),
    (73, "মাক্কাবি ২", "2 Maccabees", "2_Maccabees", 15),
]

# যেসব পুস্তকে ফাইলের নামকরণ স্বাভাবিক নিয়মে নয়
FILE_OVERRIDE = {
    "2_John": "2_John_2 John.txt",
    "3_John": "3_John_3 John.txt",
    "Jude":   "Jude_Jude.txt",
    "Obadiah": "Obadiah_Obadiah.txt",
    "Philemon": "Philemon_Philemon.txt",
}
# Esther-এর গ্রিক-সংযোজন A–F অধ্যায় ১১–১৬ হিসেবে বসে
ESTHER_EXTRA = ["A", "B", "C", "D", "E", "F"]

SRC_NAME = "The New American Bible — vatican.va (ENG0839, 2002)"

# পদ-নম্বর লাইন: শুধু সংখ্যা (ঐচ্ছিক ইংরেজি অক্ষর-প্রত্যয়, «1a», «13b» ইত্যাদি)
VERSE_NO = re.compile(r"^(\d{1,3})\s*([a-zA-Z])?$")
# পদ-শুরুর টীকা-চিহ্ন: একা «[3]» লাইন
MARK_ONLY = re.compile(r"^\[\s*(\d{1,3})\s*\]$")
# লেখার ভেতরের টীকা-চিহ্ন
INLINE_MARK = re.compile(r"\[\s*(\d{1,3})\s*\]")
# পাদটীকা-অংশের শুরু: সংখ্যা-লাইন, তারপর «[n]», «[10-14]», «[» ইত্যাদি
FOOT_START = re.compile(r"^\[\s*(?:\d+(?:\s*[-–]\s*\d+)?[a-z]?)?\s*")
# পাদটীকা-ব্লকের শুরু: «1» লাইন, তারপর «[»
# পাঠের বাইরের পদের তীর-লিঙ্ক
ARROW = "\u21d2"
# ফাঁকা/আবর্জনা
DROP_PUNCT = {"-", "–", "—", "*", "* * *", "|"}


def fix_spacing(s):
    """লাইন-জোড়ার পর সাদা জায়গা ঠিক করে।

    «earth ,» → «earth,»   «( Psalm 33:7» → «(Psalm 33:7»
    """
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:!?)\]])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    # — চিহ্নের দুই পাশে ফাঁকা রাখা ভালো দেখায় (NAB-এর অভ্যাস)
    s = re.sub(r"\s*—\s*", " — ", s)
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


# পাঠের ভেতরের চিহ্ন — একা লাইনে: «[3]»
MARKER_ONLY = re.compile(r"^\[\s*(\d{1,3}(?:\s*[-–,]\s*\d+)*)\s*[a-z]?\s*\]$")
# টীকা-শুরুর লাইন — মোড়ক + **সাথে লেখা**: «[23] There is…» বা «[10-14] Rises:…»
# অধ্যায়-স্তরের ব্লক-ভূমিকা: «[1:1- 9:34] …» বা «[27:13] …» — পদ-নম্বরের
# বদলে অধ্যায়:পদ ফরম্যাট; সাধারণত পাঠের শুরুতেই বাক্যের মাঝে লেগে থাকে
# (উৎসে রেফারেন্স লাইনে ভাঙা থাকে — «[1:1-» / « 2:4a]» — তাই ফাঁকা শিথিল)
BLOCK_NOTE = re.compile(
    r"\[\s*\d{1,3}\s*:\s*\d{1,3}(?:\s*[-–]\s*\d{1,3}(?:\s*[:-]\s*\d{1,3}[a-z]?)?)?\s*\]"
    r"|\[\s*\d{1,3}\s*[-–]\s*\d{1,3}\s*:\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?\s*\]"
)
# মোড়কের আগে কখনো ভুল কোটেশন-চিহ্ন আটকে যায় («"[1-2] Unlike…» — উৎসের বাগ)
NOTE_LINE = re.compile(r"^[\"\u201c\u2018']?\s*\[\s*(\d{1,3}(?:\s*[-–,]\s*\d+)*)\s*[a-z]?\s*\]\s*(.+)$")


def parse_chapter(path, ch_no=0):
    """একটি অধ্যায়-ফাইল পড়ে (verses, notes) ফেরত দেয়।

    vatican.va-র IntraText থেকে নামানো ফাইলের গঠন দুই ভাগে:

      ▸ **পদ-অংশ**  — লাইন-ভাঙা পদ, প্রতিটির আগে একা সংখ্যা (১, ২, ৩…)
                     মাঝে মাঝে পাঠের ভেতরের চিহ্ন «[3]» একা এক লাইনে;
      ▸ **টীকা-অংশ** — শুরু হয় এমন সংখ্যা দিয়ে যার পরের লাইনে মোড়ক
                     «[n]» **লেখাসহ** («[23] There is a play…»)।

    গুরুত্বপূর্ণ: টীকা-অংশের শুরুতে যে সংখ্যাটি থাকে সেটি **টীকার ক্রম-নম্বর**,
    পদের নম্বর নয় (Psalms ১-এ পদ ৬-এর পরে আসে «1 [Psalm 1] A preface…»)।
    যে নম্বরটি আসল পদ-রেফারেন্স তা মোড়কের ভেতরে — সেটাই notes[i].ref-এ রাখি,
    যাতে পাঠক ঠিক সেই পদের নিচে টীকা দেখাতে পারে।
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in re.split(r"\r\r\n|\r\n|\r|\n", raw)]
    lines = [ln for ln in lines if ln]
    # «Chapter / 27», «2 / Kings / 1» — পুস্তক-অধ্যায়ের নিজের শিরোনাম
    while lines and lines[0].lower() in ("chapter", "psalm", "psalms"):
        lines.pop(0)

    n = len(lines)

    def bare(line):
        return bool(re.fullmatch(r"\d{1,3}", line))

    def is_note(line):
        """সত্যিকারের টীকা-লাইন: মোড়ক «[n]» + লেখা (২+ অক্ষর)।

        «[3]» একা = পাঠের ভেতরের চিহ্ন (2 Samuel 22-এ প্রতি পদেই এমন),
        টীকা নয়।"""
        m = NOTE_LINE.match(line)
        return bool(m) and len(m.group(2).strip()) >= 2

    # ── টীকা-অংশ কোথায় শুরু? ──
    # নির্ভরযোগ্য গঠন-লক্ষণ: টীকা-অংশে সংখ্যার পরের লাইন «[» দিয়ে শুরু
    # («[23] There is…», «[Psalm 1] A preface…»)। প্রথম কোনো সংখ্যা — যার
    # পরের লাইন এমন, এবং যার পর থেকে বেশিরভাগ সংখ্যার পাশেই «[» — সেখানেই
    # টীকা-অংশ শুরু। উৎসের এলোমেলো পদ-ক্রম (Ezekiel 11-এ ২২,২৩, তারপর ১)
    # এতে কোনো বাধা নয়, কারণ শর্ত সংখ্যার ক্রমের উপর নির্ভর করে না।
    def bracket_follows(k):
        return k + 1 < n and lines[k + 1].startswith("[") and len(lines[k + 1]) > 4

    foot_start = n
    for cand in range(1, n):
        if not (bare(lines[cand]) and bracket_follows(cand)):
            continue
        nums = [k for k in range(cand, n) if bare(lines[k])]
        if not nums:
            continue
        hit = sum(1 for k in nums if bracket_follows(k))
        if hit / len(nums) >= 0.5:
            foot_start = cand
            break

    # ── ১) পদ-অংশ ──
    verses = {}
    order = []
    cur = None
    buf = []
    block_notes = []          # অধ্যায়-স্তরের ব্লক-ভূমিকা (পাঠ নয়, টীকা)

    def flush_verse():
        nonlocal buf, cur
        if cur is None:
            buf = []
            return
        txt = fix_spacing(" ".join(buf))
        txt = INLINE_MARK.sub("", txt)
        # অধ্যায়-স্তরের ব্লক-ভূমিকা পাঠ থেকে সরিয়ে আলাদা রাখি
        # (মোড়ক «[1:1- 2:4a]» + তার পরের ব্যাখ্যাবাক্য — পরের মোড়ক/শেষ পর্যন্ত)
        if BLOCK_NOTE.search(txt):
            bm = BLOCK_NOTE.search(txt)
            tail = txt[bm.end():]
            nxt = re.search(r"\[\s*\d", tail)
            body = (tail[:nxt.start()] if nxt else tail).strip()
            if body:
                block_notes.append({"ref": "", "text": fix_spacing(body)})
            txt = (txt[:bm.start()] + " " + (tail[nxt.start():] if nxt else "")).strip()
        txt = fix_spacing(txt)
        txt = re.sub(r"\s*\[\s*\]\s*", " ", txt)
        txt = fix_spacing(txt)
        if txt:
            if cur in verses:
                verses[cur] = fix_spacing(verses[cur] + " " + txt)
            else:
                verses[cur] = txt
                order.append(cur)
        buf = []

    i = 0
    while i < foot_start:
        ln = lines[i]
        if ln in DROP_PUNCT or ln.startswith("Click here") or ln == ARROW:
            i += 1
            continue
        if bare(ln):
            flush_verse()
            cur = str(int(ln))
            i += 1
            # পদের ঠিক পরের একা «[n]» চিহ্ন — বাদ
            while i < foot_start and MARKER_ONLY.match(lines[i]):
                i += 1
            continue
        if MARKER_ONLY.match(ln):
            i += 1              # পাঠের ভেতরের চিহ্ন, আলাদা লাইনে
            continue
        if cur is not None:
            buf.append(ln)
        i += 1
    flush_verse()

    # ── ২) টীকা-অংশ ──
    notes = []                  # [{"ref": "1", "text": "…"}]
    cur_ref = None
    nbuf = []

    def flush_note():
        nonlocal nbuf, cur_ref
        if not nbuf:
            nbuf = []
            return
        t = fix_spacing(" ".join(nbuf))
        t = t.replace(ARROW, " ")
        t = re.sub(r'^["\u201c\u2018\']?\s*\[\s*(?:\d+(?:\s*[-–,]\s*\d+)*\s*[a-z]?)?\s*\]\s*', "", t)
        t = fix_spacing(t)
        if t and len(t) > 2:
            notes.append({"ref": cur_ref or "", "text": t})
        nbuf = []

    i = foot_start
    while i < n:
        ln = lines[i]
        if ln in DROP_PUNCT or ln == ARROW or ln.startswith("Click here"):
            i += 1
            continue
        if bare(ln):
            # টীকা-অংশে একা সংখ্যা = নতুন টীকা। কিন্তু যদি আগের সংখ্যার পরে
            # মোড়ক এখনো খোলা («[» একা লাইনে) — সেটা একই টীকার ভেতরের
            # রেফারেন্স «⇒ 1 / Chron 19:6-9»; তখন সংখ্যাটাকে পাঠে রাখি।
            if nbuf and nbuf[-1].strip() in ("[", ""):
                nbuf.append(ln)
                i += 1
                continue
            flush_note()
            nxt = lines[i + 1] if i + 1 < n else ""
            if nxt.strip() == "[":
                cur_ref = None
                nbuf = []
                i += 1
                continue
            m = NOTE_LINE.match(nxt) if is_note(nxt) else None
            if m:
                cur_ref = m.group(1)
                nbuf = [m.group(2)] if m.group(2).strip() else []
                i += 2
                continue
            if not is_note(nxt) and nxt and not nxt.startswith("["):
                cur_ref = None
                nbuf = [nxt]          # মোড়কহীন টীকা (Psalms-এর ব্লক-ভূমিকা)
                i += 2
                continue
            cur_ref = None
            i += 1
            continue
        m = NOTE_LINE.match(ln) if is_note(ln) else None
        if m and not nbuf:
            cur_ref = m.group(1)
            nbuf = [m.group(2)]
            i += 1
            continue
        if nbuf:
            nbuf.append(ln)
        i += 1
    flush_note()

    return verses, notes + block_notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/tmp/FreeNAB/public/nabre_books")
    ap.add_argument("--out", default="assets/grantho/data/bible/english")
    ap.add_argument("--only", default="", help="শুধু এই id-গুলো (কমা দিয়ে)")
    ap.add_argument("--report", default="assets/grantho/data/_debug/nab_parse.txt")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    only = {int(x) for x in args.only.split(",") if x.strip().isdigit()}

    chapters_index = []      # [{id, bn, en, chapters:[{n, verses, notes, file}]}]
    report = []
    total_v = total_n = 0
    problems = []

    for bid, bn, en, folder, nch in BOOKS:
        if only and bid not in only:
            continue
        fdir = src / folder
        if not fdir.is_dir():
            problems.append(f"✗ {en}: ফোল্ডার নেই ({fdir})")
            continue

        ch_entries = []
        for c in range(1, nch + 1):
            if folder in FILE_OVERRIDE:
                f = fdir / FILE_OVERRIDE[folder]
            elif folder == "The_Song_of_Songs":
                f = fdir / f"The_Song_of_Songs_{c}.txt"
            elif folder == "Esther" and c > 10:
                f = fdir / f"Esther_{ESTHER_EXTRA[c - 11]}.txt"
            else:
                f = fdir / f"{folder}_{c}.txt"
            if not f.is_file():
                problems.append(f"✗ {en} {c}: ফাইল নেই ({f.name})")
                continue
            verses, notes = parse_chapter(f, c)
            if not verses:
                problems.append(f"✗ {en} {c}: কোনো পদ পাওয়া যায়নি")
                continue

            # পদ-ক্রম যাচাই: ১ থেকে শুরু, ক্রমিক?
            nums = [int(x) for x in verses]
            exp = list(range(1, len(nums) + 1))
            if sorted(nums) != exp:
                got = sorted(nums)
                miss = [x for x in range(1, got[-1] + 1) if x not in set(got)]
                if miss:
                    problems.append(f"! {en} {c}: অনুপস্থিত পদ {miss[:8]}")
            # উৎসে এলোমেলো ক্রম থাকলে সাজিয়ে নিই (পাঠ অপরিবর্তিত)
            verses = {k: verses[k] for k in sorted(verses, key=int)}

            data = {
                "id": bid,
                "book": en,
                "bookBn": bn,
                "ch": c,
                "src": SRC_NAME,
                "verses": verses,
                "notes": notes,
            }
            fn = f"ch{bid}_{c}.json"
            (out / fn).write_text(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            ch_entries.append({
                "n": c,
                "count": len(verses),
                "notes": len(notes),
                "file": fn,
            })
            total_v += len(verses)
            total_n += len(notes)

        chapters_index.append({
            "id": bid, "bn": bn, "en": en,
            "chapters": ch_entries,
            "total": sum(x["count"] for x in ch_entries),
            "notes": sum(x["notes"] for x in ch_entries),
        })
        report.append(f"{bid:>2} {en:<20} {len(ch_entries):>3} ch · "
                      f"{sum(x['count'] for x in ch_entries):>5} v · "
                      f"{sum(x['notes'] for x in ch_entries):>4} notes")
        print(report[-1], flush=True)

    # ── ম্যানিফেস্ট (assets/grantho/data/bible/english/index.json) ──
    # রিডার (assets/grantho/grantho.js) ঠিক এই আকারটাই পড়ে:
    #   chapters[]      : {id, bn, en, count, suktaCount, perChapter, testament}
    #   প্রতিটি অধ্যায়ের পাঠ: ch<bookId>_<chNo>.json
    manifest = []
    for b in chapters_index:
        manifest.append({
            "id": b["id"],
            "bn": b["bn"],
            "en": b["en"],
            "count": b["total"],
            "suktaCount": len(b["chapters"]),
            "chaptersTotal": len(b["chapters"]),
            "testament": "old" if b["id"] <= 46 else "new",
            "notes": b["notes"],
            # রিডার ঠিক এই তালিকাটাই পড়ে (নম্বর, পদ-সংখ্যা, টীকা-সংখ্যা)
            "chapters": b["chapters"],
        })

    idx = {
        "slug": "bible-english",
        "bn": "ইংরেজি বাইবেল",
        "en": "English Bible",
        "src": SRC_NAME,
        "license": "Copyright © Libreria Editrice Vaticana — "
                   "https://www.vatican.va/archive/ENG0839/_INDEX.HTM",
        "verseWord": "পদ",
        "chword": "পুস্তক",
        "groupWord": "অধ্যায়",
        "chapters": manifest,
        "total": total_v,
        "totalBooks": len(manifest),
        "totalChapters": sum(len(b["chapters"]) for b in chapters_index),
        "totalNotes": total_n,
        "version": 1,
    }
    (out / "index.json").write_text(
        json.dumps(idx, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    rp = Path(args.report)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(
        "\n".join(report) + "\n\n" + "\n".join(problems) + "\n", encoding="utf-8"
    )

    print(f"\nপুস্তক {idx['totalBooks']} · অধ্যায় {idx['totalChapters']} · "
          f"পদ {total_v:,} · টীকা {total_n:,}")
    if problems:
        print(f"সমস্যা {len(problems)} — {rp}")
        for p in problems[:15]:
            print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
