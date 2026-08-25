import argparse
from collections import defaultdict

from app.extensions import db
from app import create_app
from app.models import (
    InventoryMovement,
    InventoryStock,
    Item,
    Location,
    User,
)
from app.inventory_service import receipt


app = create_app()


# (tárhely teljes útvonala, tétel megnevezése, mennyiség)
#
# A 0 készleteket is megtartjuk az ellenőrzéshez,
# de tényleges készletpozíció nem készül belőlük.

SOURCE_ROWS = [

    # =========================================================
    # GARÁZS - JOBB OLDAL
    # =========================================================

    # 1. sor / 1. oszlop
    (
        "Garázs > Jobb oldal > 1. oszlop > 1. sor",
        "KMF 33 - 3. osztály",
        1020,
    ),

    # 1. sor / 2. oszlop
    (
        "Garázs > Jobb oldal > 2. oszlop > 1. sor",
        "Zrínyi 2024",
        0,
    ),
    (
        "Garázs > Jobb oldal > 2. oszlop > 1. sor",
        "Abacus 2015-2019",
        360,
    ),

    # 1. sor / 3. oszlop
    (
        "Garázs > Jobb oldal > 3. oszlop > 1. sor",
        "Zrínyi 2023",
        450,
    ),

    # 1. sor / 4. oszlop
    (
        "Garázs > Jobb oldal > 4. oszlop > 1. sor",
        "Zrínyi 2021",
        580,
    ),

    # 2. sor / 1. oszlop
    (
        "Garázs > Jobb oldal > 1. oszlop > 2. sor",
        "Zrínyi 2022",
        510,
    ),

    # 2. sor / 2. oszlop
    (
        "Garázs > Jobb oldal > 2. oszlop > 2. sor",
        "Zrínyi 2024",
        600,
    ),

    # 2. sor / 3. oszlop
    (
        "Garázs > Jobb oldal > 3. oszlop > 2. sor",
        "Zrínyi 2023",
        600,
    ),

    # 2. sor / 4. oszlop
    (
        "Garázs > Jobb oldal > 4. oszlop > 2. sor",
        "Zrínyi 2021",
        500,
    ),

    # 3. sor / 1. oszlop
    (
        "Garázs > Jobb oldal > 1. oszlop > 3. sor",
        "KMF 33 - 3. osztály",
        640,
    ),
    (
        "Garázs > Jobb oldal > 1. oszlop > 3. sor",
        "Abacus 2015-2019",
        150,
    ),

    # 3. sor / 2. oszlop
    (
        "Garázs > Jobb oldal > 2. oszlop > 3. sor",
        "Zrínyi 2024",
        600,
    ),

    # 3. sor / 3. oszlop
    (
        "Garázs > Jobb oldal > 3. oszlop > 3. sor",
        "KMF 38 - 8. osztály",
        920,
    ),

    # 3. sor / 4. oszlop
    (
        "Garázs > Jobb oldal > 4. oszlop > 3. sor",
        "Zrínyi 2021",
        300,
    ),
    (
        "Garázs > Jobb oldal > 4. oszlop > 3. sor",
        "Zrínyi 2020",
        0,
    ),
    (
        "Garázs > Jobb oldal > 4. oszlop > 3. sor",
        "Kecske Kupa",
        145,
    ),

    # 4. sor / 1. oszlop
    (
        "Garázs > Jobb oldal > 1. oszlop > 4. sor",
        "KMF 34 - 4. osztály",
        840,
    ),

    # 4. sor / 2. oszlop
    (
        "Garázs > Jobb oldal > 2. oszlop > 4. sor",
        "Zrínyi 2024",
        550,
    ),

    # 4. sor / 3. oszlop
    (
        "Garázs > Jobb oldal > 3. oszlop > 4. sor",
        "KMF 38 - 8. osztály",
        630,
    ),
    (
        "Garázs > Jobb oldal > 3. oszlop > 4. sor",
        "Abacus 2015-2019",
        125,
    ),

    # 4. sor / 4. oszlop
    (
        "Garázs > Jobb oldal > 4. oszlop > 4. sor",
        "Kecske Kupa",
        60,
    ),
    (
        "Garázs > Jobb oldal > 4. oszlop > 4. sor",
        "Kecske Kupa",
        210,
    ),

    # Felső rész - 1. oszlop = felső polc
    (
        "Garázs > Jobb oldal > 1. oszlop > felső polc",
        "Zrínyi 2022",
        10,
    ),
    (
        "Garázs > Jobb oldal > 1. oszlop > felső polc",
        "Abacus 2000-2004",
        145,
    ),
    (
        "Garázs > Jobb oldal > 1. oszlop > felső polc",
        "Fizika",
        30,
    ),
    (
        "Garázs > Jobb oldal > 1. oszlop > felső polc",
        "Gordiusz 2011",
        200,
    ),
    (
        "Garázs > Jobb oldal > 1. oszlop > felső polc",
        "Abacus 2005-2009",
        100,
    ),

    # Felső rész - 2. oszlop = raklap
    (
        "Garázs > Jobb oldal > 2. oszlop > raklap",
        "KMF 39 - Orosz Gyula",
        720,
    ),
    (
        "Garázs > Jobb oldal > 2. oszlop > raklap",
        "Abacus 2010-2014",
        975,
    ),
    (
        "Garázs > Jobb oldal > 2. oszlop > raklap",
        "Abacus 2010-2014",
        670,
    ),
    (
        "Garázs > Jobb oldal > 2. oszlop > raklap",
        "Abacus 2000-2004",
        320,
    ),
    (
        "Garázs > Jobb oldal > 2. oszlop > raklap",
        "Kecske Kupa",
        520,
    ),

    # Felső rész - 3. oszlop = raklap
    (
        "Garázs > Jobb oldal > 3. oszlop > raklap",
        "Zrínyi 2024",
        0,
    ),
    (
        "Garázs > Jobb oldal > 3. oszlop > raklap",
        "Abacus 2000-2004",
        500,
    ),
    (
        "Garázs > Jobb oldal > 3. oszlop > raklap",
        "Kecske Kupa",
        550,
    ),

    # Felső rész - 4. oszlop = raklap
    (
        "Garázs > Jobb oldal > 4. oszlop > raklap",
        "Kecske Kupa",
        1120,
    ),

    # =========================================================
    # GARÁZS - BAL OLDAL
    # =========================================================

    # 1. sor / 1. oszlop
    (
        "Garázs > Bal oldal > 1. oszlop > 1. sor",
        "Zrínyi 2020",
        550,
    ),

    # 1. sor / 2. oszlop
    (
        "Garázs > Bal oldal > 2. oszlop > 1. sor",
        "Zrínyi 2022 (9-12. osztály)",
        190,
    ),
    (
        "Garázs > Bal oldal > 2. oszlop > 1. sor",
        "Zrínyi 2023 (9-12. osztály)",
        30,
    ),
    (
        "Garázs > Bal oldal > 2. oszlop > 1. sor",
        "Zrínyi 2020 (9-12. osztály)",
        40,
    ),
    (
        "Garázs > Bal oldal > 2. oszlop > 1. sor",
        "Zrínyi 2021 (9-12. osztály)",
        60,
    ),
    (
        "Garázs > Bal oldal > 2. oszlop > 1. sor",
        "Abacus 2015-2019",
        255,
    ),

    # 1. sor / 3. oszlop
    (
        "Garázs > Bal oldal > 3. oszlop > 1. sor",
        "KMF 35 - 5. osztály",
        570,
    ),

    # 1. sor / 4. oszlop
    (
        "Garázs > Bal oldal > 4. oszlop > 1. sor",
        "KMF 35 - 5. osztály",
        1000,
    ),

    # 2. sor / 1. oszlop
    (
        "Garázs > Bal oldal > 1. oszlop > 2. sor",
        "Zrínyi 2020",
        550,
    ),

    # 2. sor / 2. oszlop
    (
        "Garázs > Bal oldal > 2. oszlop > 2. sor",
        "KMF 37 - 7. osztály",
        600,
    ),

    # 2. sor / 3. oszlop
    (
        "Garázs > Bal oldal > 3. oszlop > 2. sor",
        "KMF 36 - 6. osztály",
        860,
    ),

    # 2. sor / 4. oszlop
    (
        "Garázs > Bal oldal > 4. oszlop > 2. sor",
        "Abacus 2015-2019",
        280,
    ),

    # 3. sor / 1. oszlop
    (
        "Garázs > Bal oldal > 1. oszlop > 3. sor",
        "Zrínyi 2020",
        460,
    ),
    (
        "Garázs > Bal oldal > 1. oszlop > 3. sor",
        "Abacus 2015-2019",
        0,
    ),

    # 3. sor / 2. oszlop
    (
        "Garázs > Bal oldal > 2. oszlop > 3. sor",
        "KMF 37 - 7. osztály",
        960,
    ),

    # 3. sor / 3. oszlop
    (
        "Garázs > Bal oldal > 3. oszlop > 3. sor",
        "Zrínyi 2023",
        0,
    ),
    (
        "Garázs > Bal oldal > 3. oszlop > 3. sor",
        "Abacus 2015-2019",
        375,
    ),

    # 3. sor / 4. oszlop
    (
        "Garázs > Bal oldal > 4. oszlop > 3. sor",
        "Abacus 2015-2019",
        280,
    ),

    # 4. sor / 1. oszlop
    (
        "Garázs > Bal oldal > 1. oszlop > 4. sor",
        "Abacus 2010-2014",
        230,
    ),

    # 4. sor / 2. oszlop
    (
        "Garázs > Bal oldal > 2. oszlop > 4. sor",
        "Abacus 2015-2019",
        230,
    ),
    (
        "Garázs > Bal oldal > 2. oszlop > 4. sor",
        "Abacus 2015-2019",
        75,
    ),

    # 4. sor / 3. oszlop
    (
        "Garázs > Bal oldal > 3. oszlop > 4. sor",
        "KMF 36 - 6. osztály",
        680,
    ),

    # 4. sor / 4. oszlop
    (
        "Garázs > Bal oldal > 4. oszlop > 4. sor",
        "KMF 34 - 4. osztály",
        710,
    ),

    # Felső rész - 1. oszlop = felső polc
    (
        "Garázs > Bal oldal > 1. oszlop > felső polc",
        "Abacus 2010-2014",
        150,
    ),
    (
        "Garázs > Bal oldal > 1. oszlop > felső polc",
        "Tanárverseny",
        120,
    ),
    (
        "Garázs > Bal oldal > 1. oszlop > felső polc",
        "Zrínyi 2019",
        700,
    ),
    (
        "Garázs > Bal oldal > 1. oszlop > felső polc",
        "Orosz Gyula",
        190,
    ),
    (
        "Garázs > Bal oldal > 1. oszlop > felső polc",
        "Gordiusz 2009-2010",
        40,
    ),

    # Felső rész - 2. oszlop = egyéb
    (
        "Garázs > Bal oldal > 2. oszlop > egyéb",
        "Abacus 2000-2004",
        500,
    ),
]


