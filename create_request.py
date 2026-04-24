import requests

BASE_URL = "http://localhost:8000"

def create_request():
    # Login as mentee_1
    login_data = {"email": "mentee_1@test.com", "password": "password123"}
    resp = requests.post(f"{BASE_URL}/login", json=login_data)
    if resp.status_code != 200:
        print("Mentee Login failed:", resp.text)
        return
    
    token = resp.json()["token"]
    user_id = resp.json()["user"]["id"]
    print(f"Logged in as mentee_1, ID: {user_id}")
    
    # Get mentor_1 profile id
    mentor_auth = requests.post(f"{BASE_URL}/login", json={"email": "mentor_1@test.com", "password": "password123"}).json()
    token_m = mentor_auth["token"]
    resp = requests.get(f"{BASE_URL}/profile/full", headers={"Authorization": f"Bearer {token_m}"})
    mentor_profile_id = resp.json()["mentor_profile"]["id"]
    print(f"Mentor_1 Profile ID: {mentor_profile_id}")
    
    # Create request
    headers = {"Authorization": f"Bearer {token}", "X-User-Id": user_id}
    req_body = {"mentor_id": mentor_profile_id, "intro_message": "Hello mentor 1!"}
    resp = requests.post(f"{BASE_URL}/api/v1/requests", json=req_body, headers=headers)
    print(f"Create request status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == "__main__":
    create_request()
