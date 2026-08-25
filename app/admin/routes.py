from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from . import admin_bp
from ..extensions import db
from ..models import ItemType, User


@admin_bp.route("/")
def index():
    return render_template(
        "admin/index.html",
        back_url=url_for("main.index"),
    )


@admin_bp.route("/item-types")
def item_types():
    rows = (
        ItemType.query
        .order_by(
            ItemType.sort_order,
            ItemType.name,
        )
        .all()
    )

    return render_template(
        "admin/item_types/list.html",
        item_types=rows,
    back_url=url_for("admin.index"),
    )


@admin_bp.route(
    "/item-types/new",
    methods=["GET", "POST"],
)
def item_type_new():
    if request.method == "POST":
        code = (
            request.form.get("code", "")
            .strip()
            .upper()
        )

        name = (
            request.form.get("name", "")
            .strip()
        )

        sort_order_raw = (
            request.form.get(
                "sort_order",
                "0",
            )
            .strip()
        )

        if not code:
            flash(
                "A kód megadása kötelező.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=None,
                back_url=url_for("admin.item_types"),
            )

        if not name:
            flash(
                "A megnevezés megadása kötelező.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=None,
                back_url=url_for("admin.item_types"),
            )

        try:
            sort_order = int(
                sort_order_raw or 0
            )
        except ValueError:
            flash(
                "A sorrend csak egész szám lehet.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=None,
                back_url=url_for("admin.item_types"),
            )

        existing = (
            ItemType.query
            .filter_by(code=code)
            .first()
        )

        if existing is not None:
            flash(
                "Ez a tételtípus-kód már létezik.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=None,
                back_url=url_for("admin.item_types"),
            )

        item_type = ItemType(
            code=code,
            name=name,
            sort_order=sort_order,
            is_active=True,
        )

        db.session.add(item_type)
        db.session.commit()

        flash(
            "A tételtípus létrejött.",
            "success",
        )

        return redirect(
            url_for(
                "admin.item_types"
            )
        )

    return render_template(
        "admin/item_types/form.html",
        item_type=None,
        back_url=url_for("admin.item_types"),
    )


@admin_bp.route(
    "/item-types/<int:item_type_id>/edit",
    methods=["GET", "POST"],
)
def item_type_edit(item_type_id):
    item_type = db.get_or_404(
        ItemType,
        item_type_id,
    )

    if request.method == "POST":
        code = (
            request.form.get("code", "")
            .strip()
            .upper()
        )

        name = (
            request.form.get("name", "")
            .strip()
        )

        sort_order_raw = (
            request.form.get(
                "sort_order",
                "0",
            )
            .strip()
        )

        if not code or not name:
            flash(
                "A kód és a megnevezés kötelező.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=item_type,
                back_url=url_for("admin.item_types"),
            )

        try:
            sort_order = int(
                sort_order_raw or 0
            )
        except ValueError:
            flash(
                "A sorrend csak egész szám lehet.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=item_type,
                back_url=url_for("admin.item_types"),
            )

        duplicate = (
            ItemType.query
            .filter(
                ItemType.code == code,
                ItemType.id != item_type.id,
            )
            .first()
        )

        if duplicate is not None:
            flash(
                "Ez a tételtípus-kód már létezik.",
                "error",
            )

            return render_template(
                "admin/item_types/form.html",
                item_type=item_type,
                back_url=url_for("admin.item_types"),
            )

        item_type.code = code
        item_type.name = name
        item_type.sort_order = sort_order

        db.session.commit()

        flash(
            "A tételtípus módosítva.",
            "success",
        )

        return redirect(
            url_for(
                "admin.item_types"
            )
        )

    return render_template(
        "admin/item_types/form.html",
        item_type=item_type,
        back_url=url_for("admin.item_types"),
    )


@admin_bp.route(
    "/item-types/<int:item_type_id>/toggle",
    methods=["POST"],
)
def item_type_toggle(item_type_id):
    item_type = db.get_or_404(
        ItemType,
        item_type_id,
    )

    item_type.is_active = (
        not item_type.is_active
    )

    db.session.commit()

    if item_type.is_active:
        message = (
            "A tételtípus aktiválva."
        )
    else:
        message = (
            "A tételtípus inaktiválva."
        )

    flash(
        message,
        "success",
    )

    return redirect(
        url_for(
            "admin.item_types"
        )
    )

@admin_bp.route("/users")
def users():
    rows = (
        User.query
        .order_by(
            User.username,
        )
        .all()
    )

    return render_template(
        "admin/users/list.html",
        users=rows,
        back_url=url_for("admin.index"),
    )


