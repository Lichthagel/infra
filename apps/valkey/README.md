# Shared Valkey

Valkey persists AOF files under `/data` on the existing 1Gi PVC, with
`appendfsync everysec`. A crash can normally lose about one second of writes;
AOF is not a backup. Snapshot defaults are unchanged.

The Deployment uses `Recreate` to prevent overlapping processes from writing
to the same volume. Updates briefly interrupt every consumer. A startup probe
allows up to ten minutes for persistence replay before liveness checks begin.

## Enabling AOF On An Existing Instance

Do this before syncing the changed Valkey Application through ArgoCD. Simply
restarting a snapshot-only instance with AOF enabled can lose existing data;
enable it on the running process first so it creates an AOF from the live dataset.

1. Back up the existing dataset and confirm sufficient free space on `/data`
   for AOF creation and rewrites. Avoid restarting the pod during conversion.
2. Enable AOF on the running instance (these commands assume the sumireko
   kubeconfig context is named `sumireko`):

   ```bash
   kubectl --context sumireko -n valkey exec deployment/valkey -- valkey-cli CONFIG SET appendfsync everysec
   kubectl --context sumireko -n valkey exec deployment/valkey -- valkey-cli CONFIG SET appendonly yes
   kubectl --context sumireko -n valkey exec deployment/valkey -- valkey-cli INFO persistence
   ```

3. Recheck `INFO persistence` until `aof_enabled:1`,
   `aof_rewrite_in_progress:0`, `aof_rewrite_scheduled:0`,
   `aof_last_bgrewrite_status:ok`, and `aof_last_write_status:ok`.
   If conversion fails, fix the cause and complete it before restarting.
4. Sync the Valkey Application through ArgoCD. The Deployment arguments keep
   AOF enabled across restarts; no `CONFIG REWRITE` is needed.
5. Verify `CONFIG GET appendonly`, `CONFIG GET appendfsync`, and
   `INFO persistence` after the rollout, and check consumer connectivity.

For a fresh empty instance, no live conversion is needed.

## Capacity

Every logical database shares the 512Mi container memory limit and 1Gi PVC.
Monitor both, especially after adding Floppy. AOF rewrites need extra disk
space and can increase memory usage through copy-on-write. This change does
not increase resource limits or change eviction policy. Do not apply a
cache-oriented eviction policy blindly: evicting broker keys can lose queued
work. Back up persistent data separately and test restoration.
