# Username's Inventory

A lightweight self-hosted inventory and storage-location manager for households, workshops, archives, small organizations and other environments where knowing **what is stored where** matters.

Username's Inventory is built with Flask and PostgreSQL and provides a browser-based interface suitable for both desktop and mobile use.

> **Release status:** `0.1.0-alpha.1`
> This is an early public release. Back up important data before upgrades.

## Main features

- hierarchical storage locations
- item and item-type management
- stock receipt
- stock movement between locations
- stock issue
- inventory corrections
- current stock overview
- movement history
- CSV and XLSX exports
- item images
- barcode / scanner-oriented workflows
- label-related workflows
- administrator, editor and viewer roles
- Hungarian and English UI
- per-user language preference
- PostgreSQL database
- database migrations
- health endpoint
- optional reverse-proxy URL prefix

## Typical use cases

Username's Inventory can be used for:

- household storage
- garage or workshop inventory
- office supplies
- archive boxes
- books and publications
- spare parts
- warehouse-style shelf locations
- collections where exact physical placement matters

Locations may be organized as a hierarchy, for example:

```text
Garage
└── Right side
    └── Column 2
        └── Shelf 3
```

Stock is tracked at the item/location level, so the same item can exist in several places.

## Technology

- Python
- Flask
- SQLAlchemy
- PostgreSQL
- Flask-Migrate / Alembic
- Flask-Login
- Flask-Babel
- Gunicorn
- Pillow
- XlsxWriter

## Installation

Ubuntu installation instructions are available here:

- [Installation guide](docs/INSTALL.md)
- [Magyar telepítési útmutató](docs/INSTALL.hu.md)

For a new Ubuntu installation, the included installer can prepare the virtual environment, PostgreSQL database, configuration and migrations:

```bash
./install.sh
```

The installer does not create the first administrator automatically. After installation run:

```bash
venv/bin/python create_admin.py
```

A minimal manual setup is:

```bash
git clone https://github.com/rigzoltan83/heni-inventory.git
cd heni-inventory

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
```

Edit `.env`, create the PostgreSQL database and user, then run:

```bash
venv/bin/flask db upgrade
venv/bin/python create_admin.py
```

For production, run the application behind Gunicorn and optionally a reverse proxy.

## Configuration

Important environment variables:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session signing key |
| `DATABASE_URL` | PostgreSQL connection URL |
| `APP_HOST` | Development server bind address |
| `APP_PORT` | Development server port |
| `APP_PREFIX` | Optional URL prefix behind a reverse proxy |
| `ITEM_UPLOAD_FOLDER` | Optional item-image storage directory |

Example configuration is provided in `.env.example`.

## User roles

The application supports three roles:

- **admin** — full application and master-data administration
- **editor** — inventory operations without administrative access
- **viewer** — read-only inventory access

## Data and backups

The repository intentionally does **not** contain production databases, uploads, backup scripts or private initial inventory data.

Back up at least:

- the PostgreSQL database
- the item upload directory
- your production `.env`

before upgrades or migration work.

## Development status

This project was originally built for a real-world inventory workflow and is now being generalized for public use.

The current release should be considered an **alpha**. The core workflow is usable, but installation and deployment outside the original environment are still being refined.

## License

MIT License. See [LICENSE](LICENSE).

## Support

If you find the project useful, development can be supported on Patreon:

https://www.patreon.com/c/ZoltanRigo
