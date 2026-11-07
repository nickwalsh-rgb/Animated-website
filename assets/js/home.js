/* Archive 88: homepage motion (needs site.js first) */
(() => {
  const { $, $$, site, motion, splitLines, splitWords, T } = window.A88;
  const body = document.body;

  // Old links to #shop-<category> now live on the shop page.
  if (window.location.hash.startsWith("#shop-")) {
    window.location.replace(`shop/?cat=${encodeURIComponent(window.location.hash.slice(6))}`);
    return;
  }

  setupRail();

  if (!motion) {
    body.classList.remove("is-loading");
    const loader = $(".loader");
    if (loader) loader.remove();
    $(".field__video").removeAttribute("preload");
    if (window.A88.restoreScroll) window.A88.restoreScroll();
    arriveFromHash();
    return;
  }

  /* ---------- Intro: full loader on the first visit of a session, short rise after that ---------- */
  const firstVisit = !document.documentElement.classList.contains("seen-intro");
  try { sessionStorage.setItem("a88-intro", "1"); } catch (e) { /* private mode: always show it */ }

  const loaderLetters = $$(".wordmark--loader .wm-l");
  const heroLetters = $$(".wordmark--hero .wm-l");
  const heroFades = $$(".js-hero-fade");
  const counter = { v: 0 };

  site.lock();
  gsap.set(heroLetters, { y: 76 });
  gsap.set(heroFades, { autoAlpha: 0, y: 16 });
  gsap.set(".nav", { autoAlpha: 0, y: -12 });

  const intro = gsap.timeline({ defaults: { ease: "expo.out" }, onComplete: afterIntro });
  if (firstVisit && $(".loader")) {
    gsap.set(loaderLetters, { y: 76 });
    intro
      .to(loaderLetters, { y: 0, duration: T.slower, stagger: 0.06 }, 0.15)
      .to(counter, {
        v: 88, duration: T.slowest, ease: "power2.inOut",
        onUpdate: () => ($(".js-count").textContent = String(Math.round(counter.v)).padStart(2, "0")),
      }, 0.15)
      .to(loaderLetters, { y: -76, duration: T.slow, ease: "power3.in", stagger: 0.03 }, "+=0.15")
      .to(".loader", { yPercent: -100, duration: T.slower, ease: "expo.inOut" }, "-=0.25")
      .to(heroLetters, { y: 0, duration: T.slowest, stagger: 0.055 }, "-=0.45");
  } else {
    const loader = $(".loader");
    if (loader) loader.remove();
    intro.to(heroLetters, { y: 0, duration: T.slower, stagger: 0.045 }, 0.05);
  }
  intro
    .to(heroFades, { autoAlpha: 1, y: 0, duration: T.slower, stagger: 0.08 }, "-=0.9")
    .to(".nav", { autoAlpha: 1, y: 0, duration: T.slow }, "<");

  function afterIntro() {
    const loader = $(".loader");
    if (loader) loader.remove();
    body.classList.remove("is-loading");
    site.unlock();
    heroScroll();
    ScrollTrigger.refresh();
    if (window.A88.restoreScroll) window.A88.restoreScroll();
    arriveFromHash();
  }

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
    gsap.to(".hero__bottom", {
      y: -60, autoAlpha: 0, ease: "none",
      scrollTrigger: { trigger: ".hero", start: "20% top", end: "70% top", scrub: true },
    });
  }

  /* ---------- Film: a small window opens into the full-bleed film ---------- */
  const field = $(".field");
  const fieldLines = splitLines($(".field__line"));
  const smallInset = () => (window.innerWidth <= 720 ? "30% 14% 30% 14%" : "26% 33% 26% 33%");
  gsap.set(fieldLines, { yPercent: 110 });

  gsap.timeline({
    defaults: { ease: "none" },
    scrollTrigger: {
      trigger: field,
      pin: ".field__pin",
      start: "top top",
      end: "+=160%",
      scrub: 0.6,
      invalidateOnRefresh: true,
      onUpdate: (self) => (field.dataset.theme = self.progress > 0.45 ? "film" : "bone"),
      onLeaveBack: () => (field.dataset.theme = "bone"),
    },
  })
    .fromTo(".field__frame",
      { clipPath: () => `inset(${smallInset()} round 4px)` },
      { clipPath: "inset(0% 0% 0% 0% round 0px)", duration: T.slower, ease: "power2.inOut" }, 0)
    .fromTo(".field__video", { scale: 1.18 }, { scale: 1, duration: T.slowest }, 0)
    .to(".field__shade", { opacity: 1, duration: T.base }, 0.55)
    .to(fieldLines, { yPercent: 0, duration: T.base, stagger: 0.12, ease: "power3.out" }, 0.8)
    .to({}, { duration: T.fast }); // hold on the full frame before moving on

  const video = $(".field__video");
  new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) video.play().catch(() => {});
    else video.pause();
  }, { threshold: 0.01 }).observe(video);

  /* ---------- Story: words light up as you read ---------- */
  gsap.to(splitWords($(".js-words")), {
    opacity: 1, ease: "none", stagger: 0.1,
    scrollTrigger: { trigger: ".manifesto__text", start: "top 78%", end: "bottom 45%", scrub: true },
  });

  /* ---------- Archive: pinned horizontal track of swinging hang tags ---------- */
  const track = $(".archive__track");
  const tags = $$(".tag", track);
  const progress = $(".js-progress");
  const swing = tags.map((t) => gsap.quickTo(t, "rotation", { duration: T.slow, ease: "elastic.out(1, 0.35)" }));
  const distance = () => Math.max(0, track.scrollWidth - window.innerWidth);

  gsap.from(tags, {
    y: 80, opacity: 0, rotation: (i) => (i % 2 ? 6 : -6), duration: T.slowest, ease: "expo.out", stagger: 0.08,
    scrollTrigger: { trigger: ".archive", start: "top 65%" },
  });

  gsap.to(track, {
    x: () => -distance(),
    ease: "none",
    scrollTrigger: {
      id: "archive",
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

  /* ---------- Label: woven label tilts toward the pointer ---------- */
  const woven = $(".js-tilt");
  const stage = $(".label__stage");
  gsap.from(woven, {
    rotationX: 70, y: 80, autoAlpha: 0, duration: T.slowest, ease: "expo.out",
    scrollTrigger: { trigger: stage, start: "top 75%" },
  });
  gsap.fromTo(".js-mono", { scale: 0.7, rotation: -8 }, {
    scale: 1.1, rotation: 4, ease: "none",
    scrollTrigger: { trigger: ".label", start: "top bottom", end: "bottom top", scrub: true },
  });
  if (window.matchMedia("(hover: hover)").matches) {
    const rx = gsap.quickTo(woven, "rotationX", { duration: T.slow, ease: "power3.out" });
    const ry = gsap.quickTo(woven, "rotationY", { duration: T.slow, ease: "power3.out" });
    stage.addEventListener("pointermove", (e) => {
      const r = stage.getBoundingClientRect();
      ry(((e.clientX - r.left) / r.width - 0.5) * 28);
      rx(((e.clientY - r.top) / r.height - 0.5) * -22);
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
      gsap.to(marquee, { timeScale: dir * (1 + Math.min(Math.abs(v) / 400, 5)), duration: T.fast, overwrite: true });
      gsap.to(marquee, { timeScale: dir, duration: T.slower, delay: 0.25 });
    },
  });

  /* ======================================================================
     helpers
     ====================================================================== */

  /* Chapter rail: shows where you are in the homepage story and jumps to any chapter.
     Built from [data-chapter] sections, so it only lists chapters that exist. Desktop shows the
     list down the right edge; phones get a thin progress line under the top bar instead. */
  function setupRail() {
    const chapters = $$("[data-chapter]");
    if (chapters.length < 2) return;
    const rail = document.createElement("nav");
    rail.className = "rail";
    rail.setAttribute("aria-label", "Page sections");
    rail.innerHTML =
      "<ol>" + chapters.map((s) =>
        `<li><a href="#${s.id}" data-ch="${s.id}"><span class="rail__label">${s.dataset.chapter}</span><span class="rail__tick" aria-hidden="true"></span></a></li>`
      ).join("") + '</ol><span class="rail__bar" aria-hidden="true"><span class="js-rail-bar"></span></span>';
    body.appendChild(rail);
    const links = $$("a", rail);
    const bar = $(".js-rail-bar", rail);

    links.forEach((a) => a.addEventListener("click", (e) => {
      e.preventDefault();
      site.scrollTo(a.getAttribute("href"));
    }));

    // Active chapter: the one crossing the middle of the screen.
    let active = null;
    const setActive = (id) => {
      active = id;
      links.forEach((a) => {
        const on = a.dataset.ch === id;
        a.classList.toggle("is-active", on);
        if (on) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
      });
      vis();
    };
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) setActive(en.target.id); });
    }, { rootMargin: "-48% 0px -50% 0px" });
    chapters.forEach((s) => io.observe(s));

    // Visible from the first chapter until the footer (not over the hero or the film).
    let pastHero = false, atFooter = false;
    function vis() { rail.classList.toggle("is-on", pastHero && !atFooter && !!active); }
    new IntersectionObserver(([en]) => {
      pastHero = !en.isIntersecting;
      if (!pastHero) { active = null; links.forEach((a) => { a.classList.remove("is-active"); a.removeAttribute("aria-current"); }); }
      vis();
    }).observe($(".hero"));
    new IntersectionObserver(([en]) => { atFooter = en.isIntersecting; vis(); }, { rootMargin: "0px 0px -30% 0px" }).observe($(".footer"));
    // The film sits between the hero and the first chapter: no chapter is active there yet.
    new IntersectionObserver(([en]) => {
      if (en.isIntersecting && active === chapters[0].id) { active = null; links.forEach((a) => { a.classList.remove("is-active"); a.removeAttribute("aria-current"); }); vis(); }
    }, { rootMargin: "-48% 0px -50% 0px" }).observe($(".field"));

    // Progress line (phones).
    let ticking = false;
    const progress = () => {
      ticking = false;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
    };
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(progress); } };
    if (site.lenis) site.lenis.on("scroll", onScroll); else window.addEventListener("scroll", onScroll, { passive: true });
    progress();
  }

  /* Arriving from another page with a section anchor such as #returns or #join. */
  function arriveFromHash() {
    const h = window.location.hash;
    let target = null;
    try { target = h && document.querySelector(h); } catch (e) { /* not a valid selector */ }
    if (!target) return;
    setTimeout(() => site.scrollTo(h), motion ? 150 : 0);
  }
})();
