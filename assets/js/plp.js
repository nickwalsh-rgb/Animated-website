/* Archive 88: product listing page.
   Filters (size, colour), sort and "Load more" pagination run over server-rendered cards, so the page is complete
   without JS and filtering is instant with it. State lives in the URL (?size=M&colour=green&sort=new) so every
   filtered view can be shared, bookmarked and restored with Back. */
(() => {
  "use strict";
  const { $, $$, esc, icon, announce } = window.A88S;
  const root = $("[data-plp]");
  if (!root) return;
  const grid = $("[data-grid]", root);
  const form = $("[data-filter-form]", root);
  const cards = $$(".card", grid);
  const PAGE = Number(root.dataset.pageSize) || 24;
  const sortSel = $("[data-sort]", root);
  let shown = PAGE;

  // Parse each card's in-stock variants once: colour handle -> Set(sizes), plus colour handle -> colour family.
  cards.forEach((card) => {
    card._pairs = new Map();
    card.dataset.stock.split("|").filter(Boolean).forEach((chunk) => {
      const [c, sizes] = chunk.split(":");
      card._pairs.set(c, new Set(sizes.split(" ").filter(Boolean)));
    });
    card._familyMap = {};
    JSON.parse(card.dataset.colours).forEach((c) => (card._familyMap[c.h] = c.f));
  });

  const state = () => {
    const fd = new FormData(form);
    return { size: fd.getAll("size"), colour: fd.getAll("colour"), sort: sortSel.value };
  };

  function matches(card, s) {
    if (!s.size.length && !s.colour.length) return true;
    for (const [colour, sizes] of card._pairs) {
      const fam = card._familyMap[colour];
      if (s.colour.length && !s.colour.includes(fam)) continue;
      if (!s.size.length) return true;
      for (const sz of s.size) if (sizes.has(sz)) return true;
    }
    return false;
  }
  function firstMatchingColour(card, s) {
    if (!s.colour.length) return null;
    for (const [colour, sizes] of card._pairs) {
      if (s.colour.includes(card._familyMap[colour]) && (!s.size.length || s.size.some((x) => sizes.has(x)))) return colour;
    }
    return null;
  }
  const sorters = {
    featured: (a, b) => a.dataset.rank - b.dataset.rank,
    new: (a, b) => b.dataset.new - a.dataset.new || a.dataset.rank - b.dataset.rank,
    "price-asc": (a, b) => a.dataset.price - b.dataset.price || a.dataset.rank - b.dataset.rank,
    "price-desc": (a, b) => b.dataset.price - a.dataset.price || a.dataset.rank - b.dataset.rank,
  };

  function apply({ resetPage = true, push = true } = {}) {
    const s = state();
    if (resetPage) shown = PAGE;
    const sorted = [...cards].sort(sorters[s.sort] || sorters.featured);
    const frag = document.createDocumentFragment();
    let visible = 0;
    sorted.forEach((card) => {
      const ok = matches(card, s);
      card.classList.toggle("is-filtered", !ok);
      if (ok) {
        visible += 1;
        card.classList.toggle("is-paged", visible > shown);
        const colour = firstMatchingColour(card, s);
        if (colour && card.dataset.active !== colour) window.A88S.setCardColour(card, colour);
      } else card.classList.remove("is-paged");
      frag.append(card);
    });
    grid.append(frag);

    const total = visible;
    const label = `${total} ${total === 1 ? "style" : "styles"}`;
    $("[data-result-count]", root).textContent = label;
    $$("[data-show-results]", root).forEach((b) => (b.textContent = total ? `Show ${label}` : "No matches"));
    $("[data-empty]", root).hidden = total > 0;
    const pager = $("[data-pager]", root);
    pager.hidden = total === 0;
    const n = Math.min(shown, total);
    $("[data-pager-text]", root).textContent = `Showing ${n} of ${total}`;
    $("[data-pager-bar]", root).style.transform = `scaleX(${total ? n / total : 0})`;
    $("[data-load-more]", root).hidden = n >= total;

    // Active filter chips + counts
    const chips = [
      ...s.size.map((v) => ({ name: "size", v, label: `Size ${v}` })),
      ...s.colour.map((v) => ({ name: "colour", v, label: v[0].toUpperCase() + v.slice(1) })),
    ];
    $("[data-active-filters]", root).innerHTML = chips.length
      ? chips.map((c) => `<button type="button" class="active-chip" data-remove-filter="${c.name}" data-value="${esc(c.v)}" aria-label="Remove filter: ${esc(c.label)}">${esc(c.label)}${icon("x")}</button>`).join("") +
        `<button type="button" class="active-clear" data-clear-filters>Clear all</button>`
      : "";
    $("[data-filter-n]", root).textContent = chips.length || "";
    $$("[data-filter-group]", root).forEach((g) => {
      const n = $$("input:checked", g).length;
      const el = $("[data-group-count]", g);
      if (el) el.textContent = n || "";
    });

    if (push) {
      const url = new URL(location.href);
      ["size", "colour", "sort"].forEach((k) => url.searchParams.delete(k));
      s.size.forEach((v) => url.searchParams.append("size", v));
      s.colour.forEach((v) => url.searchParams.append("colour", v));
      if (s.sort !== "featured") url.searchParams.set("sort", s.sort);
      history.replaceState(null, "", url);
    }
    return total;
  }

  function fromURL() {
    const p = new URLSearchParams(location.search);
    const sizes = p.getAll("size"), colours = p.getAll("colour");
    $$('input[name="size"]', form).forEach((i) => (i.checked = sizes.includes(i.value)));
    $$('input[name="colour"]', form).forEach((i) => (i.checked = colours.includes(i.value)));
    const sort = p.get("sort");
    if (sort && sorters[sort]) sortSel.value = sort;
  }

  form.addEventListener("change", () => {
    const total = apply();
    announce(`${total} ${total === 1 ? "style" : "styles"} found`);
  });
  sortSel.addEventListener("change", () => apply());
  form.addEventListener("reset", () => setTimeout(() => apply(), 0));
  form.addEventListener("submit", (ev) => ev.preventDefault());
  root.addEventListener("click", (ev) => {
    const rm = ev.target.closest("[data-remove-filter]");
    if (rm) {
      const input = $(`input[name="${rm.dataset.removeFilter}"][value="${CSS.escape(rm.dataset.value)}"]`, form);
      if (input) input.checked = false;
      apply();
      ($("[data-active-filters] button", root) || sortSel).focus();
    }
    if (ev.target.closest("[data-clear-filters]") && ev.target.type !== "reset") {
      form.reset();
    }
    const more = ev.target.closest("[data-load-more]");
    if (more) {
      const firstNew = cards.filter((c) => c.classList.contains("is-paged") && !c.classList.contains("is-filtered"))
        .sort((a, b) => [...grid.children].indexOf(a) - [...grid.children].indexOf(b))[0];
      shown += PAGE;
      apply({ resetPage: false, push: false });
      // Move focus to the first newly revealed product so keyboard users continue from there.
      firstNew?.querySelector(".card__title a")?.focus({ preventScroll: false });
    }
  });

  fromURL();
  apply({ push: false });
})();
