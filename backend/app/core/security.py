"""Password hashing and JWT (HS256) without third-party deps."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

PBKDF2_ROUNDS = 120_000
TOKEN_TTL_SECONDS = 12 * 60 * 60


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _pbkdf2(password: str, salt: bytes, rounds: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = _pbkdf2(password, salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = _pbkdf2(password, bytes.fromhex(salt_hex), int(rounds))
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(secret: str, claims: dict[str, Any], ttl: int = TOKEN_TTL_SECONDS) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = dict(claims)
    payload["exp"] = int(time.time()) + ttl
    body = _b64e(json.dumps(header, separators=(",", ":")).encode()) + "." + \
        _b64e(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64e(signature)}"


class TokenError(Exception):
    """Raised when a token is malformed, tampered or expired."""


def decode_token(secret: str, token: str) -> dict[str, Any]:
    try:
        body, signature = token.rsplit(".", 1)
        expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64e(expected), signature):
            raise TokenError("bad signature")
        header_b64, payload_b64 = body.split(".")
        payload = json.loads(_b64d(payload_b64))
    except TokenError:
        raise
    except Exception as exc:  # noqa: BLE001 - any parse error is an invalid token
        raise TokenError("malformed token") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("token expired")
    return payload
