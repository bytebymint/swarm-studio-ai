import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl

SECRET_KEYS = re.compile(r"(^|[_-])(token|secret|password|passwd|authorization|session|api[_-]?key|credential|signature|jwt)($|[_-])", re.I)


def normalize_url(raw):
    raw = raw.strip()
    if not raw or any(ord(c) < 32 for c in raw):
        raise ValueError("Enter a website URL or localhost address.")
    if not re.match(r"^[a-z][a-z\d+.-]*://", raw, re.I):
        raw = ("http://" if re.match(r"^(localhost|127\.0\.0\.1|\[::1\])(:|/|$)", raw) else "https://") + raw
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only http:// and https:// website addresses are supported.")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in website addresses are not supported.")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("The URL port is invalid.") from exc
    if any(SECRET_KEYS.search(k) for k, _ in parse_qsl(parsed.query)):
        raise ValueError("Remove secret or session parameters from the URL before capture.")
    return urlunsplit(parsed)
