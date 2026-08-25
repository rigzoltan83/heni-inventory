from app import create_app
from app.extensions import db
from app.inventory_service import (
    InventoryError,
    issue,
    move,
    receipt,
    set_counted_quantity,
)
from app.models import InventoryStock, User


app = create_app()


with app.app_context():
    item_id = 3
    source_location_id = 5
    destination_location_id = 6

    admin_user = (
        User.query
        .filter_by(
            role=User.ROLE_ADMIN,
            is_enabled=True,
        )
        .order_by(User.id)
        .first()
    )

    if admin_user is None:
        raise SystemExit(
            "Nincs aktív admin felhasználó."
        )

    print(
        "Mozgásokat végzi:",
        admin_user.username,
        f"(id={admin_user.id})",
    )

    existing_stock = (
        InventoryStock.query
        .filter(
            InventoryStock.item_id == item_id,
            InventoryStock.location_id.in_(
                [
                    source_location_id,
                    destination_location_id,
                ]
            ),
        )
        .all()
    )

    if existing_stock:
        print()
        print(
            "FIGYELEM: a tesztelt helyeken "
            "már van készlet:"
        )

        for stock in existing_stock:
            print(
                stock.location_id,
                stock.quantity,
            )

        raise SystemExit(
            "Teszt megszakítva, nehogy meglévő "
            "készletre ráírjunk."
        )

    try:
        print()
        print("1. Bevételezés: +100")

        receipt(
            item_id=item_id,
            location_id=source_location_id,
            quantity=100,
            user_id=admin_user.id,
            note="Mozgásmotor teszt",
        )

        print("2. Áthelyezés: 30 db")

        move(
            item_id=item_id,
            from_location_id=source_location_id,
            to_location_id=destination_location_id,
            quantity=30,
            user_id=admin_user.id,
            note="Mozgásmotor teszt",
        )

        print("3. Kiadás: 5 db")

        issue(
            item_id=item_id,
            location_id=destination_location_id,
            quantity=5,
            user_id=admin_user.id,
            note="Mozgásmotor teszt",
        )

        print(
            "4. Leltárkorrekció: "
            "Bal felső ténylegesen 20 db"
        )

        set_counted_quantity(
            item_id=item_id,
            location_id=destination_location_id,
            counted_quantity=20,
            user_id=admin_user.id,
            note="Mozgásmotor teszt",
        )

        print()
        print("Teszt lefutott.")

        rows = (
            InventoryStock.query
            .filter_by(
                item_id=item_id,
            )
            .order_by(
                InventoryStock.location_id,
            )
            .all()
        )

        print()
        print("Aktuális készlet:")

        total = 0

        for row in rows:
            print(
                f"{row.location.name}: "
                f"{row.quantity} db"
            )

            total += row.quantity

        print(
            f"Összesen: {total} db"
        )

    except InventoryError as exc:
        db.session.rollback()

        raise SystemExit(
            f"Készlethiba: {exc}"
        )
