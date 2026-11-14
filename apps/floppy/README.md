# Floppy

Deployed by ArgoCD on sumireko at https://floppy.licht.moe.

## Prerequisites

- Point `floppy.licht.moe` at sumireko's Traefik ingress.
- Provision a PostgreSQL role `floppy` and database `floppy` owned by that role
  on `postgres.postgres.svc.cluster.local:5432`. The role must be able to run
  migrations in its database; do not use the PostgreSQL administrator account.
- Provision these Secrets in namespace `floppy` through the existing secret
  management process (no credentials are committed here):

| Secret | Key | Value |
| --- | --- | --- |
| `floppy-secret` | `signing-key` | A stable random Django signing key |
| `floppy-postgres` | `password` | The PostgreSQL role's password |

Secrets are mounted as files. Preserve the signing key with database backups;
changing it makes saved integration credentials unreadable. Restart the
Deployment after changing a Secret so all processes reload it.

## Shared Valkey

Floppy uses `valkey.valkey.svc.cluster.local:6379/1`, with the `floppy:` prefix.
Database 1 is reserved for Floppy by this configuration; confirm it is unused
by any consumers managed outside this repo before syncing. This is keyspace
separation, not an access-control or resource-isolation boundary.

`FLOPPY_REDIS_MAXMEMORY=0` prevents Floppy from changing server-wide Valkey
settings. The shared Valkey deployment enables AOF on its persistent `/data`
volume with `appendfsync everysec`, normally limiting crash-related loss to
about one second of writes. This is not a backup or an exactly-once task
execution guarantee. Follow the [Valkey migration instructions](../valkey/README.md)
before syncing the persistence change on an existing instance.

All consumers still share Valkey's 512Mi container memory limit and 1Gi PVC.
Monitor memory and disk usage, including AOF rewrite overhead; database numbers
do not isolate resources. Memory limits, eviction policy, and persistence remain
the shared Valkey operator's responsibility.

## First Start

Sync the Application through ArgoCD after provisioning the prerequisites.
The image runs migrations before starting the web server and background workers;
the startup probe allows up to ten minutes for this.

Public registration and the demo account are disabled. Create the first account
interactively after startup:

```bash
kubectl --context sumireko -n floppy exec -it deployment/floppy -- python manage.py createsuperuser
```

Check database, migrations, and Valkey connectivity:

```bash
kubectl --context sumireko -n floppy exec deployment/floppy -- python manage.py floppy_preflight
```

Metadata-provider credentials can be configured in Floppy's settings as needed.

## Storage And Backups

The 2Gi PVC persists logs and scheduled CSV exports under `/floppy/db`, with
exports in `/floppy/db/backups`. It does not hold the PostgreSQL database.
CSV exports are not complete backups: back up PostgreSQL separately, preserve
the signing key, and keep encrypted off-host copies. Monitor PVC usage.

After restoring PostgreSQL, run migrations if needed, then invalidate reliable
sync contexts before reopening access to clients:

```bash
kubectl --context sumireko -n floppy exec deployment/floppy -- python manage.py invalidate_sync_contexts --all-users
```
