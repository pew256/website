import json
import os
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8085

def get_project_dir(project_name):
    safe_name = "".join([c for c in project_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
    if not safe_name:
        safe_name = "Bitcoin trends"
    return os.path.join("projects", safe_name)

class AdminServer(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
        
    def send_error(self, code, message=None, explain=None):
        if code == 404:
            try:
                with open(os.path.join(os.getcwd(), '404.html'), 'rb') as f:
                    content = f.read()
                self.send_response(404)
                self.send_header("Content-Type", "text/html")
                self.send_header("Connection", "close")
                super().end_headers()
                self.wfile.write(content)
            except IOError:
                super().send_error(code, message, explain)
        else:
            super().send_error(code, message, explain)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        qs = parse_qs(parsed_url.query)
        project_name = qs.get("project", ["Bitcoin trends"])[0]
        proj_dir = get_project_dir(project_name)
        sources_file = os.path.join(proj_dir, 'sources.json')
        
        if parsed_url.path == '/api/projects':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            os.makedirs("projects", exist_ok=True)
            projects = [d for d in os.listdir("projects") if os.path.isdir(os.path.join("projects", d))]
            if "Bitcoin trends" not in projects:
                os.makedirs(os.path.join("projects", "Bitcoin trends"), exist_ok=True)
                projects.append("Bitcoin trends")
                
            self.wfile.write(json.dumps({"status": "success", "projects": sorted(projects)}).encode())

        elif parsed_url.path == '/api/sources':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            os.makedirs(proj_dir, exist_ok=True)
            if not os.path.exists(sources_file):
                with open(sources_file, 'w') as f:
                    json.dump({"twitter_profiles": [], "twitter_lists": [], "web_crawls": [], "rss_feeds": [], "mailing_lists": []}, f)
            
            with open(sources_file, 'r') as f:
                self.wfile.write(f.read().encode())

        elif parsed_url.path == '/api/latest':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            draft_file = ""
            extractions = ""
            atomic_answer = ""
            
            try:
                journal_dir = os.path.join(proj_dir, "journal")
                if os.path.exists(journal_dir):
                    drafts = [f for f in os.listdir(journal_dir) if f.startswith("draft-auto-")]
                    if drafts:
                        drafts.sort()
                        draft_file = os.path.join(journal_dir, drafts[-1])
            except Exception:
                pass
                
            if draft_file:
                try:
                    with open(draft_file, "r") as f:
                        draft_content = f.read()
                        answers = []
                        import re
                        matches = re.findall(r'> \*\*Atomic Answer:\*\*(.*?)(?=\n\n|\Z)', draft_content, re.DOTALL)
                        if matches:
                            for i, match in enumerate(matches):
                                title = "The Bull Case (Pro)" if i == 0 else "The Bear Case (Con)"
                                color = "#10b981" if i == 0 else "#ef4444"
                                match_text = match.strip()
                                answers.append(f'<div style="background: var(--surface); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border); border-top: 3px solid {color};"><h4 style="margin-top: 0; color: {color}; margin-bottom: 0.5rem;">{title}</h4><p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">{match_text}</p></div>')
                        
                        main_summary = ""
                        summary_match = re.search(r'## The Contrarian View\n(.*?)(?=\n## |\Z)', draft_content, re.DOTALL)
                        if summary_match:
                            main_summary = f'<div style="background: var(--surface); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border); margin-top: 1rem;"><h4 style="margin-top: 0; margin-bottom: 0.5rem; color: var(--primary);">The Contrarian View</h4><p style="margin: 0; font-size: 1rem; line-height: 1.6;">{summary_match.group(1).strip()}</p></div>'
                        
                        if answers:
                            grid_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-top: 1.5rem;">{"".join(answers)}</div>'
                            atomic_answer = main_summary + grid_html
                        else:
                            atomic_answer = "No atomic answer found in draft."
                            
                        subject = "Contrarian Draft"
                        subject_match = re.search(r'^Subject:\s*(.*)$', draft_content, re.MULTILINE)
                        if subject_match:
                            subject = subject_match.group(1).strip()
                except Exception:
                    subject = "Contrarian Draft"
                    atomic_answer = "Error reading draft."
            
            try:
                with open(os.path.join(proj_dir, "briefings/auto_crawled_latest.md"), "r") as f:
                    extractions = f.read()
            except Exception:
                pass

            response_data = {
                "status": "success", 
                "draft_file": draft_file, 
                "extractions": extractions, 
                "atomic_answer": atomic_answer,
                "subject": subject if draft_file else "No insights found."
            }
            self.wfile.write(json.dumps(response_data).encode())

        elif parsed_url.path == '/api/history':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            history = []
            published_map = {}
            try:
                with open("assets/published_journal.json", "r") as f:
                    pub_data = json.load(f)
                    for item in pub_data:
                        published_map[str(item.get("timestamp"))] = item.get("published_takes", "both")
            except Exception:
                pass
                
            try:
                journal_dir = os.path.join(proj_dir, "journal")
                journal_files = os.listdir(journal_dir) if os.path.exists(journal_dir) else []
                for f in journal_files:
                    if f.startswith("draft-auto-") and f.endswith(".md"):
                        timestamp = f.replace("draft-auto-", "").replace(".md", "")
                        
                        try:
                            with open(os.path.join(journal_dir, f), "r") as df:
                                content = df.read()
                                answers = []
                                import re
                                answers = []
                                bull_case = ""
                                bear_case = ""
                                # Try new format
                                matches = re.findall(r'> \*\*Atomic Answer:\*\*(.*?)(?=\n\n|\Z)', content, re.DOTALL)
                                if matches:
                                    for i, match in enumerate(matches):
                                        title = "The Bull Case (Pro)" if i == 0 else "The Bear Case (Con)"
                                        color = "#10b981" if i == 0 else "#ef4444"
                                        match_text = match.strip()
                                        if i == 0:
                                            bull_case = match_text
                                        elif i == 1:
                                            bear_case = match_text
                                        answers.append(f'<div style="background: var(--surface); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border); border-top: 3px solid {color};"><h4 style="margin-top: 0; color: {color}; margin-bottom: 0.5rem;">{title}</h4><p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">{match_text}</p></div>')
                                else:
                                    # Fallback to older format
                                    ans1, ans2 = None, None
                                    if "**Atomic Answer 1:**" in content:
                                        ans1 = content.split("**Atomic Answer 1:**", 1)[1].strip().split("\n\n")[0]
                                    if "**Atomic Answer 2:**" in content:
                                        ans2 = content.split("**Atomic Answer 2:**", 1)[1].strip().split("\n\n")[0]
                                        
                                    if ans1:
                                        bull_case = ans1
                                        answers.append(f'<div style="background: var(--surface); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border); border-top: 3px solid #10b981;"><h4 style="margin-top: 0; color: #10b981; margin-bottom: 0.5rem;">The Bull Case (Pro)</h4><p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">{ans1}</p></div>')
                                    if ans2:
                                        bear_case = ans2
                                        answers.append(f'<div style="background: var(--surface); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border); border-top: 3px solid #ef4444;"><h4 style="margin-top: 0; color: #ef4444; margin-bottom: 0.5rem;">The Bear Case (Con)</h4><p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">{ans2}</p></div>')
                                
                                # Try to extract the main Contrarian View summary
                                main_summary = ""
                                summary_match = re.search(r'## The Contrarian View\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
                                if summary_match:
                                    main_summary = f'<div style="background: var(--surface); padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border); margin-top: 1rem;"><h4 style="margin-top: 0; margin-bottom: 0.5rem; color: var(--primary);">The Contrarian View</h4><p style="margin: 0; font-size: 1rem; line-height: 1.6;">{summary_match.group(1).strip()}</p></div>'
                                
                                if answers:
                                    grid_html = f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-top: 1.5rem;">{"".join(answers)}</div>'
                                    atomic_answer = main_summary + grid_html
                                else:
                                    atomic_answer = "No atomic answer found in draft."
                                
                                # Extract Subject
                                subject = "Contrarian Draft"
                                subject_match = re.search(r'^Subject:\s*(.*)$', content, re.MULTILINE)
                                if subject_match:
                                    subject = subject_match.group(1).strip()
                                    
                        except Exception:
                            atomic_answer = "Error reading draft."
                            subject = "Contrarian Draft"
                        
                        extracts_file = os.path.join(proj_dir, f"briefings/extracts-auto-{timestamp}.md")
                        has_extracts = os.path.exists(extracts_file)
                        
                        is_pub = timestamp in published_map
                        pub_takes = published_map.get(timestamp, 'none') if is_pub else 'none'
                        
                        history.append({
                            "timestamp": timestamp,
                            "draft_file": os.path.join(journal_dir, f),
                            "extracts_file": extracts_file if has_extracts else None,
                            "atomic_answer": atomic_answer,
                            "subject": subject,
                            "bull_case": bull_case,
                            "bear_case": bear_case,
                            "is_published": is_pub,
                            "published_takes": pub_takes
                        })
                # Sort newest first
                history.sort(key=lambda x: x["timestamp"], reverse=True)
            except Exception as e:
                pass
                
            self.wfile.write(json.dumps({"status": "success", "history": history}).encode())

        else:
            # Fall back to serving static files (index.html, admin.html, css, etc.)
            super().do_GET()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        
        if parsed_url.path == '/api/projects/create':
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}
            project_name = req.get('name', 'New Project')
            proj_dir = get_project_dir(project_name)
            os.makedirs(proj_dir, exist_ok=True)
            
            sources_file = os.path.join(proj_dir, 'sources.json')
            if not os.path.exists(sources_file):
                with open(sources_file, 'w') as f:
                    json.dump({"twitter_profiles": [], "twitter_lists": [], "web_crawls": [], "rss_feeds": [], "mailing_lists": []}, f)
                    
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"success"}')
            
        elif parsed_url.path == '/api/edit_draft':
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))
            project_name = req.get('project', 'default')
            timestamp = req.get('timestamp')
            
            proj_dir = get_project_dir(project_name)
            draft_path = os.path.join(proj_dir, "journal", f"draft-auto-{timestamp}.md")
            
            try:
                with open(draft_path, "r") as f:
                    content = f.read()
                
                # Replace exact old text with new text (if changed)
                if req.get('old_subject') and req.get('new_subject') and req['old_subject'] != req['new_subject']:
                    content = content.replace(req['old_subject'], req['new_subject'], 1)
                if req.get('old_bull') and req.get('new_bull') and req['old_bull'] != req['new_bull']:
                    content = content.replace(req['old_bull'], req['new_bull'], 1)
                if req.get('old_bear') and req.get('new_bear') and req['old_bear'] != req['new_bear']:
                    content = content.replace(req['old_bear'], req['new_bear'], 1)
                    
                with open(draft_path, "w") as f:
                    f.write(content)
                
                # Update published_journal.json if it is already published
                pub_file = "assets/published_journal.json"
                if os.path.exists(pub_file):
                    with open(pub_file, "r") as f:
                        pub_data = json.load(f)
                        
                    changed = False
                    for item in pub_data:
                        if str(item.get("timestamp")) == str(timestamp):
                            if req.get('old_subject') != req.get('new_subject'): item["subject"] = req['new_subject']
                            if req.get('old_bull') != req.get('new_bull'): item["bull_case"] = req['new_bull']
                            if req.get('old_bear') != req.get('new_bear'): item["bear_case"] = req['new_bear']
                            changed = True
                            
                    if changed:
                        with open(pub_file, "w") as f:
                            json.dump(pub_data, f, indent=2)
                            
                        # Re-generate OpenGraph image to reflect edits on Public page OG
                        for item in pub_data:
                            if str(item.get("timestamp")) == str(timestamp):
                                try:
                                    import subprocess
                                    subprocess.run(["python3", "scripts/generate_og_image.py", 
                                                    "--timestamp", str(timestamp), 
                                                    "--project", project_name, 
                                                    "--takes", item.get("published_takes", "both"),
                                                    "--subject", item["subject"], 
                                                    "--bull", item["bull_case"], 
                                                    "--bear", item["bear_case"]], check=True)
                                except Exception as e:
                                    print(f"Failed to generate OG image on edit: {e}")
                                break
                                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status":"success"}')
            except Exception as e:
                print(f"Error editing draft: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"status":"error"}')
            
        elif parsed_url.path == '/api/sources':
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))
            
            project_name = req.get('project', 'Bitcoin trends')
            proj_dir = get_project_dir(project_name)
            sources_file = os.path.join(proj_dir, 'sources.json')
            
            if not os.path.exists(sources_file):
                os.makedirs(proj_dir, exist_ok=True)
                with open(sources_file, 'w') as f:
                    json.dump({"twitter_profiles": [], "twitter_lists": [], "web_crawls": [], "rss_feeds": [], "mailing_lists": []}, f)
            
            with open(sources_file, 'r') as f:
                data = json.load(f)
            
            list_type = req.get('type')
            item = req.get('item')
            action = req.get('action')

            if list_type in data:
                if action == 'add' and item not in data[list_type]:
                    if list_type == 'twitter_profiles' and item.startswith('#'):
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"status":"error", "message":"Hashtags are not supported"}')
                        return
                    data[list_type].append(item)
                elif action == 'remove' and item in data[list_type]:
                    data[list_type].remove(item)
                elif action == 'edit' and item in data[list_type]:
                    new_item = req.get('newItem')
                    if new_item:
                        if list_type == 'twitter_profiles' and new_item.startswith('#'):
                            self.send_response(400)
                            self.end_headers()
                            self.wfile.write(b'{"status":"error", "message":"Hashtags are not supported"}')
                            return
                        idx = data[list_type].index(item)
                        data[list_type][idx] = new_item
                elif action == 'clear':
                    data[list_type] = []

                with open(sources_file, 'w') as f:
                    json.dump(data, f, indent=2)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"success"}')

        elif parsed_url.path == '/api/run':
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}
            project_name = req.get('project', 'Bitcoin trends')
            proj_dir = get_project_dir(project_name)

            # Trigger the extraction engine.
            # We use subprocess to run the python script in the .venv environment
            try:
                # Assuming .venv exists from previous steps
                cmd = f"source .venv/bin/activate && python3 .agents/workflows/optimize_insight.py --auto --project '{project_name}'"
                result = subprocess.run(cmd, shell=True, check=True, executable='/bin/bash', capture_output=True, text=True)
                
                # Check output for the draft filename
                output = result.stdout
                draft_file = "check the journal output" # default fallback
                for line in output.split('\n'):
                    if "DRAFT CREATED:" in line:
                        draft_file = line.split("DRAFT CREATED:")[1].strip()

                extractions = ""
                try:
                    with open(os.path.join(proj_dir, "briefings/auto_crawled_latest.md"), "r") as f:
                        extractions = f.read()
                except Exception:
                    pass
                
                atomic_answer = ""
                try:
                    if os.path.exists(draft_file):
                        with open(draft_file, "r") as f:
                            draft_content = f.read()
                            answers = []
                            if "**Atomic Answer 1:**" in draft_content:
                                parts = draft_content.split("**Atomic Answer 1:**", 1)
                                if len(parts) > 1:
                                    ans1 = parts[1].strip().split("\n\n")[0]
                                    answers.append(f"<b>Take 1:</b> {ans1}")
                            if "**Atomic Answer 2:**" in draft_content:
                                parts = draft_content.split("**Atomic Answer 2:**", 1)
                                if len(parts) > 1:
                                    ans2 = parts[1].strip().split("\n\n")[0]
                                    answers.append(f"<b>Take 2:</b> {ans2}")
                            
                            if answers:
                                atomic_answer = "<br><br>".join(answers)
                            # Fallback for old drafts
                            elif "**Atomic Answer:**" in draft_content:
                                parts = draft_content.split("**Atomic Answer:**", 1)
                                if len(parts) > 1:
                                    atomic_answer_raw = parts[1].strip()
                                    atomic_answer = atomic_answer_raw.split("\n\n")[0]
                except Exception:
                    pass

                self.send_response(200)
                self.end_headers()
                response_data = {
                    "status": "success", 
                    "draft_file": draft_file, 
                    "extractions": extractions, 
                    "atomic_answer": atomic_answer
                }
                self.wfile.write(json.dumps(response_data).encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": e.stderr}).encode())

        elif parsed_url.path == '/api/publish':
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))
            project_name = req.get('project', 'Bitcoin trends')
            timestamp = req.get('timestamp')
            
            # publish_state is now a string: 'bull', 'bear', 'both', or 'none' (or boolean true/false for legacy)
            publish_state_raw = req.get('publish_state')
            published_takes = publish_state_raw
            if publish_state_raw is True:
                published_takes = 'both'
            elif publish_state_raw is False:
                published_takes = 'none'
            
            pub_file = "assets/published_journal.json"
            insights_dir = "insights"
            shares_dir = "assets/shares"
            os.makedirs(insights_dir, exist_ok=True)
            os.makedirs(shares_dir, exist_ok=True)
            
            try:
                with open(pub_file, "r") as f:
                    pub_data = json.load(f)
            except Exception:
                pub_data = []

            # Remove existing entry if it exists
            pub_data = [item for item in pub_data if str(item.get("timestamp")) != str(timestamp)]

            insight_html_path = os.path.join(insights_dir, f"{timestamp}.html")
            insight_image_path = os.path.join(shares_dir, f"insight-{timestamp}.png")

            if published_takes and published_takes != 'none':
                # Add it
                proj_dir = get_project_dir(project_name)
                draft_path = os.path.join(proj_dir, "journal", f"draft-auto-{timestamp}.md")
                subject = "Contrarian Draft"
                bull_case = ""
                bear_case = ""
                
                try:
                    with open(draft_path, "r") as f:
                        content = f.read()
                        import re
                        subject_match = re.search(r'^Subject:\s*(.*)$', content, re.MULTILINE)
                        if subject_match:
                            subject = subject_match.group(1).strip()
                            
                        # Extract bull/bear
                        matches = re.findall(r'> \*\*Atomic Answer:\*\*(.*?)(?=\n\n|\Z)', content, re.DOTALL)
                        if matches and len(matches) >= 2:
                            bull_case = matches[0].strip()
                            bear_case = matches[1].strip()
                        else:
                            ans1 = content.split('**Atomic Answer 1:**', 1)[1].strip().split('\\n\\n')[0] if '**Atomic Answer 1:**' in content else ''
                            ans2 = content.split('**Atomic Answer 2:**', 1)[1].strip().split('\\n\\n')[0] if '**Atomic Answer 2:**' in content else ''
                            bull_case = ans1
                            bear_case = ans2
                except Exception:
                    pass
                    
                pub_data.append({
                    "timestamp": timestamp,
                    "project": project_name,
                    "subject": subject,
                    "bull_case": bull_case,
                    "bear_case": bear_case,
                    "published_takes": published_takes
                })
                
                # Generate OpenGraph image
                try:
                    subprocess.run(["python3", "scripts/generate_og_image.py", 
                                    "--timestamp", str(timestamp), 
                                    "--project", project_name, 
                                    "--takes", published_takes,
                                    "--subject", subject, 
                                    "--bull", bull_case, 
                                    "--bear", bear_case], check=True)
                except Exception as e:
                    print(f"Failed to generate OG image: {e}")

                # Determine specific image path to use based on target take
                target_img_prefix = f"insight-{timestamp}"
                if published_takes == "bear":
                    target_img_prefix = f"con-{timestamp}"
                elif published_takes == "bull":
                    target_img_prefix = f"pro-{timestamp}"
                    
                # Dynamic description (40-60 words) to prevent mobile ellipses
                desc_text = bull_case if published_takes == 'bull' else (bear_case if published_takes == 'bear' else f"{bull_case} {bear_case}")
                words = desc_text.replace('\n', ' ').split()
                if len(words) > 55:
                    dynamic_desc = " ".join(words[:55]) + "..."
                elif len(words) >= 40:
                    dynamic_desc = " ".join(words)
                else:
                    dynamic_desc = f"{subject} - " + " ".join(words)
                    if len(dynamic_desc.split()) > 60:
                        dynamic_desc = " ".join(dynamic_desc.split()[:55]) + "..."
                    
                # Generate Platform-Specific Static HTMLs for crawlers
                platforms = {
                    "x": f"{target_img_prefix}_twitter.png",
                    "wechat": f"{target_img_prefix}_square.png",
                    "ig": f"{target_img_prefix}_vertical.png",
                    "og": f"{target_img_prefix}_og.png"
                }
                
                for plat, img_suffix in platforms.items():
                    plat_html_path = os.path.join(insights_dir, f"{plat}-{target_img_prefix}.html")
                    static_html = f'''<!DOCTYPE html>
<html lang="en" prefix="og: http://ogp.me/ns#">
<head>
    <meta charset="utf-8">
    <title>{subject} | pew256 Journal</title>
    <meta name="description" content="{dynamic_desc.replace('"', '&quot;')}">
    
    <!-- OpenGraph / LinkedIn / WeChat / WhatsApp -->
    <meta property="og:title" content="{subject} | pew256">
    <meta property="og:description" content="{dynamic_desc.replace('"', '&quot;')}">
    <meta property="og:image" content="https://pew256.com/assets/shares/{img_suffix}">
    <meta property="og:url" content="https://pew256.com/insights/{plat}-{target_img_prefix}.html">
    <meta property="og:type" content="article">
    
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{subject} | pew256">
    <meta name="twitter:description" content="{dynamic_desc.replace('"', '&quot;')}">
    <meta name="twitter:image" content="https://pew256.com/assets/shares/{img_suffix}">
    
    <script>
        // Redirect human visitors to the correct section of the main app
        window.location.replace('https://pew256.com/index.html#{target_img_prefix}');
        setTimeout(function() {{
            window.location.replace('https://pew256.com/');
        }}, 2500);
    </script>
</head>
<body>
    <p>Redirecting to the journal...</p>
    <p>If you are not redirected automatically, <a href="https://pew256.com/index.html#{target_img_prefix}">click here to read the insight</a>.</p>
</body>
</html>'''
                    with open(plat_html_path, "w") as f:
                        f.write(static_html)

            else:
                # Remove static assets if unpublishing
                for plat in ["x", "wechat", "ig", "og"]:
                    p_path = os.path.join(insights_dir, f"{plat}-{timestamp}.html")
                    if os.path.exists(p_path): os.remove(p_path)
                
                # Try to remove old fallback
                old_html = os.path.join(insights_dir, f"{timestamp}.html")
                if os.path.exists(old_html): os.remove(old_html)

            with open(pub_file, "w") as f:
                json.dump(pub_data, f, indent=2)

            # Generate diffusion assets (4K, Square, Vertical, Twitter, OG) organically
            if published_takes and published_takes != 'none':
                try:
                    import subprocess
                    subprocess.Popen(["python3", "scripts/generate_diffusion_assets.py", "--id", target_img_prefix])
                except Exception as e:
                    print(f"Failed to generate diffusion assets: {e}")

            # Git operations
            try:
                subprocess.run("git add assets/published_journal.json insights/ assets/shares/", shell=True, check=True)
                subprocess.run("git commit -m 'Auto-publish insight to Journal'", shell=True, check=True)
                subprocess.run("git push -u origin main", shell=True, check=True)
            except Exception as e:
                print(f"Git error: {e}")

            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "published_takes": published_takes}).encode())

        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    os.makedirs('projects/Bitcoin trends', exist_ok=True)
    with HTTPServer(('', PORT), AdminServer) as httpd:
        print(f"Serving at port {PORT}")
        print(f"Admin Panel: http://localhost:{PORT}/admin.html")
        httpd.serve_forever()
