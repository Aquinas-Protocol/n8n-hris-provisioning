"""Contract tests for the mock Admin SDK. Stdlib client; pytest only."""
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mock_google_admin as mga  # noqa: E402


@pytest.fixture(scope="module")
def base():
    server = mga.serve("127.0.0.1", 0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d" % server.server_address[1]
    server.shutdown()


@pytest.fixture(autouse=True)
def _reset(base):
    call(base, "POST", "/_mock/reset")


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


ADA = {"primaryEmail": "Ada.Lovelace@example.test",
       "name": {"givenName": "Ada", "familyName": "Lovelace"},
       "password": "correct horse battery staple", "changePasswordAtNextLogin": True,
       "orgUnitPath": "/Engineering"}
MEMBERS = "/admin/directory/v1/groups/eng-team%40example.test/members"


def test_get_unknown_user_404_shape(base):
    status, body = call(base, "GET", "/admin/directory/v1/users/nobody@example.test")
    assert status == 404
    assert body["error"]["code"] == 404
    assert body["error"]["errors"][0]["reason"] == "notFound"


def test_create_user_then_get_then_duplicate_409(base):
    status, user = call(base, "POST", "/admin/directory/v1/users", ADA)
    assert status == 200
    assert user["kind"] == "admin#directory#user"
    assert user["id"].isdigit() and "password" not in user
    assert user["name"]["fullName"] == "Ada Lovelace"
    # lookup by email is case-insensitive (and URL-encoded), and by id works too
    assert call(base, "GET", "/admin/directory/v1/users/ada.lovelace%40example.test")[0] == 200
    assert call(base, "GET", "/admin/directory/v1/users/" + user["id"])[0] == 200
    status, dup = call(base, "POST", "/admin/directory/v1/users", ADA)
    assert status == 409 and dup["error"]["errors"][0]["reason"] == "duplicate"


def test_add_member_then_duplicate_409(base):
    call(base, "POST", "/admin/directory/v1/users", ADA)
    status, member = call(base, "POST", MEMBERS, {"email": "ada.lovelace@example.test", "role": "MEMBER"})
    assert status == 200
    assert member["kind"] == "admin#directory#member" and member["role"] == "MEMBER"
    status, dup = call(base, "POST", MEMBERS, {"email": "ada.lovelace@example.test"})
    assert status == 409 and dup["error"]["errors"][0]["reason"] == "duplicate"
    status, listing = call(base, "GET", MEMBERS)
    assert status == 200 and len(listing["members"]) == 1


def test_fail_next_only_affects_posts_and_clears(base):
    status, armed = call(base, "POST", "/_mock/fail-next", {"count": 2})
    assert status == 200 and armed["fail_next"] == 2
    # GETs stay truthful while armed
    assert call(base, "GET", "/admin/directory/v1/users/ada.lovelace@example.test")[0] == 404
    s1, e1 = call(base, "POST", "/admin/directory/v1/users", ADA)
    s2, _ = call(base, "POST", "/admin/directory/v1/users", ADA)
    assert (s1, s2) == (500, 500)
    assert e1["error"]["errors"][0]["reason"] == "backendError"
    # failed calls did not mutate state
    assert call(base, "GET", "/_mock/state")[1]["users"] == {}
    # counter exhausted -> third call succeeds
    assert call(base, "POST", "/admin/directory/v1/users", ADA)[0] == 200


def test_validation_400_and_reset(base):
    bad = {"primaryEmail": "x@example.test", "name": {"givenName": "X"}, "password": "p"}
    status, body = call(base, "POST", "/admin/directory/v1/users", bad)
    assert status == 400 and body["error"]["errors"][0]["reason"] == "invalid"
    assert "name.familyName" in body["error"]["message"]
    call(base, "POST", "/admin/directory/v1/users", ADA)
    assert call(base, "GET", "/_mock/state")[1]["users"]
    call(base, "POST", "/_mock/reset")
    state = call(base, "GET", "/_mock/state")[1]
    assert state["users"] == {} and state["groups"] == {} and state["fail_next"] == 0
