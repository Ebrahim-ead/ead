#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""বাইবেলের ১৬টি হারানো পুস্তক ফিরিয়ে আনা (ch51–ch66)।

সমস্যা যা পাওয়া গেল (২০২৬-১১-১৬):
  `tools/merge_bible_gap.py` নতুন পুস্তকের ফাইল (ch51–66.json) লিখেছিল, কিন্তু
  সেগুলোয় `suktas` (অধ্যায়-সীমা), `testament`, `url` ছিল না — কেবল সরল
  `{id,bn,en,count,from,to,verses}`। ফলে:

    · গ্রিডে অধ্যায় দেখানোর উপায় নেই (`suktaCount: 0`)
    · `index.json`-এ এন্ট্রি যোগ হলেও পরের `fetch_bible.py` রানে (build_index)
      ম্যানিফেস্ট ধরে সূচি নতুন করে লেখায় সেগুলো মুছে যায়
    · ফল: পুস্তক ৬৬ → ৫০, আর বাইবেলের শেষ ১৬টি পুস্তক পাঠক পড়তে পারেন না

করণীয়: পদগুলোর `ch` ফিল্ড থেকেই অধ্যায়-সীমা পুনর্গঠন — ডেটা হারায়নি,
কেবল গ্রুপিং-তথ্য। ম্যানিফেস্ট (bible_books.json)-ও ৬৬-এ পূর্ণ করা হয়, নইলে
পরের রানেই আবার ৫০-এ ফিরে যেত।

ব্যবহার:
    python3 tools/repair_bible_books.py            # প্রয়োগ
    python3 tools/repair_bible_books.py --dry-run  # কেবল রিপোর্ট
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'assets', 'grantho', 'data', 'bible')
DBG = os.path.join(ROOT, 'assets', 'grantho', 'data', '_debug')
MANIFEST = os.path.join(DBG, 'bible_books.json')

FULL = list(range(1, 67))          # ৬৬ পুস্তকের ক্যানন-ক্রম


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def dump(p, obj):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def rebuild_groups(verses):
    """পদগুলোর `ch` → suktas (অধ্যায়-সীমা) ও perChapter।

    `from`/`to` = পুস্তকের ভেতরে পদ-ক্রম (n), `vfrom`/`vto` = অধ্যায়ে পদ-নম্বর (vn)।
    উৎসে অধ্যায়-ক্রম এলোমেলো হলে `ch`-এর ক্রমেই সাজানো হয় — পাঠ হারায় না।
    """
    by_ch: dict[int, list[dict]] = {}
    for v in verses:
        ch = v.get('ch')
        if not ch:
            continue
        by_ch.setdefault(int(ch), []).append(v)
    groups, per_ch = [], {}
    for chno in sorted(by_ch):
        vs = sorted(by_ch[chno], key=lambda x: (x.get('vn') or 0))
        if not vs:
            continue
        groups.append({
            'id': chno,
            'from': vs[0]['n'], 'to': vs[-1]['n'],
            'vfrom': vs[0].get('vn') or 1, 'vto': vs[-1].get('vn') or len(vs),
            'verse': len(vs),
        })
        per_ch[str(chno)] = len(vs)
    return groups, per_ch


