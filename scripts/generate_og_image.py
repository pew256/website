import asyncio
from playwright.async_api import async_playwright
import argparse
import os
import textwrap

def generate_html(timestamp, project, takes, subject, bull_case, bear_case):
    # Truncate cases if they are too long for the image
    bull_case = textwrap.shorten(bull_case, width=150, placeholder="...")
    bear_case = textwrap.shorten(bear_case, width=150, placeholder="...")
    
    # Determine which boxes to show
    show_bull = takes in ['bull', 'both']
    show_bear = takes in ['bear', 'both']
    is_single = show_bull != show_bear
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@700;800&display=swap');
            
            body {{
                margin: 0;
                padding: 0;
                width: 1200px;
                height: 630px;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                font-family: 'Inter', sans-serif;
                color: #f8fafc;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-sizing: border-box;
                padding: 60px;
                position: relative;
                overflow: hidden;
            }}
            
            /* Decorative background elements */
            .bg-glow-1 {{
                position: absolute;
                top: -100px;
                right: -100px;
                width: 600px;
                height: 600px;
                background: radial-gradient(circle, rgba(56,189,248,0.15) 0%, rgba(15,23,42,0) 70%);
                border-radius: 50%;
                z-index: 0;
            }}
            .bg-glow-2 {{
                position: absolute;
                bottom: -200px;
                left: -100px;
                width: 800px;
                height: 800px;
                background: radial-gradient(circle, rgba(16,185,129,0.1) 0%, rgba(15,23,42,0) 70%);
                border-radius: 50%;
                z-index: 0;
            }}
            
            .content {{
                position: relative;
                z-index: 10;
                display: flex;
                flex-direction: column;
                height: 100%;
            }}
            
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 40px;
            }}
            
            .tag {{
                background: rgba(56, 189, 248, 0.1);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 20px;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }}
            
            .brand {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .brand-name {{
                font-family: 'Montserrat', sans-serif;
                font-weight: 800;
                font-size: 32px;
                color: #ffffff;
            }}
            
            h1 {{
                font-family: 'Montserrat', sans-serif;
                font-size: 64px;
                font-weight: 800;
                line-height: 1.1;
                margin: 0 0 40px 0;
                color: #ffffff;
                text-wrap: balance;
            }}
            
            .cases {{
                display: flex;
                gap: 30px;
                flex: 1;
            }}
            
            .case-box {{
                flex: 1;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 16px;
                backdrop-filter: blur(10px);
            }}
            
            .bull-box { border-top: 4px solid #10b981; }
            .bear-box { border-top: 4px solid #ef4444; }
            .single-box { border-top: 4px solid #38bdf8; max-width: 800px; margin: 0 auto; }
            
            .case-title { font-weight: 700; font-size: 24px; margin: 0 0 15px 0; display: flex; align-items: center; gap: 10px; }
            .bull-title { color: #10b981; }
            .bear-title { color: #ef4444; }
            .single-title { color: #38bdf8; }
            
            .case-text {{
                font-size: 22px;
                line-height: 1.5;
                color: #cbd5e1;
                margin: 0;
            }}
        </style>
    </head>
    <body>
        <div class="bg-glow-1"></div>
        <div class="bg-glow-2"></div>
        
        <div class="content">
            <div class="header">
                <div class="tag">Contrarian Insight</div>
                <div class="brand">
                    <div class="brand-name">pew256</div>
                </div>
            </div>
            
            <h1>{subject}</h1>
            
            <div class="cases">
                """
    
    if show_bull:
        box_class = "single-box" if is_single else "bull-box"
        title_class = "single-title" if is_single else "bull-title"
        title_text = "The Bull Case" if is_single else "The Bull Case"
        html += f"""
                <div class="case-box {box_class}">
                    <h3 class="case-title {title_class}">{title_text}</h3>
                    <p class="case-text">{bull_case}</p>
                </div>"""
                
    if show_bear:
        box_class = "single-box" if is_single else "bear-box"
        title_class = "single-title" if is_single else "bear-title"
        title_text = "The Bear Case" if is_single else "The Bear Case"
        html += f"""
                <div class="case-box {box_class}">
                    <h3 class="case-title {title_class}">{title_text}</h3>
                    <p class="case-text">{bear_case}</p>
                </div>"""

    html += """
            </div>
        </div>
    </body>
    </html>
    """
    return html

async def main():
    parser = argparse.ArgumentParser(description='Generate OpenGraph Image')
    parser.add_argument('--timestamp', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--takes', required=True, help="bull, bear, or both")
    parser.add_argument('--subject', required=True)
    parser.add_argument('--bull', required=True)
    parser.add_argument('--bear', required=True)
    args = parser.parse_args()

    html_content = generate_html(args.timestamp, args.project, args.takes, args.subject, args.bull, args.bear)
    
    temp_html = f"/tmp/og_{args.timestamp}.html"
    with open(temp_html, "w") as f:
        f.write(html_content)
        
    out_dir = "assets/shares"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"insight-{args.timestamp}.png")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 630})
        await page.goto(f"file://{temp_html}")
        # Wait for web fonts to load
        await page.evaluate("document.fonts.ready")
        await page.screenshot(path=out_path)
        await browser.close()
        
    try:
        os.remove(temp_html)
    except:
        pass
        
    print(f"Generated {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
