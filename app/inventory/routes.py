from flask import (
    abort,
    current_app,
    send_from_directory,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext as _
from flask_login import (
    current_user,
    login_required,
)

import csv
from io import BytesIO, StringIO

import xlsxwriter
from datetime import datetime, time
from sqlalchemy import or_
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
    InventoryMovement,
    InventoryStock,
    Item,
    ItemIdentifier,
    ItemImage,
    Location,
    User,
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

    if return_to.endswith("?"):
        return_to = return_to[:-1]

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


def build_stock_query(
    search="",
    location_id=None,
):
    query = (
        InventoryStock.query
        .join(Item)
        .join(Location)
        .filter(
            InventoryStock.quantity > 0,
            Item.is_active.is_(True),
            Location.is_active.is_(True),
        )
    )

    if search:
        query = query.filter(
            or_(
                Item.name.ilike(
                    f"%{search}%"
                ),
                Location.name.ilike(
                    f"%{search}%"
                ),
            )
        )

    if location_id is not None:
        query = query.filter(
            InventoryStock.location_id
            == location_id
        )

    return query


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
                _("A bevételezés megtörtént."),
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
                _("Az áthelyezés megtörtént."),
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
                _("A kiadás megtörtént."),
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
                _("A készletkorrekció megtörtént."),
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
            _("Inaktív tárhely nem használható."),
            "error",
        )

        return redirect(return_to)

    if not location.can_hold_stock:
        flash(
            _("Ezen a helyen nem tárolható készlet."),
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
                _("A készletfelvitel megtörtént."),
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
                _("Adj meg vagy olvass be egy kódot."),
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
            _("Ismeretlen kód: %(code)s", code=code),
            "error",
        )

    return render_template(
        "inventory/scanner.html",
        code=code,
        back_url=url_for("main.index"),
    )


@inventory_bp.route("/stock/export.csv")
@login_required
def stock_export_csv():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    location_id = request.args.get(
        "location_id",
        type=int,
    )

    rows = (
        build_stock_query(
            search=search,
            location_id=location_id,
        )
        .order_by(
            Item.name,
            Location.name,
        )
        .all()
    )

    output = StringIO()

    writer = csv.writer(
        output,
        delimiter=";",
        lineterminator="\n",
    )

    writer.writerow(
        [
            _("Tétel"),
            _("Saját kód"),
            _("Típus"),
            _("Tárhely"),
            _("Tárhelykód"),
            _("Mennyiség"),
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row.item.name,
                row.item.internal_code,
                row.item.item_type.name,
                row.location.full_path,
                row.location.internal_code,
                row.quantity,
            ]
        )

    csv_content = (
        "\ufeff"
        + output.getvalue()
    )

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                'attachment; filename="heni_inventory_stock.csv"'
        },
    )


@inventory_bp.route("/stock/export.xlsx")
@login_required
def stock_export_xlsx():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    location_id = request.args.get(
        "location_id",
        type=int,
    )

    rows = (
        build_stock_query(
            search=search,
            location_id=location_id,
        )
        .order_by(
            Item.name,
            Location.name,
        )
        .all()
    )

    output = BytesIO()

    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
        },
    )

    worksheet = workbook.add_worksheet(
        _("Készlet")
    )

    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#E5E7EB",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    text_format = workbook.add_format(
        {
            "border": 1,
            "valign": "top",
        }
    )

    quantity_format = workbook.add_format(
        {
            "border": 1,
            "align": "right",
            "num_format": "0",
        }
    )

    headers = [
        _("Tétel"),
        _("Saját kód"),
        _("Típus"),
        _("Tárhely"),
        _("Tárhelykód"),
        _("Mennyiség"),
    ]

    for column, header in enumerate(
        headers
    ):
        worksheet.write(
            0,
            column,
            header,
            header_format,
        )

    for row_number, stock_row in enumerate(
        rows,
        start=1,
    ):
        worksheet.write(
            row_number,
            0,
            stock_row.item.name,
            text_format,
        )

        worksheet.write(
            row_number,
            1,
            stock_row.item.internal_code,
            text_format,
        )

        worksheet.write(
            row_number,
            2,
            stock_row.item.item_type.name,
            text_format,
        )

        worksheet.write(
            row_number,
            3,
            stock_row.location.full_path,
            text_format,
        )

        worksheet.write(
            row_number,
            4,
            stock_row.location.internal_code,
            text_format,
        )

        worksheet.write_number(
            row_number,
            5,
            stock_row.quantity,
            quantity_format,
        )

    last_row = max(
        len(rows),
        1,
    )

    worksheet.autofilter(
        0,
        0,
        last_row,
        len(headers) - 1,
    )

    worksheet.freeze_panes(
        1,
        0,
    )

    worksheet.set_column(
        0,
        0,
        32,
    )

    worksheet.set_column(
        1,
        1,
        16,
    )

    worksheet.set_column(
        2,
        2,
        18,
    )

    worksheet.set_column(
        3,
        3,
        42,
    )

    worksheet.set_column(
        4,
        4,
        16,
    )

    worksheet.set_column(
        5,
        5,
        12,
    )

    workbook.close()

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="heni_inventory_stock.xlsx"'
        },
    )


