"""Problem 4 check: password hashing (both formats), login, sign-up rules.

Run from the hw4 folder:
    .venv\\Scripts\\python tests\\check_auth.py

Creates one temporary account and deletes it at the end.
"""

import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

HW4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW4 / "backend"))
os.chdir(HW4 / "backend")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
os.environ.setdefault("CC_AUDIT_PATH", str(Path(tempfile.mkdtemp()) / "audit_trail.json"))

from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
from main import app  # noqa: E402

results: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{'  -> ' + detail if detail else ''}")


def main() -> None:
    db = sqlite3.connect(HW4 / "data" / "campus_customs.db")
    c = TestClient(app)
    email = f"auth.check.{int(time.time())}@yale.edu"
    pw = "Strong-pass-123"

    print("\n== Hash formats ==")
    h = auth.hash_password(pw)
    scheme, iters, salt, digest = h.split("$")
    check("new hash = pbkdf2_sha256$600000$salt$hex", scheme == "pbkdf2_sha256" and iters == "600000" and len(digest) == 64)
    check("new hash verifies; wrong password rejected", auth.verify_password(pw, h) and not auth.verify_password("wrong", h))
    check("two hashes of the same password differ (random salt)", auth.hash_password(pw) != h)
    check("malformed / unknown-scheme hashes rejected",
          not auth.verify_password(pw, "garbage") and not auth.verify_password(pw, "md5$x$y"))

    print("\n== Seed user (legacy 3-part hash, 120,000 iterations) ==")
    r = c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
    check("test@campuscustoms.yale.edu / password logs in", r.status_code == 200, r.json()["user"]["first_name"])
    check("login response has no hash or password", "pbkdf2" not in r.text and "password" not in r.json()["user"])
    r = c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "wrong"})
    check("wrong password -> 401", r.status_code == 401, r.json()["detail"])
    c.post("/api/auth/logout")

    print("\n== New account ==")
    try:
        r = c.post("/api/auth/register", json={"first_name": "Auth", "last_name": "Check", "email": email,
                                               "password": pw, "confirm_password": "different"})
        check("mismatched passwords -> 400", r.status_code == 400, r.json()["detail"])
        r = c.post("/api/auth/register", json={"first_name": "Auth", "last_name": "Check", "email": email,
                                               "password": pw, "confirm_password": pw})
        check("create account -> 201", r.status_code == 201)
        stored = db.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()[0]
        check("stored with 600,000 iterations, not plain text", stored.split("$")[1] == "600000" and pw not in stored)
        r = c.post("/api/auth/register", json={"first_name": "Auth", "last_name": "Check", "email": email.upper(),
                                               "password": pw, "confirm_password": pw})
        check("duplicate email (any case) -> 409", r.status_code == 409, r.json()["detail"])
        c.post("/api/auth/logout")
        r = c.post("/api/auth/login", json={"email": email, "password": pw})
        check("new account logs in", r.status_code == 200)
    finally:
        db.execute("DELETE FROM users WHERE lower(email) = ?", (email.lower(),))
        db.commit()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
