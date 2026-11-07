/* Archive 88: Shop the look (hotspots on editorial photos). Needs site.js first.
   Mouse: hover a number to preview, click to pin. Touch: tap to open, tap again or outside to close.
   Keyboard: Enter opens, Tab moves into the card, Esc closes. The piece list mirrors the markers. */
(() => {
  const { $, $$, motion, T } = window.A88;
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const gs = window.gsap && motion;
  let current = null; // { fig, spot, pop, pinned }
  let closeTimer = null;

  const popFor = (spot) => document.getElementById(spot.getAttribute("aria-controls"));
  const pieceFor = (fig, n) => fig.closest(".look").querySelector(`.look__piece[data-spot="${n}"]`);

  function place(fig, spot, pop) {
    const fr = fig.getBoundingClientRect();
    const sr = spot.getBoundingClientRect();
    const x = sr.left + sr.width / 2 - fr.left;
    const y = sr.top + sr.height / 2 - fr.top;
    if (window.innerWidth <= 720) {
      // Phones: dock across the photo, on the opposite half from the marker so it stays visible.
      pop.classList.add("is-docked");
      pop.classList.toggle("is-top", y > fr.height / 2);
      pop.style.cssText = "";
      return;
    }
    pop.classList.remove("is-docked", "is-top");
    const pw = pop.offsetWidth, ph = pop.offsetHeight, gap = 26, pad = 12;
    const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
    let left, top, origin;
    if (x + gap + pw <= fr.width - pad) {            // room on the right of the marker
      left = x + gap; top = clamp(y - ph / 2, pad, fr.height - ph - pad); origin = `left ${Math.round(y - top)}px`;
    } else if (x - gap - pw >= pad) {                // room on the left
      left = x - gap - pw; top = clamp(y - ph / 2, pad, fr.height - ph - pad); origin = `right ${Math.round(y - top)}px`;
    } else {                                         // narrow photo: above or below, never over the marker
      left = clamp(x - pw / 2, pad, fr.width - pw - pad);
      const below = y < fr.height / 2;
      top = below ? y + gap : y - gap - ph;
      origin = `${Math.round(x - left)}px ${below ? "top" : "bottom"}`;
    }
    pop.style.left = `${left}px`;
    pop.style.top = `${top}px`;
    pop.style.transformOrigin = origin;
  }

  function open(fig, spot, { pinned = false } = {}) {
    clearTimeout(closeTimer);
    if (current && current.spot === spot) { current.pinned = current.pinned || pinned; return; }
    if (current) close(true);
    const pop = popFor(spot);
    pop.hidden = false;
    place(fig, spot, pop);
    spot.setAttribute("aria-expanded", "true");
    spot.classList.add("is-active");
    fig.classList.add("has-open");
    const piece = pieceFor(fig, spot.dataset.spot);
    if (piece) piece.classList.add("is-active");
    current = { fig, spot, pop, pinned };
    if (gs) {
      gsap.killTweensOf([pop, ...pop.querySelectorAll(".pop__body > *")]);
      gsap.fromTo(pop, { opacity: 0, scale: 0.9, y: 8 }, { opacity: 1, scale: 1, y: 0, duration: T.base, ease: "expo.out" });
      gsap.fromTo(pop.querySelectorAll(".pop__body > *"), { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: T.base, ease: "expo.out", stagger: 0.04, delay: 0.05 });
    }
  }

  function close(immediate = false) {
    clearTimeout(closeTimer);
    if (!current) return;
    const { fig, spot, pop } = current;
    current = null;
    spot.setAttribute("aria-expanded", "false");
    spot.classList.remove("is-active");
    fig.classList.remove("has-open");
    const piece = pieceFor(fig, spot.dataset.spot);
    if (piece) piece.classList.remove("is-active");
    if (gs && !immediate) {
      gsap.to(pop, { opacity: 0, scale: 0.95, y: 4, duration: T.fast, ease: "power2.in", onComplete: () => { pop.hidden = true; } });
    } else {
      pop.hidden = true;
    }
  }

  const scheduleClose = () => {
    if (!current || current.pinned) return;
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => close(), 260);
  };

  $$(".js-look").forEach((fig) => {
    const spots = $$(".hotspot", fig);
    spots.forEach((spot) => {
      spot.addEventListener("click", () => {
        if (current && current.spot === spot) {
          // Mouse: first click pins an already-hovered card; the next click closes it.
          if (fine && !current.pinned) current.pinned = true;
          else close();
        } else {
          open(fig, spot, { pinned: true });
        }
      });
      if (fine) {
        spot.addEventListener("pointerenter", () => open(fig, spot));
        spot.addEventListener("pointerleave", scheduleClose);
        const pop = popFor(spot);
        pop.addEventListener("pointerenter", () => clearTimeout(closeTimer));
        pop.addEventListener("pointerleave", scheduleClose);
      }
    });

    // Keyboard: close when focus leaves both the marker and its card.
    fig.addEventListener("focusout", (e) => {
      if (!current || current.fig !== fig) return;
      const to = e.relatedTarget;
      if (to && (to === current.spot || current.pop.contains(to))) return;
      if (to && to.classList && to.classList.contains("hotspot")) return; // moving to another marker
      close();
    });

    // The list beside the photo lights up the matching marker, and the other way round.
    const look = fig.closest(".look");
    $$(".look__piece", look).forEach((piece) => {
      const spot = $(`.hotspot[data-spot="${piece.dataset.spot}"]`, fig);
      const on = () => spot && spot.classList.add("is-linked");
      const off = () => spot && spot.classList.remove("is-linked");
      piece.addEventListener("pointerenter", on);
      piece.addEventListener("pointerleave", off);
      piece.addEventListener("focusin", on);
      piece.addEventListener("focusout", off);
    });
    spots.forEach((spot) => {
      const piece = pieceFor(fig, spot.dataset.spot);
      spot.addEventListener("pointerenter", () => piece && piece.classList.add("is-linked"));
      spot.addEventListener("pointerleave", () => piece && piece.classList.remove("is-linked"));
    });

    // Markers pop in one by one when the look scrolls into view.
    if (gs && window.ScrollTrigger) {
      // fromTo with explicit end values: on the homepage the intro refreshes ScrollTrigger
      // mid-setup, and a plain from() could then record "invisible" as its end state.
      gsap.fromTo(spots, { scale: 0, opacity: 0 }, {
        scale: 1, opacity: 1, duration: T.slow, ease: "back.out(2.2)", stagger: 0.12, clearProps: "transform,opacity",
        scrollTrigger: { trigger: fig, start: "top 70%", once: true },
      });
      gsap.fromTo($$(".look__piece", look), { opacity: 0, x: 20 }, {
        opacity: 1, x: 0, duration: T.slow, ease: "expo.out", stagger: 0.07, clearProps: "transform,opacity",
        scrollTrigger: { trigger: look, start: "top 70%", once: true },
      });
    }
  });

  // Click or tap anywhere else closes the card.
  document.addEventListener("pointerdown", (e) => {
    if (!current) return;
    if (current.spot.contains(e.target) || current.pop.contains(e.target)) return;
    close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && current) {
      const spot = current.spot;
      close();
      spot.focus();
    }
  });
  window.addEventListener("resize", () => current && place(current.fig, current.spot, current.pop));
})();
