/* Archive 88: homepage.
   The film hero (autoplays muted, pauses off screen, has a pause button) and the archive index preview.
   Section reveals live in motion.js; scroll-linked effects are CSS (store.css, "Motion"). No scroll-jacking or
   loaders. Needs store.js. With reduced motion the film stays on its poster frame. */
(() => {
  "use strict";
  const { $, $$, reduced } = window.A88S;

  /* ---------- Hero film ---------- */
  const video = $(".hero__video");
  const toggle = $("[data-film-toggle]");
  if (video && toggle) {
    let userPaused = reduced.matches;
    const sync = () => {
      const playing = !video.paused;
      toggle.setAttribute("aria-pressed", String(!playing));
      $("[data-film-label]", toggle).textContent = playing ? "Pause film" : "Play film";
      $("use", toggle).setAttribute("href", playing ? "#i-pause" : "#i-play");
    };
    const play = () => video.play().catch(() => {});
    video.addEventListener("play", sync);
    video.addEventListener("pause", sync);
    toggle.hidden = false;
    toggle.addEventListener("click", () => {
      userPaused = !video.paused;
      userPaused ? video.pause() : play();
    });
    new IntersectionObserver(([en]) => {
      if (en.isIntersecting && !userPaused) play(); else video.pause();
    }, { threshold: 0.05 }).observe(video);
    sync();
  }

  /* ---------- Archive index: the frame on the right shows the row under the pointer or focus ---------- */
  const index = $("[data-archive-index]");
  if (index) {
    const frames = $$("[data-index-frame]", index);
    const show = (i) => frames.forEach((f) => f.classList.toggle("is-active", f.dataset.indexFrame === i));
    $$("[data-index-row]", index).forEach((row) => {
      row.addEventListener("pointerenter", () => show(row.dataset.indexRow));
      row.addEventListener("focus", () => show(row.dataset.indexRow));
    });
  }
})();
