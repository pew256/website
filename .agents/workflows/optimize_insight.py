import os
import re
import sys
import json
import asyncio
import argparse
import feedparser
from dotenv import load_dotenv
from markdownify import markdownify as md
from datetime import datetime, timedelta, timezone

# Load environment variables (like GEMINI_API_KEY) from .env
load_dotenv()



def get_project_dir(project_name):
    safe_name = "".join([c for c in project_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
    if not safe_name:
        safe_name = "Bitcoin trends"
    return os.path.join("projects", safe_name)

def get_internal_links(project_dir, limit=5):
    """Scans the journal directory and returns a list of recent post titles and paths."""
    links = []
    directory = os.path.join(project_dir, "journal")
    if not os.path.exists(directory):
        return "No existing journal posts found."
    
    for filename in os.listdir(directory):
        if filename.endswith(".md") and not filename.startswith("draft-"):
            title = filename.replace("-", " ").replace(".md", "").title()
            links.append(f"- [{title}](/{directory}/{filename})")
    
    return "\n".join(links[:limit])

def create_context_snippet(briefing_file):
    """Reads the briefing and returns a token-dense summary."""
    with open(briefing_file, 'r') as f:
        content = f.read()
    return " ".join(content.split()[:500])

def set_status(project_dir, message):
    try:
        with open(os.path.join(project_dir, "engine_status.txt"), "w") as f:
            f.write(message)
    except Exception:
        pass

async def crawl_sources(project_dir):
    # Simulate the backend boot sequence for the UI
    set_status(project_dir, "1. Acknowledging secure frontend request...")
    await asyncio.sleep(0.5)
    set_status(project_dir, "2. Initializing dedicated Python extraction environment...")
    await asyncio.sleep(0.5)
    set_status(project_dir, "3. Loading core ML dependencies and parsers into memory...")
    await asyncio.sleep(0.5)
    set_status(project_dir, "4. Mapping project configuration and locating sources.json...")
    await asyncio.sleep(0.5)
    sources_file = os.path.join(project_dir, "sources.json")
    if not os.path.exists(sources_file):
        return f"No sources found. Please configure {sources_file}"
    
    with open(sources_file, "r") as f:
        sources = json.load(f)
        
    extracted_text = []

    # Fast: Extract Custom Notes
    for index, note in enumerate(sources.get("notes", [])):
        set_status(project_dir, f"Extracting Note {index+1}...")
        extracted_text.append(f"--- Note {index+1} ---\n{note}\n")
        
    # Fast: Extract PDFs
    pdf_files = sources.get("pdf_files", [])
    if pdf_files:
        set_status(project_dir, f"Parsing {len(pdf_files)} PDF documents...")
        try:
            from PyPDF2 import PdfReader
            for pdf_name in pdf_files:
                set_status(project_dir, f"Parsing PDF: {pdf_name}")
                pdf_path = os.path.join(project_dir, "pdfs", pdf_name)
                if os.path.exists(pdf_path):
                    reader = PdfReader(pdf_path)
                    text = ""
                    for page in reader.pages:
                        extracted_page = page.extract_text()
                        if extracted_page:
                            text += extracted_page + "\n"
                    extracted_text.append(f"--- From PDF: {pdf_name} ---\n{text[:5000]}\n")
                else:
                    print(f"Warning: Failed to find PDF: {pdf_name}")
        except Exception as e:
            print(f"Warning: Failed to parse PDFs: {e}")

    has_web = len(sources.get("web_crawls", [])) > 0
    has_rss = len(sources.get("rss_feeds", [])) > 0
    has_twitter = len(sources.get("twitter_profiles", [])) > 0
    has_lists = len(sources.get("twitter_lists", [])) > 0
    requires_browser = has_web or has_rss or has_twitter or has_lists

    # Check if ANY execution is required at all
    if not (pdf_files or sources.get("notes", []) or requires_browser):
        set_status(project_dir, "No sources connected, proceeding with baseline synthesis...")
        return "[No raw extracted content was provided in the prompt for this section.]"

    if not requires_browser:
        return "\n".join(extracted_text)
        
    set_status(project_dir, "Crawling tracked sources via Playwright. This takes a few minutes.")
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install")
        return "\n".join(extracted_text)
        
    async with async_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), ".playwright_data")
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 800}
        )
        
        # Persistent contexts come with a default page
        pages = browser_context.pages
        page = pages[0] if pages else await browser_context.new_page()
        
        # Scrape Web Crawls
        for site in sources.get("web_crawls", []):
            try:
                set_status(project_dir, f"Crawling web: {site}")
                url = site if site.startswith("http") else f"https://{site}"
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
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
                
                # Extract clean visible text directly from the browser to handle SPAs and dynamic aggregators
                text = await page.evaluate('''() => {
                    document.querySelectorAll('script, style, svg, iframe, nav, footer, header, aside').forEach(e => e.remove());
                    
                    let headlines = [];
                    let links = document.querySelectorAll('a');
                    links.forEach(a => {
                        let txt = a.innerText.trim();
                        if (txt.split(' ').length > 4 && txt.length > 20 && !headlines.includes(txt)) {
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
                extracted_text.append(f"--- From {site} ---\n{text[:5000]}\n")
            except Exception as e:
                print(f"Warning: Failed to crawl {site}: {str(e)}")
                
        # Scrape RSS Feeds (Deep Crawl Top Links from last 14 days)
        for feed_url in sources.get("rss_feeds", []):
            try:
                set_status(project_dir, f"Parsing RSS feed: {feed_url}")
                url = feed_url if feed_url.startswith("http") else f"https://{feed_url}"
                feed = feedparser.parse(url)
                if feed.entries:
                    rss_text = ""
                    
                    from time import mktime
                    import dateutil.parser as dp
                    
                    now = datetime.now(timezone.utc)
                    valid_entries = 0
                    
                    for entry in feed.entries:
                        if valid_entries >= 2:
                            break
                            
                        # Check date if available
                        entry_date = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            entry_date = datetime.fromtimestamp(mktime(entry.published_parsed), timezone.utc)
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            entry_date = datetime.fromtimestamp(mktime(entry.updated_parsed), timezone.utc)
                        elif hasattr(entry, 'published'):
                            try:
                                entry_date = dp.parse(entry.published)
                                if entry_date.tzinfo is None:
                                    entry_date = entry_date.replace(tzinfo=timezone.utc)
                            except Exception:
                                pass
                                
                        if entry_date:
                            days_old = (now - entry_date).days
                            if days_old > 14:
                                continue # Skip, too old
                        
                        valid_entries += 1
                        rss_text += f"\n*** Article: {entry.get('title', 'Untitled')} ***\n"
                        link = entry.get('link', '')
                        if link:
                            try:
                                await page.goto(link, timeout=12000)
                                await page.wait_for_timeout(1000)
                                # Clean DOM before extracting completely
                                html = await page.evaluate('''() => {
                                    document.querySelectorAll('script, style, svg, iframe, nav, footer, header, aside, .ad, .advertisement, .social-share, .newsletter, [role="banner"], [role="contentinfo"], .related-articles, .sidebar').forEach(e => e.remove());
                                    const article = document.querySelector('article');
                                    if (article) return article.innerHTML;
                                    const main = document.querySelector('main');
                                    if (main) return main.innerHTML;
                                    return document.body.innerHTML;
                                }''')
                                text = md(html, heading_style="ATX", wrap=True, strip=['script', 'style', 'a', 'img'])
                                rss_text += f"\n**Extracted Content:**\n{text[:1500]}\n"
                            except Exception as e:
                                summary = entry.get('summary', '') or entry.get('description', '')
                                clean_summary = re.sub('<[^<]+>', '', summary)
                                rss_text += f"Summary (Crawl Failed): {clean_summary}\n"
                        else:
                            summary = entry.get('summary', '') or entry.get('description', '')
                            clean_summary = re.sub('<[^<]+>', '', summary)
                            rss_text += f"Summary: {clean_summary}\n"
                            
                    if rss_text:
                        extracted_text.append(f"--- From RSS Feed {feed_url} ---\n{rss_text[:2500]}\n")
                    else:
                        print(f"Warning: From RSS Feed {feed_url} - No recent articles (past 14 days) found.")
                else:
                    print(f"Warning: Failed to crawl RSS {feed_url}: No entries found or invalid feed.")
            except Exception as e:
                print(f"Warning: Failed to crawl RSS {feed_url}: {str(e)}")
                
        # Helper function to scroll and extract a timeline
        async def scrape_timeline(url, profile_name):
            try:
                await page.goto(url, timeout=20000)
                await page.wait_for_timeout(4000)
                
                seven_days_ago = datetime.utcnow() - timedelta(days=7)
                
                all_tweets = []
                seen_links = set()
                scrolls = 0
                max_scrolls = 15
                found_older = False
                
                while scrolls < max_scrolls:
                    batch = await page.evaluate('''() => {
                        const texts = document.querySelectorAll('[data-testid="tweetText"]');
                        if (texts.length === 0) return [];
                        
                        return Array.from(texts).map(t => {
                            let article = t.closest('article');
                            let timeEl = article ? article.querySelector('time') : null;
                            let dateStr = timeEl ? timeEl.textContent : 'Unknown Date';
                            let dtStr = timeEl ? timeEl.getAttribute('datetime') : null;
                            let link = (timeEl && timeEl.parentElement) ? timeEl.parentElement.href : '';
                            return {text: t.innerText.substring(0, 400), dateStr, dtStr, link};
                        });
                    }''')
                    
                    if not batch and scrolls > 0:
                        break
                        
                    new_added = 0
                    for t in batch:
                        link = t['link']
                        if link and link in seen_links:
                            continue
                            
                        dtStr = t['dtStr']
                        if dtStr:
                            try:
                                dt = datetime.fromisoformat(dtStr[:19])
                                if dt < seven_days_ago:
                                    found_older = True
                                    continue
                            except Exception:
                                pass
                                
                        if link:
                            seen_links.add(link)
                        all_tweets.append(t)
                        new_added += 1
                        
                    if found_older or (scrolls > 0 and new_added == 0):
                        break
                        
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(3000)
                    scrolls += 1
                
                if all_tweets:
                    formatted_tweets = ""
                    for i, t in enumerate(all_tweets):
                        header = f"*** Tweet {i+1} ***\n"
                        if t['link']:
                            header += f"**Posted:** [{t['dateStr']}]({t['link']})\n\n"
                        else:
                            header += f"**Posted:** {t['dateStr']}\n\n"
                        formatted_tweets += header + t['text'] + "\n\n"
                        
                    extracted_text.append(f"--- From Twitter source {profile_name} ---\n{formatted_tweets[:4000]}\n")
                else:
                    body = await page.evaluate("document.body.innerText")
                    if "Something went wrong" in body or "Try reloading" in body:
                        print(f"Warning: Failed to crawl {profile_name}: X.com blocked the request. Please authenticate.")
                    else:
                        print(f"Warning: Failed to crawl {profile_name}: No recent tweets found or profile is private.")
                        
            except Exception as e:
                print(f"Warning: Failed to crawl {profile_name}: {str(e)}")

        # Scrape Twitter Profiles
        for profile in sources.get("twitter_profiles", []):
            set_status(project_dir, f"Scraping Twitter profile: {profile}")
            url = f"https://x.com/{profile.lstrip('@')}"
            await scrape_timeline(url, profile)
            
        # Scrape Twitter Lists
        for tlist in sources.get("twitter_lists", []):
            try:
                set_status(project_dir, f"Scraping Twitter list: {tlist}")
                # Append /members to the list URL to get the directory
                members_url = tlist.rstrip('/') + '/members'
                await page.goto(members_url, timeout=20000)
                await page.wait_for_timeout(5000)
                
                # Scrape all member usernames
                members = await page.evaluate('''() => {
                    const links = document.querySelectorAll('a[role="link"]');
                    const users = new Set();
                    links.forEach(l => {
                        let href = l.getAttribute('href');
                        if (href && href.startsWith('/') && !href.includes('/status/') && !href.includes('/i/') && l.innerText.includes('@')) {
                            users.add(href.substring(1));
                        }
                    });
                    return Array.from(users);
                }''')
                
                if not members:
                    print(f"Warning: Failed to crawl List {tlist}: Could not extract members. Make sure you are authenticated.")
                    continue
                    
                for member in members:
                    url = f"https://x.com/{member}"
                    extracted_text.append(f"--- From Twitter List: {tlist} ---")
                    await scrape_timeline(url, f"@{member}")
                    
            except Exception as e:
                print(f"Warning: Failed to crawl List {tlist}: {str(e)}")
                
        await browser_context.close()
        
    return "\n".join(extracted_text)

def generate_automated_draft(content, timestamp, project_dir):
    """Generates a contrarian draft using the content and links."""
    links = get_internal_links(project_dir)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    draft = ""
    
    if api_key:
        print("Detected GEMINI_API_KEY, attempting to synthesize draft with AI...")
        set_status(project_dir, "we are interpreting and rephrasing your take")
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            
            project_topic = project_dir.replace('projects/', '')
            prompt = f"""You are a brilliant contrarian analyst. Below is a set of raw extracted intelligence for the project '{project_topic}'. 
If the extracted content indicates no sources were provided, you MUST still synthesize a speculative, highly opinionated draft based purely on the project's macro topic ('{project_topic}'), treating it as a thought experiment. NEVER refuse to generate a draft.

CRITICAL RULES FOR YOUR OUTPUT:
1. NEVER output raw URLs in the text (e.g. https://...). Instead, state the human-readable publication name (e.g., "Bitcoin Magazine", "CoinDesk").
2. NEVER use the words: "Contrary", "Contrarian analysis", or "contrarian thesis" anywhere in your text.
3. Your `Subject:` line and the `Take` titles MUST NOT contain any markdown formatting chars like `#` or `*`.

Please synthesize this into a structured markdown document following EXACTLY this format. Use bolding and bullet points in the body text only.

Subject: [A succinct, punchy 4-8 word email subject line summarizing the view. NO # OR *]

# Draft: Automated Insight from Admin Panel

## The Contrarian View
[A 2-3 paragraph macro summary explicitly taking a contrarian stance against general consensus. If no extractions exist, base this purely on the '{project_topic}' macro topic.]

## Take 1: [A punchy 3-5 word title]

> **Atomic Answer:** [A highly polished 40-70 word contrarian take.]

## Take 2: [A punchy 3-5 word title]

> **Atomic Answer:** [A second highly polished 40-70 word contrarian take.]

## Source Intelligence 
Here is a raw snippet of what our engine found:
> [A short representative quote from the extractions. If none exist, write: "Synthesized from macro thesis without external intelligence inputs."]

## Connecting the Dots
As previously discussed in our core thesis, these developments align perfectly with our prior research.
### Related Reading:
{links}

*(Generated asynchronously by the Local Sourcing Engine)*

Here is the raw extracted content to analyze:
{content}
"""
            
            set_status(project_dir, "Waiting for Gemini interpreter response...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            draft = response.text
            print("Successfully synthesized the intelligence!")
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                set_status(project_dir, "Warning: Gemini API Rate Limit Exceeded. Using local synthesis.")
            else:
                set_status(project_dir, "Warning: Gemini API Connection Failed. Using local synthesis.")
            print(f"Failed to generate draft with Gemini: {e}")
            draft = ""
            
    if not draft:
        print("Falling back to static dummy extraction template...")
        project_topic = project_dir.replace('projects/', '')
        
        draft = f"""Subject: Institutional Core Focus

# Draft: Automated Insight from Admin Panel

## The Contrarian View
Based on our recent extractions, the narrative being peddled is fundamentally flawed. We scraped multiple intelligence vectors to find that institutions are actually pivoting away from the presumed consensus regarding {project_topic}.

## Take 1: Institutional Core Focus

> **Atomic Answer:** The latest data on {project_topic} reveals a massive shift. While surface metrics distract the market, true institutional alpha lies deep within blockchain operational infrastructure. The market is entirely mispricing the foundational layer.

## Take 2: True Scaling Reality

> **Atomic Answer:** The real inflection point regarding {project_topic} is structural. Long-term decentralized finance depends entirely on how well the base-layer infrastructure scales to meet these new demands, not on superficial token narratives.

## Source Intelligence 
Here is a raw snippet of what our engine found:
> "Synthesized from macro thesis without external intelligence inputs due to synthesis timeout."

## Connecting the Dots
As previously discussed in our core thesis, these developments align perfectly with our prior research.
### Related Reading:
{links}

*(Generated asynchronously by the Local Sourcing Engine - Fallback Mode)*
"""
    
    journal_dir = os.path.join(project_dir, "journal")
    draft_path = os.path.join(journal_dir, f"draft-auto-{timestamp}.md")
    
    os.makedirs(journal_dir, exist_ok=True)
    with open(draft_path, "w") as f:
        f.write(draft)
        
    return draft_path

def main():
    parser = argparse.ArgumentParser(description="Antigravity Insight Engine")
    parser.add_argument("--auto", action="store_true", help="Run the automated extraction engine")
    parser.add_argument("--project", type=str, default="Bitcoin trends", help="The name of the project to isolate outputs")
    parser.add_argument("briefing_file", nargs="?", default=None, help="Specific briefing file to inspect")
    args = parser.parse_args()
    
    project_dir = get_project_dir(args.project)

    if args.auto:
        print(f"Running automated extraction engine for project: '{args.project}'...")
        crawled_content = asyncio.run(crawl_sources(project_dir))
            
        # Save exact crawl for records
        os.makedirs(os.path.join(project_dir, "briefings"), exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(os.path.join(project_dir, "briefings/auto_crawled_latest.md"), "w") as f:
            f.write(crawled_content)
        with open(os.path.join(project_dir, f"briefings/extracts-auto-{timestamp}.md"), "w") as f:
            f.write(crawled_content)
            
        draft_file = generate_automated_draft(crawled_content, timestamp, project_dir)
        print(f"DRAFT CREATED: {draft_file}")
        
        try:
            import subprocess
            print("Automatically capturing asset renderings of this new draft...")
            subprocess.run(["python3", "scripts/generate_diffusion_assets.py", "--id", timestamp, "--project", args.project], check=True)
        except Exception as e:
            print(f"Failed to generate assets during extraction: {e}")
    
    elif args.briefing_file:
        print("--- INTERNAL LINK SUGGESTIONS ---")
        print(get_internal_links(project_dir))
        print(f"\n--- BRIEFING CONTEXT ({args.briefing_file}) ---")
        try:
            print(create_context_snippet(args.briefing_file))
        except FileNotFoundError:
            print(f"Error: Could not find briefing file: {args.briefing_file}")
    else:
        print("--- INTERNAL LINK SUGGESTIONS ---")
        print(get_internal_links(project_dir))
        print("\nTip: Run 'python3 .agents/workflows/optimize_insight.py <path-to-briefing.md>' or '--auto' to crawl sources.")

if __name__ == "__main__":
    main()