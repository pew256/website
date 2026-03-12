import json, os, subprocess, re

project_name = "Bitcoin trends"
timestamp = "20260312_145429"
published_takes = "bull"
pub_file = os.path.join("assets", "published_journal.json")

def get_project_dir(name):
    # Mock
    return os.path.join("projects", name if name != "default" else "default")

with open(pub_file, "r") as f:
    pub_data = json.load(f)

pub_data = [item for item in pub_data if str(item.get("timestamp")) != str(timestamp)]

proj_dir = get_project_dir(project_name)
draft_path = os.path.join(proj_dir, "journal", f"draft-auto-{timestamp}.md")
subject = "Contrarian Draft"
bull_case = ""
bear_case = ""

print(f"draft_path: {draft_path}")
print(f"exists? {os.path.exists(draft_path)}")

try:
    with open(draft_path, "r") as f:
        content = f.read()
        subject_match = re.search(r'^Subject:\s*(.*)$', content, re.MULTILINE)
        if subject_match:
            subject = subject_match.group(1).strip()
            
        print(f"found subject: {subject}")
        matches = re.findall(r'> \*\*Atomic Answer:\*\*(.*?)(?=\n\n|\Z)', content, re.DOTALL)
        if matches and len(matches) >= 2:
            bull_case = matches[0].strip()
            bear_case = matches[1].strip()
        else:
            ans1 = content.split('**Atomic Answer 1:**', 1)[1].strip().split('\n\n')[0] if '**Atomic Answer 1:**' in content else ''
            ans2 = content.split('**Atomic Answer 2:**', 1)[1].strip().split('\n\n')[0] if '**Atomic Answer 2:**' in content else ''
            bull_case = ans1
            bear_case = ans2
except Exception as e:
    print(f"Error: {e}")

print(f"bull_case length: {len(bull_case)}")

pub_data.append({
    "timestamp": timestamp,
    "project": project_name,
    "subject": subject,
    "bull_case": bull_case,
    "bear_case": bear_case,
    "published_takes": published_takes
})

with open("/tmp/test_out.json", "w") as f:
    json.dump(pub_data, f, indent=2)

print("done")
