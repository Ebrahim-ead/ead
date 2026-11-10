#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""অথর্ববেদ সংহিতা — ebanglalibrary.com থেকে শুধু বাংলা অনুবাদ নামায়।

উৎস-বই: «অথর্ববেদ সংহিতা (সম্পাদনা: দিলীপ মুখোপাধ্যায়)», সিরিজ «বাংলা বেদ»।
গঠন: ২০ কাণ্ড → অনুবাক (লেসন-পাতা) → সূক্ত → মন্ত্র।

ব্যবহারকারীর সিদ্ধান্ত:
  · সম্পূর্ণ ২০ কাণ্ড না পেলে অথর্ববেদ যোগ হবে না — তাই ২০টিই নামায়।
  · «শুধুমাত্র বাংলা» — সংস্কৃত মূলপাঠ বাদ।
  · «মন্ত্রಾರ্থ আলোচনা», «টীকা», «বিনিয়োগ» — কিছুই সাইটে যাবে না।

পাতার আসল গঠন (সাইট থেকে যাচাই করা):
  অথর্ববেদ – সংহিতা — বিংশ কাণ্ড প্রথম অনুবাক প্রথম সূক্ত [ঋষি : …। দেবতা : …।]
  ইন্দ্র ত্ব বৃষভং বয়ং … স পাহি মধ্বে অন্ধসঃ ॥১॥        ← সংস্কৃত (বাদ)
  বঙ্গানুবাদ –হে ইন্দ্র! তুমি পরমৈশ্বর্যবান …৷৷ ১।            ← রাখি
  …৷৷ ২৷                                             ← রাখি
  বিনিয়োগ ও টীকা— …                                    ← এখান থেকে বাদ
  …
  দ্বিতীয় সূক্তি : …                                    ← আবার শুরু

⚠ যেসব ফাঁদে আগে পড়েছি (মন্তব্যে বাঁচিয়ে রাখা হলো):
  ১. শিরোনামের শুরুতে গ্রন্থ-অগ্রভাগ থাকতে পারে; কোলনও নাও থাকতে পারে।
  ২. «মন্ত্ৰাৰ্থ» অসমীয়া «্ৰ» (U+09CD+U+09F0) দিয়েও লেখা, আর লাইনের মাঝে আসে।
  ৩. আলোচনা সবসময় পাতার শেষে নয় — মাঝেও আসে, তারপর পরের সূক্ত শুরু হয়।
  ৪. লেসন-URL-এর স্লাগ শেষে কেটে যায় («…-প্রথম-অন/»), তাই স্লাগ থেকে
     পুনর্গঠন অসম্ভব — অনুমান করতে হয়।
  ৫. সাইডবার-পেজিনেশন «N of 3» পর্যন্ত; কেবল প্রথম পাতা দেখলে শেষ কাণ্ড হারায়।