def main(argv):
    dry = '--dry-run' in argv

    idx_path = os.path.join(DATA, 'index.json')
    idx = load(idx_path)
    have_ids = {c['id'] for c in idx['chapters']}

    manifest = load(MANIFEST) if os.path.exists(MANIFEST) else []
    man_ids = {b['i'] for b in manifest}

    report, fixed_files, added_entries = [], 0, 0

    for bid in FULL:
        fp = os.path.join(DATA, f'ch{bid}.json')
        if not os.path.exists(fp):
            report.append(f'  ⚠ ch{bid}.json নেই — বাদ')
            continue
        d = load(fp)
        verses = d.get('verses') or []
        if not verses:
            report.append(f'  ⚠ ch{bid}.json খালি — বাদ')
            continue

        groups, per_ch = rebuild_groups(verses)
        n_bn = sum(1 for v in verses if v.get('bn'))

        # ০) ``missing`` ফ্ল্যাগ পরে পাঠ যোগ হলেও মুছে যায় না — ফল: গ্রিডে
        #    «পাঠ নেই» দেখায় অথচ পাঠ আছে (যাত্রা ১১ = ১০ পদ, গণনা ৮ = ২৬,
        #    জাখারিয়া ১৩ = ৯)। যেখানে সত্যিই পদ আছে সেখানে ফ্ল্যাগ বাদ দিই।
        old_missing = d.get('missing') or []
        if old_missing:
            cleared = [m for m in old_missing
                       if any(int(v.get('ch') or 0) == int(m) for v in verses)]
            if cleared:
                still = [m for m in old_missing if m not in cleared]
                if still:
                    d['missing'] = still
                else:
                    d.pop('missing', None)
                report.append(f'  ✓ ch{bid} {d.get("bn", "")}: missing {cleared} বাদ '
                              f'(ওই অধ্যায়ে পাঠ আছে)')
                if not dry:
                    dump(fp, d)

        # ১) ফাইল নিজেই পূর্ণ কাঠামোয় আনা (suktas/withBn/suktaCount)
        need = (not d.get('suktas')) or (d.get('suktaCount') != len(groups)) \
            or ('withBn' not in d) or (d.get('withBn') != n_bn)
        if need:
            d['suktas'] = groups
            d['suktaCount'] = len(groups)
            d['groupWord'] = d.get('groupWord') or 'অধ্যায়'
            d['withBn'] = n_bn
            d['count'] = len(verses)
            d['from'], d['to'] = 1, len(verses)
            if d.get('testament') in (None, ''):
                d['testament'] = 'old' if bid <= 46 else 'new'
            if not dry:
                dump(fp, d)
            fixed_files += 1
            report.append(f'  ✓ ch{bid} {d.get("bn", "")}: {len(groups)} অধ্যায় · '
                          f'{len(verses)} পদ — suktas পুনর্গঠিত')

        # ২) index.json-এ এন্ট্রি
        if bid not in have_ids:
            entry = {
                'id': bid,
                'bn': d.get('bn', ''),
                'en': d.get('en', ''),
                'count': len(verses),
                'from': 1, 'to': len(verses),
                'suktaCount': len(groups),
                'testament': d.get('testament') or ('old' if bid <= 46 else 'new'),
                'url': d.get('url', ''),
                'perChapter': per_ch,
            }
            idx['chapters'].append(entry)
            added_entries += 1
            report.append(f'  ★ index-এ যোগ: {entry["bn"]} ({entry["en"]}) — '
                          f'{len(groups)} অধ্যায় · {len(verses)} পদ')
        else:
            # আছে — তবু perChapter/suktaCount ডেটার সাথে মিলিয়ে দিই
            for c in idx['chapters']:
                if c['id'] == bid:
                    if c.get('perChapter') != per_ch:
                        c['perChapter'] = per_ch
                    if c.get('suktaCount') != len(groups):
                        c['suktaCount'] = len(groups)
                    break

        # ৩) ম্যানিফেস্টও পূর্ণ করি — নইলে পরের fetch_bible রানে আবার হারাবে
        if bid not in man_ids:
            manifest.append({
                'i': bid, 'num': bid,
                'bn': d.get('bn', ''), 'en': d.get('en', ''),
                'lesson': d.get('url', ''),
                'ntopics': len(groups),
                'testament': d.get('testament') or ('old' if bid <= 46 else 'new'),
            })
            man_ids.add(bid)

    if not report:
        print('✓ কিছু করার নেই — সব পুস্তক ইতিমধ্যেই পূর্ণ')
        return 0

    # সূচি নতুন করে গোণা
    idx['chapters'].sort(key=lambda c: c['id'])
    idx['total'] = sum(c['count'] for c in idx['chapters'])
    # ⚠ withBn ফাইলের `withBn` ফিল্ড থেকে নেওয়া যাবে না — নতুন লেখা কিছু ফাইলে
    #   (merge_bible_gap-এর) ওই ফিল্ডই নেই। পদগুলো গুনেই বের করি।
    idx['withBn'] = 0
    for c in idx['chapters']:
        fp = os.path.join(DATA, f'ch{c["id"]}.json')
        if os.path.exists(fp):
            idx['withBn'] += sum(1 for v in load(fp).get('verses', []) if v.get('bn'))
    nch = sum(c.get('suktaCount') or 0 for c in idx['chapters'])
    # ⚠ সাইটের রীতি: সংখ্যা বাংলা অঙ্কে (টেস্টে যাচাই হয় — test_bible #১২)
    BN = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
    idx['note'] = (
        'বাংলা বাইবেল — ebanglalibrary.com থেকে সংগৃহীত; অনুপস্থিত পাঠ '
        'godlytalias/Bible-Database (একই বাংলা অনুবাদ) থেকে পূরণ করা হয়েছে। '
        f'{len(idx["chapters"])} পুস্তক, {idx["total"]:,} পদ। উৎসে যে পাঠ পাওয়া '
        'যায়নি তা অনুমান করে বসানো হয়নি (হিসাব _debug/bible_report.txt-এ)।'
    ).translate(BN)

    if not dry:
        dump(idx_path, idx)
        manifest.sort(key=lambda b: b['i'])
        dump(MANIFEST, manifest)

    print('\n'.join(report))
    print()
    print(f'ফাইল ঠিক: {fixed_files} · index-এ নতুন এন্ট্রি: {added_entries}')
    print(f'এখন: {len(idx["chapters"])} পুস্তক · {idx["total"]:,} পদ · '
          f'{nch} অধ্যায় · বাংলাসহ {idx["withBn"]:,}')
    print('  (dry-run — কিছু লেখা হয়নি)' if dry else '  ✓ লেখা হয়েছে')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
