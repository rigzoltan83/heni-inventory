from contextlib import contextmanager

from app import create_app
from app.extensions import db
from app.models import (
    InventoryStock,
    Item,
    ItemImage,
    Location,
    User,
)


app = create_app()

app.config["TESTING"] = True
app.config["LOGIN_DISABLED"] = False


def load_test_data():
    with app.app_context():
        users = {}

        for role in (
            User.ROLE_ADMIN,
            User.ROLE_EDITOR,
            User.ROLE_VIEWER,
        ):
            user = (
                User.query
                .filter(
                    User.role == role,
                    User.is_enabled.is_(True),
                )
                .order_by(User.id)
                .first()
            )

            if user is None:
                raise SystemExit(
                    f"Hiányzó aktív teszt user: {role}"
                )

            users[role] = {
                "id": user.id,
                "username": user.username,
            }

        item = (
            Item.query
            .filter(
                Item.is_active.is_(True)
            )
            .order_by(Item.id)
            .first()
        )

        if item is None:
            raise SystemExit(
                "Nincs aktív tétel a teszthez."
            )

        location = (
            Location.query
            .filter(
                Location.is_active.is_(True),
                Location.can_hold_stock.is_(True),
            )
            .order_by(Location.id)
            .first()
        )

        if location is None:
            raise SystemExit(
                "Nincs készlettartó tárhely "
                "a teszthez."
            )

        stock = (
            InventoryStock.query
            .filter(
                InventoryStock.quantity > 0
            )
            .order_by(InventoryStock.id)
            .first()
        )

        image = (
            ItemImage.query
            .order_by(ItemImage.id)
            .first()
        )

        return {
            "users": users,
            "item": {
                "id": item.id,
                "name": item.name,
            },
            "location": {
                "id": location.id,
                "name": location.full_path,
            },
            "stock": (
                {
                    "item_id": stock.item_id,
                    "location_id": stock.location_id,
                    "quantity": stock.quantity,
                }
                if stock
                else None
            ),
            "image": (
                {
                    "id": image.id,
                    "item_id": image.item_id,
                }
                if image
                else None
            ),
        }


@contextmanager
def logged_in_client(user_id):
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

        yield client


def request_status(
    client,
    method,
    path,
):
    response = client.open(
        path,
        method=method,
        follow_redirects=False,
    )

    return response.status_code


def status_ok(
    role,
    method,
    path,
    actual,
    expected,
):
    ok = actual in expected

    expected_text = "/".join(
        str(value)
        for value in sorted(expected)
    )

    print(
        f"{role:<8} "
        f"{method:<5} "
        f"{path:<58} "
        f"{actual:<4} "
        f"expected={expected_text:<9} "
        f"{'OK' if ok else 'FAIL'}"
    )

    return ok


def main():
    data = load_test_data()

    users = data["users"]
    item = data["item"]
    location = data["location"]
    stock = data["stock"]
    image = data["image"]

    print()
    print(
        "=== Username's Inventory "
        "jogosultság-audit ==="
    )
    print()

    print(
        "Teszt tétel:",
        item["id"],
        item["name"],
    )

    print(
        "Teszt tárhely:",
        location["id"],
        location["name"],
    )

    if stock:
        print(
            "Teszt készletpozíció:",
            stock["item_id"],
            stock["location_id"],
            stock["quantity"],
        )

    print()

    common_read_paths = [
        "/",
        "/inventory/items",
        (
            f"/inventory/items/"
            f"{item['id']}/stock"
        ),
        "/inventory/locations",
        (
            f"/inventory/locations/"
            f"{location['id']}"
        ),
        "/inventory/scanner",
        "/inventory/stock",
        "/inventory/movements",
        "/inventory/stock/export.csv",
        "/inventory/stock/export.xlsx",
    ]

    editor_paths = [
        (
            f"/inventory/items/"
            f"{item['id']}/receipt"
        ),
        (
            f"/inventory/locations/"
            f"{location['id']}/receipt"
        ),
    ]

    if stock:
        editor_paths.extend(
            [
                (
                    f"/inventory/items/"
                    f"{stock['item_id']}/move/"
                    f"{stock['location_id']}"
                ),
                (
                    f"/inventory/items/"
                    f"{stock['item_id']}/issue/"
                    f"{stock['location_id']}"
                ),
                (
                    f"/inventory/items/"
                    f"{stock['item_id']}/correct/"
                    f"{stock['location_id']}"
                ),
            ]
        )

    admin_read_paths = [
        "/admin/",
        "/admin/item-types",
        "/admin/items",
        "/admin/locations",
        "/admin/users",
        "/admin/items/new",
        "/admin/locations/new",
        "/admin/users/new",
    ]

    failures = 0

    for role in (
        User.ROLE_ADMIN,
        User.ROLE_EDITOR,
        User.ROLE_VIEWER,
    ):
        user = users[role]

        print()
        print(
            f"--- ROLE: {role} "
            f"({user['username']}) ---"
        )

        with logged_in_client(
            user["id"]
        ) as client:
            for path in common_read_paths:
                actual = request_status(
                    client,
                    "GET",
                    path,
                )

                if not status_ok(
                    role,
                    "GET",
                    path,
                    actual,
                    {200},
                ):
                    failures += 1

            for path in editor_paths:
                actual = request_status(
                    client,
                    "GET",
                    path,
                )

                expected = (
                    {200}
                    if role in {
                        User.ROLE_ADMIN,
                        User.ROLE_EDITOR,
                    }
                    else {403}
                )

                if not status_ok(
                    role,
                    "GET",
                    path,
                    actual,
                    expected,
                ):
                    failures += 1

            for path in admin_read_paths:
                actual = request_status(
                    client,
                    "GET",
                    path,
                )

                expected = (
                    {200}
                    if role
                    == User.ROLE_ADMIN
                    else {403}
                )

                if not status_ok(
                    role,
                    "GET",
                    path,
                    actual,
                    expected,
                ):
                    failures += 1

            if image:
                image_path = (
                    f"/inventory/items/"
                    f"{image['item_id']}/images/"
                    f"{image['id']}"
                )

                actual = request_status(
                    client,
                    "GET",
                    image_path,
                )

                # Funkcionálisan ezt minden
                # bejelentkezett usernek látnia
                # kellene.
                expected = {200}

                if not status_ok(
                    role,
                    "GET",
                    image_path,
                    actual,
                    expected,
                ):
                    failures += 1

    print()
    print(
        "--- KIJELENTKEZETT USER ---"
    )

    with app.test_client() as client:
        protected_paths = [
            "/inventory/items",
            "/inventory/stock",
            "/inventory/movements",
            "/inventory/scanner",
            "/admin/",
        ]

        for path in protected_paths:
            actual = request_status(
                client,
                "GET",
                path,
            )

            if not status_ok(
                "anon",
                "GET",
                path,
                actual,
                {302},
            ):
                failures += 1

    print()
    print("=" * 90)

    if failures:
        print(
            f"EREDMÉNY: "
            f"{failures} HIBA / ELTÉRÉS"
        )
    else:
        print(
            "EREDMÉNY: MINDEN TESZT OK"
        )

    print("=" * 90)

    raise SystemExit(
        1 if failures else 0
    )


if __name__ == "__main__":
    main()
