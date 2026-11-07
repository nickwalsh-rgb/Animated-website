/* Archive 88: shared behaviour for every page
   Smooth scroll, nav, category menu, bag, accordions, social keys, email form, reveals.
   Page scripts (home.js, product.js) read helpers from window.A88. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const html = document.documentElement;
  const body = document.body;
  const ROOT = html.dataset.root || "";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hasGsap = !!window.gsap;
  const motion = hasGsap && !reduced;
  const D = motion ? 1 : 0; // duration multiplier: 0 makes every tween instant

  if (hasGsap && window.ScrollTrigger) gsap.registerPlugin(ScrollTrigger);

  /* ---------- Scroll lock + scrolling, with or without smooth scroll ---------- */
  const site = {
    lenis: null,
    locks: 0,
    lock() {
      if (this.locks++ === 0) {
        if (this.lenis) this.lenis.stop();
        html.style.overflow = "hidden";
      }
    },
    unlock() {
      if (this.locks > 0 && --this.locks === 0) {
        html.style.overflow = "";
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
    /* Follow a link: same-page hashes scroll, anything else navigates. */
    go(href) {
      if (href.startsWith("#")) this.scrollTo(href);
      else window.location.href = href;
    },
  };

  if (motion && window.Lenis) {
    const lenis = new Lenis({ duration: 1.15, smoothWheel: true });
    site.lenis = lenis;
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
  }

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

  const A88 = (window.A88 = { $, $$, ROOT, site, motion, reduced, D, splitLines, splitWords, onCategory: null });

  $$(".js-year").forEach((el) => (el.textContent = new Date().getFullYear()));
  expireDropDates();
  setupForm();
  setupSocial();
  if (hasGsap) {
    setupMenu();
    setupCart();
    setupAccordions();
  }
  setupNavTheme();

  // Same-page anchors scroll smoothly (menu and bag links close their overlay first).
  $$('a[href^="#"]').forEach((a) => {
    if (a.closest(".menu, .cart")) return;
    a.addEventListener("click", (e) => {
      e.preventDefault();
      site.scrollTo(a.getAttribute("href"));
    });
  });

  if (motion) {
    $$(".js-lines").forEach((el) => {
      const lines = splitLines(el);
      gsap.from(lines, {
        yPercent: 110, duration: 1.1, ease: "expo.out", stagger: 0.09,
        scrollTrigger: { trigger: el, start: "top 82%" },
      });
    });
    // Opacity only (not visibility) so links and fields inside stay reachable by keyboard.
    gsap.set(".js-reveal", { opacity: 0, y: 30 });
    ScrollTrigger.batch(".js-reveal", {
      start: "top 90%",
      once: true,
      onEnter: (batch) => gsap.to(batch, { opacity: 1, y: 0, duration: 1, ease: "expo.out", stagger: 0.1 }),
    });
    // Anything that receives keyboard focus before it has scrolled into view shows at once.
    document.addEventListener("focusin", (e) => {
      const el = e.target.closest(".js-reveal, .tag");
      if (el && +getComputedStyle(el).opacity < 1) gsap.to(el, { opacity: 1, y: 0, duration: 0.3, overwrite: "auto" });
    });
    // Footer wordmark rises letter by letter. Triggered off the footer itself so it
    // still fires on phones, where the wordmark sits right at the end of the page.
    gsap.from($$(".wordmark--footer .wm-l"), {
      y: 76, duration: 1.3, ease: "expo.out", stagger: 0.06,
      scrollTrigger: { trigger: ".footer", start: "top 70%" },
    });
    window.addEventListener("load", () => ScrollTrigger.refresh());
    if (document.fonts) document.fonts.ready.then(() => ScrollTrigger.refresh());
  }

  /* ======================================================================
     Drop dates are written at build time; hide them once the date has passed
     ====================================================================== */
  function expireDropDates() {
    $$(".js-drop[data-drop]").forEach((el) => {
      if (new Date(el.dataset.drop) < new Date()) el.remove();
    });
  }

  /* ======================================================================
     NAV: colour follows the section underneath; hides on scroll down
     ====================================================================== */
  function setupNavTheme() {
    const sections = $$("[data-theme]");
    const nav = $(".nav");
    const probe = () => {
      const y = 36; // roughly the nav's vertical centre
      for (const s of sections) {
        const r = s.getBoundingClientRect();
        if (r.top <= y && r.bottom > y) { body.dataset.nav = s.dataset.theme; break; }
      }
    };
    let last = 0;
    const onScroll = () => {
      probe();
      const yNow = window.scrollY;
      nav.classList.toggle("is-hidden", yNow > last && yNow > window.innerHeight * 0.6);
      nav.classList.toggle("is-solid", yNow > 40);
      last = yNow;
    };
    if (site.lenis) site.lenis.on("scroll", onScroll);
    else window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ======================================================================
     MENU: full-screen category list with a live image preview
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
    const imgSrc = (n) => `${ROOT}assets/img/menu-${n}.jpg`;
    let open = false;
    let front = 0;
    let current = null;

    [1, 2, 3, 4, 5].forEach((i) => { const im = new Image(); im.src = imgSrc(i); });

    function activate(a, hovering = true) {
      list.classList.toggle("is-hovering", hovering);
      links.forEach((l) => l.classList.toggle("is-active", l === a));
      if (current === a) return;
      current = a;
      const next = imgs[1 - front];
      next.src = imgSrc(a.dataset.img);
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
        // On the homepage the archive scrolls to the category; elsewhere we go there.
        hide(() => (A88.onCategory ? A88.onCategory(a.dataset.cat) : (window.location.href = a.href)));
      });
    });
    list.addEventListener("pointerleave", () => list.classList.remove("is-hovering"));
    $$(".menu__links a", menu).forEach((a) =>
      a.addEventListener("click", (e) => {
        e.preventDefault();
        hide(() => site.go(a.getAttribute("href")));
      })
    );
    document.addEventListener("keydown", (e) => {
      if (!open) return;
      if (e.key === "Escape") hide();
      if (e.key === "Tab") trapFocus(e, [btn, ...$$("a, button", menu)]);
    });
  }

  /* ======================================================================
     BAG: slide-in drawer. Every piece is 1 of 1, so quantity is always one.
     Items are stored in localStorage until Shopify checkout is connected.
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
    const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
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
        const thumb = i.img
          ? `<img src="${ROOT}${esc(i.img)}" alt="" loading="lazy" />`
          : `<svg viewBox="0 0 146 68" aria-hidden="true"><use href="#mono"/></svg>`;
        const name = i.url ? `<a href="${ROOT}${esc(i.url)}">${esc(i.name)}</a>` : esc(i.name);
        return `<li class="cart__item" data-id="${esc(i.id)}">
          <div class="cart__swatch${i.img ? " has-photo" : ""}" style="--sw-bg:${bgc};--sw-fg:${fg}">${thumb}</div>
          <div class="cart__meta"><small>No. ${esc(i.id)}, ${esc(i.cat)}</small><strong>${name}</strong>
            <button class="cart__remove" type="button" data-id="${esc(i.id)}">Remove</button></div>
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
          const x = x0 + (x1 - x0) * p.t;
          const y = y0 + (y1 - y0) * p.t - Math.sin(Math.PI * p.t) * 120; // gentle arc
          gsap.set(dot, { x, y, scale: 1 - 0.4 * p.t });
        },
        onComplete: () => { dot.remove(); done(); },
      });
    }

    function add(b) {
      const id = b.dataset.id;
      if (items.some((i) => i.id === id)) return show();
      const d = b.dataset;
      items.push({ id, name: d.name, cat: d.cat, price: +d.price, theme: d.theme, img: d.img || "", url: d.url || "" });
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
      const href = e.currentTarget.getAttribute("href");
      hide(() => site.go(href));
    });
    listEl.addEventListener("click", (e) => {
      const r = e.target.closest(".cart__remove");
      if (r) remove(r.dataset.id);
    });
    $$(".js-add").forEach((b) => b.addEventListener("click", () => add(b)));
    checkout.addEventListener("click", () => {
      // TODO (Shopify): POST `items` to /cart/add.js then go to /checkout, or build a cart permalink.
      note.textContent = "Checkout isn't open yet. Your bag is saved on this device.";
    });
    document.addEventListener("keydown", (e) => {
      if (!open) return;
      if (e.key === "Escape") hide();
      if (e.key === "Tab") trapFocus(e, $$("a, button:not(:disabled)", panel));
    });
    window.addEventListener("storage", (e) => { if (e.key === KEY) { items = load(); render(); } });

    render();
  }

  /* ======================================================================
     ACCORDIONS (returns FAQ, product details): measured height animation
     ====================================================================== */
  function setupAccordions() {
    const refresh = () => window.ScrollTrigger && ScrollTrigger.refresh();
    $$(".js-acc").forEach((acc) => {
      const q = $(".acc__q", acc);
      const a = $(".acc__a", acc);
      const inner = $(".acc__body", a) || a.firstElementChild;
      q.addEventListener("click", () => {
        const isOpen = q.getAttribute("aria-expanded") === "true";
        q.setAttribute("aria-expanded", String(!isOpen));
        gsap.killTweensOf([a, inner]);
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
          gsap.fromTo(inner, { autoAlpha: 0, y: 12 }, { autoAlpha: 1, y: 0, duration: 0.7 * D, delay: 0.08 * D, ease: "expo.out" });
        }
      });
    });
  }

  function trapFocus(e, nodes) {
    const f = nodes.filter((n) => n.offsetParent !== null || n === document.activeElement);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  /* ======================================================================
     EMAIL SIGN-UP (homepage)
     ====================================================================== */
  function setupForm() {
    const form = $(".join__form");
    if (!form) return;
    const note = $(".js-note");
    const section = $(".join");
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = $("input", form);
      const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value.trim());
      section.classList.toggle("is-error", !ok);
      input.setAttribute("aria-invalid", String(!ok));
      if (!ok) { note.textContent = "That email doesn't look right. Please check it and try again."; input.focus(); return; }
      // TODO (Shopify): post to /contact#contact_form with form_type=customer, or your email provider.
      note.textContent = "You're on the list. We'll be in touch before the next drop.";
      form.reset();
    });
  }

  /* ======================================================================
     SOCIAL KEYS: tilt toward the pointer while raised; press state for touch
     ====================================================================== */
  function setupSocial() {
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    $$(".social__btn").forEach((btn) => {
      const face = $(".social__face", btn);
      if (fine) {
        btn.addEventListener("pointermove", (e) => {
          const r = btn.getBoundingClientRect();
          face.style.setProperty("--ry", (((e.clientX - r.left) / r.width - 0.5) * 22).toFixed(1) + "deg");
          face.style.setProperty("--rx", (((e.clientY - r.top) / r.height - 0.5) * -22).toFixed(1) + "deg");
        });
        btn.addEventListener("pointerleave", () => {
          face.style.removeProperty("--rx");
          face.style.removeProperty("--ry");
        });
      }
      const up = () => btn.classList.remove("is-pressed");
      btn.addEventListener("pointerdown", () => btn.classList.add("is-pressed"));
      btn.addEventListener("pointerup", () => setTimeout(up, 90));
      btn.addEventListener("pointercancel", up);
      btn.addEventListener("pointerleave", up);
    });
  }
})();
