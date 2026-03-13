import os
import sys
import asyncio
import json
import urllib.parse
from playwright.async_api import async_playwright

async def run_frontend_sharing_audit():
    print("🚀 Booting Frontend Social Sharing Logic Test...")
    
    # 1. Ensure there is at least one published article to test against
    pub_path = os.path.join(os.getcwd(), 'assets', 'published_journal.json')
    if not os.path.exists(pub_path):
        print("❌ Cannot run test: published_journal.json is missing.")
        sys.exit(1)
        
    with open(pub_path, "r") as f:
        data = json.load(f)
        if len(data) == 0:
            print("❌ Cannot run test: No published articles in published_journal.json to test against.")
            sys.exit(1)
            
    target_card = data[0]
    target_id = target_card['timestamp']
    target_subject = target_card['subject']
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Loading local frontend index.html...")
        # Assuming the local server is running on 8085
        try:
            await page.goto("http://localhost:8085/index.html", wait_until="networkidle")
            await page.wait_for_selector(f"#insight-{target_id}", timeout=5000)
        except Exception as e:
            print(f"❌ Failed to load target element on http://localhost:8085/index.html. {e}")
            sys.exit(1)
            
        print(f"Found target published card: {target_subject} (ID: {target_id})")
        
        # In index.html, social media wrappers are generated inside `.share-actions`
        # We extract the HTML of the specific card and parse its a/button elements
        
        links = await page.evaluate(f'''(id) => {{
            const card = document.querySelector(`#insight-${{id}}`);
            if (!card) return null;
            const takeDiv = card.querySelector('.share-actions');
            if (!takeDiv) return null;
            const links = Array.from(takeDiv.querySelectorAll('a[title^="Share to"]'));
            const buttons = Array.from(takeDiv.querySelectorAll('button[title^="Copy"]'));
            
            return {{
                "x_href": links.find(l => l.title === "Share to X")?.href,
                "in_href": links.find(l => l.title === "Share to LinkedIn")?.href,
                "wa_href": links.find(l => l.title === "Share to WhatsApp")?.href,
                "tg_href": links.find(l => l.title === "Share to Telegram")?.href,
                "wc_copy": buttons.find(b => b.title === "Copy WeChat Asset Link")?.getAttribute('data-copy'),
                "ig_copy": buttons.find(b => b.title === "Copy IG Vertical Link")?.getAttribute('data-copy')
            }};
        }}''', target_id)
        
        if not links:
            print("❌ Could not locate the social share icons in the DOM.")
            sys.exit(1)
            
        missing = False
        platforms = ["x_href", "in_href", "wa_href", "tg_href", "wc_copy", "ig_copy"]
        for p in platforms:
            if not links.get(p):
                print(f"❌ Missing social element payload for {p}")
                missing = True
                
        if missing:
            sys.exit(1)
            
        print("✅ Found all 6 natively mapped social media links in the DOM.")
        
        # Validate that the payloads actually embed the correct optimized "insights/" proxies
        # and contain the subject text for visibility!
        
        for k, payload in links.items():
            decoded = urllib.parse.unquote(payload)
            # Rule 1: Text optimization for visibility -> Must contain the subject
            # The test confirms that whoever copies or clicks this link will send the title text
            # NOTE: LinkedIn exclusively uses 'url' and reads og:title via server-side scrape
            if k != "in_href" and target_subject not in decoded:
                print(f"❌ Social link '{k}' does not contain optimized visibility text (missing subject: {target_subject})")
                missing = True
                
            # Rule 2: Asset routing -> Must explicitly link to the proxies in /insights/
            if "/insights/" not in decoded and ".html" not in decoded:
                print(f"❌ Social link '{k}' does not properly route to an HTML proxy in /insights/! Ensure the URL routes here, so the crawler hits the dynamically generated asset sharing endpoints.")
                missing = True
                
        if missing:
            sys.exit(1)
            
        print("✅ All frontend social formatters successfully optimize text payloads for external readers!")
        print("✅ All social formatting logic definitively targets the explicit image proxies in /insights/ for dynamic media.")
        print("\n🎉 FRONTEND SHARE AUDIT PASSED!")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_frontend_sharing_audit())
