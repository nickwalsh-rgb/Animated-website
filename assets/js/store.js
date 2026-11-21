/* Archive 88: shared runtime. No dependencies.
   - Header: see-through over the hero, solid after scrolling or while a mega menu is open
   - Mega menus (hover on desktop, chevron buttons for keyboard and touch)
   - Dialogs: one opener/closer for the menu, login, size guide and full-screen gallery (native <dialog>)
   - Menu: full-screen drill-down on phones (each level replaces the last, with a back arrow)
   - Bag: localStorage, synced across tabs, live count in the header, added-to-bag pop-up
   - Wishlist hearts, newsletter, login drawer, hero film, carousels, promotion tracking
   Exposes window.A88 for plp.js, pdp.js, bag.js, search.js and gift.js. */
(() => {
  "use strict";
  const cfg = JSON.parse(document.getElementById("store-config").textContent);
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const fmt = new Intl.NumberFormat(cfg.locale, { style: "currency", currency: cfg.currency, minimumFractionDigits: 2 });
  const money = (n) => fmt.format(n);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (n) => `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-${n}"/></svg>`;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const desktop = matchMedia("(min-width: 1024px)");
  const fine = matchMedia("(hover: hover) and (pointer: fine)");
  const store = {
    get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode: lasts this page */ } },
  };
  const liveEl = $("[data-live]");
  function announce(msg) { if (!liveEl) return; liveEl.textContent = ""; setTimeout(() => (liveEl.textContent = msg), 40); }

  /* ── Header state ──────────────────────────────────────────────────────── */
  const hdr = $("[data-header]");
  if (hdr && hdr.classList.contains("hdr--overlay")) {
    let ticking = false;
    const update = () => { hdr.classList.toggle("is-solid", scrollY > 10); ticking = false; };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    update();
  }

  /* ── Mega menus ────────────────────────────────────────────────────────── */
  const megaItems = $$("[data-mega-item]");
  let openItem = null, hoverTimer;
  function setMega(item, { focus = false } = {}) {
    if (openItem && openItem !== item) {
      openItem.classList.remove("is-open");
      $(".mega", openItem).hidden = true;
      $(".hdr__chev", openItem).setAttribute("aria-expanded", "false");
    }
    openItem = item;
    if (item) {
      item.classList.add("is-open");
      $(".mega", item).hidden = false;
      $(".hdr__chev", item).setAttribute("aria-expanded", "true");
      if (focus) $(".mega__link", item)?.focus();
    }
    hdr?.classList.toggle("is-mega", !!item);
  }
  megaItems.forEach((item) => {
    const chev = $(".hdr__chev", item);
    chev.addEventListener("click", () => setMega(openItem === item ? null : item, { focus: openItem !== item && chev.matches(":focus-visible") }));
    item.addEventListener("mouseenter", () => { if (!fine.matches) return; clearTimeout(hoverTimer); hoverTimer = setTimeout(() => setMega(item), openItem ? 0 : 80); });
    item.addEventListener("mouseleave", () => { if (!fine.matches) return; clearTimeout(hoverTimer); hoverTimer = setTimeout(() => { if (openItem === item) setMega(null); }, 120); });
    item.addEventListener("focusout", (ev) => { if (!item.contains(ev.relatedTarget) && openItem === item) setMega(null); });
    item.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && openItem === item) { setMega(null); chev.focus(); }
    });
  });
  document.addEventListener("click", (ev) => { if (openItem && !openItem.contains(ev.target)) setMega(null); });

  /* ── Dialogs ───────────────────────────────────────────────────────────── */
  function syncLock() { document.body.classList.toggle("is-locked", !!$("dialog[open]:modal")); }
  function openDialog(id, opener) {
    const dlg = document.getElementById(id);
    if (!dlg || dlg.open) return;
    $$("dialog[open]:modal").forEach((d) => { if (d !== dlg) d.close(); });
    setMega(null);
    dlg._opener = opener || document.activeElement;
    dlg.showModal();
    syncLock();
    dlg.dispatchEvent(new CustomEvent("dialog:open", { detail: { opener } }));
  }
  function closeDialog(dlg) { if (dlg?.open) dlg.close(); }
  $$("dialog").forEach((dlg) => {
    dlg.addEventListener("close", () => {
      syncLock();
      const o = dlg._opener;
      if (o && o.isConnected && document.activeElement === document.body) o.focus({ preventScroll: true });
    });
    // A click on the backdrop (the dialog element itself, outside its content box) closes drawers and menus
    dlg.addEventListener("click", (ev) => {
      if (ev.target !== dlg || dlg.matches(".fs")) return;
      const r = dlg.getBoundingClientRect();
      if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) dlg.close();
    });
  });
  document.addEventListener("click", (ev) => {
    const opener = ev.target.closest("[data-dialog-open]");
    if (opener) { ev.preventDefault(); openDialog(opener.dataset.dialogOpen, opener); return; }
    const closer = ev.target.closest("[data-dialog-close]");
    if (closer) closeDialog(closer.closest("dialog"));
  });

  /* ── Menu drill-down ───────────────────────────────────────────────────── */
  const menu = $("[data-menu]");
  if (menu) {
    const back = $("[data-menu-back]", menu), search = $("[data-menu-search]", menu), rootPanel = $("#menu-root", menu);
    const show = (panel) => {
      $$("[data-menu-panel]", menu).forEach((p) => (p.hidden = p !== panel));
      const atRoot = panel === rootPanel;
      back.hidden = atRoot; search.hidden = !atRoot;
    };
    menu.addEventListener("click", (ev) => {
      const go = ev.target.closest("[data-menu-go]");
      if (go) { const p = document.getElementById(go.dataset.menuGo); show(p); menu._from = go; $("a, button", p)?.focus(); }
    });
    back.addEventListener("click", () => { show(rootPanel); menu._from?.focus(); });
    menu.addEventListener("close", () => show(rootPanel));
    menu.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !back.hidden) { ev.preventDefault(); back.click(); } });
    desktop.addEventListener("change", (m) => { if (m.matches) closeDialog(menu); });
  }

  /* ── Login drawer (accounts are not live yet: the form says so) ────────── */
  const login = $("[data-login]");
  if (login) {
    const msg = $("[data-login-msg]", login);
    const notLive = "Accounts open soon. Your bag and wishlist are saved on this device in the meantime.";
    $("[data-pw-toggle]", login).addEventListener("click", (ev) => {
      const b = ev.currentTarget, input = $("#login-password");
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      b.textContent = show ? "Hide" : "Show";
      b.setAttribute("aria-pressed", String(show));
      b.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
    login.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const email = $("#login-email"), pw = $("#login-password");
      let ok = true;
      [[email, /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()) ? "" : "Enter your email address, like name@example.com"],
       [pw, pw.value ? "" : "Enter your password"]].forEach(([el, err]) => {
        el.setAttribute("aria-invalid", String(!!err));
        $(`#${el.id}-err`).textContent = err;
        if (err && ok) { el.focus(); ok = false; }
      });
      if (ok) msg.textContent = notLive;
    });
    $("[data-login-forgot]").addEventListener("click", (ev) => { ev.preventDefault(); msg.textContent = notLive; });
    $("[data-login-create]").addEventListener("click", () => { msg.textContent = notLive; msg.scrollIntoView({ block: "nearest" }); });
  }

  /* ── Product thumbnails (bag lines, pop-up) ────────────────────────────── */
  function thumb(line, cls = "thumb") {
    if (line.img) return `<img class="${cls}" src="${esc(cfg.root + line.img)}" alt="" width="120" height="180" loading="lazy">`;
    return `<svg class="${cls} art art--svg" viewBox="0 0 400 500" preserveAspectRatio="xMidYMid meet" aria-hidden="true" style="color:${esc(line.hex)}"><use href="#s-${esc(line.sil)}"/></svg>`;
  }

  /* ── Bag ───────────────────────────────────────────────────────────────── */
  const KEY = "a88.bag.v2";
  let lines = store.get(KEY, []);
  const Bag = {
    get lines() { return lines; },
    count: () => lines.reduce((n, l) => n + l.qty, 0),
    subtotal: () => lines.reduce((n, l) => n + l.qty * l.price, 0),
    /** item: {sku, handle, title, url, price, colour, colourName, hex, size, sil, img, max, id?} */
    add(item) {
      const found = lines.find((l) => l.sku === item.sku);
      if (found) {
        if (found.qty >= found.max) { announce(`Only ${found.max} available in ${item.size}`); return false; }
        found.qty += 1;
      } else lines.unshift({ ...item, qty: 1 });
      save();
      showAdded(item);
      announce(`Added ${item.title}, ${item.colourName}, ${item.size} to your bag. Bag, ${Bag.count()} items.`);
      return true;
    },
    setQty(sku, qty) {
      const l = lines.find((x) => x.sku === sku);
      if (!l) return;
      if (qty <= 0) lines = lines.filter((x) => x.sku !== sku);
      else l.qty = Math.min(qty, l.max);
      save();
    },
    remove(sku) { lines = lines.filter((x) => x.sku !== sku); save(); },
  };
  function save() { store.set(KEY, lines); paintCount(); document.dispatchEvent(new CustomEvent("bag:change")); }
  function paintCount() {
    const n = Bag.count();
    $$("[data-bag-count]").forEach((el) => (el.textContent = n ? String(n) : ""));
    $$("[data-bag-link]").forEach((el) => el.setAttribute("aria-label", n ? `Go to bag, ${n} item${n === 1 ? "" : "s"}` : "Go to bag"));
    $$("[data-added-bag]").forEach((el) => (el.textContent = `Bag (${n})`));
  }
  addEventListener("storage", (ev) => { if (ev.key === KEY) { lines = store.get(KEY, []); paintCount(); document.dispatchEvent(new CustomEvent("bag:change")); } });
  paintCount();

  /* Added-to-bag pop-up: stays a few seconds, longer while the pointer or focus is on it */
  const added = $("[data-added]");
  let addedTimer;
  function hideAdded() { if (added) added.hidden = true; }
  function showAdded(item) {
    if (!added) return;
    $("[data-added-item]", added).innerHTML =
      `${thumb(item)}<div><p>${esc(item.title)}</p><p>${esc(item.colourName)}</p><p>${esc(item.size)}</p></div><p>${money(item.price)}</p>`;
    added.hidden = false;
    clearTimeout(addedTimer);
    addedTimer = setTimeout(hideAdded, 6000);
  }
  if (added) {
    $("[data-added-close]", added).addEventListener("click", hideAdded);
    added.addEventListener("mouseenter", () => clearTimeout(addedTimer));
    added.addEventListener("focusin", () => clearTimeout(addedTimer));
    added.addEventListener("mouseleave", () => { addedTimer = setTimeout(hideAdded, 2500); });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") hideAdded(); });
  }

  /* ── Wishlist ──────────────────────────────────────────────────────────── */
  const WKEY = "a88.wish.v1";
  let wish = new Set(store.get(WKEY, []));
  const Wish = {
    has: (k) => wish.has(k),
    sync(scope = document) {
      $$("[data-wish]", scope).forEach((b) => {
        const on = wish.has(b.dataset.wish);
        b.setAttribute("aria-pressed", String(on));
        const label = $("[data-wish-label]", b);
        if (label) label.textContent = on ? "Saved to wishlist" : "Add to wishlist";
        else if (b.getAttribute("aria-label")) b.setAttribute("aria-label", b.getAttribute("aria-label").replace(/^(Add to|Remove from) wishlist/, on ? "Remove from wishlist" : "Add to wishlist"));
      });
    },
  };
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-wish]");
    if (!b) return;
    ev.preventDefault();
    const k = b.dataset.wish;
    wish.has(k) ? wish.delete(k) : wish.add(k);
    store.set(WKEY, [...wish]);
    Wish.sync();
    announce(wish.has(k) ? "Saved to your wishlist" : "Removed from your wishlist");
  });
  addEventListener("storage", (ev) => { if (ev.key === WKEY) { wish = new Set(store.get(WKEY, [])); Wish.sync(); } });
  Wish.sync();

  /* ── Newsletter ────────────────────────────────────────────────────────── */
  const news = $("[data-news]");
  if (news) {
    news.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const input = $("#news-email", news), out = $("#news-err", news);
      const email = input.value.trim();
      out.classList.remove("is-ok");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        input.setAttribute("aria-invalid", "true");
        out.textContent = "Enter your email address, like name@example.com";
        input.focus();
        return;
      }
      input.setAttribute("aria-invalid", "false");
      const interests = $$('input[name="interest"]:checked', news).map((i) => i.value);
      // Connect your email provider here: window.A88.subscribe = async (email, interests) => { ... }
      try { if (typeof window.A88.subscribe === "function") await window.A88.subscribe(email, interests); }
      catch { out.textContent = "That didn't go through. Please try again."; return; }
      out.classList.add("is-ok");
      out.textContent = "Thanks. You're on the list.";
      news.reset();
    });
  }

  /* ── Hero film: loads the right cut for the screen, pausable, skipped for reduced motion ──────────── */
  $$("[data-hero-video]").forEach((v) => {
    const btn = v.parentElement.querySelector("[data-playpause]");
    if (reduced.matches) { btn?.remove(); return; }
    const pick = () => {
      const src = desktop.matches ? v.dataset.srcDesktop : v.dataset.srcMobile;
      if (v.getAttribute("src") !== src) { v.setAttribute("src", src); v.poster = desktop.matches ? v.getAttribute("poster") : v.dataset.posterMobile; v.play().catch(() => {}); }
    };
    pick();
    desktop.addEventListener("change", pick);
    v.addEventListener("playing", () => v.classList.add("is-playing"));
    let userPaused = false;
    btn?.addEventListener("click", () => {
      userPaused = !v.paused;
      v.paused ? v.play() : v.pause();
      btn.classList.toggle("is-paused", userPaused);
      btn.setAttribute("aria-label", userPaused ? "Play the film" : "Pause the film");
    });
    new IntersectionObserver(([en]) => { if (!userPaused) en.isIntersecting ? v.play().catch(() => {}) : v.pause(); }).observe(v);
  });

  /* ── Carousels: arrow buttons scroll one viewport ─────────────────────── */
  $$("[data-carousel]").forEach((c) => {
    const track = $("[data-carousel-track]", c), prev = $("[data-carousel-prev]", c), next = $("[data-carousel-next]", c);
    const paint = () => {
      prev.disabled = track.scrollLeft <= 4;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
    };
    prev.addEventListener("click", () => track.scrollBy({ left: -track.clientWidth * 0.9 }));
    next.addEventListener("click", () => track.scrollBy({ left: track.clientWidth * 0.9 }));
    track.addEventListener("scroll", paint, { passive: true });
    addEventListener("resize", paint);
    paint();
  });

  /* ── Promotion tracking: GA4 view_promotion / select_promotion, if a tag manager is present ────────── */
  if (window.dataLayer) {
    const io = new IntersectionObserver((ens) => ens.forEach((en) => {
      if (!en.isIntersecting) return;
      io.unobserve(en.target);
      window.dataLayer.push({ event: "view_promotion", ecommerce: { items: [JSON.parse(en.target.dataset.promo)] } });
    }), { threshold: 0.5 });
    $$("[data-promo]").forEach((el) => {
      io.observe(el);
      el.addEventListener("click", (ev) => { if (ev.target.closest("a")) window.dataLayer.push({ event: "select_promotion", ecommerce: { items: [JSON.parse(el.dataset.promo)] } }); });
    });
  }

  window.A88 = Object.assign(window.A88 || {}, { cfg, $, $$, money, esc, icon, store, announce, openDialog, closeDialog, Bag, Wish, thumb, desktop, fine, reduced });
})();
