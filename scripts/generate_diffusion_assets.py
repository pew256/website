import sys
import os
import json
import re
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright
from PIL import Image, ImageOps

def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

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

def generate_html(formatted_date, project, subject, bull, bear, mode, is_square=False):
    
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
        
    square_css = """
        aspect-ratio: 1 / 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        max-width: 800px;
        min-height: 800px;
    """ if is_square else "max-width: 900px;"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
    <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        background: #f8fafc;
        padding: 50px;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        font-family: 'Lato', -apple-system, sans-serif;
        color: #506684;
    }}
    .journal-card {{
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 2.5rem;
        box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05);
        width: 100%;
        {square_css}
    }}
    .journal-header {{
        margin-bottom: 2rem;
    }}
    .journal-title {{
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.3;
        color: #506684;
        margin-bottom: 1rem;
        font-family: 'Montserrat', sans-serif;
    }}
    .journal-meta {{
        display: flex;
        justify-content: flex-start;
        align-items: center;
        color: #64748b;
        font-size: 0.95rem;
    }}
    .journal-content {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
    }}
    .single-column {{
        grid-template-columns: 1fr !important;
        max-width: 800px;
        margin: 0 auto;
    }}
    .take-box {{
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        background: #f8fafc;
    }}
    .bull-case {{ border-top: 3px solid #10b981; }}
    .bear-case {{ border-top: 3px solid #ef4444; }}
    .single-take {{ border-top: 3px solid #506684 !important; }}

    .take-box h4 {{
        margin-bottom: 1rem;
        font-size: 1.1rem;
        font-family: 'Montserrat', sans-serif;
    }}
    .bull-case h4 {{ color: #10b981; }}
    .bear-case h4 {{ color: #ef4444; }}
    .single-take h4 {{ color: #506684 !important; }}
    .take-box p {{
        color: #334155;
        line-height: 1.7;
        font-size: 1.05rem;
    }}
    </style>
    </head>
    <body>
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
        </div>
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
            alpha = alpha.point(lambda p: p * 0.04)
            wm.putalpha(alpha)
            
            # Calculate rotation angle based on image dimensions
            angle = math.degrees(math.atan2(base_img.height, base_img.width))
            wm = wm.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            
            wm_x = (base_img.width - wm.width) // 2
            wm_y = (base_img.height - wm.height) // 2
            base_img.paste(wm, (wm_x, wm_y), wm)
    return base_img

def process_image(timestamp, mode, raw_natural_path, raw_square_path):
    # Prefix files with mode-timestamp
    file_prefix = f"insight-{timestamp}" if mode == 'both' else f"{mode}-{timestamp}"
    
    shares_dir = os.path.join(os.getcwd(), "assets/shares")
    journal_dir = os.path.join(os.getcwd(), "assets/journal")
    os.makedirs(shares_dir, exist_ok=True)
    os.makedirs(journal_dir, exist_ok=True)
    
    out_natural = os.path.join(journal_dir, f"{file_prefix}_natural.png")
    out_square_raw = os.path.join(journal_dir, f"{file_prefix}_square.png")
    
    out_landscape = os.path.join(shares_dir, f"{file_prefix}_og.png")
    out_twitter = os.path.join(shares_dir, f"{file_prefix}_twitter.png")
    out_square = os.path.join(shares_dir, f"{file_prefix}_square.png")
    out_vertical = os.path.join(shares_dir, f"{file_prefix}_vertical.png")

    try:
        # 1. Natural Raw Journal Asset
        with Image.open(raw_natural_path) as img:
            img = img.convert("RGBA")

            new_width = img.width + 100
            new_height = img.height + 100
            padded_img = Image.new("RGBA", (new_width, new_height), (248, 250, 252, 255))
            padded_img.paste(img, (50, 50), img)
            
            # Apply diagonal watermark
            padded_img = apply_diagonal_watermark(padded_img)
            padded_img.save(out_natural, "PNG")

        # 2. Square Raw Journal Asset (using the new sq html capture)
        with Image.open(raw_square_path) as sq_img_raw:
            sq_img_raw = sq_img_raw.convert("RGBA")
            sq_size = max(sq_img_raw.width, sq_img_raw.height) + 100
            square_img = Image.new("RGBA", (sq_size, sq_size), (248, 250, 252, 255))
            sq_x = (sq_size - sq_img_raw.width) // 2
            sq_y = (sq_size - sq_img_raw.height) // 2
            square_img.paste(sq_img_raw, (sq_x, sq_y), sq_img_raw)
            
            # Apply diagonal watermark
            square_img = apply_diagonal_watermark(square_img)
            square_img.save(out_square_raw, "PNG")

            # --- DIFFUSION CROP ASSETS --- #
            # Twitter 16:9 (1200x675)
            twit_img = crop_center(square_img, sq_size, int(sq_size * (675/1200)))
            twit_img = twit_img.resize((1200, 675), Image.Resampling.LANCZOS)
            twit_img.save(out_twitter, "PNG")
            
            # LinkedIn / OG 1.91:1 (1200x630)
            og_img = crop_center(square_img, sq_size, int(sq_size * (630/1200)))
            og_img = og_img.resize((1200, 630), Image.Resampling.LANCZOS)
            og_img.save(out_landscape, "PNG")
            
            # Instagram Square (1080x1080)
            ig_sq = square_img.resize((1080, 1080), Image.Resampling.LANCZOS)
            ig_sq.save(out_square, "PNG")
            
            # Instagram Vertical 9:16 (1080x1920)
            target_h = int(sq_size * (1920/1080))
            if target_h > square_img.height:
                vert_img = Image.new("RGBA", (sq_size, target_h), (248, 250, 252, 255))
                v_y = (target_h - square_img.height) // 2
                vert_img.paste(square_img, (0, v_y), square_img)
            else:
                vert_img = crop_center(square_img, int(sq_size * (1080/1920)), sq_size)
            vert_img = vert_img.resize((1080, 1920), Image.Resampling.LANCZOS)
            vert_img.save(out_vertical, "PNG")
            
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
            
            # --- 1. Natural Capture ---
            html_natural = generate_html(formatted_date, project, subject, bull, bear, mode, is_square=False)
            page.goto("http://localhost:8085/404.html", wait_until="domcontentloaded")
            page.set_content(html_natural)
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(500)
            
            card = page.locator("#card")
            temp_path_nat = os.path.join(os.getcwd(), f"temp_{timestamp}_{mode}_nat.png")
            card.screenshot(path=temp_path_nat, type="png")
            
            # --- 2. Square Tile Capture ---
            html_square = generate_html(formatted_date, project, subject, bull, bear, mode, is_square=True)
            page.set_content(html_square)
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(500)
            
            temp_path_sq = os.path.join(os.getcwd(), f"temp_{timestamp}_{mode}_sq.png")
            card.screenshot(path=temp_path_sq, type="png")
            
            print(f"Captured clean screenshots. Watermarking and cropping diffusion assets for {mode}...")
            process_image(timestamp, mode, temp_path_nat, temp_path_sq)
            
            # Purge temp frames
            if os.path.exists(temp_path_nat):
                os.remove(temp_path_nat)
            if os.path.exists(temp_path_sq):
                os.remove(temp_path_sq)
                
        browser.close()
        print(f"Successfully generated all raw and diffusion assets for {timestamp}!")

if __name__ == "__main__":
    main()
