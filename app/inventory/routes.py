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

from urllib.parse import urlparse
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
    ItemIdentifier,
    Location,
)
from ..permissions import editor_required

def get_safe_return_to(default_url):
    return_to = (
        request.args.get(
            "return_to",
            "",
        )
        .strip()
    )

    if not return_to:
        return default_url

    parsed = urlparse(return_to)

    if parsed.scheme or parsed.netloc:
        return default_url

    if not return_to.startswith("/"):
        return default_url

    return return_to


@inventory_bp.route("/items")
@login_required
def items():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    has_stock = (
        request.args.get("has_stock")
        == "1"
    )

    query = (
        db.session.query(
            Item,
            db.func.coalesce(
                db.func.sum(
                    InventoryStock.quantity
                ),
                0,
            ).label("total_quantity"),
        )
        .outerjoin(
            InventoryStock,
            InventoryStock.item_id == Item.id,
        )
        .filter(
            Item.is_active.is_(True)
        )
        .group_by(Item.id)
    )

    if search:
        query = query.filter(
            Item.name.ilike(
                f"%{search}%"
            )
        )

    if has_stock:
        query = query.having(
            db.func.coalesce(
                db.func.sum(
                    InventoryStock.quantity
                ),
                0,
            )
            > 0
        )

    rows = (
        query
        .order_by(Item.name)
        .all()
    )

    return render_template(
        "inventory/items/list.html",
        rows=rows,
        search=search,
        has_stock=has_stock,
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

    default_back_url = url_for(
        "inventory.items"
    )

    back_url = get_safe_return_to(
        default_back_url
    )

    if back_url != default_back_url:
        current_url = url_for(
            "inventory.item_stock",
            item_id=item.id,
            return_to=back_url,
        )
    else:
        current_url = url_for(
            "inventory.item_stock",
            item_id=item.id,
        )

    return render_template(
        "inventory/items/stock.html",
        item=item,
        positions=positions,
        total_quantity=total_quantity,
        back_url=back_url,
        current_url=current_url,
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

    return_to = get_safe_return_to(
        url_for(
            "inventory.item_stock",
            item_id=item.id,
        )
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

            return redirect(return_to)

        except InventoryError as exc:
            flash(
                str(exc),
                "error",
            )

    return render_template(
        "inventory/items/receipt.html",
        item=item,
        locations=locations,
        back_url=return_to,
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

    return_to = get_safe_return_to(
        url_for(
            "inventory.item_stock",
            item_id=item.id,
        )
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

            return redirect(return_to)

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
        back_url=return_to,
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

    return_to = get_safe_return_to(
        url_for(
            "inventory.item_stock",
            item_id=item.id,
        )
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

            return redirect(return_to)

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
        back_url=return_to,
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

    return_to = get_safe_return_to(
        url_for(
            "inventory.item_stock",
            item_id=item.id,
        )
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

            return redirect(return_to)

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
        back_url=return_to,
    )

@inventory_bp.route("/locations")
@login_required
def locations():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    has_stock = (
        request.args.get("has_stock")
        == "1"
    )

    query = (
        db.session.query(
            Location,
            db.func.coalesce(
                db.func.sum(
                    InventoryStock.quantity
                ),
                0,
            ).label("total_quantity"),
            db.func.count(
                db.distinct(
                    InventoryStock.item_id
                )
            ).label("item_count"),
        )
        .outerjoin(
            InventoryStock,
            InventoryStock.location_id
            == Location.id,
        )
        .filter(
            Location.is_active.is_(True),
            Location.can_hold_stock.is_(True),
        )
        .group_by(Location.id)
    )

    if search:
        query = query.filter(
            Location.name.ilike(
                f"%{search}%"
            )
        )

    if has_stock:
        query = query.having(
            db.func.coalesce(
                db.func.sum(
                    InventoryStock.quantity
                ),
                0,
            )
            > 0
        )

    rows = (
        query
        .order_by(
            Location.name
        )
        .all()
    )

    return render_template(
        "inventory/locations/list.html",
        rows=rows,
        search=search,
        has_stock=has_stock,
        back_url=url_for("main.index"),
    )


@inventory_bp.route(
    "/locations/<int:location_id>"
)
@login_required
def location_stock(location_id):
    location = db.get_or_404(
        Location,
        location_id,
    )

    positions = (
        InventoryStock.query
        .filter(
            InventoryStock.location_id
            == location.id,
            InventoryStock.quantity > 0,
        )
        .join(Item)
        .order_by(
            Item.name
        )
        .all()
    )

    total_quantity = sum(
        position.quantity
        for position in positions
    )

    default_back_url = url_for(
        "inventory.locations"
    )

    back_url = get_safe_return_to(
        default_back_url
    )

    current_url = url_for(
        "inventory.location_stock",
        location_id=location.id,
    )

    return render_template(
        "inventory/locations/stock.html",
        location=location,
        positions=positions,
        total_quantity=total_quantity,
        back_url=back_url,
        current_url=current_url,
    )

@inventory_bp.route(
    "/locations/<int:location_id>/receipt",
    methods=["GET", "POST"],
)
@editor_required
def location_receipt(location_id):
    location = db.get_or_404(
        Location,
        location_id,
    )

    return_to = get_safe_return_to(
        url_for(
            "inventory.location_stock",
            location_id=location.id,
        )
    )

    if not location.is_active:
        flash(
            "Inaktív tárhely nem használható.",
            "error",
        )

        return redirect(return_to)

    if not location.can_hold_stock:
        flash(
            "Ezen a helyen nem tárolható készlet.",
            "error",
        )

        return redirect(
            url_for(
                "inventory.location_stock",
                location_id=location.id,
            )
        )

    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    query = (
        Item.query
        .filter(
            Item.is_active.is_(True)
        )
    )

    if search:
        query = query.filter(
            Item.name.ilike(
                f"%{search}%"
            )
        )

    items = (
        query
        .order_by(
            Item.name
        )
        .all()
    )

    if request.method == "POST":
        item_id = request.form.get(
            "item_id",
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
                item_id=item_id,
                location_id=location.id,
                quantity=quantity,
                user_id=current_user.id,
                note=note,
            )

            flash(
                "A készletfelvitel megtörtént.",
                "success",
            )

            return redirect(
                url_for(
                    "inventory.location_stock",
                    location_id=location.id,
                )
            )

        except InventoryError as exc:
            flash(
                str(exc),
                "error",
            )

    return render_template(
        "inventory/locations/receipt.html",
        location=location,
        items=items,
        search=search,
        back_url=return_to,
    )

@inventory_bp.route(
    "/scanner",
    methods=["GET", "POST"],
)
@login_required
def scanner():
    code = ""

    scanner_url = url_for(
        "inventory.scanner"
    )

    if request.method == "POST":
        code = (
            request.form.get(
                "code",
                "",
            )
            .strip()
        )

        if not code:
            flash(
                "Adj meg vagy olvass be egy kódot.",
                "error",
            )

            return render_template(
                "inventory/scanner.html",
                code=code,
                back_url=url_for("main.index"),
            )

        normalized = code.upper()

        if normalized.startswith("ITEM-"):
            try:
                item_id = int(
                    normalized.removeprefix(
                        "ITEM-"
                    )
                )
            except ValueError:
                item_id = None

            if item_id is not None:
                item = db.session.get(
                    Item,
                    item_id,
                )

                if (
                    item is not None
                    and item.is_active
                ):
                    return redirect(
                        url_for(
                            "inventory.item_stock",
                            item_id=item.id,
                            return_to=scanner_url,
                        )
                    )

        if normalized.startswith("LOC-"):
            try:
                location_id = int(
                    normalized.removeprefix(
                        "LOC-"
                    )
                )
            except ValueError:
                location_id = None

            if location_id is not None:
                location = db.session.get(
                    Location,
                    location_id,
                )

                if (
                    location is not None
                    and location.is_active
                    and location.can_hold_stock
                ):
                    return redirect(
                        url_for(
                            "inventory.location_stock",
                            location_id=location.id,
                            return_to=scanner_url,
                        )
                    )

        identifier = (
            ItemIdentifier.query
            .filter(
                ItemIdentifier.identifier_value
                == code,
                ItemIdentifier.is_active.is_(True),
            )
            .first()
        )

        if (
            identifier is not None
            and identifier.item.is_active
        ):
            return redirect(
                url_for(
                    "inventory.item_stock",
                    item_id=identifier.item.id,
                    return_to=scanner_url,
                )
            )

        flash(
            f"Ismeretlen kód: {code}",
            "error",
        )

    return render_template(
        "inventory/scanner.html",
        code=code,
        back_url=url_for("main.index"),
    )
