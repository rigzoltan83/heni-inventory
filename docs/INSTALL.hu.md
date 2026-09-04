# Username's Inventory — Ubuntu telepítés

Az útmutató Ubuntu 24.04, PostgreSQL és Gunicorn használatával mutat be egy egyszerű telepítést.

## 1. Szükséges csomagok

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

## 2. Repository klónozása

```bash
sudo mkdir -p /opt/username-inventory
sudo chown "$USER":"$USER" /opt/username-inventory

git clone \
    https://github.com/rigzoltan83/heni-inventory.git \
    /opt/username-inventory

cd /opt/username-inventory
```

## 3. Python környezet

```bash
python3 -m venv venv

venv/bin/pip install \
    --upgrade pip

venv/bin/pip install \
    -r requirements.txt
```

## 4. PostgreSQL adatbázis

A helyi PostgreSQL port ellenőrzése:

```bash
sudo -u postgres psql \
    -tAc "SHOW port;"
```

Belépés:

```bash
sudo -u postgres psql
```

Példa:

```sql
CREATE USER username_inventory_user
WITH PASSWORD 'IDE_EROS_JELSZO';

CREATE DATABASE username_inventory
OWNER username_inventory_user;

\q
```

## 5. Konfiguráció

```bash
cp .env.example .env
chmod 600 .env
```

Erős SECRET_KEY generálása:

```bash
python3 -c \
'import secrets; print(secrets.token_hex(32))'
```

Majd:

```bash
nano .env
```

Legalább ezeket állítsd be:

```text
SECRET_KEY=...
DATABASE_URL=postgresql+psycopg://username_inventory_user:JELSZO@127.0.0.1:5432/username_inventory
```

Ha a PostgreSQL nem 5432-es porton fut, a tényleges portot használd.

## 6. Adatbázis-migrációk

```bash
venv/bin/flask db upgrade
```

## 7. Első admin létrehozása

```bash
venv/bin/python create_admin.py
```

## 8. Tesztindítás

```bash
venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5070 \
    run:app
```

Másik terminálból:

```bash
curl http://127.0.0.1:5070/health
```

## 9. Production service

A `deploy/` könyvtárban található systemd minta.

Telepítés előtt az alkalmazás userét, csoportját, útvonalát és portját az adott géphez kell igazítani.

## URL-prefix

Ha például `/inventory` alatt publikálod:

```text
APP_PREFIX=/inventory
```

## Frissítés

Frissítés előtt készíts mentést az adatbázisról és az upload könyvtárról.

Utána:

```bash
cd /opt/username-inventory

git pull

venv/bin/pip install \
    -r requirements.txt

venv/bin/flask db upgrade

sudo systemctl restart \
    username-inventory
```
