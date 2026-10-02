"""Presentation identity only. Firebase UID remains the authentication authority."""
from __future__ import annotations

import re
import secrets

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
PREFIXES = frozenset({"USR", "REC", "JOB", "RES", "MED", "GRT", "ASN", "EXP"})
RESERVED_HANDLES = frozenset({
    "admin", "administrator", "root", "system", "support", "stethofuse",
    "official", "security", "api", "help", "staff",
})
ADJECTIVES = ("blue", "frost", "silver", "winter", "quiet", "pine", "snow", "fern", "ivory")
NOUNS = ("owl", "dragonfly", "falcon", "finch", "robin", "heron", "otter", "fox", "cedar", "willow")


class IdentityError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def normalize_handle(value: str) -> str:
    value = value.strip().lower()
    if not 3 <= len(value) <= 20:
        raise IdentityError("invalid_handle", "Use between 3 and 20 characters for your handle.")
    if not re.fullmatch(r"[a-z][a-z0-9_.]*[a-z0-9]", value) or re.search(r"[_.]{2}", value):
        raise IdentityError("invalid_handle", "Start with a letter. Use letters, numbers, dots or underscores, without consecutive or ending separators.")
    if value in RESERVED_HANDLES:
        raise IdentityError("reserved_handle", "That handle is reserved. Try another name.")
    return value


def public_reference(prefix: str) -> str:
    if prefix not in PREFIXES:
        raise ValueError("Unknown public reference prefix.")
    value = "".join(secrets.choice(CROCKFORD) for _ in range(10))
    return f"{prefix}-{value[:4]}-{value[4:]}"


def handle_candidate(*, suffix: bool = False) -> str:
    value = secrets.choice(ADJECTIVES) + secrets.choice(NOUNS)
    if suffix:
        value += "".join(secrets.choice(CROCKFORD.lower()) for _ in range(2))
    return normalize_handle(value)
