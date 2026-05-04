#!/usr/bin/env python3
"""
HTTP smoke / flow tests for User Service + Mentoring Service (stdlib only; no pip deps).

Exit code: 0 = all steps passed, 1 = one or more failures.

Local URLs (repo root `docker-compose.yml` host ports)
  User service:     http://localhost:8000
  Mentoring service: http://localhost:8004

If you run mentoring backend alone (see mentor-mentee-module/backend/README.md), it is often
http://localhost:8000 — then point --mentoring there and set --user-service to wherever login lives.

Examples
--------
  python scripts/mentoring_api_smoke_test.py \\
    --user-service http://localhost:8000 \\
    --mentoring http://localhost:8004 \\
    --mentee-email mentee@test.com --mentee-password "your-password"

  python scripts/mentoring_api_smoke_test.py ... --print-curl

  python scripts/mentoring_api_smoke_test.py --mentoring https://your-run.app --jwt "eyJ..."

  python scripts/mentoring_api_smoke_test.py ... --run-matchmaking \\
    --target-mentor-user-id "00000000-0000-0000-0000-000000000001" \\
    --mentor-email mentor@test.com --mentor-password "secret"

  python scripts/mentoring_api_smoke_test.py ... --book-first-slot

Environment variables (optional instead of flags)
  MENTORING_BASE_URL, USER_SERVICE_URL, MENTEE_EMAIL, MENTEE_PASSWORD,
  MENTOR_EMAIL, MENTOR_PASSWORD, TARGET_MENTOR_USER_ID, MENTORING_JWT

Cloud Run (secrets not in git): copy scripts/mentoring_api_smoke_cloud.example.py to
scripts/mentoring_api_smoke_cloud.py (gitignored), or run the cloud launcher if you
already have that file locally — it sets USER_SERVICE_URL, MENTORING_BASE_URL,
JWT_SECRET, INTERNAL_API_TOKEN, and related service URLs then invokes this script.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote


def _decode_jwt_payload_unverified(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


@dataclass
class RunContext:
    mentoring_base: str
    user_service_url: str | None
    jwt: str | None = None
    print_curl: bool = False
    insecure_tls: bool = False
    failures: list[str] = field(default_factory=list)

    def api(self, path: str) -> str:
        base = self.mentoring_base.rstrip("/")
        p = path if path.startswith("/") else f"/{path}"
        return f"{base}{p}"

    def fail(self, step: str, detail: str) -> None:
        self.failures.append(f"{step}: {detail}")

    def ok(self, step: str) -> None:
        print(f"  PASS  {step}")


def sh_quote(s: str) -> str:
    return json.dumps(s)


def _curl_line(method: str, url: str, headers: dict[str, str], body: Any | None) -> str:
    parts = ["curl", "-sS", "-X", method, sh_quote(url)]
    for k, v in headers.items():
        parts.extend(["-H", sh_quote(f"{k}: {v}")])
    if body is not None and method.upper() not in ("GET", "HEAD"):
        parts.extend(["-H", sh_quote("Content-Type: application/json"), "-d", sh_quote(json.dumps(body))])
    return " ".join(parts)


def http_json(
    ctx: RunContext,
    step: str,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    expected_status: int | tuple[int, ...] = 200,
) -> tuple[int, Any]:
    h = dict(headers or {})
    data: bytes | None = None
    if body is not None and method.upper() not in ("GET", "HEAD"):
        data = json.dumps(body).encode("utf-8")
        h.setdefault("Content-Type", "application/json")

    if ctx.print_curl:
        print(f"    # {step}")
        print(f"    {_curl_line(method, url, h, body)}")

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=h)
    ctx_ssl = ssl.create_default_context()
    if ctx.insecure_tls:
        ctx_ssl.check_hostname = False
        ctx_ssl.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx_ssl) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", errors="replace")
    except Exception as e:
        ctx.fail(step, f"request error: {e}")
        return 0, None

    exp = (expected_status,) if isinstance(expected_status, int) else expected_status
    if code not in exp:
        ctx.fail(step, f"HTTP {code}, expected {exp}: {raw[:500]}")
        return code, None

    if not raw.strip():
        return code, None
    try:
        return code, json.loads(raw)
    except json.JSONDecodeError:
        ctx.fail(step, f"non-JSON body (HTTP {code}): {raw[:300]}")
        return code, None


def login(ctx: RunContext, base: str, email: str, password: str) -> str | None:
    url = base.rstrip("/") + "/login"
    code, data = http_json(
        ctx,
        f"login {email}",
        "POST",
        url,
        body={"email": email, "password": password},
        expected_status=200,
    )
    if data is None:
        return None
    token = data.get("access_token")
    if not token:
        ctx.fail("login", "missing access_token in response")
        return None
    return str(token)


def step_health(ctx: RunContext, label: str, base: str | None) -> None:
    if not base:
        return
    url = base.rstrip("/") + "/health"
    code, data = http_json(ctx, f"{label} GET /health", "GET", url, expected_status=200)
    if data is not None and str(data.get("status", "")).lower() == "ok":
        ctx.ok(f"{label} /health")
    elif code == 200:
        ctx.ok(f"{label} /health (body: {data})")


def run_smoke(
    ctx: RunContext,
    mentee_email: str | None,
    mentee_password: str | None,
) -> str | None:
    token = ctx.jwt
    if token:
        ctx.ok("using --jwt (skip login)")
        return token
    if not ctx.user_service_url or not mentee_email or not mentee_password:
        ctx.fail("smoke", "need --jwt or (--user-service + mentee credentials)")
        return None
    token = login(ctx, ctx.user_service_url, mentee_email, mentee_password)
    if not token:
        return None
    ctx.ok("mentee login -> access_token")

    _, me = http_json(
        ctx,
        "GET /api/v1/profiles/me",
        "GET",
        ctx.api("/api/v1/profiles/me"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        expected_status=200,
    )
    if me is not None:
        ctx.ok("GET /api/v1/profiles/me")

    _, stats = http_json(
        ctx,
        "GET /api/v1/dashboard/stats",
        "GET",
        ctx.api("/api/v1/dashboard/stats"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        expected_status=200,
    )
    if stats is not None:
        ctx.ok("GET /api/v1/dashboard/stats")

    for path, name in (
        ("/api/v1/requests/outgoing", "GET /api/v1/requests/outgoing"),
        ("/api/v1/requests/incoming", "GET /api/v1/requests/incoming"),
        ("/api/v1/requests/history?limit=20", "GET /api/v1/requests/history"),
        ("/api/v1/scheduling/connected-mentors", "GET /api/v1/scheduling/connected-mentors"),
    ):
        code, _ = http_json(
            ctx,
            name,
            "GET",
            ctx.api(path),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            expected_status=(200, 404),
        )
        if code == 404 and "history" in path:
            ctx.ok(f"{name} (404 — route not deployed; not fatal)")
        elif code == 200:
            ctx.ok(name)

    q = quote("a", safe="")
    url = ctx.api(f"/api/v1/search?q={q}&role=mentor&limit=5")
    _, _ = http_json(
        ctx,
        "GET /api/v1/search",
        "GET",
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        expected_status=200,
    )
    ctx.ok("GET /api/v1/search?q=a&role=mentor")

    return token


def run_matchmaking(
    ctx: RunContext,
    mentee_email: str,
    mentee_password: str,
    mentor_email: str,
    mentor_password: str,
    target_mentor_user_id: str,
) -> None:
    if not ctx.user_service_url:
        ctx.fail("matchmaking", "--user-service required")
        return
    t_mentee = login(ctx, ctx.user_service_url, mentee_email, mentee_password)
    if not t_mentee:
        return
    ctx.ok("matchmaking: mentee login")

    intro = "Automated test intro — mentorship request."
    code, created = http_json(
        ctx,
        "POST /api/v1/requests (create)",
        "POST",
        ctx.api("/api/v1/requests"),
        headers={"Authorization": f"Bearer {t_mentee}", "Accept": "application/json"},
        body={"mentor_id": target_mentor_user_id, "intro_message": intro},
        expected_status=(200, 201, 409),
    )
    if code == 409:
        ctx.ok("POST /api/v1/requests (409 pending exists — continuing)")
    elif created is not None:
        ctx.ok("POST /api/v1/requests (created)")

    t_mentor = login(ctx, ctx.user_service_url, mentor_email, mentor_password)
    if not t_mentor:
        return
    ctx.ok("matchmaking: mentor login")

    _, incoming = http_json(
        ctx,
        "GET /api/v1/requests/incoming (mentor)",
        "GET",
        ctx.api("/api/v1/requests/incoming"),
        headers={"Authorization": f"Bearer {t_mentor}", "Accept": "application/json"},
        expected_status=200,
    )
    if not isinstance(incoming, list):
        return

    mentee_uid = (_decode_jwt_payload_unverified(t_mentee) or {}).get("user_id")
    sender_id: str | None = None
    for row in incoming:
        sid = str(row.get("sender_user_id") or "")
        if mentee_uid and sid == str(mentee_uid):
            sender_id = sid
            break
    if sender_id is None and incoming:
        sender_id = str(incoming[0].get("sender_user_id") or "")
    if not sender_id:
        ctx.fail("matchmaking", "no incoming request found; check mentor UUID / seed data")
        return
    ctx.ok(f"matchmaking: incoming sender_user_id={sender_id}")

    _, upd = http_json(
        ctx,
        "POST /api/v1/requests/{sender}/status ACCEPTED",
        "POST",
        ctx.api(f"/api/v1/requests/{sender_id}/status"),
        headers={"Authorization": f"Bearer {t_mentor}", "Accept": "application/json"},
        body={"status": "ACCEPTED"},
        expected_status=200,
    )
    if upd is not None:
        ctx.ok("POST /api/v1/requests/.../status ACCEPTED")


def run_book_first_slot(ctx: RunContext, mentee_email: str, mentee_password: str) -> None:
    if not ctx.user_service_url:
        ctx.fail("booking", "--user-service required")
        return
    token = login(ctx, ctx.user_service_url, mentee_email, mentee_password)
    if not token:
        return

    _, mentors = http_json(
        ctx,
        "GET /api/v1/scheduling/connected-mentors",
        "GET",
        ctx.api("/api/v1/scheduling/connected-mentors"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        expected_status=200,
    )
    if not isinstance(mentors, list) or not mentors:
        ctx.fail("booking", "no ACTIVE connections — connect mentee↔mentor before booking")
        return
    m0 = mentors[0]
    conn_id = m0.get("connection_id")
    mentor_id = m0.get("mentor_id")
    if not conn_id or not mentor_id:
        ctx.fail("booking", "connected-mentors row missing connection_id or mentor_id")
        return
    ctx.ok("GET /api/v1/scheduling/connected-mentors (has connection)")

    mid = quote(str(mentor_id), safe="")
    _, slots = http_json(
        ctx,
        "GET /api/v1/scheduling/availability",
        "GET",
        ctx.api(f"/api/v1/scheduling/availability?mentor_id={mid}"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        expected_status=200,
    )
    if not isinstance(slots, list) or not slots:
        ctx.fail("booking", "no availability slots — mentor must POST availability first")
        return
    slot0 = slots[0]
    slot_id = slot0.get("slot_id") or slot0.get("id")
    if not slot_id:
        ctx.fail("booking", f"unexpected slot shape: {slot0!r}")
        return
    ctx.ok("GET /api/v1/scheduling/availability (has slot)")

    _, booked = http_json(
        ctx,
        "POST /api/v1/scheduling/book",
        "POST",
        ctx.api("/api/v1/scheduling/book"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        body={"connection_id": str(conn_id), "slot_id": str(slot_id)},
        expected_status=(200, 201),
    )
    if booked is not None:
        ctx.ok("POST /api/v1/scheduling/book")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mentoring API smoke / flow tests (stdlib HTTP).")
    ap.add_argument("--mentoring", default=os.environ.get("MENTORING_BASE_URL", ""), help="Mentoring API base URL")
    ap.add_argument("--user-service", default=os.environ.get("USER_SERVICE_URL", ""), help="User service base URL (/login)")
    ap.add_argument("--jwt", default=os.environ.get("MENTORING_JWT", ""), help="Bearer JWT (skips login)")
    ap.add_argument("--mentee-email", default=os.environ.get("MENTEE_EMAIL", ""))
    ap.add_argument("--mentee-password", default=os.environ.get("MENTEE_PASSWORD", ""))
    ap.add_argument("--mentor-email", default=os.environ.get("MENTOR_EMAIL", ""))
    ap.add_argument("--mentor-password", default=os.environ.get("MENTOR_PASSWORD", ""))
    ap.add_argument("--target-mentor-user-id", default=os.environ.get("TARGET_MENTOR_USER_ID", ""))
    ap.add_argument("--print-curl", action="store_true", help="Print equivalent curl commands")
    ap.add_argument("--insecure", action="store_true", help="Skip TLS certificate verification")
    ap.add_argument("--run-matchmaking", action="store_true", help="Mentee POST request + mentor ACCEPT")
    ap.add_argument("--book-first-slot", action="store_true", help="Book first available slot (writes data)")
    args = ap.parse_args()

    if not args.mentoring:
        print("ERROR: set --mentoring or MENTORING_BASE_URL", file=sys.stderr)
        return 1

    ctx = RunContext(
        mentoring_base=args.mentoring,
        user_service_url=args.user_service or None,
        jwt=args.jwt or None,
        print_curl=args.print_curl,
        insecure_tls=args.insecure,
    )

    print("== Health ==")
    step_health(ctx, "mentoring", args.mentoring)
    step_health(ctx, "user-service", args.user_service or None)

    print("== Smoke ==")
    run_smoke(ctx, args.mentee_email or None, args.mentee_password or None)

    if args.run_matchmaking:
        print("== Matchmaking ==")
        if not args.target_mentor_user_id:
            ctx.fail("matchmaking", "--target-mentor-user-id required")
        elif not args.mentee_email or not args.mentee_password or not args.mentor_email or not args.mentor_password:
            ctx.fail("matchmaking", "need mentee + mentor email/password")
        else:
            run_matchmaking(
                ctx,
                args.mentee_email,
                args.mentee_password,
                args.mentor_email,
                args.mentor_password,
                args.target_mentor_user_id.strip(),
            )

    if args.book_first_slot:
        print("== Booking ==")
        if not args.mentee_email or not args.mentee_password:
            ctx.fail("booking", "need --mentee-email and --mentee-password")
        else:
            run_book_first_slot(ctx, args.mentee_email, args.mentee_password)

    print("== Summary ==")
    if ctx.failures:
        for f in ctx.failures:
            print(f"  FAIL  {f}")
        print(f"\n{len(ctx.failures)} failure(s)")
        return 1
    print("All steps passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
