# StethoFuse encrypted off-host backup runbook

## Decision and state

Backblaze B2 through its S3-compatible endpoint plus Restic is the approved
backup design. Backblaze's official Restic guide uses this S3-compatible route.
Restic encrypts/authenticates repository data client-side. There is no configured
off-host target today: no B2 account, bucket, app key, Restic repository, snapshot,
or restore proof exists. `/srv` and `/var/backups` are on the same host disk and
do not satisfy off-host recovery.

The proposed account region is **EU Central**. Backblaze currently has US East,
US West, EU Central and Canada East, not Asia; account region is selected at
account creation and cannot be changed for that account. EU Central is the
prepared location for this FYP project, not a legal/data-residency determination.
Review it if formal residency obligations are later introduced.

## Owner's Backblaze account action

Use a normal external browser at <https://secure.backblaze.com/b2_buckets.htm>.
Sign in or create the owner's Backblaze account personally. Before creating the
account, choose **EU Central (Amsterdam)** and confirm the region; it cannot be
changed later. No paid reserve/commitment is part of this plan; the service is
usage-based, but actual storage, transaction and restore/egress costs must be
checked in the account before use.

In the B2 console:

1. Create a **private** bucket named `stethofuse-prod-backup-927f5b7d` if available.
   If taken, append a random non-personal suffix. Do not enable public access,
   Object Lock, lifecycle deletion or replication for this initial setup.
2. Record the bucket name, region and exact S3 endpoint only. The EU Central
   endpoint code is shown in the bucket details; use that displayed value rather
   than guessing it.
3. Create an application key named `stethofuse-restic-prod`, restricted to that
   one bucket: `listFiles`, `readFiles`, `writeFiles`, `deleteFiles`, plus
   `listBuckets` (S3 Head Bucket) and `readBuckets` (S3 bucket location). The last
   two are read-only bucket metadata used by the S3 client, not bucket creation.
   Delete is needed for Restic locks and reviewed retention. No `writeKeys`,
   `deleteKeys`, `writeBuckets`, `deleteBuckets` or master-key access. Record the
   actually granted capabilities before use. The direct Restic backend names
   the bucket and does not call List Buckets; do not add account-wide
   `listAllBucketNames` merely for a generic S3 browser. Backblaze recommends
   that compatibility permission for clients that enumerate buckets; if a
   selected client/version requires it, stop that operation and review first.
4. B2 displays the application key secret once. Do not paste either key field in
   chat, a ticket, terminal output, `.env`, or Git. Save it temporarily only in
   the owner's approved password manager/secure handoff. Report back only the
   bucket name, selected region, endpoint host, and completion; the key must be
   installed on the server through the separately reviewed root-only credential
   procedure.

The bucket name is a proposal and has not been availability-checked. The app key
is not a Restic encryption password. If the account console requires card/billing
setup, review its terms and expected usage before enabling a paid commitment.

## Server credential placement

Install Restic from the server's approved package source and record its version.
Copy the prepared helper, manifest verifier and systemd examples into their
final root-owned locations only after production installation is approved:

- `/usr/local/libexec/stethofuse/backup-restic.sh`
- `/usr/local/libexec/stethofuse/backup-manifest.py`
- `/usr/local/libexec/stethofuse/backup-restore-drill.sh`
- `/etc/stethofuse/backup.env` (root:root, `0600`, placeholders replaced)
- `/etc/stethofuse/runtime.env` (existing app runtime file, root-only)
- `/etc/stethofuse/b2-application-key-id` (root:root, `0400`)
- `/etc/stethofuse/b2-application-key-secret` (root:root, `0400`)
- `/etc/stethofuse/restic-password` (root:root, `0400`)

Create a high-entropy Restic repository password using the owner's password
manager and preserve it in an offline recovery vault independent of this server
and B2 account. Securely enter it into the root-owned file without command-line
arguments or shell echo. Losing that password makes the encrypted repository
unrecoverable; B2 key recovery cannot replace it. Conversely, rotate/revoke the
B2 app key without changing the repository password if the cloud credential is
exposed.

The systemd unit loads all three files as private credentials. Inside the unit,
the helper passes B2 values only in the Restic child process environment; it does
not export them into the service environment or log values. The bucket endpoint
and repository path belong in `/etc/stethofuse/backup.env`, never credentials.
Keep `.env.example` and `backup.env.example` placeholder-only.

## Repository initialization and scheduled snapshots

After the endpoint and root-only files have been installed, verify the repository
target is exactly the new B2 S3 endpoint and bucket. Initialize the Restic
repository exactly once with the `init` command below. Do not place secrets in an
interactive shell or in the `systemd-run` command line. Record the
Restic version, bucket endpoint host and repository identifier, never key or
password values.

The repository value in `backup.env` is
`s3:s3.<region-code>.backblazeb2.com/<private-bucket>/restic`; replace both
placeholders using the console's actual endpoint and bucket. No HTTPS credentials
belong in this value. The S3 backend uses HTTPS by default.

After owner-approved installation, from the reviewed implementation checkout:

