#!/usr/bin/env bash

set -euo pipefail


APP_DIR="$(
    cd "$(
        dirname "${BASH_SOURCE[0]}"
    )"
    pwd
)"

VENV_DIR="${APP_DIR}/venv"
ENV_FILE="${APP_DIR}/.env"

DB_NAME="${DB_NAME:-username_inventory}"
DB_USER="${DB_USER:-username_inventory_user}"

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-5070}"
APP_PREFIX="${APP_PREFIX:-}"


echo
echo "Username's Inventory installer"
echo "================================"
echo "Application directory: ${APP_DIR}"
echo


if [[ ! "${DB_NAME}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Invalid DB_NAME: ${DB_NAME}" >&2
    exit 1
fi

if [[ ! "${DB_USER}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Invalid DB_USER: ${DB_USER}" >&2
    exit 1
fi


echo "[1/7] Checking required commands..."

for command in \
    python3 \
    sudo \
    psql
do
    if ! command -v "${command}" >/dev/null 2>&1; then
        echo \
            "Required command not found: ${command}" \
            >&2
        exit 1
    fi
done


echo "[2/7] Detecting PostgreSQL port..."

PGPORT="$(
    sudo -u postgres \
        psql \
        -tAc "SHOW port;" \
        | tr -d '[:space:]'
)"

if [[ -z "${PGPORT}" ]]; then
    echo "Could not detect PostgreSQL port." >&2
    exit 1
fi

echo "PostgreSQL port: ${PGPORT}"


echo "[3/7] Creating Python virtual environment..."

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" \
    -m pip install \
    --upgrade pip

"${VENV_DIR}/bin/pip" \
    install \
    -r "${APP_DIR}/requirements.txt"


echo "[4/7] Preparing PostgreSQL database..."

DB_PASSWORD="$(
    "${VENV_DIR}/bin/python" - <<'PY2'
import secrets
print(secrets.token_hex(24))
PY2
)"

ROLE_EXISTS="$(
    sudo -u postgres \
        psql \
        --port "${PGPORT}" \
        -tAc \
        "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}';" \
        | tr -d '[:space:]'
)"

if [[ "${ROLE_EXISTS}" != "1" ]]; then
    sudo -u postgres \
        createuser \
        --port "${PGPORT}" \
        "${DB_USER}"
fi

sudo -u postgres \
    psql \
    --port "${PGPORT}" \
    -v ON_ERROR_STOP=1 \
    -c \
    "ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';"


DATABASE_EXISTS="$(
    sudo -u postgres \
        psql \
        --port "${PGPORT}" \
        -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" \
        | tr -d '[:space:]'
)"

if [[ "${DATABASE_EXISTS}" != "1" ]]; then
    sudo -u postgres \
        createdb \
        --port "${PGPORT}" \
        --owner "${DB_USER}" \
        "${DB_NAME}"
fi


echo "[5/7] Writing application configuration..."

if [[ -e "${ENV_FILE}" ]]; then
    echo
    echo "ERROR: ${ENV_FILE} already exists."
    echo "Installer will not overwrite an existing configuration."
    echo
    exit 1
fi

SECRET_KEY="$(
    "${VENV_DIR}/bin/python" - <<'PY2'
import secrets
print(secrets.token_hex(32))
PY2
)"

cat > "${ENV_FILE}" <<EOF
FLASK_APP=run.py
FLASK_ENV=production

SECRET_KEY=${SECRET_KEY}

DATABASE_URL=postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@127.0.0.1:${PGPORT}/${DB_NAME}

APP_HOST=${APP_HOST}
APP_PORT=${APP_PORT}

APP_PREFIX=${APP_PREFIX}
EOF

chmod 600 "${ENV_FILE}"

mkdir -p \
    "${APP_DIR}/uploads/items"


echo "[6/7] Applying database migrations..."

cd "${APP_DIR}"

"${VENV_DIR}/bin/flask" \
    db upgrade


echo "[7/7] Verifying application startup..."

"${VENV_DIR}/bin/python" - <<'PY2'
from app import create_app

app = create_app()

with app.app_context():
    print(
        "Application:",
        app.name,
    )
    print(
        "Upload folder:",
        app.config["ITEM_UPLOAD_FOLDER"],
    )
PY2


echo
echo "================================"
echo "Installation completed."
echo
echo "Create the first administrator with:"
echo
echo "  ${VENV_DIR}/bin/python create_admin.py"
echo
echo "Test Gunicorn with:"
echo
echo "  ${VENV_DIR}/bin/gunicorn \\"
echo "      --workers 2 \\"
echo "      --bind ${APP_HOST}:${APP_PORT} \\"
echo "      run:app"
echo
echo "Configuration:"
echo "  ${ENV_FILE}"
echo
echo "Database:"
echo "  ${DB_NAME}"
echo
echo "PostgreSQL port:"
echo "  ${PGPORT}"
echo
