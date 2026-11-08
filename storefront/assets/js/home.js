/* Archive 88 storefront: homepage motion only (the shop and product pages stay still and fast).
   Ported from the main site's home.js: smooth scroll (Lenis), the intro loader (first visit per session), hero letters
   that rise in and drift apart on scroll, the pinned sideways track of swinging hang tags, and the marquee.
   Needs gsap, ScrollTrigger and Lenis (vendored in /assets/vendor) and store.js. With reduced motion, or if the
   libraries fail to load, the page is complete and static: the New in track simply scrolls sideways. */
(() => {
  "use strict";
  const { $, $$, Drawer } = window.A88S;
  const html = document.documentElement;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const loader = $(".loader");

  /* ---------- Hero film: autoplays muted (not with reduced motion), pauses off screen, has a pause button ---------- */
  const video = $(".hero__video");
  const toggle = $("[data-film-toggle]");
  if (video && toggle) {
    let userPaused = reduced;
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

  if (reduced || !window.gsap || !window.ScrollTrigger) { loader?.remove(); return; }

  gsap.registerPlugin(ScrollTrigger);
  html.classList.add("has-motion");
  const T = { fast: 0.3, base: 0.5, slow: 0.8, slower: 1.2, slowest: 1.6 }; // the main site's A88.T

  /* ---------- Smooth scroll, paused while any drawer is open ---------- */
  let lenis = null;
  if (window.Lenis) {
    lenis = new Lenis({ duration: T.slowest, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    document.addEventListener("drawer:open", () => lenis.stop());
    document.addEventListener("drawer:close", () => { if (!Drawer.top()) lenis.start(); });
  }

  /* ---------- Intro: loader on the first visit of a session, short rise after that ---------- */
  const firstVisit = loader && !html.classList.contains("seen-intro");
  try { sessionStorage.setItem("a88-store-intro", "1"); } catch { /* private mode: always show it */ }
  const heroLetters = $$(".wordmark--hero .wm-l");
  const fades = $$(".js-hero-fade");
  const counter = { v: 0 };
  const total = Number(($(".loader__count") || {}).textContent?.split("/")[1]) || 100;

  lenis?.stop();
  document.body.classList.add("is-intro");
  gsap.set(heroLetters, { y: 76 });
  gsap.set(fades, { autoAlpha: 0, y: 16 });
  gsap.set(".nav", { autoAlpha: 0, y: -12 });

  const intro = gsap.timeline({ defaults: { ease: "expo.out" }, onComplete: afterIntro });
  if (firstVisit) {
    const letters = $$(".wordmark--loader .wm-l");
    gsap.set(letters, { y: 76 });
    intro
      .to(letters, { y: 0, duration: T.slower, stagger: 0.06 }, 0.15)
      .to(counter, {
        v: total, duration: T.slowest, ease: "power2.inOut",
        onUpdate: () => ($(".js-count").textContent = String(Math.round(counter.v)).padStart(2, "0")),
      }, 0.15)
      .to(letters, { y: -76, duration: T.slow, ease: "power3.in", stagger: 0.03 }, "+=0.15")
      .to(loader, { yPercent: -100, duration: T.slower, ease: "expo.inOut" }, "-=0.25")
      .to(heroLetters, { y: 0, duration: T.slowest, stagger: 0.055 }, "-=0.45");
  } else {
    loader?.remove();
    intro.to(heroLetters, { y: 0, duration: T.slower, stagger: 0.045 }, 0.05);
  }
  intro
    .to(fades, { autoAlpha: 1, y: 0, duration: T.slower, stagger: 0.08 }, "-=0.9")
    .to(".nav", { autoAlpha: 1, y: 0, duration: T.slow, clearProps: "transform,opacity,visibility" }, "<");
  // A shopper who clicks before the intro ends shouldn't wait for it.
  addEventListener("pointerdown", () => intro.progress() < 1 && intro.progress(1), { once: true });
  addEventListener("keydown", () => intro.progress() < 1 && intro.progress(1), { once: true });

  function afterIntro() {
    loader?.remove();
    document.body.classList.remove("is-intro");
    lenis?.start();
    heroScroll();
    ScrollTrigger.refresh();
  }

  /* Hero: letters drift apart at different speeds as you scroll away */
  function heroScroll() {
    $(".wordmark--hero").style.overflow = "visible";
    const drift = [-26, 18, -12, 30, -34, 10, -20, 24, -8];
    const st = { trigger: ".hero", start: "top top", end: "bottom top", scrub: true };
    gsap.to(heroLetters, { y: (i) => drift[i] * 3, ease: "none", scrollTrigger: st });
    gsap.to(".hero__mark", { scale: 0.92, autoAlpha: 0.2, ease: "none", scrollTrigger: { ...st } });
    gsap.to(".hero__foot", { y: -60, autoAlpha: 0, ease: "none", scrollTrigger: { trigger: ".hero", start: "20% top", end: "70% top", scrub: true } });
  }

  /* ---------- New in: pinned sideways track of swinging hang tags ---------- */
  const track = $(".archive__track");
  if (track) {
    const tags = $$(".tag", track);
    const progress = $(".js-progress");
    const swing = tags.map((t) => gsap.quickTo(t, "rotation", { duration: T.slow, ease: "elastic.out(1, 0.35)" }));
    const distance = () => Math.max(0, track.scrollWidth - document.documentElement.clientWidth);

    gsap.from(tags, {
      y: 80, opacity: 0, rotation: (i) => (i % 2 ? 6 : -6), duration: T.slowest, ease: "expo.out", stagger: 0.08,
      scrollTrigger: { trigger: ".archive", start: "top 65%" },
    });
    gsap.to(track, {
      x: () => -distance(),
      ease: "none",
      scrollTrigger: {
        trigger: ".archive",
        pin: ".archive__pin",
        start: "top top",
        end: () => "+=" + distance(),
        scrub: 0.8,
        invalidateOnRefresh: true,
        onUpdate: (self) => {
          gsap.set(progress, { scaleX: self.progress });
          const v = gsap.utils.clamp(-9, 9, self.getVelocity() / -260);
          swing.forEach((fn) => fn(v));
          clearTimeout(track._rest);
          track._rest = setTimeout(() => swing.forEach((fn) => fn(0)), 120);
        },
      },
    });
    // Keyboard users tabbing through the track: scroll the page so the focused tag is in view.
    track.addEventListener("focusin", (ev) => {
      const tag = ev.target.closest(".tag");
      const st = ScrollTrigger.getAll().find((s) => s.pin === $(".archive__pin"));
      if (!tag || !st) return;
      const i = tags.indexOf(tag);
      const y = st.start + (st.end - st.start) * (i / Math.max(1, tags.length - 1));
      lenis ? lenis.scrollTo(y, { immediate: true }) : scrollTo(0, y);
    });
  }

  /* ---------- Category tiles rise in ---------- */
  gsap.from(".tiles__grid > li", {
    y: 60, autoAlpha: 0, duration: T.slower, ease: "expo.out", stagger: 0.07,
    scrollTrigger: { trigger: ".tiles__grid", start: "top 80%" },
  });

  /* ---------- Marquee: steady drift, speeds up and flips with scroll ---------- */
  const marquee = gsap.to(".marquee__track", { xPercent: -50, duration: 28, ease: "none", repeat: -1 });
  let dir = 1;
  ScrollTrigger.create({
    trigger: ".marquee", start: "top bottom", end: "bottom top",
    onUpdate: (self) => {
      const v = self.getVelocity();
      if (Math.abs(v) > 50) dir = v > 0 ? 1 : -1;
      gsap.to(marquee, { timeScale: dir * (1 + Math.min(Math.abs(v) / 400, 5)), duration: T.fast, overwrite: true });
      gsap.to(marquee, { timeScale: dir, duration: T.slower, delay: 0.25 });
    },
  });
})();
