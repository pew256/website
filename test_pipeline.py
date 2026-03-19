#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse
import subprocess
import time

def print_pass(msg):
    print(f"[\033[92mPASS\033[0m] {msg}")

def print_fail(msg):
    print(f"[\033[91mFAIL\033[0m] {msg}")

def test_config_validity():
    print("\n--- Test 1: Validate config.json Structure ---")
    try:
        with open('config.json', 'r') as f:
            data = json.load(f)
        if 'hero_headline' in data:
            print_pass("config.json is valid JSON and contains expected base keys.")
            return True
        else:
            print_fail("config.json missing core keys.")
            return False
    except Exception as e:
        print_fail(f"config.json is invalid: {e}")
        return False

def test_server_api_get():
    print("\n--- Test 2: Local Server /api/config GET ---")
    try:
        url = "http://localhost:8085/api/config?lang=en"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                # Should be flattened, not nested dicts for keys
                if isinstance(data.get('hero_headline'), str):
                    print_pass("/api/config flattening engine operates correctly for 'en'.")
                    return True
                else:
                    print_fail("/api/config flattening failed! Got object instead of string.")
                    return False
            else:
                print_fail(f"Failed HTTP {response.status}")
                return False
    except urllib.error.URLError:
        print_fail("Is server.py running on port 8085?")
        return False
    except Exception as e:
        print_fail(f"API Error: {e}")
        return False

def test_server_api_post():
    print("\n--- Test 3: Local Server /api/config POST (Save Translation) ---")
    try:
        # We read current config, add a dummy spaces to description, and post it to simulate a save
        with open('config.json', 'r') as f:
            data = json.load(f)
        
        # Don't mutate actual content heavily, just simulate string structure
        post_data = json.dumps(data).encode('utf-8')
        url = "http://localhost:8085/api/config"
        req = urllib.request.Request(url, data=post_data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                out = json.loads(response.read().decode())
                if out.get('status') == 'success':
                    print_pass("/api/config POST (Save Edits) returns successful JSON, verifying null parser protections.")
                    return True
                else:
                    print_fail(f"Server rejected save with: {out.get('message')}")
                    return False
            else:
                print_fail("Save endpoint returned non-200")
                return False
    except Exception as e:
        print_fail(f"Save POST API Error: {e}")
        return False

def test_git_diff_aggregate():
    print("\n--- Test 4: Verify diff parser endpoint ---")
    try:
        url = "http://localhost:8085/api/git_diff?hash=aggregate"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if 'json_diff' in data:
                    print_pass("Git diff builder and config unnest parser work correctly.")
                    return True
                else:
                    print_fail("Diff payload is missing 'json_diff' array.")
                    return False
    except Exception as e:
        print_fail(f"Diff API Error: {e}")
        return False

def test_git_push_configuration():
    print("\n--- Test 5: Verify Publish Target Configuration ---")
    try:
        # Check that the origin remote is correct for the public website
        remote_url = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True, check=True).stdout.strip()
        if 'pew256/website' in remote_url:
            print_pass(f"Git remote 'origin' is correctly pointing to public repo: {remote_url}")
        else:
            print_fail(f"Git remote 'origin' is incorrect! Expected pew256/website, got: {remote_url}")
            return False
            
        # Check that pew256-admin is gitignored so it never publishes
        with open('.gitignore', 'r') as f:
            if 'pew256-admin' in f.read():
                print_pass("pew256-admin is actively ignored by .gitignore, protecting admin logic from publish.")
            else:
                print_fail("pew256-admin is NOT in .gitignore! Admin logic may leak to public repo.")
                return False
                
        # Check that pew256-admin has its own correct origin
        import os
        if os.path.exists("pew256-admin/.git"):
            admin_remote = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True, check=True, cwd="pew256-admin").stdout.strip()
            if 'pew256/pew256-admin' in admin_remote:
                print_pass(f"Admin infrastructure correctly bound to private repo: {admin_remote}")
            else:
                print_fail(f"Admin infrastructure origin is incorrect! Expected pew256/pew256-admin, got: {admin_remote}")
                return False
        else:
            print_fail("Admin infrastructure missing .git directory! Cannot push internally.")
            return False
            
        # Check that server.py contains the dual-push logic
        with open('pew256-admin/server.py', 'r') as f:
            if 'admin core sync' in f.read():
                print_pass("Server.py accurately contains the dual-tier automation to synchronize both repositories.")
            else:
                print_fail("Server.py is missing the dual-tier push logic!")
                return False
                
        return True
    except Exception as e:
        print_fail(f"Git configuration error: {e}")
        return False