"""
import argparse
import html as htmllib
import json
import pathlib
import re
import sys
import time
import urllib.error
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
BN_DIGITS = "০১২৩৪৫৬৭৮৯"

# কাণ্ড ও অনুবাকের ক্রম-বাচক শব্দ (URL-অনুমান ও নাম বানাতে লাগে)
ORD_SLUG = ["প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম",
            "অষ্টম", "নবম", "দশম", "একাদশ", "দ্বাদশ", "ত্রয়োদশ", "চতুর্দশ",
            "পঞ্চদশ", "ষোড়শ", "সপ্তদশ", "অষ্টাদশ", "ঊনবিংশ", "বিংশ"]
# কাণ্ড ৬-এ ১৩টি অনুবাক — সবচেয়ে বেশি
MAX_ANUV = 13


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
_CACHE = {}


def safe_url(u):
    """URL-এ বাংলা থাকলে percent-encode — http.client ASCII চায়।

    fetch_ebl.py-এর প্রমাণিত ধাঁচ; নইলে বাংলা-স্লাগের অনুরোধ ব্যর্থ হয়।
    """
    if not u:
        return u
    p = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((
        p.scheme or "https", p.netloc,
        urllib.parse.quote(p.path, safe="/%"),
        urllib.parse.quote_plus(p.query, safe="=&%") if p.query else "",
        ""))


def get(url, tries=5, timeout=75):
    """পাতা নামাই। 404 হলে None; অন্য ব্যর্থতায় বারবার চেষ্টা।

    None আর '' আলাদা রাখা জরুরি — নইলে «সাইট ব্লক করেছে» আর «পাতায় কিছু
    নেই» একই দেখায়, আর রিপোর্টে ভুল সিদ্ধান্ত লেখা হয়।
    """
    url = safe_url(url)
    if url in _CACHE:
        return _CACHE[url]
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "bn,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read().decode("utf-8", "replace")
                _CACHE[url] = data
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"   ! HTTP {e.code} — {url[-60:]}", flush=True)
            last = e
        except Exception as e:                        # noqa: BLE001
            print(f"   ! {type(e).__name__}: {str(e)[:60]} — {url[-46:]}", flush=True)
            last = e
        time.sleep(min(40, 3 * (t + 1)))
    print(f"   ✗ চেষ্টা শেষ, ব্যর্থ ({type(last).__name__})", flush=True)
    return None


# ---------------- HTML → লাইন ----------------
BLOCK_TAGS = re.compile(
    r"</?(?:p|div|br|li|tr|h[1-6]|section|article|blockquote)\b[^>]*>", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def html_text(h):
    """HTML → লাইন-তালিকা। কেবল পাঠ-অঞ্চল নিই, নেভিগেশন বাদ।"""
    h = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", h, flags=re.S | re.I)
    m = re.search(r'<div[^>]+class="[^"]*ld-focus-mode-content[^"]*"[^>]*>(.*)', h, re.S)
    body = m.group(1) if m else h
    # শিরোনামের আগে বই-তালিকা/পাঠ-তালিকা থাকে — কেটে ফেলি
    cut = re.search(r"<h1[^>]*>.*?</h1>", body, re.S)
    if cut and len(body) > len(cut.group(0)) * 6:
        body = body[cut.start():]
    body = BLOCK_TAGS.sub("\n", body)
    body = htmllib.unescape(TAG_RE.sub("", body))
    body = body.replace("\u00a0", " ").replace("\u200b", "")
    return [re.sub(r"[ \t]+", " ", ln).strip() for ln in body.split("\n")
            if ln.strip()]


def strip_md(s):
    """পাতার **মোটা** চিহ্ন, ব্যাকস্ল্যাশ ও অতিরিক্ত ফাঁকা বাদ।"""
    s = s.replace("**", "").replace("\\", "")
    return re.sub(r"\s+", " ", s).strip()


# ---------------- চেনার নিয়ম ----------------
# ক্রম-বাচক শব্দ («প্রথম» … «বিংশ») — সূক্ত ও অনুবাক দুটোতেই ব্যবহৃত
ORD = "(" + "|".join(ORD_SLUG) + ")"

# সূক্ত-শিরোনাম। আসল রূপ:
#   «অথর্ববেদ – সংহিতা — বিংশ কাণ্ড প্রথম অনুবাক প্রথম সূক্ত [ঋষি : …]»
#   «দ্বিতীয় সূক্তি : ভুবনপতিসূক্তম»   «দ্বিতীয় অনুবাক প্রথম সূক্ত : …»
# তাই: লাইনে «সূক্ত/সূক্তি» + আগে ক্রম-বাচক শব্দ থাকলেই শিরোনাম — কোলন
# ঐচ্ছিক, শুরুতে গ্রন্থ-অগ্রভাগ থাকলেও চলে।
# বাদ: «মন্ত্রঃ» দিয়ে শুরু (সংস্কৃত পাঠ), আর ২২০+ অক্ষরের লাইন (পাঠ, শিরোনাম নয়)।
SUKTA_HEAD = re.compile(r"^(?!মন্ত্রঃ)(?=.{0,220}$)(?=.*" + ORD + r"\s*সূক্ত[ি]?).*$")

# অনুবাদ-লেবেল — সংস্কৃতের পরেই আসে। অথর্ববেদের সংস্কৃতও বাংলা লিপিতে ছাপা,
# তাই লিপি নয় — এই লেবেলই একমাত্র নির্ভরযোগ্য চিহ্ন।
BN_LABEL = re.compile(r"^बंगानुवाद|^বঙ্গানুবাদ")

# আলোচনা/টীকা শুরু। «মন্ত্ৰাৰ্থ» অসমীয়া «্ৰ» (U+09CD+U+09F0) দিয়েও লেখা,
# তাই র-এর সব রূপের জন্য অক্ষর-শ্রেণি দিয়ে লিখি।
_RA = r"[রৰ]"
_RAFALA = r"(?:[রৰ]|্ৰ|ৰ)"
ALOC = re.compile(
    r"ম\s*ন\s*্?\s*[তত]\s*্?\s*" + _RA + r"\s*্?\s*" + _RAFALA +
    r"\s*া\s*্?\s*" + _RA + r"\s*্?\s*" + _RAFALA + r"\s*্থ")
# লাইনের *যেকোনো* জায়গায় এই শব্দগুলো থাকলে আলোচনা শুরু
ALOC_WORDS = ("আলোচনা", "বিনিয়োগ", "টীকা", "টীকাল", "মন্ত্ৰাৰ্থ", "মন্ত্রাৰ্থ",
              "মন্ত্রার্থ")


def is_aloc(ln):
    """এই লাইনটি কি আলোচনা/টীকা/বিনিয়োগের শুরু?"""
    if BN_LABEL.match(ln):
        return False                     # অনুবাদ-লাইনে ডেকে ফেলার ভয় নেই
    if ALOC.search(ln):
        return True
    return any(w in ln for w in ALOC_WORDS)


def is_sukta_head(ln):
    return bool(SUKTA_HEAD.match(ln)) and "মন্ত্রঃ" not in ln


# ---------------- মন্ত্রে ভাগ ----------------
# মন্ত্র-শেষের নম্বর কয়েক রকম আসে:
#   «।। ১২॥»  «। ১২।»  «॥ ১২॥»  আর বাংলা-দাঁড়ি «৷৷ ১।» / «৷৷ ২৷»
# শেষ-দাঁড়ি ঐচ্ছিক রাখা হয়েছে (কিছু পাতায় নেই)।
NUM_PAT = re.compile(r"(?<=[।॥৷])\s*([০-৯]{1,3})\s*(?:[।॥৷]{1,2})?")


def split_mantras(text):
    """অনুবাদ-পাঠ → [{bn, vn}] — মন্ত্র-নম্বর ধরে ভাগ।

    ⚠ দাঁড়ির পর যেকোনো সংখ্যা ধরলে বাক্যের ভেতরের সংখ্যাও («১৯০৭ সালে»)
      কেটে পড়ে। তাই কেবল তখনই ভাগ করি যখন সংখ্যাটি পরের প্রত্যাশিত ক্রম।

    ⚠ আর প্রথম মন্ত্রে নম্বর না-ও থাকতে পারে («…৷৷ ২৷» দিয়ে শুরু) — তখন
      পরের সংখ্যা থেকেই ক্রম চালিয়ে শুরুর অংশটুকু ১ম মন্ত্র করি।
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    ms = list(NUM_PAT.finditer(text))
    nums = [int(m.group(1).translate(BN_DIGITS)) for m in ms]

    def run(expect, start_at):
        """expect থেকে ক্রম ধরে ভাগ করি। start_at = এই অক্ষরের পর থেকে।"""
        out, pos = [], start_at
        for m, num in zip(ms, nums):
            # start_at থেকে শুরু হওয়া ম্যাচটিকেও নিতে হবে — তাই <= নয়, <
            # শুধু তখনই বাদ যখন ম্যাচটি start_at-এর *আগে* শেষ হয়েছে।
            if m.end() <= start_at or num != expect:
                continue
            seg = text[pos:m.start()].strip()
            if len(seg) >= 8:
                out.append({"bn": seg, "vn": num})
                expect = num + 1
                pos = m.end()
        return out, pos

    # ১) ক্রম ১ থেকে শুরু ধরার চেষ্টা (সাধারণ কেস)
    out, pos = run(1, 0)
    # ২) না মিললে সংখ্যাটা অন্য জায়গা থেকে শুরু হতে পারে («…৷৷ ২৷ …৷৷ ৩৷»)।
    #    তখন প্রথম যে নম্বর পাই সেটিকেই ক্রমের শুরু ধরি — পুনরায় এক চেষ্টা।
    #    (মন্ত্রে বানানো নম্বর নয় — write() সূক্তের ভেতরে আবার ১ থেকে গোনে।)
    if not out and ms:
        alt, apos = run(nums[0], 0)
        if len(alt) > len(out):
            out, pos = alt, apos
    # ৩) প্রথম মন্ত্র নম্বরহীন হলে («…৷৷ ২৷» = ২য় মন্ত্র, ১ম টা নম্বরহীন)
    #    — তখন শুরুর অংশটুকুই ১ম মন্ত্র, বাকিটা ক্রম মেনে।
    if ms:
        first = ms[0]
        head = text[:first.start()].strip()
        if len(head) >= 8 and (not out or out[0]["bn"] != head):
            # ২য় মন্ত্রের নম্বর = nums[0] হলে nums[1] হবে ৩ — সেই ক্রমেই
            rest, apos = run(nums[1] if len(nums) > 1 else nums[0] + 1,
                             first.end())
            if rest:
                out = [{"bn": head, "vn": 0}] + rest
                pos = apos

    for i, v in enumerate(out, 1):
        v["vn"] = i
    tail = text[pos:].strip(" ।॥৷")
    if len(tail) >= 8:
        if out and len(tail) < 40:       # ছোট লেজ = আগের মন্ত্রের অংশ
            out[-1]["bn"] = (out[-1]["bn"] + " " + tail).strip()
        else:
            out.append({"bn": tail, "vn": len(out) + 1})
    return out


