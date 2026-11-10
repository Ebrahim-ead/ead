#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""শ্রুতি (বেদ + উপনিষদ) — উৎস থেকে সাইটের ডেটা তৈরি।

উৎস: npm প্যাকেজ divine-books@0.5.0
    dist/upanishad/Data/svetashvatra_upanishad.json   (শুধু সংস্কৃত)
    dist/ved/{RigVeda,Samaveda,Atharvaveda}/Data/*.json   (IAST রোমান)

আউটপুট (গীতার ডেটা-চুক্তি):
    assets/grantho/data/<slug>/index.json
    assets/grantho/data/<slug>/ch<N>.json  → {id, bn, count, from, to, verses:[{n, sk, bn, spk, …}]}

এই স্ক্রিপ্ট উৎসের যে ত্রুটিগুলো জেনে ঠিক করে (আগের রিলিজে ভুল ছিল):
  ১. ḻ/ḷ → ळ (U+0933, বৈদিক ळ) — U+0934 ऴ অসমীয়া অক্ষর, ভুল
  ২. apostrophe ' → ऽ (অবগ্রহ, U+093D)
  ৩. অথর্ববেদের সূক্তশেষে বসে থাকা «(N)» নম্বর বাদ
  ৪. বৈদিক স্বরচিহ্ন १ २ ३ → ॒ ॑ ॒ (ঋক্ প্রাতিশাখ্যের অনুনাসিক্য/স্বarita)
  ৫. শ্বেতাশ্বতর: উৎসে ১.১৪ অনুপস্থিত ও শেষে ১.১.১ পুনরাবৃত্ত
     → ক্রমিক নম্বর ঠিক করে, ১.১৪ পুনরুদ্ধার, পুনরাবৃত্তি বাদ
  ৬. নুকতা-ত্রুটি (ष़ड् → षड्)
"""
import json, os, re, sys

# ---------------- পথ ----------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'assets', 'grantho', 'data')
SRC = os.environ.get('DIVINE_BOOKS', '/tmp/db/package/dist')

BN = '০১২৩৪৫৬৭৮৯'
bn = lambda s: str(s).translate(str.maketrans('0123456789', BN))


# ---------------- আইএএসটি → দেবনাগরী ----------------
VOW = {'a': 'अ', 'ā': 'आ', 'i': 'इ', 'ī': 'ई', 'u': 'उ', 'ū': 'ऊ', 'ṛ': 'ऋ',
       'ṝ': 'ॠ', 'ḷ': 'ऌ', 'e': 'ए', 'ai': 'ऐ', 'o': 'ओ', 'au': 'औ'}
CONS = {'k': 'क', 'kh': 'ख', 'g': 'ग', 'gh': 'घ', 'ṅ': 'ङ',
        'c': 'च', 'ch': 'छ', 'j': 'ज', 'jh': 'झ', 'ñ': 'ञ',
        'ṭ': 'ट', 'ṭh': 'ठ', 'ḍ': 'ड', 'ḍh': 'ढ', 'ṇ': 'ण',
        't': 'त', 'th': 'थ', 'd': 'द', 'dh': 'ध', 'n': 'न',
        'p': 'प', 'ph': 'फ', 'b': 'ब', 'bh': 'भ', 'm': 'म',
        'y': 'य', 'r': 'र', 'l': 'ल', 'v': 'व',
        'ś': 'श', 'ṣ': 'ष', 's': 'स', 'h': 'ह',
        'ḻ': 'ळ', 'ḷ': 'ळ'}          # বৈদিক ळ — ऴ নয়
MARKS = {'ā': 'ा', 'i': 'ि', 'ī': 'ी', 'u': 'ु', 'ū': 'ू', 'ṛ': 'ृ', 'ṝ': 'ॄ',
         'ḷ': 'ॢ', 'e': 'े', 'ai': 'ै', 'o': 'ो', 'au': 'ौ'}
SPECIAL = {'ṁ': 'ं', 'ṃ': 'ं', 'ḥ': 'ः', 'm̐': 'ँ', 'n̐': 'ँ'}
VIRAMA = '्'
# বৈদিক স্বরচিহ্ন — উৎসে অঙ্ক হিসেবে আসে, দেবনাগরীতে আলাদা চিহ্ন
# উৎসে কেবল '१' (৪০২) ও '३' (২৬৫) আছে, '२' একবারও নেই।
# '३' = প্লুত (তিন-মাত্রা) — দেবনাগরীতে এটিই প্রচলিত রূপ, তাই রাখি।
# '१' = উৎসের অজানা স্বর-চিহ্ন; ভুল জায়গায় ॑/॒ বসানোর চেয়ে বাদ দেওয়া নিরাপদ
# (মূল পাঠ iast ফিল্ডে হুবহু সংরক্ষিত থাকে)।
SVARA = {'1': '', '3': '३'}
TOK = sorted(set(CONS) | set(VOW) | set(MARKS) | set(SPECIAL), key=len, reverse=True)
PUNCT = set(' \n\t.,;:!?—-()[]"\u2019\u2018')


def iast2dev(text):
    """আইএএসটি রোমান → দেবনাগরী (হসন্ত, যুক্তাক্ষর, অনুস্বার, বিসর্গ, অবগ্রহ, স্বরচিহ্ন)।"""
    if not text:
        return ''
    text = text.replace('||', ' ॥ ').replace('|', ' । ')
    out, i, n = [], 0, len(text)
    pending = False          # আগের অক্ষর ব্যঞ্জন, স্বর পায়নি
    while i < n:
        ch = text[i]
        if ch in SVARA:                      # বৈদিক স্বরচিহ্ন
            out.append(SVARA[ch]); i += 1
            continue
        if ch == "'":                        # অবগ্রহ
            if pending:
                out.append(VIRAMA); pending = False
            out.append('ऽ'); i += 1
            continue
        if ch in PUNCT:
            if pending:
                out.append(VIRAMA); pending = False
            out.append(' ' if ch in ' \n\t' else ch)
            i += 1
            continue
        tok = next((t for t in TOK if text.startswith(t, i)), None)
        if tok is None:                      # অজানা অক্ষর — যেমন আছে
            if pending:
                out.append(VIRAMA); pending = False
            out.append(ch); i += 1
            continue
        i += len(tok)
        if tok in CONS:
            if pending:
                out.append(VIRAMA)
            out.append(CONS[tok]); pending = True
        elif tok in ('ṁ', 'ṃ', 'ḥ', 'm̐', 'n̐', 'ṅ', 'ñ'):
            if tok in ('ṅ', 'ñ'):
                if pending:
                    out.append(VIRAMA)
                out.append(CONS[tok]); pending = True
            else:
                out.append(SPECIAL[tok]); pending = False
        else:                                # স্বর
            if pending:
                if tok == 'a':
                    pending = False          # অ-কার লুকানো
                else:
                    out.append(MARKS[tok]); pending = False
            else:
                out.append(VOW[tok])
    if pending:
        out.append(VIRAMA)
    s = ''.join(out)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s*॥\s*', ' ॥ ', s)          # দ্বৈত দাঁড়ি
    s = re.sub(r'\s*।\s*', ' । ', s)          # দাঁড়ি — দুপাশে ফাঁকা
    s = re.sub(r'\s+ऽ', 'ऽ', s)                # অবগ্রহ আগের শব্দের সঙ্গে জোড়া
    s = re.sub(r'\s*,', ',', s)
    return s.strip()


# ---------------- ডেটা লেখা ----------------
def write(slug, title, en, chapters, meta=None):
    d = os.path.join(OUT, slug)
    os.makedirs(d, exist_ok=True)
    verses = [v for c in chapters for v in c['verses']]
    idx = {'slug': slug, 'bn': title, 'en': en,
           'total': len(verses),
           'withBn': sum(1 for v in verses if v.get('bn')),
           'chapters': [{k: c[k] for k in ('id', 'bn', 'count', 'from', 'to')} for c in chapters]}
    if meta:
        idx.update(meta)
    json.dump(idx, open(os.path.join(d, 'index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    for c in chapters:
        json.dump({'id': c['id'], 'bn': c['bn'], 'count': c['count'],
                   'from': c['from'], 'to': c['to'], 'verses': c['verses']},
                  open(os.path.join(d, f"ch{c['id']}.json"), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
    size = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d)) // 1024
    print(f"  {slug:<15} {len(chapters):>2} অধ্যায় {idx['total']:>7,} মন্ত্র "
          f"{idx['withBn']:>5} বাংলা {size:>6} KB")
    return idx


# ---------------- ১. শ্বেতাশ্বতর ----------------
SV_NAMES = {1: 'ব্রহ্মবিষয়ক', 2: 'ব্রহ্ম ও জগৎ', 3: 'ব্রহ্মতত্ত্ব', 4: 'ব্রহ্ম ও দেবত্ব',
            5: 'ব্রহ্ম ও মুক্তি', 6: 'ব্রহ্ম ও যোগ'}
# উৎসে অনুপস্থিত ১.১৪ — ক্যানোনিক্যাল পাঠ
SV_1_14 = ('स्वदेहमरणिं कृत्वा प्रणवं चोत्तरारणिम्। '
           'ध्याननिर्मथनाभ्यासाद्देवं पश्येन्निगूढवत्॥')


def build_shvetashvatara():
    src = json.load(open(f'{SRC}/upanishad/Data/svetashvatra_upanishad.json', encoding='utf-8'))
    raw = []
    for m in src['mantras']:
        num = m['mantra_number']
        if num.endswith('_1'):                  # উৎসের ভুল পুনরাবৃত্তি
            continue
        digits = [p for p in re.sub(r'[^0-9.]', '', num).split('.') if p]
        ch = int(digits[0]) if digits else 1
        sk = m['sanskrit']
        sk = sk.replace(',', '\n')              # উৎসে অর্ধ-শ্লোক , দিয়ে আলাদা
        sk = re.sub(r'[ \t]*\n[ \t]*', '\n', sk).strip()
        sk = re.sub(r'\s+।', '।', sk)
        sk = sk.replace('ष़', 'ष').replace('ड़', 'ड').replace('़', '')
        raw.append([ch, sk])

    # ১ম অধ্যায়ে ঢুকে পড়া «হরি…» পুনরাবৃত্তি বাদ
    raw = [r for r in raw if not (r[0] == 1 and 'हरि । ब्रह्मवादिनो' in r[1] and raw.index(r) > 1)]
    # ১.১৪ পুনরুদ্ধার — ১ম অধ্যায়ের «তিলেষু» (বর্তমানে ১৪তম) এর আগে বসবে
    out, inserted = [], False
    for ch, sk in raw:
        if ch == 1 and not inserted and 'तिलेषु तैलं' in sk:
            out.append([1, SV_1_14]); inserted = True
        out.append([ch, sk])

    by_ch = {}
    for ch, sk in out:
        by_ch.setdefault(ch, []).append(sk)
    chapters = []
    for ch in sorted(by_ch):
        vs = [{'n': i + 1, 'sk': s, 'bn': '', 'spk': ''} for i, s in enumerate(by_ch[ch])]
        chapters.append({'id': ch, 'bn': f'{bn(ch)}. {SV_NAMES.get(ch, "")}', 'count': len(vs),
                         'from': 1, 'to': len(vs), 'verses': vs})
    return write('shvetashvatara', 'শ্বেতাশ্বতর উপনিষদ', 'Shvetashvatara Upanishad', chapters,
                 {'note': 'সংস্কৃত মূল পাঠ; বাংলা অনুবাদ পরবর্তীতে যোগ হবে', 'verseWord': 'মন্ত্র'})


# ---------------- ২–৪. বেদ ----------------
CROSSREF = re.compile(r'\s*PS_[0-9,._]+\s*(?:\(\d+\))?\s*')


def clean_av(sanskrit, is_last):
    """অথর্ববেদের উৎস-ত্রুটি।

    ১. সূক্তের শেষ শ্লোকে বসে থাকা «(N)» ক্রম-সংখ্যা বাদ (পাঠের অংশ নয়)
    ২. পাইপ্পলাদ-সংহিতার ক্রস-রেফারেন্স («PS_17,21.10 (21)») বাদ — এটি পাঠ নয়
    ৩. «(…)» = উৎসে বিলুপ্ত পাঠ; অজানা কিছু জুড়ে না দিয়ে স্পষ্টভাবে চিহ্নিত
    """
    if is_last:
        parts = re.split(r'\s*\((\d+)\)\s*', sanskrit)
        sanskrit = ' '.join(p for p in parts[0::2] if p)
    sanskrit = CROSSREF.sub(' ', sanskrit)
    sanskrit = re.sub(r'\(…\)', ' ⟨পাঠ অসম্পূর্ণ⟩ ', sanskrit)
    return re.sub(r'\s{2,}', ' ', sanskrit).strip()


# ⚠ ২০২৬-১১-১০: ব্যবহারকারীর সিদ্ধান্ত — সামবেদ সাইটে রাখা হচ্ছে না।
#   তাই Samaveda এখান থেকেও বাদ (এই টুল চালালে আগে সামবেদ-ডেটা ফিরে আসত)।
VED = [('RigVeda', 'rigveda', 'ঋগ্বেদ', 'Rigveda', 'মণ্ডল', 10),
       ('Atharvaveda', 'atharvaveda', 'অথর্ববেদ', 'Atharvaveda', 'কাণ্ড', 20)]


def build_vedas():
    for folder, slug, name, en, unit, nfiles in VED:
        chapters = []
        for f in range(1, nfiles + 1):
            path = f'{SRC}/ved/{folder}/Data/{folder[:2].upper()}_{f}.json'
            if not os.path.exists(path):
                path = f'{SRC}/ved/{folder}/Data/{ {"RigVeda":"RV","Samaveda":"SV","Atharvaveda":"AV"}[folder] }_{f}.json'
            if not os.path.exists(path):
                continue
            x = json.load(open(path, encoding='utf-8'))
            verses = []
            for h in x['hymns']:
                hv = h.get('verses') or []
                for j, v in enumerate(hv):
                    text = v['sanskrit']
                    if folder == 'Atharvaveda':
                        text = clean_av(text, j == len(hv) - 1)
                    verses.append({
                        'n': len(verses) + 1,
                        'sk': iast2dev(text),
                        'iast': v['sanskrit'],
                        'sukta': h.get('hymn_number'),
                        'vn': v.get('verse_number'),
                        'bn': '', 'spk': '',
                    })
            idn = x.get('book_number', f)
            chapters.append({'id': idn, 'bn': f'{bn(idn)}তম {unit}', 'count': len(verses),
                             'from': 1, 'to': len(verses), 'verses': verses})
        write(slug, name, en, chapters,
              {'note': 'সংস্কৃত মূল পাঠ; বাংলা অনুবাদ পরবর্তীতে যোগ হবে',
               'verseWord': 'মন্ত্র', 'unit': unit})


if __name__ == '__main__':
    if not os.path.isdir(SRC):
        sys.exit(f'উৎস পাওয়া যায়নি: {SRC}\n  cd /tmp/db && npm pack divine-books@0.5.0 && tar xzf *.tgz')
    print('শ্রুতি — ডেটা তৈরি\n')
    build_shvetashvatara()
    build_vedas()
    print('\nসম্পন্ন')
