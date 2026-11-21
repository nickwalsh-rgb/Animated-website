/* Archive 88: bag page. Line items, quantity, remove, promo code, free-delivery message, totals and checkout.
   Checkout hands off to Shopify when store.json has a shopify_domain and every line has a variant id. */
(() => {
  "use strict";
  const { $, $$, cfg, money, esc, thumb, Bag, announce } = window.A88;
  const root = $("[data-bag]");
  if (!root) return;
  const list = $("[data-bag-lines]", root);

  function render() {
    const lines = Bag.lines;
    const empty = !lines.length;
    $("[data-bag-empty]", root).hidden = !empty;
    $$("[data-bag-full]", root).forEach((el) => (el.hidden = empty));
    if (empty) return;
    list.innerHTML = lines.map((l) => {
      const opts = Array.from({ length: Math.max(l.qty, Math.min(l.max, 10)) }, (_, i) => `<option value="${i + 1}"${i + 1 === l.qty ? " selected" : ""}>${i + 1}</option>`).join("");
      const href = cfg.root + l.url;
      return `<li class="line" data-sku="${esc(l.sku)}">
  <a class="line__img" href="${esc(href)}" tabindex="-1" aria-hidden="true">${thumb(l, "art")}</a>
  <div>
    <a class="line__name" href="${esc(href)}">${esc(l.title)}</a>
    <p class="line__meta">${esc(l.colourName)}</p>
    <p class="line__meta">${esc(l.size)}</p>
    <label class="line__qty">Quantity: <select data-qty aria-label="Quantity for ${esc(l.title)}, ${esc(l.size)}">${opts}</select></label>
  </div>
  <p class="line__price">${money(l.price * l.qty)}</p>
  <button type="button" class="line__remove" data-remove>Remove<span class="sr-only"> ${esc(l.title)}, ${esc(l.size)}</span></button>
</li>`;
    }).join("");
    const sub = Bag.subtotal();
    const free = sub >= cfg.free;
    const delivery = free ? 0 : cfg.delivery;
    $("[data-bag-subtotal]", root).textContent = money(sub);
    $("[data-bag-delivery]", root).textContent = money(delivery);
    $("[data-bag-total]", root).textContent = money(sub + delivery);
    $("[data-bag-meter]", root).textContent = free ? "You've unlocked free delivery." : `You're ${money(cfg.free - sub)} away from free delivery.`;
  }

  list.addEventListener("change", (ev) => {
    if (!ev.target.matches("[data-qty]")) return;
    const sku = ev.target.closest(".line").dataset.sku;
    Bag.setQty(sku, Number(ev.target.value));
    announce("Bag updated");
    $(`.line[data-sku="${CSS.escape(sku)}"] [data-qty]`, list)?.focus();
  });
  list.addEventListener("click", (ev) => {
    if (!ev.target.closest("[data-remove]")) return;
    const li = ev.target.closest(".line");
    const next = li.nextElementSibling || li.previousElementSibling;
    const sku = li.dataset.sku;
    Bag.remove(sku);
    announce("Item removed from your bag");
    (next ? $(`.line[data-sku="${CSS.escape(next.dataset.sku)}"] [data-qty]`, list) : $(".bag__empty .btn", root))?.focus();
  });

  $("[data-promo]", root).addEventListener("submit", (ev) => {
    ev.preventDefault();
    const code = $("#promo-code").value.trim();
    $("[data-promo-msg]", root).textContent = code ? `"${code}" isn't a valid code.` : "Enter a promo code.";
  });

  $("[data-checkout]", root).addEventListener("click", () => {
    const ids = Bag.lines.map((l) => l.id && `${l.id}:${l.qty}`);
    if (cfg.shopify && ids.every(Boolean)) { location.href = `https://${cfg.shopify}/cart/${ids.join(",")}`; return; }
    $("[data-checkout-msg]", root).textContent = "Checkout opens once the shop is connected to Shopify. Your bag is saved on this device.";
  });

  document.addEventListener("bag:change", render);
  render();
  if (location.hash === "#checkout" && Bag.lines.length) $("#checkout").focus();
})();