SUKTA_NAME = re.compile(
    r"সূক্ত[ি]?\s*[:ঃ]?\s*\**\s*(.*?)\s*(?:\[\s*ঋষি|\**ঋষি|$)")


def sukta_name(title):
    """শিরোনাম-লাইন থেকে সূক্তের নাম («শত্রুনাশনম্»)।

    নাম না থাকলে খালি — কিন্তু সূক্ত বাদ যায় না («দ্বিতীয় সূক্তি» ধাঁচে
    নামও নেই, কোলনও নেই; আগে এই কারণেই সূক্ত হারাত)।
    """
    m = SUKTA_NAME.search(title or "")
    nm = (m.group(1) if m else "")
    nm = re.sub(r"\[.*$", "", nm).strip(" :ঃ*-–—[]")
    nm = re.sub(r"\s+", " ", nm)
    return nm if 1 < len(nm) <= 40 else ""


# ---------------- মূল পার্সার ----------------
def parse_page(lines):
    """পাতার লাইন → [{title, name, verses:[{bn, vn}]}]

    নীতি:
      · সূক্ত-শিরোনাম পেলে নতুন সূক্ত শুরু।
      · আলোচনা/টীকা পেলে সূক্ত বন্ধ — কিন্তু *পার্সিং থামে না*: একই অনুবাকে
        আলোচনার পরে পরের সূক্ত থাকতে পারে (কাণ্ড ৫-এ আগে এখানেই সব হারাত)।
      · «বঙ্গানুবাদ» লেবেলের আগের লাইন সংস্কৃত — বাদ।
    """
    suktas, cur, buf, seen_bn, skip, started = [], None, [], False, False, False
    for raw in lines:
        ln = strip_md(raw)
        if not ln:
            continue

        # ১) সূক্ত-শিরোনাম — আলোচনার পরে হলেও নতুন সূক্ত শুরু করে
        if is_sukta_head(ln):
            if cur is not None and buf and seen_bn:
                _push(suktas, cur, buf)
            cur, buf, seen_bn, skip, started = {"title": ln}, [], False, False, False
            continue

        # ২) আলোচনা/টীকা — চলমান সূক্ত বন্ধ করে «বাদ» মোডে যাই
        if skip:
            continue
        if cur is not None and is_aloc(ln):
            if buf and seen_bn:
                _push(suktas, cur, buf)
            cur, buf, seen_bn, skip = None, [], False, True
            continue
        if cur is None:
            continue                          # অনুবাক-শিরোনাম/ভূমিকা

        # ৩) অনুবাদ-লেবেল (নিজে, বা লাইনের মাঝে)
        if BN_LABEL.match(ln):
            seen_bn = started = True
            buf.append(BN_LABEL.sub("", ln).lstrip(" –—‐-:").strip())
            continue
        m = BN_LABEL.search(ln)
        if m:
            seen_bn = started = True
            buf.append(ln[m.end():].lstrip(" –—‐-:").strip())
            continue
        if not seen_bn:
            continue                          # সংস্কৃত পাঠ — বাদ
        buf.append(ln)

    if cur is not None and buf and seen_bn:
        _push(suktas, cur, buf)

    # কিছু পাতা লেবেল ছাড়াই সরাসরি অনুবাদ রাখে (কাণ্ড ৫-এর মতো)। লেবেল-পথে
    # সূক্ত-শিরোনামের অর্ধেকেরও কম পেলে বিকল্প পথে আবার, বেশি যা মেলে তা নিই।
    heads = sum(1 for ln in lines if is_sukta_head(strip_md(ln)))
    if not suktas or (heads and len(suktas) < heads * 0.5):
        alt = sweep_page(lines)
        if len(alt) > len(suktas):
            suktas = alt
    return suktas


