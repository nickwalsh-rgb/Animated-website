/* Archive 88: search page. Full screen, focused on arrival, trending searches until the shopper types.
   Results appear as you type (200ms debounce) and the query is written to the address as ?query=, so a search can
   be shared or reloaded. Every word must match the name, colour, category, fabric, fit or style number; name
   matches rank first. Filtering and sorting reuse the listing panel (plp.js). */
(() => {
  "use strict";
  const { $, $$, cfg, esc } = window.A88;
  const root = $("[data-search]");
  if (!root) return;
  const input = $("#q", root), grid = $("[data-grid]", root);
  const trending = $("[data-trending]", root), suggest = $("[data-suggest]", root), sugList = $("[data-suggest-list]", root);
  const head = $("[data-results-head]", root), foot = $("[data-results-foot]", root), none = $("[data-none]", root);
  let index = null, timer;

  const load = () => index || (index = fetch(`${cfg.root}search.json`).then((r) => r.json()));

  function mark(label, q) {
    const i = label.toLowerCase().indexOf(q);
    if (i < 0) return esc(label);
    return `${esc(label.slice(0, i))}<mark>${esc(label.slice(i, i + q.length))}</mark>${esc(label.slice(i + q.length))}`;
  }

  async function run(raw, { write = true } = {}) {
    const q = raw.trim().toLowerCase();
    if (write) {
      const url = new URL(location.href);
      q ? url.searchParams.set("query", raw.trim()) : url.searchParams.delete("query");
      ["colour", "size", "waist", "fit", "fabric", "category", "sort", "page"].forEach((k) => url.searchParams.delete(k));
      history.replaceState(null, "", url.pathname + url.search);
    }
    trending.hidden = !!q;
    if (!q) {
      suggest.hidden = true; head.hidden = true; foot.hidden = true; none.hidden = true; grid.innerHTML = "";
      return;
    }
    const data = await load();
    const words = q.split(/\s+/).filter(Boolean);
    const hits = data.items
      .map((it, n) => ({ it, n, score: (it.t.startsWith(q) ? 0 : it.t.includes(words[0]) ? 1 : 2) }))
      .filter(({ it }) => words.every((w) => it.s.includes(w)))
      .sort((a, b) => a.score - b.score || a.n - b.n);
    const sugs = data.suggest.filter((s) => s.l.toLowerCase().includes(q)).slice(0, 6);
    suggest.hidden = !sugs.length;
    sugList.innerHTML = sugs.map((s) => `<li><a href="${esc(cfg.root + s.u)}">${mark(s.l, q)}</a></li>`).join("");
    grid.innerHTML = hits.map(({ it }) => it.h).join("");
    $$("[data-card]", grid).forEach((c, i) => (c.dataset.order = i));
    head.hidden = !hits.length; foot.hidden = !hits.length; none.hidden = !!hits.length;
    window.A88.listing?.refresh();
  }

  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => run(input.value), 200); });
  $("[data-search-form]", root).addEventListener("submit", (ev) => { ev.preventDefault(); clearTimeout(timer); run(input.value); input.blur(); });
  trending.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-term]");
    if (!b) return;
    input.value = b.dataset.term;
    run(input.value);
    input.focus();
  });
  $("[data-search-close]", root).addEventListener("click", (ev) => {
    if (document.referrer && new URL(document.referrer).origin === location.origin && history.length > 1) { ev.preventDefault(); history.back(); }
  });

  const initial = new URLSearchParams(location.search).get("query") || "";
  if (initial) { input.value = initial; run(initial, { write: false }); }
  input.focus();
})();
