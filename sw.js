/* ============================================================
   sw.js — Service Worker (অফলাইন সমর্থন)
   ------------------------------------------------------------
   ## কৌশল — কেন এভাবে

   সাইট ১৮৩ MB। পুরোটা আগেই ক্যাশ করা অসম্ভব (ফোনে জায়গা নেই,
   ব্যবহারকারীর ডেটাও নষ্ট হবে)। তাই তিন স্তরে ভাগ:

   ১. **অ্যাপ-শেল** (≈৪ MB) — HTML/CSS/JS/ফন্ট/আইকন
      install-এ ক্যাশ → অফলাইনেও সাইট খোলে।
   ২. **পেজ** — network-first, ব্যর্থ হলে ক্যাশ।
      ⇒ নতুন লেখা সবসময় আসবে, কিন্তু নেট ছাড়াও পুরোনোটা পড়া যাবে।
   ৩. **ডেটা** (হাদিস/কুরআন/গ্রন্থ JSON, ছবি) — cache-first।
      যা একবার পড়েছেন, পরে নেট ছাড়াই পড়তে পারবেন।

   ## সীমা (দুই ধরনের, দুটোই কার্যকর)

   প্রতিটি ক্যাশে **এন্ট্রি-সংখ্যা** আর **মোট মাপ** — দুটোই মানা হয়।
   যেটা আগে ছাড়ায়, সেটাই বাদ দেওয়ার কারণ হয়।

     শেল  ৩০০ এন্ট্রি / ৬ MB   (৫.১ MB ছবি সহ — কখনো ফুলে যায় না)
     পাতা ২০০ এন্ট্রি / ২৫ MB
     ডেটা ২৫০ এন্ট্রি / ৪৫ MB  (সবচেয়ে বড় ফাইল ২.১ MB)

   ডেটা ৪৫ MB কেন: হাদিসের বড় কিতাবের একটি অধ্যায়ই ~১.৮ MB।
   পুরো একটা কিতাব (বুখারী ৯৭ অধ্যায় ≈ ২০ MB) পড়তে বসলে ৪০ MB-তে
   পুরোনো জমা মুছে গিয়ে আবার নামাতে হত। ৬০০টা ছোট আয়াত-ফাইলের
   জায়গায় এখন ২৫০টা — তবে বড় ফাইলগুলোর জন্য ৪৫ MB যথেষ্ট।

   মাপ কীভাবে মাপি: ক্যাশ করা প্রতিটি `Response`-এর `Content-Length`
   পড়ি; না থাকলে `blob()` করে সত্যিকারের আকার নিই। আকার-স্ক্যান
   প্রতিবার নতুন কিছু ক্যাশ করার পর চলে, আর serialized — একসাথে অনেক
   fetch হলে বারবার পুরো ক্যাশ স্ক্যান করে না।

   ## সংস্করণ

   শেল/পাতার কিছু বদলালে `SHELL_VERSION` বাড়ান — পুরোনো শেল-ক্যাশ
   নিজে মুছে যাবে, কিন্তু ডেটা অটুট থাকবে। ডেটার গঠন (JSON-এর আকার)
   বদলালে তবেই `DATA_VERSION` বাড়ান।
   ============================================================ */

/* শেল ও পাতা আলাদা সংস্করণ নম্বর পায় — শুধু শেল-তালিকা বদলালে
   ব্যবহারকারীর জমানো ডেটা (১৪২ MB পর্যন্ত) মুছে যাওয়া উচিত নয়।
   ডেটার গঠন বদলালে তবেই DATA_VERSION বাড়াবেন। */
var SHELL_VERSION = 'v2';
var DATA_VERSION = 'v1';

var SHELL_CACHE = 'ead-shell-' + SHELL_VERSION;
var PAGE_CACHE = 'ead-pages-' + SHELL_VERSION;
var DATA_CACHE = 'ead-data-' + DATA_VERSION;

/* ---- ক্যাশ-বাজেট: [সর্বোচ্চ এন্ট্রি, সর্বোচ্চ বাইট] ---- */
var LIMITS = {};
LIMITS[SHELL_CACHE] = [300, 6 * 1024 * 1024];
LIMITS[PAGE_CACHE] = [200, 25 * 1024 * 1024];
LIMITS[DATA_CACHE] = [250, 45 * 1024 * 1024];

