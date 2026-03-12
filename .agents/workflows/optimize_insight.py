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

# Optional import, we only need playwright if doing --auto
try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

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

async def crawl_sources(project_dir):
    if not async_playwright:
        print("Playwright not installed. Run: pip install playwright && playwright install")
        return ""
    
    sources_file = os.path.join(project_dir, "sources.json")
    if not os.path.exists(sources_file):
        return f"No sources found. Please configure {sources_file}"
    
    with open(sources_file, "r") as f:
        sources = json.load(f)
        
    extracted_text = []
    
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
                url = site if site.startswith("http") else f"https://{site}"
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                # Clean DOM before extracting completely
                html = await page.evaluate('''() => {
                    document.querySelectorAll('script, style, svg, iframe, nav, footer, header, aside').forEach(e => e.remove());
                    const article = document.querySelector('article');
                    if (article) return article.innerHTML;
                    const main = document.querySelector('main');
                    if (main) return main.innerHTML;
                    return document.body.innerHTML;
                }''')
                
                # Convert messy HTML to clean Markdown to preserve paragraphs/headings
                text = md(html, heading_style="ATX", wrap=True, strip=['script', 'style'])
                extracted_text.append(f"--- From {site} ---\n{text[:5000]}\n")
            except Exception as e:
                extracted_text.append(f"Failed to crawl {site}: {str(e)}")
                
        # Scrape RSS Feeds (Deep Crawl Top Links from last 14 days)
        for feed_url in sources.get("rss_feeds", []):
            try:
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
                        extracted_text.append(f"--- From RSS Feed {feed_url} ---\nNo recent articles (past 14 days) found.\n")
                else:
                    extracted_text.append(f"Failed to crawl RSS {feed_url}: No entries found or invalid feed.")
            except Exception as e:
                extracted_text.append(f"Failed to crawl RSS {feed_url}: {str(e)}")
                
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
                        extracted_text.append(f"Failed to crawl {profile_name}: X.com blocked the request. Please authenticate.")
                    else:
                        extracted_text.append(f"Failed to crawl {profile_name}: No recent tweets found or profile is private.")
                        
            except Exception as e:
                extracted_text.append(f"Failed to crawl {profile_name}: {str(e)}")

        # Scrape Twitter Profiles
        for profile in sources.get("twitter_profiles", []):
            url = f"https://x.com/{profile.lstrip('@')}"
            await scrape_timeline(url, profile)
            
        # Scrape Twitter Lists
        for tlist in sources.get("twitter_lists", []):
            try:
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
                    extracted_text.append(f"Failed to crawl List {tlist}: Could not extract members. Make sure you are authenticated.")
                    continue
                    
                for member in members:
                    url = f"https://x.com/{member}"
                    extracted_text.append(f"--- From Twitter List: {tlist} ---")
                    await scrape_timeline(url, f"@{member}")
                    
            except Exception as e:
                extracted_text.append(f"Failed to crawl List {tlist}: {str(e)}")
                
        await browser_context.close()
        
    return "\n".join(extracted_text)

def generate_automated_draft(content, timestamp, project_dir):
    """Generates a contrarian draft using the content and links."""
    links = get_internal_links(project_dir)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    draft = ""
    
    if api_key:
        print("Detected GEMINI_API_KEY, attempting to synthesize draft with AI...")
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            
            prompt = f"""You are a brilliant contrarian analyst. Below is a set of raw extracted intelligence. 
Please synthesize this into a structured markdown document following EXACTLY this format. Use bolding, bullet points, and clean spacing.

Subject: [A succinct, punchy 4-8 word email subject line summarizing the contrarian view]

# Draft: Automated Insight from Admin Panel

## The Contrarian View
[A 2-3 paragraph macro summary combining the most critical points across the extractions, explicitly taking a contrarian stance against general consensus.]

## Take 1: [A punchy 3-5 word title]

> **Atomic Answer:** [A highly polished 40-70 word contrarian take.]

## Take 2: [A punchy 3-5 word title]

> **Atomic Answer:** [A second highly polished 40-70 word contrarian take.]

## Source Intelligence 
Here is a raw snippet of what our engine found:
> [A short representative quote or two from the extractions.]

## Connecting the Dots
As previously discussed in our core thesis, these developments align perfectly with our prior research.
### Related Reading:
{links}

*(Generated asynchronously by the Local Sourcing Engine)*

Here is the raw extracted content to analyze:
{content}
"""
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            draft = response.text
            print("Successfully synthesized the intelligence!")
        except Exception as e:
            print(f"Failed to generate draft with Gemini: {e}")
            draft = ""
            
    if not draft:
        print("Falling back to static dummy extraction template...")
        # Ensure content has something usable to quote
        clean_content = content.replace("---", "").strip()
        topic_snippet = clean_content[:150].replace('\n', ' ') if clean_content else "general industry trends"

        draft = f"""# Draft: Automated Insight from Admin Panel

## Take 1: Institutional Core Focus

> **Atomic Answer:** The latest data on {topic_snippet[:50]}... reveals a massive shift. While surface metrics distract the market, true institutional alpha lies deep within Bitcoin and blockchain operational infrastructure. The market is entirely mispricing the foundational layer.

## Take 2: True Scaling Reality

> **Atomic Answer:** Contrary to consensus regarding {topic_snippet[:50]}..., the real inflection point is structural. Long-term decentralized finance depends entirely on how well Bitcoin's base-layer infrastructure scales to meet these new demands, not on superficial token narratives.

## The Contrarian View
Based on our recent extractions, the narrative being peddled is fundamentally flawed. We scraped multiple intelligence vectors to find that institutions are actually pivoting *away* from the presumed consensus.

## Source Intelligence 
Here is a raw snippet of what our engine found:
> {content[:200]}...

## Connecting the Dots
As previously discussed in our core thesis, these developments align perfectly with our prior research.
### Related Reading:
{links}

*(Generated asynchronously by the Local Sourcing Engine)*
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