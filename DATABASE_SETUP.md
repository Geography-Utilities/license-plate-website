**Created partially using GenAI**

# Database Setup — Production

This document covers how to set up PostgreSQL for this project on a fresh
production host, plus the specific issues we hit (and fixed) getting
migrations running reliably. Read the **Common Issues** section before
opening a support thread — it covers everything we've actually run into.

---

## 1. Install PostgreSQL

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

This installs and starts the `postgresql` systemd service automatically.

## 2. Create the database and application role

Connect as the Postgres superuser:

```bash
sudo -u postgres psql
```

Then run:

```sql
CREATE DATABASE plates_db;
CREATE USER plates_app WITH PASSWORD 'use-a-long-random-string';
GRANT ALL PRIVILEGES ON DATABASE plates_db TO plates_app;
```

### Schema permissions (Postgres 15+)

Postgres 15 changed the default so that **only the database owner** has
`CREATE` rights on the `public` schema — a non-owner role like `plates_app`
cannot create tables until you grant it explicitly. Without this step,
migrations fail with `permission denied for schema public`.

```sql
\c plates_db

GRANT CREATE ON SCHEMA public TO plates_app;
GRANT USAGE ON SCHEMA public TO plates_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO plates_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO plates_app;
```

The `SEQUENCES` grant matters because auto-incrementing primary keys are
backed by Postgres sequences — without it, inserts can fail even after
table creation succeeds.

**Simpler alternative:** since `plates_db` is a single-app database with no
other tenants, you can just make `plates_app` the owner instead of managing
schema grants separately:

```sql
ALTER DATABASE plates_db OWNER TO plates_app;
```

### Network exposure

By default Postgres only listens on `localhost` and only accepts local
connections (`pg_hba.conf`). **Leave it this way** as long as the app and
database are on the same host — do not open port 5432 externally. If a
future multi-node deployment requires Postgres to be reachable from other
hosts, that requires deliberate `listen_addresses` / `pg_hba.conf` /
firewall changes plus `sslmode=require` on connections — not the default
setup.

## 3. Install Redis for rate limiting

Install Debian's Redis server package and enable the service:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable --now redis-server
```

Keep Redis private because it contains rate-limit state and must not be
reachable from the public internet. Edit `/etc/redis/redis.conf` and verify
these settings:

```conf
bind 127.0.0.1 ::1
protected-mode yes
```

For an additional authentication boundary, set a long random password in the
same file:

```conf
requirepass <long-random-redis-password>
```

Restart Redis and verify it locally. `redis-cli --askpass` prompts without
putting the password in the shell command history:

```bash
sudo systemctl restart redis-server
redis-cli --askpass ping
```

The expected response is `PONG`. Do not open port 6379 in the firewall or
configure Redis to bind to a public interface. Redis persistence and backups
are not required for rate-limit correctness; losing Redis state only resets
the current counters.

## 4. Application dependencies

```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate psycopg2-binary python-dotenv
```

## 5. Environment configuration

Production environment variables live in:

```
/etc/licenseplates/.env
```

Required variables:

```
FLASK_ENV=production
DATABASE_URL=postgresql://plates_app:<real-password>@localhost:5432/plates_db
RATELIMIT_STORAGE_URI=redis://localhost:6379/0
```

`RATELIMIT_STORAGE_URI` must point to shared Redis storage in production so
rate limits apply consistently across all Gunicorn workers and hosts.
If Redis authentication is enabled, use the password in the URI and URL-encode
any special characters:

```
RATELIMIT_STORAGE_URI=redis://:<redis-password>@localhost:6379/0
```

Do **not** wrap values in quotes in this file, and do not use a literal
placeholder like `{password}` — the app does not perform any substitution
on this file. Put the actual password directly in the string.

If the actual password contains special characters (`@ : / # % ?`), it
must be URL-encoded, or the connection string will be parsed incorrectly:

```bash
python3 -c "import urllib.parse; print(urllib.parse.quote('your-password', safe=''))"
```

### systemd service

The gunicorn service loads this file via `EnvironmentFile`:

```ini
[Service]
EnvironmentFile=/etc/licenseplates/.env
...
```

