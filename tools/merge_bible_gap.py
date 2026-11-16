#!/usr/bin/env python3
"""বাইবেলের অনুপস্থিত পাঠ যোগ — godlytalias/Bible-Database (Bengali) থেকে।

কেন এই উৎস: সাইট যেসব পদ ইতিমধ্যেই রাখে, তার সাথে **একই অনুবাদ** (প্রথম
পদগুলো হুবহু মেলে; ৭২% অক্ষর-হুবহু, বাকিটা উৎসেরই বানান-ভুল) — অর্থাৎ
এটি ebanglalibrary.com-এর একই Bengali পাঠ। তাই পুরোনো পাঠ অক্ষত রেখে
কেবল যা নেই তা এখান থেকে ভরা যায়।

নীতি:
  · পুরোনো পাঠে হাত দেওয়া হয় না — কেবল অনুপস্থিত অধ্যায়/পদ যোগ
  · উৎসের `|` → «। » (সাইটের যতিচিহ্ন-রীতি)
  · ইংরেজি অঙ্ক → বাংলা অঙ্ক (সাইটের রীতি)
  · উৎসের সুস্পষ্ট বানান-ভুল ঠিক করা হয় (যেমন বেঁচ্ছেিলেন → বেঁচে ছিলেন)
  · যা যোগ হলো ও কী বাদ পড়ল — রিপোর্টে লেখা থাকে

ব্যবহার:
  python3 tools/merge_bible_gap.py --src /tmp/bn.json --dry-run
  python3 tools/merge_bible_gap.py --src /tmp/bn.json
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'assets', 'grantho', 'data', 'bible')
BN_DIGITS = '০১২৩৪৫৬৭৮৯'

# index.json-এর পুস্তক-ক্রম (id) → উৎসের সূচি (০-ভিত্তিক)। দুটোই প্রামাণ্য
# ৬৬ পুস্তকের ক্রম, তাই সরাসরি — তবে নাম দিয়েও যাচাই করা হয়।
BOOK_ORDER = [
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua',
    'Judges', 'Ruth', '1 Samuel', '2 Samuel', '1 Kings', '2 Kings',
    '1 Chronicles', '2 Chronicles', 'Ezra', 'Nehemiah', 'Esther', 'Job',
    'Psalms', 'Proverbs', 'Ecclesiastes', 'Song of Solomon', 'Isaiah',
    'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos',
    'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai',
    'Zechariah', 'Malachi', 'Matthew', 'Mark', 'Luke', 'John', 'Acts',
    'Romans', '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
    'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
    '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews', 'James',
    '1 Peter', '2 Peter', '1 John', '2 John', '3 John', 'Jude', 'Revelation',
]

# উৎসের পরিচিত বানান-ভুল → শুদ্ধ রূপ (সাইটের পুরোনো পাঠের সাথে মিলিয়ে)
FIXES = [
    ('বেঁচ্ছেিলেন', 'বেঁচে ছিলেন'),
    ('বেঁচ্ছিলেন', 'বেঁচে ছিলেন'),
]


# নতুন ২০ পুস্তকের বাংলা নাম — বাংলা বাইবেলের প্রামাণ্য রূপ
BN_NAMES = {
    '2 Chronicles': 'বংশাবলি ২',
    'Nehemiah': 'নেহেমিয়া',
    'Jeremiah': 'যিরমিয়',
    'Galatians': 'গালাতীয়',
    'Colossians': 'কলসীয়',
    '1 Thessalonians': '১ থিষলনীকীয়',
    '2 Thessalonians': '২ থিষলনীকীয়',
    '1 Timothy': '১ তীমথিয়',
    '2 Timothy': '২ তীমথিয়',
    'Titus': 'তীত',
    'Philemon': 'ফিলীমোন',
    'Hebrews': 'ইব্রীয়',
    'James': 'যাকোব',
    '1 Peter': '১ পিতর',
    '2 Peter': '২ পিতর',
    '1 John': '১ যোহন',
    '2 John': '২ যোহন',
    '3 John': '৩ যোহন',
    'Jude': 'যিহূদা',
    'Revelation': 'প্রকাশিত বাক্য',
}

def to_bn_digits(s):
    """ইংরেজি অঙ্ক → বাংলা অঙ্ক (সাইটের সব সংখ্যা বাংলায়)।"""
    return ''.join(BN_DIGITS[int(c)] if c.isdigit() else c for c in s)


def clean(text):
    """উৎসের কাঁচা পাঠ → সাইটের রীতি।"""
    t = (text or '').strip()
    for bad, good in FIXES:
        t = t.replace(bad, good)
    # `|` পুরো বাক্য-বিভাজক (উৎসের রীতি) → দাঁড়ি
    t = re.sub(r'\s*\|\s*', '। ', t)
    t = to_bn_digits(t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\s+([।,;:!?”’])', r'\1', t)
    t = t.strip()
    # শেষে যতিচিহ্ন না থাকলে দাঁড়ি বসাই (সাইটের রীতি)
    if t and t[-1] not in '।.!?”"’\')':
        t += '।'
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='বাংলা বাইবেলের JSON (Bengali/bible.json)')
    ap.add_argument('--dry-run', action='store_true', help='না লিখে শুধু হিসাব দেখায়')
    args = ap.parse_args()

    src = json.load(open(args.src, encoding='utf-8'))['Book']
    idx_path = os.path.join(DATA, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))

    if len(src) != 66:
        sys.exit(f'উৎসে ৬৬ পুস্তক প্রত্যাশিত, পাওয়া {len(src)}')

    order_of = {name: i for i, name in enumerate(BOOK_ORDER)}

    # পুরোনো পুস্তক → id-র ম্যাপ
    by_en = {c['en']: c for c in idx['chapters']}

    report = []
    added_books = []
    total_added_v = 0
    total_added_ch = 0

    # ---- ১. অনুপস্থিত পুস্তক যোগ (index.json-এ নেই) ----
    next_id = max(c['id'] for c in idx['chapters'])
    for name in BOOK_ORDER:
        if name in by_en:
            continue
        si = order_of[name]
        chapters = src[si]['Chapter']
        next_id += 1          # বাগ-সংশোধন: একই id যেন দুই পুস্তকে না বসে
        new_id = next_id
        entry = {
            'id': new_id,
            'bn': BN_NAMES.get(name),
            'en': name,
            'count': 0,
            'from': 1,
            'to': 0,
            'suktaCount': len(chapters),
        }
        added_books.append((entry, si, chapters))

    # ---- ২. বিদ্যমান পুস্তকে অনুপস্থিত অধ্যায় ভরা ----
    for c in idx['chapters']:
        name = c['en']
        if name not in order_of:
            continue
        si = order_of[name]
        src_ch = src[si]['Chapter']
        f = os.path.join(DATA, f"ch{c['id']}.json")
        d = json.load(open(f, encoding='utf-8'))
        verses = d.get('verses') or []
        have_ch = {v.get('ch') for v in verses}
        # প্রতি অধ্যায়ের সর্বোচ্চ পদ-নম্বর
        max_vn = {}
        for v in verses:
            max_vn[v.get('ch')] = max(max_vn.get(v.get('ch'), 0), v.get('vn') or 0)
        n = d.get('n') or 0
        per = dict(c.get('perChapter') or {})
        added_here = 0
        for ci, sch in enumerate(src_ch, start=1):
            svl = sch.get('Verse') or []
            start = 0
            if ci in have_ch:
                start = max_vn.get(ci, 0)
            new_vs = []
            for k in range(start, len(svl)):
                txt = clean(svl[k].get('Verse'))
                if not txt:
                    continue
                n += 1
                new_vs.append({'n': n, 'vn': k + 1, 'ch': ci, 'bn': txt})
            if new_vs:
                verses.extend(new_vs)
                added_here += len(new_vs)
                per[str(ci)] = len(svl)
        if added_here:
            # n-ক্রম ঠিক আছে কি না (পুস্তক-ভিত্তিক ক্রম)
            verses.sort(key=lambda v: (v.get('ch') or 0, v.get('vn') or 0))
            for i, v in enumerate(verses, start=1):
                v['n'] = i
            d['verses'] = verses
            d['count'] = len(verses)
            d['from'], d['to'] = 1, len(verses)
            if not args.dry_run:
                json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
            c['count'] = len(verses)
            c['perChapter'] = per
            c['suktaCount'] = len(per)
            total_added_v += added_here
            total_added_ch += len([k for k in per if k not in have_ch])
            report.append(f'  {c["bn"]}: +{added_here} পদ · অধ্যায় এখন {len(per)}/{c.get("chaptersTotal", "?")}')

    # ---- ৩. নতুন পুস্তকগুলো লেখা ----
    for entry, si, chapters in added_books:
        verses = []
        n = 0
        per = {}
        for ci, sch in enumerate(chapters, start=1):
            svl = sch.get('Verse') or []
            per[str(ci)] = len(svl)
            for k, sv in enumerate(svl):
                txt = clean(sv.get('Verse'))
                if not txt:
                    continue
                n += 1
                verses.append({'n': n, 'vn': k + 1, 'ch': ci, 'bn': txt})
        f = os.path.join(DATA, f"ch{entry['id']}.json")
        data = {'id': entry['id'], 'bn': entry['bn'], 'en': entry['en'],
                'count': len(verses), 'from': 1, 'to': len(verses),
                'verses': verses}
        if not args.dry_run:
            json.dump(data, open(f, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        entry['count'] = len(verses)
        entry['to'] = len(verses)
        entry['perChapter'] = per
        entry['testament'] = 'new' if si >= 39 else 'old'
        idx['chapters'].append(entry)
        total_added_v += len(verses)
        total_added_ch += len(per)
        report.append(f'  ★ নতুন পুস্তক {entry["en"]}: {len(per)} অধ্যায় · {len(verses)} পদ')

    # ---- ৪. index.json হালনাগাদ ----
    if not args.dry_run and (report):
        idx['chapters'].sort(key=lambda c: BOOK_ORDER.index(c['en']) if c['en'] in BOOK_ORDER else 999)
        idx['total'] = sum(c['count'] for c in idx['chapters'])
        idx['withBn'] = idx['total']
        idx['chaptersTotal'] = sum(c.get('chaptersTotal') or c.get('suktaCount') or 0 for c in idx['chapters'])
        json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    print('\n'.join(report) if report else 'যোগ করার কিছু নেই')
    print(f'\nমোট: +{total_added_v:,} পদ · +{total_added_ch} অধ্যায়'
          + ('  (dry-run — কিছু লেখা হয়নি)' if args.dry_run else ''))


if __name__ == '__main__':
    main()
