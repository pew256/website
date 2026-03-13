import sys
import os
import json
import re
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright
from PIL import Image, ImageOps

def fit_contain(pil_img, target_width, target_height, bg_color=(248, 250, 252, 255)):
    # Calculate scale to fit inside target entirely
    img_ratio = pil_img.width / pil_img.height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        # Fits to width
        new_w = target_width
        new_h = int(target_width / img_ratio)
    else:
        # Fits to height
        new_h = target_height
        new_w = int(target_height * img_ratio)
        
    scaled_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    new_img = Image.new("RGBA", (target_width, target_height), bg_color)
    paste_x = (target_width - new_w) // 2
    paste_y = (target_height - new_h) // 2
    new_img.paste(scaled_img, (paste_x, paste_y), scaled_img)
    return new_img

def parse_markdown_draft(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        subject = "Contrarian Draft"
        bull = ""
        bear = ""
        
        for line in content.split('\n'):
            if line.startswith('Subject: '):
                subject = line.replace('Subject: ', '').strip()
                
        # Simple extraction blocks based on the generated markdown framework
        take1_match = re.search(r'## Take 1:.*?> \*\*Atomic Answer:\*\*(.*?)(?=## Take 2:|## Source Intelligence)', content, re.DOTALL)
        if take1_match:
            bull = take1_match.group(1).strip()
            
        take2_match = re.search(r'## Take 2:.*?> \*\*Atomic Answer:\*\*(.*?)(?=## Source Intelligence)', content, re.DOTALL)
        if take2_match:
            bear = take2_match.group(1).strip()
            
        return subject, bull, bear
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None, None, None

def fetch_content_for_id(target_id, project):
    # Determine timestamp from 'insight-20260312_145429' or 'con-20260312_145429' OR just '20260312_145429'
    timestamp = target_id.split('-')[-1] if '-' in target_id else target_id
    
    subject, bull, bear = None, None, None
    
    # 1. Try to read from published_journal.json first (if it's already live)
    pub_path = os.path.join(os.getcwd(), 'assets', 'published_journal.json')
    if os.path.exists(pub_path):
        with open(pub_path, 'r') as f:
            data = json.load(f)
            for item in data:
                if item.get('timestamp') == timestamp:
                    subject = item.get('subject')
                    bull = item.get('bull_case')
                    bear = item.get('bear_case')
                    project = item.get('project', project)
                    print("Found content in published_journal.json")
                    break
                    
    # 2. If not found in published, look for the raw draft file (Extraction time or Edit time)
    if not subject:
        draft_dir = os.path.join(os.getcwd(), 'projects', project, 'journal')
        possible_files = [f"draft-auto-{timestamp}.md", f"draft-{timestamp}.md"]
        for p_file in possible_files:
            draft_path = os.path.join(draft_dir, p_file)
            if os.path.exists(draft_path):
                print(f"Found content in {draft_path}")
                subject, bull, bear = parse_markdown_draft(draft_path)
                break
                
    # Formatting the Timestamp nicely: "March 12, 2026"
    try:
        dt = datetime.strptime(timestamp.split('_')[0], "%Y%m%d")
        formatted_date = dt.strftime("%B %-d, %Y")
    except:
        formatted_date = "Recently"
        
    return timestamp, formatted_date, project, subject, bull, bear

def generate_html(formatted_date, project, subject, bull, bear, mode, target_width, target_height):
    
    content_class = "single-column" if mode in ['bull', 'bear'] else ""
    bull_html = ""
    bear_html = ""
    
    if mode in ['both', 'bull']:
        css_class = "single-take" if mode == 'bull' else "bull-case"
        title_text = "The Bull Case (Pro)" if mode == 'both' else "The Contrarian Take"
        bull_html = f"""
        <div class="take-box {css_class}">
            <h4>{title_text}</h4>
            <p>{bull}</p>
        </div>
        """
        
    if mode in ['both', 'bear']:
        css_class = "single-take" if mode == 'bear' else "bear-case"
        title_text = "The Bear Case (Con)" if mode == 'both' else "The Contrarian Take"
        bear_html = f"""
        <div class="take-box {css_class}">
            <h4>{title_text}</h4>
            <p>{bear}</p>
        </div>
        """
        
    # Dynamically size the inner card based on the container aspect ratio
    card_max_width = "900px" if target_width > target_height else "650px"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
    <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        background: #000000; /* dark outer for contrast debug */
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
        min-height: 100vh;
        font-family: 'Lato', -apple-system, sans-serif;
        color: #506684;
    }}
    #capture-frame {{
        width: {target_width}px;
        height: {target_height}px;
        background: #f8fafc;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0px; /* Removed outer padding so card fills entirely */
        container-type: size;
    }}
    .journal-card {{
        background: #FFFFFF;
        border: 2px solid #E2E8F0;
        border-radius: 24px; /* increased rounding for sleek corners */
        padding: clamp(0.5rem, 2cqh, 2rem) clamp(1rem, 3cqw, 3rem); /* Minimized padding to maximize usable card space */
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08); /* slightly deepened shadow */
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    .journal-header {{
        margin-bottom: clamp(0.5rem, 1.5cqh, 1rem);
    }}
    .journal-title {{
        font-size: clamp(1.5rem, 5cqmin, 3rem);
        font-weight: 700;
        line-height: 1.2;
        color: #506684;
        margin-bottom: 0.25rem;
        font-family: 'Montserrat', sans-serif;
    }}
    .journal-meta {{
        display: flex;
        justify-content: flex-start;
        align-items: center;
        color: #64748b;
        font-size: clamp(0.85rem, 2cqmin, 1.2rem);
    }}
    .journal-content {{
        display: grid;
        grid-template-columns: { '1fr' if mode in ['bull', 'bear'] else '1fr 1fr' };
        gap: clamp(0.5rem, 1.5cqmin, 1rem);
        flex: 1;
        overflow: hidden; /* Prevent spillage if scaling fails */
    }}
    .single-column {{
        grid-template-columns: 1fr !important;
        max-width: 800px;
        margin: 0 auto;
        width: 100%;
    }}
    .take-box {{
        padding: clamp(0.75rem, 2cqh, 1.5rem) clamp(0.75rem, 2cqw, 1.5rem);
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        background: #f8fafc;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;
    }}
    .bull-case {{ border-top: 3px solid #10b981; }}
    .bear-case {{ border-top: 3px solid #ef4444; }}
    .single-take {{ border-top: 3px solid #506684 !important; }}

    .take-box h4 {{
        margin-bottom: 1rem;
        font-size: 1.8rem;
        font-family: 'Montserrat', sans-serif;
    }}
    .bull-case h4 {{ color: #10b981; }}
    .bear-case h4 {{ color: #ef4444; }}
    .single-take h4 {{ color: #506684 !important; }}
    .take-box p {{
        color: #334155;
        line-height: 1.6;
        font-size: 1.4rem;
    }}
    </style>
    </head>
    <body>
        <div id="capture-frame">
            <div class="journal-card" id="card">
                <div class="journal-header">
                    <h3 class="journal-title">{subject}</h3>
                    <div class="journal-meta">
                        <span>Published: {formatted_date} &nbsp;&bull;&nbsp; {project}</span>
                    </div>
                </div>
                <div class="journal-content {content_class}">
                    {bull_html}
                    {bear_html}
                </div>
                <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #E2E8F0; color: #94a3b8; font-size: 0.95rem; font-weight: 600; font-family: 'Montserrat', sans-serif; text-align: right;">
                    Precision in Blockchain
                </div>
            </div>
        </div>
        <script>
            // Native scaling algorithm to guarantee text perfectly fills but never overflows the space
            document.fonts.ready.then(() => {{
                const boxes = document.querySelectorAll('.take-box');
                boxes.forEach(box => {{
                    let p = box.querySelector('p');
                    let h4 = box.querySelector('h4');
                    if (!p || !h4) return;
                    
                    let pSize = 2.8; // Start comfortably large (rem)
                    let h4Size = 3.2;
                    p.style.fontSize = pSize + 'rem';
                    h4.style.fontSize = h4Size + 'rem';
                    
                    // Iteratively shrink until there is no vertical overflow
                    while (box.scrollHeight > box.clientHeight && pSize > 0.5) {{
                        pSize -= 0.05;
                        h4Size -= 0.05;
                        p.style.fontSize = pSize + 'rem';
                        h4.style.fontSize = h4Size + 'rem';
                    }}
                }});
                
                // Signal to Playwright that scaling is complete
                window.textScalingComplete = true;
            }});
        </script>
    </body>
    </html>
    """

def apply_diagonal_watermark(base_img):
    wm_path = os.path.join(os.getcwd(), "assets/brand-kit/pew256-logo-knockout.png")
    if os.path.exists(wm_path):
        with Image.open(wm_path) as wm:
            wm = wm.convert("RGBA")
            import math
            # Calculate diagonal length
            diag_length = math.hypot(base_img.width, base_img.height)
            # Make the watermark span 80% of the diagonal
            target_wm_width = int(diag_length * 0.8)
            wm_ratio = wm.height / wm.width
            target_wm_height = int(target_wm_width * wm_ratio)
            
            wm = wm.resize((target_wm_width, target_wm_height), Image.Resampling.LANCZOS)
            
            # Reduce opacity
            alpha = wm.split()[3]
            alpha = alpha.point(lambda p: p * 0.12)
            wm.putalpha(alpha)
            
            # Calculate rotation angle based on image dimensions
            angle = math.degrees(math.atan2(base_img.height, base_img.width))
            wm = wm.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            
            wm_x = (base_img.width - wm.width) // 2
            wm_y = (base_img.height - wm.height) // 2
            base_img.paste(wm, (wm_x, wm_y), wm)
    return base_img

def process_image(timestamp, mode, raw_twitter, raw_og, raw_square, raw_vertical):
    if mode == 'both':
        file_prefix = f"insight-{timestamp}"
    elif mode == 'bull':
        file_prefix = f"pro-{timestamp}"
    elif mode == 'bear':
        file_prefix = f"con-{timestamp}"
    else:
        file_prefix = f"{mode}-{timestamp}"
    
    shares_dir = os.path.join(os.getcwd(), "assets/shares")
    os.makedirs(shares_dir, exist_ok=True)
    
    out_landscape = os.path.join(shares_dir, f"{file_prefix}_og.png")
    out_twitter = os.path.join(shares_dir, f"{file_prefix}_twitter.png")
    out_square = os.path.join(shares_dir, f"{file_prefix}_square.png")
    out_vertical = os.path.join(shares_dir, f"{file_prefix}_vertical.png")

    try:
        # 1. Twitter 16:9
        with Image.open(raw_twitter) as img:
            img = img.convert("RGBA")
            img = apply_diagonal_watermark(img)
            img.save(out_twitter, "PNG")

        # 2. LinkedIn / OG 1.91:1
        with Image.open(raw_og) as img:
            img = img.convert("RGBA")
            img = apply_diagonal_watermark(img)
            img.save(out_landscape, "PNG")
            
        # 3. Instagram Square 1:1
        with Image.open(raw_square) as img:
            img = img.convert("RGBA")
            img = apply_diagonal_watermark(img)
            img.save(out_square, "PNG")
            
        # 4. Instagram Vertical 9:16
        with Image.open(raw_vertical) as img:
            img = img.convert("RGBA")
            img = apply_diagonal_watermark(img)
            img.save(out_vertical, "PNG")
            
        return True
    except Exception as e:
        print(f"Error processing image for {mode}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Draft timestamp (e.g. 20260312_145429)")
    parser.add_argument("--project", default="Bitcoin trends", help="Project folder")
    parser.add_argument("--mode", default="all", help="all, both, bull, bear")
    args = parser.parse_args()

    timestamp, formatted_date, project, subject, bull, bear = fetch_content_for_id(args.id, args.project)
    
    if not subject:
        print(f"Could not find any published or drafted content for ID {args.id}")
        sys.exit(1)

    modes_to_run = ['both', 'bull', 'bear'] if args.mode == 'all' else [args.mode]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Using a wide 4K viewport to ensure high-fidelity crisp text for cropping later
        page = browser.new_page(viewport={"width": 3840, "height": 2160}, device_scale_factor=2)
        
        for mode in modes_to_run:
            print(f"Generating preview for mode: {mode}...")
            
            # The 4 specific social platform explicit aspect ratios we need images for
            platform_sizes = {
                "twitter": (1200, 675),
                "og": (1200, 630),
                "square": (1080, 1080),
                "vertical": (1080, 1920)
            }
            
            temp_paths = {}
            for plat, (width, height) in platform_sizes.items():
                print(f" > Rendering exact CSS {width}x{height} capture frame for {plat}...")
                html_rendered = generate_html(formatted_date, project, subject, bull, bear, mode, target_width=width, target_height=height)
                
                # Navigate to blank slate then apply content
                page.goto("http://localhost:8085/404.html", wait_until="domcontentloaded")
                page.set_content(html_rendered)
                page.evaluate("document.fonts.ready")
                
                # Explicitly wait for the JS font-scaling algorithm to finish layout constraints
                page.wait_for_function("window.textScalingComplete === true", timeout=2000)
                page.wait_for_timeout(100) # tiny visual flush buffer
                
                # Snapshot the wrapper containing the perfect padding natively 
                frame = page.locator("#capture-frame")
                temp_paths[plat] = os.path.join(os.getcwd(), f"temp_{timestamp}_{mode}_{plat}.png")
                frame.screenshot(path=temp_paths[plat], type="png")
            
            print(f"Captured perfectly dimensioned screenshots. Watermarking and saving assets for {mode}...")
            process_image(timestamp, mode, temp_paths["twitter"], temp_paths["og"], temp_paths["square"], temp_paths["vertical"])
            
            # Purge temp frames
            for path in temp_paths.values():
                if os.path.exists(path):
                    os.remove(path)
                
        browser.close()
        print(f"Successfully generated all raw and diffusion assets for {timestamp}!")

if __name__ == "__main__":
    main()
