import os
import sys
import asyncio
from playwright.async_api import async_playwright

# Add the current directory to the path so we can import from scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_diffusion_assets import generate_html

async def run_legibility_audit():
    """
    Automated test to computationally enforce the layout legibility rules.
    This guarantees that the proxy images generated for social media ALWAYS
    prioritize space readability and never regress to the padding letterbox logic.
    """
    print("🚀 Booting Legibility Assertion Test Suite...")
    
    # 1. Generate an extreme edge-case: Massive amounts of text
    lorem_ipsum = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
    
    # Test on the most constrained aspect ratio (Twitter landscape: 1200x675)
    target_width = 1200
    target_height = 675
    
    html_payload = generate_html(
        subject="Extreme Legibility Edge-Case Audit",
        formatted_date="March 13, 2026",
        project="Assertion Framework",
        bull=lorem_ipsum,
        bear=lorem_ipsum,
        mode="both",
        target_width=target_width,
        target_height=target_height
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": target_width, "height": target_height})
        
        # Load the raw HTML exactly how the generation script does
        await page.goto("http://localhost:8085/404.html") # Needs to be something valid or blank
        await page.set_content(html_payload)
        await page.evaluate("document.fonts.ready")
        
        try:
            # RULE 5: Anti-Clipping JS Injection Enforcement
            # Wait for the JS scaling logic to complete its down-res calculations
            await page.wait_for_function("window.textScalingComplete === true", timeout=5000)
            print("✅ Anti-Clipping CSS/JS calculation engine successfully injected and ran.")
        except Exception as e:
            print("❌ FAILURE: The Anti-Clipping JS engine failed to run or was removed from HTML generation.")
            sys.exit(1)
            
        
        # RULE 2: The 100% Stretch Rule Enforcement
        card_box = await page.locator(".journal-card").bounding_box()
        frame_box = await page.locator("#capture-frame").bounding_box()
        
        if card_box['width'] < (frame_box['width'] * 0.9):
            print(f"❌ FAILURE: The central card is no longer maximizing the frame width! Size: {card_box['width']}/{frame_box['width']}")
            sys.exit(1)
            
        print("✅ Space Legibility: The text card maximizes the 100% boundary stretch limit.")
        
        
        # FINAL COMPUTATION: Legibility Verification
        # Check the font size to ensure it did not shrink past an illegible threshold
        # We want to ensure at least 1rem (16px) or similar exists. Given the massive text constraint
        # on a short 675px height frame, the JS loop will heavily compress it, but it should remain readable.
        
        min_font_px = await page.evaluate('''() => {
            const paragraphs = document.querySelectorAll('.take-box p');
            let minSize = 999;
            paragraphs.forEach(p => {
                const style = window.getComputedStyle(p);
                const size = parseFloat(style.fontSize);
                if (size < minSize) minSize = size;
            });
            return minSize;
        }''')
        
        print(f"🔍 Computed Absolute Minimum Font Pixels generated: {min_font_px}px")
        
        if min_font_px < 14: # 14px absolute math minimum readability fail condition
            print("❌ FAILURE: The layout algorithm aggressively compressed the fonts into illegibility (<14px) to fit the container!")
            sys.exit(1)
            
        print("✅ The layout algorithm successfully maintained legibility ratios!")
        print("\n🎉 ALL LEGIBILITY & SPACE OPTIMIZATION ASSERTIONS PASSED!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_legibility_audit())
