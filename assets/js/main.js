/* Archive 88 — motion
   GSAP + ScrollTrigger for choreography, Lenis for smooth scroll. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const body = document.body;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  $(".js-year").textContent = new Date().getFullYear();

  setupForm();

  /* Shared helpers used by the menu, bag and returns (work with or without motion). */
  const site = {
    lenis: null,
    locks: 0,
    lock() {
      if (this.locks++ === 0) {
        if (this.lenis) this.lenis.stop();
        document.documentElement.style.overflow = "hidden";
      }
    },
    unlock() {
      if (this.locks > 0 && --this.locks === 0) {
        document.documentElement.style.overflow = "";
        if (this.lenis) this.lenis.start();
      }
    },
    scrollTo(target, offset = 0) {
      if (typeof target === "string") target = target === "#top" ? 0 : $(target);
      if (target === null || target === undefined) return;
      if (this.lenis) this.lenis.scrollTo(target, { duration: 1.6, offset });
      else {
        const y = typeof target === "number" ? target : target.getBoundingClientRect().top + window.scrollY + offset;
        window.scrollTo({ top: y, behavior: reduced ? "auto" : "smooth" });
      }
    },
  };
  const D = reduced || !window.gsap ? 0 : 1; // duration multiplier for overlay motion

  if (window.gsap) {
    setupMenu();
    setupCart();
    setupReturns();
  }

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
  site.lenis = lenis;
  site.locks = 1; // held by the loader until the intro finishes
  lenis.stop();
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);

  $$('a[href^="#"]').forEach((a) => {
    if (a.closest(".menu, .cart")) return; // those close their overlay first
    a.addEventListener("click", (e) => {
      e.preventDefault();
      site.scrollTo(a.getAttribute("href"));
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
      site.locks = 1;
      site.unlock();
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

  /* ---------- Field: a small window opens into the full-bleed film ---------- */
  const field = $(".field");
  const fieldLines = splitLines($(".field__line"));
  const smallInset = () => (window.innerWidth <= 720 ? "30% 14% 30% 14%" : "26% 33% 26% 33%");
  gsap.set(fieldLines, { yPercent: 110 });
  gsap.set(".field__caption .eyebrow", { autoAlpha: 0 });

  const fieldTl = gsap.timeline({
    defaults: { ease: "none" },
    scrollTrigger: {
      trigger: field,
      pin: ".field__pin",
      start: "top top",
      end: "+=160%",
      scrub: 0.6,
      invalidateOnRefresh: true,
      // Nav goes light once the film fills the screen.
      onUpdate: (self) => (field.dataset.theme = self.progress > 0.45 ? "film" : "bone"),
      onLeaveBack: () => (field.dataset.theme = "bone"),
    },
  });
  fieldTl
    .fromTo(".field__frame",
      { clipPath: () => `inset(${smallInset()} round 4px)` },
      { clipPath: "inset(0% 0% 0% 0% round 0px)", duration: 1, ease: "power2.inOut" }, 0)
    .fromTo(".field__video", { scale: 1.18 }, { scale: 1, duration: 1.2 }, 0)
    .to(".field__meta", { autoAlpha: 0, duration: 0.3 }, 0.1)
    .to(".field__shade", { opacity: 1, duration: 0.5 }, 0.55)
    .to(".field__caption .eyebrow", { autoAlpha: 1, duration: 0.3 }, 0.8)
    .to(fieldLines, { yPercent: 0, duration: 0.5, stagger: 0.12, ease: "power3.out" }, 0.8)
    .to({}, { duration: 0.3 }); // hold on the full frame before moving on

  // Only decode/play the film while it's on screen.
  const video = $(".field__video");
  new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) video.play().catch(() => {});
    else video.pause();
  }, { threshold: 0.01 }).observe(video);

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
      id: "archive",
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

  /* ======================================================================
     MENU — full-screen category list with a live image preview
     ====================================================================== */
  function setupMenu() {
    const btn = $(".js-menu-btn");
    const menu = $("#menu");
    const bg = $(".menu__bg", menu);
    const list = $(".menu__cats", menu);
    const links = $$(".menu__cats a", menu);
    const names = $$(".menu__name > span", menu);
    const extras = $$(".menu__num, .menu__count, .menu__arrow, .menu__eyebrow, .menu__preview, .menu__foot", menu);
    const imgs = $$(".menu__img", menu);
    const desc = $(".js-menu-desc", menu);
    let open = false;
    let front = 0;
    let current = null;

    // Category counts come from the tags on the page, so they stay true.
    links.forEach((a) => {
      const c = a.dataset.cat;
      const n = c === "all" ? $$(".tag").length : $$(`.tag[data-cat="${c}"]`).length;
      $(".js-cat-count", a).textContent = String(n).padStart(2, "0");
    });
    // Warm the cache so image swaps are instant.
    [1, 2, 3, 4, 5].forEach((i) => { const im = new Image(); im.src = `assets/img/menu-${i}.jpg`; });

    function activate(a, hovering = true) {
      list.classList.toggle("is-hovering", hovering);
      links.forEach((l) => l.classList.toggle("is-active", l === a));
      if (current === a) return;
      current = a;
      const next = imgs[1 - front];
      next.src = `assets/img/menu-${a.dataset.img}.jpg`;
      gsap.set(imgs[front], { zIndex: 1 });
      gsap.fromTo(next,
        { zIndex: 2, clipPath: "inset(100% 0% 0% 0%)", scale: 1.15 },
        { clipPath: "inset(0% 0% 0% 0%)", scale: 1, duration: 1 * D, ease: "expo.out", overwrite: true });
      front = 1 - front;
      gsap.to(desc, {
        autoAlpha: 0, y: -6, duration: 0.18 * D, overwrite: true,
        onComplete: () => {
          desc.textContent = a.dataset.desc;
          gsap.fromTo(desc, { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, duration: 0.5 * D, ease: "expo.out" });
        },
      });
    }

    function show() {
      if (open) return;
      open = true;
      menu.hidden = false;
      body.classList.add("menu-open");
      btn.setAttribute("aria-expanded", "true");
      site.lock();
      current = null;
      activate(links[0], false);
      gsap.killTweensOf([bg, ...names, ...extras]);
      gsap.timeline()
        .fromTo(bg, { clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 0.9 * D, ease: "expo.inOut" })
        .fromTo(names, { yPercent: 110 }, { yPercent: 0, duration: 1.1 * D, ease: "expo.out", stagger: 0.05 * D }, 0.45 * D)
        .fromTo(extras, { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 0.8 * D, ease: "expo.out", stagger: 0.02 * D }, 0.6 * D)
        .add(() => links[0].focus({ preventScroll: true }), 0.5 * D);
    }

    function hide(after) {
      if (!open) return;
      open = false;
      btn.setAttribute("aria-expanded", "false");
      gsap.killTweensOf([bg, ...names, ...extras]);
      gsap.timeline({
        onComplete: () => {
          menu.hidden = true;
          body.classList.remove("menu-open");
          list.classList.remove("is-hovering");
          site.unlock();
          if (after) after(); else btn.focus({ preventScroll: true });
        },
      })
        .to(extras, { autoAlpha: 0, duration: 0.25 * D }, 0)
        .to(names, { yPercent: -110, duration: 0.5 * D, ease: "power3.in", stagger: 0.025 * D }, 0)
        .to(bg, { clipPath: "inset(0% 0% 100% 0%)", duration: 0.8 * D, ease: "expo.inOut" }, 0.25 * D);
    }

    btn.addEventListener("click", () => (open ? hide() : show()));
    links.forEach((a) => {
      a.addEventListener("pointerenter", () => activate(a));
      a.addEventListener("focus", () => activate(a));
      a.addEventListener("click", (e) => {
        e.preventDefault();
        hide(() => scrollToCategory(a.dataset.cat));
      });
    });
    list.addEventListener("pointerleave", () => list.classList.remove("is-hovering"));
    $$(".menu__links a", menu).forEach((a) =>
      a.addEventListener("click", (e) => {
        e.preventDefault();
        hide(() => site.scrollTo(a.getAttribute("href")));
      })
    );
    document.addEventListener("keydown", (e) => {
      if (!open) return;
      if (e.key === "Escape") hide();
      if (e.key === "Tab") trapFocus(e, [btn, ...$$("a, button", menu)]);
    });
  }

  /* Scroll to the first tag of a category inside the pinned horizontal track. */
  function scrollToCategory(cat) {
    const tag = cat === "all" ? $(".tag") : $(`.tag[data-cat="${cat}"]`);
    const track = $(".archive__track");
    const st = window.ScrollTrigger && ScrollTrigger.getById("archive");
    if (!tag) return site.scrollTo("#archive");
    const pad = parseFloat(getComputedStyle(track).paddingLeft) || 0;
    const left = tag.getBoundingClientRect().left - track.getBoundingClientRect().left - pad;
    if (st) {
      const maxX = Math.max(1, track.scrollWidth - window.innerWidth);
      const x = gsap.utils.clamp(0, maxX, left);
      site.scrollTo(st.start + (x / maxX) * (st.end - st.start) + 2);
    } else {
      site.scrollTo("#archive");
      $(".archive__pin").scrollLeft = left;
    }
    if (D) gsap.fromTo(tag, { y: 0 }, { y: -22, duration: 0.45, ease: "power2.out", yoyo: true, repeat: 1, delay: 1.7 });
  }

  /* ======================================================================
     BAG — slide-in drawer; every piece is 1 of 1, so quantity is always one
     ====================================================================== */
  function setupCart() {
    const KEY = "a88-bag";
    const cart = $("#cart");
    const panel = $(".cart__panel", cart);
    const scrim = $(".cart__scrim", cart);
    const listEl = $(".js-cart-items", cart);
    const empty = $(".js-cart-empty", cart);
    const checkout = $(".js-checkout", cart);
    const note = $(".cart__note", cart);
    const btn = $(".js-cart-btn");
    const countEl = $(".nav__count");
    const money = (n) => "£" + n.toLocaleString("en-GB");
    const swatch = { "tag--ink": ["#1b211d", "#e6e3da"], "tag--pine": ["#2f3d33", "#e6e3da"], "tag--paper": ["#e6e3da", "#1b211d"] };
    let items = load();
    let open = false;
    let lastFocus = null;

    function load() {
      try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; }
    }
    function save() {
      try { localStorage.setItem(KEY, JSON.stringify(items)); } catch (e) { /* private mode: bag lasts this visit */ }
    }

    function render() {
      $$(".js-cart-count").forEach((el) => (el.textContent = items.length));
      $(".js-subtotal", cart).textContent = money(items.reduce((s, i) => s + i.price, 0));
      empty.hidden = items.length > 0;
      listEl.hidden = items.length === 0;
      checkout.disabled = items.length === 0;
      btn.setAttribute("aria-label", `Bag, ${items.length} item${items.length === 1 ? "" : "s"}`);
      listEl.innerHTML = items.map((i) => {
        const [bgc, fg] = swatch[i.theme] || swatch["tag--ink"];
        return `<li class="cart__item" data-id="${i.id}">
          <div class="cart__swatch" style="--sw-bg:${bgc};--sw-fg:${fg}"><svg viewBox="0 0 146 68" aria-hidden="true"><use href="#mono"/></svg></div>
          <div class="cart__meta"><small>No. ${i.id} — ${i.cat}</small><strong>${i.name}</strong>
            <button class="cart__remove" type="button" data-id="${i.id}">Remove</button></div>
          <span class="cart__price">${money(i.price)}</span></li>`;
      }).join("");
      $$(".js-add").forEach((b) => {
        const inBag = items.some((i) => i.id === b.dataset.id);
        b.classList.toggle("is-added", inBag);
        $(".tag__cta", b).textContent = inBag ? "In bag" : "Add to bag";
        b.setAttribute("aria-label", `${inBag ? "In bag" : "Add to bag"}: ${b.dataset.name}, ${money(+b.dataset.price)}`);
      });
    }

    function bump() {
      if (!D) return;
      gsap.fromTo(countEl, { scale: 1.45 }, { scale: 1, duration: 0.7, ease: "elastic.out(1, 0.4)" });
    }

    function fly(from, done) {
      if (!D) return done();
      const a = from.getBoundingClientRect();
      const b = countEl.getBoundingClientRect();
      const dot = document.createElement("span");
      dot.className = "fly-dot";
      document.body.appendChild(dot);
      const x0 = a.left + a.width / 2, y0 = a.top + a.height / 2;
      const x1 = b.left + b.width / 2, y1 = b.top + b.height / 2;
      const p = { t: 0 };
      gsap.to(p, {
        t: 1, duration: 0.85, ease: "power2.inOut",
        onUpdate: () => {
          // A gentle arc up to the bag.
          const x = x0 + (x1 - x0) * p.t;
          const y = y0 + (y1 - y0) * p.t - Math.sin(Math.PI * p.t) * 120;
          gsap.set(dot, { x, y, scale: 1 - 0.4 * p.t });
        },
        onComplete: () => { dot.remove(); done(); },
      });
    }

    function add(b) {
      const id = b.dataset.id;
      if (items.some((i) => i.id === id)) return show();
      const tag = b.closest(".tag");
      const theme = ["tag--ink", "tag--pine", "tag--paper"].find((c) => tag.classList.contains(c));
      items.push({ id, name: b.dataset.name, cat: b.dataset.cat, price: +b.dataset.price, theme });
      save();
      $(".nav").classList.remove("is-hidden"); // bring the bag into view for the hand-off
      $(".tag__cta", b).textContent = "Added";
      fly(b, () => { render(); bump(); });
    }

    function remove(id) {
      const li = $(`.cart__item[data-id="${id}"]`, listEl);
      const finish = () => { items = items.filter((i) => i.id !== id); save(); render(); };
      if (!li || !D) return finish();
      gsap.timeline({ onComplete: finish })
        .to(li, { x: 40, autoAlpha: 0, duration: 0.35, ease: "power2.in" })
        .to(li, { height: 0, paddingTop: 0, paddingBottom: 0, borderWidth: 0, duration: 0.4, ease: "power3.inOut" });
    }

    function show() {
      if (open) return;
      open = true;
      lastFocus = document.activeElement;
      cart.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      site.lock();
      render();
      gsap.killTweensOf([panel, scrim]);
      gsap.timeline()
        .fromTo(scrim, { opacity: 0 }, { opacity: 1, duration: 0.5 * D })
        .fromTo(panel, { xPercent: 100 }, { xPercent: 0, duration: 0.9 * D, ease: "expo.out" }, 0)
        .fromTo($$(".cart__head, .cart__item, .cart__empty > *, .cart__foot", cart),
          { autoAlpha: 0, x: 30 }, { autoAlpha: 1, x: 0, duration: 0.8 * D, ease: "expo.out", stagger: 0.05 * D }, 0.15 * D);
      $(".cart__close", cart).focus({ preventScroll: true });
    }

    function hide(after) {
      if (!open) return;
      open = false;
      btn.setAttribute("aria-expanded", "false");
      gsap.killTweensOf([panel, scrim]);
      gsap.timeline({
        onComplete: () => {
          cart.hidden = true;
          site.unlock();
          if (after) after(); else if (lastFocus) lastFocus.focus({ preventScroll: true });
        },
      })
        .to(panel, { xPercent: 100, duration: 0.6 * D, ease: "expo.in" })
        .to(scrim, { opacity: 0, duration: 0.4 * D }, 0.2 * D);
    }

    btn.addEventListener("click", show);
    $$(".js-cart-close", cart).forEach((el) => el.addEventListener("click", () => hide()));
    $(".js-cart-browse", cart).addEventListener("click", (e) => {
      e.preventDefault();
      hide(() => site.scrollTo("#archive"));
    });
    listEl.addEventListener("click", (e) => {
      const r = e.target.closest(".cart__remove");
      if (r) remove(r.dataset.id);
    });
    $$(".js-add").forEach((b) => b.addEventListener("click", () => add(b)));
    checkout.addEventListener("click", () => {
      // TODO: hand `items` to your checkout (e.g. Shopify cart permalink or Stripe Checkout).
      note.textContent = "Checkout isn't open yet. Your bag is saved on this device.";
    });
    document.addEventListener("keydown", (e) => {
      if (!open) return;
      if (e.key === "Escape") hide();
      if (e.key === "Tab") trapFocus(e, $$("a, button:not(:disabled)", panel));
    });

    render();
  }

  /* ======================================================================
     RETURNS — accordion with measured height animation
     ====================================================================== */
  function setupReturns() {
    $$(".js-acc").forEach((acc) => {
      const q = $(".acc__q", acc);
      const a = $(".acc__a", acc);
      const p = $("p", a);
      q.addEventListener("click", () => {
        const isOpen = q.getAttribute("aria-expanded") === "true";
        q.setAttribute("aria-expanded", String(!isOpen));
        gsap.killTweensOf([a, p]);
        if (isOpen) {
          gsap.to(a, {
            height: 0, duration: 0.5 * D, ease: "power3.inOut",
            onComplete: () => { a.hidden = true; gsap.set(a, { clearProps: "height" }); refresh(); },
          });
        } else {
          a.hidden = false;
          gsap.fromTo(a, { height: 0 }, {
            height: "auto", duration: 0.7 * D, ease: "expo.out",
            onComplete: () => { gsap.set(a, { clearProps: "height" }); refresh(); },
          });
          gsap.fromTo(p, { autoAlpha: 0, y: 12 }, { autoAlpha: 1, y: 0, duration: 0.7 * D, delay: 0.08 * D, ease: "expo.out" });
        }
      });
    });
    const refresh = () => window.ScrollTrigger && ScrollTrigger.refresh();
  }

  function trapFocus(e, nodes) {
    const f = nodes.filter((n) => n.offsetParent !== null || n === document.activeElement);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

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
