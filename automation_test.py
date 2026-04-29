import asyncio
import httpx
import uuid
from datetime import datetime

# Configuration
USER_SERVICE_URL = "https://user-service-1095720168864-1095720168864.us-central1.run.app"
MENTORING_SERVICE_URL = "https://mentoring-service-1095720168864-1095720168864.us-central1.run.app"

MENTOR_EMAIL = "mentor_2@test.com"
MENTEE_EMAIL = "mentee_2@test.com"
PASSWORD = "password123"

# For Booking Flow (mentor_1 and mentee_1 are pre-connected in seed)
BOOKING_MENTOR_EMAIL = "mentor_1@test.com"
BOOKING_MENTEE_EMAIL = "mentee_1@test.com"

async def login(email, password):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{USER_SERVICE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if resp.status_code != 200:
            print(f"Login failed for {email}: {resp.text}")
            return None, None
        data = resp.json()
        return data["access_token"], data["user_id"]

async def test_connection_flow():
    print("\n--- Testing Connection Request Flow ---")
    
    # 1. Login as Mentee
    token_me, uid_me = await login(MENTEE_EMAIL, PASSWORD)
    if not token_me: return
    print(f"Logged in as Mentee: {uid_me}")

    # 2. Login as Mentor to get their user_id
    token_mo, uid_mo = await login(MENTOR_EMAIL, PASSWORD)
    if not token_mo: return
    print(f"Target Mentor ID: {uid_mo}")

    async with httpx.AsyncClient() as client:
        # 3. Mentee sends connection request
        # Note: Mentoring Service uses X-User-Id header internally or Bearer token?
        # Based on deps.py, it expects X-User-Id for some, but frontend uses Bearer.
        # Actually, Mentoring Service is decoupled and expects X-User-Id from gateway/proxy.
        # But for this test, we call it directly.
        headers_me = {"Authorization": f"Bearer {token_me}", "X-User-Id": uid_me}
        
        print(f"Sending connection request from {uid_me} to {uid_mo}...")
        req_body = {
            "mentor_user_id": uid_mo,
            "intro_message": "Hello! I would like to be your mentee."
        }
        resp = await client.post(
            f"{MENTORING_SERVICE_URL}/api/v1/requests",
            json=req_body,
            headers=headers_me
        )
        if resp.status_code not in (200, 201):
            print(f"Failed to send request: {resp.text}")
            return
        request_id = resp.json()["id"]
        print(f"Request sent! ID: {request_id}")

        # 4. Mentor accepts the request
        headers_mo = {"Authorization": f"Bearer {token_mo}", "X-User-Id": uid_mo}
        print(f"Mentor {uid_mo} accepting request {request_id}...")
        resp = await client.put(
            f"{MENTORING_SERVICE_URL}/api/v1/requests/{request_id}/status",
            json={"status": "ACCEPTED"},
            headers=headers_mo
        )
        if resp.status_code != 200:
            print(f"Failed to accept request: {resp.text}")
            return
        print("Request accepted! Connection created.")

async def test_booking_flow():
    print("\n--- Testing Session Booking Flow ---")
    
    # 1. Login as Mentor to get ID
    token_mo, uid_mo = await login(BOOKING_MENTOR_EMAIL, PASSWORD)
    if not token_mo: return
    
    # 2. Login as Mentee
    token_me, uid_me = await login(BOOKING_MENTEE_EMAIL, PASSWORD)
    if not token_me: return
    print(f"Logged in as Mentee: {uid_me}")

    async with httpx.AsyncClient() as client:
        headers_me = {"Authorization": f"Bearer {token_me}", "X-User-Id": uid_me}
        headers_mo = {"Authorization": f"Bearer {token_mo}", "X-User-Id": uid_mo}

        # 3. Fetch connected mentors to get the connection_id
        print("Fetching connected mentors...")
        resp = await client.get(
            f"{USER_SERVICE_URL}/api/v1/scheduling/connected-mentors",
            headers=headers_me
        )
        if resp.status_code != 200:
            print(f"Failed to fetch connected mentors: {resp.text}")
            return
        
        mentors = resp.json()
        conn = next((m for m in mentors if str(m["mentor_name"]).lower().startswith("mentor 1")), None)
        if not conn:
            print("Mentor 1 not found in connected mentors list.")
            return
        
        connection_id = conn["connection_id"]
        mentor_id = conn["mentor_id"] # This is the profile ID
        print(f"Using Connection ID: {connection_id}, Mentor Profile ID: {mentor_id}")

        # 4. Get Availability
        print(f"Fetching availability for mentor {mentor_id}...")
        resp = await client.get(
            f"{USER_SERVICE_URL}/api/v1/scheduling/availability?mentor_id={mentor_id}",
            headers=headers_me
        )
        if resp.status_code != 200:
            print(f"Failed to fetch availability: {resp.text}")
            return
        
        slots = resp.json()
        if not slots:
            print("No available slots found for this mentor. Please seed some slots.")
            return
        
        slot_id = slots[0]["slot_id"]
        print(f"Selected Slot ID: {slot_id}")

        # 5. Book Session
        print(f"Booking session for slot {slot_id}...")
        resp = await client.post(
            f"{USER_SERVICE_URL}/api/v1/scheduling/book",
            json={"connection_id": str(connection_id), "slot_id": str(slot_id)},
            headers=headers_me
        )
        if resp.status_code not in (200, 201):
            print(f"Failed to book session: {resp.text}")
            return
        
        booking_request_id = resp.json()["id"]
        print(f"Booking request created! ID: {booking_request_id}")

        # 6. Mentor Accepts Booking
        # The booking confirmation usually happens in the scheduling service or a separate endpoint
        # Based on typical flow, mentor accepts via a PUT to a session_booking_request endpoint
        # But let's assume the flow ends here for the automation or mentor confirms.
        print("Booking flow test completed (Request created).")

async def main():
    try:
        await test_connection_flow()
        await test_booking_flow()
    except Exception as e:
        print(f"\nCRITICAL ERROR during testing: {e}")

if __name__ == "__main__":
    asyncio.run(main())
