"""Optional shared-credential HTTP Basic Auth gate for the whole app.

Controlled by two environment variables, AUTH_USERNAME / AUTH_PASSWORD - set
them on the hosting platform (e.g. Render) to require a login for the entire
site, including the static frontend and every /api/* route. If either is
unset (e.g. running locally via `uvicorn ...`), the app stays open - there's
no point password-protecting your own laptop.

This is deliberately a single shared username/password for the whole team,
not per-person accounts - simplest thing that actually keeps a public URL
from being open to anyone who finds it.
"""

import base64
import os
import secrets

from fastapi import Request
from fastapi.responses import Response

AUTH_USERNAME = os.environ.get("AUTH_USERNAME")
AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD")

# Render (and most hosts) hit this path to check the service is alive - it
# must stay reachable without credentials or the host will think it's down.
EXEMPT_PATHS = {"/healthz"}


async def basic_auth_middleware(request: Request, call_next):
    if request.url.path in EXEMPT_PATHS or not AUTH_USERNAME or not AUTH_PASSWORD:
        return await call_next(request)

    unauthorized = Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Grade Separation Scoring"'},
    )

    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "basic":
        return unauthorized

    try:
        username, _, password = base64.b64decode(encoded).decode("utf-8").partition(":")
    except Exception:
        return unauthorized

    if not (secrets.compare_digest(username, AUTH_USERNAME) and secrets.compare_digest(password, AUTH_PASSWORD)):
        return unauthorized

    return await call_next(request)