@inventory_bp.route("/stock")
@login_required
def stock():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    location_id = request.args.get(
        "location_id",
        type=int,
    )

    query = build_stock_query(
        search=search,
        location_id=location_id,
    )

    if search:
        query = query.filter(
            or_(
                Item.name.ilike(
                    f"%{search}%"
                ),
                Location.name.ilike(
                    f"%{search}%"
                ),
            )
        )

    if location_id is not None:
        query = query.filter(
            InventoryStock.location_id
            == location_id
        )

    rows = (
        query
        .order_by(
            Item.name,
            Location.name,
        )
        .all()
    )

    locations = (
        Location.query
        .filter(
            Location.is_active.is_(True),
            Location.can_hold_stock.is_(True),
        )
        .order_by(
            Location.name
        )
        .all()
    )

    total_quantity = sum(
        row.quantity
        for row in rows
    )

    return render_template(
        "inventory/stock/list.html",
        rows=rows,
        locations=locations,
        search=search,
        selected_location_id=location_id,
        total_quantity=total_quantity,
        back_url=url_for("main.index"),
    )

MOVEMENT_TYPE_LABELS = {
    InventoryMovement.TYPE_RECEIPT:
        "Bevételezés",

    InventoryMovement.TYPE_MOVE:
        "Áthelyezés",

    InventoryMovement.TYPE_ISSUE:
        "Kiadás",

    InventoryMovement.TYPE_CORRECTION_PLUS:
        "Korrekció +",

    InventoryMovement.TYPE_CORRECTION_MINUS:
        "Korrekció −",
}



def _movement_translation_markers():
    return (
        _("Bevételezés"),
        _("Áthelyezés"),
        _("Kiadás"),
        _("Korrekció +"),
        _("Korrekció −"),
    )

def movement_type_display(
    movement_type,
):
    label = MOVEMENT_TYPE_LABELS.get(
        movement_type
    )

    if not label:
        return movement_type

    label = _(label)

    return (
        f"{movement_type} "
        f"({label})"
    )

def build_movement_query(
    search="",
    movement_type="",
    location_id=None,
    user_id=None,
    date_from=None,
    date_to=None,
):
    query = (
        InventoryMovement.query
        .join(Item)
    )

    if search:
        query = query.filter(
            Item.name.ilike(
                f"%{search}%"
            )
        )

    if (
        movement_type
        in InventoryMovement.VALID_TYPES
    ):
        query = query.filter(
            InventoryMovement.movement_type
            == movement_type
        )

    if location_id is not None:
        query = query.filter(
            or_(
                InventoryMovement.from_location_id
                == location_id,
                InventoryMovement.to_location_id
                == location_id,
            )
        )

    if user_id is not None:
        query = query.filter(
            InventoryMovement.created_by_user_id
            == user_id
        )

    if date_from is not None:
        query = query.filter(
            InventoryMovement.created_at
            >= date_from
        )

    if date_to is not None:
        query = query.filter(
            InventoryMovement.created_at
            <= date_to
        )

    return query


