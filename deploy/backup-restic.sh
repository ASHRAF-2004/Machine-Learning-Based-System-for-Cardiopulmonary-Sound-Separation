#!/usr/bin/env bash
# Scheduled encrypted StethoFuse backup. Install outside the checkout and run
# only after configuring a real remote restic repository and root-only secrets.
set -Eeuo pipefail
umask 077

fail() { printf 'StethoFuse backup: %s\n' "$1" >&2; exit 1; }

: "${STETHOFUSE_RUNTIME_ROOT:?Set STETHOFUSE_RUNTIME_ROOT}"
: "${STETHOFUSE_RUNTIME_ENV_FILE:?Set STETHOFUSE_RUNTIME_ENV_FILE}"
: "${STETHOFUSE_DEPLOY_DIR:?Set STETHOFUSE_DEPLOY_DIR}"
: "${RESTIC_REPOSITORY:?Set RESTIC_REPOSITORY to the approved remote repository}"
: "${RESTIC_PASSWORD_FILE:?Set RESTIC_PASSWORD_FILE outside the project and runtime}"
: "${RESTIC_CACHE_DIR:=/var/cache/stethofuse-restic}"
: "${AWS_ACCESS_KEY_ID:?Set the bucket-scoped B2 S3 key ID through the service environment}"
: "${AWS_SECRET_ACCESS_KEY:?Set the bucket-scoped B2 S3 secret through the service environment}"

command -v restic >/dev/null 2>&1 || fail 'restic is not installed.'
command -v docker >/dev/null 2>&1 || fail 'Docker is not installed.'
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
password_owner_mode="$(stat -c '%u:%a' -- "$RESTIC_PASSWORD_FILE")"
[[ "$password_owner_mode" == 0:400 || "$password_owner_mode" == 0:600 ]] || \
  fail 'restic password file must be root-owned with mode 0400 or 0600.'

password_path="$(realpath -m -- "$RESTIC_PASSWORD_FILE")"
runtime_path="$(realpath -m -- "$STETHOFUSE_RUNTIME_ROOT")"
project_path="$(realpath -m -- "$STETHOFUSE_DEPLOY_DIR/..")"
case "$password_path" in
  "$runtime_path"/*|"$project_path"/*) fail 'restic password must be stored outside the project and runtime.' ;;
esac

compose=(docker compose
  --project-name stethofuse-production
  --project-directory "$STETHOFUSE_DEPLOY_DIR/.."
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
    rm -f -- "$manifest_file"
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

# Quiesce SQLite and file writes so the database and private media form one
# consistent point-in-time snapshot. The EXIT trap attempts to restore service.
restart_stack=1
"${compose[@]}" stop --timeout 60 web api >/dev/null

unsupported_entry="$(find "$STETHOFUSE_RUNTIME_ROOT/data" "$STETHOFUSE_RUNTIME_ROOT/private" \
  -mindepth 1 ! -type d ! -type f -print -quit)"
[[ -z "$unsupported_entry" ]] || \
  fail 'persistent data contains a non-regular entry; refusing an incomplete backup.'

manifest_file="$(mktemp "${TMPDIR:-/tmp}/stethofuse-backup-manifest.XXXXXX")"
(
  cd -- "$STETHOFUSE_RUNTIME_ROOT"
  find data private -type f -print0 | sort -z | xargs -0 -r sha256sum --
) > "$manifest_file"
sha256sum -- "$STETHOFUSE_RUNTIME_ENV_FILE" >> "$manifest_file"

install -d -o root -g root -m 0700 -- "$RESTIC_CACHE_DIR"
restic --cache-dir "$RESTIC_CACHE_DIR" --password-file "$RESTIC_PASSWORD_FILE" backup \
  --host stethofuse-production \
  --tag stethofuse --tag production \
  "$STETHOFUSE_RUNTIME_ROOT/data" \
  "$STETHOFUSE_RUNTIME_ROOT/private" \
  "$STETHOFUSE_RUNTIME_ENV_FILE" \
  "$manifest_file"