def sweep_page(lines):
    """বিকল্প পথ — লেবেলের ওপর নির্ভর না করে লাইনগুলো নিজেই।

    কিছু অনুবাক-পাতায় «বঙ্গানুবাদ» লেখাই থাকে না, অনুবাদ সরাসরি শুরু হয়।
    এখানে প্রতিটি বড় লাইন সম্ভাব্য অনুবাদ; তবে বাদ: ঋষি/দেবতা-বracket,
    «মন্ত্রঃ» (সংস্কৃত), ছোট লাইন, আর আলোচনার পরে সব কিছু।
    """
    suktas, cur, buf = [], None, []
    for raw in lines:
        ln = strip_md(raw)
        if not ln:
            continue
        if is_sukta_head(ln):
            if cur is not None and buf:
                _push(suktas, cur, buf)
            cur, buf = {"title": ln}, []
            continue
        if is_aloc(ln):
            if cur is not None and buf:
                _push(suktas, cur, buf)
            break                             # আলোচনা = পাতার পাঠ শেষ
        if ln.startswith("[") or ("ঋষি" in ln and "দেবতা" in ln):
            continue
        if ln.startswith("মন্ত্রঃ") or len(ln) < 40:
            continue
        buf.append(BN_LABEL.sub("", ln).lstrip(" –—‐-:*").strip())
    if cur is not None and buf:
        _push(suktas, cur, buf)
    return suktas


