from __future__ import annotations

import hashlib
import hmac
import secrets
from http.cookies import SimpleCookie


PBKDF2_ITERATIONS = 200_000
SESSION_COOKIE_NAME = "saralnyaya_session"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, stored_digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        int(iterations_text),
    )
    return hmac.compare_digest(digest.hex(), stored_digest)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def parse_cookie_header(header_value: str | None) -> dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(header_value or "")
    return {key: morsel.value for key, morsel in cookie.items()}


def build_session_cookie(token: str, max_age: int = 60 * 60 * 24 * 14) -> str:
    cookie = SimpleCookie()
    cookie[SESSION_COOKIE_NAME] = token
    cookie[SESSION_COOKIE_NAME]["path"] = "/"
    cookie[SESSION_COOKIE_NAME]["httponly"] = True
    cookie[SESSION_COOKIE_NAME]["samesite"] = "Lax"
    cookie[SESSION_COOKIE_NAME]["max-age"] = max_age
    return cookie[SESSION_COOKIE_NAME].OutputString()


def build_clear_session_cookie() -> str:
    cookie = SimpleCookie()
    cookie[SESSION_COOKIE_NAME] = ""
    cookie[SESSION_COOKIE_NAME]["path"] = "/"
    cookie[SESSION_COOKIE_NAME]["httponly"] = True
    cookie[SESSION_COOKIE_NAME]["samesite"] = "Lax"
    cookie[SESSION_COOKIE_NAME]["max-age"] = 0
    return cookie[SESSION_COOKIE_NAME].OutputString()
