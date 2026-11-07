/* Archive 88: product page (needs site.js first) */
(() => {
  const { $, $$, motion } = window.A88;
  const slides = $(".js-slides");
  const pager = $$(".js-pager i");

  /* Phones: photos swipe sideways; the pager line under them follows along. */
  if (slides && pager.length > 1 && "IntersectionObserver" in window) {
    const figs = $$(".pdp__slide", slides);
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting && en.intersectionRatio > 0.6) {
          const i = figs.indexOf(en.target);
          pager.forEach((p, j) => p.classList.toggle("is-on", j === i));
        }
      });
    }, { root: slides, threshold: [0.6] });
    figs.forEach((f) => io.observe(f));
  }

  if (!motion) return;

  /* Entrance: first photo unmasks upward, details rise in one after another. */
  const first = $(".pdp__slide");
  gsap.timeline({ defaults: { ease: "expo.out" } })
    .from(".nav", { autoAlpha: 0, y: -12, duration: 0.8 }, 0)
    .fromTo(first, { clipPath: "inset(100% 0% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 1.3 }, 0.05)
    .from($("img, svg", first), { scale: 1.12, duration: 1.6 }, 0.05)
    .from(".crumbs", { autoAlpha: 0, y: 10, duration: 0.8 }, 0.2)
    .from($$(".js-pdp-in"), { opacity: 0, y: 24, duration: 1, stagger: 0.07 }, 0.25);

  /* Desktop: later photos unmask as they scroll into view. */
  $$(".pdp__slide").slice(1).forEach((s) => {
    gsap.fromTo(s, { clipPath: "inset(12% 0% 0% 0%)", autoAlpha: 0.4 }, {
      clipPath: "inset(0% 0% 0% 0%)", autoAlpha: 1, duration: 1.1, ease: "expo.out",
      scrollTrigger: { trigger: s, start: "top 88%", once: true },
    });
  });
})();
