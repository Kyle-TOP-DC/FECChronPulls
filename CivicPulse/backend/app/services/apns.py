"""Apple Push Notification service sender (token-based JWT auth).

Without APNS credentials configured, pushes are logged instead of sent so the
rest of the system (dashboards, push history) still works in development.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx

from ..config import APNS_ENV, APNS_KEY_ID, APNS_KEY_PATH, APNS_TEAM_ID, APNS_TOPIC

log = logging.getLogger(__name__)

_HOSTS = {
    "sandbox": "https://api.sandbox.push.apple.com",
    "production": "https://api.push.apple.com",
}

_jwt_cache: tuple[float, str] | None = None


def configured() -> bool:
    return bool(APNS_TEAM_ID and APNS_KEY_ID and Path(APNS_KEY_PATH).exists())


def _auth_token() -> str:
    """APNs provider JWTs are valid 20-60 minutes; cache for 40."""
    global _jwt_cache
    now = time.time()
    if _jwt_cache and now - _jwt_cache[0] < 2400:
        return _jwt_cache[1]
    import jwt  # PyJWT

    token = jwt.encode(
        {"iss": APNS_TEAM_ID, "iat": int(now)},
        Path(APNS_KEY_PATH).read_text(),
        algorithm="ES256",
        headers={"kid": APNS_KEY_ID},
    )
    _jwt_cache = (now, token)
    return token


def send_push(
    device_tokens: list[str], title: str, body: str, article_id: int | None = None
) -> tuple[int, int]:
    """Send an alert push to each token. Returns (sent, failed)."""
    if not device_tokens:
        return 0, 0
    if not configured():
        log.info(
            "APNs not configured — would send to %d device(s): %s / %s",
            len(device_tokens), title, body,
        )
        return 0, len(device_tokens)

    payload = {
        "aps": {"alert": {"title": title, "body": body}, "sound": "default"},
    }
    if article_id is not None:
        payload["article_id"] = article_id

    host = _HOSTS.get(APNS_ENV, _HOSTS["sandbox"])
    headers = {
        "authorization": f"bearer {_auth_token()}",
        "apns-topic": APNS_TOPIC,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    sent = failed = 0
    with httpx.Client(http2=True, timeout=10) as client:
        for token in device_tokens:
            try:
                resp = client.post(f"{host}/3/device/{token}", json=payload, headers=headers)
                if resp.status_code == 200:
                    sent += 1
                else:
                    failed += 1
                    log.warning("APNs %s for %s…: %s", resp.status_code, token[:8], resp.text)
            except Exception as exc:
                failed += 1
                log.warning("APNs error for %s…: %s", token[:8], exc)
    return sent, failed
