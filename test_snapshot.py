import os
import httpx
import json

def test_snapshot():
    base = "http://localhost:8000"
    token = "change-me-in-production"
    
    r = httpx.get(
        f"{base}/internal/matchmaking/snapshot",
        headers={"X-Internal-Token": token},
        timeout=30.0,
    )
    if r.status_code != 200:
        print(f"Error: {r.status_code}")
        print(r.text)
        return
    
    data = r.json()
    mentors = data.get("mentors", [])
    print(f"Found {len(mentors)} mentors")
    for m in mentors[:3]:
        print(f"UID: {m.get('user_id')}, Name: {m.get('display_name')}, ProfileID: {m.get('mentor_profile_id')}")

if __name__ == "__main__":
    test_snapshot()
