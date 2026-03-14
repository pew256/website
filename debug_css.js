const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://localhost:8085/admin.html');
  await page.click('#btn-view-list');
  await page.waitForTimeout(1000);
  
  const styles = await page.evaluate(() => {
    const card = document.querySelector('.dashboard-card');
    const content = card.querySelector('.card-content');
    const title = card.querySelector('.card-title');
    return {
      cardDisplay: getComputedStyle(card).display,
      cardGridCols: getComputedStyle(card).gridTemplateColumns,
      contentDisplay: getComputedStyle(content).display,
      contentWidth: getComputedStyle(content).width,
      titleDisplay: getComputedStyle(title).display,
      titleFontSize: getComputedStyle(title).fontSize,
      cardPadding: getComputedStyle(card).padding
    };
  });
  console.log(JSON.stringify(styles, null, 2));
  await browser.close();
})();
