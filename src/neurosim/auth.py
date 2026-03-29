import hashlib
import hmac
import os


def _get_access_code() -> str:
    return os.environ.get("NEUROSIM_ACCESS_CODE", "")


def generate_token(passphrase: str) -> str:
    """Generate an HMAC token from a passphrase."""
    return hmac.new(
        key=b"neurosim-access",
        msg=passphrase.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def validate_token(token: str | None) -> bool:
    """Check if a token matches the current access code."""
    if not token:
        return False
    expected = generate_token(_get_access_code())
    return hmac.compare_digest(token, expected)


def check_passphrase(passphrase: str) -> bool:
    """Check if a passphrase matches the access code."""
    return hmac.compare_digest(passphrase, _get_access_code())
