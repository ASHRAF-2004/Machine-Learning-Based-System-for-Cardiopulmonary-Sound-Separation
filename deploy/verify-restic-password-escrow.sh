#!/usr/bin/env bash
# Verify the owner's offline Restic password against one known synthetic B2 file.
# The installed /etc/stethofuse/restic-password is deliberately never read.
set -Eeuo pipefail
umask 077

fail() { printf 'Restic escrow recovery: %s\n' "$1" >&2; exit 1; }
runtime_dir="${XDG_RUNTIME_DIR:-}"
[[ -n "$runtime_dir" && -d "$runtime_dir" && ! -L "$runtime_dir" ]] || \
  fail 'A private user runtime directory is required.'
[[ "$(stat -c '%u:%a' -- "$runtime_dir")" == "$(id -u):700" ]] || \
  fail 'The user runtime directory must be owned by this user with mode 0700.'
command -v restic >/dev/null || fail 'Restic is not installed.'
command -v systemd-run >/dev/null || fail 'systemd-run is not installed.'
sudo -n true >/dev/null 2>&1 || fail 'Run from a terminal with an available sudo authorization.'

password_file="$(mktemp "$runtime_dir/stethofuse-restic-paper.XXXXXX")"
restore_dir="$(mktemp -d "$runtime_dir/stethofuse-restic-escrow.XXXXXX")"
chmod 0600 -- "$password_file"
cleanup() {
  result=$?
  trap - EXIT HUP INT TERM
  rm -f -- "$password_file"
  rm -rf -- "$restore_dir"
  exit "$result"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

IFS= read -r -s -p 'Enter the offline Restic repository password (hidden): ' password </dev/tty
printf '\n'
[[ -n "$password" ]] || fail 'The entered password was empty.'
printf '%s' "$password" > "$password_file"
unset password

unit="stethofuse-restic-escrow-verify-$(date +%s)"
sudo systemd-run --unit="$unit" --wait --collect --pipe \
  --property=User=root --property=Group=root --property=UMask=0077 \
  --property=EnvironmentFile=/etc/stethofuse/backup.env \
  --property="LoadCredential=restic-password:$password_file" \
  --property=LoadCredential=b2-application-key-id:/etc/stethofuse/b2-application-key-id \
  --property=LoadCredential=b2-application-key-secret:/etc/stethofuse/b2-application-key-secret \
  --setenv="RECOVERY_DIR=$restore_dir" \
  /bin/bash -ceu '
    cred="$CREDENTIALS_DIRECTORY"
    snapshot="793ee58fb3a158d9dfa6eadefa8301b135f3c5d97ea3d321aef2da514eba8a26"
    fixture="/var/tmp/stethofuse-restore-drill.yciIWQ/source/runtime.env"
    expected="f8126b7eb5c103d336765dd205c9d1309e318cfb4817536d447dd9e45c2a0da8"
    restic_call() {
      AWS_ACCESS_KEY_ID="$(<"$cred/b2-application-key-id")" \
      AWS_SECRET_ACCESS_KEY="$(<"$cred/b2-application-key-secret")" \
        restic --no-cache --password-file "$cred/restic-password" "$@"
    }
    restic_call snapshots "$snapshot" >/dev/null
    restic_call dump "$snapshot" "$fixture" > "$RECOVERY_DIR/runtime.env"
    actual="$(sha256sum "$RECOVERY_DIR/runtime.env" | cut -d" " -f1)"
    [[ "$actual" == "$expected" ]] || {
      printf "Restic escrow recovery: synthetic file hash mismatch.\n" >&2
      exit 1
    }
    printf "RESTIC_PASSWORD_ESCROW_RECOVERY=VERIFIED\n"
    printf "Snapshot: %s\nSynthetic file SHA-256: %s\n" "$snapshot" "$actual"
  '
