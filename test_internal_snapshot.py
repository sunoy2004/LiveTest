import httpx
import os

base = os.getenv('USER_SERVICE_URL')
token = os.getenv('INTERNAL_API_TOKEN')
print(f"URL: {base}")
print(f"Token: {token}")
r = httpx.get(f'{base}/internal/matchmaking/snapshot', headers={'X-Internal-Token': token})
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print(f"Mentors: {len(r.json().get('mentors', []))}")
else:
    print(r.text)
