// OrbitX background video: seamless loop by crossfading two copies of the same clip.
// Runs once per page (guarded), never touches Streamlit's own elements, and fails quietly:
// if anything is missing the first video keeps using the browser's native loop.
(function () {
  var a = document.getElementById("orbitx-bg-a");
  var b = document.getElementById("orbitx-bg-b");
  if (!a || !b || a.dataset.orbitxBound) return;
  a.dataset.orbitxBound = "1";

  var FADE = 1.6; // seconds of overlap; keep in sync with the CSS opacity transition
  var current = a, next = b, fading = false;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function fail(video) {
    video.classList.remove("is-on");
    video.style.display = "none"; // the CSS gradient behind it remains
  }
  a.addEventListener("error", function () { fail(a); fail(b); });

  if (reduceMotion) { a.removeAttribute("autoplay"); a.pause(); return; }

  a.loop = false; // JavaScript is running, so we handle the loop ourselves
  a.play().catch(function () {}); // autoplay can be refused; the page works without video

  function swap() {
    fading = true;
    var old = current;
    next.currentTime = 0;
    var started = next.play();
    if (started && started.catch) started.catch(function () {});
    next.classList.add("is-on");
    old.classList.remove("is-on");
    current = next;
    next = old;
    setTimeout(function () { old.pause(); fading = false; }, FADE * 1000 + 150);
  }

  setInterval(function () {
    if (document.hidden || fading || current.paused) return;
    var d = current.duration;
    if (d && isFinite(d) && current.currentTime >= d - FADE) swap();
    else if (current.ended) swap();
  }, 100);

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { a.pause(); b.pause(); }
    else { current.play().catch(function () {}); }
  });
})();
