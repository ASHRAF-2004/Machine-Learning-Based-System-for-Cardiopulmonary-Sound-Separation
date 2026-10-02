# Production ML acceptance addendum — 29 September 2026

**PRODUCTION ML INTEGRATION DEPLOYED / SYNTHETIC END-TO-END ACCEPTANCE PASSED /
ROLE AND PRIVACY ACCEPTANCE PASSED / POST-ACCEPTANCE BACKUP VERIFIED.** This is
the acceptance addendum for the deployed release; the 27 September receipt
remains the historical M1/edge baseline. No model, application code, routing,
Firebase configuration, or Axora service was changed in this acceptance pass.

## Frozen deployment and first-pass evidence

- Deployed implementation SHA: `c96c7cb147833daba88e99596dd71d3f814274e9`.
- Model: `stethofuse-tcn-small-hls-refit-waveform-v2`, Compact Conv-TasNet
  N64/B32/H64, 171,313 parameters; CPU, one durable worker.
- Checkpoint SHA-256:
  `1f7e549ba53240bc085221e4eed1f935bb7c330e9a66cfab4c183c8f096c2658`.
- Specification SHA-256:
  `2573ae06b11aafc595a4cdb179e3ab0c9f7fbe37859863dcd36a5d8c70210b1b`.
- The production files and `SHA256SUMS` matched before and after backup; the
  worker reported `ready` after strict model load. Model files are root-owned
  mode `0440` below `/srv/stethofuse/models`; this path is not mounted into the
  web/API static-media surface. A public `HEAD` to the model-like URL returned
  only the SPA `text/html` fallback, not model bytes.
- Existing synthetic production acceptance remains healthy: recording
  `afa546ff69ad44e3829f9335514ec342`, succeeded job
  `6dc4a754bcb2497ca54c9a5aa366c4d1`, result
  `39b39440436a4e1ba1a34d86796b793d`. Original, Heart, and Lung artifacts are
  distinct private resources. Both outputs are finite 4-kHz mono WAVs of
  60,000 samples; original input hash and persisted provenance were previously
  verified. Repeated Separate reused the same job/result. These checks were
  not rerun unnecessarily.

## SSH identity and initial grant-denial diagnosis

The backup SSH target was `ashraf@axora-server`, resolved locally to
`127.0.1.1:22` on this same physical host. Network-presented ED25519 host-key
fingerprint `SHA256:hIbbjk+nwo69eiGn2kj4pb6Ott98VHsVYlN2GgEhLVs` exactly matched
the fingerprint calculated from the host's own `/etc/ssh/ssh_host_ed25519_key.pub`
through the local trusted shell. Only that exact verified key was added for
`axora-server`; ordinary host-key checking was retained. A normal SSH attempt
passed host verification but could not authenticate the `ashraf` user
(`Permission denied (publickey,password)`). No SSH bypass was used. Since this
shell was already on that host and the approved root-only systemd backup
service was available locally, backup used that service rather than weakening
SSH authentication.

The first grant `403` was a **test/harness ID typo**, not an authorization
defect. The owner (`adoashraf103@gmail.com`, application ID
`fe8bdb54b7bf41f8b8220ff602eabb2c`) submitted a valid read grant scoped to the
acceptance Heart resource, but used recipient ID ending `...45d`; the existing
active, verified Audio Analyst's actual ID ends `...45d4`. The nonexistent
recipient was correctly denied. No grant was created by that attempt, and no
code/security policy change was made.

Using the verified analyst ID and the existing owner UI, one exact-scope
`read` grant was then created:

- recording: `afa546ff69ad44e3829f9335514ec342`;
- Heart resource: `8474305741ba488dbf5069774df41bf3`;
- Lung sibling: `631721b650514e209e41018540ebf271`;
- grant: `1d5d24d9017b4fe8aa50f7ebe9cc0ee5`;
- recipient: `7fc12b955f01462e9206342c6cdc45d4`.

The grant was active only for the Heart resource. The authenticated analyst
opened the recording as an explicit grant and loaded the Heart audio through
the protected media UI. The authorized-resource view contained Heart only; it
did not expose the Lung sibling. The owner then revoked this grant through the
normal UI. The database retains the revoked grant and both `grant.created` and
`grant.revoked` audit events. After a fresh analyst sign-in, opening the same
recording returned the application's permission-denied state. A signed-in
Administrator without a grant received the same denial. Earlier production
acceptance also verified anonymous audio requests return `401`; historical
production evidence covers unrelated/unassigned identities on separate
synthetic fixtures. No credentials or bearer tokens were copied into evidence.

## Backup, restore verification, and recovery

The installed encrypted Restic/B2 service was run once after privacy checks.
It stopped StethoFuse web, API, and the one ML worker together; queued work
remained in the database and no job was processing. The backup exited `0` after
restarting web/API healthy and the worker reported `ready` again. No Axora
service was included in the stop set.

- Remote snapshot:
  `e133d7db3c3db4758db266135674c45515746462bb30ef37eed7fa3865a75e1b`.
- Snapshot time: `2026-09-29T17:52:19.817691859+08:00`.
- Restic reported 16 files and 3.796 MiB processed; remote listing contains
  `/srv/stethofuse/data`, `/srv/stethofuse/private`, and
  `/srv/stethofuse/models`, including the SQLite DB, synthetic acceptance
  Heart/Lung WAVs, `endpoint.pt`, `final_separator_v2.json`, and `SHA256SUMS`.
- A safe isolated restore of the model bundle passed the bundled SHA-256 checks
  for both checkpoint and spec. A second isolated restore passed the existing
  manifest verifier: manifest hash, exact data/private file sets, byte
  comparisons, and SQLite `integrity_check=ok`. Both temporary restore trees
  were removed after verification. Retention pruning remains disabled.
- Worker quiescence is enabled in the existing backup environment
  (`STETHOFUSE_ML_WORKER_ENABLED=1`); it stopped web/API/worker as one consistent
  set and confirmed services resumed. The backup timer remains active.

## Final health and scope

After backup, public StethoFuse `/health` returned `200`; the API and web
containers were `running healthy`, the ML worker was running with a fresh
`ready` log entry, SQLite passed integrity, and the acceptance job remained
succeeded. Axora app and Caddy containers remained `running healthy` and were
not touched. The deployment receipt identifies Axora's public hostname as
`axora.management`; its public root returned `200`. An earlier probe used an
incorrect assumed hostname/path and was not used as Axora health evidence.

No patient or T9 audio was used. No model training/tuning, T9 rerun, model
replacement, deployment restart for code, frontend/owl change, Firebase/Caddy/
Cloudflare change, or Axora modification occurred. Physical stethoscope
qualification and clinical validation remain unclaimed.
