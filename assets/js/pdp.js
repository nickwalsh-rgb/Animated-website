/* Archive 88: product page.
   - Colour: each colour has its own address (?colour=), switched in place
   - Size: radio tiles; the button reads "Choose size" (disabled look) until a size is picked, then "Add to bag"
   - Sticky purchase bar once the main button scrolls away (IntersectionObserver)
   - Gallery: two-column grid on desktop, swipe with a 1/4 counter on phones, full-screen viewer with zoom and keys
   - Size guide: two tabs, measurements per size, hover a row to highlight it on the drawing */
(() => {
  "use strict";
  const { $, $$, Bag, Wish, openDialog, announce } = window.A88;
  const page = $("[data-pdp]");
  if (!page) return;
  const P = JSON.parse($("#product-data").textContent);
  const LOW = window.A88.cfg.low;
  const form = $("[data-buy]", page), msg = $("[data-buy-msg]", form), atc = $("[data-atc]", form), atcLabel = $("[data-atc-label]", form);
  const bar = $("[data-pbar]"), barBtn = $("[data-pbar-btn]");
  let colour = P.colours[0].h;

  /* ── Colour ────────────────────────────────────────────────────────────── */
  function setColour(h, { push = false } = {}) {
    const c = P.colours.find((x) => x.h === h) || P.colours[0];
    colour = c.h;
    $$("[data-gal-set]", page).forEach((s) => (s.hidden = s.dataset.galSet !== c.h));
    $$("[data-swatch]", page).forEach((a) => (a.dataset.swatch === c.h ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current")));
    $("[data-colour-name]", page).textContent = c.n;
    const wl = $(".wishlink", page);
    wl.dataset.wish = `${P.handle}/${c.h}`;
    Wish.sync(page);
    const stock = P.stock[c.h];
    $$('input[name="size"]', form).forEach((r) => {
      r.disabled = !(stock[r.value] > 0);
      r.closest(".size").classList.toggle("is-low", stock[r.value] > 0 && stock[r.value] <= LOW);
      if (r.disabled && r.checked) r.checked = false;
    });
    paintButton();
    const set = currentSet();
    $("[data-gal-total]", page).textContent = $$(".gal__slide", set).length;
    $("[data-gal-index]", page).textContent = "1";
    set.scrollLeft = 0;
    const url = new URL(location.href);
    c.h === P.colours[0].h ? url.searchParams.delete("colour") : url.searchParams.set("colour", c.h);
    history[push ? "pushState" : "replaceState"](null, "", url.pathname + url.search);
  }
  const currentSet = () => $(`[data-gal-set="${CSS.escape(colour)}"]`, page);
  $$("[data-swatch]", page).forEach((a) => a.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (a.dataset.swatch !== colour) { setColour(a.dataset.swatch, { push: true }); announce(`Colour: ${$("[data-colour-name]", page).textContent}`); }
  }));
  addEventListener("popstate", () => setColour(new URLSearchParams(location.search).get("colour") || P.colours[0].h));

  /* ── Size and add to bag ───────────────────────────────────────────────── */
  const chosen = () => $('input[name="size"]:checked', form)?.value;
  function paintButton() {
    const s = chosen();
    atc.setAttribute("aria-disabled", String(!s));
    atcLabel.textContent = s ? "Add to bag" : "Choose size";
    barBtn.textContent = s ? "Add to bag" : "Choose size";
    msg.textContent = "";
    if (s) {
      const n = P.stock[colour][s];
      if (n <= LOW) msg.textContent = n === 1 ? "Only 1 left in stock" : `Only ${n} left in stock`;
    }
  }
  form.addEventListener("change", (ev) => { if (ev.target.name === "size") paintButton(); });
  function add() {
    const s = chosen();
    if (!s) {
      msg.textContent = "Choose a size";
      const first = $('input[name="size"]:not(:disabled)', form);
      first?.closest(".sizes").scrollIntoView({ block: "center", behavior: "smooth" });
      first?.focus({ preventScroll: true });
      return;
    }
    const c = P.colours.find((x) => x.h === colour);
    Bag.add({ sku: `${P.style}-${c.h.toUpperCase()}-${s}`, handle: P.handle, title: P.title, url: P.url + (c.h === P.colours[0].h ? "" : `?colour=${c.h}`),
      price: P.price, colour: c.h, colourName: c.n, hex: c.hex, size: s, sil: P.sil, img: c.img, max: P.stock[c.h][s], id: P.ids[`${c.h}/${s}`] || null });
  }
  form.addEventListener("submit", (ev) => { ev.preventDefault(); add(); });
  barBtn.addEventListener("click", add);

  /* Sticky purchase bar: shown once the main button has scrolled up out of view */
  new IntersectionObserver(([en]) => {
    const show = !en.isIntersecting && en.boundingClientRect.top < 0;
    bar.classList.toggle("is-visible", show);
    bar.setAttribute("aria-hidden", String(!show));
    barBtn.tabIndex = show ? 0 : -1;
  }).observe(atc);

  /* ── Gallery counter (phones) ──────────────────────────────────────────── */
  $$("[data-gal-set]", page).forEach((set) => set.addEventListener("scroll", () => {
    const i = Math.round(set.scrollLeft / set.clientWidth) + 1;
    $("[data-gal-index]", page).textContent = i;
  }, { passive: true }));

  /* ── Full-screen gallery ───────────────────────────────────────────────── */
  const fs = $("[data-fs]");
  const stage = $("[data-fs-stage]", fs), thumbs = $("[data-fs-thumbs]", fs);
  let fsIndex = 0, zoom = 1, frames = [];
  function fsShow(i) {
    fsIndex = (i + frames.length) % frames.length;
    zoom = 1;
    stage.innerHTML = "";
    const art = frames[fsIndex].querySelector(".art").cloneNode(true);
    art.removeAttribute("loading");
    stage.append(art);
    $$("button", thumbs).forEach((b, n) => b.setAttribute("aria-current", String(n === fsIndex)));
    $("[data-fs-index]", fs).textContent = fsIndex + 1;
  }
  function setZoom(z) {
    zoom = Math.min(3, Math.max(1, z));
    const art = $(".art", stage);
    if (art) art.style.transform = `scale(${zoom})`;
  }
  page.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-gal-open]");
    if (!btn) return;
    frames = $$(".gal__frame", currentSet());
    thumbs.innerHTML = frames.map((f, n) => `<li><button type="button" aria-label="Image ${n + 1}">${f.querySelector(".art").outerHTML.replace(/role="img" aria-label="[^"]*"/, 'aria-hidden="true"')}</button></li>`).join("");
    $("[data-fs-total]", fs).textContent = frames.length;
    openDialog("fullscreen", btn);
    fsShow(Number(btn.dataset.galOpen));
    stage.focus();
  });
  thumbs.addEventListener("click", (ev) => { const b = ev.target.closest("button"); if (b) fsShow($$("button", thumbs).indexOf(b)); });
  $$("[data-fs-zoom]", fs).forEach((b) => b.addEventListener("click", () => setZoom(zoom + (b.dataset.fsZoom === "in" ? 0.5 : -0.5))));
  fs.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowRight") { ev.preventDefault(); fsShow(fsIndex + 1); }
    else if (ev.key === "ArrowLeft") { ev.preventDefault(); fsShow(fsIndex - 1); }
    else if (ev.key === "+" || ev.key === "=") setZoom(zoom + 0.5);
    else if (ev.key === "-") setZoom(zoom - 0.5);
  });
  stage.addEventListener("click", () => setZoom(zoom > 1 ? 1 : 2));

  /* ── Size guide ────────────────────────────────────────────────────────── */
  const sg = $("[data-sg]");
  if (sg) {
    const data = JSON.parse($("#size-data").textContent);
    const tabs = $$('[role="tab"]', sg);
    const select = (t) => {
      tabs.forEach((x) => {
        const on = x === t;
        x.setAttribute("aria-selected", String(on));
        x.tabIndex = on ? 0 : -1;
        document.getElementById(x.getAttribute("aria-controls")).hidden = !on;
      });
      t.focus();
    };
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t));
      t.addEventListener("keydown", (ev) => {
        if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") { ev.preventDefault(); select(tabs[(i + (ev.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length]); }
      });
    });
    const setSize = (s) => {
      $$("[data-sg-size]", sg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sgSize === s)));
      data.values[s].forEach((v, i) => ($(`[data-sg-val="${i}"]`, sg).textContent = `${v} cm`));
    };
    sg.addEventListener("click", (ev) => { const b = ev.target.closest("[data-sg-size]"); if (b) setSize(b.dataset.sgSize); });
    const mark = (i) => {
      $$("[data-sg-row]", sg).forEach((r) => r.classList.toggle("is-on", r.dataset.sgRow === String(i)));
      $$("[data-sg-mark]", sg).forEach((m) => m.classList.toggle("is-on", m.dataset.sgMark === String(i)));
    };
    $$("[data-sg-row]", sg).forEach((r) => {
      r.addEventListener("mouseenter", () => mark(r.dataset.sgRow));
      r.addEventListener("mouseleave", () => mark(-1));
    });
    $("#size-guide").addEventListener("dialog:open", () => { const s = chosen(); if (s && data.values[s]) setSize(s); });
  }

  setColour(new URLSearchParams(location.search).get("colour") || P.colours[0].h);
})();