/* ---- অ্যাপ-শেল: যা ছাড়া সাইট চলে না ----
   ইনস্টলে কেবল এগুলোই নামে — দ্রুত ইনস্টল, কম ডেটা।
   ২০২ KB ফন্ট ১.৪ MB TTF-এর বদলে এসেছে; search-index.js (২৭৮ KB)
   আর এখানে নেই — সার্চ খুললে runtime-এ ক্যাশ হবে। */
var SHELL = [
  '/ead/',
  '/ead/index.html',
  '/ead/offline.html',
  '/ead/manifest.json',

  '/ead/assets/site.css',
  '/ead/assets/site-extra.css',
  '/ead/assets/nav-motion.css',
  '/ead/assets/site-motion.css',
  '/ead/assets/nav-motion.js',
  '/ead/assets/site-motion.js',
  '/ead/assets/site-search.js',
  '/ead/assets/pwa.js',

  '/ead/assets/fonts/noto-sans-bengali.woff2',

  '/ead/assets/img/favicon-32.png',
  '/ead/assets/img/icon-192.png',
  '/ead/assets/img/apple-touch-icon.png',

  /* হোম-পাতার প্রথম দৃশ্যের ছবি — অফলাইনে প্রথম খোলাতেই দেখা যাবে */
  '/ead/assets/img/1f4b2d3123.webp',
  '/ead/assets/img/f2b99e768b.webp'
];

/* ---- ইনস্টলের পরেই নামুক (নীরবে, সাইট চলার পথ আটকাবে না) ----
   এগুলো বড়/কম-দরকারি — SHELL শেষ হলে আলাদাভাবে নামাই। */
var PREFETCH = [
  '/ead/assets/search-index.js',
  '/ead/assets/reader-tools.js',
  '/ead/assets/book-pdf.js',
  '/ead/assets/article-pages.js',
  '/ead/assets/img/icon-512.png',
  '/ead/assets/img/icon-maskable-512.png',
  '/ead/assets/img/b612b62bb3.jpg'
];

/* ---- ক্লায়েন্ট ইনস্টল-মোডে (standalone) চলছে কি ----
   Navigation-অনুরোধে display-mode জানা যায় না, তাই ক্লায়েন্ট-তালিকা
   দেখি। ব্যর্থ হলে false — অর্থাৎ আগের নিরাপদ network-first। */
function isStandaloneNav() {
  return self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    .then(function (list) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].frameType === 'top-level' &&
            /standalone|minimal-ui/.test(list[i].displayMode || '')) return true;
      }
      return false;
    })
    .catch(function () { return false; });
}

/* ---- কোন পথে ডেটা (cache-first) ---- */
function isData(url) {
  return /\/(assets\/(hadith|quran|grantho|filistin)\/|search-ayahs\.js$)/.test(url.pathname);
}

/* ---- কোন পথে শেল-ফাইল (cache-first, দ্রুত) ---- */
function isShellAsset(url) {
  return /\.(css|js|woff2?|ttf|png|jpg|jpeg|webp|svg|ico)$/.test(url.pathname);
}

/* ============================================================
   install — শেল ক্যাশ
   ============================================================ */
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(function (cache) {
      /* আলাদা আলাদা করে যোগ করি: একটা ফাইল ব্যর্থ হলে
         পুরো install ভেঙে না যায়। */
      return Promise.all(
        SHELL.map(function (u) {
          return cache.add(new Request(u, { cache: 'reload' })).catch(function () {
            /* স্কিপ — পরে runtime-এ ধরা পড়বে */
          });
        })
      );
    }).then(function () {
      /* SHELL প্রস্তুত — এখন বাকিগুলো নীরবে নামাই।
         একটা ব্যর্থ হলেও install ভাঙে না। */
      return caches.open(SHELL_CACHE).then(function (cache) {
        return Promise.all(PREFETCH.map(function (u) {
          return cache.add(new Request(u, { cache: 'reload' })).catch(function () {});
        }));
      });
    }).then(function () {
      return self.skipWaiting();   /* নতুন SW সঙ্গে সঙ্গে সক্রিয় */
    })
  );
});

