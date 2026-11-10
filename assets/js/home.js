/* The Easy Life: homepage.
   The sunlit wall keeps the visitor's time: the patch of sun leans, stretches and warms through the day, and the small
   sundial beside the pause button says what hour it is showing. Add ?light=7.5 to the address to see another hour
   (0 to 24). This file also pauses the shadows off screen, swaps the category plate, and fades sections up once as
   they arrive. It also runs the hero lookbook and the featured collection's filter tabs. No scroll-jacking, pinning or loaders. Needs store.js. With reduced motion the shadows hold still. */
(() => {
  "use strict";
  const { $, $$, reduced } = window.A88S;

  /* ---------- The light follows the clock ---------- */
  // hour, slant (deg), shift (vmax), length, lit plaster (rgb), shade, leaf strength, dimness
  const DAY = [
    [0, -30, 9, 1.3, [236, 238, 241], 0.081, 0.25, 0.8],
    [5.5, -30, 9, 1.3, [239, 240, 242], 0.097, 0.3, 0.7],
    [7, -28, 8, 1.28, [253, 250, 243], 0.162, 0.8, 0],
    [10, -17, 4, 1.13, [253, 253, 250], 0.178, 1, 0],
    [13, -3, 0, 1.02, [254, 254, 252], 0.194, 1.05, 0],
    [16, 12, -4, 1.1, [254, 251, 243], 0.186, 1, 0],
    [19, 26, -8, 1.26, [252, 244, 230], 0.162, 0.85, 0],
    [20.5, 30, -9, 1.3, [242, 240, 238], 0.113, 0.4, 0.55],
    [21.5, 30, -9, 1.3, [236, 238, 241], 0.081, 0.25, 0.8],
    [24, -30, 9, 1.3, [236, 238, 241], 0.081, 0.25, 0.8],
  ];
  const PHRASES = [[5.5, "Not light yet"], [8, "First light"], [11.5, "Morning light"], [14, "Midday light"], [17.5, "Afternoon light"], [20, "Evening light"], [21.5, "Last light"], [24, "After dark"]];
  const asked = parseFloat(new URLSearchParams(location.search).get("light"));
  const now = () => {
    if (!Number.isNaN(asked)) return ((asked % 24) + 24) % 24;
    const d = new Date();
    return d.getHours() + d.getMinutes() / 60;
  };
  const mix = (a, b, k) => a + (b - a) * k;
  const dial = $("[data-dial]");
  const root = document.documentElement.style;
  function light() {
    const h = now();
    const i = Math.max(1, DAY.findIndex((row) => row[0] > h));
    const a = DAY[i - 1], b = DAY[i], k = (h - a[0]) / (b[0] - a[0]);
    root.setProperty("--sun-skew", `${mix(a[1], b[1], k).toFixed(2)}deg`);
    root.setProperty("--sun-shift", `${mix(a[2], b[2], k).toFixed(2)}vmax`);
    root.setProperty("--sun-len", mix(a[3], b[3], k).toFixed(3));
    root.setProperty("--sun-lit", `rgb(${a[4].map((v, n) => Math.round(mix(v, b[4][n], k))).join(" ")})`);
    root.setProperty("--sun-shade", mix(a[5], b[5], k).toFixed(3));
    root.setProperty("--sun-leaf", mix(a[6], b[6], k).toFixed(2));
    root.setProperty("--sun-dim", mix(a[7], b[7], k).toFixed(2));
    // The mark's own shadow leans with the light: left of the leaf in the morning, right of it by evening.
    root.setProperty("--mark-x", Math.round(mix(a[1], b[1], k) * 5.5));
    if (!dial) return;
    const hh = Math.floor(h), mm = Math.floor((h - hh) * 60);
    $("[data-dial-time]", dial).textContent = `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    $("[data-dial-phrase]", dial).textContent = `${PHRASES.find((p) => h < p[0])[1]}, where you are`;
    // The dot rides the arc from 5.30 to 21.30 and rests below the line overnight.
    const day = (h - 5.5) / 16, up = day >= 0 && day <= 1, sun = $("[data-dial-sun]", dial);
    sun.setAttribute("cx", (up ? 36 - 32 * Math.cos(Math.PI * day) : 36).toFixed(1));
    sun.setAttribute("cy", (up ? 26 - 22 * Math.sin(Math.PI * day) : 31).toFixed(1));
    sun.style.opacity = up ? 1 : 0.35;
    dial.hidden = false;
  }
  const walls = $$("[data-wall]");
  if (walls.length) {
    light();
    setInterval(light, 60000);
  }

  /* ---------- Shadows: pause off screen, and on request ---------- */
  const toggle = $("[data-wall-toggle]");
  if (walls.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => en.target.classList.toggle("is-offscreen", !en.isIntersecting));
    });
    walls.forEach((w) => io.observe(w));
  }
  if (toggle && reduced.matches) toggle.hidden = true;
  if (walls.length && toggle) {
    toggle.addEventListener("click", () => {
      const paused = toggle.getAttribute("aria-pressed") !== "true";
      toggle.setAttribute("aria-pressed", String(paused));
      walls.forEach((w) => w.classList.toggle("is-paused", paused));
      $("[data-wall-label]", toggle).textContent = paused ? "Play the moving shadows" : "Pause the moving shadows";
      $("use", toggle).setAttribute("href", paused ? "#i-play" : "#i-pause");
    });
  }

  /* ---------- Lookbook: arrows, arrow keys and swipes change the look; a line or a piece picks one piece out ---------- */
  const book = $("[data-lookbook]");
  if (book) {
    const looks = $$("[data-look]", book), counter = $("[data-look-index]", book);
    let at = 0;
    const show = (i) => {
      at = (i + looks.length) % looks.length;
      looks.forEach((look, n) => {
        look.classList.toggle("is-active", n === at);
        look.toggleAttribute("inert", n !== at);
        look.classList.remove("has-focus");
      });
      counter.textContent = at + 1;
    };
    $("[data-look-prev]", book).addEventListener("click", () => show(at - 1));
    $("[data-look-next]", book).addEventListener("click", () => show(at + 1));
    book.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft") show(at - 1);
      else if (ev.key === "ArrowRight") show(at + 1);
    });
    let x0 = null;
    book.addEventListener("pointerdown", (ev) => { x0 = ev.pointerType === "touch" ? ev.clientX : null; });
    book.addEventListener("pointerup", (ev) => {
      if (x0 !== null && Math.abs(ev.clientX - x0) > 48) show(at + (ev.clientX < x0 ? 1 : -1));
      x0 = null;
    });
    const pick = (look, piece) => {
      look.classList.toggle("has-focus", piece !== null);
      $$("[data-piece]", look).forEach((el) => el.classList.toggle("is-focus", el.dataset.piece === piece));
    };
    looks.forEach((look) => {
      $$("[data-piece]", look).forEach((el) => {
        el.addEventListener("pointerenter", (ev) => ev.pointerType === "mouse" && pick(look, el.dataset.piece));
        el.addEventListener("pointerleave", () => pick(look, null));
        el.addEventListener("focus", () => pick(look, el.dataset.piece));
        el.addEventListener("blur", () => pick(look, null));
      });
    });
  }

  /* ---------- Featured collection: filter tabs. Each tab shows its six styles, arriving one after another ---------- */
  const feat = $("[data-featured]");
  if (feat) {
    const tabs = $$("[data-tab]", feat), cells = $$(".featured__cell", feat), status = $("[data-featured-status]", feat);
    tabs.forEach((tab) => tab.addEventListener("click", () => {
      if (tab.getAttribute("aria-pressed") === "true") return;
      tabs.forEach((el) => el.setAttribute("aria-pressed", String(el === tab)));
      let i = 0;
      cells.forEach((cell) => {
        const on = cell.dataset.groups.split(" ").includes(tab.dataset.tab);
        cell.hidden = !on;
        cell.classList.remove("is-enter");
        if (!on) return;
        cell.classList.add("is-in"); // already revealed: the tab change plays its own entrance
        cell.style.transitionDelay = "0s";
        cell.style.setProperty("--i", i++);
        void cell.offsetWidth;
        cell.classList.add("is-enter");
      });
      status.textContent = `Showing ${i} styles: ${tab.textContent}`;
    }));
  }

  /* ---------- Category index: the plate shows whichever name is pointed at or focused ---------- */
  $$("[data-index] .index__item").forEach((item, _, all) => {
    const on = () => all.forEach((el) => el.classList.toggle("is-active", el === item));
    item.addEventListener("pointerenter", (ev) => ev.pointerType === "mouse" && on());
    item.addEventListener("focusin", on);
  });

  /* ---------- Sections fade up once as they arrive ---------- */
  const items = $$(".reveal");
  if (reduced.matches || !items.length || !("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("has-motion");
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return;
      // Neighbours entering together arrive one after another.
      const siblings = [...en.target.parentElement.children].filter((n) => n.classList.contains("reveal"));
      en.target.style.transitionDelay = `${Math.min(siblings.indexOf(en.target), 5) * 60}ms`;
      en.target.classList.add("is-in");
      io.unobserve(en.target);
    });
  }, { rootMargin: "0px 0px -8% 0px" });
  items.forEach((el) => io.observe(el));
})();
