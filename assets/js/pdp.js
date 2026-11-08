/* Archive 88: product detail page.
   The size x colour variant matrix (#variant-matrix, written by build.py) drives everything: which sizes are
   available in the chosen colour, stock messages, the gallery set, the mobile sticky bar and the size sheet.
   Selection lives in the URL (?colour=olive&size=M) so a shared link opens the exact variant. */
(() => {
  "use strict";
  const { $, $$, esc, Drawer, Cart, cfg } = window.A88S;
  const pdp = $("[data-pdp]");
  if (!pdp) return;
  const M = JSON.parse($("#variant-matrix").textContent);
  const form = $("[data-buy]", pdp);
  const sizeSet = $('[data-option="size"]', form);
  const sizeMsg = $("[data-size-msg]", form);
  const stockMsg = $("[data-stock-msg]", form);
  const atc = $("[data-atc]", form);
  const sticky = $("[data-sticky-atc]");
  const stickyBtn = $("[data-sticky-btn]");
  const sheet = document.getElementById("size-sheet");
  const atcLabel = atc.innerHTML;

  const colour = () => M.colours.find((c) => c.h === form.colour.value) || M.colours[0];
  const size = () => (form.querySelector('input[name="size"]:checked') || {}).value || "";
  const units = (c, s) => (M.stock[c] || {})[s] || 0;

  function syncSizes() {
    const c = colour().h;
    $$('input[name="size"]', form).forEach((input) => {
      const n = units(c, input.value);
      input.disabled = n === 0;
      input.closest(".size-opt").classList.toggle("is-low", n > 0 && n <= cfg.lowStock);
      input.setAttribute("aria-label", `${input.value}${n === 0 ? ", sold out" : n <= cfg.lowStock ? `, only ${n} left` : ""}`);
    });
  }

  function update({ push = true } = {}) {
    const c = colour(), s = size();
    $("[data-colour-name]", form).textContent = c.n;
    $("[data-size-name]", form).textContent = s;
    // gallery: show this colour's set
    $$(".gallery__set", pdp).forEach((set) => (set.hidden = set.dataset.colour !== c.h));
    updatePager();
    // stock message
    const n = s ? units(c.h, s) : 0;
    stockMsg.className = "stock-msg";
    if (!s) stockMsg.textContent = "";
    else if (n <= cfg.lowStock) { stockMsg.textContent = `Only ${n} left in ${s}`; stockMsg.classList.add("is-low"); }
    else { stockMsg.textContent = "In stock. Dispatched in 1 to 2 working days"; stockMsg.classList.add("is-in"); }
    const all = M.sizes.every((x) => units(c.h, x) === 0);
    atc.disabled = all;
    atc.innerHTML = all ? `<span class="buy-btn__price">Sold out in ${esc(c.n)}</span>` : atcLabel;
    // sticky bar
    $("[data-sticky-variant]").textContent = [c.n, s].filter(Boolean).join(", ");
    $("[data-sticky-label]", stickyBtn).textContent = all ? "Sold out" : s ? "Add to bag" : "Select size";
    stickyBtn.disabled = all;
    if (push) {
      const url = new URL(location.href);
      url.searchParams.set("colour", c.h);
      s ? url.searchParams.set("size", s) : url.searchParams.delete("size");
      history.replaceState(null, "", url);
    }
  }

  function setInvalid(on) {
    sizeSet.classList.toggle("is-invalid", on);
    sizeMsg.textContent = on ? "Select a size to add this to your bag" : "";
  }

  form.addEventListener("change", (ev) => {
    if (ev.target.name === "colour") {
      const prev = size();
      syncSizes();
      if (prev && units(colour().h, prev) === 0) {
        form.querySelector('input[name="size"]:checked').checked = false;
        sizeMsg.textContent = `${prev} is sold out in ${colour().n}. Choose another size.`;
      } else if (!sizeSet.classList.contains("is-invalid")) sizeMsg.textContent = "";
    }
    if (ev.target.name === "size") setInvalid(false);
    update();
  });

  function item(s) {
    const c = colour();
    return {
      sku: `${M.style}-${c.h.toUpperCase()}-${s}`, handle: M.handle, title: M.title,
      url: `products/${M.handle}/?colour=${c.h}`, price: M.price, colour: c.h, colourName: c.n, hex: c.hex, size: s,
      sil: M.sil, img: c.img || null, max: units(c.h, s), variantId: M.ids[`${c.h}/${s}`] || null,
    };
  }
  function addSelected(opener) {
    const s = size();
    if (!s) return false;
    if (Cart.add(item(s), { opener })) {
      atc.classList.add("is-added");
      $("[data-atc-label]", atc).textContent = "In bag";
      setTimeout(() => { atc.classList.remove("is-added"); update({ push: false }); }, 1400);
    }
    return true;
  }
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (!addSelected(atc)) {
      setInvalid(true);
      const first = form.querySelector('input[name="size"]:not(:disabled)');
      sizeSet.scrollIntoView({ block: "center", behavior: window.A88S.reduced.matches ? "auto" : "smooth" });
      first?.focus({ preventScroll: true });
    }
  });

  /* Mobile sticky Add to bag: visible whenever the main button is off screen. */
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([entry]) => {
      const show = !entry.isIntersecting;
      if (show) sticky.hidden = false;
      requestAnimationFrame(() => sticky.classList.toggle("is-visible", show));
      document.body.classList.toggle("has-sticky-atc", show);
      sticky.toggleAttribute("inert", !show);
    }, { threshold: 0 }).observe(atc);
  }
  stickyBtn.addEventListener("click", () => {
    if (size()) { addSelected(stickyBtn); return; }
    // No size yet: open a bottom sheet with this colour's sizes, so the shopper never has to scroll back up.
    const c = colour();
    $("[data-size-sheet]", sheet).innerHTML = `<p class="size-sheet__note">Colour: ${esc(c.n)}</p>` + M.sizes.map((s) => {
      const n = units(c.h, s);
      return `<button type="button" data-pick="${esc(s)}" ${n ? "" : "disabled"} aria-label="${esc(s)}${n ? (n <= cfg.lowStock ? `, only ${n} left` : "") : ", sold out"}">${esc(s)}</button>`;
    }).join("");
    Drawer.open(sheet, stickyBtn);
  });
  sheet.addEventListener("click", (ev) => {
    const pick = ev.target.closest("[data-pick]");
    if (!pick) return;
    const input = form.querySelector(`input[name="size"][value="${CSS.escape(pick.dataset.pick)}"]`);
    input.checked = true;
    setInvalid(false);
    update();
    Drawer.close(sheet);
    addSelected(stickyBtn);
  });

  /* Gallery pager (phones: swipe carousel) */
  function updatePager() {
    const set = $(".gallery__set:not([hidden])", pdp);
    if (!set) return;
    const i = Math.round(set.scrollLeft / Math.max(1, set.clientWidth));
    $("[data-gallery-index]", pdp).textContent = Math.min(i + 1, set.children.length);
    $("[data-gallery-total]", pdp).textContent = set.children.length;
  }
  $$(".gallery__set", pdp).forEach((set) => set.addEventListener("scroll", updatePager, { passive: true }));

  /* Restore selection from the URL */
  const p = new URLSearchParams(location.search);
  const wantColour = p.get("colour"), wantSize = p.get("size");
  if (wantColour && M.colours.some((c) => c.h === wantColour)) form.querySelector(`input[name="colour"][value="${CSS.escape(wantColour)}"]`).checked = true;
  syncSizes();
  if (wantSize) {
    const input = form.querySelector(`input[name="size"][value="${CSS.escape(wantSize)}"]`);
    if (input && !input.disabled) input.checked = true;
  }
  update({ push: false });
})();
