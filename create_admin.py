from getpass import getpass

from app import create_app
from app.extensions import db
from app.models import User


app = create_app()


with app.app_context():
    username = input(
        "Admin felhasználónév: "
    ).strip()

    display_name = input(
        "Megjelenő név: "
    ).strip()

    if not username:
        raise SystemExit(
            "A felhasználónév nem lehet üres."
        )

    if not display_name:
        raise SystemExit(
            "A megjelenő név nem lehet üres."
        )

    existing_user = (
        User.query
        .filter_by(username=username)
        .first()
    )

    if existing_user is not None:
        raise SystemExit(
            "Ez a felhasználónév már létezik."
        )

    password = getpass(
        "Jelszó: "
    )

    password_again = getpass(
        "Jelszó még egyszer: "
    )

    if password != password_again:
        raise SystemExit(
            "A két jelszó nem egyezik."
        )

    if len(password) < 8:
        raise SystemExit(
            "A jelszó legalább 8 karakter legyen."
        )

    user = User(
        username=username,
        display_name=display_name,
        role=User.ROLE_ADMIN,
        is_enabled=True,
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    print()
    print(
        f"Admin létrehozva: "
        f"{user.username} "
        f"(id={user.id})"
    )