/* ============================================================
   activate — পুরোনো সংস্করণের ক্যাশ মুছি
   ============================================================ */
self.addEventListener('activate', function (event) {
  var keep = [SHELL_CACHE, PAGE_CACHE, DATA_CACHE];
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names.map(function (n) {
          /* শুধু আমাদের নিজের পুরোনো ক্যাশ — অন্য কিছুর ছোঁব না */
          if (n.indexOf('ead-') === 0 && keep.indexOf(n) === -1) {
            return caches.delete(n);
          }
        })
      );
    }).then(function () {
      /* navigationPreload: ব্রাউজার নেটওয়ার্ক-অনুরোধ SW চালুর সাথে
         সাথেই شروع করে — SW ও নেটওয়ার্ক সমান্তরালে চলে, তাই প্রথম
         পাতাটা আগে আসে (ইনস্টল করা অ্যাপে বোধগম্যভাবে দ্রুত)। */
      if (self.registration.navigationPreload) {
        return self.registration.navigationPreload.enable().catch(function () {});
      }
    }).then(function () {
      return self.clients.claim();  /* খোলা ট্যাবও নতুন SW পায় */
    })
  );
});

/* ============================================================
   fetch — কৌশল নির্বাচন
   ============================================================ */
self.addEventListener('fetch', function (event) {
  var req = event.request;

  /* শুধু GET; বাইরের ডোমেইন ছোঁব না */
  if (req.method !== 'GET') return;
  var url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (url.origin !== self.location.origin) return;

  /* নেভিগেশন (পাতা খোলা)
     ------------------------------------------------------------
     ব্রাউজার-ট্যাব : network-first → ক্যাশ → offline   (নতুন লেখা সর্বদা)
     ইনস্টল-অ্যাপ    : cache-first (SWR)               (সাথে সাথে খোলে) */
  if (req.mode === 'navigate') {
    event.respondWith(
      isStandaloneNav().then(function (inApp) {
        return inApp ? appNav(req) : webNav(req, event);
      })
    );
    return;
  }

  /* ডেটা — cache-first, না থাকলে নেট + ক্যাশে রাখি */
  if (isData(url)) {
    event.respondWith(
      caches.match(req).then(function (hit) {
        if (hit) return hit;
        return fetch(req).then(function (res) {
          if (res && res.ok) {
            var copy = res.clone();
            caches.open(DATA_CACHE).then(function (c) {
              c.put(req, copy).then(function () { trimCache(DATA_CACHE); });
            });
          }
          return res;
        });
      })
    );
    return;
  }

  /* স্টাইল/স্ক্রিপ্ট/ফন্ট/ছবি — cache-first, নেট-ফলব্যাক */
  if (isShellAsset(url)) {
    event.respondWith(
      caches.match(req).then(function (hit) {
        return (
          hit ||
          fetch(req).then(function (res) {
            if (res && res.ok) {
              var copy = res.clone();
              caches.open(SHELL_CACHE).then(function (c) {
                c.put(req, copy).then(function () { trimCache(SHELL_CACHE); });
              });
            }
            return res;
          }).catch(function () {
            return new Response('', { status: 504, statusText: 'offline' });
          })
        );
      })
    );
    return;
  }

  /* বাকি সব — সাধারণ নেটওয়ার্ক */
});

/* ============================================================
   appNav — ইনস্টল করা অ্যাপে পাতা খোলা
   ------------------------------------------------------------
   ক্যাশে থাকলে সাথে সাথে দেখাই, আর নীরবে নেটওয়ার্ক থেকে নতুন কপি
   নামিয়ে রাখি (stale-while-revalidate)। ফলে অ্যাপ খোলা তাৎক্ষণিক,
   অথচ পরের খোলায় নতুন লেখা — দুইয়ের সুবিধাই।
   ============================================================ */
