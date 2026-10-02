"""Trusted, explicit first-admin operation; dry-run by default, never an HTTP route.

Run from implementation with the M1 virtualenv. The intended person must first
sign in, verify email and sync their normal staff account through the real UI.
Only after explicit operator approval run --apply with the same exact UID twice.
No signup, password, provider account, or backup administrator is created here.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.access_foundation import DisabledVerifier
from app.m1.config import Settings
from app.m1.bootstrap_provider import configured_bootstrap_directory
from app.m1.store import M1Store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uid", required=True, help="Existing provider UID copied from the confirmed intended account")
    parser.add_argument("--confirm-uid", required=True, help="Repeat the exact independently confirmed UID")
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize the local role mutation and live provider verification")
    args = parser.parse_args(argv)
    if args.uid != args.confirm_uid or not args.uid or len(args.uid) > 128:
        parser.error("Exact matching UID confirmation is required.")
    try:
        settings = Settings.from_environment()
        if settings is None:
            raise ValueError("Explicit M1 paths are required.")
        store = M1Store(settings.database)
        # No initialize call: a typo must not create a fresh bootstrap database.
        with store._connection() as db:
            row = db.execute("SELECT id,role,status,email_verified FROM af_users WHERE provider_uid=?", (args.uid,)).fetchone()
            if row is None or row["status"] != "active" or row["email_verified"] != 1:
                raise ValueError("An existing active verified local account is required.")
        if not args.apply:
            print("DRY RUN: existing local account found; no provider call or role change. Confirm the intended UID and obtain explicit approval before --apply.")
            return 0
        directory = configured_bootstrap_directory(settings)
        if isinstance(directory, DisabledVerifier):
            raise ValueError("Firebase server verification must be explicitly configured.")
        changed = store.bootstrap_first_admin(directory, provider_uid=args.uid, confirmed_uid=args.confirm_uid)
        print("Primary administrator initialized." if changed else "Unchanged: this same primary administrator was already initialized.")
        return 0
    except Exception:
        # No credential, provider diagnostic, private filesystem path or user data.
        print("Bootstrap refused. Check isolated M1 configuration, existing verified account, exact UID approval, and bootstrap eligibility.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
