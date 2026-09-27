#!/usr/bin/env bash
set -euo pipefail

readonly target=/etc/stethofuse/b2-application-key-id

if (( EUID != 0 )); then
  printf 'Run this helper with sudo from a local terminal.\n' >&2
  exit 1
fi
if [[ ! -f "$target" || -L "$target" ]]; then
  printf 'Expected an existing regular key-ID file; no change made.\n' >&2
  exit 1
fi

read -r -s -p 'Enter the Backblaze keyID field (not the applicationKey): ' key_id </dev/tty
printf '\n' >/dev/tty
if [[ ! "$key_id" =~ ^[0-9a-f]{25}$ ]]; then
  unset key_id
  printf 'Key ID format rejected; expected 25 lowercase hexadecimal characters. No change made.\n' >&2
  exit 1
fi

umask 0077
staging=$(mktemp /etc/stethofuse/.b2-key-id.XXXXXXXX)
cleanup() {
  if [[ -n "${staging:-}" && -e "$staging" ]]; then
    rm -f -- "$staging"
  fi
  unset key_id
}
trap cleanup EXIT HUP INT TERM

printf '%s\n' "$key_id" >"$staging"
unset key_id
chown root:root "$staging"
chmod 0400 "$staging"
mv -fT -- "$staging" "$target"
printf 'Corrected key-ID file installed as root:root mode 0400.\n'
