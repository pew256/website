import urllib.request
import json
import uuid
import os

URL_EDIT = "http://localhost:8085/api/edit_draft"
URL_REVERT = "http://localhost:8085/api/get_original_content"

# Create a fake draft file
proj = "Bitcoin trends"
proj_dir = f"projects/{proj}/journal"
os.makedirs(proj_dir, exist_ok=True)
dummy_timestamp = "test_revert_" + str(uuid.uuid4())[:8]
draft_path = os.path.join(proj_dir, f"draft-auto-{dummy_timestamp}.md")

orig_text = """Subject: Original Subject Line

# Draft: Automated Insight from Admin Panel

## Take 1: The Bull Title

> **Atomic Answer:** Original Bull paragraph content here.

## Take 2: The Bear Title

> **Atomic Answer:** Original Bear paragraph content here.
"""

with open(draft_path, "w") as f:
    f.write(orig_text)

def test():
    print("Testing original content fetch (Pre-edit)...")
    data = {"project": proj, "timestamp": dummy_timestamp}
    req = urllib.request.Request(URL_REVERT, method="POST", headers={'Content-Type': 'application/json'}, data=json.dumps(data).encode('utf-8'))
    resp = json.loads(urllib.request.urlopen(req).read().decode())
    
    assert resp['subject'] == 'Original Subject Line', "Pre-edit Subject failed"
    assert resp['bull'] == 'Original Bull paragraph content here.', "Pre-edit Bull failed"
    print("✅ Pre-edit read succeeds perfectly from current .md")

    print("\nSimulating a human edit to create a .orig backup...")
    edit_payload = {
        "project": proj,
        "timestamp": dummy_timestamp,
        "old_subject": "Original Subject Line",
        "new_subject": "MUTATED SUBJECT",
        "old_bull": "Original Bull paragraph content here.",
        "new_bull": "MUTATED BULL",
        "old_bear": "Original Bear paragraph content here.",
        "new_bear": "MUTATED BEAR"
    }
    urllib.request.urlopen(urllib.request.Request(URL_EDIT, method="POST", headers={'Content-Type': 'application/json'}, data=json.dumps(edit_payload).encode()))
    
    assert os.path.exists(draft_path + ".orig"), "❌ The .orig backup file was NOT created by api/edit_draft!"
    
    # Read the mutated draft manually to assure it actually changed
    with open(draft_path, "r") as f:
        mut_content = f.read()
    assert "MUTATED SUBJECT" in mut_content, "Mock file did not mutate"

    print("✅ The .orig backup file was successfully created by api/edit_draft.")

    print("\nTesting original content fetch (Post-edit)...")
    req = urllib.request.Request(URL_REVERT, method="POST", headers={'Content-Type': 'application/json'}, data=json.dumps(data).encode('utf-8'))
    resp2 = json.loads(urllib.request.urlopen(req).read().decode())
    
    assert resp2['subject'] == 'Original Subject Line', f"Post-edit Revert failed: {resp2}"
    assert resp2['bull'] == 'Original Bull paragraph content here.', "Post-edit Revert failed"
    assert resp2['bear'] == 'Original Bear paragraph content here.', "Post-edit Revert failed"
    
    print("✅ Post-edit read succeeds perfectly! endpoint parses the .orig raw backup accurately.")

    print("\n🎉 All Revert functionality is verified!")

    # Cleanup
    os.remove(draft_path)
    os.remove(draft_path + ".orig")
    
if __name__ == "__main__":
    test()
