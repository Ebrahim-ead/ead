#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""অথর্ববেদ সংহিতা — ebanglalibrary.com থেকে শুধু বাংলা অনুবাদ নামায়।

উৎস-বই: «অথর্ববেদ সংহিতা (সম্পাদনা: দিলীপ মুখোপাধ্যায়)», সিরিজ «বাংলা বেদ»।
গঠন: ২০ কাণ্ড → অনুবাক (লেসন-পাতা) → সূক্ত → মন্ত্র।
প্রতি অনুবাক-পাতায় মন্ত্রের বাংলা অনুবাদ থাকে («বঙ্গানুবাদ – …»)।

ব্যবহারকারীর সিদ্ধান্ত (২০২৬-১১-০১):
  · সম্পূর্ণ ২০ কাণ্ড না পেলে অথর্ববেদ যোগ হবে না — তাই ২০টিই নামে।
  · «শুধুমাত্র বাংলা» — সংস্কৃত (देवनागरी) মূলপাঠ বাদ।
  · «মন্ত্রার্থ আলোচনা» ও «টীকা/বিনিয়োগ» বাদ।

পাতা-ধাঁচ (যাচাই করা):
  প্রথম সূক্তি : মেধাজননম্ [ঋষি : অথর্বা। দেবতা : বাচস্পতি। ছন্দ : ...]
  <संस्कृत মন্ত্র>
  বঙ্গানুবাদ – <বাংলা>
  ...
  দ্বিতীয় সূক্তি : ...
  ...
  টীকা/বিনিয়োগ – <বাদ>

