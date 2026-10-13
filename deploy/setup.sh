#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Install Docker Engine and the Docker Compose plugin, then rerun.'; exit 1; }
docker compose version >/dev/null
[[ -f deploy/.env ]] || python3 deploy/configure.py
chmod 600 deploy/.env
compose=(docker compose --env-file deploy/.env -f deploy/compose.yaml)
"${compose[@]}" build
"${compose[@]}" run --rm api python -m production.manage check-db
python3 deploy/migrate.py
echo 'DBA: apply deploy/sql/02_runtime_permissions.sql, adding your runtime database user to the role.'
read -r -p 'Press Enter after the runtime permissions are ready. ' BIA_PERMISSION_READY
read -r -p 'Create an administrator now? [Y/n] ' BIA_CREATE_ADMIN
if [[ "$BIA_CREATE_ADMIN" != 'n' && "$BIA_CREATE_ADMIN" != 'N' ]]; then
  "${compose[@]}" run --rm api python -m production.manage create-admin
fi
"${compose[@]}" up -d
"${compose[@]}" ps
echo 'BIA started. Open the HTTPS origin configured in deploy/.env and sign in.'