def _push(out, cur, buf):
    vs = split_mantras(" ".join(buf))
    if vs:
        cur["verses"] = vs
        cur["name"] = sukta_name(cur.get("title", ""))
        out.append(cur)


# ---------------- লেসন-তালিকা ----------------
# LearnDash-এ <a>-এর ভেতরে <span class="ld-item-title"> থাকে — তাই [^<]
# দিয়ে শিরোনাম নিলে কিছুই মেলে না।
LINK_RE = re.compile(
    r'href="(https://www\.ebanglalibrary\.com/(?:lessons|topics)/[^"#?]+)"'
    r"[^>]*>(.{0,400}?)</a>", re.S)
# লেসন-URL-এর স্লাগে ক্রম থাকে: «…/lessons/০১।১-প্রথম-কাণ্ড-প্রথম-অনুবাক/»
SLUG_NUM = re.compile(r"/lessons/([০-৯]{1,2})\s*।\s*([০-৯]{1,2})")
TITLE_NUM = re.compile(r"^([০-৯]{1,2})\s*।\s*([০-৯]{1,2})")
STOP_TITLE = re.compile(r"নিবেদন|ভূমিকা|সূচিপত্র|পরিশিষ্ট|গ্রন্থপঞ্জি")


def page_rows(h):
    """পাতার HTML → [(কাণ্ড, অনুবাক, url, শিরোনাম)]।

    ক্রম আগে লেসন-URL-এর স্লাগে (নির্ভরযোগ্য), না পেলে শিরোনামে («০১।১ …»)।
    ভূমিকা/সম্পাদকের নিবেদন বাদ — সেগুলোতে সূক্ত-শিরোনাম নেই।
    """
    out, seen = [], set()
    for mm in LINK_RE.finditer(h or ""):
        u = htmllib.unescape(mm.group(1))
        if u in seen:
            continue
        t = re.sub(r"\s+", " ", htmllib.unescape(TAG_RE.sub(" ", mm.group(2)))).strip()
        if STOP_TITLE.search(t):
            continue
        num = SLUG_NUM.search(urllib.parse.unquote(u)) or TITLE_NUM.match(t)
        if not num:
            continue
        k, a = to_int(num.group(1)), to_int(num.group(2))
        if 1 <= k <= 20 and 1 <= a <= MAX_ANUV:
            seen.add(u)
            out.append((k, a, u, t or f"{bnnum(k)}।{bnnum(a)}"))
    return out


