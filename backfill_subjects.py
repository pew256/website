import glob

draft_files = glob.glob("journal/draft-auto-*.md")
print(f"Found {len(draft_files)} draft files to check.")

for filepath in draft_files:
    with open(filepath, "r") as f:
        content = f.read()
    
    if "Subject:" in content:
        continue
    
    print(f"Processing local fallback for {filepath}...")
    
    # Simple heuristic to extract the first sentence
    import re
    rawText = content.replace('\n', ' ').replace('# Draft: Automated Insight from Admin Panel', '').strip()
    rawText = rawText.replace('## The Contrarian View', '').strip()
    
    subject = "Contrarian Draft"
    if rawText:
        firstDot = rawText.find('.')
        if firstDot > 0 and firstDot < 80:
            subject = rawText[:firstDot].strip()
        else:
            subject = rawText[:60].strip() + "..."
            
    subject = subject.replace('"', '').replace("'", '').strip()
    
    new_content = f"Subject: {subject}\n\n{content}"
    
    with open(filepath, "w") as f:
        f.write(new_content)
    
    print(f"  -> Added fallback subject: {subject}")

print("Done backfilling all remaining subjects locally!")
