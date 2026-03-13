import json
import urllib.request
import time

def backfill():
    with open('assets/published_journal.json', 'r') as f:
        data = json.load(f)
        
    for item in data:
        print(f"Triggering regeneration for {item['timestamp']}...")
        payload = {
            "timestamp": item['timestamp'],
            "project": item['project'],
            "publish_state": True,
            "published_takes": item.get('published_takes', 'both')
        }
        
        req = urllib.request.Request(
            'http://localhost:8085/api/publish',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                print(f"Success for {item['timestamp']}: {response.read().decode()}")
        except Exception as e:
            print(f"Error for {item['timestamp']}: {e}")
            
        time.sleep(2)

if __name__ == '__main__':
    backfill()
