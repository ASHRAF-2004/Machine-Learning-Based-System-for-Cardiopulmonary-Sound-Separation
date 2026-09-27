#!/usr/bin/env bash
# Scheduled encrypted StethoFuse backup. Install outside the checkout and run
# only after configuring a real remote restic repository and root-only secrets.
set -Eeuo pipefail
umask 077

fail() { printf 'StethoFuse backup: %s\n' "$1" >&2; exit 1; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

: "${STETHOFUSE_RUNTIME_ROOT:?Set STETHOFUSE_RUNTIME_ROOT}"
: "${STETHOFUSE_RUNTIME_ENV_FILE:?Set STETHOFUSE_RUNTIME_ENV_FILE}"
: "${STETHOFUSE_DEPLOY_DIR:?Set STETHOFUSE_DEPLOY_DIR}"
: "${RESTIC_REPOSITORY:?Set RESTIC_REPOSITORY to the approved remote repository}"
: "${RESTIC_PASSWORD_FILE:?Set RESTIC_PASSWORD_FILE outside the project and runtime}"
: "${RESTIC_CACHE_DIR:=/var/cache/stethofuse-restic}"
: "${STETHOFUSE_B2_ACCESS_KEY_ID_FILE:?Set the systemd B2 key-ID credential path}"
: "${STETHOFUSE_B2_SECRET_ACCESS_KEY_FILE:?Set the systemd B2 secret credential path}"

command -v restic >/dev/null 2>&1 || fail 'restic is not installed.'
command -v docker >/dev/null 2>&1 || fail 'Docker is not installed.'
command -v python3 >/dev/null 2>&1 || fail 'Python 3 is not installed.'
[[ -f "$script_dir/backup-manifest.py" && ! -L "$script_dir/backup-manifest.py" ]] || \
  fail 'The installed SHA-256 manifest helper is missing or a symlink.'
[[ "$RESTIC_REPOSITORY" == s3:s3.*.backblazeb2.com/* ]] || \
  fail 'This prepared profile accepts only the approved remote B2 S3 endpoint.'
[[ -d "$STETHOFUSE_RUNTIME_ROOT/data" && ! -L "$STETHOFUSE_RUNTIME_ROOT/data" ]] || \
  fail 'runtime data directory is missing or a symlink.'
[[ -d "$STETHOFUSE_RUNTIME_ROOT/private" && ! -L "$STETHOFUSE_RUNTIME_ROOT/private" ]] || \
  fail 'private storage directory is missing or a symlink.'
[[ -f "$STETHOFUSE_RUNTIME_ENV_FILE" && ! -L "$STETHOFUSE_RUNTIME_ENV_FILE" ]] || \
  fail 'runtime environment file is missing or a symlink.'
[[ -f "$RESTIC_PASSWORD_FILE" && -s "$RESTIC_PASSWORD_FILE" && ! -L "$RESTIC_PASSWORD_FILE" ]] || \
  fail 'restic password file is missing, empty, or a symlink.'
[[ -f "$STETHOFUSE_B2_ACCESS_KEY_ID_FILE" && -s "$STETHOFUSE_B2_ACCESS_KEY_ID_FILE" && ! -L "$STETHOFUSE_B2_ACCESS_KEY_ID_FILE" ]] || \
  fail 'B2 key-ID credential is missing or invalid.'
[[ -f "$STETHOFUSE_B2_SECRET_ACCESS_KEY_FILE" && -s "$STETHOFUSE_B2_SECRET_ACCESS_KEY_FILE" && ! -L "$STETHOFUSE_B2_SECRET_ACCESS_KEY_FILE" ]] || \
  fail 'B2 secret credential is missing or invalid.'
password_owner_mode="$(stat -c '%u:%a' -- "$RESTIC_PASSWORD_FILE")"
[[ "$password_owner_mode" == 0:400 || "$password_owner_mode" == 0:600 ]] || \
  fail 'restic password file must be root-owned with mode 0400 or 0600.'

runtime_path="$(realpath -m -- "$STETHOFUSE_RUNTIME_ROOT")"
project_path="$(realpath -m -- "$STETHOFUSE_DEPLOY_DIR/..")"
for credential in "$RESTIC_PASSWORD_FILE" "$STETHOFUSE_B2_ACCESS_KEY_ID_FILE" "$STETHOFUSE_B2_SECRET_ACCESS_KEY_FILE"; do
  credential_mode="$(stat -c '%u:%a' -- "$credential")"
  [[ "$credential_mode" == 0:400 || "$credential_mode" == 0:600 ]] || \
    fail 'Backup credentials must be root-owned with mode 0400 or 0600.'
  credential_path="$(realpath -m -- "$credential")"
  case "$credential_path" in
    "$runtime_path"/*|"$project_path"/*) fail 'Backup credentials must be outside the project and runtime.' ;;
  esac
done

compose=(docker compose
  --project-name stethofuse-production
  --project-directory "$STETHOFUSE_DEPLOY_DIR"
  --env-file "$STETHOFUSE_RUNTIME_ENV_FILE"
  -f "$STETHOFUSE_DEPLOY_DIR/compose.yaml"
  -f "$STETHOFUSE_DEPLOY_DIR/compose.firebase.yaml")

require_one_healthy_container() {
  local service="$1"
  local -a container_ids=()
  local state
  mapfile -t container_ids < <("${compose[@]}" ps -q "$service")
  [[ "${#container_ids[@]}" == 1 ]] || \
    fail "$service must have exactly one container; refusing an ambiguous maintenance transition."
  state="$(docker inspect --type container \
    --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    "${container_ids[0]}")"
  [[ "$state" == 'running healthy' ]] || \
    fail "$service must be running and healthy before backup."
}
require_one_healthy_container api
require_one_healthy_container web

restart_stack=0
manifest_file=""
restore_stack() {
  result=$?
  trap - EXIT
  if [[ -n "$manifest_file" ]]; then
    if ! rm -f -- "$manifest_file"; then
      printf 'StethoFuse backup: temporary manifest cleanup failed.\n' >&2
      result=1
    fi
  fi
  if [[ "$restart_stack" == 1 ]]; then
    if ! "${compose[@]}" up -d web api >/dev/null; then
      printf 'StethoFuse backup: restart failed; operator intervention is required.\n' >&2
      result=1
    fi
  fi
  exit "$result"
}
trap restore_stack EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# Quiesce SQLite and file writes so the database and private media form one
# consistent point-in-time snapshot. The EXIT trap attempts to restore service.
restart_stack=1
"${compose[@]}" stop --timeout 60 web api >/dev/null

unsupported_entry="$(find "$STETHOFUSE_RUNTIME_ROOT/data" "$STETHOFUSE_RUNTIME_ROOT/private" \
  -mindepth 1 ! -type d ! -type f -print -quit)"
[[ -z "$unsupported_entry" ]] || \
  fail 'persistent data contains a non-regular entry; refusing an incomplete backup.'

manifest_file="$(mktemp "${TMPDIR:-/tmp}/stethofuse-backup-manifest.XXXXXX")"
python3 "$script_dir/backup-manifest.py" create \
  --data-root "$STETHOFUSE_RUNTIME_ROOT/data" \
  --private-root "$STETHOFUSE_RUNTIME_ROOT/private" \
  --runtime-env "$STETHOFUSE_RUNTIME_ENV_FILE" > "$manifest_file"

install -d -o root -g root -m 0700 -- "$RESTIC_CACHE_DIR"
restic_call() {
  local b2_key_id b2_secret
  b2_key_id="$(<"$STETHOFUSE_B2_ACCESS_KEY_ID_FILE")"
  b2_secret="$(<"$STETHOFUSE_B2_SECRET_ACCESS_KEY_FILE")"
  [[ -n "$b2_key_id" && -n "$b2_secret" ]] || fail 'B2 credentials are empty.'
  AWS_ACCESS_KEY_ID="$b2_key_id" AWS_SECRET_ACCESS_KEY="$b2_secret" \
    restic --cache-dir "$RESTIC_CACHE_DIR" --password-file "$RESTIC_PASSWORD_FILE" "$@"
  unset b2_key_id b2_secret
}

restic_call backup \
  --host stethofuse-production \
  --tag stethofuse --tag production \
  "$STETHOFUSE_RUNTIME_ROOT/data" \
  "$STETHOFUSE_RUNTIME_ROOT/private" \
  "$STETHOFUSE_RUNTIME_ENV_FILE" \
  "$manifest_file"

# The first verified restore is a hard gate before any pruning is enabled.
restore_marker="/etc/stethofuse/remote-restore-verified"
if [[ -f "$restore_marker" && ! -L "$restore_marker" ]]; then
  marker_owner_mode="$(stat -c '%u:%a' -- "$restore_marker")"
  [[ "$marker_owner_mode" == 0:400 || "$marker_owner_mode" == 0:600 ]] || \
    fail 'restore verification marker must be root-owned with mode 0400 or 0600.'
  restic_call forget --host stethofuse-production --tag stethofuse --group-by host,tags \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
else
  printf 'StethoFuse backup: retention pruning skipped until a verified restore is recorded.\n'
fi
