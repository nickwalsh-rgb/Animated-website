/* Archive 88 storefront: gift cards.
   Amount chips, two delivery buttons (email / post) that each open their own form, a live card preview, inline
   validation, and Add to bag (a gift card is a normal bag line, with the recipient details attached). */
(() => {
  "use strict";
  const { $, $$, money, Cart, cfg, announce } = window.A88S;
  const root = $("[data-gift]");
  if (!root) return;
  const conf = JSON.parse($("#gift-config").textContent);
  const card = $("[data-gift-card]", root);
  const methods = $$("[data-gift-method]", root);
  const forms = { email: $("#gift-email"), post: $("#gift-post") };
  const amount = () => Number(($('input[name="amount"]:checked', root) || {}).value || conf.amounts[0]);
  let method = null;

  /* Preview + price labels */
  function render() {
    const a = amount();
    $("[data-gift-amount]", card).textContent = money(a);
    $$("[data-gift-price]", root).forEach((n) => (n.textContent = money(a)));
    const to = method && forms[method] ? $(`#${method}-to`, forms[method]).value.trim() : "";
    $("[data-gift-to]", card).textContent = to || "someone good";
    card.dataset.method = method || "email";
    $("[data-gift-kind]", card).textContent = method === "post" ? "Gift card · By post" : "E-gift card";
  }
  $$('input[name="amount"]', root).forEach((i) => i.addEventListener("change", render));

  /* The two buttons: each opens its own form; opening one closes the other */
  function choose(m, { focus = true } = {}) {
    method = m;
    methods.forEach((b) => {
      const on = b.dataset.giftMethod === m;
      b.setAttribute("aria-expanded", String(on));
      b.classList.toggle("is-on", on);
    });
    Object.entries(forms).forEach(([k, f]) => (f.hidden = k !== m));
    render();
    if (focus) $("input, textarea", forms[m]).focus({ preventScroll: false });
    const url = new URL(location.href);
    url.searchParams.set("send", m);
    history.replaceState(null, "", url);
  }
  methods.forEach((b) => b.addEventListener("click", () => choose(b.dataset.giftMethod)));

  /* Validation: checked when you leave a field, and all at once on submit */
  const POSTCODE = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;
  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  function check(input) {
    const v = input.value.trim();
    const label = $(`label[for="${input.id}"]`).childNodes[0].textContent.trim();
    let msg = "";
    if (input.required && !v) msg = `Enter ${label.toLowerCase().replace(/^their /, "their ").replace(/^your /, "your ")}`;
    else if (input.type === "email" && v && !EMAIL.test(v)) msg = "Enter an email address like name@example.com";
    else if (input.id === "post-postcode" && v && !POSTCODE.test(v)) msg = "Enter a UK postcode like SW1A 1AA";
    else if (input.type === "date" && v && v < input.min) msg = "Choose today or a later date";
    const err = $(`#${input.id}-err`);
    err.textContent = msg;
    input.setAttribute("aria-invalid", msg ? "true" : "false");
    input.closest(".field").classList.toggle("is-invalid", !!msg);
    return !msg;
  }
  Object.values(forms).forEach((f) => {
    f.addEventListener("focusout", (ev) => {
      if (ev.target.matches("input, textarea") && (ev.target.value || ev.target.getAttribute("aria-invalid"))) check(ev.target);
    });
    f.addEventListener("input", (ev) => {
      if (ev.target.id.endsWith("-to")) render();
      if (ev.target.getAttribute("aria-invalid") === "true") check(ev.target);
    });
    f.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const fields = $$("input, textarea", f);
      const bad = fields.filter((i) => !check(i));
      if (bad.length) { bad[0].focus(); return; }
      add(f.dataset.giftForm, Object.fromEntries(fields.map((i) => [i.id.replace(/^(email|post)-/, ""), i.value.trim()])), f);
    });
  });

  function add(m, d, form) {
    const a = amount();
    const when = m === "email"
      ? (d.date && d.date !== new Date().toISOString().slice(0, 10)
        ? "Sends " + new Date(d.date + "T12:00").toLocaleDateString(cfg.locale, { day: "numeric", month: "short" })
        : "Sends today")
      : d.postcode.toUpperCase();
    const ok = Cart.add({
      sku: `GIFT-${m.toUpperCase()}-${a}-${Date.now().toString(36)}`,
      handle: "gift-card", title: "Gift card", url: "gift-cards/", price: a,
      colour: m, colourName: (m === "email" ? "Email to " : "Post to ") + d.to, hex: m === "email" ? "#1b211d" : "#2f3d33",
      size: when, sil: "gift", img: null, max: 10,
      variantId: conf.ids[`${m}/${a}`] || null,
      gift: { method: m, amount: a, ...d },
    }, { opener: $("button[type=submit]", form) });
    if (ok) {
      form.reset();
      $$("[aria-invalid]", form).forEach((i) => i.removeAttribute("aria-invalid"));
      render();
      announce(`Gift card for ${d.to} added to your bag`);
    }
  }

  /* Card tilts toward the pointer (fine pointers, motion allowed) */
  if (matchMedia("(hover: hover) and (pointer: fine)").matches && !window.A88S.reduced.matches) {
    const stage = $(".gift__visual", root);
    stage.addEventListener("pointermove", (ev) => {
      const r = stage.getBoundingClientRect();
      card.style.setProperty("--ry", `${((ev.clientX - r.left) / r.width - 0.5) * 16}deg`);
      card.style.setProperty("--rx", `${((ev.clientY - r.top) / r.height - 0.5) * -12}deg`);
    });
    stage.addEventListener("pointerleave", () => { card.style.setProperty("--rx", "0deg"); card.style.setProperty("--ry", "0deg"); });
  }

  const want = new URLSearchParams(location.search).get("send");
  if (want && forms[want]) choose(want, { focus: false });
  render();
})();
