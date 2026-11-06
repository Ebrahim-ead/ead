#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""শুক্ল যজুর্বেদ (slug: yajurveda-shukla) — নামানো ডেটার পরিষ্কারক (সংস্করণ ২)।

ব্যবহারকারীর নির্দেশ: «প্রত্যেকটা মন্ত্র যেন থাকে, কোন মন্ত্র যেন উল্টাপাল্টা না
হয়, অপ্রয়োজনীয় কথা সব সরাই দাও»। সেই তিন দাবি মেটাতে এই টুল যা করে:

১) মন্ত্র-নম্বর ঠিক করা (উল্টাপাল্টা দূর)
   উৎসের পাঠে মন্ত্র-নম্বরের কোনো চিহ্নই নেই (০/১৭৯১ খণ্ডে পাঠের শুরুতে নম্বর
   পাওয়া গেছে), অথচ ফেচার নম্বর বসিয়েছিল উৎস-পাতার অন্য চিহ্ন থেকে। ফলে
   ২২/৪০ অধ্যায়ে নম্বর অসংগত ছিল: চ্যাপ্টার ৩৪-এ ধারা শুরুই হতো «১০, ২, ৩, ৪…»
   দিয়ে, চ্যাপ্টার ১১-এ ৫৫টি মন্ত্রের নম্বর ছড়িয়ে ছিল ১–৮৩ পর্যন্ত (২৮টি গ্যাপ),
   চ্যাপ্টার ১ ও ২ শুরু হতো ২ নম্বর থেকে। এখন নম্বর বসে পড়ার ক্রমে ১..N, আর
   উৎসের পুরোনো চিহ্ন `srcN` ঘরে অটুট থাকে (তথ্য হারায় না)।

২) প্রতিটি মন্ত্র অটুট রাখা
   মন্ত্র-তালিকা থেকে কিছুই মুছে ফেলা হয় না। অধ্যায়ের শুরুতে থাকা
   অনুক্রমণিকা/ভূমিকা-অনুবাদ আর অধ্যায়-শিরোনামের লাইন — এগুলো মন্ত্র নয়,
   তাই সেগুলো আলাদা ঘরে (`preface`, `heading`) সরানো হয় এবং রিডারে আলাদা
   ব্লকে দেখানো হয়। পাঠের এক অক্ষরও ফেলা যায় না: পরিষ্কারের আগে ও পরে
   মোট অক্ষর-সংখ্যা মিলিয়ে দেখা হয় (অস্বাভাবিক কম পড়লে টুল থেমে যায়)।

৩) অপ্রয়োজনীয়/অস্বাভাবিক জিনিস সরানো
   - ভুল ঘরে থাকা পাঠ: কয়েকটি খণ্ডের বাংলা পাঠ চলে গিয়েছিল `sk` ঘরে। পুরো
     বইয়ে একটিতেও আসল দেবনাগরী অক্ষর নেই (উৎসে সংস্কৃত মূল ছাপাই নেই),
     তাই দেবনাগরীবিহীন `sk` = ভুল ঘর; পাঠ ফিরিয়ে দেওয়া হয়, মূল টুকরো
     _debug/yajurveda_sk_moved.json-এ জমা থাকে।
   - বানান: উৎসের পাঠে অসমীয়া «ৰ» (U+09F0) ও «ৱ» (U+09F1) বসে আছে যেখানে
     বাংলায় র/ব হয় — «ব্ৰহ্ম» → «ব্রহ্ম», «শত্ৰু» → «শত্রু», «ইন্দ্ৰ» → «ইন্দ্র»,
     «উপজিৱিকা» → «উপজিবিকা»। মোট ১৪০০-এর বেশি জায়গায়। প্রতিটি বদল
     এক-অক্ষরের বিনিময়, তাই পাঠের দৈর্ঘ্য বদলায় না।
   - অধ্যায়-শিরোনাম: কাটা ঠিকানা-টুকরো («০১ শুক্লযজুর্বেদ পূর্বা») বদলে পূর্ণ রূপ
     («প্রথম অধ্যায় · পূর্বার্ধ»), উৎসের টুকরোর সাথে মিলিয়ে যাচাইসহ।
   - index-এর ভুল দাবি («মূল সংস্কৃত পাঠ …») বদলে ডেটার সাথে মেলানো।

