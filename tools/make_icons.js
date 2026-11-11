// Archive 88: renders the share image and app icons from the logo files.
//   node tools/make_icons.js        (needs Playwright; only when the logo, palette or campaign picture changes)
// Writes assets/img/og-image.jpg (1200 x 630), icon-512.png and apple-touch-icon.png (180).
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const svg = (f, colour) => read(f).replace('fill="currentColor"', `fill="${colour}"`);
const uri = (f) => `data:image/jpeg;base64,${fs.readFileSync(path.join(root, f)).toString("base64")}`;
const font = (f) => `data:font/woff2;base64,${fs.readFileSync(path.join(root, f)).toString("base64")}`;
const store = JSON.parse(read("data/store.json"));

const og = `<body style="margin:0;width:1200px;height:630px;position:relative;overflow:hidden;background:#17271f;color:#efebe1">
<style>@font-face{font-family:G;src:url(${font("assets/fonts/geist-mono-latin.woff2")})}</style>
<img src="${uri("assets/img/forest-poster.jpg")}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">
<div style="position:absolute;inset:0;background:linear-gradient(20deg,rgba(14,24,19,.92),rgba(14,24,19,.45) 55%,rgba(14,24,19,.25))"></div>
<div style="position:absolute;left:72px;right:72px;bottom:150px">${svg("assets/brand/lockup.svg", "#efebe1")}</div>
<p style="position:absolute;left:72px;bottom:64px;margin:0;font:500 22px G;letter-spacing:.14em;text-transform:uppercase">${store.tagline}. ${store.established}.</p>
</body>`;
const icon = (size) => `<body style="margin:0;width:${size}px;height:${size}px;display:grid;place-items:center;background:#17271f">
<div style="width:64%">${svg("assets/brand/emblem.svg", "#efebe1")}</div></body>`;

(async () => {
  const browser = await chromium.launch();
  const shot = async (html, w, h, file, type) => {
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await page.setContent(html, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(root, file), type, ...(type === "jpeg" ? { quality: 86 } : {}) });
    await page.close();
  };
  await shot(og, 1200, 630, "assets/img/og-image.jpg", "jpeg");
  await shot(icon(512), 512, 512, "assets/img/icon-512.png", "png");
  await shot(icon(180), 180, 180, "assets/img/apple-touch-icon.png", "png");
  await browser.close();
  console.log("wrote og-image.jpg, icon-512.png, apple-touch-icon.png");
})();
