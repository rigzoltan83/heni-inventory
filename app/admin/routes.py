from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from . import admin_bp
from ..extensions import db
from ..models import ItemType


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