যা ইচ্ছে করে ছোঁয়া হয় না (ভুল-পজিটিভ এড়ানো):
   «?» (১৩৬ বার) আসল প্রশ্নবোধক; «[প্রশ্ন]/[উত্তর]» ও «(১)(২)…» (৬০৮ বার)
   উৎসের নিজস্ব টীকা-চিহ্ন; «–»/«-» যৌগিক শব্দের স্বাভাবিক যতি; «॥» বৈদিক
   দ্বৈত-দাঁড়ি। আর «হোম», «প্রকাশক», «সূচি», «পরবর্তী» শব্দগুলো এখানে সাইটের
   নেভিগেশন-ঝুট নয়, অনুবাদকের গদ্যের অংশ (হোম-কৰ্ম্ম, বেদার্থপ্রকাশক, পরবর্তী
   কণ্ডিকা) — তাই সেগুলো কাটা হয় না।

ব্যবহার:  python3 tools/clean_yajurveda.py [--dry]
আইডেমপোটেন্ট: দুবার চালালে দ্বিতীয়বার কোনো পরিবর্তন হয় না।
"""

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "grantho" / "data"
SLUG = "yajurveda-shukla"
DBG = DATA / "_debug"

DEVA = re.compile("[\u0904-\u0939\u093D\u0950\u0958-\u0961\u0972-\u097F]")
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
EN2BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

# অসমীয়া রা/ওয়া → বাংলা র/ব (উৎসের পাঠে ধারাবাহিকভাবে ভুল অক্ষর বসে আছে)
ORTHO = str.maketrans({"\u09F0": "র", "\u09F1": "ব"})

# উৎসের লেসন-সূচি অনুযায়ী ৪০ অধ্যায়ের ক্রম-নাম ও ভাগ
# (পূর্বার্ধ ১–২০, উত্তরার্ধ ২১–৪০)
ORDINALS = [
    "প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম", "অষ্টম",
    "নবম", "দশম", "একাদশ", "দ্বাদশ", "ত্রয়োদশ", "চতুর্দশ", "পঞ্চদশ", "ষোড়শ",
    "সপ্তদশ", "অষ্টাদশ", "ঊনবিংশ", "বিংশ", "একবিংশ", "দ্বাবিংশ",
    "ত্রয়োবিংশ", "চতুর্বিশ", "পঞ্চবিংশ", "ষড়বিংশ", "সপ্তবিংশ", "অষ্টাবিংশ",
    "ঊনত্রিংশ", "ত্রিংশ", "একত্রিংশ", "দ্বাত্রিংশ", "ত্রয়স্ত্রিংশ",
    "চতুস্ত্রিংশ", "পঞ্চত্রিংশ", "ষট্ত্রিংশ", "সপ্তত্রিংশ", "অষ্টাত্রিংশ",
    "ঊনচত্বারিংশ", "চত্বারিংশ",
]


def bn_digits(n):
    return str(n).translate(EN2BN)


def toi(x):
    """'১২' / '12' / 12 → 12; লেবেল (যেমন «অনুক্রমণিকা») হলে None."""
    s = str(x).strip().translate(BN_DIGITS)
    m = re.match(r"([0-9]+)", s)
    return int(m.group(1)) if m else None


def norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def fix_ortho(text):
    """অসমীয়া ৰ/ৱ → বাংলা র/ব। এক-অক্ষর বিনিময়, তাই দৈর্ঘ্য বদলায় না।"""
    if not text:
        return text, 0
    fixed = str(text).translate(ORTHO)
    return fixed, sum(1 for a, b in zip(str(text), fixed) if a != b)


def is_heading(text):
    """অধ্যায়-শিরোনামের ছোট লাইন (মন্ত্র নয়)।"""
    t = str(text or "").strip()
    return len(norm(t)) < 200 and "অধ্যায়" in t and not t.endswith(("।", "?", "!", "॥"))


def split_front_matter(verses):
    """অধ্যায়ের শুরুতে থাকা ভূমিকা/অনুক্রমণিকা খণ্ড আলাদা করা।

    দুটি উৎস থেকে চেনা হয়:
      - আগেই চিহ্নিত খণ্ড (preface/srcN ঘর — পুরোনো রান থেকে)
      - প্রথম নম্বর-রিস্টার্টের আগের খণ্ডগুলো (ফেচারের ভুল নম্বর ধরার লক্ষণ)
    শর্ত: রিস্টার্ট-বিন্দু ১..৪-এর ভেতরে হতে হবে এবং সেই খণ্ডগুলোতে যথেষ্ট গদ্য
    থাকতে হবে — নইলে এটি ভূমিকা নয়, তখন কিছু সরানো হয় না।
    """
    head = 0
    while head < len(verses) and verses[head].get("preface"):
        head += 1
    if head:
        return head
    ns = [toi(v.get("n")) for v in verses]
    r = None
    for i in range(1, len(ns)):
        if ns[i] is not None and ns[i - 1] is not None and ns[i] <= ns[i - 1]:
            r = i
            break
    if not r or r > 4:
        return 0
    if sum(len(norm(v.get("bn"))) for v in verses[:r]) < 400:
        return 0
    return r


def chapter_title(cid, old):
    """উৎসের কাটা-টুকরো শিরোনাম থেকে পূর্ণ শিরোনাম, মিল যাচাইসহ।"""
    if cid < 1 or cid > len(ORDINALS):
        return old, "সীমার বাইরে"
    word = ORDINALS[cid - 1]
    half = "পূর্বার্ধ" if cid <= 20 else "উত্তরার্ধ"

    # উৎসের বানান কাটা থাকায় ফলা-চিহ্নে পার্থক্য থাকতে পারে («ষটত্র» বনাম
    # «ষট্ত্রিংশ»), তাই হসন্ত (্) বাদ দিয়ে তুলনা। ক্রম-নামের টুকরোই না থাকলে
    # (যেমন চ্যাপ্টার ২১: কেবল «সংহিতা») সূচিতে তার অবস্থানই যথেষ্ট প্রমাণ।
    def key(s):
        return re.sub("[\u09CD]", "", norm(s))

    GENERIC = ("শুক্ল", "যজুর্বেদ", "শুক্লযজুর্বেদ", "সংহিতা", "অন", "অনুবাদ")
    frags = [norm(t) for t in re.findall(r"[^\s—–-]+", str(old or "")) if len(norm(t)) > 2]
    cands = (key(word), key(half))
    named = [f for f in frags if not any(f.startswith(g) or g.startswith(f) for g in GENERIC)
             and not f.translate(BN_DIGITS).isdigit()]
    matched = any(c.startswith(key(f)) or key(f).startswith(c[:3]) or c[:3] == key(f)[:3]
                  for f in named for c in cands)
    if named and not matched:
        return old, f"মিলেনি ({'/'.join(named[-2:])} ≠ {'/'.join(c[:8] for c in cands)})"
    note = "" if named else "সাধারণ টুকরো — সূচিতে অবস্থান থেকে নির্ধারিত"
    return f"{word} অধ্যায় · {half}", note


def clean(dry=False):
    log = []
    d = DATA / SLUG
    idxp = d / "index.json"
    if not idxp.exists():
        print(f"ডেটা নেই: {idxp} — আগে CI ফেচ চালাতে হবে")
        return 1
    idx = json.loads(idxp.read_text(encoding="utf-8"))

    moved = []
    st = dict(preface=0, heading=0, sk=0, ortho=0, title=0, renum=0, dup=0)
    chars_before = chars_after = 0
    n_mantra = n_mantrabn = 0

    for c in idx.get("chapters", []):
        fp = d / f'ch{c["id"]}.json'
        if not fp.exists():
            log.append(f'চ্যাপ্টার {c["id"]}: ফাইল নেই')
            continue
        blob = json.loads(fp.read_text(encoding="utf-8"))
        raw = blob.get("verses", [])
        # আগে থেকে সংরক্ষিত ভূমিকা/শিরোনাম-পাঠও মোট অক্ষরে ধরতে হবে, নইলে
        # দ্বিতীয় রানে সেটি হারিয়ে গেলেও নিরাপত্তা-যাচাই ধরতে পারবে না।
        old_pre = str(blob.get("preface") or "").strip()
        old_head = str(blob.get("heading") or "").strip()
        chars_before += (sum(len(norm(v.get("bn"))) + len(norm(v.get("sk"))) for v in raw)
                         + len(norm(old_pre)) + len(norm(old_head)))

        # (ক) ভুল ঘরে থাকা পাঠ ফেরানো — দেবনাগরীবিহীন sk সবসময়ই ভুল ঘর
        for v in raw:
            sk = str(v.get("sk") or "").strip()
            if sk and not DEVA.search(sk):
                bn = str(v.get("bn") or "").strip()
                merged = sk if (len(bn) < 100 and norm(bn) in norm(sk)) else (
                    sk if not bn else sk + "\n" + bn)
                moved.append({"chapter": c["id"], "n": v.get("n"),
                              "sk_chars": len(sk), "bn_chars": len(bn)})
                v["bn"], v["sk"] = merged, ""
                st["sk"] += 1

        # (খ) ভূমিকা/অনুক্রমণিকা ও অধ্যায়-শিরোনামের লাইন আলাদা করা
        k = split_front_matter(raw)
        front, mantras = list(raw[:k]), list(raw[k:])
        headings = [v for v in front if is_heading(v.get("bn"))]
        preface = [v for v in front if not is_heading(v.get("bn"))]
        # মন্ত্র-তালিকার ভেতরেও শিরোনাম-লাইন থাকলে সেটি আলাদা (মন্ত্র নয়)
        extra_head = [v for v in mantras if is_heading(v.get("bn"))]
        if extra_head:
            mantras = [v for v in mantras if not is_heading(v.get("bn"))]
            headings += extra_head
        st["heading"] += len(headings) + (1 if old_head and not headings else 0)
        st["preface"] += len(preface) + (1 if old_pre and not preface else 0)

        # (গ) বানান স্বাভাবিক করা (সব খণ্ডে — ভূমিকা ও মন্ত্র দুটোতেই)
        for v in front + mantras:
            v["bn"], n1 = fix_ortho(v.get("bn"))
            v["sk"], n2 = fix_ortho(v.get("sk"))
            st["ortho"] += n1 + n2

        # (ঘ) মন্ত্র-নম্বর পড়ার ক্রমে ১..N — উৎসের চিহ্ন srcN-এ অটুট
        for i, v in enumerate(mantras, start=1):
            if "srcN" not in v and v.get("n") is not None:
                v["srcN"] = v.get("n")
            if v.get("n") != i:
                v["n"] = i
                st["renum"] += 1
            v.pop("preface", None)
            if not str(v.get("bn") or "").strip():
                log.append(f'চ্যাপ্টার {c["id"]} খণ্ড {i}: বাংলা পাঠ ফাঁকা!')

        # উৎসের পুরোনো চিহ্নে ডুপ্লিকেট থাকলে শুধু নথিভুক্ত করা (পাঠ অটুট)
        olds = [toi(v.get("srcN")) for v in mantras]
        olds = [x for x in olds if x is not None]
        dups = sorted({x for x in olds if olds.count(x) > 1})
        if dups:
            st["dup"] += 1
            log.append(f'চ্যাপ্টার {c["id"]}: উৎসের চিহ্নে ডুপ্লিকেট {dups[:6]} '
                       f'(প্রদর্শন-নম্বর এখন ক্রমিক)')

        # (ঙ) ভূমিকা ও শিরোনাম চ্যাপ্টার-ঘরে (পাঠ হারায় না, রিডারে আলাদা ব্লকে দেখায়)
        new_pre = [str(v.get("bn") or "").strip() for v in preface if str(v.get("bn") or "").strip()]
        new_head = [str(v.get("bn") or "").strip() for v in headings if str(v.get("bn") or "").strip()]
        # আইডেমপোটেন্সি: এই রানে নতুন ভূমিকা না মিললে আগে সংরক্ষিতটিই থাকবে।
        # (আগে ফাঁকা টেক্সট দিয়ে পুরোনো ভূমিকা মুছে যেত — পাঠ হারাত।)
        pre_txt = "\n\n".join(([old_pre] if old_pre else []) + new_pre)
        head_txt = "\n".join(([old_head] if old_head else []) + new_head)

        # (চ) শিরোনাম ঠিক করা
        new, why = chapter_title(int(c["id"]), c.get("bn"))
        if new != c.get("bn"):
            c["bn"] = new
            st["title"] += 1
        elif why:
            log.append(f'চ্যাপ্টার {c["id"]}: শিরোনাম বদলানো হয়নি — {why}')

        # (ছ) গণনা ও পরিসর — এখন প্রতিটি মন্ত্র ১..N, তাই পরিসর পরিষ্কার
        c["count"] = len(mantras)
        c["withBn"] = sum(1 for v in mantras if str(v.get("bn") or "").strip())
        c["from"], c["to"] = (1, len(mantras)) if mantras else (0, 0)
        # ভূমিকা-খণ্ড আগেই আলাদা ঘরে সরে গেলে `preface` তালিকা ফাঁকা থাকে — তাই
        # সংরক্ষিত টেক্সট থেকেই গোনা হয় (নইলে দ্বিতীয় রানে গণনা শূন্য হয়ে যেত)।
        c["prefaceCount"] = len([x for x in pre_txt.split("\n\n") if x.strip()]) if pre_txt else 0
        n_mantra += len(mantras)
        n_mantrabn += c["withBn"]

        # (জ) চ্যাপ্টার-ফাইল: রিডার এখান থেকেই শিরোনাম/সংখ্যা পড়ে
        blob["bn"] = c["bn"]
        blob["count"] = c["count"]
        blob["withBn"] = c["withBn"]
        blob["from"], blob["to"] = c["from"], c["to"]
        blob["verses"] = mantras
        if pre_txt:
            blob["preface"] = pre_txt
        else:
            blob.pop("preface", None)
        if head_txt:
            blob["heading"] = head_txt
        else:
            blob.pop("heading", None)
        blob.pop("prefaceCount", None)

        chars_after += (sum(len(norm(v.get("bn"))) + len(norm(v.get("sk"))) for v in mantras)
                        + len(norm(pre_txt)) + len(norm(head_txt)))

        if not dry:
            fp.write_text(json.dumps(blob, ensure_ascii=False, indent=1), encoding="utf-8")

    # (ঝ) index হালনাগাদ + ভুল দাবি সংশোধন
    idx["total"] = n_mantra
    idx["withBn"] = n_mantrabn
    note = ("মন্ত্র-নম্বর পড়ার ক্রমে বসানো (উৎসের পাঠে মন্ত্র-নম্বরের চিহ্ন ছিল না)। "
            "প্রতি অধ্যায়ের শুরুতে উৎসের অনুক্রমণিকা-অনুবাদ আলাদা ব্লকে দেওয়া আছে, "
            "যা মন্ত্র-গণনার বাইরে।")
    if idx.get("note") != note:
        log.append("index.note হালনাগাদ হলো")
        idx["note"] = note
    if not dry:
        idxp.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
        if moved:
            DBG.mkdir(parents=True, exist_ok=True)
            (DBG / "yajurveda_sk_moved.json").write_text(
                json.dumps(moved, ensure_ascii=False, indent=1), encoding="utf-8")

    # (ঞ) নিরাপত্তা-যাচাই: এক অক্ষরও হারানো যাবে না
    if chars_after != chars_before:
        print(f"⛔ থেমে গেছে: পাঠের অক্ষর বদলে গেছে — আগে {chars_before}, পরে {chars_after} "
              f"(পার্থক্য {chars_after - chars_before})")
        return 1

    print(f'মন্ত্র: {n_mantra} (বাংলাসহ {n_mantrabn}) · ভূমিকাযুক্ত অধ্যায়: {st["preface"]} · '
          f'শিরোনাম-লাইন: {st["heading"]} · নম্বর ঠিক: {st["renum"]} · বানান বদল: {st["ortho"]} · '
          f'sk থেকে ফেরানো: {st["sk"]} · শিরোনাম ঠিক: {st["title"]} · '
          f'উৎস-ডুপ্লিকেট অধ্যায়: {st["dup"]} · অক্ষর অটুট: {chars_after}'
          + (" · [dry-run]" if dry else ""))
    for line in log[:30]:
        print("  " + line)
    if len(log) > 30:
        print(f"  … আরও {len(log) - 30} লাইন")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="শুধু দেখাও, লেখো না")
    a = ap.parse_args()
    sys.exit(clean(dry=a.dry))
