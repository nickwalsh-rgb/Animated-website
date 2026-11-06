/* Archive 88 — motion
   GSAP + ScrollTrigger for choreography, Lenis for smooth scroll. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const body = document.body;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  $(".js-year").textContent = new Date().getFullYear();

  setupForm();

  if (reduced || !window.gsap) {
    body.classList.remove("is-loading");
    const loader = $(".loader");
    if (loader) loader.remove();
    setupNavTheme(null);
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Smooth scroll ---------- */
  const lenis = new Lenis({ duration: 1.15, smoothWheel: true });
  lenis.stop();
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);

  $$('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      const target = id === "#top" ? 0 : $(id);
      if (target === null) return;
      e.preventDefault();
      lenis.scrollTo(target, { duration: 1.6 });
    });
  });

  /* ---------- Text splitting helpers ---------- */
  function splitWords(el) {
    const words = el.textContent.trim().split(/\s+/);
    el.innerHTML = words.map((w) => `<span class="w">${w}</span>`).join(" ");
    return $$(".w", el);
  }
  function splitLines(el) {
    const lines = el.innerHTML.split(/<br\s*\/?>/i);
    el.innerHTML = lines.map((l) => `<span class="line"><span>${l.trim()}</span></span>`).join("");
    return $$(".line > span", el);
  }

  /* ---------- Intro: loader → hero ---------- */
  const loaderLetters = $$(".wordmark--loader .wm-l");
  const heroLetters = $$(".wordmark--hero .wm-l");
  const heroFades = $$(".js-hero-fade");
  const counter = { v: 0 };

  gsap.set(loaderLetters, { y: 76 });
  gsap.set(heroLetters, { y: 76 });
  gsap.set(heroFades, { autoAlpha: 0, y: 16 });
  gsap.set(".nav", { autoAlpha: 0, y: -12 });

  const intro = gsap.timeline({ defaults: { ease: "expo.out" } });
  intro
    .to(loaderLetters, { y: 0, duration: 1.1, stagger: 0.06 }, 0.15)
    .to(counter, {
      v: 88, duration: 1.6, ease: "power2.inOut",
      onUpdate: () => ($(".js-count").textContent = String(Math.round(counter.v)).padStart(2, "0")),
    }, 0.15)
    .to(loaderLetters, { y: -76, duration: 0.7, ease: "power3.in", stagger: 0.03 }, "+=0.15")
    .to(".loader", { yPercent: -100, duration: 1.0, ease: "expo.inOut" }, "-=0.25")
    .to(heroLetters, { y: 0, duration: 1.3, stagger: 0.055 }, "-=0.45")
    .to(heroFades, { autoAlpha: 1, y: 0, duration: 1, stagger: 0.08 }, "-=1")
    .to(".nav", { autoAlpha: 1, y: 0, duration: 0.9 }, "<")
    .add(() => {
      $(".loader").remove();
      body.classList.remove("is-loading");
      lenis.start();
      heroScroll();
      ScrollTrigger.refresh();
    });

  /* Hero: letters drift apart at different speeds as you scroll away */
  function heroScroll() {
    $(".wordmark--hero").style.overflow = "visible";
    const drift = [-26, 18, -12, 30, -34, 10, -20, 24, -8];
    gsap.to(heroLetters, {
      y: (i) => drift[i] * 3,
      ease: "none",
      scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
    });
    gsap.to(".hero__mark", {
      scale: 0.92, autoAlpha: 0.2, ease: "none",
      scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
    });
    gsap.to(".hero__bottom, .hero__top", {
      y: -60, autoAlpha: 0, ease: "none",
      scrollTrigger: { trigger: ".hero", start: "20% top", end: "70% top", scrub: true },
    });
  }

  /* ---------- Nav: theme per section + hide on scroll down ---------- */
  setupNavTheme(lenis);

  /* ---------- Manifesto: words light up as you read ---------- */
  const words = splitWords($(".js-words"));
  gsap.to(words, {
    opacity: 1, ease: "none", stagger: 0.1,
    scrollTrigger: { trigger: ".manifesto__text", start: "top 78%", end: "bottom 45%", scrub: true },
  });

  /* ---------- Display headings: line-by-line rise ---------- */
  $$(".js-lines").forEach((el) => {
    const lines = splitLines(el);
    gsap.from(lines, {
      yPercent: 110, duration: 1.1, ease: "expo.out", stagger: 0.09,
      scrollTrigger: { trigger: el, start: "top 82%" },
    });
  });

  /* ---------- Generic reveals ---------- */
  gsap.set(".js-reveal", { autoAlpha: 0, y: 30 });
  ScrollTrigger.batch(".js-reveal", {
    start: "top 88%",
    once: true,
    onEnter: (batch) => gsap.to(batch, { autoAlpha: 1, y: 0, duration: 1, ease: "expo.out", stagger: 0.1 }),
  });

  /* ---------- Archive: pinned horizontal track of swinging hang tags ---------- */
  const track = $(".archive__track");
  const tags = $$(".tag", track);
  const progressEl = $(".js-progress");
  const swing = tags.map((t) => gsap.quickTo(t, "rotation", { duration: 0.9, ease: "elastic.out(1, 0.35)" }));
  const distance = () => Math.max(0, track.scrollWidth - window.innerWidth);

  gsap.from(tags, {
    y: 80, autoAlpha: 0, rotation: (i) => (i % 2 ? 6 : -6), duration: 1.2, ease: "expo.out", stagger: 0.08,
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
        const idx = Math.min(tags.length, Math.floor(self.progress * tags.length) + 1);
        progressEl.textContent = String(idx).padStart(2, "0");
        const v = gsap.utils.clamp(-9, 9, self.getVelocity() / -260);
        swing.forEach((fn) => fn(v));
        clearTimeout(track._rest);
        track._rest = setTimeout(() => swing.forEach((fn) => fn(0)), 120);
      },
    },
  });

  /* ---------- Label: woven label tilts toward the pointer ---------- */
  const woven = $(".js-tilt");
  const stage = $(".label__stage");
  gsap.from(woven, {
    rotationX: 70, y: 80, autoAlpha: 0, duration: 1.4, ease: "expo.out",
    scrollTrigger: { trigger: stage, start: "top 75%" },
  });
  gsap.fromTo(".js-mono", { scale: 0.7, rotation: -8 }, {
    scale: 1.1, rotation: 4, ease: "none",
    scrollTrigger: { trigger: ".label", start: "top bottom", end: "bottom top", scrub: true },
  });
  if (window.matchMedia("(hover: hover)").matches) {
    const rx = gsap.quickTo(woven, "rotationX", { duration: 0.8, ease: "power3.out" });
    const ry = gsap.quickTo(woven, "rotationY", { duration: 0.8, ease: "power3.out" });
    stage.addEventListener("pointermove", (e) => {
      const r = stage.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      ry(px * 28);
      rx(py * -22);
    });
    stage.addEventListener("pointerleave", () => { rx(0); ry(0); });
  }

  /* ---------- Marquee: steady drift, speeds up and flips with scroll ---------- */
  const marquee = gsap.to(".marquee__track", { xPercent: -50, duration: 28, ease: "none", repeat: -1 });
  let dir = 1;
  ScrollTrigger.create({
    trigger: ".marquee",
    start: "top bottom",
    end: "bottom top",
    onUpdate: (self) => {
      const v = self.getVelocity();
      if (Math.abs(v) > 50) dir = v > 0 ? 1 : -1;
      gsap.to(marquee, { timeScale: dir * (1 + Math.min(Math.abs(v) / 400, 5)), duration: 0.2, overwrite: true });
      gsap.to(marquee, { timeScale: dir, duration: 1, delay: 0.25 });
    },
  });

  /* ---------- Footer: wordmark rises letter by letter ---------- */
  const footLetters = $$(".wordmark--footer .wm-l");
  gsap.from(footLetters, {
    y: 76, duration: 1.3, ease: "expo.out", stagger: 0.06,
    scrollTrigger: { trigger: ".wordmark--footer", start: "top 92%" },
  });

  window.addEventListener("load", () => ScrollTrigger.refresh());
  if (document.fonts) document.fonts.ready.then(() => ScrollTrigger.refresh());

  /* ---------- helpers ---------- */
  function setupNavTheme(lenisInstance) {
    const sections = $$("[data-theme]");
    const probe = () => {
      const y = 36; // roughly the nav's vertical centre
      for (const s of sections) {
        const r = s.getBoundingClientRect();
        if (r.top <= y && r.bottom > y) { body.dataset.nav = s.dataset.theme; break; }
      }
    };
    const nav = $(".nav");
    let last = 0;
    const onScroll = () => {
      probe();
      const yNow = window.scrollY;
      nav.classList.toggle("is-hidden", yNow > last && yNow > window.innerHeight * 0.6);
      nav.classList.toggle("is-solid", yNow > window.innerHeight * 0.5);
      last = yNow;
    };
    if (lenisInstance) lenisInstance.on("scroll", onScroll);
    else window.addEventListener("scroll", onScroll, { passive: true });
    probe();
  }
})();

function setupForm() {
  const form = document.querySelector(".join__form");
  const note = document.querySelector(".js-note");
  const section = document.querySelector(".join");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const input = form.querySelector("input");
    const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value.trim());
    section.classList.toggle("is-error", !ok);
    if (!ok) { note.textContent = "That email doesn't look right — try again."; input.focus(); return; }
    // TODO: send input.value to your mailing-list provider here.
    note.textContent = "You're on the list. We'll be in touch before the next drop.";
    form.reset();
  });
}
