from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
)

from . import inventory_bp
from ..extensions import db
from ..inventory_service import (
    InventoryError,
    issue,
    move,
    receipt,
    set_counted_quantity,
)
from ..models import (
    InventoryStock,
    Item,
    Location,
)
from ..permissions import editor_required


@inventory_bp.route("/items")
@login_required
def items():
    rows = (
        Item.query
        .filter_by(is_active=True)
        .order_by(Item.name)
        .all()
    )

    return render_template(
        "inventory/items/list.html",
        items=rows,
        back_url=url_for("main.index"),
    )


@inventory_bp.route(
    "/items/<int:item_id>/stock"
)
@login_required
def item_stock(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    positions = (
        InventoryStock.query
        .filter(
            InventoryStock.item_id == item.id,
            InventoryStock.quantity > 0,
        )
        .join(Location)
        .order_by(
            Location.name,
        )
        .all()
    )

    total_quantity = sum(
        row.quantity
        for row in positions
    )

    return render_template(
        "inventory/items/stock.html",
        item=item,
        positions=positions,
        total_quantity=total_quantity,
        back_url=url_for("main.index"),
    )


@inventory_bp.route(
    "/items/<int:item_id>/receipt",
    methods=["GET", "POST"],
)
@editor_required
def item_receipt(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    locations = (
        Location.query
        .filter_by(
            is_active=True,
            can_hold_stock=True,
        )
        .order_by(Location.name)
        .all()
    )

    if request.method == "POST":
        location_id = request.form.get(
            "location_id",
            type=int,
        )

        quantity = request.form.get(
            "quantity"
        )

        note = (
            request.form.get(
                "note",
                "",
            )
            .strip()
        )

        try:
            receipt(
                item_id=item.id,
                location_id=location_id,
                quantity=quantity,
                user_id=current_user.id,
                note=note,
            )

            flash(
                "A bevételezés megtörtént.",
                "success",
            )

            return redirect(
                url_for(
                    "inventory.item_stock",
                    item_id=item.id,
                )
            )

        except InventoryError as exc:
            flash(
                str(exc),
                "error",
            )

    return render_template(
        "inventory/items/receipt.html",
        item=item,
        locations=locations,
        back_url=url_for(
            "inventory.item_stock",
            item_id=item.id,
        ),
    )


@inventory_bp.route(
    "/items/<int:item_id>/move/<int:from_location_id>",
    methods=["GET", "POST"],
)
@editor_required
def item_move(
    item_id,
    from_location_id,
):
    item = db.get_or_404(
        Item,
        item_id,
    )

    source = db.get_or_404(
        Location,
        from_location_id,
    )

    stock = (
        InventoryStock.query
        .filter_by(
            item_id=item.id,
            location_id=source.id,
        )
        .first_or_404()
    )

    destinations = (
        Location.query
        .filter(
            Location.is_active.is_(True),
            Location.can_hold_stock.is_(True),
            Location.id != source.id,
        )
        .order_by(Location.name)
        .all()
    )

    if request.method == "POST":
        destination_id = request.form.get(
            "destination_id",
            type=int,
        )

        quantity = request.form.get(
            "quantity"
        )

        note = (
            request.form.get(
                "note",
                "",
            )
            .strip()
        )

        try:
            move(
                item_id=item.id,
                from_location_id=source.id,
                to_location_id=destination_id,
                quantity=quantity,
                user_id=current_user.id,
                note=note,
            )

            flash(
                "Az áthelyezés megtörtént.",
                "success",
            )

            return redirect(
                url_for(
                    "inventory.item_stock",
                    item_id=item.id,
                )
            )

        except InventoryError as exc:
            flash(
                str(exc),
                "error",
            )

    return render_template(
        "inventory/items/move.html",
        item=item,
        source=source,
        stock=stock,
        destinations=destinations,
        back_url=url_for(
            "inventory.item_stock",
            item_id=item.id,
        ),
    )


@inventory_bp.route(
    "/items/<int:item_id>/issue/<int:location_id>",
    methods=["GET", "POST"],
)
@editor_required
def item_issue(
    item_id,
    location_id,
):
    item = db.get_or_404(
        Item,
        item_id,
    )

    location = db.get_or_404(
        Location,
        location_id,
    )

    stock = (
        InventoryStock.query
        .filter_by(
            item_id=item.id,
            location_id=location.id,
        )
        .first_or_404()
    )

    if request.method == "POST":
        quantity = request.form.get(
            "quantity"
        )

        note = (
            request.form.get(
                "note",
                "",
            )
            .strip()
        )

        try:
            issue(
                item_id=item.id,
                location_id=location.id,
                quantity=quantity,
                user_id=current_user.id,
                note=note,
            )

            flash(
                "A kiadás megtörtént.",
                "success",
            )

            return redirect(
                url_for(
                    "inventory.item_stock",
                    item_id=item.id,
                )
            )

        except InventoryError as exc:
            flash(
                str(exc),
                "error",
            )

    return render_template(
        "inventory/items/issue.html",
        item=item,
        location=location,
        stock=stock,
        back_url=url_for(
            "inventory.item_stock",
            item_id=item.id,
        ),
    )


@inventory_bp.route(
    "/items/<int:item_id>/correct/<int:location_id>",
    methods=["GET", "POST"],
)
@editor_required
def item_correct(
    item_id,
    location_id,
):
    item = db.get_or_404(
        Item,
        item_id,
    )

    location = db.get_or_404(
        Location,
        location_id,
    )

    stock = (
        InventoryStock.query
        .filter_by(
            item_id=item.id,
            location_id=location.id,
        )
        .first_or_404()
    )

    if request.method == "POST":
        counted_quantity = request.form.get(
            "counted_quantity"
        )

        note = (
            request.form.get(
                "note",
                "",
            )
            .strip()
        )

        try:
            set_counted_quantity(
                item_id=item.id,
                location_id=location.id,
                counted_quantity=counted_quantity,
                user_id=current_user.id,
                note=note,
            )

            flash(
                "A készletkorrekció megtörtént.",
                "success",
            )

            return redirect(
                url_for(
                    "inventory.item_stock",
                    item_id=item.id,
                )
            )

        except InventoryError as exc:
            flash(
                str(exc),
                "error",
            )

    return render_template(
        "inventory/items/correct.html",
        item=item,
        location=location,
        stock=stock,
        back_url=url_for(
            "inventory.item_stock",
            item_id=item.id,
        ),
    )
