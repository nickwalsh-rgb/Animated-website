/* Archive 88: product listings (category pages and search results).
   One "Filter" pill opens the filter and sort panel: a floating card under the pill on desktop (no dimmed page),
   a full-screen sheet on phones. Choices are drafted in the panel and applied with "Show N items". Filters, sort
   and page live in the address (?colour=green&size=M&sort=price-asc&page=2), so a listing can be shared and the
   back button works. Pages hold 48 items, as on the original. Facets count colourways (cards), not variants. */
(() => {
  "use strict";
  const { $, $$, esc, icon, desktop, announce, Wish } = window.A88;
  const root = $("[data-listing]") || $("[data-search]");
  const panel = $("[data-filter-panel]");
  if (!root || !panel) return;
  const grid = $("[data-grid]", root);
  const pager = $("[data-pager]");
  const pageSize = Number(root.dataset.pageSize) || Infinity;
  const FAM = { black: ["Black", "#1B211D"], grey: ["Grey", "#8D918C"], white: ["White", "#F4F2EC"], neutral: ["Neutral", "#CFC6B4"],
    brown: ["Brown", "#7A5A40"], green: ["Green", "#4F6248"], blue: ["Blue", "#2F4A6B"], red: ["Red", "#9A3B2E"] };
  const ALPHA = ["XS", "S", "M", "L", "XL", "XXL"];
  const CATS = { outerwear: "Outerwear", knitwear: "Knitwear", shirts: "Shirts", trousers: "Trousers", jersey: "Jersey", tailoring: "Tailoring" };
  const FACETS = [
    { key: "colour", label: "Colour", get: (c) => [c.dataset.colour] },
    { key: "size", label: "Size", get: (c) => c.dataset.sizes.split(",").filter((s) => s && !/^\d+$/.test(s)) },
    { key: "waist", label: "Waist", get: (c) => c.dataset.sizes.split(",").filter((s) => /^\d+$/.test(s)) },
    { key: "fit", label: "Fit", get: (c) => [c.dataset.fit] },
    { key: "fabric", label: "Fabric", get: (c) => [c.dataset.fabric] },
    { key: "category", label: "Category", get: (c) => [c.dataset.cat] },
  ];
  const SORTS = ["new", "relevance", "price-asc", "price-desc"];
  const defaultSort = root.matches("[data-search]") ? "relevance" : "new";

  const cards = () => $$("[data-card]", grid);
  const readState = () => {
    const q = new URLSearchParams(location.search);
    const s = { sort: SORTS.includes(q.get("sort")) ? q.get("sort") : defaultSort, page: Math.max(1, parseInt(q.get("page"), 10) || 1) };
    FACETS.forEach((f) => (s[f.key] = (q.get(f.key) || "").split(",").filter(Boolean)));
    return s;
  };
  let state = readState();
  let draft = null;

  const selectedCount = (s) => FACETS.reduce((n, f) => n + s[f.key].length, 0);
  const matches = (card, s) => FACETS.every((f) => !s[f.key].length || f.get(card).some((v) => s[f.key].includes(v)));
  function sortCards(list, sort) {
    const by = {
      new: (a, b) => b.dataset.new - a.dataset.new || a.dataset.rank - b.dataset.rank,
      relevance: (a, b) => (a.dataset.order ?? a.dataset.rank) - (b.dataset.order ?? b.dataset.rank),
      "price-asc": (a, b) => a.dataset.price - b.dataset.price || a.dataset.rank - b.dataset.rank,
      "price-desc": (a, b) => b.dataset.price - a.dataset.price || a.dataset.rank - b.dataset.rank,
    }[sort];
    return list.sort(by);
  }

  /* Facet options come from the cards on the page, so every listing shows only what it holds */
  function options() {
    const all = cards();
    return FACETS.map((f) => {
      const vals = new Set();
      all.forEach((c) => f.get(c).forEach((v) => v && vals.add(v)));
      let list = [...vals];
      if (f.key === "colour") list = Object.keys(FAM).filter((k) => vals.has(k));
      else if (f.key === "size") list = ALPHA.filter((k) => vals.has(k));
      else if (f.key === "waist") list.sort((a, b) => a - b);
      else list.sort();
      return { ...f, list };
    }).filter((f) => f.list.length > (f.key === "category" || f.key === "fit" || f.key === "fabric" ? 1 : 0));
  }

  function renderFacets() {
    const box = $("[data-facets]", panel);
    box.innerHTML = options().map((f) => {
      const opts = f.list.map((v) => {
        const id = `f-${f.key}-${v}`.replace(/[^a-z0-9-]/gi, "-");
        const checked = draft[f.key].includes(v) ? " checked" : "";
        if (f.key === "colour") {
          const [name, hex] = FAM[v] || [v, "#ccc"];
          return `<label class="fopt fopt--colour" for="${id}"><input type="checkbox" id="${id}" name="${f.key}" value="${esc(v)}"${checked}><span><i style="--sw:${hex}"></i>${esc(name)}</span></label>`;
        }
        const label = f.key === "category" ? (CATS[v] || v) : f.key === "fit" ? `${v} fit` : v;
        return `<label class="fopt" for="${id}"><input type="checkbox" id="${id}" name="${f.key}" value="${esc(v)}"${checked}><span>${esc(label)}</span></label>`;
      }).join("");
      return `<details class="facet"${draft[f.key].length ? " open" : ""}><summary class="facet__sum">${f.label}${draft[f.key].length ? ` (${draft[f.key].length})` : ""}` +
        `${icon("plus").replace('class="icon"', 'class="icon facet__plus"')}${icon("minus").replace('class="icon"', 'class="icon facet__minus"')}</summary>` +
        `<div class="facet__opts${f.key === "colour" ? " facet__opts--colour" : ""}">${opts}</div></details>`;
    }).join("");
  }

  function paintDraft() {
    $$('input[name="sort"]', panel).forEach((r) => (r.checked = r.value === draft.sort));
    const n = cards().filter((c) => matches(c, draft)).length;
    $("[data-filter-total]", panel).textContent = n;
  }

  /* Apply: filter, sort, paginate, then update the pill, the pager and the address */
  function apply({ push = false, scroll = false } = {}) {
    const all = sortCards(cards(), state.sort);
    const hits = all.filter((c) => matches(c, state));
    const pages = Math.max(1, Math.ceil(hits.length / pageSize));
    if (state.page > pages) state.page = pages;
    const start = Number.isFinite(pageSize) ? (state.page - 1) * pageSize : 0;
    const shown = new Set(hits.slice(start, start + pageSize));
    const frag = document.createDocumentFragment();
    all.forEach((c) => { c.hidden = !shown.has(c); frag.append(c); });
    grid.append(frag);

    const n = selectedCount(state);
    $$("[data-filter-label]").forEach((el) => (el.textContent = n ? `${n} Filter${n === 1 ? "" : "s"}` : "Filter"));
    const count = $("[data-result-count]", root);
    if (count) count.textContent = `${hits.length} item${hits.length === 1 ? "" : "s"}`;

    if (pager) {
      pager.hidden = pages < 2;
      const prev = $("[data-pager-prev]", pager), next = $("[data-pager-next]", pager);
      $("[data-pager-current]", pager).textContent = state.page;
      $("[data-pager-total]", pager).textContent = pages;
      prev.href = url({ page: state.page - 1 }); next.href = url({ page: state.page + 1 });
      prev.setAttribute("aria-disabled", String(state.page <= 1));
      next.setAttribute("aria-disabled", String(state.page >= pages));
    }
    const href = url({});
    if (href !== location.pathname + location.search) history[push ? "pushState" : "replaceState"](null, "", href);
    if (scroll) grid.scrollIntoView({ block: "start", behavior: "auto" });
    return hits.length;
  }

  function url(over) {
    const q = new URLSearchParams(location.search);
    const s = { ...state, ...over };
    FACETS.forEach((f) => (s[f.key].length ? q.set(f.key, s[f.key].join(",")) : q.delete(f.key)));
    s.sort !== defaultSort ? q.set("sort", s.sort) : q.delete("sort");
    s.page > 1 ? q.set("page", s.page) : q.delete("page");
    const qs = q.toString();
    return location.pathname + (qs ? `?${qs}` : "");
  }

  /* Panel */
  let opener = null;
  function openPanel(btn) {
    opener = btn;
    draft = JSON.parse(JSON.stringify(state));
    renderFacets();
    paintDraft();
    if (desktop.matches) panel.show(); else { panel.showModal(); document.body.classList.add("is-locked"); }
    $$("[data-filter-open]").forEach((b) => b.setAttribute("aria-expanded", "true"));
    $('input[name="sort"]:checked', panel)?.focus();
  }
  function closePanel() {
    if (!panel.open) return;
    panel.close();
  }
  panel.addEventListener("close", () => {
    document.body.classList.remove("is-locked");
    $$("[data-filter-open]").forEach((b) => b.setAttribute("aria-expanded", "false"));
    if (opener && opener.offsetParent !== null) opener.focus({ preventScroll: true });
  });
  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-filter-open]");
    if (btn) { panel.open ? closePanel() : openPanel(btn); return; }
    if (panel.open && !panel.matches(":modal") && !panel.contains(ev.target)) closePanel();
  });
  panel.addEventListener("keydown", (ev) => { if (ev.key === "Escape") { ev.preventDefault(); closePanel(); } });
  panel.addEventListener("change", (ev) => {
    const t = ev.target;
    if (t.name === "sort") draft.sort = t.value;
    else if (draft[t.name]) {
      draft[t.name] = t.checked ? [...new Set([...draft[t.name], t.value])] : draft[t.name].filter((v) => v !== t.value);
      const sum = t.closest(".facet").querySelector(".facet__sum").firstChild;
      const f = FACETS.find((x) => x.key === t.name);
      sum.textContent = f.label + (draft[t.name].length ? ` (${draft[t.name].length})` : "");
    }
    paintDraft();
  });
  $("[data-filter-clear]", panel).addEventListener("click", () => {
    FACETS.forEach((f) => (draft[f.key] = []));
    renderFacets(); paintDraft();
  });
  $("[data-filter-cancel]", panel).addEventListener("click", closePanel);
  $("[data-filter-apply]", panel).addEventListener("click", () => {
    state = { ...draft, page: 1 };
    const n = apply({ push: true });
    closePanel();
    announce(`Showing ${n} item${n === 1 ? "" : "s"}`);
  });
  desktop.addEventListener("change", closePanel);

  /* Pager: plain links that work without JS; with JS they switch page in place */
  pager?.addEventListener("click", (ev) => {
    const a = ev.target.closest("a");
    if (!a || a.getAttribute("aria-disabled") === "true") return;
    ev.preventDefault();
    state.page += a.matches("[data-pager-next]") ? 1 : -1;
    apply({ push: true, scroll: true });
    $("[data-pager-current]", pager).focus?.();
  });
  addEventListener("popstate", () => { state = readState(); apply(); });

  window.A88.listing = { refresh() { state = readState(); state.page = 1; const n = apply(); Wish.sync(grid); return n; }, apply };
  if (root.matches("[data-listing]")) apply();
})();