def build_maps():
    items_by_name = defaultdict(list)

    for item in (
        Item.query
        .filter(
            Item.is_active.is_(True)
        )
        .all()
    ):
        items_by_name[item.name].append(item)

    locations_by_path = defaultdict(list)

    for location in (
        Location.query
        .filter(
            Location.is_active.is_(True),
            Location.can_hold_stock.is_(True),
        )
        .all()
    ):
        locations_by_path[
            location.full_path
        ].append(location)

    return (
        items_by_name,
        locations_by_path,
    )


def validate_and_group(
    items_by_name,
    locations_by_path,
):
    errors = []

    grouped = defaultdict(int)

    zero_rows = []

    for (
        location_path,
        item_name,
        quantity,
    ) in SOURCE_ROWS:

        items = items_by_name.get(
            item_name,
            [],
        )

        locations = locations_by_path.get(
            location_path,
            [],
        )

        if len(items) != 1:
            errors.append(
                (
                    f"Tétel nem oldható fel "
                    f"pontosan egyszer: "
                    f"{item_name!r} "
                    f"(találat: {len(items)})"
                )
            )

        if len(locations) != 1:
            errors.append(
                (
                    f"Tárhely nem oldható fel "
                    f"pontosan egyszer: "
                    f"{location_path!r} "
                    f"(találat: {len(locations)})"
                )
            )

        if quantity < 0:
            errors.append(
                (
                    f"Negatív induló készlet: "
                    f"{item_name} / "
                    f"{location_path} / "
                    f"{quantity}"
                )
            )

        if (
            len(items) != 1
            or len(locations) != 1
        ):
            continue

        if quantity == 0:
            zero_rows.append(
                (
                    location_path,
                    item_name,
                    quantity,
                )
            )

            continue

        key = (
            items[0].id,
            locations[0].id,
            item_name,
            location_path,
        )

        grouped[key] += quantity

    return (
        errors,
        grouped,
        zero_rows,
    )


