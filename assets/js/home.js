/* Archive 88: homepage.
   Deliberately calm: the film hero (autoplays muted, pauses off screen, has a pause button) and a gentle fade-up as
   sections enter the viewport. No scroll-jacking, pinning or loaders. Needs store.js. With reduced motion the film
   stays on its poster frame and every section is simply visible. */
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

  /* ---------- Sections fade up once as they arrive ---------- */
  const items = $$(".reveal");
  if (reduced.matches || !items.length || !("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("has-motion");
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return;
      // Neighbours entering together arrive one after another.
      const siblings = [...en.target.parentElement.children].filter((n) => n.classList.contains("reveal"));
      en.target.style.transitionDelay = `${Math.min(siblings.indexOf(en.target), 5) * 60}ms`;
      en.target.classList.add("is-in");
      io.unobserve(en.target);
    });
  }, { rootMargin: "0px 0px -8% 0px" });
  items.forEach((el) => io.observe(el));
})();
