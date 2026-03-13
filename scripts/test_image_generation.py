import os
import sys
import uuid
import subprocess
import shutil

def run_test():
    print("🚀 Booting Image Asset Generation Test...")
    test_id = "testgen_" + str(uuid.uuid4())[:8]
    
    # 1. Create a dummy draft so generate_diffusion_assets.py finds it
    draft_dir = os.path.join(os.getcwd(), 'projects', 'Bitcoin trends', 'journal')
    os.makedirs(draft_dir, exist_ok=True)
    draft_path = os.path.join(draft_dir, f"draft-{test_id}.md")
    
    expected_files = [
        f"insight-{test_id}_twitter.png",
        f"insight-{test_id}_og.png",
        f"insight-{test_id}_square.png",
        f"insight-{test_id}_vertical.png"
    ]
    
    with open(draft_path, "w") as f:
        f.write("Subject: Automated Asset Integration Test\n")
        f.write("## Take 1:\n> **Atomic Answer:** This is a bull case test.\n")
        f.write("## Take 2:\n> **Atomic Answer:** This is a bear case test.\n")
        
    try:
        # 2. Run the generator script natively using the project virtual environment
        venv_python = os.path.join(os.getcwd(), ".venv", "bin", "python")
        cmd = [venv_python, "scripts/generate_diffusion_assets.py", "--id", test_id, "--project", "Bitcoin trends", "--mode", "both"]
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ Generator script failed!")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)
            
        # 3. Assert all 4 output aspect ratios exist in assets/shares/
        shares_dir = os.path.join(os.getcwd(), "assets", "shares")
        
        missing = False
        for f in expected_files:
            file_path = os.path.join(shares_dir, f)
            if not os.path.exists(file_path):
                print(f"❌ Missing expected output asset: {f}")
                missing = True
            else:
                # Basic file size check to ensure it actually wrote real image bytes
                if os.path.getsize(file_path) < 1000:
                    print(f"❌ Asset {f} is suspiciously small (< 1KB). Generation logic may have failed silently.")
                    missing = True
                    
        if missing:
            sys.exit(1)
            
        print("✅ Success! All social media hardware aspect ratios successfully generated and saved to assets/shares/.")
        
    finally:
        # 4. Cleanup dummy testing footprint from disk
        if os.path.exists(draft_path):
            os.remove(draft_path)
        for f in expected_files:
            file_path = os.path.join(shares_dir, f)
            if os.path.exists(file_path):
                os.remove(file_path)

if __name__ == "__main__":
    run_test()
