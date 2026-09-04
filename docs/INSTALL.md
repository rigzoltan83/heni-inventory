# Username's Inventory — Ubuntu Installation

This guide describes a straightforward installation on Ubuntu 24.04 with PostgreSQL and Gunicorn.

## 1. Install system packages

```bash
sudo apt update

sudo apt install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    postgresql \
    postgresql-contrib
```

## 2. Clone the repository

```bash
sudo mkdir -p /opt/username-inventory
sudo chown "$USER":"$USER" /opt/username-inventory

git clone \
    https://github.com/rigzoltan83/heni-inventory.git \
    /opt/username-inventory

cd /opt/username-inventory
```

## 3. Create the Python environment

```bash
python3 -m venv venv

venv/bin/pip install \
    --upgrade pip

venv/bin/pip install \
    -r requirements.txt
```

## 4. Create the PostgreSQL database

Check the local PostgreSQL port:

```bash
sudo -u postgres psql \
    -tAc "SHOW port;"
```

Create the application database and user:

```bash
sudo -u postgres psql
```

Example SQL:

```sql
CREATE USER username_inventory_user
WITH PASSWORD 'CHANGE_THIS_PASSWORD';

CREATE DATABASE username_inventory
OWNER username_inventory_user;

\q
```

## 5. Configure the application

```bash
cp .env.example .env
chmod 600 .env
```

Generate a strong secret:

```bash
python3 -c \
'import secrets; print(secrets.token_hex(32))'
```

Edit `.env`:

```bash
nano .env
```

Set at least:

```text
SECRET_KEY=...
DATABASE_URL=postgresql+psycopg://username_inventory_user:PASSWORD@127.0.0.1:5432/username_inventory
```

Use the actual PostgreSQL port if it is not `5432`.

## 6. Apply database migrations

```bash
venv/bin/flask db upgrade
```

## 7. Create the first administrator

```bash
venv/bin/python create_admin.py
```

## 8. Test the application

```bash
venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5070 \
    run:app
```

In another terminal:

```bash
curl http://127.0.0.1:5070/health
```

Expected result:

```json
{
  "application": "heni-inventory",
  "database": "ok",
  "status": "ok"
}
```

## 9. Production service

A systemd template is provided under `deploy/`.

Adjust its user, group, installation path and port before installing it.

## URL prefix

When the application is published under a subpath, set for example:

```text
APP_PREFIX=/inventory
```

Direct Gunicorn requests should still use paths without that prefix. The prefix is intended for reverse-proxy deployment.

## Upgrading

Before upgrades, back up the database and uploads.

Then:

```bash
cd /opt/username-inventory

git pull

venv/bin/pip install \
    -r requirements.txt

venv/bin/flask db upgrade

sudo systemctl restart \
    username-inventory
```
