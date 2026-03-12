#!/usr/bin/env python3
import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    print("\n--- X.com Authentication Setup ---\n")
    print("Launching visible Chrome browser...")
    print("Please log in to your X.com account manually.")
    print("Once you are fully logged in and see your home feed, close the browser window to save your session.\n")
    
    # Ensure directory exists in project root for persistent auth
    user_data_dir = os.path.join(os.getcwd(), ".playwright_data")
    
    async with async_playwright() as p:
        # Launch persistent context. Headless=False so the user can see and interact.
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 800}
        )
        
        page = await browser_context.new_page()
        await page.goto("https://x.com/login")
        
        print("Waiting for you to close the browser...")
        # Keep the script running until the user closes the browser window themselves
        try:
            await page.wait_for_event("close", timeout=0)
        except Exception:
            pass
            
        print("\nBrowser closed. Session data saved to .playwright_data/")
        print("The extraction engine will now be able to scrape X.com lists and hashtags!")

if __name__ == "__main__":
    asyncio.run(main())
