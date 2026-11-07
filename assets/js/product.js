/* Archive 88: product page (needs site.js first) */
(() => {
  const { $, $$, motion, T, site } = window.A88;
  const slides = $(".js-slides");
  const pager = $$(".js-pager i");

  /* Phones: photos swipe sideways; the pager line under them follows along. */
  if (slides && pager.length > 1 && "IntersectionObserver" in window) {
    const figs = $$(".pdp__slide", slides);
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting && en.intersectionRatio > 0.6) {
          const i = figs.indexOf(en.target);
          pager.forEach((p, j) => p.classList.toggle("is-on", j === i));
        }
      });
    }, { root: slides, threshold: [0.6] });
    figs.forEach((f) => io.observe(f));
  }

  /* Phones: the buy bar pins to the bottom whenever the main buy button is off screen,
     and steps aside for the footer. Its button is a normal .js-add, so the bag handles it. */
  const bar = $(".js-buybar");
  const mainBuy = $(".pdp__buy");
  if (bar && mainBuy && "IntersectionObserver" in window) {
    const mq = matchMedia("(max-width: 900px)");
    let buyVisible = true, atFooter = false;
    const set = () => {
      const on = mq.matches && !buyVisible && !atFooter;
      bar.classList.toggle("is-on", on);
      bar.inert = !on;
    };
    new IntersectionObserver(([en]) => { buyVisible = en.isIntersecting; set(); }).observe(mainBuy);
    const foot = $(".footer");
    if (foot) new IntersectionObserver(([en]) => { atFooter = en.isIntersecting; set(); }).observe(foot);
    mq.addEventListener("change", set);
  }

  /* Check the fit: your measurement (remembered on this device, per measurement name)
     against this piece's, as words for everyone and a small scale for sighted users. */
  const fit = $(".js-fit");
  if (fit) {
    const key = $(".js-fit-key", fit), val = $(".js-fit-val", fit), out = $(".js-fit-out", fit), scale = $(".js-fit-scale", fit);
    const store = (k) => `a88-fit:${k.toLowerCase()}`;
    const get = (k) => { try { return localStorage.getItem(store(k)) || ""; } catch (e) { return ""; } };
    const put = (k, v) => { try { v ? localStorage.setItem(store(k), v) : localStorage.removeItem(store(k)); } catch (e) { /* private mode */ } };
    const saved = [...key.options].find((o) => get(o.value));
    if (saved) key.value = saved.value;
    const round = (n) => String(Math.round(n * 2) / 2);
    let speak;
    const show = (now) => {
      const opt = key.selectedOptions[0];
      const piece = +opt.dataset.cm, mine = parseFloat(val.value);
      clearTimeout(speak);
      if (!(mine > 0 && mine <= 250)) { out.textContent = ""; scale.hidden = true; return; }
      const d = piece - mine, a = Math.abs(d), name = opt.value.toLowerCase();
      const long = /length|sleeve|rise|inseam/i.test(opt.value);
      const word = d > 0 ? (long ? "longer" : "wider") : (long ? "shorter" : "narrower");
      const msg = a < 1
        ? `A near match: within 1 cm of yours on the ${name}.`
        : `This piece is ${round(a)} cm ${word} than yours on the ${name}${a <= 2 ? ", barely noticeable" : a >= 6 ? ", a clear difference" : ""}.`;
      // The scale moves straight away; the words wait for a pause in typing so screen readers aren't flooded.
      const mid = (piece + mine) / 2, range = Math.max(8, a * 1.5);
      const at = (x) => `${50 + ((x - mid) / range) * 50}%`;
      $(".fit__mark--piece", scale).style.setProperty("--at", at(piece));
      $(".fit__mark--you", scale).style.setProperty("--at", at(mine));
      scale.hidden = false;
      if (now) out.textContent = msg; else speak = setTimeout(() => { out.textContent = msg; }, 450);
    };
    key.addEventListener("change", () => { val.value = get(key.value); show(true); });
    val.addEventListener("input", () => { put(key.value, val.value.trim()); show(false); });
    val.value = get(key.value);
    show(true);
  }

  /* Photo zoom: only when there are real photos. Opens a full-screen viewer; click or
     "Zoom in" magnifies at that spot, the mouse looks around, touch scrolls. */
  const imgs = $$(".pdp__slide img");
  if (imgs.length && typeof HTMLDialogElement === "function") {
    const ICON = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="M12.5 12.5 18 18M8.5 6v5M6 8.5h5"/></svg>';
    const dlg = document.createElement("dialog");
    dlg.className = "zoom";
    dlg.setAttribute("aria-label", "Photo viewer");
    dlg.innerHTML = `<div class="zoom__stage"><img class="zoom__img" alt="" draggable="false" /></div>
      <p class="zoom__hint">Click to zoom in, then move to look around.</p>
      <button class="zoom__btn zoom__close" type="button">Close</button>
      <div class="zoom__bar">
        <button class="zoom__btn js-zprev" type="button" aria-label="Previous photo">&larr;</button>
        <button class="zoom__btn js-ztoggle" type="button">Zoom in</button>
        <span class="zoom__count" aria-live="polite"></span>
        <button class="zoom__btn js-znext" type="button" aria-label="Next photo">&rarr;</button>
      </div>`;
    document.body.appendChild(dlg);
    const stage = $(".zoom__stage", dlg), big = $(".zoom__img", dlg), count = $(".zoom__count", dlg);
    const prev = $(".js-zprev", dlg), next = $(".js-znext", dlg), toggle = $(".js-ztoggle", dlg);
    let at = 0, zoomed = false;

    // The largest file in the srcset, so zooming shows real detail.
    const best = (im) => {
      const set = (im.getAttribute("srcset") || "").split(",").map((s) => s.trim().split(/\s+/)).filter((p) => p[0]);
      if (!set.length) return im.currentSrc || im.src;
      set.sort((a, b) => parseInt(b[1], 10) - parseInt(a[1], 10));
      return new URL(set[0][0], location.href).href;
    };
    // Where the photo actually sits inside the stage (object-fit: contain leaves margins).
    const fitted = () => {
      const W = stage.clientWidth, H = stage.clientHeight;
      const s = Math.min(W / (big.naturalWidth || W), H / (big.naturalHeight || H));
      const w = (big.naturalWidth || W) * s, h = (big.naturalHeight || H) * s;
      return { w, h, x: (W - w) / 2, y: (H - h) / 2 };
    };
    const setZoom = (on, fx = 0.5, fy = 0.5) => {
      zoomed = on;
      dlg.classList.toggle("is-zoomed", on);
      toggle.textContent = on ? "Zoom out" : "Zoom in";
      if (on) {
        const f = fitted();
        big.style.width = `${f.w * 2.4}px`;
        big.style.height = `${f.h * 2.4}px`;
        stage.scrollLeft = fx * stage.scrollWidth - stage.clientWidth / 2;
        stage.scrollTop = fy * stage.scrollHeight - stage.clientHeight / 2;
        if (motion) big.animate([{ scale: 1 / 2.4 + 0.25, opacity: 0.6 }, { scale: 1, opacity: 1 }], { duration: T.fast * 1000, easing: "cubic-bezier(.16,1,.3,1)" });
      } else {
        big.style.width = big.style.height = "";
        stage.scrollLeft = stage.scrollTop = 0;
      }
    };
    const go = (n) => {
      at = Math.max(0, Math.min(imgs.length - 1, n));
      setZoom(false);
      big.src = best(imgs[at]);
      big.alt = imgs[at].alt;
      count.textContent = `${at + 1} / ${imgs.length}`;
      prev.disabled = at === 0;
      next.disabled = at === imgs.length - 1;
      prev.hidden = next.hidden = imgs.length < 2;
    };
    const open = (n) => {
      go(n);
      dlg.showModal();
      site.lock();
      if (motion) gsap.fromTo(dlg, { opacity: 0 }, { opacity: 1, duration: T.fast, ease: "power2.out" });
      toggle.focus();
    };

    big.addEventListener("click", (e) => {
      if (zoomed) return setZoom(false);
      const f = fitted(), r = stage.getBoundingClientRect();
      const fx = (e.clientX - r.left - f.x) / f.w, fy = (e.clientY - r.top - f.y) / f.h;
      if (fx < 0 || fx > 1 || fy < 0 || fy > 1) return;
      setZoom(true, fx, fy);
    });
    // Mouse: look around by moving, rather than dragging scrollbars.
    stage.addEventListener("pointermove", (e) => {
      if (!zoomed || e.pointerType !== "mouse") return;
      const r = stage.getBoundingClientRect();
      stage.scrollLeft = ((e.clientX - r.left) / r.width) * (stage.scrollWidth - stage.clientWidth);
      stage.scrollTop = ((e.clientY - r.top) / r.height) * (stage.scrollHeight - stage.clientHeight);
    });
    toggle.addEventListener("click", () => setZoom(!zoomed));
    prev.addEventListener("click", () => go(at - 1));
    next.addEventListener("click", () => go(at + 1));
    $(".zoom__close", dlg).addEventListener("click", () => dlg.close());
    dlg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") { e.preventDefault(); go(at - 1); }
      if (e.key === "ArrowRight") { e.preventDefault(); go(at + 1); }
    });
    dlg.addEventListener("close", () => { site.unlock(); setZoom(false); });

    imgs.forEach((im, i) => {
      const fig = im.closest(".pdp__slide");
      fig.classList.add("has-zoom");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pdp__zoom";
      b.setAttribute("aria-label", `Zoom photo ${i + 1} of ${imgs.length}`);
      b.innerHTML = ICON;
      b.addEventListener("click", () => open(i));
      fig.appendChild(b);
      im.addEventListener("click", () => open(i));
    });
  }

  if (!motion) return;

  /* Entrance: first photo unmasks upward, details rise in one after another.
     Runs on the first frame, after "pagereveal": if the page arrived via a page transition,
     the photo is already morphing in from the hang tag, so it isn't animated again. */
  const first = $(".pdp__slide");
  requestAnimationFrame(() => {
    const morphing = document.documentElement.classList.contains("vt-in");
    const tl = gsap.timeline({ defaults: { ease: "expo.out" } });
    if (!morphing) {
      tl.from(".nav", { autoAlpha: 0, y: -12, duration: T.slow }, 0)
        .fromTo(first, { clipPath: "inset(100% 0% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: T.slowest }, 0.05)
        .from($("img, svg", first), { scale: 1.12, duration: T.slowest }, 0.05);
    }
    tl.from(".crumbs", { autoAlpha: 0, y: 10, duration: T.slow }, morphing ? 0.15 : 0.2)
      .from($$(".js-pdp-in"), { opacity: 0, y: 24, duration: T.slower, stagger: 0.07 }, morphing ? 0.2 : 0.25);
  });

  /* Desktop: later photos unmask as they scroll into view. */
  $$(".pdp__slide").slice(1).forEach((s) => {
    gsap.fromTo(s, { clipPath: "inset(12% 0% 0% 0%)", autoAlpha: 0.4 }, {
      clipPath: "inset(0% 0% 0% 0%)", autoAlpha: 1, duration: T.slower, ease: "expo.out",
      scrollTrigger: { trigger: s, start: "top 88%", once: true },
    });
  });
})();