def show_preview(
    grouped,
    zero_rows,
):
    print()
    print("=" * 100)
    print("INDULÓ KÉSZLET - ELLENŐRZŐ ELŐNÉZET")
    print("=" * 100)

    current_location = None

    total_quantity = 0

    for (
        item_id,
        location_id,
        item_name,
        location_path,
    ), quantity in sorted(
        grouped.items(),
        key=lambda row: (
            row[0][3],
            row[0][2],
        ),
    ):
        if location_path != current_location:
            print()
            print(location_path)

            current_location = location_path

        print(
            f"  {item_name:<42} "
            f"{quantity:>6} db "
            f"(item={item_id}, loc={location_id})"
        )

        total_quantity += quantity

    print()
    print("-" * 100)
    print(
        f"Készletpozíciók száma: "
        f"{len(grouped)}"
    )
    print(
        f"Összes induló darabszám: "
        f"{total_quantity}"
    )

    print()
    print("NULLÁS FORRÁSSOROK - NEM KERÜLNEK KÉSZLETRE")

    if zero_rows:
        for (
            location_path,
            item_name,
            quantity,
        ) in zero_rows:
            print(
                f"  {location_path}"
                f" | {item_name}"
                f" | {quantity}"
            )
    else:
        print("  nincs")

    print("=" * 100)
    print()