def _of_n(h):
    """«1 of 3» ধাঁচে পৃষ্ঠা-সংখ্যা; না পেলে None।"""
    m = re.search(r"(\d{1,2})\s*of\s*(\d{1,2})", h or "")
    return min(int(m.group(2)), 12) if m else None


def lesson_index():
    """সব অনুবাক-পাতার তালিকা — BFS।

    কেন: বই-পাতার সূচিতে সব লেসন থাকে না, আর সাইডবারও পৃষ্ঠায় ভাগ করা
    («N of 3»)। প্রতিটি লেসন-পাতার ভেতরে পুরো কোর্সের তালিকা থাকে, তাই
    বই-পাতা থেকে শুরু করে প্রতিটি পাওয়া লেসন ঘুরি ও তার পৃষ্ঠাগুলোও দেখি।
    """
    seen_url, rows, queue = set(), [], [BOOK]
    seen_page = set()
    while queue and len(seen_page) < 260:
        url = queue.pop(0)
        if url in seen_page:
            continue
        seen_page.add(url)
        h = get(url)
        if not h:
            continue
        if "404" in h[:4000] or "Not found, error 404" in h[:8000]:
            continue
        before = len(rows)
        for k, a, u, t in page_rows(h):
            if u in seen_url:
                continue
            seen_url.add(u)
            rows.append({"kanda": k, "anuvaka": a, "url": u, "title": t})
            queue.append(u)
        # পৃষ্ঠা-সংখ্যা: বই-পাতায় ভিন্ন কী, লেসনে ভিন্ন
        n = _of_n(h)
        if "?" not in url:
            if url == BOOK:
                for i in range(2, (n or 3) + 1):
                    queue.append(f"{BOOK}?ld-courseinfo-lesson-page={i}")
            else:
                for i in range(1, (n or 4) + 1):
                    queue.append(f"{url}?ld-lesson-page={i}")
        if len(rows) > before:
            print(f"   · +{len(rows) - before} লিংক ({rows[-1]['title'][:34]}) "
                  f"— মোট {len(rows)}", flush=True)
        time.sleep(0.4)
    rows.sort(key=lambda r: (r["kanda"], r["anuvaka"]))
    per = {}
    for r in rows:
        per[r["kanda"]] = per.get(r["kanda"], 0) + 1
    print("লেসন-কভারেজ: " + " · ".join(f"{k}:{v}" for k, v in sorted(per.items())),
          flush=True)
    return rows


# ---------------- অনুমান (স্লাগ-জোড়া) ----------------
# লেসন-URL শেষে কেটে যায় («০৮।১-অষ্টম-কাণ্ড-প্রথম-অন/»), তাই তালিকা থেকে
# পুনর্গঠন অসম্ভব। তবে একই কাণ্ডের পাওয়া লেসন থেকে প্রেফিক্স শেখা যায় —
# আর নাহলেও কাণ্ড-ও-অনুবাকের নাম দিয়ে বানানো যায়।
TAILS = ("", "-অনুবাক", "-অনুবা", "-অনুব", "-অনু", "-অন", "-অ")


def lesson_urls(kanda, anuv, learned):
    """(কাণ্ড, অনুবাক) → সম্ভাব্য URL-তালিকা (আগে শেখা প্রেফিক্স)।"""
    stems = []
    if kanda in learned:
        stems.append(f"{bnnum(kanda)}।{bnnum(anuv)}-{learned[kanda]}")
    stems.append(f"{bnnum(kanda)}।{bnnum(anuv)}-{ORD_SLUG[kanda - 1]}-কাণ্ড-"
                 f"{ORD_SLUG[anuv - 1]}")
    seen, out = set(), []
    for st in stems:
        for tail in TAILS:
            u = f"{BASE}/lessons/{urllib.parse.quote(st + tail)}/"
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


