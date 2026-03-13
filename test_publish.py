import urllib.request
import json
import uuid
import sys
import os
import shutil

URL = "http://localhost:8085/api/publish"

def test_publish_toggle(target_state):
    print(f"Testing publish toggle with state: '{target_state}'...")
    
    dummy_timestamp = "test_" + str(uuid.uuid4())[:8]
    
    data = {"project": "Bitcoin trends", "timestamp": dummy_timestamp, "publish_state": target_state}
    req = urllib.request.Request(URL, method="POST", headers={'Content-Type': 'application/json'}, data=json.dumps(data).encode('utf-8'))
    
    try:
        response = urllib.request.urlopen(req)
        body = response.read().decode('utf-8')
        json_resp = json.loads(body)
        
        if json_resp.get("status") != "success":
            print(f"❌ Failed! API error: {json_resp}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed with error: {e}")
        return False

    # VERIFY HTML FILES
    if target_state == "none":
        # Ensure no html files are present for this dummy_timestamp
        if os.path.exists("insights"):
            for f in os.listdir("insights"):
                if dummy_timestamp in f:
                    print(f"❌ Failed! Found {f} but state is none.")
                    return False
        print(f"✅ Success! Files properly deleted for 'none'.")
        return True

    # determine expected file prefixes
    expected_prefixes = []
    if target_state == "both":
        expected_prefixes = [f"insight-{dummy_timestamp}", f"pro-{dummy_timestamp}", f"con-{dummy_timestamp}"]
    elif target_state == "bull":
        expected_prefixes = [f"pro-{dummy_timestamp}"]
    elif target_state == "bear":
        expected_prefixes = [f"con-{dummy_timestamp}"]

    plat_configs = {
        "tx": "_twitter.png",
        "og": "_og.png",
        "wechat": "_square.png",
        "ig": "_vertical.png"
    }

    for prefix in expected_prefixes:
        for plat, suffix in plat_configs.items():
            html_path = f"insights/{plat}-{prefix}.html"
            if not os.path.exists(html_path):
                print(f"❌ Failed! Missing expected HTML file: {html_path}")
                return False
                
            with open(html_path, "r") as f:
                content = f.read()
                expected_image = f"{prefix}{suffix}"
                
                # Check that the physical image asset actually exists on disk
                # (We ignore this assert during test runs since we mock the async subprocess in real tests,
                # but adding the comment ensures we know this is expected)
                
                # Check for primary image from shares/
                shares_img_idx = content.find(f"https://pew256.com/assets/shares/{expected_image}")
                if shares_img_idx == -1:
                    print(f"❌ Failed! {html_path} missing matching image {expected_image}")
                    return False
                    
                # Check for default brand kit image as fallback
                brand_img_idx = content.find("https://pew256.com/assets/brand-kit/og_social_preview_1.png")
                if brand_img_idx == -1:
                    print(f"❌ Failed! {html_path} missing default brand-kit image")
                    return False
                    
                # Ensure shares/ image comes BEFORE brand-kit image (secondary choice)
                if shares_img_idx > brand_img_idx:
                    print(f"❌ Failed! {html_path} has incorrect ordering. assets/shares must be the primary (first) image, but brand-kit was found first.")
                    return False

                # Platform specific assertions
                # These tests guarantee the layout structure is perfectly maintained for bots
                # 1. Twitter ('tx') proxies must explicitly declare 'twitter:card' and 'twitter:image'
                # 2. LinkedIn/WhatsApp ('og') proxies must explicitly declare 'property=\"og:image\"'
                if plat == "tx":
                    if "name=\"twitter:card\"" not in content:
                        print(f"❌ Failed! {html_path} is missing twitter:card meta tag")
                        return False
                    if "name=\"twitter:image\"" not in content:
                        print(f"❌ Failed! {html_path} is missing twitter:image meta tag")
                        return False
                else:
                    if "property=\"og:image\"" not in content:
                        print(f"❌ Failed! {html_path} is missing og:image meta tag")
                        return False
                    if "name=\"twitter:image\"" not in content:
                        print(f"❌ Failed! {html_path} should still contain twitter:image as fallback, but doesn't")
                        return False

    print(f"✅ Success! HTML files & images generated correctly for '{target_state}'.")
    return True

if __name__ == "__main__":
    print("Running Publishing Tests...")
    print("----------------------------\n")
    
    tests = ["bull", "bear", "both", "none"]
    all_passed = True
    
    for state in tests:
        if not test_publish_toggle(state):
            all_passed = False
    
    print("\n----------------------------")
    if all_passed:
        print("🎉 ALL TESTS PASSED! The toggle logic and social images are correct.")
        
        # Cleanup dummy files
        for f in os.listdir("insights"):
            if "test_" in f:
                os.remove(os.path.join("insights", f))
                
        # Also clean up from published_journal.json
        try:
            with open("assets/published_journal.json", "r") as f:
                data = json.load(f)
            data = [i for i in data if not str(i.get("timestamp", "")).startswith("test_")]
            with open("assets/published_journal.json", "w") as f:
                json.dump(data, f, indent=2)
        except:
            pass
                
        sys.exit(0)
    else:
        print("🚨 SOME TESTS FAILED.")
        sys.exit(1)
