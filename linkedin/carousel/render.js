// Render each .slide of index.html to PNG (1080x1350 at 2x) and a PDF carousel.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 1500 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.resolve(__dirname, 'index.html'));
  await p.waitForTimeout(500);
  const ids = await p.$$eval('.slide', s => s.map(x => x.id));
  for (const [i, id] of ids.entries()) {
    await p.locator('#' + id).screenshot({ path: path.resolve(__dirname, `slide_${i + 1}.png`) });
  }
  await b.close();
  console.log('rendered', ids.length);
})();