After changing the `.env` file or the unit file itself:

```bash
sudo systemctl daemon-reload
sudo systemctl restart plates-gunicorn
```

## 6. Running `flask db` commands manually (SSH)

`EnvironmentFile=` only applies to the systemd-managed gunicorn process —
it does **not** carry over to an interactive SSH shell. Running `flask db
migrate` by hand without loading the same environment will silently fall
back to `DevelopmentConfig` (see Common Issues below) and fail or hit the
wrong database.

Before running any `flask db ...` command by hand, load the production
environment into your shell:

```bash
set -a
source /etc/licenseplates/.env
set +a
```

`set -a` ensures every variable sourced from the file is actually
**exported** (visible to child processes like `flask`), not just set as a
shell-local variable. Plain `source .env` without `set -a` looks like it
worked (`echo $FLASK_ENV` shows the right value) but `flask` itself won't
see it — this was the root cause of the first migration failure we hit.

Also confirm there's no stray `.env` file inside the project directory
itself (`/home/server/license_plates_site/.env`) left over from local
testing — Flask's CLI auto-loads a `.env` from the current working
directory, which can silently override the intended
`/etc/licenseplates/.env` values if one exists.

## 7. First-time migration setup

```bash
set -a
source /etc/licenseplates/.env
set +a

flask db init          # only if migrations/ doesn't exist yet
flask db migrate -m "initial database table migration"
flask db upgrade
```

If `flask db migrate` reports `Error: Target database is not up to date`,
it means a migration file exists that hasn't been applied yet. Run:

```bash
flask db current   # shows what the DB thinks its current revision is
flask db heads      # shows the latest revision in migrations/versions/
flask db upgrade    # applies the pending migration
```

## 8. Routine deploys

Migrations should run as part of the deploy process, not as a manual
afterthought — this avoids the export/environment mismatch entirely and
ensures migrations always run before gunicorn restarts (so no request
hits new code against an old schema).

```bash
#!/bin/bash
set -e
cd /home/server/license_plates_site
source .venv/bin/activate

set -a
source /etc/licenseplates/.env
set +a

pg_dump -U plates_app -h localhost -F c plates_db \
  -f /var/backups/postgres/pre_migrate_$(date +%F_%H%M).dump

git pull
flask db upgrade
sudo systemctl restart plates-gunicorn
```

`set -e` at the top ensures the script stops immediately if any step
fails (e.g., a bad migration) instead of restarting gunicorn into a
half-migrated database.

## 9. Backups

```bash
pg_dump -U plates_app -h localhost -F c plates_db -f plates_backup_$(date +%F).dump
```

Restore:

```bash
pg_restore -U plates_app -h localhost -d plates_db plates_backup_2026-09-17.dump
```

Store credentials for non-interactive `pg_dump` (e.g. in cron) in
`~/.pgpass` (`chmod 600`) rather than in a script.

Backups should be copied off the VM (rsync to another host/NAS) — a dump
sitting next to the database it backs up does not protect against disk or
host failure.

---

## Encountered Issues

| Symptom | Cause | Fix |
|---|---|---|
| `password authentication failed for user "plates_dev"` | `FLASK_ENV` not set/exported in this shell → app silently falls back to `DevelopmentConfig`'s hardcoded dev credentials | `export FLASK_ENV=production` (or `set -a; source .env; set +a`) |
| `echo $FLASK_ENV` shows correct value, but `flask shell` / `os.environ.get("FLASK_ENV")` shows `None` | Variable was set as shell-local, not exported — child processes never see it | Always `export`, or use `set -a` around `source` |
| `permission denied for schema public` | Postgres 15+ default: non-owner roles have no `CREATE` on `public` | `GRANT CREATE, USAGE ON SCHEMA public TO plates_app;` (see Step 2) |
| `Error: Target database is not up to date` | A migration file exists on disk but hasn't been applied via `flask db upgrade` | Run `flask db current` / `flask db heads` to check, then `flask db upgrade` |
| Migration file missing after a failed `flask db migrate` | The command failed partway (e.g. on the permission error) before writing the file | Check `migrations/versions/`; if empty, `flask db stamp head` then re-run `migrate` |