নম্বর-নীতি (ঋগ্বেদের মতোই): কাণ্ডের ভেতরে মন্ত্র `n` = ১…N ক্রমিক,
আর প্রতিটি সূক্তে `vn` = ১…k (দেখানোর নম্বর)।
"""
import argparse
import html as htmllib
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://www.ebanglalibrary.com"
BOOK = (BASE + "/books/%e0%a6%85%e0%a6%a5%e0%a6%b0%e0%a7%8d%e0%a6%ac%e0%a6%ac%e0%a7%87%e0%a6%a6-"
        "%e0%a6%b8%e0%a6%82%e0%a6%b9%e0%a6%bf%e0%a6%a4%e0%a6%be-%e0%a6%b8%e0%a6%ae%e0%a7%8d"
        "%e0%a6%aa%e0%a6%be%e0%a6%a6%e0%a6%a8/")
SRC = "বাংলা অনুবাদ — ebanglalibrary.com"
OUT = ROOT / "assets/grantho/data/atharvaveda"
UA = "Mozilla/5.0 (compatible; ead-grantho/1.0; +https://github.com/Ebrahim-ead/ead)"
DEV = re.compile(r"[\u0900-\u097F]")          # দেবনাগরী
BN = re.compile(r"[\u0980-\u09FF]")

# কাণ্ডের বাংলা নাম
KANDA_BN = {
    1: "প্রথম", 2: "দ্বিতীয়", 3: "তৃতীয়", 4: "চতুর্থ", 5: "পঞ্চম", 6: "ষষ্ঠ",
    7: "সপ্তম", 8: "অষ্টম", 9: "নবম", 10: "দশম", 11: "একাদশ", 12: "দ্বাদশ",
    13: "ত্রয়োদশ", 14: "চতুর্দশ", 15: "পঞ্চদশ", 16: "ষোড়শ", 17: "সপ্তদশ",
    18: "অষ্টাদশ", 19: "ঊনবিংশ", 20: "বিংশ",
}
BN_DIGITS = "০১২৩৪৫৬৭৮৯"


def bnnum(x):
    return "".join(BN_DIGITS[int(c)] if c.isdigit() else c for c in str(x))


def to_int(s):
    if s is None:
        return 0
    s = str(s).strip()
    for i, d in enumerate(BN_DIGITS):
        s = s.replace(d, str(i))
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


# ---------------- নেটওয়ার্ক ----------------
def get(url, tries=4, timeout=60):
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "bn,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                      # noqa: BLE001
            last = e
            time.sleep(2.5 * (t + 1))
    print(f"   ! {type(last).__name__}: {url[:80]}", flush=True)
    return ""


# ---------------- পাঠ-নিষ্কাশন ----------------
BLOCK_TAGS = re.compile(r"</?(?:p|div|br|li|tr|h[1-6]|section|article|blockquote)\b[^>]*>",
                        re.I)


def html_text(h):
    """HTML → উপযোগী পাঠ। কেবল কাণ্ড-বিষয়বস্তুর অংশ নিই।"""
    # স্ক্রিপ্ট/স্টাইল/নেভিগেশন বাদ
    h = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", h, flags=re.S | re.I)
    # মূল পাঠ-অঞ্চল: ld-lesson-item / ld-focus-mode-content থাকলে তা-ই
    m = re.search(r'<div[^>]+class="[^"]*ld-focus-mode-content[^"]*"[^>]*>(.*)', h, re.S)
    body = m.group(1) if m else h
    # শিরোনামের আগের অংশ (বই-তালিকা/পাঠ-তালিকা) কেটে ফেলি
    cut = re.search(r'<h1[^>]*>.*?</h1>', body, re.S)
    if cut and len(body) > len(cut.group(0)) * 6:
        body = body[cut.start():]
    body = BLOCK_TAGS.sub("\n", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = htmllib.unescape(body)
    body = body.replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in body.split("\n")]
    return [ln for ln in lines if ln]


ORD = (r"(?:প্রথম|দ্বিতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম|"
       r"একাদশ|দ্বাদশ|ত্রয়োদশ|চতুর্দশ|পঞ্চদশ|ষোড়শ|সপ্তদশ|অষ্টাদশ|ঊনবিংশ|"
       r"বিংশ|একবিংশ|দ্বাবিংশ|ত্রয়োবিংশ)")
# শিরোনাম আসে দুই ধাঁচে: «প্রথম সূক্ত : …» আর «দ্বিতীয় অনুবাক প্রথম সূক্ত : …»
SUKTA_RE = re.compile(r"^\**\s*(?:" + ORD + r"\s+অনুবাক\s+)?" + ORD + r"\s*সূক্ত")
# সূক্ত-শিরোনাম চেনার রূপ। বাস্তব পাতায় শিরোনামের আগে গ্রন্থ-অগ্রভাগও আসে:
#   «অথর্ববেদ – সংহিতা — দ্বিতীয় কাণ্ড প্রথম অনুবাক প্রথম সূক্ত : পরমং ধাম»
# তাই শুরুর ^-অ্যাংকর তুলে দিলাম; বদলে লাইনটিতে «সূক্ত :» থাকা বắt্য।
# নীতি: «… অনুবাক … সূক্ত :» ধাঁচটা অগ্রভাগসহও ধরা পড়ে, আর «মন্ত্রঃ …»
# লাইন (সংস্কৃত) কোথাও «সূক্ত :» পায় না — তাই নিরাপদ।
SUKTA_HEAD = re.compile(r"^(?:.*?\s)?(?:" + ORD + r"\s+অনুবাক\s+)?(?:কাণ্ড\s+)?"
                        r"(?:" + ORD + r"\s*)?সূক্ত\s*[:ঃ]")
SUKTA_ONLY = SUKTA_HEAD
BN_LABEL = re.compile(r"^\**\s*বঙ্গানুবাদ")
# আলোচনা/টীকা যেখানে শুরু হয়। বাস্তব পাতায় শিরোনাম আসে «সূক্তস্য বিনিয়োগঃ—»,
# «সূক্তস্য বিনিয়োগঃ –», «টীকা–», «মন্ত্রার্থ আলোচনা» ধাঁচে — তাই «বিনিয়োগ»
# শব্দটিই যেকোনো জায়গায় থাকলে থামি (আগে ^ দিয়ে শুরু-শব্দ ধরা হতো, ফলে
# «সূক্তস্য বিনিয়োগঃ» মিলত না আর পুরো আলোচনা পাঠে ঢুকে যেত)।
# ⚠ «বঙ্গানুবাদ» লাইনে এই শব্দ থাকতে পারে না, তাই নিরাপদ।
STOP_LABEL = re.compile(r"^\**\s*(?:মন্ত্রার্থ|মন্ত্ৰার্থ|টীকা|টীকাল)")
NUM_END = re.compile(r"[।॥]\s*([০-৯]{1,3})\s*[।॥]?\s*$")


def strip_md(s):
    """পাতার **মোটা** চিহ্ন ও খালি স্পেস বাদ।"""
    s = s.replace("**", "").replace("\\", "")
    return re.sub(r"\s+", " ", s).strip()


def is_bn_heavy(s):
    return len(BN.findall(s)) >= max(3, len(s) * 0.25)


def parse_page(lines):
    """পাতার লাইন → [{sukta, title, verses:[{bn, vn}]}] (আলোচনা ও সংস্কৃত বাদ)।

    নীতি: উৎসে অনুবাদ সবসময় «বঙ্গানুবাদ –» লেবেলের পরে থাকে; লেবেলের আগের
    লাইনগুলো সংস্কৃত মন্ত্র। অথর্ববেদ বাংলা লিপিতেই ছাপা, তাই লিপি দেখে আলাদা
    করা যায় না — লেবেলই একমাত্র নির্ভরযোগ্য চিহ্ন।
    """
    suktas, cur, buf, seen_bn = [], None, [], False
    for raw in lines:
        ln = strip_md(raw)
        if not ln:
            continue
        # কেবল সত্যিকারের সূক্ত-শিরোনাম — সংস্কৃত «মন্ত্রঃ …» লাইন কখনোই নয়
        if (SUKTA_ONLY.match(ln) or SUKTA_HEAD.match(ln)) and "মন্ত্রঃ" not in ln:
            if cur is not None and buf and seen_bn:
                _push_sukta(suktas, cur, buf)
            cur, buf, seen_bn = {"title": ln}, [], False
            continue
        if cur is None:
            continue                              # অনুবাক-শিরোনাম/ভূমিকা — বাদ
        # আলোচনা শুরু: «টীকা/মন্ত্রার্থ» দিয়ে শুরু, অথবা যেকোনো জায়গায়
        # «বিনিয়োগ» (যেমন «সূক্তস্য বিনিয়োগঃ—»)
        if (STOP_LABEL.match(ln) or "বিনিয়োগ" in ln) and not BN_LABEL.match(ln):
            if buf and seen_bn:
                _push_sukta(suktas, cur, buf)
            cur, buf, seen_bn = None, [], False   # আলোচনা/টীকা — বাদ
            continue
        if BN_LABEL.match(ln):
            seen_bn = True
            buf.append(BN_LABEL.sub("", ln).lstrip(" –—‐-:").strip())
            continue
        if BN_LABEL.search(ln):
            seen_bn = True
            _, tail = BN_LABEL.split(ln, maxsplit=1)
            buf.append(tail.lstrip(" –—‐-:").strip())
            continue
        if not seen_bn:
            continue                              # সংস্কৃত মন্ত্র — বাদ
        buf.append(ln)
    if cur is not None and buf and seen_bn:
        _push_sukta(suktas, cur, buf)
    del lines
    return suktas


SUKTA_NAME = re.compile(r"সূক্ত[ি]?\s*[:ঃ]\s*\**\s*(.*?)\s*(?:\[\s*ঋষি|\**ঋষি|$)")


def sukta_name(title):
    """শিরোনাম-লাইন থেকে সূক্তের নাম («শত্রুনাশনম্») বের করি।"""
    m = SUKTA_NAME.search(title or "")
    nm = (m.group(1) if m else "").strip(" :ঃ*-–—")
    nm = re.sub(r"\s+", " ", nm)
    return nm if 1 < len(nm) <= 40 else ""


def _push_sukta(out, cur, buf):
    vs = split_translations(buf)
    if vs:
        cur["verses"] = vs
        cur["name"] = sukta_name(cur.get("title", ""))
        out.append(cur)


def split_translations(chunks):
    """অনুবাদ-অনুচ্ছেদ জোড়া লাগিয়ে মন্ত্র-নম্বর ধরে ভাগ করি।

    উৎসে প্রতি মন্ত্রের অনুবাদ শেষ হয় নম্বর+দাঁড়িতে, কয়েক রকমে:
        «।। ১২॥»   «। ১২।»   «॥ ১২॥»   বাংলা-দাঁড়ি: «৷৷ ১।» / «৷৷ ২৷»
    এক মন্ত্র কয়েক লাইনে ভাঙা থাকতে পারে — তাই জোড়া লাগিয়ে তারপর ভাগ।

    ⚠ কেন ক্রমিক-যাচাই: দাঁড়ির পর যেকোনো সংখ্যা ধরা হলে বাক্যের ভেতরের
      সংখ্যাও («১৯০৭ সালে») কেটে পড়ত। তাই কেবল তখনই ভাগ করি যখন নম্বরটি
      পরের প্রত্যাশিত ক্রম (১, ২, ৩ …) হয় — নইলে ওই সংখ্যা পাঠের অংশ।
    """
    text = " ".join(x for x in chunks if x)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    pat = re.compile(r"(?<=[।॥৷])\s*([০-৯]{1,3})\s*(?:[।॥৷]{1,2})?")
    out, start, expect = [], 0, 1
    for m in pat.finditer(text):
        num = int(m.group(1).translate(BN_DIGITS))
        if num != expect:
            continue                       # বাক্যের ভেতরের সংখ্যা — পাঠেই থাকুক
        seg = text[start:m.start()].strip()
        if len(seg) >= 8:
            out.append({"bn": seg, "vn": expect})
            expect += 1
            start = m.end()
    tail = text[start:].strip(" ।॥৷")
    # শেষ অংশ যদি নম্বরহীন হয়: ছোট লেজ আগের মন্ত্রে জুড়ি, নইলে নতুন মন্ত্র
    if tail and len(tail) >= 8:
        if out and len(tail) < 40:
            out[-1]["bn"] = (out[-1]["bn"] + " " + tail).strip()
        else:
            out.append({"bn": tail, "vn": expect})
    return out


# ---------------- তালিকা ----------------
LINK_RE = re.compile(r'href="(https://www\.ebanglalibrary\.com/(?:lessons|topics)/'
                     r'[^"#?]+)"[^>]*>\s*([^<]{0,90}?)</a>')
# লেসন-URL-এর স্লাগেই ক্রম থাকে: «…/lessons/০১।১-প্রথম-কাণ্ড-প্রথম-অনুবাক/»
SLUG_NUM = re.compile(r"/lessons/([০-৯]{1,2})\s*।\s*([০-৯]{1,2})")
# শিরোনামের সংখ্যা (স্লাগ নষ্ট হলেও ফলব্যাক)
TITLE_NUM = re.compile(r"^([০-৯]{1,2})\s*।\s*([০-৯]{1,2})")
STOP_TITLE = re.compile(r"নিবেদন|ভূমিকা|সূচিপত্র|পরিশিষ্ট|গ্রন্থপঞ্জি")


def _page_rows(h):
    """এক পাতা HTML → [(kanda, anuvaka, url, title)]।

    ক্রম দুভাবে খুঁজি: আগে লেসন-URL-এর স্লাগে (নির্ভরযোগ্য — পুরো URL-ই
    বহু পৃষ্ঠায় দেখা যায়), না পেলে শিরোনামের «০১।১ …» লেখায়। ভূমিকা/
    সম্পাদকের নিবেদন বাদ যায়, কারণ সেগুলোতে সূক্ত-শিরোনাম নেই।
    """
    out, seen = [], set()
    for mm in LINK_RE.finditer(h or ""):
        u = htmllib.unescape(mm.group(1))
        if u in seen:
            continue
        t = re.sub(r"\s+", " ", htmllib.unescape(mm.group(2))).strip()
        if STOP_TITLE.search(t):
            continue
        num = SLUG_NUM.search(urllib.parse.unquote(u)) or TITLE_NUM.match(t)
        if not num:
            continue
        kanda, anuv = to_int(num.group(1)), to_int(num.group(2))
        if not (1 <= kanda <= 20):
            continue
        seen.add(u)
        out.append((kanda, anuv, u, t or f"{bnnum(kanda)}।{bnnum(anuv)}"))
    return out


def lesson_index(limit=0):
    """সব অনুবাক-পাতার (কাণ্ড, অনুবাক, url, শিরোনাম) তালিকা — BFS।

    কেন BFS: বই-পাতার সূচি আংশিক (ব্রাউজারে কেবল কাণ্ড ১–৭ দেখায়; মন্তব্যেও
    পাঠকেরা «বাকি কাণ্ড কোথায়?» লিখেছেন)। কিন্তু প্রতিটি লেসন-পাতার ভেতরে
    পুরো কোর্সের সাইডবার-তালিকা থাকে (নিজের পেজিনেশনে)। তাই বই-পাতা থেকে
    শুরু করে যতগুলো লেসন-পাতার সন্ধান পাওয়া যায় সব ঘুরে লিংক জমা করি —
    এক প্যাটার্ন/এক অঞ্চল বদলালেও বাকি কাণ্ড বাদ পড়ে না।

    ব্যবহারকারীর শর্ত: ২০ কাণ্ড সম্পূর্ণ না হলে গ্রন্থ যোগ হবে না — তাই অর্ধেক
    তালিকা নিয়ে সন্তুষ্ট হই না, যতটা পাওয়া যায় সব পথে খুঁজি।
    """
    seen_url, rows, queue = set(), [], [BOOK]
    pages_done = 0
    while queue and pages_done < 400:
        url = queue.pop(0)
        pages_done += 1
        h = get(url)
        if not h:
            continue
        before = len(rows)
        for kanda, anuv, u, t in _page_rows(h):
            if u in seen_url:
                continue
            seen_url.add(u)
            rows.append({"kanda": kanda, "anuvaka": anuv, "url": u, "title": t})
            # প্রতিটি নতুন লেসন-পাতাও ঘুরব — তার সাইডবারে আরও লেসন থাকতে পারে
            queue.append(u)
        # বই-পাতার নিজস্ব পেজিনেশন (৩ পৃষ্ঠা: «1 of 3»)
        if url == BOOK:
            m = re.search(r"(\d{1,3})\s*of\s*(\d{1,3})", h)
            if m:
                for i in range(2, min(int(m.group(2)), 12) + 1):
                    queue.append(f"{BOOK}?ld-courseinfo-lesson-page={i}")
        # লেসন-পাতার সাইডবার-পেজিনেশন (?ld-lesson-page=N) — পূর্ণ কোর্স-তালিকা
        elif "?" not in url:
            for i in (1, 2, 3, 4, 5):
                queue.append(f"{url}?ld-lesson-page={i}")
        if len(rows) > before:
            print(f"   · নতুন {len(rows) - before}টি লেসন-লিংক "
                  f"({rows[-1]['title'][:30]}) — মোট {len(rows)}", flush=True)
        if limit and len(rows) >= limit:
            break
        time.sleep(0.6)
    rows.sort(key=lambda r: (r["kanda"], r["anuvaka"]))
    # কাণ্ড-ভিত্তিক সারসংক্ষেপ (কোন কাণ্ডে কত অনুবাক পাওয়া গেল)
    per = {}
    for r in rows:
        per[r["kanda"]] = per.get(r["kanda"], 0) + 1
    print("কাণ্ড-কভারেজ: " + " · ".join(f"{k}:{v}" for k, v in sorted(per.items())),
          flush=True)
    return rows


# ---------------- লেখা ----------------
def write(out, index_rows):
    OUT.mkdir(parents=True, exist_ok=True)
    by_kanda = {}
    for r in index_rows:
        by_kanda.setdefault(r["kanda"], []).append(r)

    chapters, ok_kanda, fail = [], [], []
    for kanda in sorted(by_kanda):
        rows = by_kanda[kanda]
        verses, suktas, kept_pages = [], [], []
        for r in rows:
            h = get(r["url"])
            if not h:
                fail.append(r["title"])
                continue
            suktas_raw = parse_page(html_text(h))
            if not suktas_raw:
                fail.append(r["title"])
                continue
            kept_pages.append(r["url"])
            for s in suktas_raw:
                sid = len(suktas) + 1
                frm = len(verses) + 1
                for v in s["verses"]:
                    verses.append({"n": len(verses) + 1, "sk": "", "bn": v["bn"],
                                   "spk": "", "bnSrc": SRC, "vn": v["vn"]})
                if len(verses) >= frm:
                    suktas.append({"id": sid, "from": frm, "to": len(verses),
                                   "mantra": len(verses) - frm + 1,
                                   "name": s.get("name") or ""})
            print(f"   · {r['title'][:44]}: {len(suktas)} সূক্ত / {len(verses)} মন্ত্র",
                  flush=True)
            time.sleep(0.5)
        if not verses:
            print(f"   ✗ কাণ্ড {kanda}: কিছু পাওয়া গেল না", flush=True)
            fail.extend(r["title"] for r in rows)
            continue
        # সূক্তে মন্ত্র-নম্বর ১ থেকে (ঋগ্বেদের নীতি)
        for s in suktas:
            for i, v in enumerate(verses[s["from"] - 1:s["to"]], start=1):
                v["vn"] = i
        obj = {"id": kanda, "bn": f"কাণ্ড {bnnum(kanda)}", "count": len(verses),
               "from": 1, "to": len(verses), "verses": verses,
               "url": kept_pages[0] if kept_pages else BOOK,
               "suktas": suktas, "suktaCount": len(suktas),
               "shlokaCount": len(verses), "withBn": len(verses)}
        with open(OUT / f"ch{kanda}.json", "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        chapters.append({"id": kanda, "bn": obj["bn"], "count": len(verses),
                         "from": 1, "to": len(verses), "withBn": len(verses),
                         "suktaCount": len(suktas), "shlokaCount": len(verses),
                         "grid": {"count": len(suktas)}})
        ok_kanda.append(kanda)
        print(f"✓ কাণ্ড {bnnum(kanda)}: {len(suktas)} সূক্ত · {len(verses)} মন্ত্র",
              flush=True)

    rep = ["কাণ্ড পাওয়া গেল: %s" % ok_kanda, "ব্যর্থ পাতা: %s" % (fail or "—")]
    # কোন কাণ্ড একটিও পাওয়া গেল না — সেটাই সিদ্ধান্তের কারণ
    missing_rows = [k for k in range(1, 21) if k not in by_kanda]
    if missing_rows:
        rep.append("উৎসে লেসনই নেই (৪০৪): কাণ্ড %s" % missing_rows)
        rep.append("কারণ: ebanglalibrary-এ «অথর্ববেদ সংহিতা» বইটির সূচিতে ও "
                   "প্রতিটি লেসন-পাতার সাইডবারে কেবল কাণ্ড ১–৭-এর লেসন আছে "
                   "(সর্বোচ্চ ০৭।০৪)। কাণ্ড ৮–২০-এর কোনো লেসন-পাতা নেই — "
                   "সরাসরি চাইলে ৪০৪। পাঠকেরাও মন্তব্যে একই কথা লিখেছেন "
                   "(«বাকি কান্ড কোথায়?»)।")
    (OUT / "_fetch_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")

    # ---- শর্ত: ২০ কাণ্ড সম্পূর্ণ + মন্ত্র-সংখ্যা যুক্তিসঙ্গত না হলে ইনডেক্স নয় ----
    total = sum(c["count"] for c in chapters)
    suk = sum(c["suktaCount"] for c in chapters)
    missing = [k for k in range(1, 21) if k not in ok_kanda]
    if missing:
        print(f"\n⛔ কাণ্ড {missing} পাওয়া যায়নি — ইনডেক্স লেখা হবে না "
              f"(ব্যবহারকারীর শর্ত: সম্পূর্ণ ২০ কাণ্ড)। ch ফাইল রাখা হলো, "
              f"পরের রানে বাকিটা নামবে।", flush=True)
        return {"ok": False, "missing": missing, "chapters": chapters}

    # শৌণক সংহিতা: ৬,০৭৯ মন্ত্র (প্রায় ৬,০০০)। কম পেলে পার্স/লিংক সমস্যা।
    if total < 5000 or suk < 600:
        print(f"\n⛔ মোট {total} মন্ত্র / {suk} সূক্ত — প্রত্যাশার (৬,০৭৯ / ৭৩৪) "
              f"চেয়ে অনেক কম; পার্স বা লিংকে সমস্যা। ইনডেক্স লেখা হবে না।",
              flush=True)
        return {"ok": False, "missing": [], "chapters": chapters, "low": True}

    idx = {"slug": "atharvaveda", "bn": "অথর্ববেদ সংহিতা",
           "en": "Atharvaveda", "total": sum(c["count"] for c in chapters),
           "withBn": sum(c["withBn"] for c in chapters),
           "chapters": chapters, "verseWord": "মন্ত্র",
           "bnSrc": SRC,
           "note": "শুধু বাংলা অনুবাদ (সংস্কৃত মূলপাঠ বাদ) — ebanglalibrary.com; "
                   "প্রতিটি সূক্তে মন্ত্র-নম্বর ১ থেকে।",
           "suktaTotal": suk,
           "shlokaTotal": total,
           "groupWord": "সূক্ত", "chword": "কাণ্ড", "bookWord": "কাণ্ড"}
    with open(OUT / "index.json", "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print(f"\n✔ ইনডেক্স: {idx['withBn']}/{idx['total']} মন্ত্র · "
          f"{len(chapters)} কাণ্ড · {idx['suktaTotal']} সূক্ত", flush=True)
    for c in chapters:
        print(f"   কাণ্ড {c['id']}: {c['suktaCount']} সূক্ত · {c['count']} মন্ত্র",
              flush=True)
    return {"ok": True, "index": idx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-only", action="store_true", help="কেবল অনুবাক-তালিকা")
    ap.add_argument("--limit", type=int, default=0, help="পরীক্ষার জন্য কাণ্ড-সীমা")
    a = ap.parse_args()
    rows = lesson_index()
    print(f"অনুবাক-পাতা: {len(rows)}টি", flush=True)
    kd = {}
    for r in rows:
        kd[r["kanda"]] = kd.get(r["kanda"], 0) + 1
    print("কাণ্ডভিত্তিক:", kd, flush=True)
    (ROOT / "_atharva_lessons.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.list_only:
        return
    if a.limit:
        rows = [r for r in rows if r["kanda"] <= a.limit]
    res = write(OUT, rows)
    if not res.get("ok"):
        sys.exit(3)


if __name__ == "__main__":
    main()