def fill_missing(rows):
    """তালিকায় না থাকা অনুবাক-পাতা অনুমান করে খুঁজি।

    এভাবেই কাণ্ড ২০ পাওয়া গেছে — সাইডবারের শেষ পৃষ্ঠা («3 of 3») আগে
    ঘোরা হতো না, আর স্লাগ কাটা থাকায় লিংক-তালিকা থেকে তাও হারাত।
    """
    learned = {}
    for r in rows:
        m = re.search(r"/lessons/[০-৯]{1,2}\s*।\s*[০-৯]{1,2}-([^/]+)/",
                      urllib.parse.unquote(r["url"]))
        if m:
            learned.setdefault(r["kanda"], m.group(1))
    have = {(r["kanda"], r["anuvaka"]) for r in rows}
    found = {r["url"] for r in rows}
    added = 0
    for k in range(1, 21):
        for a in range(1, MAX_ANUV + 1):
            if (k, a) in have:
                continue
            for u in lesson_urls(k, a, learned):
                if u in found:
                    break
                h = get(u)
                if not h or "404" in h[:4000]:
                    continue
                if not parse_page(html_text(h)):
                    continue
                found.add(u)
                rows.append({"kanda": k, "anuvaka": a, "url": u,
                             "title": f"{bnnum(k)}।{bnnum(a)} {ORD_SLUG[k-1]} কাণ্ড : "
                                      f"{ORD_SLUG[a-1]} অনুবাক"})
                have.add((k, a))
                added += 1
                print(f"   + অনুমানে পেলাম: কাণ্ড {bnnum(k)}.{bnnum(a)}", flush=True)
                break
    if added:
        print(f"   (অনুমান-পথে {added}টি নতুন পাতা)", flush=True)
        rows.sort(key=lambda r: (r["kanda"], r["anuvaka"]))
    return rows