@inventory_bp.route("/movements")
@login_required
def movements():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    movement_type = (
        request.args.get(
            "movement_type",
            "",
        )
        .strip()
    )

    location_id = request.args.get(
        "location_id",
        type=int,
    )

    user_id = request.args.get(
        "user_id",
        type=int,
    )

    date_from_raw = (
        request.args.get(
            "date_from",
            "",
        )
        .strip()
    )

    date_to_raw = (
        request.args.get(
            "date_to",
            "",
        )
        .strip()
    )

    page = request.args.get(
        "page",
        default=1,
        type=int,
    )

    if page < 1:
        page = 1

    if (
        movement_type
        not in InventoryMovement.VALID_TYPES
    ):
        movement_type = ""

    date_from = None

    if date_from_raw:
        try:
            date_from = datetime.strptime(
                date_from_raw,
                "%Y-%m-%d",
            )
        except ValueError:
            date_from_raw = ""

    date_to = None

    if date_to_raw:
        try:
            parsed_date_to = datetime.strptime(
                date_to_raw,
                "%Y-%m-%d",
            ).date()

            date_to = datetime.combine(
                parsed_date_to,
                time.max,
            )

        except ValueError:
            date_to_raw = ""

    query = build_movement_query(
        search=search,
        movement_type=movement_type,
        location_id=location_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    per_page = 50

    total_rows = query.count()

    total_pages = max(
        1,
        (
            total_rows
            + per_page
            - 1
        )
        // per_page
    )

    if page > total_pages:
        page = total_pages

    rows = (
        query
        .order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        )
        .offset(
            (page - 1) * per_page
        )
        .limit(per_page)
        .all()
    )

    movement_types = [
        (
            value,
            _(label),
        )
        for value, label
        in MOVEMENT_TYPE_LABELS.items()
    ]

    locations = (
        Location.query
        .filter(
            Location.is_active.is_(True),
            Location.can_hold_stock.is_(True),
        )
        .order_by(
            Location.name
        )
        .all()
    )

    users = (
        User.query
        .filter(
            User.is_enabled.is_(True)
        )
        .order_by(
            User.display_name
        )
        .all()
    )

    return_url = url_for(
        "inventory.movements",
        q=search or None,
        movement_type=movement_type or None,
        location_id=location_id,
        user_id=user_id,
        date_from=date_from_raw or None,
        date_to=date_to_raw or None,
        page=page,
    )

    return render_template(
        "inventory/movements/list.html",
        rows=rows,
        search=search,
        movement_type=movement_type,
        movement_types=movement_types,
        movement_type_display=movement_type_display,
        locations=locations,
        users=users,
        selected_location_id=location_id,
        selected_user_id=user_id,
        date_from=date_from_raw,
        date_to=date_to_raw,
        page=page,
        total_pages=total_pages,
        total_rows=total_rows,
        return_url=return_url,
        back_url=url_for("main.index"),
    )


@inventory_bp.route(
    "/movements/export.csv"
)
@login_required
def movements_export_csv():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    movement_type = (
        request.args.get(
            "movement_type",
            "",
        )
        .strip()
    )

    location_id = request.args.get(
        "location_id",
        type=int,
    )

    user_id = request.args.get(
        "user_id",
        type=int,
    )

    date_from_raw = (
        request.args.get(
            "date_from",
            "",
        )
        .strip()
    )

    date_to_raw = (
        request.args.get(
            "date_to",
            "",
        )
        .strip()
    )

    date_from = None

    if date_from_raw:
        try:
            date_from = datetime.strptime(
                date_from_raw,
                "%Y-%m-%d",
            )
        except ValueError:
            date_from = None

    date_to = None

    if date_to_raw:
        try:
            parsed_date_to = datetime.strptime(
                date_to_raw,
                "%Y-%m-%d",
            ).date()

            date_to = datetime.combine(
                parsed_date_to,
                time.max,
            )
        except ValueError:
            date_to = None

    if (
        movement_type
        not in InventoryMovement.VALID_TYPES
    ):
        movement_type = ""

    rows = (
        build_movement_query(
            search=search,
            movement_type=movement_type,
            location_id=location_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        .order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        )
        .all()
    )

    output = StringIO()

    writer = csv.writer(
        output,
        delimiter=";",
        lineterminator="\n",
    )

    writer.writerow(
        [
            _("Időpont"),
            _("Tétel"),
            _("Saját kód"),
            _("Mozgástípus"),
            _("Honnan"),
            _("Hova"),
            _("Mennyiség"),
            _("Felhasználó"),
            _("Megjegyzés"),
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                row.item.name,
                row.item.internal_code,
                movement_type_display(
                    row.movement_type
                ),
                (
                    row.from_location.full_path
                    if row.from_location
                    else ""
                ),
                (
                    row.to_location.full_path
                    if row.to_location
                    else ""
                ),
                row.quantity,
                (
                    row.created_by.display_name
                    if row.created_by
                    else ""
                ),
                row.note or "",
            ]
        )

    csv_content = (
        "\ufeff"
        + output.getvalue()
    )

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                'attachment; filename="heni_inventory_movements.csv"'
        },
    )


