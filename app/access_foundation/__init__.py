"""Unwired access-control preparation; importing this package has no side effects.

Legacy routes, database and file serving are NOT protected by this package.
See docs/ACCESS_FOUNDATION.md before any future integration.
"""

from .identity import AuthenticationDenied, DisabledVerifier, VerifiedIdentity
from .store import AccessDenied, DevelopmentAccessStore, Role, Status

__all__ = [
    "AccessDenied", "AuthenticationDenied", "DevelopmentAccessStore",
    "DisabledVerifier", "Role", "Status", "VerifiedIdentity",
]