```sh
sudo install -d -o root -g root -m 0755 /usr/local/libexec/stethofuse
sudo install -o root -g root -m 0755 deploy/backup-restic.sh deploy/backup-manifest.py \
  deploy/backup-restore-drill.sh /usr/local/libexec/stethofuse/

stethofuse_drill() {
  sudo systemd-run --unit=stethofuse-backup-drill --wait --collect --pipe \
    --property=User=root --property=Group=root --property=UMask=0077 \
    --property=EnvironmentFile=/etc/stethofuse/backup.env \
    --property=LoadCredential=restic-password:/etc/stethofuse/restic-password \
    --property=LoadCredential=b2-application-key-id:/etc/stethofuse/b2-application-key-id \
    --property=LoadCredential=b2-application-key-secret:/etc/stethofuse/b2-application-key-secret \
    /usr/local/libexec/stethofuse/backup-restore-drill.sh "$1"
}
stethofuse_drill init   # Exactly once, for the confirmed new empty repository.
stethofuse_drill drill  # Synthetic fixture only; no application DB or service touched.
```

The drill creates a private temporary tree, a synthetic SQLite database and a
0.01-second silent WAV, uploads an encrypted snapshot, checks the repository,
restores that exact snapshot into a separate tree, and validates SQLite integrity,
SHA-256 hashes, exact file sets and byte equality. It prints the snapshot ID and
retained evidence directory; it never prints credentials. Run it again after
independently recovering the password from the owner's offline escrow. It does
not enable pruning or change the production application. The script is prepared;
no real B2 execution has occurred.

The prepared `backup-restic.sh` requires exactly one healthy API and web
container, stops both to quiesce SQLite/media, hashes the database/private files
and runtime env in bounded-memory chunks, uploads an encrypted snapshot, and
restarts services on success or failure. It excludes images, build caches,
node_modules, model caches and credentials. Review the first snapshot before
enabling the timer.

Retention is 7 daily, 4 weekly and 6 monthly snapshots. The helper does not run
`forget --prune` until the root-owned `0400` marker
`/etc/stethofuse/remote-restore-verified` exists. Do not create the marker until
the restore procedure below has passed and the evidence has been recorded.
Retention groups by host and tags, not by the unique temporary manifest path.
The synthetic drill uses a different host/tag and is excluded from production
retention. Keep its snapshot until evidence review.

After a successful drill and approved production installation, install the
service/timer examples and enable the timer. Only then create the marker:

```sh
sudo install -o root -g root -m 0400 /dev/null /etc/stethofuse/remote-restore-verified
sudo install -o root -g root -m 0644 deploy/stethofuse-backup.service.example \
  /etc/systemd/system/stethofuse-backup.service
sudo install -o root -g root -m 0644 deploy/stethofuse-backup.timer.example \
  /etc/systemd/system/stethofuse-backup.timer
sudo systemctl daemon-reload
sudo systemctl start stethofuse-backup.service
sudo systemctl enable --now stethofuse-backup.timer
```

Pruning may leave B2's historical object versions subject to the bucket's version
policy. Inspect usage after retention; do not introduce independent lifecycle
deletion that could invalidate Restic snapshots. Monitor backup exit status and
storage charges. Disable only this timer to pause scheduled backups; revoke the
bucket key in B2 to cut remote access. Never delete the repository during rollback.

## Mandatory encrypted remote restore drill

The executable synthetic drill above is the deployment prerequisite. The manual
paths below are for later production snapshot drills against an unchanged or
quiesced source; do not compare hashes against a database that is being written.

Use the root-only systemd credential mechanism to list snapshots and restore one
synthetic-only snapshot to a new empty staging directory, for example
`/var/tmp/stethofuse-restore-<unique-run-id>`. Never restore over `/srv/stethofuse`
or an active database. Restic preserves source paths under the target root. Find
the single `tmp/stethofuse-backup-manifest.*` included in that snapshot, then run
the installed manifest helper with:

```sh
python3 /usr/local/libexec/stethofuse/backup-manifest.py verify-restore \
  --manifest "$RESTORED_MANIFEST" \
  --source-data /srv/stethofuse/data \
  --source-private /srv/stethofuse/private \
  --source-env /etc/stethofuse/runtime.env \
  --restored-data "$RESTORE_ROOT/srv/stethofuse/data" \
  --restored-private "$RESTORE_ROOT/srv/stethofuse/private" \
  --restored-env "$RESTORE_ROOT/etc/stethofuse/runtime.env"
```

Supply `RESTORE_ROOT` and `RESTORED_MANIFEST` only in the transient local
operator environment; they are paths, not credentials. The helper checks exact
data/private file sets, each SHA-256, byte-for-byte file equality and SQLite
`PRAGMA integrity_check=ok`. Test the restored application only against staged
synthetic data and the matching image; never expose it publicly. Record snapshot
ID/time, Restic version, test command/result, SQLite status and synthetic
checksum comparison in the FYP2 evidence ledger without storing audio contents
or credentials. Remove the isolated staging copy only after its evidence is
reviewed. Then, and only then, install the root-owned prune marker and enable the
timer.

The repository password must also be tested from the separate offline escrow.
An untested password escrow is not a verified recovery plan. Periodically run
`restic check` and perform a full isolated restore at least quarterly.

## References

- [Backblaze's Restic/S3-compatible integration guide](https://www.backblaze.com/docs/cloud-storage-integrate-restic-with-backblaze-b2)
- [Backblaze regions and region selection](https://www.backblaze.com/docs/cloud-storage-data-regions)
- [Backblaze application-key capabilities](https://www.backblaze.com/docs/cloud-storage-application-key-capabilities)
- [Backblaze S3-compatible endpoints](https://www.backblaze.com/docs/en/cloud-storage-call-the-s3-compatible-api)
- [S3 key capabilities and metadata permissions](https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys)
- [Restic S3 backend implementation](https://github.com/restic/restic/blob/master/internal/backend/s3/s3.go)
