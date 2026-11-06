#!/usr/bin/env python3
"""বাইবেল ডেটার অফলাইন মেরামত — যেখানে উৎস আর নাওয়া যায় না।

কেন এই স্ক্রিপ্ট: নামানো পাঠ (assets/grantho/data/bible/) আর ইংরেজি কাঁচা
(raw/) ডেটা রিপোতে জমা আছে, কিন্তু কয়েকটি জায়গায় পার্স-ভুলে পাঠ ভুল
অবস্থায় সেঁধে গেছে — উৎস-সাইটে ঢুকে আবার নামানো ছাড়া সেগুলো ঠিক হবে না
(আর কিছু পাতা এখন লগইন-দেয়ালের পেছনে)। তাই যা **অফলাইনেই প্রমাণযোগ্য**
কেবল সেটুকুই এখানে সারানো হয়:

১. **গণনা ৭** — উৎস-পাতায় ২৮টি পদ একাসাথে জোড়া লেগে (পদ ১১) গেছে; ভেতরে
   দিন-ভিত্তিক নেতাদের উপহারের তালিকা «১২…৮৩» ধারাবাহিক সংখ্যায় ভাগ করা।
   সত্যতা: ঠিক ৭২টি টোকেন, ১২ থেকে ৮৩ পর্যন্ত একটিও না মিসিয়ে, শেষ টোকেনের
   পরে «এগুলো ছিল … উপহার।» — তবেই কাটা হয়।
২. **যোয়েল ১** — একই রোগ, রোমান অঙ্কে (ASCII) «2…20» — ১৯টি পদ।
৩. **যাত্রাপুস্তক** — গোষ্ঠী-নম্বর এক করে পিছিয়ে গেছে: গোষ্ঠী ১১-এ আছে
   প্রকৃত ১২-এর ৫১ পদ, ১২-এ ১৩-এর ২২ পদ। (১১-এর পাঠ উৎসেই লগইন-দেয়ালের
   পেছনে ছিল — তাই missing-এ ১১ থাকবে, আর ১২/১৩ যাবে নিজের ঘরে।)
৪. **ওবাদিয়া** — পুরোনো discover-এ লেবেলের «1 Topic» কাটা হয়নি, তাই bn
   ফিল্ডে «৩১. ওবাদিয়া (Obadiah) 1 Topic» ঢুকে গেছে।
৫. **ইংরেজি raw** — পদ-শুরুর জমে থাকা পাঠ («2 Paul, a slave…», «1 Such is…»)
   পুরোনো পার্সারের দূষণ; সামনের শ্রেণিতে সামঞ্জস্যপূর্ণ হলে কাটা হয়, নইলে
   হাত দেওয়া হয় না (সন্দেহ হলে ছেড়ে দেওয়া নীতি)।

এরপর কাঠামো (n, suktas, count) পুরো বইয়ের জন্য নতুন করে গোনা হয়, index
পুনর্লিখন হয়, ইংরেজি join আবার চলে — সব কেবল তখনই, যখন প্রতিটি প্রমাণ মেলে।
কিছু না মিললে জায়গাটি **ছোঁয়া হয় না**, রিপোর্টে লেখা হয় _debug/bible_repair.txt।

ব্যবহার:  python3 tools/repair_bible_data.py [--dry-run]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data/bible"
DBG = ROOT / "assets/grantho/data/_debug"
BN = "০১২৩৪৫৬৭৮৯"


def bn_digits(n):
    return "".join(BN[int(c)] for c in str(n))


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                 encoding="utf-8")


def regen(book):
    """বইয়ের কাঠামো নতুন করে গোনা — পাঠ অপরিবর্তিত, কেবল হিসাব।

    n (বই-ব্যাপী ক্রমিক), suktas (প্রতি অধ্যায়ের from/to/vfrom/vto/verse),
    count, suktasCount, withBn, to। ক্রম ভাঙা থাকলে এখানেই ধরা পড়ে।
    """
    n = 0
    groups = []
    for g in book["suktas"]:
        vs = [v for v in book["verses"] if v["ch"] == g["id"]]
        if not vs:
            continue
        start = n + 1
        for v in vs:
            n += 1
            v["n"] = n
        g["from"], g["to"] = start, n
        g["vfrom"], g["vto"] = vs[0]["vn"], vs[-1]["vn"]
        g["verse"] = len(vs)
        groups.append(g)
    book["suktas"] = groups
    book["count"] = n
    book["from"], book["to"] = (1, n) if n else (0, 0)
    book["suktaCount"] = len(groups)
    book["withBn"] = sum(1 for v in book["verses"] if str(v.get("bn") or "").strip())
    return book


def split_glyph_token(text, first, last, tail_ok):
    """«১২…৮৩» ধারাবাহিক টোকেনে ভাগ — প্রমাণ ছাড়া কিছুই ফেরানো হয় না।"""
    toks = [(m.start(), m.group(0))
            for m in re.finditer(r"[০-৯]{1,3}", text)]
    want = [bn_digits(x) for x in range(first, last + 1)]
    if [t for _, t in toks] != want:
        return None, (f"টোকেন-মিল নেই: পাওয়া {len(toks)}টি "
                      f"({[t for _, t in toks][:4]}…), প্রত্যাশা {len(want)}টি "
                      f"({want[:4]}…)")
    prefix = text[:toks[0][0]].strip()
    pieces, heads = [], []
    for k, (pos, tok) in enumerate(toks):
        end = toks[k + 1][0] if k + 1 < len(toks) else len(text)
        piece = text[pos:end].strip()
        pieces.append(piece)
        # নতুন পদ চেনা: সংখ্যার পরে সরাসরি বাংলা অক্ষর («১২প্রথম», «১৩তাঁর») —
        # উৎস-পাতায় ব্ল্যাংক নেই। পাঠের ভেতরের সংখ্যা («৭০ পাঁঠা») কখনোই এই
        # আকার নেয় না, কারণ সেখানে সংখ্যার পরে ফাঁকা থাকে।
        heads.append(bool(re.match(r"^[০-৯]{1,3}[\u0980-\u09FF]", piece)))
    if not all(heads):
        bad = [i + first for i, h in enumerate(heads) if not h]
        return None, f"{len(bad)}টি টোকেনের পরে নতুন পদের সূচনা নেই (যেমন {bad[:3]})"
    if not re.search(tail_ok, pieces[-1]):
        return None, "শেষ পদে প্রত্যাশিত উপসংহার নেই"
    if not prefix or len(prefix) > 300:
        return None, "প্রারম্ভিক (নম্বরহীন) অংশ প্রত্যাশিত নয়"
    return (prefix, pieces), "ok"


def split_ascii_token(text, first, last):
    """রোমান-অঙ্কের ধারাবাহিক নম্বর (যোয়েল ১: «2 …» ‹‑› «20 …») ভাগ করা।

    কেন আলাদা: উৎস-পাতায় সংখ্যাগুলো ASCII («2», «3» … «20»), আর সেগুলোই
    পদ-সূচনা। কাটার পর প্রতিটি পদে নিজের নম্বরই রাখা হয় — লেবেল হিসেবে
    দরকার (নতুন যোগ হওয়া অংশটা কোন পদ, তা পাঠক-গণনা ছাড়াই বোঝা যায়)।
    প্রমাণ: টোকেন ঠিক ২ থেকে ২০ পর্যন্ত একটানা — নইলে কিছুই ফেরানো হয় না।
    """
    toks = [(m.start(), int(m.group(1)))
            for m in re.finditer(r"(?<![\d০-৯])(\d{1,2})(?![\d০-৯])", text)
            if first <= int(m.group(1)) <= last]
    if [n for _, n in toks] != list(range(first, last + 1)):
        return None, f"ASCII নম্বর-ক্রম মেলেনি ({len(toks)}টি পাওয়া গেল)"
    pieces, heads = [], []
    for k, (pos, n) in enumerate(toks):
        end = toks[k + 1][0] if k + 1 < len(toks) else len(text)
        piece = text[pos:end].strip()
        pieces.append(piece)
        # নতুন পদ: নম্বরের পরে ফাঁকা-থেকে-বাংলা শব্দ («2 হে প্রবীণেরা»)
        heads.append(bool(re.match(r"^\d{1,2}\s+[\u0980-\u09FF]", piece)))
    if not all(heads):
        return None, "কিছু টোকেনের পরে নতুন পদের সূচনা নেই"
    return pieces, "ok"


def strip_footnotes(en):
    """পদ-পাঠের লেজে লেগে থাকা টীকা-তালিকা ও টীকা-চিহ্ন কাটা।

    পুরোনো পার্সার টীকা-তালিকা পাঠের সঙ্গেই জুড়ে দিয়েছিল («…no shame. 1
    [4b-25] This section…», «…of Judea. 19 1 [1-13] See the note on…»)।
    লাইভে এগুলোই দূষণ হিসেবে দেখা যাচ্ছিল। ছাঁচ: ছোট সংখ্যা + «[» + রেফারেন্স
    («[4b-25]», «[1-6,8-9]», «[Psalm 63]») — বন্ধনী কখনো অসম্পূর্ণও ছিল।

    কাজ একাধিক ধাপে, আর ধাপগুলো একে-অপরের ওপর নির্ভর করে (কপিরাইট-লেজ কাটার
    পরেই হয়তো «19» লেজে এসে পড়ে; টীকা-তালিকা কাটার পরেই আগের টীকা-চিহ্ন
    লেজে আসে) — তাই যতক্ষণ কিছু বদলায়, ততক্ষণ পুনরাবৃত্তি (সর্বোচ্চ ৫ বার)।

    কোনো ধাপ অনিশ্চিত হলে সেটি কিছুই কাটে না — অনুমান নয়, ছাঁচ-মিলই শর্ত।
    """
    if not en:
        return en

    def _tail_num(t):
        # পাঠের শেষে ঝুলে-থাকা টীকা-চিহ্ন («…faith. 10», «…bread, 5»,
        # «…with you.") 33», «…our daily bread 4»): সংখ্যাটি শেষ যতিচিহ্নের পরে
        # বা সোজা শব্দের পরে একা বসলে কাটা — সংখ্যাটি একক ও ছোট (≤ ৩৫) হলে।
        # সাবধান: «…in 70», «…for 40 days» জাতীয় আসল সংখ্যা রাখতে হয়; তাই
        # বড় সংখ্যা (বছর/সংখ্যা-গণনা) ছোঁয়া হয় না।
        # সংখ্যাটি ছোট এবং তার আগে বিরাম/শব্দ — টীকা-চিহ্ন। αρσενικό-সন্দেহ:
        # ৫০-এর বেশি হলে (বছর/সংখ্যা) ছোঁয়া হয় না।
        t = re.sub(r"(?<=[A-Za-z,.;:!?”\"'\d])\s(\d{1,2})\s*$",
                   lambda m: "" if int(m.group(1)) <= 50 else m.group(0),
                   t).strip()
        # টীকা-চিহ্নের বন্ধনী-অবশিষ্ট: «) 10 (» বা শুধু «)» — পাঠ নয়
        t = re.sub(r"\s*\)\s*\d{0,2}\s*\(?\s*$", "", t).strip()
        # আসল পাঠ যদি শুধু বন্ধনী/যতিচিহ্ন হয়ে যায়, সেটি ছুঁড়ে ফেলা (পাঠ নেই)
        if t and not re.search(r"[A-Za-z]", t):
            return ""
        return t

    def _page_tail(t):
        # পাতা-পাদটীকা: নেভিগেশন ও কপিরাইট — পাঠ নয়
        return re.sub(r"\s*(?:Previous\s*-\s*Next|Next\s*-\s*Previous)?\s*"
                      r"Copyright\s*©?\s*Libreria Editrice Vaticana\s*$",
                      "", t).strip()

    def _footnote_list(t):
        # প্রথম «‹সংখ্যা› [» — এর আগের সবটুকু পাঠ, পিছনের সব টীকা।
        for m in re.finditer(r"(?<=\s)(?:##\s*)?\d{1,3}\s*\[", t):
            head = t[:m.start()].strip()
            if len(head.split()) < 3:
                continue
            rest = t[m.end():]
            cut = rest.find("]")
            inner = (rest[:cut] if cut >= 0 else rest[:120]).strip()
            refish = bool(re.fullmatch(r"[\d\s,;:.\-–ab]+", inner or "")
                          or re.match(r"^(?:Psalm|Ps)\s+\d", inner or "")
                          or re.match(r"^[A-Z][A-Za-z.]{1,14}\s+"
                                      r"(?:\d|Kings|Sam|Chron)", inner or ""))
            # রেফারেন্স-জাতীয় না হলে পাঠটি পূর্ণ বিরামে শেষ হওয়া চাই
            if not refish and not re.search(r"[.!?;:”\"']$", head):
                continue
            return head
        return t

    for _ in range(5):
        prev = en
        en = _page_tail(en)          # কপিরাইট-লেজ আগে, নইলে টীকা-চিহ্ন আটকে থাকে
        en = _footnote_list(en)      # তারপর টীকা-তালিকা
        en = _tail_num(en)           # শেষে ঝুলে-থাকা টীকা-সংখ্যা
        en = re.sub(r"\s*##\s*$", "", en).strip()
        if en == prev:
            break
    return en


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-join", action="store_true")
    args = ap.parse_args()

    rep, changed = [], False
    before, after = {}, {}
    dry = args.dry_run          # শুকনো-রানে কোনো ফাইলেই হাত দেওয়া হয় না
    fresh = {}                  # dry-রানে বদলে যাওয়া বইয়ের হিসাব

    # ── ০) আগের হিসাব ─────────────────────────────────────────────
    idx_old = load(DATA / "index.json")
    for c in idx_old["chapters"]:
        before[c["id"]] = c["count"]

    # ── ১) গণনা ৭: জোড়া-লাগা তালিকা ভাগ ───────────────────────────
    p = DATA / "ch4.json"
    b = load(p)
    target = next((v for v in b["verses"]
                   if v["ch"] == 7 and v["vn"] == 11), None)
    if target is None:
        rep.append("· গণনা: অ৭/১১ পাওয়া যায়নি — ছোঁয়া হলো না")
    else:
        got, why = split_glyph_token(target["bn"], 12, 83,
                                     r"উপহার\s*[।.]?\s*$")
        pieces = got[1] if got else None
        prefix = got[0] if got else ""
        if not pieces:
            rep.append(f"· গণনা: ভাগ করা গেল না — {why} (অপরিবর্তিত)")
        else:
            nxt = [v for v in b["verses"] if v["ch"] == 7 and v["vn"] > 11]
            assert nxt and nxt[0]["vn"] == 84, "অ৭-এর পরের পদ ৮৪ নয়"
            head_txt = b["verses"]
            pos = head_txt.index(target)
            # প্রত্যাশিত ক্রম: পদ ১১ = ভূমিকা («বেদীটিকে উৎসর্গ করার জন্যে…»),
            # তারপর ১২…৮৩ (৭২ দিন), তারপরেই ৮৪ («সুতরাং ঐসব দ্রব্যসামগ্রী…»)।
            # আগে ভূমিকাটুকুও ১২ নম্বরে বসে যেত, তাই ১১ ফাঁকা ও মোট এক পদ কম
            # হতো — এখন ঠিক জায়গায়।
            newv = [{"n": 0, "vn": 11, "ch": 7, "bn": prefix,
                     "spk": "", "bnSrc": target.get("bnSrc", "")}]
            for k, piece in enumerate(pieces):
                nv = {"n": 0, "vn": 12 + k, "ch": 7, "bn": piece,
                      "spk": "", "bnSrc": target.get("bnSrc", "")}
                newv.append(nv)
            # পাঠে প্রথম পদাংশ («১২প্রথম দিন…») পুরোটা নতুন পদেই থাকে
            b["verses"][pos:pos + 1] = newv
            regen(b)
            fresh[p.name] = b
            if not dry:
                save(p, b)
            changed = True
            rep.append(f"✓ গণনা: অ৭/১১ → {len(pieces)}টি পদ (১২–৮৩); বইয়ের পদ "
                       f"{sum(before.values()) and ''}{b['count']} (আগে ১১৯০)")

    # ── ২) যোয়েল ১: ASCII তালিকা ভাগ ─────────────────────────────
    p = DATA / "ch29.json"
    j = load(p)
    if not j["verses"]:
        rep.append("· যোয়েল: কোনো পদ নেই — ছোঁয়া হলো না")
    else:
        first = j["verses"][0]
        # পূর্বশর্ত: ১ম পদে কেবল «…বার্তা:» আছে তারপর সরাসরি «2 …» — নইলে
        # এখানে হাত দেওয়া হয় না (কোনো অনুমান নয়)।
        m2 = re.search(r"(?<![\d০-৯])2\s+[\u0980-\u09FF]", first["bn"])
        pre = first["bn"][:m2.start()].strip() if m2 else ""
        pieces, why = split_ascii_token(first["bn"], 2, 20) if m2 else (None, "প্রারম্ভিক অংশ পাওয়া যায়নি")
        if not pieces:
            rep.append(f"· যোয়েল: ভাগ করা গেল না — {why} (অপরিবর্তিত)")
        elif not pre or len(pre) > 90:
            rep.append("· যোয়েল: আশানুরূপ প্রারম্ভ («…বার্তা:») নেই — ছোঁয়া হলো না")
        else:
            newv = [{"n": 0, "vn": 1, "ch": 1, "bn": pre,
                     "spk": "", "bnSrc": first.get("bnSrc", "")}]
            for k, piece in enumerate(pieces):
                nv = {"n": 0, "vn": 2 + k, "ch": 1, "bn": piece,
                      "spk": "", "bnSrc": first.get("bnSrc", "")}
                newv.append(nv)
            j["verses"][0:1] = newv
            j.pop("missing", None)
            regen(j)
            fresh[p.name] = j
            if not dry:
                save(p, j)
            changed = True
            rep.append(f"✓ যোয়েল: অ১ → {len(pieces)}টি পদ (২–২০); বইয়ে মোট "
                       f"{j['count']}")

    # ── ৩) যাত্রাপুস্তক: গোষ্ঠী-সরণ সারানো ────────────────────────
    # রোগ: উৎসের স্লাগ যাত্রাপুস্তক-১০ («-১০-2») আসলে ১১-এর পাতা, আর
    # তার পরের স্লাগগুলোও এক ধাপ পিছানো — ফলে অ১১-এর পাঠ নেই, বরং অ১২-এর
    # ৫১ পদ «অধ্যায় ১১» ঘরে, অ১৩-এর ২২ পদ «অধ্যায় ১২» ঘরে।
    # প্রমাণ (উৎস-পাঠের বাইরে, কাঠামোতেই): ঘর ১১-এ ৫১ পদ ও ১২-এ ২২ পদ,
    # ১৩ নেই, বাকি সব গোষ্ঠী ১..১০ লেগে। তখনই এক ঘর সরা হয়, নইলে নয়।
    p = DATA / "ch2.json"
    e = load(p)
    ids = [g["id"] for g in e["suktas"]]
    g11 = next((g for g in e["suktas"] if g["id"] == 11), None)
    g12 = next((g for g in e["suktas"] if g["id"] == 12), None)
    g13 = next((g for g in e["suktas"] if g["id"] == 13), None)
    if (ids[:10] != list(range(1, 11)) or g11 is None or g12 is None
            or g13 is not None or g11["verse"] != 51 or g12["verse"] != 22
            or ids[12:14] != [14, 15]):
        rep.append(f"· যাত্রাপুস্তক: প্রত্যাশিত গঠন মেলেনি (প্রথম গোষ্ঠী {ids[:3]}…"
                   f" ১১={'আছে' if g11 else 'নেই'} ১২={'আছে' if g12 else 'নেই'} "
                   f"১৩={'আছে' if g13 else 'নেই'}) — ছোঁয়া হলো না")
    else:
        for v in e["verses"]:
            if v["ch"] == 11:
                v["ch"] = 12
            elif v["ch"] == 12:
                v["ch"] = 13
        for g in e["suktas"]:
            if g["id"] == 11:
                g["id"] = 12
            elif g["id"] == 12:
                g["id"] = 13
        e["suktas"].sort(key=lambda g: g["id"])
        e["missing"] = [11]     # প্রকৃত অধ্যায় ১১ই উৎসে ছিল (লগইন-দেয়ালের পিছনে)
        regen(e)
        fresh[p.name] = e
        if not dry:
            save(p, e)
        changed = True
        rep.append("✓ যাত্রাপুস্তক: গোষ্ঠী ১১→১২, ১২→১৩; missing=[১১]; "
                   f"পদ {e['count']} অপরিবর্তিত")

    # ── ৪) ওবাদিয়া: লেবেল-আবর্জনা ────────────────────────────────
    p = DATA / "ch31.json"
    o = load(p)
    def norm(x):
        # unicode-রূপ (য়/য-়), ব্ল্যাংকের পরিমাণ — সব এক করে তুলনা
        import unicodedata
        return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(x or ""))).strip()

    cur_bn = str(o.get("bn") or "")
    ob_bad = re.match(r"^৩১\.\s*ওবাদিয়া\s*\(Obadiah\)\s*1\s*Topic$", norm(cur_bn))
    if norm(cur_bn) == norm("ওবাদিয়া"):
        rep.append("· ওবাদিয়া: ইতিমধ্যে ঠিক আছে")
    elif ob_bad:
        # হুবহু সেই আবর্জনা-লেবেল («৩১. ওবাদিয়া (Obadiah) 1 Topic») — ছাঁচে
        # মিললেই বদলানো হয়; অন্য কিছু হলে হাত দেওয়া হয় না।
        o["bn"], o["en"] = "ওবাদিয়া", "Obadiah"
        if not dry:
            save(p, o)
        changed = True
        rep.append("✓ ওবাদিয়া: bn ফিল্ডের «৩১. … 1 Topic» সরানো হলো")
    else:
        rep.append(f"· ওবাদিয়া: অপ্রত্যাশিত bn={cur_bn!r} — ছোঁয়া হলো না")

    # ── ৪.৫) ম্যানিফেস্ট: ওবাদিয়ার নাম ───────────────────────────
    mp = DBG / "bible_books.json"
    if mp.exists():
        m = load(mp)
        ob = next((x for x in m if x.get("i") == 31), None)
        if ob and re.match(r"^৩১\.\s*ওবাদিয়া\s*\(Obadiah\)\s*1\s*Topic$",
                           norm(ob.get("bn"))):
            ob["bn"], ob["en"] = "ওবাদিয়া", "Obadiah"
            if not dry:
                save(mp, m)
            changed = True
            rep.append("✓ ম্যানিফেস্ট: ওবাদিয়ার নাম ঠিক হলো")

    # ── ৫) ইংরেজি raw: পদ-শুরুর টীকা-চিহ্ন ও লেজের টীকা-তালিকা ────
    # পুরোনো পার্সার পদ-সংখ্যা বোঝার সময় লাইন-শুরুর সংখ্যাগুলো টীকা-লিঙ্ক
    # হিসেবেও চিনত না, তাই পাঠে জমে গিয়েছিল («2 Paul, a slave…»); আবার কিছু
    # পদে পুরো টীকা-তালিকা লেজে জোড়া লেগেছে («…no shame. 1 [4b-25] …»).
    # নতুন পার্সার (_en_parts) এগুলো ঠিক করে — পুরোনো raw-কেও একই নিয়মে
    # পরিষ্কার করা হয়, যাতে রি-ওয়াক ছাড়াই ঠিক পাঠ পাওয়া যায়।
    RAW = DATA / "en/raw"
    stripped = 0
    for fp in sorted(RAW.glob("raw*.json")):
        d = load(fp)
        hit = 0
        for ch, vs in (d.get("chapters") or {}).items():
            for v in vs:
                en = v.get("en") or ""
                # (ক) লেজের টীকা-তালিকা
                clean = strip_footnotes(en)
                if clean != en:
                    en = clean
                    hit += 1
                # (খ) শুরুর সংখ্যা — টীকা-চিহ্ন, কেবল ব্যতিক্রম: সংখ্যাটি
                # ঠিক পরের পদ-নম্বর হলে সেটি পাঠের নিজের নম্বর (কাটা হয় না)
                m = re.match(r"^(\d{1,3})\s+(\S)", en)
                if m:
                    n0 = int(m.group(1))
                    after = en[m.start(2):]
                    # পাঠের নিজের নম্বরও হতে পারে («2 Joram, son of Ahab…»
                    # আসলে Kins 2:3-এর ২ নং পদ) — তখনই রাখি, যখন ঠিক পরের
                    # পদ-নম্বর হয় এবং পাশে টীকা-আবর্জনা না থাকে।
                    keep = (n0 == v["vn"] + 1
                            and not re.match(r"^\s*\[", after)
                            and "*" not in en[:80])
                    if not keep:
                        en = after
                        hit += 1
                if en != (v.get("en") or ""):
                    v["en"] = en
        # সিলমোহর প্রতিটি ফাইলে, বদল হোক বা না হোক: এই রিপেয়ারের পর সব raw
        # নতুন পার্সারের নিয়মে পরিষ্কার। পিভি না বাড়ালে পরের রিওয়াকের
        # save_raw এগুলো «পুরোনো দূষিত» ভেবে ফেলে দিত — সামসঙ্গীতের মতো বই
        # আবার অসম্পূর্ণ হয়ে যেত।
        try:
            import fetch_bible_en as _FE
            if d.get("pvEn") != _FE.PV_EN:
                d["pvEn"] = _FE.PV_EN
                hit += 1
        except Exception:  # noqa: BLE001
            pass
        if hit:
            if not dry:
                save(fp, d)
            stripped += hit
    if stripped:
        changed = True
        rep.append(f"✓ ইংরেজি raw: {stripped}টি পদ পরিষ্কার হলো "
                   "(শুরুর টীকা-চিহ্ন + লেজের টীকা-তালিকা)")

    # ── ৬) সূচি ───────────────────────────────────────────────────
    idx = load(DATA / "index.json")
    rep.append("")
    rep.append("বই-ভিত্তিক পদ (আগে → পরে):")
    total_new = 0
    for c in idx["chapters"]:
        fp = DATA / f"ch{c['id']}.json"
        if not fp.exists():
            continue
        # শুকনো-রানে ফাইল ছোঁয়া হয়নি — কিন্তু বদলটা জানা দরকার। তাই যে
        # বইগুলো এই রানে হাতে-গোনা হয়ে আছে, সেগুলোর হিসাব স্মৃতি থেকে।
        d = load(fp)
        if dry and fp.name in fresh:
            d = fresh[fp.name]
        total_new += d["count"]
        mark = "" if before.get(c["id"]) == d["count"] else "  ←"
        rep.append(f"  {c['id']:>2}. {d['bn']:<14} {before.get(c['id'], 0):>5} → "
                   f"{d['count']:>5}{mark}")
    rep.insert(0, f"বাইবেল-রিপেয়ার · "
                  f"{'শুকনো-রান (কিছু লেখা হয়নি)' if args.dry_run else 'প্রয়োগ'}"
                  f" · মোট পদ {sum(before.values())} → {total_new}")
    DBG.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print("\n".join(rep))
        return 0

    if changed:
        # সূচি নতুন করে — ফাইলগুলোর বর্তমান সত্য থেকেই
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import fetch_bible as FB
        books = FB.load_manifest()
        idx2 = FB.write_index(books)
        rep.append(f"✓ সূচি: পুস্তক {len(idx2['chapters'])} · পদ {idx2['total']} · "
                   f"বাংলাসহ {idx2['withBn']}")

    # ── ৭) ইংরেজি পুনঃমিলন ────────────────────────────────────────
    if not args.no_join:
        import fetch_bible_en as FE
        rc = FE.join_bookkeeping()
        rep.append(f"✓ ইংরেজি join: rc={rc}")
        done = DBG / "bible_en_done.txt"
        if done.exists():
            done.unlink()      # পুরোনো সমাপ্তি-চিহ্ন বাতিল; নতুন রান নিজে দেবে
            rep.append("· পুরোনো bible_en_done.txt মুছে ফেলা হলো (নতুন রান সত্য দেবে)")

    # ── ৮) বেসলাইন ───────────────────────────────────────────────
    import guard_data as G
    base = json.loads(G.BASE_FILE.read_text(encoding="utf-8")) \
        if G.BASE_FILE.exists() else {"slugs": {}}
    base.setdefault("slugs", {})
    idx3 = load(DATA / "index.json")
    base["slugs"]["bible"] = {"total": G.site_total(idx3),
                              "withBn": idx3.get("withBn", 0),
                              "chapters": len(idx3["chapters"])}
    G.BASE_FILE.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    rep.append(f"✓ বেসলাইন: bible → {base['slugs']['bible']}")

    txt = "\n".join(rep) + "\n"
    (DBG / "bible_repair.txt").write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
