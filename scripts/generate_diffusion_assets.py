import sys
import os
import argparse
from playwright.sync_api import sync_playwright
from PIL import Image, ImageOps

def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Element ID on index.html (e.g. con-20260312_010304)")
    args = parser.parse_args()

    target_id = args.id
    
    # Paths
    shares_dir = os.path.join(os.getcwd(), "assets/shares")
    os.makedirs(shares_dir, exist_ok=True)
    
    capture_4k = os.path.join(shares_dir, f"{target_id}_4k.png")
    out_landscape = os.path.join(shares_dir, f"{target_id}_og.png")
    out_twitter = os.path.join(shares_dir, f"{target_id}_twitter.png")
    out_square = os.path.join(shares_dir, f"{target_id}_square.png")
    out_vertical = os.path.join(shares_dir, f"{target_id}_vertical.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 4K resolution
        page = browser.new_page(viewport={"width": 3840, "height": 2160})
        
        try:
            page.goto("http://localhost:8085/index.html")
            page.wait_for_selector(f"#{target_id}", timeout=10000)
            
            # Hide everything else
            page.evaluate(f"""() => {{
                document.querySelectorAll('body > *:not(main)').forEach(el => el.style.display = 'none');
                document.querySelectorAll('main > *:not(.journal-section)').forEach(el => el.style.display = 'none');
                
                const target = document.getElementById('{target_id}');
                if(target) {{
                    const entry = target.closest('.journal-entry');
                    if(entry) {{
                        Array.from(entry.parentNode.children).forEach(sibling => {{
                            if(sibling !== entry) sibling.style.display = 'none';
                        }});
                        
                        const takes = entry.querySelectorAll('.take-box');
                        takes.forEach(take => {{
                            if(take.id !== '{target_id}') take.style.display = 'none';
                        }});
                        
                        document.body.style.display = 'flex';
                        document.body.style.alignItems = 'center';
                        document.body.style.justifyContent = 'center';
                        document.body.style.minHeight = '100vh';
                        document.body.style.background = '#0f172a';
                        
                        const main = document.querySelector('main');
                        main.style.width = '100%';
                        main.style.display = 'flex';
                        main.style.justifyContent = 'center';
                        
                        target.style.width = '1600px';
                        target.style.maxWidth = '100%';
                        target.style.transform = 'scale(1.5)';
                        target.style.transformOrigin = 'center';
                    }}
                }}
            }}""")
            
            page.wait_for_timeout(2000)
            page.screenshot(path=capture_4k, full_page=True)
            print(f"Captured 4K screenshot: {capture_4k}")
            
        except Exception as e:
            print(f"Error extracting DOM for `{target_id}`: {e}")
            browser.close()
            return
            
        browser.close()

    if not os.path.exists(capture_4k):
        print("4K capture failed.")
        return

    try:
        with Image.open(capture_4k) as img:
            # Landscape (1200x630 - OG/LinkedIn/WhatsApp)
            land_img = img.copy()
            ratio = 1200 / float(img.width)
            land_img = land_img.resize((1200, int(img.height * ratio)), Image.Resampling.LANCZOS)
            land_img_og = crop_center(land_img, 1200, 630)
            land_img_og.save(out_landscape)
            print(f"Saved Landscape (1200x630): {out_landscape}")
            
            # Twitter (1200x675 - 16:9)
            twitter_img = crop_center(land_img, 1200, 675)
            twitter_img.save(out_twitter)
            print(f"Saved Twitter Summary (1200x675): {out_twitter}")

            # Square
            sq_img = img.copy()
            ratio_sq = 1080 / float(img.height) # fits height to 1080
            sq_img = sq_img.resize((int(img.width * ratio_sq), 1080), Image.Resampling.LANCZOS)
            sq_crop = crop_center(sq_img, 1080, 1080)
            sq_crop.save(out_square)
            print(f"Saved Square (1080x1080): {out_square}")

            # Vertical
            vert_img = Image.new("RGB", (1080, 1920), (15, 23, 42)) # Matches page bg
            offset = ((1080 - sq_crop.width) // 2, (1920 - sq_crop.height) // 2)
            vert_img.paste(sq_crop, offset)
            vert_img.save(out_vertical)
            print(f"Saved Vertical (1080x1920): {out_vertical}")

    except Exception as e:
        print(f"Image processing failed: {e}")

if __name__ == "__main__":
    main()
