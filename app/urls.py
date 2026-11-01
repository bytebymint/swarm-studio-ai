import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl

SECRET_KEYS = re.compile(r"(^|[_-])(token|secret|password|passwd|authorization|session|api[_-]?key|credential|signature|jwt)($|[_-])", re.I)
