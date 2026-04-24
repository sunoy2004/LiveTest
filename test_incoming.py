import requests

BASE_URL = "http://localhost:8000"

def test_fetch_incoming():
    # Login as mentor_1
    login_data = {"email": "mentor_1@test.com", "password": "password123"}
    resp = requests.post(f"{BASE_URL}/login", json=login_data)
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
    
    token = resp.json()["token"]
    user_id = resp.json()["user"]["id"]
    print(f"Logged in as mentor_1, ID: {user_id}")
    
    # Fetch incoming requests
    headers = {"Authorization": f"Bearer {token}", "X-User-Id": user_id}
    resp = requests.get(f"{BASE_URL}/api/v1/requests/incoming", headers=headers)
    print(f"Incoming requests status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == "__main__":
    test_fetch_incoming()
