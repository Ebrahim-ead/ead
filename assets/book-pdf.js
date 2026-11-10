/* book-pdf.js — বইয়ের PDF সবার ডিভাইসে খোলার নিশ্চয়তা।
 *
 * ⚠ যে সমস্যাটা এটি সারায় (২০২৬-১১-১০, ব্যবহারকারীর রিপোর্ট):
 *   «ফোন ব্যবহার করে ওয়েবসাইটে বইয়ের PDF গুলো দেখা যায় না।»
 *
 * কারণ: পাতায় PDF <iframe>-এ এমবেড করা ছিল। ডেস্কটপে তা চলে, কিন্তু
 *   • iOS Safari (iPhone/iPad): iframe-এ PDF-এর শুধু *প্রথম পৃষ্ঠা* দেখায়,
 *     বাকিটা দেখতে হলে আলাদা করে খুলতে হয়;
 *   • Android Chrome: বহু সংস্করণে iframe-ভেতরে PDF রেন্ডারই হয় না —
 *     ফাঁকা সাদা জায়গা থাকে (নিম্ন-শক্তির ডিভাইসে বিশেষত);
 *   • Samsung Internet / Firefox mobile: প্রায়ই ডাউনলোডে পাঠিয়ে দেয়।
 *   অর্থাৎ ওই «অনলাইনে পড়ুন» বোতাম ফোনে চাপলে কিছুই দেখা যেত না।
 *
 * সমাধান: ব্লকটি কেবল *সত্যিই* PDF দেখাতে পারে এমন পরিবেশে খুলি
 *   (navigator.pdfViewerEnabled + ডেস্কটপ-প্রস্থ)। নইলে PDF নতুন ট্যাবে
 *   খোলার বড় বোতাম + ডাউনলোড দেখাই — ফোনের নিজের PDF রিডারেই তা চলবে,
 *   যা সব iOS/Android-এ কাজ করে। কোনো ফিচার হারায় না, বরং পথ পরিষ্কার।
 *
 * নীতি: ইনলাইন-হ্যান্ডলার/অতিরিক্ত নির্ভরতা নেই; প্রতিটি বই-ব্লক আলাদা
 *   `[data-book-viewer]` ধারক দিয়ে চিহ্নিত, সাথে `[data-book-fallback]` প্যানেল।
 */
(function () {
  'use strict';

  /** এই ব্রাউজার কি iframe-এর ভেতরে PDF রেন্ডার করতে পারে? */
  function canInlinePdf() {
    // ১) সরাসরি জিজ্ঞাসা — Chrome/Edge/Safari আধুনিক সংস্করণে আছে
    if (typeof navigator !== 'undefined' && 'pdfViewerEnabled' in navigator) {
      if (!navigator.pdfViewerEnabled) return false;
    }
    // ২) মোবাইল/টাচ — ওখানে ইনলাইন রেন্ডার অবিশ্বাস্য, তাই ফলব্যাকই ভালো
    var ua = (navigator && navigator.userAgent) || '';
    if (/iPhone|iPad|iPod|Android|Mobile|SamsungBrowser|Opera Mini/i.test(ua)) return false;
    // ৩) ছোট স্ক্রিন (ফোন) — PDF-পৃষ্ঠা পড়াই কষ্টকর
    if (typeof window.matchMedia === 'function' &&
        window.matchMedia('(max-width: 760px)').matches) return false;
    // ৪) টাচ-প্রধান ডিভাইস
    if (typeof navigator !== 'undefined' && navigator.maxTouchPoints > 1 &&
        typeof window.matchMedia === 'function' &&
        !window.matchMedia('(pointer: fine)').matches) return false;
    return true;
  }

  var INLINE_OK = canInlinePdf();

  /** একটি বই-ব্লকে সিদ্ধান্ত প্রয়োগ করি। */
  function setup(box) {
    var frame = box.querySelector('iframe');
    // ফলব্যাক-প্যানেল ভিউয়ারের ভেতরে বা ঠিক পরে — দুই জায়গাতেই খুঁজি
    var fallback = box.querySelector('[data-book-fallback]') ||
                   (box.nextElementSibling && box.nextElementSibling.matches('[data-book-fallback]')
                     ? box.nextElementSibling : null) ||
                   document.querySelector('[data-book-fallback]');
    var openLink = (fallback && fallback.querySelector('[data-book-open]')) ||
                   document.querySelector('[data-book-open]');
    var url = box.getAttribute('data-book-src') || (openLink && openLink.getAttribute('href')) || '';

    if (!frame || !fallback || !url) return;

    if (INLINE_OK) {
      // ডেস্কটপ: আগের মতোই ইনলাইন ভিউয়ার
      frame.setAttribute('src', url);
      fallback.hidden = true;
    } else {
      // ফোন: ভিউয়ার লুকিয়ে PDF খোলার স্পষ্ট পথ দেখাই
      frame.removeAttribute('src');      // অকারণে ৯–১৪ MB নামবে না
      fallback.hidden = false;
      box.classList.add('is-fallback');
      // iOS/Android-এর নিজের রিডারে খুললে সব পৃষ্ঠা ঠিকঠাক চলে
      if (openLink) openLink.setAttribute('href', url);
    }
  }

  function run() {
    var boxes = document.querySelectorAll('[data-book-viewer]');
    for (var i = 0; i < boxes.length; i++) setup(boxes[i]);
  }

  // ⚠ jsdom/পরীক্ষায় readyState কখনো 'complete' নাও হতে পারে — তাই সরাসরিই
  //   চালাই, আর DOMContentLoaded-এ আবার (run() idempotent: দুবার চললে ক্ষতি নেই)।
  run();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  }

  // পরীক্ষার জন্য প্রকাশ (tools/test_pdf.mjs ব্যবহার করে)
  window.__bookPdf = { canInlinePdf: canInlinePdf, inlineOk: INLINE_OK };
})();
