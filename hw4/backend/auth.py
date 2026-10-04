"""Create account, log in, log out, and current-user routes.

Passwords use the same scheme as the existing users in the database:
    pbkdf2_sha256$<salt>$<hex digest>   (PBKDF2-HMAC-SHA256, 120,000 iterations)
Plain passwords and hashes are never logged or returned.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import closing

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

HASH_SCHEME = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000
MIN_PASSWORD_LENGTH = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- password hashing ----------

def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(12)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), HASH_ITERATIONS)
    return f"{HASH_SCHEME}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, expected = stored.split("$")
    except ValueError:
        return False
    if scheme != HASH_SCHEME:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), HASH_ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected)


# A real hash of a random password, so a login with an unknown email
# takes the same time as one with a wrong password.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# ---------- request models ----------

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------- helpers ----------

def public_user(row: sqlite3.Row) -> dict:
    """The only user fields ever sent to the browser (no password hash)."""
    first = row["first_name"] or (row["name"] or "").split(" ")[0]
    last = row["last_name"] or " ".join((row["name"] or "").split(" ")[1:])
    return {"id": row["id"], "first_name": first, "last_name": last, "email": row["email"]}


USER_COLUMNS = "id, name, email, first_name, last_name"


def current_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    with closing(get_db()) as conn:
        row = conn.execute(
            f"SELECT {USER_COLUMNS} FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        request.session.clear()
        return None
    return public_user(row)


# ---------- routes ----------

@router.post("/register", status_code=201)
def register(body: RegisterRequest, request: Request) -> dict:
    first = body.first_name.strip()
    last = body.last_name.strip()
    email = body.email.strip().lower()

    if not first or not last:
        raise HTTPException(400, "Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords do not match.")

    with closing(get_db(readonly=False)) as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if exists:
            raise HTTPException(409, "An account with this email already exists. Try logging in.")
        try:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with this email already exists. Try logging in.")
        row = conn.execute(
            f"SELECT {USER_COLUMNS} FROM users WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    # Sign the new customer in straight away.
    request.session.clear()
    request.session["user_id"] = row["id"]
    return {"user": public_user(row)}


@router.post("/login")
def login(body: LoginRequest, request: Request) -> dict:
    email = body.email.strip().lower()
    with closing(get_db()) as conn:
        row = conn.execute(
            f"SELECT {USER_COLUMNS}, password_hash FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()

    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        # Same message for unknown email and wrong password.
        raise HTTPException(401, "Incorrect email or password.")

    request.session.clear()
    request.session["user_id"] = row["id"]
    return {"user": public_user(row)}


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    return {"user": current_user(request)}