@admin_bp.route(
    "/users/new",
    methods=["GET", "POST"],
)
def user_new():
    if request.method == "POST":
        username = (
            request.form.get("username", "")
            .strip()
        )

        display_name = (
            request.form.get("display_name", "")
            .strip()
        )

        role = (
            request.form.get("role", "")
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        password_again = request.form.get(
            "password_again",
            "",
        )

        if not username:
            flash(
                "A felhasználónév kötelező.",
                "error",
            )
        elif not display_name:
            flash(
                "A megjelenő név kötelező.",
                "error",
            )
        elif role not in User.VALID_ROLES:
            flash(
                "Érvénytelen szerepkör.",
                "error",
            )
        elif len(password) < 8:
            flash(
                "A jelszó legalább 8 karakter legyen.",
                "error",
            )
        elif password != password_again:
            flash(
                "A két jelszó nem egyezik.",
                "error",
            )
        elif (
            User.query
            .filter_by(username=username)
            .first()
            is not None
        ):
            flash(
                "Ez a felhasználónév már létezik.",
                "error",
            )
        else:
            user = User(
                username=username,
                display_name=display_name,
                role=role,
                is_enabled=True,
            )

            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash(
                "A felhasználó létrejött.",
                "success",
            )

            return redirect(
                url_for("admin.users")
            )

    return render_template(
        "admin/users/form.html",
        user=None,
        roles=[
            ("admin", "Admin"),
            ("editor", "Editor"),
            ("viewer", "Viewer"),
        ],
        back_url=url_for("admin.users"),
    )


@admin_bp.route(
    "/users/<int:user_id>/edit",
    methods=["GET", "POST"],
)
def user_edit(user_id):
    user = db.get_or_404(
        User,
        user_id,
    )

    if request.method == "POST":
        username = (
            request.form.get("username", "")
            .strip()
        )

        display_name = (
            request.form.get("display_name", "")
            .strip()
        )

        role = (
            request.form.get("role", "")
            .strip()
        )

        duplicate = (
            User.query
            .filter(
                User.username == username,
                User.id != user.id,
            )
            .first()
        )

        if not username:
            flash(
                "A felhasználónév kötelező.",
                "error",
            )
        elif not display_name:
            flash(
                "A megjelenő név kötelező.",
                "error",
            )
        elif role not in User.VALID_ROLES:
            flash(
                "Érvénytelen szerepkör.",
                "error",
            )
        elif duplicate is not None:
            flash(
                "Ez a felhasználónév már létezik.",
                "error",
            )
        else:
            user.username = username
            user.display_name = display_name
            user.role = role

            db.session.commit()

            flash(
                "A felhasználó módosítva.",
                "success",
            )

            return redirect(
                url_for("admin.users")
            )

    return render_template(
        "admin/users/form.html",
        user=user,
        roles=[
            ("admin", "Admin"),
            ("editor", "Editor"),
            ("viewer", "Viewer"),
        ],
        back_url=url_for("admin.users"),
    )


@admin_bp.route(
    "/users/<int:user_id>/toggle",
    methods=["POST"],
)
def user_toggle(user_id):
    from flask_login import current_user

    user = db.get_or_404(
        User,
        user_id,
    )

    if user.id == current_user.id:
        flash(
            "A saját felhasználódat nem inaktiválhatod.",
            "error",
        )

        return redirect(
            url_for("admin.users")
        )

    user.is_enabled = (
        not user.is_enabled
    )

    db.session.commit()

    flash(
        (
            "A felhasználó aktiválva."
            if user.is_enabled
            else "A felhasználó inaktiválva."
        ),
        "success",
    )

    return redirect(
        url_for("admin.users")
    )


@admin_bp.route(
    "/users/<int:user_id>/password",
    methods=["GET", "POST"],
)
def user_password(user_id):
    user = db.get_or_404(
        User,
        user_id,
    )

    if request.method == "POST":
        password = request.form.get(
            "password",
            "",
        )

        password_again = request.form.get(
            "password_again",
            "",
        )

        if len(password) < 8:
            flash(
                "A jelszó legalább 8 karakter legyen.",
                "error",
            )
        elif password != password_again:
            flash(
                "A két jelszó nem egyezik.",
                "error",
            )
        else:
            user.set_password(password)
            db.session.commit()

            flash(
                "A jelszó módosítva.",
                "success",
            )

            return redirect(
                url_for("admin.users")
            )

    return render_template(
        "admin/users/password.html",
        user=user,
        back_url=url_for("admin.users"),
    )
