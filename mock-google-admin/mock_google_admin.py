"""Mock of the Google Workspace Admin SDK Directory API -- just enough surface for
the HRIS provisioning workflow, with real response shapes.

Why a mock: the workflow's Google leg has to be demonstrable without a paid
Workspace tenant and without domain-wide delegation. The request/response
bodies mirror the real Directory API ``users`` / ``members`` resources, so
pointing the HTTP Request nodes at https://admin.googleapis.com with a Google
OAuth2 credential is a URL + auth swap, not a rewrite.

Endpoints
  GET  /admin/directory/v1/users/{userKey}            200 user | 404 notFound
  POST /admin/directory/v1/users                      200 user | 400 invalid | 409 duplicate
  POST /admin/directory/v1/groups/{groupKey}/members  200 member | 400 invalid | 409 duplicate
  GET  /admin/directory/v1/groups/{groupKey}/members  200 members list
  GET  /_mock/state                                   dump users/groups/calls
  POST /_mock/reset                                   clear everything
  POST /_mock/fail-next   {"count": 1, "status": 500} make the next N mutating
                                                      calls fail (GETs stay truthful)

Stdlib only. In-memory. Passwords are validated but never stored or echoed.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

USERS_PATH = "/admin/directory/v1/users"
GROUPS_PATH = "/admin/directory/v1/groups"


class State:
    def __init__(self) -> None:
        self.lock = threading.RLock()  # re-entrant: _send records the call while callers may hold it
        self.reset()

    def reset(self) -> None:
        self.users: dict[str, dict] = {}         # primaryEmail (lower) -> user resource
        self.groups: dict[str, list[dict]] = {}  # groupKey (lower) -> [member resource]
        self.calls: list[dict] = []
        self.fail_next = 0
        self.fail_status = 500
        self._next_id = 100000000000000000000

    def new_id(self) -> str:
        self._next_id += 1
        return str(self._next_id)


STATE = State()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def google_error(code: int, reason: str, message: str) -> dict:
    return {"error": {"code": code, "message": message,
                      "errors": [{"domain": "global", "reason": reason, "message": message}]}}


class Handler(BaseHTTPRequestHandler):
    server_version = "MockGoogleAdmin/1.0"

    # ---- plumbing -------------------------------------------------------
    def log_message(self, fmt, *args):  # one line per call, no timestamps noise
        sys.stdout.write("%s\n" % (fmt % args))
        sys.stdout.flush()

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
        if not self.path.startswith("/_mock/"):  # keep healthcheck/state polls out of the call log
            with STATE.lock:
                STATE.calls.append({"ts": now_iso(), "method": self.command,
                                    "path": self.path, "status": status})

    def _json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _consume_failure(self) -> bool:
        """True if this mutating call must fail (fail-next armed)."""
        with STATE.lock:
            if STATE.fail_next > 0:
                STATE.fail_next -= 1
                return True
        return False

    # ---- routing --------------------------------------------------------
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/_mock/state":
            with STATE.lock:
                snapshot = {"users": STATE.users, "groups": STATE.groups,
                            "fail_next": STATE.fail_next, "calls": list(STATE.calls)}
            return self._send(200, snapshot)
        if path.startswith(USERS_PATH + "/"):
            key = unquote(path[len(USERS_PATH) + 1:]).lower()
            with STATE.lock:
                user = STATE.users.get(key) or next(
                    (u for u in STATE.users.values() if u["id"] == key), None)
            if user:
                return self._send(200, user)
            return self._send(404, google_error(404, "notFound", "Resource Not Found: userKey"))
        if path.startswith(GROUPS_PATH + "/") and path.endswith("/members"):
            group_key = unquote(path[len(GROUPS_PATH) + 1:-len("/members")]).lower()
            with STATE.lock:
                members = list(STATE.groups.get(group_key, []))
            return self._send(200, {"kind": "admin#directory#members", "etag": "\"mock\"",
                                    "members": members})
        return self._send(404, google_error(404, "notFound", "Not Found"))

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/_mock/reset":
            with STATE.lock:
                STATE.reset()
            return self._send(200, {"ok": True})
        if path == "/_mock/fail-next":
            body = self._json_body() or {}
            with STATE.lock:
                STATE.fail_next = int(body.get("count", 1))
                STATE.fail_status = int(body.get("status", 500))
                armed = STATE.fail_next
            return self._send(200, {"ok": True, "fail_next": armed})
        if path == USERS_PATH:
            return self._create_user()
        if path.startswith(GROUPS_PATH + "/") and path.endswith("/members"):
            group_key = unquote(path[len(GROUPS_PATH) + 1:-len("/members")]).lower()
            return self._add_member(group_key)
        return self._send(404, google_error(404, "notFound", "Not Found"))

    # ---- resources ------------------------------------------------------
    def _create_user(self) -> None:
        body = self._json_body()
        if body is None:
            return self._send(400, google_error(400, "invalid", "Invalid JSON body"))
        name = body.get("name") or {}
        email = str(body.get("primaryEmail") or "").strip()
        missing = [f for f, v in (("primaryEmail", email),
                                  ("name.givenName", name.get("givenName")),
                                  ("name.familyName", name.get("familyName")),
                                  ("password", body.get("password"))) if not v]
        if missing or "@" not in email:
            return self._send(400, google_error(
                400, "invalid", "Invalid Input: " + ", ".join(missing or ["primaryEmail"])))
        if self._consume_failure():
            return self._send(STATE.fail_status,
                              google_error(STATE.fail_status, "backendError", "Backend Error"))
        key = email.lower()
        with STATE.lock:
            if key in STATE.users:
                return self._send(409, google_error(409, "duplicate", "Entity already exists."))
            user = {
                "kind": "admin#directory#user",
                "id": STATE.new_id(),
                "etag": "\"mock-%d\"" % (len(STATE.users) + 1),
                "primaryEmail": email,
                "name": {"givenName": name["givenName"], "familyName": name["familyName"],
                         "fullName": "%s %s" % (name["givenName"], name["familyName"])},
                "isAdmin": False,
                "isDelegatedAdmin": False,
                "suspended": False,
                "changePasswordAtNextLogin": bool(body.get("changePasswordAtNextLogin", False)),
                "orgUnitPath": body.get("orgUnitPath") or "/",
                "creationTime": now_iso(),
                "emails": [{"address": email, "primary": True}],
                "externalIds": body.get("externalIds") or [],
                "customerId": "C0mockcust",
            }
            STATE.users[key] = user
        return self._send(200, user)

    def _add_member(self, group_key: str) -> None:
        body = self._json_body()
        if body is None or not str(body.get("email") or "").strip():
            return self._send(400, google_error(400, "invalid", "Invalid Input: memberKey"))
        if self._consume_failure():
            return self._send(STATE.fail_status,
                              google_error(STATE.fail_status, "backendError", "Backend Error"))
        email = str(body["email"]).strip()
        with STATE.lock:
            # Mock simplification: groups are auto-created on first member add.
            members = STATE.groups.setdefault(group_key, [])
            if any(m["email"].lower() == email.lower() for m in members):
                return self._send(409, google_error(409, "duplicate", "Member already exists."))
            user = STATE.users.get(email.lower())
            member = {
                "kind": "admin#directory#member",
                "etag": "\"mock\"",
                "id": user["id"] if user else STATE.new_id(),
                "email": email,
                "role": str(body.get("role") or "MEMBER").upper(),
                "type": "USER",
                "status": "ACTIVE",
                "delivery_settings": "ALL_MAIL",
            }
            members.append(member)
        return self._send(200, member)


def serve(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Mock Google Admin SDK Directory API")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)
    server = serve(args.host, args.port)
    print("mock-google-admin listening on http://%s:%d" % (args.host, args.port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
