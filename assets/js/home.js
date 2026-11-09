/* The Easy Life: homepage.
   Deliberately calm: leaf shadows sway on the sunlit wall (CSS only; this file pauses them off screen and wires the
   pause button) and sections fade up once as they arrive. No scroll-jacking, pinning or loaders. Needs store.js.
   With reduced motion the shadows hold still and every section is simply visible. */
(() => {
  "use strict";
  const { $, $$, reduced } = window.A88S;

  /* ---------- Sunlit wall ---------- */
  const walls = $$("[data-wall]");
  const toggle = $("[data-wall-toggle]");
  if (walls.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => en.target.classList.toggle("is-offscreen", !en.isIntersecting));
    });
    walls.forEach((w) => io.observe(w));
  }
  if (walls.length && toggle && !reduced.matches) {
    toggle.hidden = false;
    toggle.addEventListener("click", () => {
      const paused = toggle.getAttribute("aria-pressed") !== "true";
      toggle.setAttribute("aria-pressed", String(paused));
      walls.forEach((w) => w.classList.toggle("is-paused", paused));
      $("[data-wall-label]", toggle).textContent = paused ? "Play the moving shadows" : "Pause the moving shadows";
      $("use", toggle).setAttribute("href", paused ? "#i-play" : "#i-pause");
    });
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
