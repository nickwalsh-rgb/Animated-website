/* Archive 88 reel: motion engine for landing/index.html.
   No libraries. One requestAnimationFrame loop reads a smoothed scroll position and hands each scene its
   0..1 progress through its own scroll track, so scrolling scrubs every animation like a playhead.
   prefers-reduced-motion: no count-in, no smoothing, no zoom, no ambient movement; every scene still reads. */
(() => {
  "use strict";

  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const FINE = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const doc = document.documentElement;
  const body = document.body;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // ── Maths ─────────────────────────────────────────────────────────────────────────────────────────────
  const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, t) => a + (b - a) * t;
  const range = (v, a, b) => clamp((v - a) / (b - a));
  const E = {
    out3: (t) => 1 - Math.pow(1 - t, 3),
    in3: (t) => t * t * t,
    inOut3: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outExpo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    inOutExpo: (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2),
    outBack: (t) => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  };
  const hexToRgb = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const mixRgb = (a, b, t) => a.map((v, i) => Math.round(lerp(v, b[i], t)));
  const pad = (n, l = 2) => String(n).padStart(l, "0");
  let seed = 88;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;

  // ── State ─────────────────────────────────────────────────────────────────────────────────────────────
  const S = { vw: innerWidth, vh: innerHeight, sy: scrollY, y: scrollY, py: scrollY, vel: 0, svel: 0, t: 0, docH: 1,
    mx: innerWidth / 2, my: innerHeight / 2, rx: innerWidth / 2, ry: innerHeight / 2, mouseIn: false, ready: false, revealAt: 0 };
  addEventListener("scroll", () => { S.sy = scrollY; }, { passive: true });
  addEventListener("pointermove", (e) => { S.mx = e.clientX; S.my = e.clientY; S.mouseIn = e.pointerType === "mouse"; }, { passive: true });

  // ── Text splitting ────────────────────────────────────────────────────────────────────────────────────
  function splitChars(el) {
    const text = el.textContent.trim();
    el.setAttribute("aria-label", text);
    el.textContent = "";
    const chars = [];
    text.split(" ").forEach((w, wi, arr) => {
      const word = document.createElement("span");
      word.className = "word";
      word.setAttribute("aria-hidden", "true");
      for (const c of w) {
        const ch = document.createElement("span");
        ch.className = "ch";
        const inner = document.createElement("span");
        inner.textContent = c;
        ch.appendChild(inner);
        word.appendChild(ch);
        chars.push(inner);
      }
      el.appendChild(word);
      if (wi < arr.length - 1) el.appendChild(document.createTextNode(" "));
    });
    return chars;
  }

  // ── Film grain ────────────────────────────────────────────────────────────────────────────────────────
  (function grain() {
    const c = document.createElement("canvas");
    c.width = c.height = 180;
    const x = c.getContext("2d");
    const img = x.createImageData(180, 180);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = Math.random() > 0.5 ? 255 : 0;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = Math.random() * 110;
    }
    x.putImageData(img, 0, 0);
    $(".grain").style.backgroundImage = `url(${c.toDataURL()})`;
  })();

  // ── Cursor ────────────────────────────────────────────────────────────────────────────────────────────
  const cursor = $(".cursor");
  const cRing = $(".cursor__ring");
  const cDot = $(".cursor__dot");
  const cLabel = $(".cursor__label");
  if (FINE) {
    body.classList.add("has-cursor");
    document.addEventListener("pointerover", (e) => {
      const t = e.target.closest("[data-cursor]");
      if (t) { cLabel.textContent = t.dataset.cursor; cursor.classList.add("is-label"); }
      else cursor.classList.remove("is-label");
    });
    document.addEventListener("pointerdown", () => cursor.classList.add("is-down"));
    document.addEventListener("pointerup", () => cursor.classList.remove("is-down"));
    document.addEventListener("pointerleave", () => { cursor.style.opacity = 0; });
    document.addEventListener("pointerenter", () => { cursor.style.opacity = 1; });
    // Magnetic controls lean towards the pointer
    $$(".magnetic").forEach((m) => {
      m.style.transition = "transform .5s cubic-bezier(.22,1,.36,1)";
      m.addEventListener("pointermove", (e) => {
        const r = m.getBoundingClientRect();
        const dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
        m.style.transform = `translate(${dx * 0.28}px, ${dy * 0.38}px)`;
      });
      m.addEventListener("pointerleave", () => { m.style.transform = ""; });
    });
  }
  function drawCursor() {
    if (!FINE) return;
    const k = RM ? 1 : 0.2;
    S.rx = lerp(S.rx, S.mx, k);
    S.ry = lerp(S.ry, S.my, k);
    cDot.style.transform = `translate3d(${S.mx}px, ${S.my}px, 0)`;
    cRing.style.transform = `translate3d(${S.rx}px, ${S.ry}px, 0)`;
  }

  // ── Scenes and measurement ────────────────────────────────────────────────────────────────────────────
  const scenes = $$(".scene").map((el, i) => ({ el, i, id: el.id, name: el.dataset.scene, top: 0, h: 0, update: null }));
  const byId = (id) => scenes.find((s) => s.id === id);
  const progress = (s) => clamp((S.y - s.top) / Math.max(1, s.h - S.vh));
  const visible = (s) => {
    const a = Math.min(S.y, S.sy), b = Math.max(S.y, S.sy);
    return b + S.vh > s.top && a < s.top + s.h;
  };
  const measureHooks = [];
  function measure() {
    S.vw = innerWidth;
    S.vh = innerHeight;
    measureHooks.forEach((f) => f());
    scenes.forEach((s) => { s.top = s.el.offsetTop; s.h = s.el.offsetHeight; });
    S.docH = doc.scrollHeight;
    buildIndex();
  }

  // ── HUD: timecode, scene name, progress ───────────────────────────────────────────────────────────────
  const tcEl = $(".js-tc"), sceneNo = $(".js-scene-no"), sceneName = $(".js-scene-name"), progEl = $(".js-prog");
  let currentScene = -1;
  const timecode = (y) => {
    const f = Math.max(0, Math.floor((y / S.vh) * 2 * 25)); // one screen of scroll = two seconds of reel
    return `${pad(Math.floor(f / 90000))}:${pad(Math.floor(f / 1500) % 60)}:${pad(Math.floor(f / 25) % 60)}:${pad(f % 25)}`;
  };
  function hud() {
    tcEl.textContent = timecode(S.y);
    progEl.style.transform = `scaleX(${clamp(S.y / Math.max(1, S.docH - S.vh))})`;
    let cur = 0;
    scenes.forEach((s, i) => { if (S.y + S.vh * 0.5 >= s.top) cur = i; });
    if (cur !== currentScene) {
      currentScene = cur;
      sceneNo.textContent = pad(cur + 1);
      sceneName.textContent = scenes[cur].name;
      sceneName.classList.remove("is-swap");
      void sceneName.offsetWidth;
      sceneName.classList.add("is-swap");
      $$(".js-index-list a").forEach((a, i) => a.setAttribute("aria-current", i === cur ? "true" : "false"));
    }
  }

  // ── Scene index (full-screen menu) ────────────────────────────────────────────────────────────────────
  const indexEl = $("#index"), menuBtn = $(".hud__menu"), listEl = $(".js-index-list"), mainEl = $("#main");
  function buildIndex() {
    listEl.innerHTML = scenes.map((s, i) =>
      `<li><a href="#${s.id}" data-i="${i}" style="transition-delay:${0.12 + i * 0.05}s"><span class="index__no">${pad(i + 1)}</span>` +
      `<span class="index__name">${s.name}</span><span class="index__tc">${timecode(s.top)}</span></a></li>`).join("");
    if (currentScene >= 0) listEl.children[currentScene]?.firstChild.setAttribute("aria-current", "true");
  }
  function setIndex(open, focusBack = true) {
    doc.classList.toggle("is-index", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    $(".hud__menu-text").textContent = open ? "Close" : "Index";
    menuBtn.dataset.cursor = open ? "Close" : "Open";
    if (FINE && cursor.classList.contains("is-label")) cLabel.textContent = menuBtn.dataset.cursor;
    indexEl.inert = !open;
    mainEl.inert = open;
    if (open) setTimeout(() => listEl.querySelector("a")?.focus({ preventScroll: true }), 300);
    else if (focusBack) menuBtn.focus({ preventScroll: true });
  }
  menuBtn.addEventListener("click", () => setIndex(!doc.classList.contains("is-index")));
  addEventListener("keydown", (e) => { if (e.key === "Escape" && doc.classList.contains("is-index")) setIndex(false); });
  listEl.addEventListener("click", (e) => {
    const a = e.target.closest("a");
    if (!a) return;
    e.preventDefault();
    const s = scenes[+a.dataset.i];
    // A cut, not a scrub: jump while the panel covers the screen, then pull it away
    scrollTo({ top: s.top + (s.id === "opening" ? 0 : 2), behavior: "instant" });
    S.sy = S.y = S.py = scrollY;
    setIndex(false, false);
    const h = s.el.querySelector("h1, h2");
    if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); }
  });
  $(".hud__logo").addEventListener("click", (e) => {
    e.preventDefault();
    scrollTo({ top: 0, behavior: "instant" }); // the smoothed playhead rewinds through the reel on its own
  });

  // ── 01 Opening ────────────────────────────────────────────────────────────────────────────────────────
  const hero = (() => {
    const s = byId("opening");
    const stage = $(".hero__stage", s.el);
    const film = $(".hero__film", s.el);
    const video = $(".js-film", s.el);
    const paper = $(".js-paper", s.el);
    const zoomG = $(".js-wm-zoom", s.el);
    const letters = $$(".js-wm-l", s.el);
    const rule = $(".hero__rule", s.el);
    const ui = $(".js-hero-ui", s.el);
    const shade = $(".hero__shade", s.el);
    const endLabel = $(".hero__end-label", s.el), endSub = $(".hero__end-sub", s.el);
    const endChars = splitChars($(".js-chars", s.el));
    // the lede: one masked line per <br>
    const lede = $(".js-lines", s.el);
    lede.innerHTML = lede.innerHTML.split(/<br\s*\/?>/i).map((l, i) => `<span class="line"><span style="transition-delay:${0.55 + i * 0.1}s">${l.trim()}</span></span>`).join("");
    $$(".js-rise", s.el).forEach((el, i) => { el.style.transitionDelay = `${0.35 + i * 0.08}s`; });

    const IX = 309.576, IY = 33.79, STEM = 9.52; // centre and width of the I stem in wordmark units
    let b = 1, ox = 0, oy = 0, maxS = 80;
    measureHooks.push(() => {
      b = Math.min(S.vw * (S.vw < 700 ? 0.9 : 0.86), 1700) / 640;
      ox = (S.vw - 640 * b) / 2;
      oy = S.vh * 0.5 - 34 * b - (S.vw < 700 ? S.vh * 0.03 : 0);
      maxS = (Math.max(S.vw, S.vh * 0.2) * 1.25) / (STEM * b);
      stage.style.setProperty("--wm-h", `${68 * b}px`);
      if (video.dataset.land && !RM) {
        const want = S.vw / S.vh < 0.8 ? video.dataset.port : video.dataset.land;
        if (!video.src.endsWith(want.replace("../", ""))) { video.src = want; video.load(); }
      }
    });
    let playing = false;

    s.update = (p, vis) => {
      if (!vis) { if (playing) { video.pause(); playing = false; } return; }
      if (!playing && !RM && S.ready) { playing = true; video.play().catch(() => { playing = false; }); }

      // Letters rise into place once the count-in lifts
      const since = S.ready ? S.t - S.revealAt : 0;
      letters.forEach((l, i) => {
        const e = RM ? 1 : E.outExpo(clamp((since - i * 0.065) / 1.25));
        l.setAttribute("transform", `translate(0 ${((1 - e) * 82).toFixed(2)})`);
      });
      const ruleE = RM ? 1 : E.inOutExpo(clamp((since - 0.5) / 1.3));

      // Fly through the I
      const zp = RM ? 0 : E.inOut3(range(p, 0.08, 0.64));
      const k = Math.exp(Math.log(maxS) * zp);
      const ix = ox + IX * b, iy = oy + IY * b;
      const cx = lerp(ix, S.vw / 2, zp), cy = lerp(iy, S.vh / 2, zp);
      zoomG.setAttribute("transform", `translate(${cx.toFixed(2)} ${cy.toFixed(2)}) scale(${(b * k).toFixed(4)}) translate(${-IX} ${-IY})`);
      paper.style.opacity = RM ? 1 - range(p, 0.12, 0.45) : 1 - range(p, 0.56, 0.64);

      const ry = oy + 68 * b + Math.max(10, 16 * b);
      rule.setAttribute("x1", ox.toFixed(1));
      rule.setAttribute("x2", (ox + 640 * b * ruleE).toFixed(1));
      rule.setAttribute("y1", ry.toFixed(1));
      rule.setAttribute("y2", ry.toFixed(1));
      rule.style.opacity = 1 - range(p, 0.02, 0.1);

      const fade = range(p, 0.02, 0.14);
      ui.style.opacity = 1 - fade;
      ui.style.transform = `translate3d(0, ${-fade * 40}px, 0)`;

      const mxn = S.mouseIn ? (S.rx / S.vw - 0.5) : 0, myn = S.mouseIn ? (S.ry / S.vh - 0.5) : 0;
      film.style.transform = RM ? "" : `translate3d(${-mxn * 24}px, ${-myn * 18}px, 0) scale(${1.22 - 0.16 * zp + 0.06 * range(p, 0.64, 1)})`;
      shade.style.opacity = range(p, 0.55, 0.75);

      const q = range(p, 0.66, 0.86);
      const n = endChars.length;
      endChars.forEach((c, i) => {
        const d = (i / n) * 0.45;
        const e = RM ? (q > 0 ? 1 : 0) : E.outExpo(range(q, d, d + 0.55));
        c.style.transform = `translate3d(0, ${((1 - e) * 112).toFixed(1)}%, 0) rotate(${((1 - e) * 8).toFixed(2)}deg)`;
      });
      endLabel.style.opacity = range(p, 0.66, 0.74);
      endSub.style.opacity = range(p, 0.78, 0.88);
      endSub.style.transform = `translate3d(0, ${(1 - E.out3(range(p, 0.78, 0.9))) * 20}px, 0)`;
    };
    return s;
  })();

  // ── 02 Manifesto ──────────────────────────────────────────────────────────────────────────────────────
  (() => {
    const s = byId("manifesto");
    const p = $(".js-words", s.el);
    const items = [];
    [...p.childNodes].forEach((node) => {
      if (node.nodeType === 3) {
        const frag = document.createDocumentFragment();
        node.textContent.split(/(\s+)/).forEach((w) => {
          if (!w) return;
          if (/^\s+$/.test(w)) { frag.appendChild(document.createTextNode(" ")); return; }
          const span = document.createElement("span");
          span.className = "w";
          span.textContent = w;
          frag.appendChild(span);
          items.push({ el: span, pill: false, last: -1 });
        });
        node.replaceWith(frag);
      } else if (node.classList?.contains("pill")) {
        items.push({ el: node, pill: true, svg: node.firstElementChild, last: -1 });
      }
    });
    s.update = (pr) => {
      const reveal = range(pr, 0.06, 0.82) * (items.length + 2);
      items.forEach((it, i) => {
        const a = RM ? (reveal > i ? 1 : 0) : clamp(reveal - i);
        if (Math.abs(a - it.last) < 0.002) return;
        it.last = a;
        if (it.pill) {
          const e = E.out3(a);
          it.el.style.width = `${(e * 1.5).toFixed(3)}em`;
          it.svg.style.transform = `translateY(.16em) scale(${(0.4 + 0.6 * E.outBack(a)).toFixed(3)}) rotate(${((1 - a) * -20).toFixed(1)}deg)`;
        } else {
          it.el.style.opacity = (0.14 + 0.86 * a).toFixed(3);
        }
      });
    };
  })();

  // ── 03 Fibres: a field of strands that re-forms as each fibre ─────────────────────────────────────────
  (() => {
    const s = byId("fibres");
    const stage = $(".js-fibre-stage", s.el);
    const cv = $(".js-fibre-canvas", s.el);
    const ctx = cv.getContext("2d");
    const names = $$(".js-fibre-name", s.el);
    const specs = $$(".js-fibre-spec", s.el);
    const roll = $(".js-fibre-no", s.el);
    names.forEach((n) => splitChars(n).forEach((c, i) => { c.style.transitionDelay = `${i * 0.035}s`; }));

    const N = 132, M = 84;
    const sd = Array.from({ length: N }, () => [rand(), rand(), rand(), rand(), rand(), rand()]);
    const BG = ["#2f3d33", "#e9e3d3", "#fbfaf8", "#1b211d"].map(hexToRgb);
    const ST = [[233, 227, 211, 0.5], [27, 33, 29, 0.42], [27, 33, 29, 0.3], [176, 138, 91, 0.62]];
    const LW = [1.15, 1, 0.9, 0.55];
    const FG = ["#fbfaf8", "#1b211d", "#1b211d", "#fbfaf8"];
    const BOLLS = [[0.16, 0.3], [0.5, 0.2], [0.84, 0.32], [0.3, 0.66], [0.66, 0.6], [0.9, 0.78], [0.08, 0.86]];
    let W = 0, H = 0, dpr = 1, active = -1;
    measureHooks.push(() => {
      dpr = Math.min(devicePixelRatio || 1, 1.75);
      W = S.vw; H = S.vh;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    });

    const o = { x: 0, y: 0 };
    function gen(mode, i, u, t) {
      const r = sd[i];
      switch (mode) {
        case 0: { // wool: crimped, springy waves
          const a = u * (30 + r[3] * 22) + r[1] * 6.283 + t * 0.9;
          const amp = 4 + r[4] * 7;
          o.x = -0.1 * W + u * 1.2 * W + Math.cos(a) * amp * 0.8;
          o.y = H * (0.05 + 0.9 * r[0]) + Math.sin(u * 3 + r[2] * 6 + t * 0.25) * H * 0.05 + Math.sin(a) * amp;
          break;
        }
        case 1: { // linen: long straight warp and weft, over and under
          const k = i >> 1, half = N / 2;
          const weave = Math.sin(u * 140 + k * Math.PI) * 1.4 + Math.sin(t * 0.5 + k) * 1.5;
          if (i % 2 === 0) { o.x = -0.05 * W + u * 1.1 * W; o.y = H * ((k + 0.5) / half) + weave; }
          else { o.y = -0.05 * H + u * 1.1 * H; o.x = W * ((k + 0.5) / half) + weave; }
          break;
        }
        case 2: { // cotton: soft bolls
          const c = BOLLS[i % BOLLS.length];
          const R = Math.min(W, H) * (0.12 + 0.05 * ((i % BOLLS.length) % 3)) ;
          const a = u * (2 + r[0] * 1.6) * 6.283 + r[1] * 6.283 + t * 0.16 * (r[2] > 0.5 ? 1 : -1);
          const rr = R * (0.22 + 0.78 * Math.sqrt(r[3])) * (1 + 0.2 * Math.sin(u * 19 + r[4] * 6 + t * 0.9));
          o.x = c[0] * W + Math.cos(a) * rr * 1.08;
          o.y = c[1] * H + Math.sin(a) * rr * 0.9;
          break;
        }
        default: { // cashmere: fine, combed, flowing
          o.x = -0.12 * W + u * 1.24 * W;
          o.y = H * (r[0] * 1.1 - 0.05) + Math.sin(u * 2.4 + r[1] * 1.2 + t * 0.35) * H * 0.13 +
            Math.sin(u * 7 + r[2] * 6 + t * 0.7) * H * 0.012 + (u - 0.5) * H * 0.28;
        }
      }
      return o;
    }

    function setActive(a) {
      if (a === active) return;
      active = a;
      names.forEach((n, j) => { n.classList.toggle("is-on", j === a); n.classList.toggle("is-gone", j < a); });
      specs.forEach((sp, j) => sp.classList.toggle("is-on", j === a));
      roll.style.setProperty("--i", a);
      $$("span", roll).forEach((x) => x.style.setProperty("--i", a));
      stage.style.color = FG[a];
    }

    s.update = (p, vis) => {
      if (!vis) return;
      const f = range(p, 0.06, 0.94) * 3;
      const k = Math.min(2, Math.floor(f));
      const blend = E.inOut3(range(f - k, 0.5, 1));
      setActive(blend > 0.5 ? k + 1 : k);
      const t = RM ? 0 : S.t;
      const bg = mixRgb(BG[k], BG[k + 1], blend);
      const st = ST[k].map((v, i) => lerp(v, ST[k + 1][i], blend));
      const swirl = RM ? 0 : Math.sin(blend * Math.PI);
      const mx = S.mouseIn ? S.rx : -9999, my = S.mouseIn ? S.ry : -9999;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = `rgb(${bg})`;
      ctx.fillRect(0, 0, W, H);
      const a = { x: 0, y: 0 };
      const paths = [new Path2D(), new Path2D()];
      for (let i = 0; i < N; i++) {
        const path = paths[i % 11 === 0 ? 1 : 0];
        for (let j = 0; j < M; j++) {
          const u = j / (M - 1);
          gen(k, i, u, t); a.x = o.x; a.y = o.y;
          gen(k + 1, i, u, t);
          let x = lerp(a.x, o.x, blend) + Math.sin(i * 1.7 + u * 5 + t) * 60 * swirl;
          let y = lerp(a.y, o.y, blend) + Math.cos(i * 2.3 + u * 4 + t) * 60 * swirl;
          const dx = x - mx, dy = y - my, d2 = dx * dx + dy * dy;
          if (d2 < 32400) { const d = Math.sqrt(d2) || 1, push = Math.pow(1 - d / 180, 2) * 70; x += (dx / d) * push; y += (dy / d) * push; }
          if (j === 0) path.moveTo(x, y); else path.lineTo(x, y);
        }
      }
      ctx.lineJoin = "round";
      ctx.lineWidth = lerp(LW[k], LW[k + 1], blend);
      ctx.strokeStyle = `rgba(${st[0] | 0},${st[1] | 0},${st[2] | 0},${st[3].toFixed(3)})`;
      ctx.stroke(paths[0]);
      ctx.lineWidth += 0.4;
      ctx.strokeStyle = "rgba(163,71,31,.85)";
      ctx.stroke(paths[1]);
    };
  })();

  // ── 04 Collection: a moving rail of looks ─────────────────────────────────────────────────────────────
  (() => {
    const s = byId("collection");
    const track = $(".js-looks-track", s.el);
    const ghost = $(".js-looks-ghost", s.el);
    const bar = $(".js-looks-bar", s.el);
    const count = $(".js-looks-count", s.el);
    const looks = $$(".look", s.el).map((li) => {
      const media = $(".look__media", li);
      // Photography drops in here: set data-image="../assets/img/looks/look-01.jpg" on the <li>
      if (li.dataset.image) {
        const name = $(".look__name", li).textContent;
        media.innerHTML = `<img src="${li.dataset.image}" alt="${name}" loading="lazy" decoding="async">`;
      }
      return { li, fig: $("figure", li), media, x: 0, w: 0, seen: false };
    });
    let travel = 0, skew = 0;
    measureHooks.push(() => {
      track.style.transform = "none";
      travel = Math.max(0, track.scrollWidth - S.vw);
      looks.forEach((l) => { l.x = l.li.offsetLeft; l.w = l.li.offsetWidth; });
      s.el.style.height = `${travel + S.vh * 1.35}px`;
    });
    s.update = (p, vis) => {
      if (!vis) return;
      const x = -travel * range(p, 0.04, 0.96);
      track.style.transform = `translate3d(${x.toFixed(1)}px,0,0)`;
      ghost.style.transform = `translate3d(${(x * 0.3).toFixed(1)}px,-50%,0)`;
      skew = lerp(skew, RM ? 0 : clamp(S.vel * 0.18, -9, 9), 0.12);
      let best = 0, bestD = 1e9;
      looks.forEach((l, i) => {
        const cx = l.x + x + l.w / 2;
        const rel = (cx - S.vw / 2) / S.vw;
        if (Math.abs(rel) < bestD) { bestD = Math.abs(rel); best = i; }
        if (!l.seen && cx - l.w / 2 < S.vw * 0.98) { l.seen = true; l.li.classList.add("is-in"); }
        if (Math.abs(rel) > 1.2) return;
        l.fig.style.transform = RM ? "" : `rotateY(${(rel * -16).toFixed(2)}deg) skewX(${skew.toFixed(2)}deg)`;
        l.media.style.transform = RM ? "" : `translate3d(${(rel * -9).toFixed(2)}%,0,0)`;
      });
      bar.style.transform = `scaleX(${range(p, 0.04, 0.96)})`;
      count.textContent = `${pad(best + 1)} / ${pad(looks.length)}`;
    };
  })();

  // ── 05 Construction: pattern pieces become a shirt ────────────────────────────────────────────────────
  (() => {
    const s = byId("construction");
    const NS = "http://www.w3.org/2000/svg";
    const mk = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); parent?.appendChild(n); return n; };
    const piecesG = $(".js-pieces", s.el), stitchG = $(".js-stitches", s.el), maskG = $(".js-stitch-mask", s.el);
    const buttonsG = $(".js-buttons", s.el), tag = $(".js-tag", s.el), swing = $(".js-tag-swing", s.el), ruler = $(".js-ruler", s.el);
    const steps = $$(".js-steps li", s.el);
    const stPieces = $(".js-stat-pieces", s.el), stSeams = $(".js-stat-seams", s.el), stButtons = $(".js-stat-buttons", s.el);

    // Cutting-mat ruler: a tick every 20 units, a number every 100 (10 cm)
    for (let x = 0; x <= 1200; x += 20) mk("line", { x1: x, y1: 0, x2: x, y2: x % 100 ? 6 : 12 }, ruler);
    for (let y = 0; y <= 760; y += 20) mk("line", { x1: 0, y1: y, x2: y % 100 ? 6 : 12, y2: y }, ruler);
    for (let x = 100; x < 1200; x += 100) mk("text", { x: x + 3, y: 22 }, ruler).textContent = x / 10;
    for (let y = 100; y < 760; y += 100) mk("text", { x: 16, y: y + 3 }, ruler).textContent = y / 10;

    // Pieces in finished-shirt coordinates (400 x 500), and where each lies on the mat before sewing
    const P = [
      { d: "M200 92 Q182 90 170 72 L130 84 L106 94 Q100 150 94 206 L96 404 Q150 426 200 418 Z", l: "Left front", n: "Cut 1 · self", f: [-405, -8, 0] },
      { d: "M200 92 Q218 90 230 72 L270 84 L294 94 Q300 150 306 206 L304 404 Q250 426 200 418 Z", l: "Right front", n: "Cut 1 · self", f: [405, -8, 0] },
      { d: "M106 94 L82 104 Q66 112 64 132 L52 346 L94 352 L94 206 Q100 150 106 94 Z", l: "Sleeve", n: "Cut 2 · pair", f: [-60, -280, -90] },
      { d: "M294 94 L318 104 Q334 112 336 132 L348 346 L306 352 L306 206 Q300 150 294 94 Z", l: "Sleeve", n: "Cut 2 · pair", f: [60, -280, 90] },
      { d: "M164 64 Q200 54 236 64 L232 74 L216 104 L200 92 L184 104 L168 74 Z", l: "Collar", n: "Cut 2 · fuse 1", f: [0, 470, 0] },
      { d: "M52 348 L94 352 L93 376 L51 372 Z", l: "Cuff", n: "Cut 4", f: [-150, 200, 0] },
      { d: "M348 348 L306 352 L307 376 L349 372 Z", l: "Cuff", n: "Cut 4", f: [150, 200, 0] },
      { d: "M222 150 L262 150 L262 192 L242 198 L222 192 Z", l: "Pocket", n: "Cut 1", f: [-42, 120, -14] },
    ];
    const pieces = P.map((pc) => {
      const g = mk("g", { class: "piece" }, piecesG);
      const cut = mk("path", { d: pc.d, class: "piece__cut", fill: "url(#poplin)", "fill-opacity": 0, pathLength: 1, "stroke-dasharray": "1 1", "stroke-dashoffset": 1 }, g);
      const bb = cut.getBBox();
      const cx = bb.x + bb.width / 2, cy = bb.y + bb.height / 2;
      const meta = mk("g", { class: "piece__meta" }, g);
      if (bb.height > 60) {
        const gl = Math.min(bb.height * 0.5, 160);
        mk("path", { d: `M${cx} ${cy - gl / 2 + 14} V${cy + gl / 2 - 30} M${cx - 4} ${cy - gl / 2 + 22} L${cx} ${cy - gl / 2 + 14} L${cx + 4} ${cy - gl / 2 + 22} M${cx - 4} ${cy + gl / 2 - 38} L${cx} ${cy + gl / 2 - 30} L${cx + 4} ${cy + gl / 2 - 38}`, class: "piece__grain" }, meta);
      }
      const big = bb.height > 60;
      const lbl = mk("text", { x: cx, y: big ? cy + bb.height * 0.22 : cy - 16, "text-anchor": "middle", class: "piece__label" }, meta);
      lbl.textContent = pc.l;
      const note = mk("text", { x: cx, y: big ? cy + bb.height * 0.22 + 14 : cy - 4, "text-anchor": "middle", class: "piece__note" }, meta);
      note.textContent = pc.n;
      if (!big) { lbl.setAttribute("y", bb.y - 22); note.setAttribute("y", bb.y - 9); }
      return { g, cut, meta, cx, cy, f: pc.f };
    });

    const SEAMS = [
      "M172 77 L131 89 L108 98", "M228 77 L269 89 L292 98",
      "M108 99 Q102 152 98 204", "M292 99 Q298 152 302 204",
      "M99 214 L100 398", "M301 214 L300 398",
      "M69 132 L57 342", "M331 132 L343 342",
      "M56 355 L90 359", "M344 355 L310 359",
      "M101 398 Q150 417 200 411 Q250 417 299 398",
      "M207 100 L207 410",
      "M226 154 L258 154 L258 189 L242 194 L226 189 Z",
      "M169 69 Q200 60 231 69",
    ];
    const maskWrap = mk("g", { transform: "translate(380 110) scale(1.1)" }, maskG);
    const twins = SEAMS.map((d) => { mk("path", { d }, stitchG); return mk("path", { d, pathLength: 1, "stroke-dasharray": "1 1", "stroke-dashoffset": 1 }, maskWrap); });
    const buttons = [120, 165, 210, 255, 300, 345, 390].map((y) => {
      const g = mk("g", { transform: `translate(200 ${y}) scale(0)` }, buttonsG);
      mk("circle", { r: 5.5, fill: "#ecebe6", stroke: "#1b211d", "stroke-width": 0.9 }, g);
      mk("circle", { cx: -1.6, cy: 0, r: 0.9, fill: "#1b211d" }, g);
      mk("circle", { cx: 1.6, cy: 0, r: 0.9, fill: "#1b211d" }, g);
      return g;
    });
    stPieces.textContent = pad(P.length);

    let lastP = -1;
    s.update = (p, vis) => {
      if (!vis || Math.abs(p - lastP) < 0.0004) return;
      lastP = p;
      const cut = RM ? 1 : E.out3(range(p, 0.02, 0.16));
      const metaO = range(p, 0.06, 0.16) * (1 - range(p, 0.42, 0.56));
      const fill = range(p, 0.5, 0.64);
      pieces.forEach((pc, i) => {
        const a = E.inOut3(range(p, 0.18 + i * 0.035, 0.42 + i * 0.035));
        const k = 1 - a;
        pc.g.setAttribute("transform", `translate(${(pc.f[0] * k).toFixed(2)} ${(pc.f[1] * k).toFixed(2)}) rotate(${(pc.f[2] * k).toFixed(2)} ${pc.cx} ${pc.cy})`);
        pc.cut.setAttribute("stroke-dashoffset", (1 - cut).toFixed(3));
        pc.cut.setAttribute("fill-opacity", (0.18 * cut + 0.82 * fill).toFixed(3));
        pc.meta.style.opacity = metaO;
      });
      const st = range(p, 0.62, 0.8);
      let seams = 0;
      twins.forEach((t, i) => {
        const d = (i / twins.length) * 0.6;
        const e = range(st, d, d + 0.4);
        if (e >= 1) seams++;
        t.setAttribute("stroke-dashoffset", (1 - e).toFixed(3));
      });
      const bt = range(p, 0.78, 0.88);
      let nb = 0;
      buttons.forEach((g, i) => {
        const e = range(bt, i * 0.09, i * 0.09 + 0.4);
        if (e > 0.5) nb++;
        g.setAttribute("transform", `translate(200 ${120 + i * 45}) scale(${Math.max(0, E.outBack(e)).toFixed(3)})`);
      });
      const tq = range(p, 0.86, 0.97);
      const drop = (1 - E.outBack(tq)) * -340;
      const ang = Math.sin(tq * 13) * (1 - tq) * 26;
      tag.setAttribute("transform", `translate(860 ${(200 + drop).toFixed(1)})`);
      tag.style.opacity = tq > 0 ? 1 : 0;
      swing.setAttribute("transform", `rotate(${ang.toFixed(2)} 0 -60)`);

      const phases = [[0, 0.18], [0.18, 0.66], [0.62, 0.8], [0.78, 0.97]];
      steps.forEach((li, i) => {
        const ph = range(p, phases[i][0], phases[i][1]);
        li.style.setProperty("--p", ph.toFixed(3));
        li.classList.toggle("is-on", p >= phases[i][0]);
      });
      stSeams.textContent = pad(seams);
      stButtons.textContent = nb;
    };
  })();

  // ── 06 Numbers: belts of type and odometers ───────────────────────────────────────────────────────────
  (() => {
    const s = byId("numbers");
    const belts = $$(".js-marquee", s.el).map((m) => {
      const row = m.firstElementChild;
      const one = row.innerHTML;
      row.innerHTML = one.repeat(4);
      return { row, dir: +m.dataset.dir, x: 0, w: 0, one };
    });
    measureHooks.push(() => belts.forEach((b) => { b.w = b.row.scrollWidth / 4; }));
    let sk = 0, drift = 1;
    s.update = (p, vis) => {
      if (!vis) return;
      if (Math.abs(S.vel) > 0.5) drift = Math.sign(S.vel);
      sk = lerp(sk, RM ? 0 : clamp(-S.vel * 0.22, -14, 14), 0.1);
      belts.forEach((b) => {
        if (!RM) b.x -= b.dir * (drift * 1.1 + S.vel * 0.35);
        if (b.w) { b.x %= b.w; if (b.x > 0) b.x -= b.w; }
        b.row.style.transform = `translate3d(${b.x.toFixed(1)}px,0,0) skewX(${(sk * b.dir).toFixed(2)}deg)`;
      });
    };

    const odos = $$(".js-odo", s.el).map((el) => {
      const target = el.dataset.to;
      el.textContent = "";
      const cols = [...target].map((d, i) => {
        const col = document.createElement("span");
        col.className = "col";
        col.setAttribute("aria-hidden", "true");
        col.innerHTML = Array.from({ length: 30 }, (_, k) => `<span>${k % 10}</span>`).join("");
        col.style.transitionDelay = `${i * 0.14}s`;
        el.appendChild(col);
        return { col, to: 20 + +d };
      });
      return { el, cols };
    });
    const io = new IntersectionObserver((ents) => ents.forEach((e) => {
      if (!e.isIntersecting) return;
      const o = odos.find((x) => x.el === e.target);
      o.cols.forEach((c) => { c.col.style.transform = `translateY(${-c.to}em)`; });
      io.unobserve(e.target);
    }), { threshold: 0.6 });
    odos.forEach((o) => {
      if (RM) o.cols.forEach((c) => { c.col.style.transition = "none"; c.col.style.transform = `translateY(${-c.to}em)`; });
      else io.observe(o.el);
    });
  })();

  // ── 07 Sign-up, credits, footer ───────────────────────────────────────────────────────────────────────
  (() => {
    const s = byId("signup");
    const chars = splitChars($(".js-wave", s.el)).map((c) => c.parentElement);
    const roll = $(".js-credits", s.el);
    const wm = $(".js-foot-wm", s.el);
    const uses = $$("use", wm);
    uses.forEach((u, i) => {
      u.style.transform = "translateY(115%)";
      u.style.transition = `transform 1.4s cubic-bezier(.22,1,.36,1) ${i * 0.06}s`;
    });
    wm.style.overflow = "hidden";
    const wio = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { uses.forEach((u) => { u.style.transform = "none"; }); wio.disconnect(); }
    }, { threshold: 0.3 });
    wio.observe(wm);

    let lastW = chars.map(() => 400);
    s.update = (p, vis) => {
      if (!vis) return;
      chars.forEach((c, i) => {
        let f;
        if (S.mouseIn) {
          const r = c.getBoundingClientRect();
          const dx = r.left + r.width / 2 - S.rx, dy = r.top + r.height / 2 - S.ry;
          f = Math.exp(-(dx * dx + dy * dy) / (2 * 150 * 150));
        } else f = RM ? 0 : 0.5 + 0.5 * Math.sin(S.t * 2.2 - i * 0.45);
        const w = Math.round((400 + 300 * f) / 10) * 10;
        if (w !== lastW[i]) { lastW[i] = w; c.style.fontWeight = w; c.style.color = f > 0.55 ? "var(--camel)" : ""; }
      });
      const rh = roll.scrollHeight;
      roll.style.transform = RM ? "translateY(-220px)" : `translate3d(0, ${-((S.t * 28) % rh)}px, 0)`;
    };

    const form = $(".js-signup", s.el), input = $("#email", s.el), msg = $(".js-signup-msg", s.el);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = input.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) {
        input.setAttribute("aria-invalid", "true");
        msg.classList.add("is-error");
        msg.textContent = "Enter an email address, like name@example.com.";
        input.focus();
        return;
      }
      input.removeAttribute("aria-invalid");
      msg.classList.remove("is-error");
      form.classList.add("is-done");
      msg.textContent = "Thanks. You'll get one email when the shop opens.";
      // Hook for an email provider, as on the shop (see README)
      if (typeof window.A88?.subscribe === "function") window.A88.subscribe(v, ["launch"]);
    });
    input.addEventListener("input", () => { if (input.hasAttribute("aria-invalid")) { input.removeAttribute("aria-invalid"); msg.textContent = ""; } });
  })();

  // ── Count-in ──────────────────────────────────────────────────────────────────────────────────────────
  const intro = $(".intro");
  function reveal() {
    S.ready = true;
    S.revealAt = S.t;
    body.classList.remove("is-loading");
    body.classList.add("is-ready");
  }
  (function countIn() {
    if (RM || scrollY > S.vh) { intro.classList.add("is-gone"); reveal(); return; }
    body.classList.add("is-loading");
    const countEl = $(".js-count"), barEl = $(".js-intro-bar"), state = $(".js-intro-state");
    const line = $(".intro__mono-line"), fill = $(".intro__mono-fill");
    const fontsReady = Promise.race([document.fonts?.ready ?? Promise.resolve(), new Promise((r) => setTimeout(r, 2500))]);
    let fontsOk = false;
    fontsReady.then(() => { fontsOk = true; });
    let start = performance.now(), done = false;
    const DUR = 2000;
    const skip = () => { start -= DUR; };
    intro.addEventListener("click", skip);
    addEventListener("keydown", skip, { once: true });
    (function step(now) {
      const q = clamp((now - start) / DUR);
      const e = E.inOut3(q);
      countEl.textContent = pad(Math.round(88 * e));
      barEl.style.transform = `scaleX(${e})`;
      line.style.strokeDashoffset = 1 - E.out3(q);
      fill.style.opacity = range(q, 0.75, 1);
      if (q < 1 || !fontsOk) { requestAnimationFrame(step); return; }
      if (done) return;
      done = true;
      state.textContent = "Rolling";
      setTimeout(() => {
        intro.classList.add("is-out");
        setTimeout(reveal, 450);
        setTimeout(() => intro.classList.add("is-gone"), 1600);
      }, 260);
    })(start);
  })();

  // ── Loop ──────────────────────────────────────────────────────────────────────────────────────────────
  let last = performance.now();
  function tick(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    S.t += dt;
    const k = RM ? 1 : 1 - Math.pow(1 - 0.13, dt * 60);
    S.y = lerp(S.y, S.sy, k);
    if (Math.abs(S.y - S.sy) < 0.05) S.y = S.sy;
    S.vel = (S.y - S.py) / Math.max(dt * 60, 0.5);
    S.py = S.y;
    scenes.forEach((s) => s.update && s.update(progress(s), visible(s)));
    hud();
    drawCursor();
    requestAnimationFrame(tick);
  }

  let rw = innerWidth, rh = innerHeight, rt;
  addEventListener("resize", () => {
    clearTimeout(rt);
    rt = setTimeout(() => {
      if (innerWidth === rw && Math.abs(innerHeight - rh) < 120) return; // ignore phone toolbar wobble
      rw = innerWidth; rh = innerHeight;
      measure();
    }, 120);
  });
  measure();
  document.fonts?.ready.then(measure);
  addEventListener("load", measure);
  requestAnimationFrame(tick);
})();
