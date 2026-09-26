#!/usr/bin/env bash
# Owner-approved B2 initialization or a synthetic-only remote restore drill.
# Run through the credential-loading systemd command in BACKUP_B2_RUNBOOK.md.
set -Eeuo pipefail
umask 077

fail() { printf 'StethoFuse restore drill: %s\n' "$1" >&2; exit 1; }
[[ "$EUID" == 0 ]] || fail 'Run through the documented root-owned systemd unit.'
action="${1:-drill}"
[[ "$action" == init || "$action" == drill ]] || fail 'Expected init or drill.'
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
: "${RESTIC_REPOSITORY:?Set the approved B2 S3 repository}"
: "${CREDENTIALS_DIRECTORY:?systemd credentials are required}"
[[ "$RESTIC_REPOSITORY" =~ ^s3:s3\.[a-z0-9-]+\.backblazeb2\.com/[a-z0-9.-]+(/[a-zA-Z0-9/_-]+)?$ ]] || \
  fail 'Expected the approved B2 S3 endpoint/bucket.'
for credential in restic-password b2-application-key-id b2-application-key-secret; do
  file="$CREDENTIALS_DIRECTORY/$credential"
  [[ -f "$file" && -s "$file" && ! -L "$file" ]] || fail 'Missing private systemd credential.'
  mode="$(stat -c '%u:%a' -- "$file")"
  [[ "$mode" == 0:400 || "$mode" == 0:600 ]] || fail 'Credential must be root-owned, mode 0400/0600.'
done
command -v restic >/dev/null || fail 'Restic is not installed.'
command -v python3 >/dev/null || fail 'Python 3 is not installed.'

restic_call() {
  # Values are inherited only by this child, never placed in arguments or output.
  AWS_ACCESS_KEY_ID="$(<"$CREDENTIALS_DIRECTORY/b2-application-key-id")" \
  AWS_SECRET_ACCESS_KEY="$(<"$CREDENTIALS_DIRECTORY/b2-application-key-secret")" \
    restic --no-cache --password-file "$CREDENTIALS_DIRECTORY/restic-password" "$@"
}

if [[ "$action" == init ]]; then
  # Explicit action only; Restic refuses an already initialized repository.
  restic_call init
  exit
fi

drill_root="$(mktemp -d /var/tmp/stethofuse-restore-drill.XXXXXX)"
source_root="$drill_root/source"
python3 - "$source_root" <<'PY'
import pathlib, sqlite3, sys, wave
root = pathlib.Path(sys.argv[1])
(root / 'data').mkdir(parents=True, mode=0o700)
(root / 'private').mkdir(mode=0o700)
with sqlite3.connect(root / 'data/m1.sqlite3') as db:
    db.execute('CREATE TABLE fixture (value TEXT NOT NULL)')
    db.execute("INSERT INTO fixture VALUES ('synthetic restore drill only')")
with wave.open(str(root / 'private/synthetic.wav'), 'wb') as audio:
    audio.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
    audio.writeframes(b'\0\0' * 80)
(root / 'runtime.env').write_text('STETHOFUSE_TEST_FIXTURE=synthetic-only\n')
PY
python3 "$script_dir/backup-manifest.py" create \
  --data-root "$source_root/data" --private-root "$source_root/private" \
  --runtime-env "$source_root/runtime.env" > "$source_root/SHA256.json"

restic_call backup --json --host stethofuse-restore-drill \
  --tag stethofuse-restore-drill "$source_root" > "$drill_root/backup.jsonl"
snapshot_id="$(python3 - "$drill_root/backup.jsonl" <<'PY'
import json, pathlib, re, sys
summaries = [entry for line in pathlib.Path(sys.argv[1]).read_text().splitlines()
             if (entry := json.loads(line)).get('message_type') == 'summary']
if len(summaries) != 1 or not re.fullmatch('[0-9a-f]{8,64}', summaries[0].get('snapshot_id', '')):
    raise SystemExit('No unambiguous successful snapshot ID.')
print(summaries[0]['snapshot_id'])
PY
)"
restic_call check
restic_call restore "$snapshot_id" --target "$drill_root/restored"
restored_root="$drill_root/restored$source_root"
python3 "$script_dir/backup-manifest.py" verify-restore \
  --manifest "$restored_root/SHA256.json" \
  --source-data "$source_root/data" --source-private "$source_root/private" \
  --source-env "$source_root/runtime.env" \
  --restored-data "$restored_root/data" --restored-private "$restored_root/private" \
  --restored-env "$restored_root/runtime.env"
restic version
printf 'Verified synthetic B2 snapshot: %s\nEvidence/staging retained at: %s\n' "$snapshot_id" "$drill_root"
# No prune, timer enablement, or restore-verification marker is created here.
