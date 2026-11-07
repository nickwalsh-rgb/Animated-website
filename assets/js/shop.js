/* Archive 88: Shop all page (needs site.js first)
   Filter by category and size, optionally include sold pieces. State lives in the URL
   (?cat=knitwear&size=m&sold=1) so filtered views can be shared and linked from the menu.
   Tags glide to their new places with GSAP Flip. */
(() => {
  const { $, $$, motion, site, T } = window.A88;
  const grid = $(".js-grid");
  const tags = $$(".tag", grid);
  const countEl = $(".js-shop-count");
  const nounEl = $(".js-shop-noun");
  const empty = $(".js-empty");
  const soldBox = $(".js-show-sold");
  const catChips = $$("[data-cat].chip");
  const sizeChips = $$("[data-size].chip");
  const useFlip = motion && window.Flip;
  if (useFlip) gsap.registerPlugin(Flip);

  const params = new URLSearchParams(window.location.search);
  const valid = (chips, key, v) => (v && chips.some((c) => c.dataset[key] === v) ? v : "all");
  const state = {
    cat: valid(catChips, "cat", params.get("cat")),
    size: valid(sizeChips, "size", params.get("size")),
    sold: params.get("sold") === "1",
  };

  const matches = (t) =>
    (state.cat === "all" || t.dataset.cat === state.cat) &&
    (state.size === "all" || t.dataset.size === state.size) &&
    (state.sold || t.dataset.sold === "0");

  function syncControls() {
    catChips.forEach((c) => { const on = c.dataset.cat === state.cat; c.classList.toggle("is-on", on); c.setAttribute("aria-pressed", on); });
    sizeChips.forEach((c) => { const on = c.dataset.size === state.size; c.classList.toggle("is-on", on); c.setAttribute("aria-pressed", on); });
    soldBox.checked = state.sold;
    // Dim categories with nothing to show (still clickable).
    catChips.forEach((c) => {
      if (c.dataset.cat === "all") return;
      c.classList.toggle("is-empty", !tags.some((t) => t.dataset.cat === c.dataset.cat && (state.sold || t.dataset.sold === "0")));
    });
    // Dim size options that have nothing under the current category (still clickable).
    sizeChips.forEach((c) => {
      if (c.dataset.size === "all") return;
      const any = tags.some((t) => t.dataset.size === c.dataset.size &&
        (state.cat === "all" || t.dataset.cat === state.cat) && (state.sold || t.dataset.sold === "0"));
      c.classList.toggle("is-empty", !any);
    });
  }

  function syncUrl() {
    const q = new URLSearchParams();
    if (state.cat !== "all") q.set("cat", state.cat);
    if (state.size !== "all") q.set("size", state.size);
    if (state.sold) q.set("sold", "1");
    const qs = q.toString();
    history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }

  function apply(animate) {
    const flipState = animate && useFlip ? Flip.getState(tags) : null;
    let n = 0;
    tags.forEach((t) => { const show = matches(t); t.hidden = !show; if (show) n++; });
    countEl.textContent = n;
    nounEl.textContent = n === 1 ? "piece" : "pieces";
    empty.hidden = n > 0;
    syncControls();
    syncUrl();
    if (flipState) {
      Flip.from(flipState, {
        duration: T.slow, ease: "expo.out", absolute: true, nested: true,
        onEnter: (els) => gsap.fromTo(els, { opacity: 0, y: 30, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: T.slow, ease: "expo.out", stagger: 0.04 }),
        onLeave: (els) => gsap.to(els, { opacity: 0, scale: 0.94, duration: T.fast, ease: "power2.in" }),
        onComplete: () => window.ScrollTrigger && ScrollTrigger.refresh(),
      });
    }
  }

  catChips.forEach((c) => c.addEventListener("click", () => { state.cat = c.dataset.cat; apply(true); }));
  sizeChips.forEach((c) => c.addEventListener("click", () => { state.size = c.dataset.size; apply(true); }));
  soldBox.addEventListener("change", () => { state.sold = soldBox.checked; apply(true); });
  $(".js-clear").addEventListener("click", () => { state.cat = "all"; state.size = "all"; state.sold = false; apply(true); });

  // Choosing a category in the menu while already here filters in place.
  window.A88.onCategory = (cat) => {
    state.cat = valid(catChips, "cat", cat);
    apply(true);
    site.scrollTo(0);
  };

  apply(false);

  if (motion) {
    gsap.from(tags.filter((t) => !t.hidden), {
      opacity: 0, y: 50, rotation: (i) => (i % 2 ? 3 : -3), duration: T.slower, ease: "expo.out", stagger: 0.06, delay: 0.15,
    });
    gsap.from(".filters", { opacity: 0, y: 16, duration: T.slow, ease: "expo.out", delay: 0.1 });
  }
})();
