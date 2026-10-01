from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def login_rate_limit_key(request) -> str:
    return f"{request.client.host}:login_attempt"
