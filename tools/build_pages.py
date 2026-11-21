import datetime
import hashlib
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assets/grantho/data/<slug>/index.json → grantho/hindu/<slug>.html + হাব-কার্ড।

নীতি: ডেটায় যতটুকু বাংলা আছে ঠিক ততটুকুই দেখাই, বাড়িয়ে নয়।
কোনো index.json না থাকলে বা শূন্য হলে সেই গ্রন্থের পাতা/কার্ড তৈরি হয় না।
"""
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/grantho/data"
OUT = ROOT / "grantho/hindu"

# ---- সাইটে এখন কোন গ্রন্থ থাকবে -------------------------------------------
ACTIVE = ("gita", "rigveda", "samaveda", "yajurveda-shukla", "atharvaveda",
          "shvetashvatara", "prashna", "chandogya", "brihadaranyaka",
          "mahabharata",
          "bible",
          "dhammapada", "digha-nikaya", "majjhima-nikaya", "samyutta-nikaya",
          "anguttara-nikaya", "vinaya-vibhanga")

BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


class Shrink(Exception):
    """ডেটা হঠাৎ অনেক ছোট হয়ে গেছে — পাতা বানিয়ে সাইট খারাপ করব না।"""


def bn(n):
    return str(n).translate(BN)


def commas(n):
    return bn(f"{int(n):,}")


# ---- প্রতিটি গ্রন্থের রূপকথা -------------------------------------------------
BOOKS = {
    "rigveda": dict(
        kind="veda", title=("ঋগ্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
        kicker="হিন্দু · বেদ · ঋগ্বেদ", crumb="ঋগ্বেদ সংহিতা",
        intro="ঋগ্বেদের বাংলা অনুবাদ — রমেশচন্দ্র দত্তের অনুবাদ (ebanglalibrary.com)।",
        word="মন্ত্র", chword="মণ্ডল",
        src="বাংলা অনুবাদ ebanglalibrary.com থেকে (অনুবাদ: রমেশচন্দ্র দত্ত)।",
        excerpt="দেবতাদের স্তবসমূহ — রমেশচন্দ্র দত্তের বাংলা অনুবাদে ১০ মণ্ডলের ১০,৪৫৬ মন্ত্র।",
    ),
}

# বাইবেল — খ্রিস্টান অংশের প্রথম গ্রন্থ। পাতা grantho/christian/ ফোল্ডারে,
# তাই hub-লিংক এক ধাপ ওপরে (../christian.html) আর ক্রাম্ব থেকে টেমপ্লেটের
# «হিন্দু» অ্যাংকরটি বাদ দিতে হয় (crumbDrop)।
BOOKS["bible"] = dict(
    kind="bible", dir="christian", title=("বাংলা বাইবেল", ""),
    hub="../christian.html", hubname="খ্রিস্টান", crumbDrop="হিন্দু",
    kicker="খ্রিস্টান · বাইবেল", crumb="বাংলা বাইবেল",
    intro=("বাংলা বাইবেলের সম্পূর্ণ পাঠ — পুরাতন ও নতুন নিয়মের পুস্তকগুলো "
           "অধ্যায় ও পদ ধরে সাজানো (ebanglalibrary.com)।"),
    word="পদ", chword="পুস্তক", groupword="অধ্যায়",
    src=("বাংলা পাঠ — ebanglalibrary.com («বাংলা বাইবেল»); ইংরেজি পাশে — "
         "The New American Bible, vatican.va। উৎসে যে পদ পাওয়া যায়নি তা অনুমান করে "
         "বসানো হয় না — সেগুলো রিপোর্টে নথিভুক্ত থাকে।"),
    excerpt="সৃষ্টি থেকে নতুন নিয়ম পর্যন্ত — পুস্তক, অধ্যায় ও পদ-নম্বরসহ সম্পূর্ণ বাংলা পাঠ।")

BOOKS["yajurveda-shukla"] = dict(
    kind="veda", title=("শুক্ল যজুর্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · শুক্ল যজুর্বেদ", crumb="শুক্ল যজুর্বেদ সংহিতা",
    intro="শুক্ল যজুর্বেদের বাংলা অনুবাদ — দুর্গাদাস লাহিড়ী (ebanglalibrary.com)।",
    word="মন্ত্র", chword="অধ্যায়",
    # সতর্কতা: এই সংস্করণে সংস্কৃত মূল পাঠ নেই, তাই «মূল পাঠ» দাবি করা যাবে না
    src="বাংলা অনুবাদ — দুর্গাদাস লাহিড়ী; ebanglalibrary.com থেকে সংগৃহীত।",
    excerpt="যজ্ঞের বিধি ও মন্ত্রের বেদ — শুক্ল শাখার বাংলা অনুবাদসহ।")
BOOKS["yajurveda-krishna"] = dict(
    kind="veda", title=("কৃষ্ণ যজুর্বেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · কৃষ্ণ যজুর্বেদ", crumb="কৃষ্ণ যজুর্বেদ সংহিতা",
    intro="কৃষ্ণ যজুর্বেদের বাংলা অনুবাদসহ পাঠ — ebanglalibrary.com।",
    word="মন্ত্র", chword="অধ্যায়",
    src="বাংলা অনুবাদ ebanglalibrary.com থেকে সংগৃহীত।",
    excerpt="যজ্ঞের বিধি ও মন্ত্রের বেদ — কৃষ্ণ শাখার বাংলা অনুবাদসহ।")
BOOKS["samaveda"] = dict(
    kind="veda", title=("সামবেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · সামবেদ", crumb="সামবেদ সংহিতা",
    intro="কৌথুমী শাখার সামবেদ সংহিতা — পূর্বার্চিক, আরণ্যক, মহানাম্নী ও উত্তরার্চিকের ২৮ অধ্যায় ও ৪৭০ সূক্ত/দশতির ১,৮৭৫ মন্ত্র সস্বর সংস্কৃত মূল পাঠ, দুর্গাদাস লাহিড়ীর পূর্ণ বাংলা অনুবাদ এবং R.T.H. Griffith-এর ইংরেজি অনুবাদসহ।",
    word="মন্ত্র", chword="অধ্যায়", groupword="সূক্ত",
    src="মূল সস্বর সংস্কৃত পাঠ sanchaya (সস্বরা কৌথুমীয়া সংহিতা) থেকে; বাংলা অনুবাদ দুর্গাদাস লাহিড়ী (ebanglalibrary.com); ইংরেজি অনুবাদ Ralph T.H. Griffith (১৮৯৩)।",
    excerpt="কৌথুমী শাখার সামবেদ — ২৮ অধ্যায়ের ১,৮৭৫ মন্ত্র মূল সস্বর সংস্কৃত, পূর্ণ বাংলা ও ইংরেজি অনুবাদসহ।")
BOOKS["atharvaveda"] = dict(
    kind="veda", title=("অথর্ববেদ", "সংহিতা"), hub="veda.html", hubname="বেদ",
    kicker="হিন্দু · বেদ · অথর্ববেদ", crumb="অথর্ববেদ সংহিতা",
    intro="শৌনক শাখার অথর্ববেদ সংহিতা — ২০ কাণ্ড ও ৭৩৬ সূক্তের পূর্ণ সস্বর সংস্কৃত মূল পাঠ, ইংরেজি অনুবাদ এবং নিরীক্ষিত বাংলা অনুবাদসহ।",
    word="মন্ত্র", chword="কাণ্ড", groupword="সূক্ত",
    src="মূল সস্বর সংস্কৃত পাঠ vishvAsa/vedAH (শৌনক সংহিতা) থেকে; ইংরেজি অনুবাদ R.T.H. Griffith (১৮৯৫–৯৬) ও W.D. Whitney (১৯০৫); বাংলা অনুবাদ ebanglalibrary.com থেকে।",
    excerpt="শৌনক শাখার অথর্ববেদ — ২০ কাণ্ডের ৫,৯৭৬ মন্ত্র মূল সংস্কৃত, ইংরেজি ও বাংলা অনুবাদসহ।")
BOOKS["shvetashvatara"] = dict(
    kind="upanishad", title=("শ্বেতাশ্বতর", "উপনিষদ"), hub="../hindu.html", hubname="হিন্দু",
    kicker="হিন্দু · উপনিষদ · শ্বেতাশ্বতর", crumb="শ্বেতাশ্বতর উপনিষদ",
    intro="ষড়ধ্যায় শ্বেতাশ্বতর উপনিষদ — ৬ অধ্যায়ের ১১৩ মন্ত্র পাঁচ-সূত্র নিরীক্ষিত দেবনাগরী সংস্কৃত মূল পাঠ, স্বামী লোকেশ্বরানন্দের বাংলা সরলার্থ এবং F. Max Müller-এর ইংরেজি অনুবাদসহ।",
    word="মন্ত্র", chword="অধ্যায়",
    src="মূল সংস্কৃত পাঠ পাঁচটি প্রামাণ্য সংস্করণ মিলিয়ে নিরীক্ষিত; বাংলা সরলার্থ — স্বামী লোকেশ্বরানন্দ (ebanglalibrary.com); ইংরেজি অনুবাদ — F. Max Müller (Sacred Books of the East, Vol. 15, 1884)।",
    excerpt="৬ অধ্যায়ের ১১৩ মন্ত্র — মূল সংস্কৃত, বাংলা সরলার্থ ও ইংরেজি অনুবাদসহ।")
BOOKS["prashna"] = dict(
    kind="upanishad", title=("প্রশ্ন", "উপনিষদ"), hub="../hindu.html", hubname="হিন্দু",
    kicker="হিন্দু · উপনিষদ · প্রশ্ন", crumb="প্রশ্ন উপনিষদ",
    intro="ষড়ধ্যায় প্রশ্ন উপনিষদ — ৬ প্রশ্নের ৬৭ মন্ত্র চার-সূত্র নিরীক্ষিত দেবনাগরী সংস্কৃত মূল পাঠ, স্বামী লোকেশ্বরানন্দের বাংলা সরলার্থ এবং F. Max Müller-এর ইংরেজি অনুবাদসহ।",
    word="মন্ত্র", chword="প্রশ্ন",
    src="মূল সংস্কৃত পাঠ চারটি প্রামাণ্য সংস্করণ মিলিয়ে নিরীক্ষিত; বাংলা সরলার্থ — স্বামী লোকেশ্বরানন্দ (ebanglalibrary.com); ইংরেজি অনুবাদ — F. Max Müller (Sacred Books of the East, Vol. 15, 1884)।",
    excerpt="৬ প্রশ্নের ৬৭ মন্ত্র — মূল সংস্কৃত, বাংলা সরলার্থ ও ইংরেজি অনুবাদসহ।")
BOOKS["chandogya"] = dict(
    kind="upanishad", title=("ছান্দোগ্য", "উপনিষদ"), hub="../hindu.html", hubname="হিন্দু",
    kicker="হিন্দু · উপনিষদ · ছান্দোগ্য", crumb="ছান্দোগ্য উপনিষদ",
    intro="অষ্টাধ্যায় ছান্দোগ্য উপনিষদ — ৮ অধ্যায় ও ১৫৪ খণ্ডের ৬২৮ মন্ত্র বহুমূল নিরীক্ষিত দেবনাগরী সংস্কৃত মূল পাঠ, বাংলা সরলার্থ এবং F. Max Müller-এর ইংরেজি অনুবাদসহ।",
    word="মন্ত্র", chword="অধ্যায়", groupword="খণ্ড",
    src="মূল সংস্কৃত পাঠ GRETIL ও sanskritdocuments.org মিলিয়ে নিরীক্ষিত; বাংলা সরলার্থ — ebanglalibrary.com; ইংরেজি অনুবাদ — F. Max Müller (Sacred Books of the East, Vol. 1, 1879)।",
    excerpt="৮ অধ্যায় ও ১৫৪ খণ্ডের ৬২৮ মন্ত্র — মূল সংস্কৃত, বাংলা সরলার্থ ও ইংরেজি অনুবাদসহ।")
BOOKS["brihadaranyaka"] = dict(
    kind="upanishad", title=("বৃহদারণ্যক", "উপনিষদ"), hub="../hindu.html", hubname="হিন্দু",
    kicker="হিন্দু · উপনিষদ · বৃহদারণ্যক", crumb="বৃহদারণ্যক উপনিষদ",
    intro="কাণ্বশাখীয় বৃহদারণ্যক উপনিষদ — ৬ অধ্যায় ও ৪৭ ব্রাহ্মণের ৪৩৫ মন্ত্র বহুমূল নিরীক্ষিত দেবনাগরী সংস্কৃত মূল পাঠ, স্বামী গম্ভীরানন্দের বাংলা সরলার্থ এবং F. Max Müller ও Robert E. Hume-এর ইংরেজি অনুবাদসহ।",
    word="মন্ত্র", chword="অধ্যায়", groupword="ব্রাহ্মণ",
    src="মূল সংস্কৃত পাঠ GRETIL ও প্রামাণ্য দেবনাগরী সংস্করণ মিলিয়ে নিরীক্ষিত; বাংলা সরলার্থ — স্বামী গম্ভীরানন্দ (উদ্বোধন কার্যালয়); ইংরেজি অনুবাদ — F. Max Müller (SBE Vol. 15, 1884) ও Robert E. Hume (1921, VI.4)।",
    excerpt="৬ অধ্যায় ও ৪৭ ব্রাহ্মণের ৪৩৫ মন্ত্র — মূল সংস্কৃত, বাংলা সরলার্থ ও ইংরেজি অনুবাদসহ।")

# ---- বৌদ্ধ ধর্মগ্রন্থ (ত্রিপিটক) ------------------------------------------
BOOKS["dhammapada"] = dict(
    kind="tripitaka", dir="buddhist", title=("ধম্মপদ", ""),
    hub="../buddhist.html", hubname="বৌদ্ধ", crumbDrop="হিন্দু",
    kicker="বৌদ্ধ · ত্রিপিটক · খুদ্দক নিকায়", crumb="ধম্মপদ",
    intro="খুদ্দক নিকায়ের ধম্মপদ — ২৬টি বর্গে ৪২৩টি মূল পালি গাথা, সতীশচন্দ্র মিত্রের প্রামাণ্য বাংলা পদ্যানুবাদ (১৯০৫, পাবলিক ডোমেইন) ও ভিক্ষু সুজাতোর ইংরেজি অনুবাদসহ।",
    word="গাথা", chword="বর্গ", rootword="পালি",
    src="বাংলা পদ্যানুবাদ — সতীশচন্দ্র মিত্র (১৯০৫, পাবলিক ডোমেইন; বাংলা উইকিসংকলন)। মূল পালি (মহাসঙ্গীতি) ও ইংরেজি অনুবাদ (ভিক্ষু সুজাতো) — SuttaCentral/bilara-data (CC0)। ১৬ স্থানে দুটি বা তিনটি গাথা একত্রে অনূদিত হওয়ায় ৪০৫টি অনুচ্ছেদে ৪২৩ গাথাই অটুট রাখা হয়েছে।",
    excerpt="২৬ বর্গে ৪২৩ মূল গাথা — সতীশচন্দ্র মিত্রের পদ্যানুবাদ, পালি ও ইংরেজিসহ।")
BOOKS["digha-nikaya"] = dict(
    kind="tripitaka", dir="buddhist", title=("দীর্ঘ", "নিকায়"),
    hub="../buddhist.html", hubname="বৌদ্ধ", crumbDrop="হিন্দু",
    kicker="বৌদ্ধ · সুত্ত পিটক · দীর্ঘ নিকায়", crumb="দীর্ঘ নিকায়",
    intro="সুত্ত পিটকের দীর্ঘ নিকায় — ৩টি বর্গে সম্পূর্ণ ৩৪টি সূত্র, ভিক্ষু শীলভদ্রের বাংলা অনুবাদ, মহাসঙ্গীতি পালি মূল ও ভিক্ষু সুজাতোর ইংরেজি অনুবাদসহ।",
    word="সূত্র", chword="বর্গ", groupword="সূত্র", rootword="পালি",
    src="বাংলা অনুবাদ — ভিক্ষু শীলভদ্র (মৃত্যু ১৯৫৭, পাবলিক ডোমেইন; ত্রিপিটক পাবলিশিং সোসাইটি / SuttaCentral)। মূল পালি ও ইংরেজি (ভিক্ষু সুজাতো) — SuttaCentral/bilara-data (CC0)।",
    excerpt="৩ বর্গে সম্পূর্ণ ৩৪ সূত্র — ভিক্ষু শীলভদ্রের বাংলা অনুবাদ, পালি ও ইংরেজিসহ।")
BOOKS["majjhima-nikaya"] = dict(
    kind="tripitaka", dir="buddhist", title=("মধ্যম", "নিকায়"),
    hub="../buddhist.html", hubname="বৌদ্ধ", crumbDrop="হিন্দু",
    kicker="বৌদ্ধ · সুত্ত পিটক · মধ্যম নিকায়", crumb="মধ্যম নিকায়",
    intro="সুত্ত পিটকের মধ্যম নিকায় — ১৫টি বর্গে সম্পূর্ণ ১৫২টি সূত্র, ড. বেণীমাধব বড়ুয়া, ধর্মাধার মহাস্থবির ও বিনয়েন্দ্রনাথ চৌধুরীর বাংলা অনুবাদ, মূল পালি ও ইংরেজিসহ।",
    word="সূত্র", chword="বর্গ", groupword="সূত্র", rootword="পালি",
    src="বাংলা অনুবাদ — ড. বেণীমাধব বড়ুয়া (১–৫০), ধর্মাধার মহাস্থবির (৫১–১০০) ও বিনয়েন্দ্রনাথ চৌধুরী (১০১–১৫২); SuttaCentral। মূল পালি ও ইংরেজি (ভিক্ষু সুজাতো) — SuttaCentral/bilara-data (CC0)।",
    excerpt="১৫ বর্গে ১৫২ সূত্র — পালি মূল, বাংলা ও ইংরেজি অনুবাদসহ।")
BOOKS["samyutta-nikaya"] = dict(
    kind="tripitaka", dir="buddhist", title=("সংযুক্ত", "নিকায়"),
    hub="../buddhist.html", hubname="বৌদ্ধ", crumbDrop="হিন্দু",
    kicker="বৌদ্ধ · সুত্ত পিটক · সংযুক্ত নিকায়", crumb="সংযুক্ত নিকায়",
    intro="সুত্ত পিটকের সংযুক্ত নিকায় — ৫৬টি সংযুক্তে সম্পূর্ণ ১,৮১৯টি সূত্র, বাংলা অনুবাদকদল (২০১৮), মহাসঙ্গীতি পালি মূল ও ভিক্ষু সুজাতোর ইংরেজি অনুবাদসহ।",
    word="সূত্র", chword="সংযুক্ত", groupword="সূত্র", rootword="পালি",
    src="বাংলা অনুবাদ — ইন্দ্রগুপ্ত ভিক্ষু, বঙ্গীস ভিক্ষু, অজিত ভিক্ষু, প্রজ্ঞাদর্শী ভিক্ষু, জ্ঞানেন্দ্রিয় ভিক্ষু প্রমুখ (২০১৮), SuttaCentral। মূল পালি ও ইংরেজি (ভিক্ষু সুজাতো) — SuttaCentral/bilara-data (CC0)।",
    excerpt="৫৬ সংযুক্তে ১,৮১৯ সূত্র — পালি, বাংলা ও ইংরেজিসহ।")
BOOKS["anguttara-nikaya"] = dict(
    kind="tripitaka", dir="buddhist", title=("অঙ্গুত্তর", "নিকায়"),
    hub="../buddhist.html", hubname="বৌদ্ধ", crumbDrop="হিন্দু",
    kicker="বৌদ্ধ · সুত্ত পিটক · অঙ্গুত্তর নিকায়", crumb="অঙ্গুত্তর নিকায়",
    intro="সুত্ত পিটকের অঙ্গুত্তর নিকায় — ১১টি নিপাতে ১,৪০৮টি সূত্র ও বর্গ-পাঠ, বাংলা অনুবাদ, মহাসঙ্গীতি পালি মূল ও ভিক্ষু সুজাতোর ইংরেজি অনুবাদসহ।",
    word="পাঠ", chword="নিপাত", groupword="সূত্র", rootword="পালি",
    src="বাংলা অনুবাদ — সুমঙ্গল বড়ুয়া, প্রজ্ঞাদর্শী ভিক্ষু ও অনুবাদকমণ্ডলী (২০১৮), SuttaCentral। মূল পালি ও ইংরেজি (ভিক্ষু সুজাতো) — SuttaCentral/bilara-data (CC0)।",
    excerpt="১১ নিপাতে ১,৪০৮ পাঠ — পালি, বাংলা ও ইংরেজিসহ।")
BOOKS["vinaya-vibhanga"] = dict(
    kind="tripitaka", dir="buddhist", title=("ভিক্ষু", "বিভঙ্গ"),
    hub="../buddhist.html", hubname="বৌদ্ধ", crumbDrop="হিন্দু",
    kicker="বৌদ্ধ · বিনয় পিটক · ভিক্ষু বিভঙ্গ", crumb="ভিক্ষু বিভঙ্গ",
    intro="বিনয় পিটকের ভিক্ষু বিভঙ্গ — বাংলা অনূদিত ৪টি অধ্যায়ের ৪৯টি শিক্ষাপদ (পারাজিকা ৪, সঙ্ঘাদিসেস ১৩, অনিয়ত ২ ও নিস্সগ্গিয় পাচিত্তিয় ৩০) মূল পালি ও ভিক্ষু ব্রহ্মালীর ইংরেজি অনুবাদসহ।",
    word="শিক্ষাপদ", chword="অধ্যায়", groupword="শিক্ষাপদ", rootword="পালি",
    src="বাংলা অনুবাদ — ভদন্ত বুদ্ধবংশ ভিক্ষু (SuttaCentral); মূল পালি ও ইংরেজি অনুবাদ (ভিক্ষু ব্রহ্মালী) — SuttaCentral/bilara-data (CC0)। অবশিষ্ট পাচিত্তিয়-সেখিয়া অংশ বাংলা ডিজিটাল উৎসে অনুপস্থিত থাকায় অনুমান করে বসানো হয়নি।",
    excerpt="৪ অধ্যায়ে ৪৯ শিক্ষাপদ — পালি, বাংলা ও ইংরেজিসহ।")

UPA = {
    "upanishad-aitareya": ("ঐতরেয় উপনিষদ", "জগৎসৃষ্টি, আত্মার প্রবেশ ও «প্রজ্ঞানং ব্রহ্ম» — ঐতরেয় আরণ্যকের উপনিষদ।"),
    "upanishad-brihadaranyaka": ("বৃহদারণ্যক উপনিষদ", "«অহং ব্রহ্মাস্মি» — বৃহত্তম প্রধান উপনিষদ, যাজ্ঞবল্ক্য-মৈত্রেয়ীর সংলাপ।"),
    "upanishad-isha": ("ঈশ উপনিষদ", "ব্রহ্মেই জগৎ পরিব্যাপ্ত — কর্ম, জ্ঞান ও মৃত্যুর পরে গতির প্রশ্নে অষ্টাদশ মন্ত্রের সংক্ষিপ্ততম প্রধান উপনিষদ।"),
    "upanishad-kena": ("কেন উপনিষদ", "«কার ইচ্ছায় মন চলে?» — ব্রহ্মকে ইন্দ্রিয়ের অতীত বলে চিনিয়ে দেওয়া চার খণ্ডের উপনিষদ।"),
    "upanishad-prashna": ("প্রশ্ন উপনিষদ", "ছয় প্রশ্নকর্তা শিষ্যের ছয় প্রশ্নে প্রাণ, রশ্মি ও ওঁ-তত্ত্বের উত্তর।"),
    "upanishad-mundaka": ("মুণ্ডক উপনিষদ", "পরাবিদ্যা ও অপরাবিদ্যার পার্থক্য, এবং «সত্যেই জয়» — তিন মুণ্ডকের উপনিষদ।"),
    "upanishad-mandukya": ("মাণ্ডূক্য উপনিষদ", "ওঁ-কারের চার পদ ও চেতনার চার অবস্থা (জাগ্রত, স্বপ্ন, সুষুপ্তি, তুরীয়)।"),
    "upanishad-taittiriya": ("তৈত্তিরীয় উপনিষদ", "শিক্ষাবল্লী ও ব্রহ্মানন্দবল্লী — অন্ন, প্রাণ ও আনন্দের স্তরে ব্রহ্মানুসন্ধান।"),
    "upanishad-aitareya": ("ঐতরেয় উপনিষদ", "জগৎসৃষ্টি, আত্মার প্রবেশ ও «প্রজ্ঞানং ব্রহ্ম» — ঐতরেয় আরণ্যকের উপনিষদ।"),
}

# টেমপ্লেট: আগে সামবেদ-পাতা (মূল নকশা), না থাকলে যেকোনো বানানো গ্রন্থ-পাতা।
# সামবেদ সাইট থেকে সরানো হয়েছে, তাই এখানেও নির্ভরতা রাখা যাবে না।
#
# ▸ নতুন পাতা বানানোর *পরে* আনকন্ডিশনালি normalize() চালানো হয় (নিচে), কারণ
#   টেমপ্লেট-পাতাটাই পুরোনো হতে পারে: নতুন পাতা থেকে আধুনিক ফুটার/SEO/ক্লাস
#   টেনে নিয়ে সেগুলো বসানো হয়। ফলে build_pages.py দিয়ে rebuild করলেও
#   ফুটার-সংক্ষেপ, og:image ও canonical হারে না (আগে ফিরে যেত)।
def _pick_template():
    for cand in ("rigveda.html", "yajurveda-shukla.html", "gita.html"):
        p = OUT / cand
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise SystemExit("টেমপ্লেট-পাতা পাওয়া গেল না (rigveda/yajurveda-shukla/gita)")


TEMPLATE = _pick_template()

SITE = "https://ebrahim-ead.github.io/ead"
OG_CARD = SITE + "/assets/og-cover.jpg"


def _ref_page() -> str:
    """আধুনিক (হাতে ঠিক করা) পাতা — ফুটার ও head-এর জন্য সবচেয়ে ভালো নমুনা।"""
    for cand in ("rigveda.html", "gita.html", "islam.html"):
        p = OUT / cand
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


REF = _ref_page()
FOOTER = (re.search(r"<footer\b.*?</footer>", REF, re.S).group(0)
          if REF and re.search(r"<footer\b.*?</footer>", REF, re.S) else "")
EXTRA_CSS = re.compile(
    r'<link[^>]*href="(?:\.\./\.\./|\.\./|\.){0,3}assets/site-extra\.css"[^>]*>'
    r'(?:\s*<link[^>]*\?v=\d+"[^>]*>)?')


def normalize(slug: str, html: str, sub: str = "hindu") -> str:
    """new/পুরোনো নির্বিশেষে প্রতিটি বানানো পাতায় একই head ও ফুটার।

    `sub` = grantho/-এর নিচে কোন ফোল্ডারে পাতাটি থাকে (হিন্দু গ্রন্থে "hindu",
    বাইবেলে "christian") — ক্যানোনিকাল ঠিকানা এর ওপরেই দাঁড়ায়।
    """
    href = f"{SITE}/grantho/{sub}/{slug}.html"
    # ১) SEO ট্যাগ — আগে থাকলে হালনাগাদ, না থাকলে যোগ (canonical বারবার যোগ হয় না)
    if 'property="og:image"' in html:
        html = re.sub(r'(<meta property="og:image" content=")[^"]*(")', lambda m: m.group(1) + OG_CARD + m.group(2), html, count=1)
        html = re.sub(r'(<meta property="og:url" content=")[^"]*(")', lambda m: m.group(1) + href + m.group(2), html, count=1)
        html = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + href + m.group(2), html, count=1)
        if 'rel="canonical"' not in html:
            html = html.replace("</head>", f'<link rel="canonical" href="{href}">\n</head>', 1)
    else:
        lines = [f'<meta property="og:image" content="{OG_CARD}">',
                 '<meta property="og:image:width" content="1200">',
                 '<meta property="og:image:height" content="630">']
        if 'name="twitter:card"' in html:          # কার্ড-লাইন থাকলে মান ঠিক করি
            html = re.sub(r'<meta name="twitter:card"[^>]*>',
                          '<meta name="twitter:card" content="summary_large_image">', html, count=1)
        else:
            lines.append('<meta name="twitter:card" content="summary_large_image">')
        lines.append(f'<link rel="canonical" href="{href}">')
        html = html.replace("</head>", "\n".join(lines) + "\n</head>", 1)
    # ১.৫) শেয়ার-ট্যাগের শিরোনাম/বিবরণ সবসময় নিজের পাতার <title>/description থেকেই।
    #      পুরোনো টেমপ্লেট থেকে «Ebrahim Ead সম্পর্কে» কপি হয়ে শেয়ার-প্রিভিউতে
    #      ভুল শিরোনাম যেত — রি-বিল্ডেও যেন না ফেরে।
    _t = re.search(r"<title>(.*?)</title>", html, re.S)
    _d = re.search(r'<meta name="description" content="([^"]*)"', html)
    if _t:
        _title, _desc = _t.group(1).strip(), (_d.group(1) if _d else "")
        for _attr in ("property", "name"):
            html = re.sub(rf'(<meta {_attr}="og:title" content=")[^"]*(")',
                          lambda m, v=_title: m.group(1) + v + m.group(2), html, count=1)
            html = re.sub(rf'(<meta {_attr}="twitter:title" content=")[^"]*(")',
                          lambda m, v=_title: m.group(1) + v + m.group(2), html, count=1)
        html = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                      lambda m, v=_desc: m.group(1) + v + m.group(2), html, count=1)
        html = re.sub(r'(<meta name="twitter:description" content=")[^"]*(")',
                      lambda m, v=_desc: m.group(1) + v + m.group(2), html, count=1)
    # ২) site-extra.css (মোবাইল/সূত্র/কম্প্যাক্ট ফুটার) — নতুনরা এটা পায় না
    if "site-extra.css" not in html:
        html = html.replace("</head>", '<link rel="stylesheet" href="../../assets/site-extra.css">\n</head>', 1)
    # ২.৫) PNG আইকন ও PWA manifest (data: SVG favicon সরিয়ে সব পাতায় সামঞ্জস্য)
    html = re.sub(r'<link rel="icon" href="data:image/svg\+xml,[^"]*">\s*', "", html)
    _pwa_add = ""
    if 'favicon-32.png' not in html:
        _pwa_add += (
            '<link rel="icon" type="image/png" sizes="32x32" href="/ead/assets/img/favicon-32.png">'
            '<link rel="icon" type="image/png" sizes="192x192" href="/ead/assets/img/icon-192.png">'
            '<link rel="apple-touch-icon" sizes="180x180" href="/ead/assets/img/apple-touch-icon.png">'
        )
    if 'rel="manifest"' not in html:
        _pwa_add += '<link rel="manifest" href="/ead/manifest.json">'
    if 'apple-mobile-web-app-capable' not in html:
        _pwa_add += (
            '<meta name="apple-mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
            '<meta name="apple-mobile-web-app-title" content="Ebrahim Ead">'
            '<meta name="mobile-web-app-capable" content="yes">'
        )
    if _pwa_add:
        _tc = re.search(r'<meta name="theme-color"[^>]*>\s*', html)
        if _tc:
            html = html[:_tc.end()] + _pwa_add + html[_tc.end():]
        else:
            html = html.replace("</head>", _pwa_add + "</head>", 1)
    # ৩) ফুটার — পুরোনো টেমপ্লেটের ফুটার বদলে আধুনিক (সংক্ষিপ্ত) ফুটার
    if FOOTER:
        m = re.search(r"<footer\b.*?</footer>", html, re.S)
        if m and m.group(0) != FOOTER:
            html = html[:m.start()] + FOOTER + html[m.end():]
    return stamp_grantho_assets(html)


GRANTHO_ASSETS = (
    "assets/grantho/grantho.css",
    "assets/grantho/grantho-common.js",
    "assets/grantho/grantho.js",
    "assets/grantho/bible-reader.js",
    "assets/grantho/mahabharata-reader.js",
)


def stamp_grantho_assets(html: str) -> str:
    """গ্রন্থ CSS/JS লিংকে ফাইল-হ্যাশ (?v=…) বসানো — পুরোনো SW/HTTP ক্যাশ এড়াতে।"""
    if "assets/grantho/grantho-common.js" not in html:
        html = re.sub(
            r'([ \t]*)(<script src="([^"]*?)assets/grantho/(?:grantho|bible-reader|mahabharata-reader)\.js[^"]*"[^>]*></script>)',
            r'\1<script src="\3assets/grantho/grantho-common.js" defer></script>\n\1\2',
            html,
            count=1,
        )
    for rel in GRANTHO_ASSETS:
        p = ROOT / rel
        if not p.exists():
            continue
        h8 = hashlib.sha256(p.read_bytes()).hexdigest()[:8]
        pat = re.compile(r'((?:href|src)="[^"]*?' + re.escape(rel) + r')(?:\?v=[0-9a-f]+)?"')
        html = pat.sub(rf'\1?v={h8}"', html)
    return html


def load(slug):
    p = DATA / slug / "index.json"
    if not p.exists():
        return None
    try:
        idx = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not idx.get("chapters") or not idx.get("total"):
        return None
    return idx


# দেবনাগরী *অক্ষর* — দাঁড়ি (U+0964) ও অঙ্ক বাদ: সেগুলো বাংলা লেখাতেও বসে,
# তাই শুধু তাদের উপস্থিতিতে পাঠকে সংস্কৃত ধরলে ভুল দাবি ছাপা হয়।
DEVANAGARI_LETTERS = re.compile(r"[\u0904-\u0939\u093D\u0950\u0958-\u0961\u0972-\u097F]")


def count_with_sk(slug: str, idx: dict) -> int:
    """কতটি শ্লোক/মন্ত্রে আসলেই সংস্কৃত (দেবনাগরী) বা পালি পাঠ আছে — পাতার দাবি যেন ডেটার সাথে মেলে।"""
    is_pali = idx.get("rootLang") == "pi"
    n = 0
    for c in idx.get("chapters", []):
        fp = DATA / slug / f"ch{c['id']}.json"
        if not fp.exists():
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if is_pali:
            n += sum(1 for v in d.get("verses", []) if str(v.get("sk") or "").strip())
        else:
            n += sum(1 for v in d.get("verses", []) if DEVANAGARI_LETTERS.search(str(v.get("sk") or "")))
    return n


def _apply_identity(h, slug, meta, main, sub):
    """পাতার নিজস্ব পরিচয় বসানো — টেমপ্লেট যেকোনো গ্রন্থের পাতাই হোক।

    আগে এখানে হার্ডকোডেড "সামবেদ …" স্ট্রিং বদলানো হতো; কিন্তু _pick_template()
    samaveda.html না পেয়ে rigveda.html ফলব্যাক করায় সেই বদলিগুলো মিলত না — ফলে
    শুক্ল যজুর্বেদের পাতায় data-base ঋগ্বেদের ফোল্ডারেই থেকে গিয়েছিল এবং
    পাঠকে ঋগ্বেদের মন্ত্র দেখাত। তাই সব বদলি এখন রেগেক্স-ভিত্তিক।
    """
    label = f"{main} {sub}".strip()
    crumb = meta.get("crumb") or label
    # ডেটা-উৎস: রিডার-JS এখান থেকেই গ্রন্থের ফোল্ডার ধরে — এটি ভুল হলে অন্য গ্রন্থের পাঠ দেখায়
    h = re.sub(r'data-granth="[^"]*"', f'data-granth="{slug}"', h, count=1)
    h = re.sub(r'data-base="[^"]*"', f'data-base="../../assets/grantho/data/{slug}/"', h, count=1)
    # কিকার (g-kicker / g-kicker2 দুই রূপই টেমপ্লেটে থাকতে পারে)
    if meta.get("kicker"):
        h = re.sub(r'(<span class="g-kicker2?">)[^<]*(</span>)',
                   lambda m: m.group(1) + meta["kicker"] + m.group(2), h)
    # শিরোনাম <h1> (অ্যাট্রিবিউট থাকলেও অটুট রাখা হয়)
    inner = f"{main} <span>{sub}</span>" if sub else main
    h = re.sub(r'(<h1[^>]*>).*?(</h1>)', lambda m: m.group(1) + inner + m.group(2),
               h, count=1, flags=re.S)
    # ব্রেডক্রাম্ব: «ধর্মীয় গ্রন্থ › হিন্দু ›» অংশ অটুট রেখে হাব-লিংক ও গ্রন্থের নাম বদলানো
    cm = re.search(r'(<p class="g-crumb">)(.*?)(</p>)', h, re.S)
    if cm:
        if meta.get("hub") == "../hindu.html":
            mid = f'<a href="../../grantho.html">ধর্মীয় গ্রন্থ</a><span>›</span><a href="../hindu.html">হিন্দু</a><span>›</span>{crumb}'
        else:
            mid = cm.group(2)
            anchors = list(re.finditer(r'<a href="[^"]*"[^>]*>.*?</a>', mid, re.S))
            if anchors:
                last = anchors[-1]
                hub = f'<a href="{meta["hub"]}">{meta["hubname"]}</a>'
                mid = mid[:last.start()] + hub + mid[last.end():]
            if meta.get("crumbDrop"):
                # টেমপ্লেট হিন্দু পাতার, তাই ক্রাম্বে «হিন্দু» অ্যাংকর থেকে যায় —
                # অন্য ধর্মের পাতায় সেটি ভুল পরিচয়, তাই অ্যাংকর+বিভাজকসহ বাদ।
                for a in list(re.finditer(r'<a href="[^"]*"[^>]*>.*?</a>\s*(?:<span>›</span>)?',
                                          mid, re.S)):
                    if meta["crumbDrop"] in a.group(0):
                        mid = mid[:a.start()] + mid[a.end():]
                        break
            sep = '<span>›</span>'
            k = mid.rfind(sep)
            if k >= 0:
                mid = mid[:k + len(sep)] + crumb
        h = h[:cm.start()] + cm.group(1) + mid + cm.group(3) + h[cm.end():]
    # টেমপ্লেটের অন্য গ্রন্থের নাম শিরোনাম-জুড়ে ছড়িয়ে থাকলে তাও বদলানো
    h = h.replace("সামবেদ সংহিতা", label).replace("ঋগ্বেদ সংহিতা", label)
    return h


def make_page(slug, idx, meta):
    main, sub = meta["title"]
    outdir = OUT.parent / meta.get("dir", "hindu")   # হিন্দু বা খ্রিস্টান ফোল্ডার
    nch = len(idx["chapters"])
    total, withbn = idx["total"], idx.get("withBn", 0)
    withsk = count_with_sk(slug, idx)
    h = TEMPLATE

    h = _apply_identity(h, slug, meta, main, sub)
    h = re.sub(r'(<div class="g-intro">.*?<p>)[^<]*(</p>)',
               lambda m: m.group(1) + meta["intro"] + m.group(2), h, count=1, flags=re.S)

    if withbn:
        facts = f'<span class="g-fact"><b>{commas(withbn)}</b> {meta["word"]} (বাংলাসহ)</span>'
    else:
        # বাংলা অনুবাদ এখনো নেই — «০ মন্ত্র (বাংলাসহ)» দেখানো বিভ্রান্তিকর, তাই বাদ
        facts = f'<span class="g-fact"><b>{commas(total)}</b> {meta["word"]}</span>'
    if total != withbn:
        if withbn:
            facts += f'<span class="g-fact"><b>{commas(total)}</b> মোট {meta["word"]}</span>'
        # ⚠ «সংস্কৃত মূল পাঠ» চিপ কেবল বেদ-জাতীয় গ্রন্থে — বাইবেলে সংস্কৃত
        #   পাঠের প্রশ্নই নেই। আগে এখানে শর্তহীন যোগ হতো, ফলে বাংলা বাইবেলের
        #   অননুবাদিত পদগুলোকে ভুলভাবে «সংস্কৃত মূল পাঠ» বলা হচ্ছিল।
        if meta.get("kind") not in ("bible", "tripitaka"):
            facts += '<span class="g-fact">সংস্কৃত মূল পাঠ</span>'
    if idx.get("gathaTotal"):
        facts += f'<span class="g-fact"><b>{commas(idx["gathaTotal"])}</b> মূল গাথা</span>'
    facts += f'<span class="g-fact"><b>{commas(nch)}</b> {meta["chword"]}</span>'
    nsuk = idx.get("suktaTotal") or sum(c.get("suktaCount", 0) for c in idx["chapters"])
    nshl = idx.get("shlokaTotal") or sum(c.get("shlokaCount", 0) for c in idx["chapters"])
    if nsuk:
        # ঋগ্বেদে «সূক্ত», বাইবেলে «অধ্যায়» — ডেটার groupWord থেকে
        gw = idx.get("groupWord") or meta.get("groupword") or "সূক্ত"
        if gw != meta["word"]:
            facts += f'<span class="g-fact"><b>{commas(nsuk)}</b> {gw}</span>'
    if nshl:
        facts += f'<span class="g-fact"><b>{commas(nshl)}</b> শ্লোক</span>'
    # ইংরেজি অনুবাদ (বাইবেল / অথর্ববেদ / ত্রিপিটক): কত পদে/মন্ত্রে মিলেছে তা ডেটা থেকেই
    enj = OUT / slug / "en" / "joined.json"
    en_n = int(idx.get("withEn") or idx.get("enSections") or 0)
    if not en_n and enj.exists():
        en_n = json.loads(enj.read_text(encoding="utf-8")).get("enVerses", 0)
    if en_n:
        if meta.get("kind") == "tripitaka":
            facts += '<span class="g-fact">পালি · বাংলা · ইংরেজি</span>'
        elif idx.get("hasEnProse") or idx.get("hasEnSections"):
            facts += f'<span class="g-fact"><b>{commas(en_n)}</b> {meta.get("groupword", "অধ্যায়")}ে ইংরেজি</span>'
        else:
            facts += f'<span class="g-fact"><b>{commas(en_n)}</b> {meta["word"]}ে ইংরেজি</span>'
    h = re.sub(r'<div class="g-facts">.*?</div>', '<div class="g-facts">' + facts + '</div>',
               h, count=1, flags=re.S)

    # সার্চ-বাক্স: টেমপ্লেটের লেবেল অন্য গ্রন্থে ভুল হতো, আর সংস্কৃত না থাকলে "(সংস্কৃত)" বিভ্রান্তিকর
    rw = meta.get("rootword") or "সংস্কৃত"
    wloc = meta["word"] + ("য়" if meta["word"].endswith("া") else "ে")
    ph = f'{wloc} খুঁজুন'
    if not withbn and withsk:
        ph += " (সংস্কৃত বা ইংরেজি)" if en_n else f" ({rw})"
    elif withsk:
        ph += f" ({rw} বা বাংলা)"
    elif withsk == 0:
        ph += " (বাংলা)"
    h = re.sub(r'(<input id="g-search"[^>]*placeholder=")[^"]*(")', lambda m: m.group(1) + ph + m.group(2), h, count=1)
    h = re.sub(r'(<input id="g-search"[^>]*aria-label=")[^"]*(")',
               lambda m: m.group(1) + f'{wloc} খুঁজুন' + m.group(2), h, count=1)
    if withsk == 0:
        h = re.sub(r'\s*<button[^>]*id="g-sk-btn".*?</button>', '', h, count=1, flags=re.S)
    elif 'id="g-sk-btn"' not in h:
        h = re.sub(
            r'(<button[^>]*id="g-bn-btn")',
            rf'<button class="g-btn on" id="g-sk-btn" type="button" aria-pressed="true">{rw}</button>\n      \1',
            h, count=1,
        )
    else:
        h = re.sub(r'(<button[^>]*id="g-sk-btn"[^>]*>)[^<]*(</button>)',
                   lambda m: m.group(1) + rw + m.group(2), h, count=1)
    if not withbn:
        h = re.sub(r'<button([^>]*id="g-bn-btn"[^>]*)>', lambda m: m.group(0) if ' hidden' in m.group(1) else f'<button{m.group(1)} hidden>', h, count=1)
    # সব খণ্ডেই বাংলা অনুবাদ থাকলে বা কোনো বাংলাই না থাকলে «কেবল যেগুলোর অনুবাদ আছে» ছাঁকনিটি অকেজো
    if (withbn and withbn >= total) or not withbn:
        h = re.sub(r'\s*<label[^>]*>\s*<input[^>]*id="g-only-bn"[^>]*>[^<]*</label>',
                   '', h, count=1, flags=re.S)
    elif 'id="g-only-bn"' not in h:
        h = re.sub(
            r'(<button[^>]*id="g-bn-btn"[^>]*>.*?</button>)',
            r'\1\n      <label class="g-chk"><input type="checkbox" id="g-only-bn"> কেবল যেগুলোর অনুবাদ আছে</label>',
            h, count=1, flags=re.S,
        )
    if (DATA / slug / "en").is_dir() and 'id="g-en-note"' not in h and '<div id="g-bn-note"' in h:
        h = h.replace('<div id="g-bn-note"',
                      '<div id="g-en-note" class="g-en-note" hidden></div>\n        <div id="g-bn-note"', 1)

    # রিডারের নতুন গঠন (পুস্তক → অধ্যায় → পদ): টেমপ্লেটে ব্লকগুলো হাতে বসানো
    # থাকে, কিন্তু গ্রুপ-তথ্য (testament/অধ্যায়-সংখ্যা/ইংরেজি-কভারেজ) ডেটা
    # থেকে এখানেই বসানো হয় — পুরোনো টেমপ্লেটেও কার্যকর।
    # প্যানেলের শিরোনাম ডেটার chword থেকেই («পুস্তক») — হার্ডকোডেড «অধ্যায়» ভুল ছিল।
    # ⚠ টেমপ্লেট ভাগাভাগি: ঋগ্বেদ/যজুর্বেদ/বাইবেল একই `g-side-title` প্যাটার্ন
    #   ব্যবহার করে, তাই এক পাতার বিল্ড অন্য পাতার শিরোনাম বদলে দিত («মণ্ডল»
    #   ঢুকে যেত যজুর্বেদের পাতায়)। এখন সব গ্রন্থে নিজের chword-ই বসানো হয়।
    _cw = meta.get("chword") or "অধ্যায়"
    h = re.sub(r'(<b id="g-side-title">)[^<]*(</b>)',
               lambda m: m.group(1) + _cw + m.group(2), h, count=1)
    if not nsuk and meta.get("kind") != "bible":
        # একক-স্তরের গ্রন্থে (যেমন যজুর্বেদ, শ্বেতাশ্বতর) অধ্যায়-তালিকা শুরু থেকেই দৃশ্যমান,
        # পুস্তক-তালিকা ও সূক্ত-গ্রিড দরকার নেই।
        h = re.sub(
            r'<div id="g-book-list">(.*?)</div>\s*<div id="g-chapter-list" hidden></div>',
            lambda m: f'<div id="g-book-list" hidden></div>\n          <div id="g-chapter-list">{m.group(1)}</div>',
            h, count=1, flags=re.S,
        )
        h = h.replace('<div id="g-crumb2" class="g-crumb2" hidden></div>', '')
        h = re.sub(r'<div id="g-chapter-grid"[^>]*></div>', '', h, count=1)
    elif nsuk and meta.get("groupword"):
        h = re.sub(
            r'(<div id="g-chapter-grid"[^>]*aria-label=")[^"]*(")',
            lambda m: m.group(1) + meta["groupword"] + m.group(2),
            h, count=1,
        )
    if meta.get("kind") == "bible":
        # প্যানেলের id — ভাঁজ-নিয়ন্ত্রণ ও স্ক্রলযোগ্য বডি এর ওপরেই দাঁড়িয়ে
        h = h.replace('<aside class="g-side">', '<aside class="g-side" id="g-side">', 1)
    # একবার আপগ্রেড হয়ে গেলে আর লিখি না — নইলে দ্বিতীয় রানে পুরনো
    # প্যাটার্ন («g-chapter-list"></div>») মিলত না আর g-testament/g-en-note
    # হারিয়ে যেত (একই বাগ দুই রানে দুই রকম ক্ষতি করত)।
    if meta.get("kind") == "bible" and 'id="g-book-list"' not in h:
        # পুরোনো টেমপ্লেটে কেবল খণ্ড-তালিকা ছিল — নতুন স্তরগুলোর কনটেইনার বসাই,
        # সাথে মোবাইলে ভাঁজ-বোতাম ও গুটিয়ে রাখা যায় এমন বডি।
        # হেডে আর কিছু নয়: বাঁয়ে পুস্তকের শব্দ (এটিই ভাঁজ-বোতাম), ডানে
        # বড় করে «তালিকা»। আগের «অধ্যায় / ৪৬ পুস্তক · ২৪,০৮৭ পদ» ফোনের
        # মোটা লাইনে জায়গা নিত, আর সহজে চোখেও পড়ত না।
        _HEAD = ('<div class="g-side-head">'
                 '<button class="g-side-toggle" id="g-side-toggle" type="button" '
                 'aria-expanded="true" aria-controls="g-side-body">'
                 '<b id="g-side-title">পুস্তক</b>'
                 '<span class="g-side-word">তালিকা '
                 '<span class="g-side-chev" aria-hidden="true"></span></span>'
                 '</button></div>')
        # পুরো হেড-div একবারে বদলাই (পুরোনো গঠনে ভেতরে «অধ্যায়»+গণনা ছিল,
        # তাই শুধু বোতাম বসিয়ে দিলে ওই দুটো বাইরে পড়ে থাকত)।
        h, n = re.subn(r'<div class="g-side-head">.*?</div>', _HEAD, h, count=1, flags=re.S)
        if not n:
            # হেড-div না থাকলে তালিকার গোড়ায় বসাই
            h = h.replace('<div id="g-book-list">', _HEAD + '<div id="g-book-list">', 1)

        # পুরনো গঠন হলেই কেবল (idempotent) — একবার আপগ্রেড হলে আর ছোঁব না
        if 'id="g-side-body"' not in h and '<div id="g-chapter-list"></div>' in h:
            h = h.replace('<div id="g-chapter-list"></div>',
                      '<div class="g-side-now" id="g-side-now" aria-live="polite"></div>'
                      '<div class="g-side-body" id="g-side-body">'
                      '<div id="g-testament" class="g-tset" role="group" '
                      'aria-label="নিয়ম" hidden></div>'
                      '<div id="g-book-list"></div>'
                      '<div id="g-chapter-list" hidden></div>'
                          '</div>', 1)
    # `g-testament` (পুরাতন/নতুন নিয়ম ছাঁকনি) ও `g-en-note` — grantho.js ও
    # test_reader দুটোই এই id ধরে কাজ করে। টেমপ্লেট বদলালে এরা যেন কখনো
    # না হারায়, তাই আলাদা করে (idempotent) নিশ্চিত করি।
    if meta.get("kind") == "bible":
        # ⚠ idempotent: আগের রানে বসানো হয়ে থাকলে আর বসাই না। মূল বাগ ছিল
        #   এখানে idempotent না হওয়া — প্রতি বিল্ডে আরেকটা g-testament
        #   জমে PAGE ভরে যেত (নিয়ম-ছাঁকনি কয়বার দেখা যেত)।
        if 'id="g-testament"' not in h and 'id="g-book-list"' in h:
            h = h.replace('<div id="g-book-list">',
                          '<div id="g-testament" class="g-tset" role="group" '
                          'aria-label="নিয়ম" hidden></div><div id="g-book-list">', 1)
        if 'id="g-en-note"' not in h and '<div id="g-bn-note"' in h:
            h = h.replace('<div id="g-bn-note"',
                          '<div id="g-en-note" class="g-en-note" hidden></div>'
                          '<div id="g-bn-note"', 1)

    src = meta["src"]
    # সংস্কৃত পাঠের প্রাপ্যতা — আগে হার্ডকোডেড দাবি ছিল যা ডেটার সাথে মিলত না।
    # বাইবেলের ক্ষেত্রে এই টীকা অর্থহীন (সেখানে সংস্কৃতের প্রশ্নই নেই)।
    if meta.get("kind") in ("bible", "tripitaka"):
        pass
    elif withsk == 0:
        src += (f' এই সংস্করণে সংস্কৃত মূল পাঠ ছাপা হয়নি, তাই {meta["word"]}ে কেবল বাংলা অনুবাদ আছে'
                ' — কোনো অনুমানভিত্তিক সংস্কৃত পাঠ বসানো হয় না।')
    elif withsk < total:
        src += (f' সংস্কৃত মূল পাঠ আংশিক — {commas(total)}টি {meta["word"]}ের মধ্যে কেবল {commas(withsk)}টিতে'
                f' উৎসে সংস্কৃত পাওয়া গেছে, সেগুলোতেই তা ছাপা হয়েছে; বাকিগুলোতে কেবল বাংলা অনুবাদ আছে।'
                ' কোনো অনুমানভিত্তিক সংস্কৃত পাঠ বসানো হয় না।')
    if withbn and withbn < total:
        src += (f' {commas(total - withbn)}টি {meta["word"]}র বাংলা পাঠ উৎসে পাওয়া যায়নি'
                # ⚠ বাক্যটা «।» দিয়ে শেষ করতে হয় — নইলে পরের (ডেটার) নোট
                #   জুড়ে গিয়ে জোড়া-বাক্য দাঁড়ায় («…পাঠ বসানো হয়নি বাংলা বাইবেল — …»)।
                ' — সংখ্যাটি গোনা আছে, পাঠ বসানো হয়নি।')
        # উপরের বাক্যে হাজার-কমা + «পদ»র যোগ হয়ে দাঁড়াত «৩৫১টি পদর» —
        # বিশুদ্ধ বানান রক্ষা: meta["word"]-এর পরে সরাসরি «র» নয়, মিলিয়ে।
        src = re.sub(re.escape(meta["word"]) + r"র বাংলা পাঠ",
                     meta["word"] + "ের বাংলা পাঠ", src)
    if idx.get("note"):   # ডেটার টীকা সবার শেষে (আগে দুবার যোগ হতো)
        src += " " + idx["note"]
    if en_n and meta.get("kind") == "bible":
        src += (" ইংরেজি অনুবাদ: The New American Bible — vatican.va। যেসব অধ্যায়ে বাংলার সঙ্গে "
                "পদ-সংখ্যা ও পদ-নম্বর হুবহু মিলেছে, সেখানেই ইংরেজি দেখানো হয়; যে অধ্যায়ে দুই "
                "সংস্করণের পদ-বিন্যাস আলাদা, সেখানে ইংরেজি বাদ রাখা হয়েছে (অনুমান করে বসানো হয় না)।")
    h = re.sub(r'<div class="g-src"><b>পাঠ সম্পর্কে।</b>.*?</div>',
               f'<div class="g-src"><b>পাঠ সম্পর্কে।</b> {src}</div>', h, count=1, flags=re.S)

    label = f"{main} {sub}".strip()
    # বাইবেলের description হাতে লেখা জেনেরিকে ডিফল্টে পড়ত: «বাংলা বাইবেল-র
    # ৩১,১৩০টি পদ…» — দ্বিতীয় শব্দে «-র» জোড়া বানান আর পুস্তক-সংখ্যা বাদ।
    # ক্যানোনিকাল বর্ণনা এখানেই তৈরি হয়, তাই বিশেষ-কেসটাও এখানে রাখা হলো।
    if meta.get("kind") == "bible":
        fulldesc = (f"বাংলা বাইবেলের সম্পূর্ণ পাঠ — {commas(nch)} পুস্তক, "
                    f"{commas(withbn)} পদ বাংলা অনুবাদসহ (ebanglalibrary.com)।")
    elif slug == "atharvaveda":
        fulldesc = (f"{label} — {commas(nch)} কাণ্ড, {commas(total)} মন্ত্র সংস্কৃত মূল পাঠ, "
                    f"{commas(en_n)} মন্ত্রে ইংরেজি ও {commas(withbn)} মন্ত্রে বাংলা অনুবাদসহ।")
    elif slug == "samaveda":
        fulldesc = (f"{label} — {commas(nch)} অধ্যায়, {commas(total)} মন্ত্র সস্বর সংস্কৃত মূল পাঠ, "
                    f"{commas(withbn)} মন্ত্রে বাংলা ও {commas(en_n)} মন্ত্রে ইংরেজি অনুবাদসহ।")
    elif slug == "shvetashvatara":
        fulldesc = (f"{label} — {commas(nch)} অধ্যায়, {commas(total)} মন্ত্র মূল সংস্কৃত পাঠ, "
                    f"স্বামী লোকেশ্বরানন্দের বাংলা সরলার্থ ও F. Max Müller-এর ইংরেজি অনুবাদসহ।")
    elif slug == "prashna":
        fulldesc = (f"{label} — {commas(nch)} প্রশ্ন, {commas(total)} মন্ত্র মূল সংস্কৃত পাঠ, "
                    f"স্বামী লোকেশ্বরানন্দের বাংলা সরলার্থ ও F. Max Müller-এর ইংরেজি অনুবাদসহ।")
    elif slug == "chandogya":
        fulldesc = (f"{label} — {commas(nch)} অধ্যায়, {commas(nsuk)} খণ্ড ও {commas(total)} মন্ত্র মূল সংস্কৃত পাঠ, "
                    f"বাংলা সরলার্থ ও F. Max Müller-এর ইংরেজি অনুবাদসহ।")
    elif slug == "brihadaranyaka":
        fulldesc = (f"{label} — {commas(nch)} অধ্যায়, {commas(nsuk)} ব্রাহ্মণ ও {commas(total)} মন্ত্র মূল সংস্কৃত পাঠ, "
                    f"স্বামী গম্ভীরানন্দের বাংলা সরলার্থ ও F. Max Müller / Robert E. Hume-এর ইংরেজি অনুবাদসহ।")
    elif meta.get("kind") == "tripitaka":
        fulldesc = meta["intro"]
    elif not withbn:
        fulldesc = meta["intro"]
    else:
        fulldesc = f'{label}-র {commas(withbn)}টি {meta["word"]} বাংলা অনুবাদসহ — ebanglalibrary.com।'
    # সতর্কতা: দশার-অভাবে হঠাৎ বড় পতন (যেমন ৯২২২ → ২১ শ্লোক) সাইটে বসিয়ে দেব না।
    env = os.environ.get("GRANTHO_ALLOW_SHRINK", "").strip().lower() in ("1", "true", "yes")
    if not env and (outdir / f"{slug}.html").exists():
        old_html = (outdir / f"{slug}.html").read_text(encoding="utf-8")
        m = re.search(r'<span class="g-fact"><b>([০-৯,]+)</b>\s*' + re.escape(meta["word"]),
                      old_html)
        if m:
            prev = int(m.group(1).replace(",", "").translate(BN_MAP))
            cmp_cur = withbn if withbn else total
            if prev and cmp_cur < prev * 0.85:
                raise Shrink(f"{slug}: পুরনো পাতায় {prev}, নতুন ডেটায় {cmp_cur} — "
                             f"হঠাৎ বড় পতন")

    if not withbn:
        page_title = (f'{label} — {commas(total)} {meta["word"]}, সংস্কৃত ও ইংরেজি | Ebrahim Ead'
                      if en_n else f'{label} — {commas(total)} {meta["word"]}, সংস্কৃত মূল পাঠ | Ebrahim Ead')
        tw_title = f'{label} — {commas(total)} {meta["word"]}'
    else:
        page_title = f'{label} — {commas(withbn)} {meta["word"]}, বাংলা অনুবাদসহ | Ebrahim Ead'
        tw_title = f'{label} — {commas(withbn)} {meta["word"]}'

    h = re.sub(r'<title>[^<]*</title>', f'<title>{page_title}</title>', h, count=1)
    for pat, val in ((r'(<meta name="description" content=")[^"]*(")', fulldesc),
                     (r'(<meta property="og:title" content=")[^"]*(")', page_title),
                     (r'(<meta property="og:description" content=")[^"]*(")', fulldesc),
                     (r'(<meta name="twitter:title" content=")[^"]*(")', tw_title),
                     (r'(<meta name="twitter:description" content=")[^"]*(")', fulldesc)):
        h = re.sub(pat, lambda m, v=val: m.group(1) + v + m.group(2), h, count=1)

    # বাইবেলের নিজস্ব পাঠক-ইঞ্জিন — grantho.js চারটি গ্রন্থ শেয়ার করে, আর
    # বাইবেলের আচরণ আলাদা করে গোছাতে হলে ওটায় হাত দিতে হতো (অন্য তিনটি
    # গ্রন্থ ভাঙার ঝুঁকি)। তাই টেমপ্লেট থেকে আসা grantho.js-ট্যাগটি এখানেই
    # বদলে দেওয়া হয় — নইলে প্রতি রাতের rebuild-এ পাতা আবার পুরোনো ইঞ্জিনে
    # ফিরে যেত (২০২৬-১১-১৬-এ ঠিক এমনটাই হয়েছিল)।
    if meta.get("kind") == "bible":
        h = re.sub(
            r'<script src="\.\./\.\./assets/grantho/grantho\.js(?:\?v=[0-9a-f]+)?" defer></script>',
            '<script src="../../assets/grantho/bible-reader.js" defer></script>',
            h,
        )

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{slug}.html").write_text(
        normalize(slug, h, meta.get("dir", "hindu")), encoding="utf-8")
    return dict(slug=slug, total=total, withbn=withbn, nch=nch, nsuk=nsuk, with_en=en_n)


def make_mahabharata_page(idx):
    """মহাভারত (১৮ পর্ব × বাংলা/ইংরেজি/সংস্কৃত) — নিজস্ব mahabharata-reader.js সহ।"""
    ed = idx.get("editions", {})
    n_parvas = len(idx.get("parvas") or [])
    bn_chs = int(idx.get("bnChTotal") or ed.get("bn", {}).get("chapters") or 0)
    bn_upas = int(idx.get("bnUpaTotal") or ed.get("bn", {}).get("upakhyanas") or 0)
    en_secs = int(idx.get("enSecTotal") or ed.get("en", {}).get("sections") or 0)
    sa_chs = int(idx.get("saChTotal") or ed.get("sa", {}).get("chapters") or 0)
    sa_shl = int(idx.get("saShlokaTotal") or ed.get("sa", {}).get("shlokas") or 0)

    h = TEMPLATE
    h = re.sub(r'data-granth="[^"]*"', 'data-granth="mahabharata"', h, count=1)
    h = re.sub(r'data-base="[^"]*"', 'data-base="../../assets/grantho/data/mahabharata/"', h, count=1)
    h = re.sub(r'(<span class="g-kicker2?">)[^<]*(</span>)',
               lambda m: m.group(1) + 'হিন্দু · মহাকাব্য · মহাভারত' + m.group(2), h)
    h = re.sub(r'(<h1[^>]*>).*?(</h1>)',
               lambda m: m.group(1) + 'মহাভারত' + m.group(2), h, count=1, flags=re.S)
    h = re.sub(r'(<p class="g-crumb">).*?(</p>)',
               lambda m: m.group(1) + '<a href="../../grantho.html">ধর্মীয় গ্রন্থ</a><span>›</span><a href="../hindu.html">হিন্দু</a><span>›</span>মহাভারত' + m.group(2),
               h, count=1, flags=re.S)

    intro = (f"ব্যাসদেব রচিত মহাভারতের {commas(n_parvas)}টি পর্ব — কালীপ্রসন্ন সিংহের বাংলা গদ্যানুবাদ "
             f"({commas(bn_chs)} অধ্যায়, {commas(bn_upas)} উপাখ্যান), কিশোরীমোহন গাঙ্গুলীর ইংরেজি অনুবাদ "
             f"({commas(en_secs)} পরিচ্ছেদ ও পাদটীকা) এবং পূর্ণাঙ্গ দেবনাগরী সংস্কৃত মূল পাঠ "
             f"({commas(sa_chs)} অধ্যায়, {commas(sa_shl)} শ্লোক) একত্রে।")
    h = re.sub(r'(<div class="g-intro">.*?<p>)[^<]*(</p>)',
               lambda m: m.group(1) + intro + m.group(2), h, count=1, flags=re.S)

    facts = (f'<span class="g-fact"><b>{commas(n_parvas)}</b> পর্ব</span>'
             f'<span class="g-fact"><b>{commas(bn_chs)}</b> বাংলা অধ্যায়</span>'
             f'<span class="g-fact"><b>{commas(en_secs)}</b> ইংরেজি পরিচ্ছেদ</span>'
             f'<span class="g-fact"><b>{commas(sa_shl)}</b> সংস্কৃত শ্লোক</span>')
    h = re.sub(r'<div class="g-facts">.*?</div>', '<div class="g-facts">' + facts + '</div>',
               h, count=1, flags=re.S)

    h = re.sub(r'(<input id="g-search"[^>]*placeholder=")[^"]*(")',
               lambda m: m.group(1) + 'এই পর্বে খুঁজুন (বাংলা / ইংরেজি / সংস্কৃত)' + m.group(2), h, count=1)
    h = re.sub(r'(<input id="g-search"[^>]*aria-label=")[^"]*(")',
               lambda m: m.group(1) + 'পর্বে খুঁজুন' + m.group(2), h, count=1)
    h = re.sub(r'<button[^>]*id="g-bn-btn"[^>]*>.*?</button>',
               '<div id="g-mbh-ed" class="g-mbh-ed" role="group" aria-label="সংস্করণ বেছে নিন"></div>',
               h, count=1, flags=re.S)
    h = re.sub(r'(<b id="g-side-title">)[^<]*(</b>)',
               lambda m: m.group(1) + 'পর্ব' + m.group(2), h, count=1)
    h = re.sub(r'(<div id="g-chapter-grid"[^>]*aria-label=")[^"]*(")',
               lambda m: m.group(1) + 'অধ্যায় ও পরিচ্ছেদ' + m.group(2), h, count=1)
    if 'id="g-en-note"' not in h and '<div id="g-bn-note"' in h:
        h = h.replace('<div id="g-bn-note"',
                      '<div id="g-en-note" class="g-en-note" hidden></div>\n        <div id="g-bn-note"', 1)
    h = h.replace('<span class="sr-only">মন্ত্র লোড হচ্ছে…</span>',
                  '<span class="sr-only">অধ্যায় লোড হচ্ছে…</span>')

    src = (f'বাংলা গদ্যানুবাদ: কালীপ্রসন্ন সিংহ ({commas(n_parvas)} পর্ব, {commas(bn_chs)} অধ্যায়, '
           f'{commas(bn_upas)} উপাখ্যান; ডিজিটাল বাংলা উৎসে আদিপর্ব অধ্যায় ১৫৪, উদ্যোগপর্ব অধ্যায় ৯৩ ও ১৮৬ '
           f'এবং শল্যপর্ব অধ্যায় ৪৬–৬৫ অনুপস্থিত — অনুমান করে কোনো পাঠ বসানো হয়নি)। '
           f'ইংরেজি অনুবাদ: Kisari Mohan Ganguli (sacred-texts.com — {commas(en_secs)} পরিচ্ছেদ, '
           f'মূল ভূমিকা ও পাদটীকাসহ)। মূল সংস্কৃত (দেবনাগরী): কুম্ভকোণম্ ও মহাপ্রস্থানিক সংকলন '
           f'({commas(sa_chs)} অধ্যায়, {commas(sa_shl)} শ্লোক — উইকিসংকলন ও কুম্ভকোণম্ থেকে অনুপস্থিত '
           f'অধ্যায় ও শ্লোক মিলিয়ে সম্পূর্ণ)।')
    h = re.sub(r'<div class="g-src"><b>পাঠ সম্পর্কে।</b>.*?</div>',
               f'<div class="g-src"><b>পাঠ সম্পর্কে।</b> {src}</div>', h, count=1, flags=re.S)

    page_title = f'মহাভারত — {commas(n_parvas)} পর্ব · বাংলা, ইংরেজি ও {commas(sa_shl)} সংস্কৃত শ্লোক | Ebrahim Ead'
    tw_title = f'মহাভারত — {commas(n_parvas)} পর্ব · {commas(sa_shl)} শ্লোক'
    fulldesc = intro
    h = re.sub(r'<title>[^<]*</title>', f'<title>{page_title}</title>', h, count=1)
    for pat, val in ((r'(<meta name="description" content=")[^"]*(")', fulldesc),
                     (r'(<meta property="og:title" content=")[^"]*(")', page_title),
                     (r'(<meta property="og:description" content=")[^"]*(")', fulldesc),
                     (r'(<meta name="twitter:title" content=")[^"]*(")', tw_title),
                     (r'(<meta name="twitter:description" content=")[^"]*(")', fulldesc)):
        h = re.sub(pat, lambda m, v=val: m.group(1) + v + m.group(2), h, count=1)

    h = re.sub(
        r'<script src="\.\./\.\./assets/grantho/grantho\.js(?:\?v=[0-9a-f]+)?" defer></script>',
        '<script src="../../assets/grantho/mahabharata-reader.js" defer></script>',
        h,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mahabharata.html").write_text(normalize("mahabharata", h, "hindu"), encoding="utf-8")
    return dict(slug="mahabharata", nch=n_parvas, bn_chs=bn_chs, en_secs=en_secs, sa_chs=sa_chs, sa_shl=sa_shl)


def refresh_sitemap(entries):
    """বানানো পাতাগুলোর ঠিকানা sitemap.xml-এ আছে কি না দেখে, না থাকলে যোগ।

    কেন: সাইটম্যাপ হাতে রাখা হয়, তাই নতুন গ্রন্থ-পাতা (যেমন বাইবেল) যোগ হলে
    সেটি বাদ পড়ে যেত — সার্চ-ইঞ্জিন তখন পাতাটি খুঁজে পেত না।
    """
    f = ROOT / "sitemap.xml"
    if not f.exists():
        return 0
    s = f.read_text(encoding="utf-8")
    added = 0
    for slug, sub in entries:
        url = f"{SITE}/grantho/{sub}/{slug}.html"
        if url in s:
            continue
        # বিদ্যমান এন্ট্রির সাথে একই ফরম্যাট (এক লাইনে, lastmod সহ)
        today = datetime.date.today().isoformat()
        block = (f'  <url><loc>{url}</loc><lastmod>{today}</lastmod>'
                 f'<changefreq>weekly</changefreq><priority>0.7</priority></url>\n')
        s = s.replace("</urlset>", block + "</urlset>", 1)
        added += 1
    if added:
        f.write_text(s, encoding="utf-8")
        print(f"  সাইটম্যাপে যোগ: {added}টি পাতা")
    return added


def card(href, kicker, title, sub, excerpt="", soon=False):
    """হাবের কার্ড — ছোট, শুধু নাম আর এক লাইনের হিসাব।

    কেন: আগে প্রতিটি কার্ডে ট্যাগ, বড় শিরোনাম, দুই লাইনের বিবরণ আর
    «পড়ুন →» বাটন ছিল — ফোনে ইসলামের ভেতরে কুরআন/হাদিস দেখতে অনেক
    স্ক্রল করতে হত। এখন ট্যাগ ও বড় বিবরণ বাদ (`excerpt` আর ব্যবহার হয়
    না, শুধু interface মিলিয়ে রাখতে আছে); নামের নিচে ছোট মিউটেড লাইনে
    সংখ্যা (`sub`), ডানে সরু তির।
    """
    if soon:
        return (f'<article class="article-card rv cmp-card is-soon">'
                f'<a class="article-card-link" href="#" aria-disabled="true" tabindex="-1">'
                f'<span class="cmp-body"><h2 class="cmp-title">{title}</h2>'
                f'<span class="cmp-meta">{sub}</span></span>'
                f'<span class="cmp-go" aria-hidden="true">→</span></a></article>')
    return (f'<article class="article-card rv cmp-card">'
            f'<a class="article-card-link" href="{href}">'
            f'<span class="cmp-body"><h2 class="cmp-title">{title}</h2>'
            f'<span class="cmp-meta">{sub}</span></span>'
            f'<span class="cmp-go" aria-hidden="true">→</span></a></article>')


def replace_grid(page, inner, sub="hindu"):
    p = (OUT if sub == "hindu" else OUT.parent / sub) / page
    if not p.exists():
        print("  (পাতা নেই)", page)
        return
    s = p.read_text(encoding="utf-8")
    # গ্রিডের শেষে সব পাতায় g-note/g-back থাকে না (হিন্দু-হাবে নেই) —
    # তাই ওগুলো থাকলে সেখানেই থামি, নাহলে বন্ধ-ট্যাগের আগেই।
    m = re.search(r'<div class="g-grid">.*?</div>\s*(?=<div class="g-note"|<a class="g-back"|</section>|</main>)',
                  s, re.S)
    if not m:
        print("  (গ্রিড খুঁজে পাইনি)", page)
        return
    s = s[:m.start()] + '<div class="g-grid">' + inner + '</div>\n  ' + s[m.end():]
    p.write_text(s, encoding="utf-8")
    print("  গ্রিড আপডেট:", page)


def refresh_rigveda_layout():
    """ঋগ্বেদে সূক্ত/শ্লোক-ভাগ হালনাগাদ করি (নতুন মণ্ডল নামলে দরকার হয়)।"""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import rigveda_suktas
    except Exception as e:
        print("  (সূক্ত-ভাগ বাদ:", e, ")")
        return
    try:
        rigveda_suktas.main(apply=True)
    except Exception as e:
        print("  (সূক্ত-ভাগ ব্যর্থ:", e, ")")


def main():
    made = []
    if (DATA / "rigveda" / "index.json").exists():
        refresh_rigveda_layout()
    # ---- বেদ
    vedas = []
    for slug in [x for x in ("rigveda", "samaveda", "yajurveda-shukla", "atharvaveda",
                             "yajurveda-krishna") if x in ACTIVE]:
        meta = BOOKS.get(slug)
        idx = load(slug)
        if not meta or not idx:
            continue
        r = make_page(slug, idx, meta)
        made.append(r)
        vedas.append((slug, r, meta))
        print(f"{slug}: {r['withbn']}/{r['total']} · {r['nch']}")

    grid = ""
    order = ["rigveda", "samaveda", "yajurveda-shukla", "atharvaveda", "yajurveda-krishna"]
    byslug = {s: (r, m) for s, r, m in vedas}
    labels = {"rigveda": ("বেদ · ঋগ্বেদ", "ঋগ্বেদ"),
              "samaveda": ("বেদ · সামবেদ", "সামবেদ"),
              "yajurveda-shukla": ("বেদ · শুক্ল যজুর্বেদ", "শুক্ল যজুর্বেদ"),
              "atharvaveda": ("বেদ · অথর্ববেদ", "অথর্ববেদ"),
              "yajurveda-krishna": ("বেদ · কৃষ্ণ যজুর্বেদ", "কৃষ্ণ যজুর্বেদ")}
    for slug in order:
        if slug in byslug:
            r, m = byslug[slug]
            k, t = labels[slug]
            # «বাংলা অনুবাদসহ» বাদ: কার্ড ছোট রাখার চাহিদা — সংখ্যাটাই যথেষ্ট
            shown_n = r["total"] if slug == "atharvaveda" else r["withbn"]
            grid += card(f"{slug}.html", k, t,
                         f'{commas(shown_n)} {m["word"]} · {commas(r["nch"])} {m["chword"]}',
                         m["excerpt"])
        elif slug in ACTIVE and slug in ("yajurveda-krishna",):
            k, t = labels[slug]
            grid += card("", k, t, "কৃষ্ণ শাখা — শীঘ্রই",
                         "যজ্ঞের বিধি ও মন্ত্রের বেদ — উৎস থেকে পাঠ নামানো হচ্ছে।", soon=True)
    replace_grid("veda.html", grid)

    # ---- মহাভারত
    mbh_info = None
    if "mahabharata" in ACTIVE and (DATA / "mahabharata" / "index.json").exists():
        mbh_idx = json.loads((DATA / "mahabharata" / "index.json").read_text(encoding="utf-8"))
        if mbh_idx.get("parvas"):
            mbh_info = make_mahabharata_page(mbh_idx)
            made.append({"slug": "mahabharata"})
            print(f"mahabharata: {mbh_info['nch']} পর্ব · bn={mbh_info['bn_chs']} · "
                  f"en={mbh_info['en_secs']} · sa={mbh_info['sa_shl']}")

    # ---- উপনিষদ
    upa_cards, upa_total = "", 0
    for slug in list(UPA):
        idx = load(slug) if slug in ACTIVE else None
        if not idx:
            continue
        name, ex = UPA[slug]
        r = make_page(slug, idx, dict(
            kind="upanishad", title=(name, ""), hub="upanishad.html", hubname="উপনিষদ",
            kicker="হিন্দু · উপনিষদ · " + name.replace(" উপনিষদ", ""),
            crumb=name,
            intro=f"{name} — সংস্কৃত মূল, অন্বয়, সরলার্থ ও ব্যাখ্যা; বাংলা ebanglalibrary.com থেকে (স্বামী লোকেশ্বরানন্দ)।",
            word="মন্ত্র", chword="খণ্ড",
            src="সংস্কৃত মূল বাংলা অক্ষরে (উৎস-সংস্করণ অনুসারে); বাংলা অনুবাদ ও ব্যাখ্যা ebanglalibrary.com (স্বামী লোকেশ্বরানন্দ, «উপনিষদ – প্রথম ভাগ»)।",
            excerpt=ex))
        upa_total += r["withbn"]
        upa_cards += card(f'{slug}.html', f'উপনিষদ · {name.replace(" উপনিষদ","")}', name,
                          f'{commas(r["withbn"])} মন্ত্র · {commas(r["nch"])} খণ্ড', ex)
        print(f"{slug}: {r['withbn']}")
    # শ্বেতাশ্বতর/কঠ/ছান্দোগ্য হাতে-বানানো পাতা — সেগুলো আগে রাখি
    if upa_cards and (OUT / "upanishad.html").exists():
        s = (OUT / "upanishad.html").read_text(encoding="utf-8")
        fixed = []
        for href in ("shvetashvatara.html", "katha.html", "chandogya.html"):
            m = re.search(r'<article class="article-card rv"><a class="article-card-link" href="' + href + r'">.*?</article>', s, re.S)
            if m:
                fixed.append(m.group(0))
                fn = href.replace(".html", "")
                idx = load(fn)
                if idx:
                    upa_total += idx.get("withBn", 0)
        replace_grid("upanishad.html", "".join(fixed) + upa_cards +
                     card("", "উপনিষদ · প্রধান ১৩", "বাকি প্রধান উপনিষদ",
                          "বৃহদারণ্যক · কৌষীতমি · মৈত্রায়ণী",
                          "উৎসে যেগুলো পূর্ণ পাওয়া যায়নি সেগুলো পরে যোগ হবে।", soon=True))
    print("উপনিষদ মোট:", upa_total)

    # ---- প্রধান উপনিষদসমূহ
    for up_slug in ("shvetashvatara", "prashna", "chandogya", "brihadaranyaka"):
        if up_slug in ACTIVE:
            s_idx = load(up_slug)
            s_meta = BOOKS.get(up_slug)
            if s_idx and s_meta:
                r = make_page(up_slug, s_idx, s_meta)
                made.append(r)
                print(f"{up_slug}: {r['withbn']}/{r['total']} · {r['nch']}")

    # ---- হিন্দু-হাব: কার্ডগুলো ডেটা থেকেই বানাই
    #   আগে এই পাতা হাতে লেখা কার্ড ধরে সংখ্যা আপডেট করত, ফলে কার্ডের
    #   গঠন (বড় বিবরণ/বাটন) বদলাতে গেলে হাতে-এডিট ছাড়া উপায় ছিল না —
    #   রি-বিল্ডে সেটা ফিরেও যেত। এখন বেদের মতোই replace_grid দিয়ে তৈরি।
    if made or upa_cards:
        hp_cards = ""
        g = load("gita")
        if g:
            hp_cards += card("hindu/gita.html", "হিন্দু · গীতা", "শ্রীমদ্ভগবদ্গীতা",
                             f'{commas(g["withBn"])} শ্লোক · {commas(len(g["chapters"]))} অধ্যায়')
        rv = next((r for sl, r, _ in vedas if sl == "rigveda"), None)
        if rv:
            hp_cards += card("hindu/rigveda.html", "হিন্দু · বেদ", "ঋগ্বেদ সংহিতা",
                             f'{commas(rv["withbn"])} মন্ত্র · {commas(rv["nch"])} মণ্ডল')
        sv = next((r for sl, r, _ in vedas if sl == "samaveda"), None)
        if sv:
            hp_cards += card("hindu/samaveda.html", "হিন্দু · বেদ", "সামবেদ সংহিতা",
                             f'{commas(sv["withbn"])} মন্ত্র · {commas(sv["nch"])} অধ্যায়')
        yv = next((r for sl, r, _ in vedas if sl == "yajurveda-shukla"), None)
        if yv:
            hp_cards += card("hindu/yajurveda-shukla.html", "হিন্দু · বেদ", "শুক্ল যজুর্বেদ সংহিতা",
                             f'{commas(yv["withbn"])} মন্ত্র · {commas(yv["nch"])} অধ্যায়')
        av = next((r for sl, r, _ in vedas if sl == "atharvaveda"), None)
        if av:
            hp_cards += card("hindu/atharvaveda.html", "হিন্দু · বেদ", "অথর্ববেদ সংহিতা",
                             f'{commas(av["total"])} মন্ত্র · {commas(av["nch"])} কাণ্ড')
        for up_slug, up_name in (
            ("shvetashvatara", "শ্বেতাশ্বতর উপনিষদ"),
            ("prashna", "প্রশ্ন উপনিষদ"),
            ("chandogya", "ছান্দোগ্য উপনিষদ"),
            ("brihadaranyaka", "বৃহদারণ্যক উপনিষদ"),
        ):
            up_r = next((r for r in made if r["slug"] == up_slug), None)
            if up_r:
                up_m = BOOKS[up_slug]
                hp_cards += card(f"hindu/{up_slug}.html", f"হিন্দু · উপনিষদ", up_name,
                                 f'{commas(up_r["withbn"])} মন্ত্র · {commas(up_r["nch"])} {up_m["chword"]}')
        if mbh_info:
            hp_cards += card("hindu/mahabharata.html", "হিন্দু · মহাকাব্য", "মহাভারত",
                             f'{commas(mbh_info["nch"])} পর্ব · {commas(mbh_info["sa_shl"])} সংস্কৃত শ্লোক')
        if hp_cards:
            replace_grid("hindu.html", hp_cards, sub="")
        print("হিন্দু-হাব:", sum(r["withbn"] for _, r, _ in vedas))

    # ---- ইসলাম-হাব: কুরআন ও হাদিসের কার্ড (হাতে লেখা নয়)
    #   সংখ্যা ডেটা থেকেই — পাঠ বাড়লে/কমলে কার্ড নিজেই ঠিক হয়।
    isl = ""
    qf = ROOT / "assets/quran/data/index.json"
    hf = ROOT / "assets/hadith/data/index.json"
    if qf.exists():
        q = json.loads(qf.read_text(encoding="utf-8"))
        n_sura = len(q.get("suras") or [])
        isl += card("../quran.html", "ইসলাম · কুরআন", "আল-কুরআনুল কারীম",
                    f'{commas(n_sura)} সূরা · {commas(q.get("total") or 0)} আয়াত')
    if hf.exists():
        h = json.loads(hf.read_text(encoding="utf-8"))
        isl += card("../hadith.html", "ইসলাম · হাদিস", "হাদিস",
                    f'সিহাহ সিত্তাহ ও মিশকাত — {commas(h.get("total") or 0)} হাদিস')
    if isl:
        replace_grid("islam.html", isl, sub="")
        print("ইসলাম-হাব: কার্ড তৈরি")

    # ---- বৌদ্ধ-হাব: ডিজিটাল পাঠক (ধম্মপদ, চার নিকায় ও বিনয়)
    bud_cards = ""
    bud_built = []
    for bslug in ("dhammapada", "digha-nikaya", "majjhima-nikaya",
                  "samyutta-nikaya", "anguttara-nikaya", "vinaya-vibhanga"):
        if bslug not in ACTIVE:
            continue
        bidx = load(bslug)
        bmeta = BOOKS.get(bslug)
        if not bidx or not bmeta:
            continue
        br = make_page(bslug, bidx, bmeta)
        bud_built.append((bslug, "buddhist"))
        print(f"{bslug}: {br['withbn']}/{br['total']} · {br['nch']}")
        title_str = " ".join(x for x in bmeta["title"] if x)
        if bslug == "dhammapada":
            sub_str = f'{commas(bidx.get("gathaTotal") or br["total"])} গাথা · {commas(br["nch"])} {bmeta["chword"]}'
        else:
            sub_str = f'{commas(br["total"])} {bmeta["word"]} · {commas(br["nch"])} {bmeta["chword"]}'
        bud_cards += card(f"buddhist/{bslug}.html", bmeta["kicker"], title_str, sub_str)
    if bud_cards:
        replace_grid("buddhist.html", bud_cards, sub="")

    # ---- খ্রিস্টান: বাংলা বাইবেল
    built = [(r["slug"], "hindu") for r in made] + bud_built
    if "bible" in ACTIVE:
        idx = load("bible")
        meta = BOOKS.get("bible")
        if idx and meta:
            r = make_page("bible", idx, meta)
            if r:
                built.append(("bible", "christian"))
                chs = idx["chapters"]
                old = sum(1 for c in chs if c.get("testament") == "old")
                part = sum(1 for c in chs if c.get("missing"))
                # কার্ড ছোট রাখার চাহিদা — নিয়ম-ভাগ বাদ, শুধু পদ/পুস্তক/অধ্যায়
                sub = f'{commas(r["withbn"])} পদ · {commas(r["nch"])} পুস্তক'
                # english-bible কার্ডও এখানেই তৈরি হয় — নাহলে প্রতিবার গ্রিড
                # নতুন করে লেখার সময় (replace_grid পুরোটা বদলে দেয়) কার্ডটি
                # হারিয়ে যায়। ডেটা না থাকলে কার্ড বসানো হয় না।
                en = load("bible/english")
                en_card = ""
                if en and en.get("total"):
                    en_card = card(
                        "christian/english-bible.html", "খ্রিস্টান · বাইবেল",
                        "English Bible",
                        f'{commas(en["total"])} পদ · {commas(en["totalBooks"])} পুস্তক · The New American Bible',
                        "")
                replace_grid("christian.html",
                             card("christian/bible.html", "খ্রিস্টান · বাইবেল",
                                  "বাংলা বাইবেল", sub, meta["excerpt"]) + en_card, sub="")
                print(f"bible: {r['withbn']}/{r['total']} · {r['nch']} পুস্তক · "
                      f"{idx.get('suktaTotal') or sum(c.get('suktaCount', 0) for c in chs)} অধ্যায়")
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import seo as _seo
    except Exception:
        _seo = None
    stamped = 0
    for hp in sorted((ROOT / "grantho").rglob("*.html")):
        raw = hp.read_text(encoding="utf-8")
        upd = stamp_grantho_assets(raw)
        if _seo is not None:
            upd, _ = _seo.add_meta(upd, _seo.DEFAULT_BASE, hp)
        if upd != raw:
            hp.write_text(upd, encoding="utf-8")
            stamped += 1
    if stamped:
        print(f"গ্রন্থ-অ্যাসেট সংস্করণ (?v=): {stamped}টি পাতা হালনাগাদ")
    refresh_sitemap(built)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Shrink as e:
        print("\n" + "=" * 60)
        print(f"⛔ বিল্ড থামানো হলো — {e}")
        print("ডেটা যাচাই না করে কিছু কমিট/প্রকাশ হবে না। জোর করে বিল্ড করতে:")
        print("   GRANTHO_ALLOW_SHRINK=1 python3 tools/build_pages.py")
        print("=" * 60)
        sys.exit(1)
