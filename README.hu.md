# Username's Inventory

Egyszerű, saját szerveren futtatható készlet- és tárhelynyilvántartó rendszer otthoni, műhely-, archív-, irodai vagy kisebb raktári használatra.

A rendszer fő célja annak gyors megválaszolása, hogy **miből mennyi van, és pontosan hol található**.

> **Kiadás:** `0.1.0-alpha.1`
> Ez egy korai publikus alpha kiadás. Fontos adatok esetén frissítés előtt mindig készíts mentést.

## Fő funkciók

- hierarchikus tárhelystruktúra
- tételek és tételtípusok kezelése
- bevételezés
- áthelyezés
- kiadás
- leltárkorrekció
- aktuális készlet áttekintése
- készletmozgások naplója
- CSV és XLSX export
- tételképek
- vonalkód-/scanner-központú munkafolyamatok
- címkézési funkciók
- admin, editor és viewer jogosultság
- magyar és angol felület
- felhasználónként választható nyelv
- PostgreSQL adatbázis
- adatbázis-migrációk
- health endpoint
- opcionális URL-prefix reverse proxy mögött

## Példa tárhelystruktúra

```text
Garázs
└── Jobb oldal
    └── 2. oszlop
        └── 3. polc
```

Egy tétel egyszerre több tárhelyen is rendelkezhet készlettel.

## Technológia

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

## Telepítés

Új Ubuntu telepítésnél a mellékelt installer létre tudja hozni a Python környezetet, a PostgreSQL adatbázist, a konfigurációt és lefuttatja a migrációkat:

```bash
./install.sh
```

Az első admin felhasználót külön kell létrehozni:

```bash
venv/bin/python create_admin.py
```


Részletes útmutató:

- [Magyar telepítési útmutató](docs/INSTALL.hu.md)
- [English installation guide](docs/INSTALL.md)

## Jogosultságok

Három fő szerepkör van:

- **admin** — teljes adminisztráció
- **editor** — készletműveletek adminfelület nélkül
- **viewer** — csak olvasási jogosultság

## Mentés

A publikus repository szándékosan nem tartalmaz:

- production adatbázist
- feltöltött képeket
- helyi backup scriptet
- eredeti induló készletadatokat
- `.env` fájlt

Frissítés előtt legalább az adatbázist, az upload könyvtárat és a production `.env` fájlt érdemes menteni.

## Fejlesztési állapot

A projekt eredetileg valós készletkezelési igényre készült, majd később lett általánosítva publikus használatra.

A jelenlegi változat **alpha kiadás**.

## Licenc

MIT License. Lásd: [LICENSE](LICENSE).

## Támogatás

Patreon:

https://www.patreon.com/c/ZoltanRigo