# ---------------- লেখা ----------------
def write(rows):
    OUT.mkdir(parents=True, exist_ok=True)
    by = {}
    for r in rows:
        by.setdefault(r["kanda"], []).append(r)

    chapters, ok, fail = [], [], []
    for k in sorted(by):
        verses, suktas, kept = [], [], []
        for r in by[k]:
            h = get(r["url"])
            if not h:
                fail.append(r["title"])
                continue
            parsed = parse_page(html_text(h))
            if not parsed:
                fail.append(r["title"])
                continue
            kept.append(r["url"])
            for s in parsed:
                frm = len(verses) + 1
                for v in s["verses"]:
                    verses.append({"n": len(verses) + 1, "sk": "", "bn": v["bn"],
                                   "spk": "", "bnSrc": SRC, "vn": v["vn"]})
                if len(verses) >= frm:
                    suktas.append({"id": len(suktas) + 1, "from": frm,
                                   "to": len(verses), "mantra": len(verses) - frm + 1,
                                   "name": s.get("name") or ""})
            print(f"   · {r['title'][:44]}: {len(suktas)} সূক্ত / {len(verses)} মন্ত্র",
                  flush=True)
            time.sleep(0.3)
        if not verses:
            fail.extend(r["title"] for r in by[k])
            print(f"   ✗ কাণ্ড {k}: কিছুই পাওয়া গেল না", flush=True)
            continue
        # সূক্তে মন্ত্র-নম্বর ১ থেকে (ঋগ্বেদের নীতি)
        for s in suktas:
            for i, v in enumerate(verses[s["from"] - 1:s["to"]], start=1):
                v["vn"] = i
        obj = {"id": k, "bn": f"কাণ্ড {bnnum(k)}", "count": len(verses),
               "from": 1, "to": len(verses), "verses": verses,
               "url": kept[0] if kept else BOOK, "suktas": suktas,
               "suktaCount": len(suktas), "shlokaCount": len(verses),
               "withBn": len(verses)}
        (OUT / f"ch{k}.json").write_text(
            json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        chapters.append({"id": k, "bn": obj["bn"], "count": len(verses),
                         "from": 1, "to": len(verses), "withBn": len(verses),
                         "suktaCount": len(suktas), "shlokaCount": len(verses),
                         "grid": {"count": len(suktas)}})
        ok.append(k)
        print(f"✓ কাণ্ড {bnnum(k)}: {len(suktas)} সূক্ত · {len(verses)} মন্ত্র",
              flush=True)

    total = sum(c["count"] for c in chapters)
    suk = sum(c["suktaCount"] for c in chapters)
    missing = [k for k in range(1, 21) if k not in ok]
    rep = [f"কাণ্ড পাওয়া গেল: {ok}", f"ব্যর্থ পাতা: {fail or '—'}"]
    if missing:
        rep.append(f"পাওয়া যায়নি: কাণ্ড {missing}")
    rep.append(f"মোট: {total} মন্ত্র · {suk} সূক্ত")
    (OUT / "_fetch_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")

    # ---- শর্ত: ২০ কাণ্ড সম্পূর্ণ না হলে ইনডেক্স নয় ----
    if missing:
        print(f"\n⛔ কাণ্ড {missing} পাওয়া যায়নি — ইনডেক্স লেখা হবে না "
              f"(শর্ত: সম্পূর্ণ ২০ কাণ্ড)। ch ফাইল রাখা হলো, পরের রানে বাকিটা নামবে।",
              flush=True)
        return {"ok": False, "missing": missing, "chapters": chapters}

    # শৌণক সংহিতা ≈ ৬,০৭৯ মন্ত্র · ৭৩৪ সূক্ত। কম হলে পার্সে সমস্যা।
    if total < 5000 or suk < 600:
        print(f"\n⛔ মোট {total} মন্ত্র / {suk} সূক্ত — প্রত্যাশার (৬,০৭৯ / ৭৩৪) "
              f"চেয়ে অনেক কম; পার্স বা লিঙ্কে সমস্যা। ইনডেক্স লেখা হবে না।",
              flush=True)
        return {"ok": False, "low": True, "chapters": chapters}

    idx = {"slug": "atharvaveda", "bn": "অথর্ববেদ সংহিতা", "en": "Atharvaveda",
           "total": total, "withBn": total, "chapters": chapters,
           "verseWord": "মন্ত্র", "bnSrc": SRC,
           "note": "শুধু বাংলা অনুবাদ (সংস্কৃত মূলপাঠ, মন্ত্রার্থ-আলোচনা ও টীকা "
                   "বাদ) — ebanglalibrary.com; প্রতিটি সূক্তে মন্ত্র-নম্বর ১ থেকে।",
           "suktaTotal": suk, "shlokaTotal": total,
           "groupWord": "সূক্ত", "chword": "কাণ্ড", "bookWord": "কাণ্ড"}
    (OUT / "index.json").write_text(
        json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✔ ইনডেক্স: {total} মন্ত্র · {len(chapters)} কাণ্ড · {suk} সূক্ত",
          flush=True)
    for c in chapters:
        print(f"   কাণ্ড {c['id']}: {c['suktaCount']} সূক্ত · {c['count']} মন্ত্র",
              flush=True)
    return {"ok": True, "index": idx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-only", action="store_true", help="কেবল অনুবাক-তালিকা")
    ap.add_argument("--limit", type=int, default=0, help="পরীক্ষার জন্য কাণ্ড-সীমা")
    a = ap.parse_args()

    if not get(BOOK):
        print("::error::বই-পাতাই নামানো গেল না — নেটওয়ার্ক/ব্লক সমস্যা "
              f"(URL: {BOOK})", flush=True)
        sys.exit(2)

    rows = lesson_index()
    print(f"অনুবাক-পাতা (তালিকা): {len(rows)}", flush=True)
    if not rows:
        print("::error::একটিও লেসন-লিংক পাওয়া গেল না — বই-পাতার HTML-গঠন "
              "বদলেছে, নাকি সাইট নেটওয়ার্ক থেকে আটকে দিয়েছে (উপরের ! দেখুন)।",
              flush=True)
        sys.exit(2)
    rows = fill_missing(rows)
    (ROOT / "_atharva_lessons.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    kd = {}
    for r in rows:
        kd[r["kanda"]] = kd.get(r["kanda"], 0) + 1
    print("কাণ্ডভিত্তিক অনুবাক:", dict(sorted(kd.items())), flush=True)
    if a.list_only:
        return
    if a.limit:
        rows = [r for r in rows if r["kanda"] <= a.limit]
    res = write(rows)
    if not res.get("ok"):
        sys.exit(3)


if __name__ == "__main__":
    main()
