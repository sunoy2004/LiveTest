import requests

def test_recs():
    # Login as mentee_1
    login_data = {"email": "mentee_1@test.com", "password": "password123"}
    resp = requests.post("http://localhost:8000/login", json=login_data)
    if resp.status_code != 200:
        print("Login failed")
        return
    
    token = resp.json()["token"]
    user_id = resp.json()["user"]["id"]
    
    # Call AI service
    headers = {"Authorization": f"Bearer {token}", "X-User-Id": user_id}
    # User service URL is used as base for proxy, but here we can call ai-service directly (8001)
    # wait, the AI service is on 8001
    resp = requests.get(f"http://localhost:8001/recommendations?user_id={user_id}", headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        for r in data[:3]:
            print(f"Mentor: {r.get('mentor_id')}, Name: {r.get('display_name')}")
    else:
        print(resp.text)

if __name__ == "__main__":
    test_recs()
