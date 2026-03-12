import glob
import os
import re

draft_files = glob.glob("journal/draft-auto-*.md")
print(f"Found {len(draft_files)} draft files to check for missing extractions.")

for filepath in draft_files:
    # Get timestamp from filename
    filename = os.path.basename(filepath)
    # format is draft-auto-YYYYMMDD_HHMMSS.md
    timestamp_match = re.search(r'draft-auto-(.*?)\.md', filename)
    if not timestamp_match:
        continue
    timestamp = timestamp_match.group(1)
    
    extracts_file = f"briefings/extracts-auto-{timestamp}.md"
    if os.path.exists(extracts_file):
        continue
        
    print(f"Extraction missing for {timestamp}, attempting to backfill from draft...")
    
    with open(filepath, "r") as f:
        content = f.read()
    
    # Try to extract the snippet between "## Source Intelligence" and "## Connecting the Dots"
    snippet_match = re.search(r'## Source Intelligence\s*(.*?)\s*## Connecting the Dots', content, re.DOTALL)
    if not snippet_match:
        # Fallback if the format changed slightly
        snippet_match = re.search(r'## Source Intelligence\s*(.*)', content, re.DOTALL)
        
    if snippet_match:
        snippet = snippet_match.group(1).strip()
        # Remove the leading quotes or "Here is a raw snippet..." if any
        snippet = snippet.replace("Here is a raw snippet of what our engine found:", "").strip()
        if snippet.startswith("> "):
            snippet = snippet[2:]
        snippet = snippet.replace("\n> ", "\n")
        
        # Create a formatted markdown string
        reconstructed_extract = f"# Reconstructed Extraction Log\n\n*This log was reconstructed from the associated draft because historical logging was not enabled at the time of generation.*\n\n---\n\n{snippet}\n"
        
        with open(extracts_file, "w") as f:
            f.write(reconstructed_extract)
        print(f"  -> Successfully recreated {extracts_file}")
    else:
        print(f"  -> Failed: Could not find Source Intelligence section in {filepath}")

print("Done backfilling extractions!")