@inventory_bp.route(
    "/movements/export.xlsx"
)
@login_required
def movements_export_xlsx():
    search = (
        request.args.get(
            "q",
            "",
        )
        .strip()
    )

    movement_type = (
        request.args.get(
            "movement_type",
            "",
        )
        .strip()
    )

    location_id = request.args.get(
        "location_id",
        type=int,
    )

    user_id = request.args.get(
        "user_id",
        type=int,
    )

    date_from_raw = (
        request.args.get(
            "date_from",
            "",
        )
        .strip()
    )

    date_to_raw = (
        request.args.get(
            "date_to",
            "",
        )
        .strip()
    )

    date_from = None

    if date_from_raw:
        try:
            date_from = datetime.strptime(
                date_from_raw,
                "%Y-%m-%d",
            )
        except ValueError:
            date_from = None

    date_to = None

    if date_to_raw:
        try:
            parsed_date_to = datetime.strptime(
                date_to_raw,
                "%Y-%m-%d",
            ).date()

            date_to = datetime.combine(
                parsed_date_to,
                time.max,
            )
        except ValueError:
            date_to = None

    if (
        movement_type
        not in InventoryMovement.VALID_TYPES
    ):
        movement_type = ""

    rows = (
        build_movement_query(
            search=search,
            movement_type=movement_type,
            location_id=location_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        .order_by(
            InventoryMovement.created_at.desc(),
            InventoryMovement.id.desc(),
        )
        .all()
    )

    output = BytesIO()

    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
        },
    )

    worksheet = workbook.add_worksheet(
        _("Mozgások")
    )

    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#E5E7EB",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    text_format = workbook.add_format(
        {
            "border": 1,
            "valign": "top",
        }
    )

    quantity_format = workbook.add_format(
        {
            "border": 1,
            "align": "right",
            "num_format": "0",
        }
    )

    headers = [
        _("Időpont"),
        _("Tétel"),
        _("Saját kód"),
        _("Mozgástípus"),
        _("Honnan"),
        _("Hova"),
        _("Mennyiség"),
        _("Felhasználó"),
        _("Megjegyzés"),
    ]

    for column, header in enumerate(
        headers
    ):
        worksheet.write(
            0,
            column,
            header,
            header_format,
        )

    for row_number, movement in enumerate(
        rows,
        start=1,
    ):
        worksheet.write(
            row_number,
            0,
            movement.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            text_format,
        )

        worksheet.write(
            row_number,
            1,
            movement.item.name,
            text_format,
        )

        worksheet.write(
            row_number,
            2,
            movement.item.internal_code,
            text_format,
        )

        worksheet.write(
            row_number,
            3,
            movement_type_display(
                movement.movement_type
            ),
            text_format,
        )

        worksheet.write(
            row_number,
            4,
            (
                movement.from_location.full_path
                if movement.from_location
                else ""
            ),
            text_format,
        )

        worksheet.write(
            row_number,
            5,
            (
                movement.to_location.full_path
                if movement.to_location
                else ""
            ),
            text_format,
        )

        worksheet.write_number(
            row_number,
            6,
            movement.quantity,
            quantity_format,
        )

        worksheet.write(
            row_number,
            7,
            (
                movement.created_by.display_name
                if movement.created_by
                else ""
            ),
            text_format,
        )

        worksheet.write(
            row_number,
            8,
            movement.note or "",
            text_format,
        )

    last_row = max(
        len(rows),
        1,
    )

    worksheet.autofilter(
        0,
        0,
        last_row,
        len(headers) - 1,
    )

    worksheet.freeze_panes(
        1,
        0,
    )

    worksheet.set_column(
        0,
        0,
        20,
    )

    worksheet.set_column(
        1,
        1,
        30,
    )

    worksheet.set_column(
        2,
        2,
        16,
    )

    worksheet.set_column(
        3,
        3,
        18,
    )

    worksheet.set_column(
        4,
        5,
        38,
    )

    worksheet.set_column(
        6,
        6,
        12,
    )

    worksheet.set_column(
        7,
        7,
        20,
    )

    worksheet.set_column(
        8,
        8,
        40,
    )

    workbook.close()

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="heni_inventory_movements.xlsx"'
        },
    )


@inventory_bp.route(
    "/items/<int:item_id>/images/<int:image_id>"
)
@login_required
def item_image(
    item_id,
    image_id,
):
    item = db.get_or_404(
        Item,
        item_id,
    )

    image = db.get_or_404(
        ItemImage,
        image_id,
    )

    if image.item_id != item.id:
        abort(404)

    return send_from_directory(
        current_app.config[
            "ITEM_UPLOAD_FOLDER"
        ],
        image.filename,
    )
