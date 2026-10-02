#!/usr/bin/env bash
set -euo pipefail

readonly target=/etc/stethofuse
readonly destination_names=(
  b2-application-key-id
  b2-application-key-secret
  restic-password
)

if (( EUID != 0 )); then
  printf 'Run this helper with sudo from a local terminal.\n' >&2
  exit 1
fi

if [[ -L "$target" ]]; then
  printf 'Refusing a symlink at %s.\n' "$target" >&2
  exit 1
fi

install -d -o root -g root -m 0700 -- "$target"
chmod 0700 -- "$target"

for name in "${destination_names[@]}"; do
  if [[ -e "$target/$name" || -L "$target/$name" ]]; then
    printf 'Refusing to overwrite existing credential: %s/%s\n' "$target" "$name" >&2
    exit 1
  fi
done

read_secret() {
  local prompt=$1
  local __result=$2
  local value
  IFS= read -r -s -p "$prompt" value </dev/tty
  printf '\n' >/dev/tty
  if [[ -z "$value" ]]; then
    printf 'Empty input is not allowed. Nothing was installed.\n' >&2
    exit 1
  fi
  printf -v "$__result" '%s' "$value"
  unset value
}

read_secret 'B2 application key ID: ' b2_key_id
read_secret 'B2 application key secret: ' b2_key_secret
read_secret 'Restic repository password (from your offline password manager): ' restic_password
read_secret 'Re-enter Restic repository password: ' restic_password_confirmation

if [[ "$restic_password" != "$restic_password_confirmation" ]]; then
  printf 'Restic password entries did not match. Nothing was installed.\n' >&2
  unset b2_key_id b2_key_secret restic_password restic_password_confirmation
  exit 1
fi

if [[ "$b2_key_id" == *[[:space:]]* || "$b2_key_secret" == *[[:space:]]* ]]; then
  printf 'B2 key fields must not contain whitespace. Nothing was installed.\n' >&2
  unset b2_key_id b2_key_secret restic_password restic_password_confirmation
  exit 1
fi

umask 0077
staging=$(mktemp -d "$target/.credential-install.XXXXXXXX")
cleanup() {
  if [[ -n "${staging:-}" && -d "$staging" ]]; then
    rm -f -- "$staging/b2-application-key-id" \
      "$staging/b2-application-key-secret" "$staging/restic-password"
    rmdir -- "$staging" 2>/dev/null || true
  fi
  unset b2_key_id b2_key_secret restic_password restic_password_confirmation
}
trap cleanup EXIT HUP INT TERM

printf '%s\n' "$b2_key_id" >"$staging/b2-application-key-id"
printf '%s\n' "$b2_key_secret" >"$staging/b2-application-key-secret"
printf '%s\n' "$restic_password" >"$staging/restic-password"
unset b2_key_id b2_key_secret restic_password restic_password_confirmation

chown root:root "$staging/b2-application-key-id" \
  "$staging/b2-application-key-secret" "$staging/restic-password"
chmod 0400 "$staging/b2-application-key-id" \
  "$staging/b2-application-key-secret" "$staging/restic-password"

for name in "${destination_names[@]}"; do
  if [[ -e "$target/$name" || -L "$target/$name" ]]; then
    printf 'A destination appeared during setup; refusing overwrite.\n' >&2
    exit 1
  fi
  mv -T --no-clobber "$staging/$name" "$target/$name"
done

printf 'Installed three root-only credential files under %s (mode 0400).\n' "$target"
