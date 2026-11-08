/* Archive 88: shared runtime.
   - Drawer: one controller for every slide-out panel (bag, menu, filters, size sheet)
   - Cart: bag state (localStorage, synced across tabs), drawer rendering, free-shipping meter
   - Cards: colour swatches and quick add on product cards (PLP, home, recommendations)
   Exposes window.A88S for plp.js and pdp.js. No dependencies. */
(() => {
  "use strict";
  const cfg = JSON.parse(document.getElementById("store-config").textContent);
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const fmt = new Intl.NumberFormat(cfg.locale, { style: "currency", currency: cfg.currency, maximumFractionDigits: 0 });
  const money = (n) => fmt.format(n);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (n) => `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-${n}"/></svg>`;

  /* ── Toast / announcements ─────────────────────────────────────────────── */
  const toastEl = $("[data-toast]");
  let toastTimer;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 2600);
  }

  const Mega = { close() {} }; // replaced below once the header is wired

  /* ── Drawer ────────────────────────────────────────────────────────────── */
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
  const stack = [];
  /* Everything except the open drawer becomes inert (no clicks, focus or screen reader). Walks up from the drawer
     and inerts each sibling on the way, so a drawer that lives inside <main> (the PLP filters) stays usable.
     Live regions are left alone so announcements still read. Returns what it changed, to undo on close. */
  function inertAround(el) {
    const changed = [];
    for (let node = el; node && node.parentElement && node !== document.body; node = node.parentElement) {
      for (const sib of node.parentElement.children) {
        if (sib === node || sib.inert || sib.matches("script, template, [aria-live], [role=status]")) continue;
        sib.setAttribute("inert", "");
        changed.push(sib);
      }
    }
    return changed;
  }
  const Drawer = {
    open(el, opener) {
      if (!el || el.classList.contains("is-open")) return;
      el._opener = opener || document.activeElement;
      const persistent = el.hasAttribute("data-drawer-persistent");
      if (persistent) { el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); }
      el.hidden = false;
      void el.offsetWidth; // let the closed state paint so the panel slides in
      el.classList.add("is-open");
      stack.push(el);
      document.body.classList.add("is-locked");
      el._inerted = inertAround(el);
      Mega.close({ restore: false });
      if (el._opener && el._opener.setAttribute) el._opener.setAttribute("aria-expanded", "true");
      const panel = $(".drawer__panel", el);
      requestAnimationFrame(() => panel.focus({ preventScroll: true }));
      el.dispatchEvent(new CustomEvent("drawer:open", { bubbles: true }));
    },
    close(el) {
      if (!el || !el.classList.contains("is-open")) return;
      el.classList.remove("is-open");
      stack.splice(stack.indexOf(el), 1);
      if (!stack.length) document.body.classList.remove("is-locked");
      (el._inerted || []).forEach((n) => n.removeAttribute("inert"));
      el._inerted = null;
      const persistent = el.hasAttribute("data-drawer-persistent");
      const done = () => {
        if (el.classList.contains("is-open")) return;
        if (persistent) { el.removeAttribute("role"); el.removeAttribute("aria-modal"); } else el.hidden = true;
      };
      reduced.matches ? done() : setTimeout(done, 240);
      if (el._opener && el._opener.focus) { el._opener.setAttribute?.("aria-expanded", "false"); el._opener.focus({ preventScroll: true }); }
      el.dispatchEvent(new CustomEvent("drawer:close", { bubbles: true }));
    },
    top: () => stack[stack.length - 1],
  };
  document.addEventListener("click", (ev) => {
    const opener = ev.target.closest("[data-drawer-open]");
    if (opener) { ev.preventDefault(); Drawer.open(document.getElementById(opener.dataset.drawerOpen), opener); return; }
    const closer = ev.target.closest("[data-drawer-close]");
    if (closer) Drawer.close(closer.closest(".drawer"));
  });
  document.addEventListener("keydown", (ev) => {
    const top = Drawer.top();
    if (!top) return;
    if (ev.key === "Escape") { ev.preventDefault(); Drawer.close(top); return; }
    if (ev.key !== "Tab") return;
    const items = $$(FOCUSABLE, $(".drawer__panel", top)).filter((n) => n.offsetParent !== null);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (ev.shiftKey && (document.activeElement === first || document.activeElement === $(".drawer__panel", top))) { ev.preventDefault(); last.focus(); }
    else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
  });
  // A persistent drawer (PLP filters) becomes a plain sidebar at desktop width: close it if the viewport grows.
  matchMedia("(min-width: 1000px)").addEventListener("change", (m) => { if (m.matches) $$(".drawer--inline.is-open").forEach((d) => Drawer.close(d)); });

  /* ── Cart ──────────────────────────────────────────────────────────────── */
  const KEY = "a88.store.bag.v1";
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; } };
  let lines = read();
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(lines)); } catch { /* private mode: bag lasts this page */ } };
  const cartEl = document.getElementById("cart");
  const listEl = $("[data-cart-lines]", cartEl);

  const Cart = {
    get lines() { return lines; },
    count: () => lines.reduce((n, l) => n + l.qty, 0),
    subtotal: () => lines.reduce((n, l) => n + l.qty * l.price, 0),
    /** item: {sku, handle, title, url, price, colour, colourName, hex, size, sil, img, max} */
    add(item, { open = true, opener } = {}) {
      const existing = lines.find((l) => l.sku === item.sku);
      if (existing) {
        if (existing.qty >= existing.max) { toast(`Only ${existing.max} available in ${item.size}`); return false; }
        existing.qty += 1;
      } else lines.unshift({ ...item, qty: 1 });
      save(); render(item.sku);
      const btn = $("[data-bag-btn]");
      btn.classList.remove("is-bump"); void btn.offsetWidth; btn.classList.add("is-bump");
      navigator.vibrate?.(8);
      if (open) Drawer.open(cartEl, opener || btn);
      announce(`Added ${item.title}, ${item.colourName}, size ${item.size} to your bag`);
      return true;
    },
    setQty(sku, qty) {
      const l = lines.find((x) => x.sku === sku);
      if (!l) return;
      if (qty <= 0) lines = lines.filter((x) => x.sku !== sku);
      else l.qty = Math.min(qty, l.max);
      save(); render();
    },
  };
  const live = document.createElement("p");
  live.className = "sr-only"; live.setAttribute("aria-live", "polite");
  document.body.append(live);
  function announce(msg) { live.textContent = ""; setTimeout(() => (live.textContent = msg), 30); }

  function thumb(l) {
    const inner = l.img
      ? `<img class="media__item" src="${esc(l.img)}" alt="" width="88" height="110" loading="lazy">`
      : `<svg class="media__item media__art" viewBox="0 0 400 500" aria-hidden="true" style="color:${esc(l.hex)}"><use href="#s-${esc(l.sil)}" width="400" height="500"/></svg>`;
    return `<a class="media" href="${esc(cfg.root + l.url)}" tabindex="-1" aria-hidden="true">${inner}</a>`;
  }
  function render(newSku) {
    const count = Cart.count();
    $$("[data-bag-count]").forEach((n) => { n.textContent = count; n.toggleAttribute("data-empty", count === 0); });
    $$("[data-bag-btn]").forEach((b) => b.setAttribute("aria-label", `Bag, ${count} ${count === 1 ? "item" : "items"}`));
    $("[data-drawer-count]", cartEl).textContent = count ? `(${count})` : "";
    $("[data-cart-empty]", cartEl).hidden = lines.length > 0;
    $(".drawer__foot", cartEl).hidden = lines.length === 0;
    // Gift cards don't ship as goods, so they don't count toward free delivery.
    const goods = lines.filter((l) => !l.gift);
    $("[data-ship-meter]", cartEl).hidden = goods.length === 0;
    listEl.innerHTML = lines.map((l) => `
      <li class="cart-line" data-sku="${esc(l.sku)}" ${l.sku === newSku ? "" : 'style="animation:none"'}>
        ${thumb(l)}
        <div>
          <div class="cart-line__top"><p class="cart-line__title"><a href="${esc(cfg.root + l.url)}">${esc(l.title)}</a></p><p>${money(l.price * l.qty)}</p></div>
          <p class="cart-line__meta">${esc(l.colourName)} · ${esc(l.size)}</p>
          ${l.qty >= l.max ? `<p class="cart-line__warn">${l.max <= cfg.lowStock ? `Only ${l.max} left` : "Maximum quantity"}</p>` : ""}
          <div class="cart-line__row">
            <div class="qty" role="group" aria-label="Quantity, ${esc(l.title)}">
              <button type="button" data-qty="-1" aria-label="Decrease quantity">${icon("minus")}</button>
              <output aria-live="polite">${l.qty}</output>
              <button type="button" data-qty="1" aria-label="Increase quantity" ${l.qty >= l.max ? "disabled" : ""}>${icon("plus")}</button>
            </div>
            <button type="button" class="cart-line__remove" data-remove>Remove</button>
          </div>
        </div>
      </li>`).join("");
    $("[data-cart-subtotal]", cartEl).textContent = money(Cart.subtotal());
    const sub = goods.reduce((n, l) => n + l.qty * l.price, 0), th = cfg.freeShipping, meter = $("[data-ship-meter]", cartEl);
    const left = th - sub;
    $("[data-ship-text]", cartEl).innerHTML = left > 0
      ? `You're <strong>${money(left)}</strong> away from free UK delivery`
      : `<strong>Free UK delivery</strong> on this order`;
    $("[data-ship-bar]", cartEl).style.transform = `scaleX(${Math.min(1, sub / th)})`;
    meter.classList.toggle("is-met", left <= 0);
  }
  listEl.addEventListener("click", (ev) => {
    const line = ev.target.closest(".cart-line");
    if (!line) return;
    const sku = line.dataset.sku, l = lines.find((x) => x.sku === sku);
    const q = ev.target.closest("[data-qty]");
    if (q) {
      const idx = $$(".cart-line", listEl).indexOf(line);
      Cart.setQty(sku, l.qty + Number(q.dataset.qty));
      // keep focus on the stepper (render replaced the node)
      const again = $$(".cart-line", listEl)[idx];
      (again && $(`[data-qty="${q.dataset.qty}"]:not(:disabled)`, again) || again && $("[data-qty]", again) || $(".drawer__panel", cartEl)).focus();
    }
    if (ev.target.closest("[data-remove]")) {
      const removed = { ...l };
      Cart.setQty(sku, 0);
      $(".drawer__panel", cartEl).focus();
      announce(`Removed ${removed.title} from your bag`);
    }
  });
  $("[data-checkout]", cartEl).addEventListener("click", (ev) => {
    const msg = $("[data-checkout-msg]", cartEl);
    const ids = lines.map((l) => l.variantId && `${l.variantId}:${l.qty}`);
    if (cfg.shopify && ids.every(Boolean)) { location.href = `https://${cfg.shopify}/cart/${ids.join(",")}`; return; }
    msg.textContent = "Checkout opens once the store is connected to Shopify.";
    ev.currentTarget.focus();
  });
  addEventListener("storage", (ev) => { if (ev.key === KEY) { lines = read(); render(); } });
  render();

  /* ── Product cards: swatches + quick add ───────────────────────────────── */
  function cardState(card) {
    if (!card._colours) card._colours = JSON.parse(card.dataset.colours);
    return card._colours;
  }
  function setCardColour(card, handle) {
    const colours = cardState(card);
    const c = colours.find((x) => x.h === handle) || colours[0];
    card.dataset.active = c.h;
    $$(".swatch", card).forEach((s) => s.setAttribute("aria-pressed", String(s.dataset.colour === c.h)));
    const name = $("[data-card-colour]", card);
    if (name) name.textContent = c.n;
    const items = $$(".media__item", card);
    items.forEach((item, i) => {
      if (item.tagName === "svg") item.style.color = c.hex;
      else if (c.img) {
        const src = $("source", item), img = $("img", item);
        if (src) src.srcset = c.img[i] || c.img[0];
        if (img) { img.src = c.src[i] || c.src[0]; }
      }
      const label = item.getAttribute("aria-label") || ($("img", item)?.alt ?? "");
      const next = label.replace(/ in .+?, /, ` in ${c.n}, `);
      item.tagName === "svg" ? item.setAttribute("aria-label", next) : $("img", item) && ($("img", item).alt = next);
    });
    const link = `${card.dataset.url}?colour=${encodeURIComponent(c.h)}`;
    $$("a", card).forEach((a) => (a.href = link));
    renderQuickAdd(card);
  }
  function renderQuickAdd(card) {
    const qa = $("[data-quick-add]", card);
    if (!qa) return;
    const colours = cardState(card);
    const c = colours.find((x) => x.h === card.dataset.active) || colours[0];
    $(".quick-add__colour", qa).textContent = c.n;
    $(".quick-add__sizes", qa).innerHTML = Object.entries(c.stock).map(([size, n]) =>
      `<button type="button" data-size="${esc(size)}" ${n ? "" : "disabled"} aria-label="Add size ${esc(size)} to bag${n ? "" : ", sold out"}">${esc(size)}</button>`).join("");
  }
  function cardItem(card, size) {
    const colours = cardState(card);
    const c = colours.find((x) => x.h === card.dataset.active) || colours[0];
    return {
      sku: `${card.dataset.style}-${c.h.toUpperCase()}-${size}`, handle: card.dataset.product, title: card.dataset.title,
      url: card.dataset.url.replace(cfg.root, "") + `?colour=${c.h}`, price: Number(card.dataset.price),
      colour: c.h, colourName: c.n, hex: c.hex, size, sil: card.dataset.sil, img: c.src ? c.src[0] : null, max: c.stock[size],
    };
  }
  document.addEventListener("click", (ev) => {
    const sw = ev.target.closest(".card .swatch");
    if (sw) { ev.preventDefault(); setCardColour(sw.closest(".card"), sw.dataset.colour); return; }
    const qa = ev.target.closest(".quick-add__sizes button");
    if (qa) {
      const card = qa.closest(".card");
      if (Cart.add(cardItem(card, qa.dataset.size), { opener: qa })) {
        qa.classList.add("is-added");
        setTimeout(() => qa.classList.remove("is-added"), 1200);
      }
    }
  });
  // Build quick-add rows lazily, on first hover/focus, so 100 cards cost nothing up front.
  const prime = (ev) => {
    const card = ev.target.closest?.(".card");
    if (card && !card._primed) { card._primed = true; if (!card.dataset.active) card.dataset.active = cardState(card)[0].h; renderQuickAdd(card); }
  };
  document.addEventListener("pointerover", prime, { passive: true });
  document.addEventListener("focusin", prime);

  /* ── Nav tone: inverts over dark sections ([data-nav="dark"]) ───────────
     Checks which section sits under the middle of the header, measured where the header actually is (it starts
     below the announcement bar, then sticks to the top). Over imagery that asks for it ([data-nav-clear]) the
     header goes see-through with light type; over other dark sections it is a solid ink bar. */
  const navEl = $(".nav");
  const darks = $$('[data-nav="dark"]');
  if (navEl && darks.length) {
    let queued = false;
    const tone = () => {
      queued = false;
      const r = navEl.getBoundingClientRect();
      const y = r.top + r.height / 2;
      const under = darks.find((d) => { const box = d.getBoundingClientRect(); return box.top <= y && box.bottom > y; });
      document.body.classList.toggle("nav-on-dark", !!under);
      document.body.classList.toggle("nav-clear", !!under && under.hasAttribute("data-nav-clear"));
    };
    const queue = () => { if (!queued) { queued = true; requestAnimationFrame(tone); } };
    addEventListener("scroll", queue, { passive: true });
    addEventListener("resize", queue);
    tone();
  }

  /* ── Announcement bar: rotates every 6s, pauses on hover/focus or with the pause button ── */
  const bar = $("[data-announce]");
  if (bar) {
    const items = $$(".announce__item", bar);
    const pauseBtn = $("[data-announce-pause]", bar);
    let i = 0, timer = null, userPaused = reduced.matches, hover = false;
    const show = (n) => {
      i = (n + items.length) % items.length;
      items.forEach((it, k) => { it.classList.toggle("is-active", k === i); k === i ? it.removeAttribute("aria-hidden") : it.setAttribute("aria-hidden", "true"); });
      $$("a", bar).forEach((a) => (a.tabIndex = a.closest(".is-active") ? 0 : -1));
    };
    const run = () => { clearInterval(timer); if (!userPaused && !hover && items.length > 1) timer = setInterval(() => show(i + 1), 6000); };
    const syncPause = () => {
      pauseBtn.setAttribute("aria-pressed", String(userPaused));
      $(".sr-only", pauseBtn).textContent = userPaused ? "Play messages" : "Pause messages";
      $("use", pauseBtn).setAttribute("href", userPaused ? "#i-play" : "#i-pause");
    };
    $$("[data-announce-step]", bar).forEach((b) => b.addEventListener("click", () => { show(i + Number(b.dataset.announceStep)); run(); }));
    pauseBtn.addEventListener("click", () => { userPaused = !userPaused; syncPause(); run(); });
    bar.addEventListener("pointerenter", () => { hover = true; run(); });
    bar.addEventListener("pointerleave", () => { hover = false; run(); });
    bar.addEventListener("focusin", () => { hover = true; run(); });
    bar.addEventListener("focusout", () => { hover = false; run(); });
    show(0); syncPause(); run();
  }

  /* ── Mega-menu (desktop): click or hover "Shop"; Esc, click outside or leaving closes it ── */
  const megaBtn = $("[data-mega]"), megaPanel = $("[data-mega-panel]"), megaScrim = $("[data-mega-scrim]");
  if (megaBtn && megaPanel) {
    const fine = matchMedia("(hover: hover) and (pointer: fine)");
    let openTimer, closeTimer;
    const isOpen = () => megaBtn.getAttribute("aria-expanded") === "true";
    const open = () => {
      clearTimeout(closeTimer);
      if (isOpen()) return;
      megaPanel.hidden = false; megaScrim.hidden = false;
      void megaPanel.offsetWidth;
      megaPanel.classList.add("is-open"); megaScrim.classList.add("is-open");
      megaBtn.setAttribute("aria-expanded", "true");
      document.body.classList.add("mega-open");
    };
    Mega.close = ({ restore = false } = {}) => {
      clearTimeout(openTimer);
      if (!isOpen()) return;
      megaPanel.classList.remove("is-open"); megaScrim.classList.remove("is-open");
      megaBtn.setAttribute("aria-expanded", "false");
      document.body.classList.remove("mega-open");
      const done = () => { if (!isOpen()) { megaPanel.hidden = true; megaScrim.hidden = true; } };
      reduced.matches ? done() : setTimeout(done, 220);
      if (restore) megaBtn.focus();
    };
    megaBtn.addEventListener("click", () => (isOpen() ? Mega.close() : open()));
    const zone = [megaBtn, megaPanel];
    zone.forEach((el) => {
      el.addEventListener("pointerenter", (ev) => { if (ev.pointerType === "mouse" && fine.matches) { clearTimeout(closeTimer); openTimer = setTimeout(open, 120); } });
      el.addEventListener("pointerleave", (ev) => { if (ev.pointerType === "mouse") { clearTimeout(openTimer); closeTimer = setTimeout(() => Mega.close(), 220); } });
    });
    megaScrim.addEventListener("click", () => Mega.close());
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && isOpen()) { ev.preventDefault(); Mega.close({ restore: true }); } });
    document.addEventListener("focusin", (ev) => { if (isOpen() && !megaPanel.contains(ev.target) && ev.target !== megaBtn) Mega.close(); });
    matchMedia("(max-width: 999px)").addEventListener("change", (m) => m.matches && Mega.close());
  }

  /* ── Search: loads search.json on first open, matches every word against name, category, colours, cloth ── */
  const searchEl = document.getElementById("search");
  if (searchEl) {
    const form = $("[data-search]", searchEl), input = $("input", form), results = $("[data-search-results]", searchEl);
    const countEl = $("[data-search-count]", searchEl), suggest = $("[data-search-suggest]", searchEl), clear = $("[data-search-clear]", searchEl);
    let index = null, loading = null;
    const load = () => loading || (loading = fetch(cfg.root + "search.json").then((r) => r.json()).then((d) => (index = d.map((x) => ({ ...x, hay: `${x.t} ${x.c} ${x.k}`.toLowerCase() })))).catch(() => (index = [])));
    // One pass over the plain text, so a highlight never lands inside markup added for another word.
    const mark = (text, words) => {
      const re = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "ig");
      return text.split(re).map((part, k) => (k % 2 ? `<mark>${esc(part)}</mark>` : esc(part))).join("");
    };
    const art = (x) => x.i
      ? `<img class="media__item" src="${esc(cfg.root + x.i)}" alt="" loading="lazy">`
      : `<svg class="media__item media__art" viewBox="0 0 400 500" aria-hidden="true" style="color:${esc(x.h)}"><use href="#s-${esc(x.s)}" width="400" height="500"/></svg>`;
    async function find() {
      const q = input.value.trim().toLowerCase();
      clear.hidden = !q;
      suggest.hidden = !!q;
      if (!q) { results.innerHTML = ""; countEl.textContent = ""; return; }
      await load();
      if (input.value.trim().toLowerCase() !== q) return; // a newer query is on its way
      const words = q.split(/\s+/).filter(Boolean);
      // Every word must match somewhere; styles whose name matches come first, then catalogue order.
      const score = (x) => words.filter((w) => x.t.toLowerCase().includes(w)).length * 2 + words.filter((w) => x.c.toLowerCase().includes(w)).length;
      const hits = index.filter((x) => words.every((w) => x.hay.includes(w))).map((x, k) => ({ x, k, s: score(x) }))
        .sort((a, b) => b.s - a.s || a.k - b.k).map((h) => h.x).slice(0, 12);
      countEl.textContent = hits.length ? `${hits.length === 12 ? "Top 12" : hits.length} ${hits.length === 1 ? "result" : "results"} for “${input.value.trim()}”` : `No results for “${input.value.trim()}”. Try a category, a colour or a cloth such as wool.`;
      results.innerHTML = hits.map((x) => `<li><a class="search-hit" href="${esc(cfg.root + x.u)}"><span class="media">${art(x)}</span>
        <span class="search-hit__title">${mark(x.t, words)}</span><span class="search-hit__meta">${esc(x.c)} · ${money(x.p)}${x.n > 1 ? ` · ${x.n} colours` : ""}</span></a></li>`).join("");
      if (!hits.length) suggest.hidden = false;
    }
    let t;
    input.addEventListener("input", () => { clearTimeout(t); t = setTimeout(find, 90); });
    form.addEventListener("submit", (ev) => { ev.preventDefault(); const first = $("a", results); if (first) location.href = first.href; });
    form.addEventListener("reset", () => setTimeout(() => { find(); input.focus(); }));
    searchEl.addEventListener("drawer:open", () => { load(); setTimeout(() => input.focus(), 60); });
  }

  /* ── Rails: previous / next buttons scroll one viewport of cards ── */
  $$("[data-rail]").forEach((rail) => {
    const track = $("[data-rail-track]", rail), prev = $("[data-rail-prev]", rail), next = $("[data-rail-next]", rail);
    const sync = () => {
      prev.disabled = track.scrollLeft < 4;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
    };
    const step = (dir) => track.scrollBy({ left: dir * track.clientWidth * 0.9, behavior: reduced.matches ? "auto" : "smooth" });
    prev.addEventListener("click", () => step(-1));
    next.addEventListener("click", () => step(1));
    track.addEventListener("scroll", () => requestAnimationFrame(sync), { passive: true });
    addEventListener("resize", sync);
    sync();
  });

  /* ── Newsletter sign-up (footer). Hook: set window.A88S.subscribe(email) to return a promise from your email provider. ── */
  const signup = $("[data-signup]");
  if (signup) {
    const input = $("input", signup), msg = $("[data-signup-msg]", signup), btn = $("button", signup);
    const DEFAULT = msg.textContent;
    const valid = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim());
    const state = (name, text) => {
      signup.classList.remove("is-error", "is-done");
      if (name) signup.classList.add("is-" + name);
      input.setAttribute("aria-invalid", String(name === "error"));
      msg.textContent = text;
    };
    input.addEventListener("blur", () => { if (input.value.trim() && !valid(input.value)) state("error", "Enter an email address like name@example.com"); });
    input.addEventListener("input", () => { if (signup.classList.contains("is-error") && valid(input.value)) state(null, DEFAULT); });
    signup.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      if (!valid(input.value)) { state("error", "Enter an email address like name@example.com"); input.focus(); return; }
      btn.setAttribute("aria-disabled", "true"); btn.textContent = "Subscribing";
      try {
        await (window.A88S.subscribe ? window.A88S.subscribe(input.value.trim()) : new Promise((r) => setTimeout(r, 400)));
        state("done", "You're on the list. We'll write when something new lands."); signup.reset();
      } catch { state("error", "Something went wrong on our side. Please try again in a moment."); }
      btn.removeAttribute("aria-disabled"); btn.textContent = "Subscribe";
    });
  }

  window.A88S = { cfg, $, $$, money, esc, icon, toast, announce, Drawer, Cart, setCardColour, reduced };
})();
