import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            locale='en-US',
            geolocation={'longitude': -122.4194, 'latitude': 37.7749},
            permissions=['geolocation'],
            color_scheme='dark'
        )
        page = await context.new_page()
        
        url = 'https://news.google.com/foryou?hl=en-US&gl=US&ceid=US%3Aen'
        print(f"Navigating to {url}")
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_timeout(3000)

        # Attempt to click common cookie consent buttons to remove overlays
        try:
            accept_texts = ['Accept all', 'Agree', 'Accept', 'Consens', 'Tout accepter', 'Accepter', 'I accept']
            reject_texts = ['Reject all', 'Tout refuser', 'Refuser']
            clicked = False
            for text in reject_texts + accept_texts:
                try:
                    buttons = await page.locator(f'button:has-text("{text}")').all()
                    for btn in buttons:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(1000)
                            clicked = True
                            break
                except:
                    pass
                if clicked:
                    break
        except:
            pass

        text = await page.evaluate('''() => {
            document.querySelectorAll('script, style, svg, iframe, nav, footer, header, aside').forEach(e => e.remove());
            
            let headlines = [];
            let links = document.querySelectorAll('a');
            links.forEach(a => {
                let txt = a.innerText.trim();
                // Google News For You page might need different filtering
                if (txt.split(' ').length > 2 && txt.length > 10 && !headlines.includes(txt)) {
                    headlines.push(txt);
                }
            });
            
            let root = document.querySelector('article') || document.querySelector('main') || document.body;
            let bodyText = root.innerText;
            
            if (headlines.length > 5) {
                return "HEADLINES:\\n" + headlines.join('\\n');
            }
            return bodyText;
        }''')
        
        print("\n--- EXTRACTED TEXT ---\n")
        print(text[:2000])
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
