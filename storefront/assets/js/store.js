/* Archive 88 storefront: shared runtime.
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

  /* ── Drawer ────────────────────────────────────────────────────────────── */
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
  const stack = [];
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
      $("main")?.setAttribute("inert", "");
      $(".nav")?.setAttribute("inert", "");
      if (el._opener && el._opener.setAttribute) el._opener.setAttribute("aria-expanded", "true");
      const panel = $(".drawer__panel", el);
      requestAnimationFrame(() => panel.focus({ preventScroll: true }));
      el.dispatchEvent(new CustomEvent("drawer:open", { bubbles: true }));
    },
    close(el) {
      if (!el || !el.classList.contains("is-open")) return;
      el.classList.remove("is-open");
      stack.splice(stack.indexOf(el), 1);
      if (!stack.length) {
        document.body.classList.remove("is-locked");
        $("main")?.removeAttribute("inert");
        $(".nav")?.removeAttribute("inert");
      }
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
    $("[data-ship-meter]", cartEl).hidden = lines.length === 0;
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
    const sub = Cart.subtotal(), th = cfg.freeShipping, meter = $("[data-ship-meter]", cartEl);
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
    msg.textContent = "Checkout opens once the store is connected to Shopify (see storefront/docs/DESIGN-SYSTEM.md).";
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

  window.A88S = { cfg, $, $$, money, esc, icon, toast, announce, Drawer, Cart, setCardColour, reduced };
})();
