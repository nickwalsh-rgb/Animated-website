/* Archive 88: shared motion and small page behaviours (every page). Needs store.js.
   - Sections marked .reveal arrive once as they enter the screen (IntersectionObserver, never a scroll listener).
   - A product picture carries over from a card to its product page (cross-document view transition, where supported).
   - The theme switch in the footer: Auto (follows the device), Light, Dark. Remembered on this device.
   With reduced motion nothing moves; with no JavaScript everything is simply visible. */
(() => {
  "use strict";
  const { $, $$, reduced } = window.A88S;
  const root = document.documentElement;

  /* ---------- Reveal on scroll ---------- */
  const items = $$(".reveal");
  if (!reduced.matches && items.length && "IntersectionObserver" in window) {
    root.classList.add("has-motion");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        // Neighbours entering together arrive one after another.
        const siblings = [...en.target.parentElement.children].filter((n) => n.classList.contains("reveal"));
        en.target.style.transitionDelay = `${Math.min(siblings.indexOf(en.target), 5) * 70}ms`;
        en.target.classList.add("is-in");
        en.target.addEventListener("transitionend", () => { en.target.style.transitionDelay = ""; }, { once: true });
        io.unobserve(en.target);
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    items.forEach((el) => io.observe(el));
  }

  /* ---------- Card picture to product page ---------- */
  if (!reduced.matches && "CSSViewTransitionRule" in window) {
    document.addEventListener("click", (ev) => {
      const card = ev.target.closest && ev.target.closest(".card");
      if (!card || !ev.target.closest("a")) return;
      $$(".card .media").forEach((m) => (m.style.viewTransitionName = ""));
      const media = $(".media", card);
      if (media) media.style.viewTransitionName = "product-media";
    });
    const target = $("[data-vt-target] .gallery__set:not([hidden]) .media");
    if (target) {
      target.style.viewTransitionName = "product-media";
      // Only the arrival uses the shared name; afterwards the gallery behaves normally.
      addEventListener("pageshow", () => setTimeout(() => (target.style.viewTransitionName = ""), 900), { once: true });
    }
  }

  /* ---------- Theme switch ---------- */
  const btn = $("[data-theme-switch]");
  if (btn) {
    const label = $("[data-theme-label]", btn);
    const order = ["auto", "light", "dark"];
    const names = { auto: "Auto", light: "Light", dark: "Dark" };
    let mode = "auto";
    try { const saved = localStorage.getItem("a88-theme"); if (saved === "light" || saved === "dark") mode = saved; } catch (e) { /* private mode */ }
    const apply = () => {
      if (mode === "auto") delete root.dataset.theme; else root.dataset.theme = mode;
      label.textContent = names[mode];
      btn.setAttribute("aria-label", `Colour theme: ${names[mode]}. Change theme`);
    };
    btn.hidden = false;
    btn.addEventListener("click", () => {
      mode = order[(order.indexOf(mode) + 1) % order.length];
      try { localStorage.setItem("a88-theme", mode); } catch (e) { /* ignore */ }
      apply();
    });
    apply();
  }
})();