def apply_import(
    grouped,
    admin_user,
):
    existing_stock = (
        InventoryStock.query.count()
    )

    existing_movements = (
        InventoryMovement.query.count()
    )

    if (
        existing_stock != 0
        or existing_movements != 0
    ):
        raise RuntimeError(
            "Az import megtagadva: "
            "az adatbázisban már van készlet "
            "vagy készletmozgás. "
            f"stock={existing_stock}, "
            f"movements={existing_movements}"
        )

    print(
        f"Bevételezést végző user: "
        f"{admin_user.username} "
        f"(id={admin_user.id})"
    )

    for (
        item_id,
        location_id,
        item_name,
        location_path,
    ), quantity in sorted(
        grouped.items(),
        key=lambda row: (
            row[0][3],
            row[0][2],
        ),
    ):
        print(
            f"BEVÉTELEZÉS: "
            f"{item_name} -> "
            f"{location_path}: "
            f"{quantity} db"
        )

        receipt(
            item_id=item_id,
            location_id=location_id,
            quantity=quantity,
            user_id=admin_user.id,
            note="Induló készlet import",
            commit=False,
        )

    db.session.commit()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Az ellenőrzés után ténylegesen "
            "betölti a készletet."
        ),
    )

    args = parser.parse_args()

    with app.app_context():
        (
            items_by_name,
            locations_by_path,
        ) = build_maps()

        (
            errors,
            grouped,
            zero_rows,
        ) = validate_and_group(
            items_by_name,
            locations_by_path,
        )

        if errors:
            print()
            print("HIBÁK:")

            for error in errors:
                print(
                    " -",
                    error,
                )

            raise SystemExit(1)

        show_preview(
            grouped,
            zero_rows,
        )

        if not args.apply:
            print(
                "ELLENŐRZÉS KÉSZ."
            )
            print(
                "Az adatbázis NEM módosult."
            )
            print()
            print(
                "Tényleges betöltés:"
            )
            print(
                "python import_initial_stock.py --apply"
            )

            return

        admin_user = (
            User.query
            .filter(
                User.role
                == User.ROLE_ADMIN,
                User.is_enabled.is_(True),
            )
            .order_by(User.id)
            .first()
        )

        if admin_user is None:
            raise RuntimeError(
                "Nincs aktív admin user."
            )

        try:
            apply_import(
                grouped,
                admin_user,
            )

        except Exception:
            db.session.rollback()
            raise

        print()
        print("INDULÓ KÉSZLET BETÖLTVE.")


if __name__ == "__main__":
    main()