function appNav(req) {
  return caches.match(req).then(function (hit) {
    var fresh = fetch(req).then(function (res) {
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(PAGE_CACHE).then(function (c) {
          c.put(req, copy).then(function () { trimCache(PAGE_CACHE); });
        });
      }
      return res;
    }).catch(function () { return null; });

    if (hit) {
      fresh.catch(function () {});      /* নীরবে আপডেট, UI আটকাবে না */
      return hit;
    }
    return fresh.then(function (res) {
      /* নিরাপদ fallback: caches.match() Promise ফেরায় — সত্য-মিথ্যা নয়।
         আগে `res || caches.match(...)` লিখা ছিল, যা সবসময় Promise-ই
         দিত, ফলে অফলাইন-পাতা কখনো আসত না। */
      if (res) return res;
      return caches.match('/ead/offline.html')
        .then(function (o) { return o || caches.match('/ead/index.html'); });
    });
  });
}

/* ============================================================
   webNav — ব্রাউজার-ট্যাবে পাতা খোলা (আগের আচরণ)
   ============================================================ */
function webNav(req, event) {
  return (event.preloadResponse || Promise.resolve(null))
    .then(function (pre) { return pre || fetch(req); })
    .then(function (res) {
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(PAGE_CACHE).then(function (c) {
          c.put(req, copy).then(function () { trimCache(PAGE_CACHE); });
        });
      }
      return res;
    })
    .catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) return hit;
        return caches.match('/ead/offline.html')
          .then(function (o) { return o || caches.match('/ead/index.html'); });
      });
    });
}

/* ============================================================
   trimCache — ক্যাশকে বাজেটের ভিতরে রাখি
   ------------------------------------------------------------
   দুই শর্ত: এন্ট্রি-সংখ্যা আর মোট বাইট। যেটা ছাড়ায়, সেই অনুযায়ী
   সবচেয়ে পুরোনো (আগে যোগ হওয়া) এন্ট্রি বাদ যায়।
   ============================================================ */
/* একটার পরে একটা — একসাথে কয়েকটা fetch এলে বারবার স্ক্যান নয় */
var trimChain = {};

function trimCache(name) {
  var budget = LIMITS[name];
  if (!budget) return Promise.resolve();
  var maxEntries = budget[0];
  var maxBytes = budget[1];

  /* আগের স্ক্যান শেষ হলে তবেই এই স্ক্যান */
  trimChain[name] = (trimChain[name] || Promise.resolve()).then(function () {
    return caches.open(name).then(function (cache) {
      return cache.keys().then(function (keys) {
        if (!keys.length) return;
        return Promise.all(
          keys.map(function (k) {
            return cache.match(k).then(function (res) {
              if (!res) return { key: k, bytes: 0 };
              return sizeOf(res).then(function (b) { return { key: k, bytes: b }; });
            });
          })
        ).then(function (entries) {
          /* পুরোনো আগে বাদ — যতক্ষণ হয় সংখ্যা, নয় মাপ ছাড়িয়ে থাকে */
          var total = 0;
          for (var i = 0; i < entries.length; i++) total += entries[i].bytes;

          var count = entries.length;
          var drop = [];
          for (var j = 0; j < entries.length; j++) {
            if (count <= maxEntries && total <= maxBytes) break;
            drop.push(entries[j].key);
            total -= entries[j].bytes;
            count--;
          }
          if (!drop.length) return;
          return Promise.all(drop.map(function (k) { return cache.delete(k); }));
        });
      });
    });
  }).catch(function () {
    /* ক্যাশ API ব্যর্থ হলেও সাইট চলবে — কখনো নেটওয়ার্ক-পথ আটকাবে না */
  });

  return trimChain[name];
}

/* Content-Length থাকলে সেটাই; না থাকলে blob করে সত্যিকারের আকার */
function sizeOf(res) {
  var h = res.headers.get('Content-Length');
  if (h) {
    var n = parseInt(h, 10);
    if (!isNaN(n)) return Promise.resolve(n);
  }
  return res.clone().blob().then(function (b) { return b.size; })
    .catch(function () { return 0; });
}

/* ============================================================
   message — পেজ থেকে আদেশ (ইনস্টল-বাটন/আপডেট)
   ============================================================ */
self.addEventListener('message', function (event) {
  var data = event.data || {};
  if (data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (data.type === 'CLEAR_DATA') {
    caches.delete(DATA_CACHE).then(function () {
      if (event.source) event.source.postMessage({ type: 'DATA_CLEARED' });
    });
  }
});