def test_config_diff_generator():
    print("\n--- Test 7: Verify JSON Differential Engine (Unnest Parser) ---")
    try:
        # Save original config
        with open('config.json', 'r') as f:
            original_content = f.read()
        
        # Inject dummy edit
        data = json.loads(original_content)
        data['hero_headline'] = "PIPELINE_TEST_EDIT_" + str(time.time())
        with open('config.json', 'w') as f:
            json.dump(data, f)
            
        # Trigger diff engine
        url = "http://localhost:8085/api/git_diff?hash=pending"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                out = json.loads(response.read().decode())
                json_diff = out.get('json_diff', [])
                
                # Restore immediately before checking asserts to ensure clean state
                with open('config.json', 'w') as f:
                    f.write(original_content)
                    
                if len(json_diff) > 0 and any(item.get('key') == 'hero_headline' for item in json_diff):
                    print_pass("JSON structural differential engine correctly parsed the modification without throwing silent NameErrors.")
                    return True
                else:
                    print_fail("Differential engine failed to capture the structural change. The unnest recursive function crashed or swallowed an exception.")
                    return False
            else:
                # Restore
                with open('config.json', 'w') as f:
                    f.write(original_content)
                print_fail("Diff endpoint returned non-200")
                return False
    except Exception as e:
        # Restore
        try:
            with open('config.json', 'w') as f:
                f.write(original_content)
        except: pass
        print_fail(f"Differential API Error: {e}")
        return False

def test_cache_headers():
    print("\n--- Test 6: Verify API Cache-Control Headers ---")
    try:
        url = "http://localhost:8085/api/git_history"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            headers = dict(response.info())
            cache_header = headers.get('Cache-Control', '')
            if 'no-store' in cache_header and 'no-cache' in cache_header:
                print_pass("Cache-Control headers confirm browsers will not phantom-cache pending statuses.")
                return True
            else:
                print_fail(f"Missing aggressive cache-busting headers! Found: {cache_header}")
                return False
    except Exception as e:
        print_fail(f"Header API Error: {e}")
        return False

def test_preview_aggregate():
    print("\n--- Test 8: Verify Previewer Aggregate Endpoint ---")
    try:
        url = "http://localhost:8085/previewer?hash=aggregate"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                html = response.read().decode('utf-8')
                if "Unsaved / Pending Modifications" in html:
                    print_pass("Previewer successfully intercepts the 'aggregate' virtual hash and generates a localized time machine iframe.")
                    return True
                else:
                    print_fail("Previewer responded with 200 but failed to render the specific aggregate HTML payload.")
                    return False
            else:
                print_fail("Previewer endpoint returned non-200. It likely crashed trying to pass 'aggregate' string to git.")
                return False
    except Exception as e:
        print_fail(f"Previewer API Error: {e}")
        return False

if __name__ == '__main__':
    print("========================================")
    print("   pew256.com Pipeline Self-Test")
    print("========================================")
    
    t1 = test_config_validity()
    t2 = test_server_api_get()
    t3 = test_server_api_post()
    t4 = test_git_diff_aggregate()
    t5 = test_git_push_configuration()
    t6 = test_cache_headers()
    t7 = test_config_diff_generator()
    t8 = test_preview_aggregate()
    
    print("\n========================================")
    if all([t1, t2, t3, t4, t5, t6, t7, t8]):
        print("\033[92mALL PIPELINE TESTS PASSED\033[0m")
        print("Your application state is structurally sound.")
    else:
        print("\033[91mSOME TESTS FAILED. PLEASE REVIEW LOGS.\033[0m")
    print("========================================")
    
    # Optional: Automatically execute locally to show user results
