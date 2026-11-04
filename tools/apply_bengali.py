#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""বাংলা অনুবাদ — vivekavani.com থেকে এনে ডেটায় বসানো।

উৎস: vivekavani.com-এর বাংলা ভাষ্য (মূল: রামকৃষ্ণ মঠ/মিশনের বঙ্গানুবাদ)।
প্রতিটি মন্ত্রের আলাদা পোস্ট, প্যাটার্ন:
    শ্বেতাশ্বতর   svu{অধ্যায়}v{মন্ত্র}b
    ছান্দোগ্য     chu{অধ্যায়}c{খণ্ড}v{মন্ত্র}
    কঠ           kau{অধ্যায়}c{খণ্ড}v{মন্ত্র}
    গীতা         b{অধ্যায়}v{শ্লোক}

পোস্টের গঠন (পাঠ-অংশ):
    <দেবনাগরী শ্লোক>
    ব্যাখ্যা—<বাংলা অনুবাদ> …
    সম্বন্ধ—<পরের মন্ত্রের ভূমিকা>   ← বাদ দিতে হবে

ফেচ করা পেজ /tmp/trans/<slug>/<chapter>.txt-এ রাখা হয়, তারপর এই স্ক্রিপ্ট
সেগুলো পার্স করে assets/grantho/data/<slug>/ch<N>.json-এ bn বসায়।

ব্যবহার:
    python3 tools/apply_bengali.py shvetashvatara
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, 'assets', 'grantho', 'data')
CACHE = os.environ.get('TRANS_CACHE', '/tmp/trans')

BN_DIGITS = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
SRC_NAME = 'বঙ্গানুবাদ (রামকৃষ্ণ মঠ ও মিশন)'


def parse_page(text):
    """একটি পোস্টের লেখা → (অনুবাদ, মুদ্রণ-টীকা)।

    ফেচ করা লেখায় এমনি এমনিই «Skip to main content» ইত্যাদি থাকে;
    আমরা «ব্যাখ্যা—» থেকে শুরু করি এবং «সম্বন্ধ—»/«Share this»-এ থামি।
    """
    if not text:
        return '', ''
    t = text
    # নেভিগেশন-আবর্জনা বাদ
    i = t.find('Additional menu')
    if i > -1:
        t = t[i + len('Additional menu'):]

    # ব্যাখ্যা শুরু
    m = re.search(r'ব্যাখ্যা\s*[—-]\s*', t)
    if not m:
        return '', ''
    body = t[m.end():]

    # শেষ কোথায়
    end = len(body)
    for stop in ('Share this on', 'সম্বন্ধ—', 'সম্বন্ধ -'):
        j = body.find(stop)
        if j > -1:
            end = min(end, j)
    body = body[:end].strip()

    body = re.sub(r'\s+', ' ', body)

    # পাদটীকা আলাদা করি: «… (১)» বা «(১)এইভাবে…»
    notes = []
    # শ্লেষ বন্ধনীর পরের ব্যাখ্যা (১) …… এগুলো টীকা হিসেবে রাখি
    for nm in re.finditer(r'\(\s*([০-৯]+)\s*\)\s*([^()]{40,})', body):
        notes.append(f'({nm.group(1)}) ' + nm.group(2).strip())
    main = re.sub(r'\(\s*[০-৯]+\s*\)\s*[^()]{40,}', '', body).strip()
    main = re.sub(r'\s{2,}', ' ', main)
    note = ' '.join(notes).strip()
    return main, note


def fetch_note(base_url, slug, ch, verse):
    """ভবিষ্যতের জন্য: সরাসরি ডাউনলোড (এখন fetch_page দিয়ে করা হয়)।"""
    raise NotImplementedError


def apply(slug, pattern='svu{c}v{v}b', chapters=None, clean_rules=None):
    """ক্যাশ করা ফেচ থেকে bn বসাই।"""
    d = os.path.join(DATA, slug)
    idx = json.load(open(os.path.join(d, 'index.json'), encoding='utf-8'))
    chs = chapters or [c['id'] for c in idx['chapters']]
    filled = 0
    for ch in chs:
        cache_dir = os.path.join(CACHE, slug, str(ch))
        if not os.path.isdir(cache_dir):
            continue
        files = sorted(os.listdir(cache_dir))
        for fn in files:
            if not fn.endswith('.txt'):
                continue
            verse_no = int(re.findall(r'(\d+)', fn)[0])
            raw = open(os.path.join(cache_dir, fn), encoding='utf-8').read()
            bn, note = parse_page(raw)
            if not bn:
                print(f'  ⚠ {slug} {ch}.{verse_no}: অনুবাদ পাওয়া যায়নি')
                continue
            chf = os.path.join(d, f'ch{ch}.json')
            data = json.load(open(chf, encoding='utf-8'))
            for v in data['verses']:
                if v['n'] == verse_no:
                    v['bn'] = bn
                    if note:
                        v['bnNote'] = note
                    v['bnSrc'] = SRC_NAME
                    filled += 1
                    break
            json.dump(data, open(chf, 'w', encoding='utf-8'),
                      ensure_ascii=False, separators=(',', ':'))

    # index.json-এ withBn হালনাগাদ
    total = withbn = 0
    for c in idx['chapters']:
        data = json.load(open(os.path.join(d, f"ch{c['id']}.json"), encoding='utf-8'))
        total += data['count']
        withbn += sum(1 for v in data['verses'] if v.get('bn'))
    idx['withBn'] = withbn
    idx['total'] = total
    idx['bnSrc'] = SRC_NAME
    json.dump(idx, open(os.path.join(d, 'index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'  {slug}: {withbn}/{total} মন্ত্রে বাংলা')
    return withbn, total


if __name__ == '__main__':
    slug = sys.argv[1] if len(sys.argv) > 1 else 'shvetashvatara'
    pat = sys.argv[2] if len(sys.argv) > 2 else 'svu{c}v{v}b'
    apply(slug, pat)
