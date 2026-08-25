from io import BytesIO

import barcode
from barcode.writer import SVGWriter
from flask import Response
from flask_login import current_user

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from . import admin_bp
from ..extensions import db
from ..models import (
    InventoryStock,
    Item,
    ItemIdentifier,
    ItemType,
    ItemImage,
    Location,
    User,
)
from ..image_service import (
    ImageUploadError,
    delete_item_image_file,
    save_item_image,
)
from ..inventory_service import (
    InventoryError,
    issue,
    move,
    receipt,
    set_counted_quantity,
)


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

def build_location_tree(locations):
    by_parent = {}

    for location in locations:
        by_parent.setdefault(
            location.parent_id,
            [],
        ).append(location)

    for children in by_parent.values():
        children.sort(
            key=lambda row: (
                row.sort_order,
                row.name.lower(),
            )
        )

    result = []

    def walk(parent_id, level):
        for location in by_parent.get(
            parent_id,
            [],
        ):
            result.append(
                {
                    "location": location,
                    "level": level,
                }
            )

            walk(
                location.id,
                level + 1,
            )

    walk(
        None,
        0,
    )

    return result


@admin_bp.route("/locations")
def locations():
    rows = (
        Location.query
        .order_by(
            Location.sort_order,
            Location.name,
        )
        .all()
    )

    tree = build_location_tree(
        rows
    )

    return render_template(
        "admin/locations/list.html",
        location_tree=tree,
        back_url=url_for("admin.index"),
    )


@admin_bp.route(
    "/locations/new",
    methods=["GET", "POST"],
)
def location_new():
    parent_id = request.args.get(
        "parent_id",
        type=int,
    )

    parent = None

    if parent_id is not None:
        parent = db.get_or_404(
            Location,
            parent_id,
        )

    if request.method == "POST":
        name = (
            request.form.get(
                "name",
                "",
            )
            .strip()
        )

        location_type = (
            request.form.get(
                "location_type",
                "",
            )
            .strip()
        )

        parent_id_raw = (
            request.form.get(
                "parent_id",
                "",
            )
            .strip()
        )

        sort_order_raw = (
            request.form.get(
                "sort_order",
                "0",
            )
            .strip()
        )

        can_hold_stock = (
            request.form.get(
                "can_hold_stock"
            )
            == "on"
        )

        if not name:
            flash(
                "A megnevezés kötelező.",
                "error",
            )

        elif (
            location_type
            not in Location.VALID_TYPES
        ):
            flash(
                "Érvénytelen tárhelytípus.",
                "error",
            )

        else:
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
                    "admin/locations/form.html",
                    location=None,
                    parent=parent,
                    locations=Location.query
                    .order_by(
                        Location.name
                    )
                    .all(),
                    back_url=url_for(
                        "admin.locations"
                    ),
                )

            parent_id_value = (
                int(parent_id_raw)
                if parent_id_raw
                else None
            )

            location = Location(
                name=name,
                location_type=location_type,
                parent_id=parent_id_value,
                sort_order=sort_order,
                can_hold_stock=can_hold_stock,
                is_active=True,
            )

            db.session.add(location)
            db.session.commit()

            flash(
                "A tárhely létrejött.",
                "success",
            )

            return redirect(
                url_for(
                    "admin.locations"
                )
            )

    return render_template(
        "admin/locations/form.html",
        location=None,
        parent=parent,
        locations=Location.query
        .order_by(
            Location.name
        )
        .all(),
        back_url=url_for(
            "admin.locations"
        ),
    )


@admin_bp.route(
    "/locations/<int:location_id>/edit",
    methods=["GET", "POST"],
)
def location_edit(location_id):
    location = db.get_or_404(
        Location,
        location_id,
    )

    if request.method == "POST":
        name = (
            request.form.get(
                "name",
                "",
            )
            .strip()
        )

        location_type = (
            request.form.get(
                "location_type",
                "",
            )
            .strip()
        )

        parent_id_raw = (
            request.form.get(
                "parent_id",
                "",
            )
            .strip()
        )

        sort_order_raw = (
            request.form.get(
                "sort_order",
                "0",
            )
            .strip()
        )

        can_hold_stock = (
            request.form.get(
                "can_hold_stock"
            )
            == "on"
        )

        if not name:
            flash(
                "A megnevezés kötelező.",
                "error",
            )

        elif (
            location_type
            not in Location.VALID_TYPES
        ):
            flash(
                "Érvénytelen tárhelytípus.",
                "error",
            )

        else:
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
                    "admin/locations/form.html",
                    location=location,
                    parent=None,
                    locations=Location.query
                    .filter(
                        Location.id
                        != location.id
                    )
                    .order_by(
                        Location.name
                    )
                    .all(),
                    back_url=url_for(
                        "admin.locations"
                    ),
                )

            parent_id_value = (
                int(parent_id_raw)
                if parent_id_raw
                else None
            )

            if (
                parent_id_value
                == location.id
            ):
                flash(
                    "Egy tárhely nem lehet saját maga szülője.",
                    "error",
                )
            else:
                location.name = name
                location.location_type = (
                    location_type
                )
                location.parent_id = (
                    parent_id_value
                )
                location.sort_order = (
                    sort_order
                )
                location.can_hold_stock = (
                    can_hold_stock
                )

                db.session.commit()

                flash(
                    "A tárhely módosítva.",
                    "success",
                )

                return redirect(
                    url_for(
                        "admin.locations"
                    )
                )

    return render_template(
        "admin/locations/form.html",
        location=location,
        parent=None,
        locations=Location.query
        .filter(
            Location.id != location.id
        )
        .order_by(
            Location.name
        )
        .all(),
        back_url=url_for(
            "admin.locations"
        ),
    )


@admin_bp.route(
    "/locations/<int:location_id>/toggle",
    methods=["POST"],
)
def location_toggle(location_id):
    location = db.get_or_404(
        Location,
        location_id,
    )

    location.is_active = (
        not location.is_active
    )

    db.session.commit()

    flash(
        (
            "A tárhely aktiválva."
            if location.is_active
            else "A tárhely inaktiválva."
        ),
        "success",
    )

    return redirect(
        url_for(
            "admin.locations"
        )
    )

@admin_bp.route(
    "/locations/<int:location_id>/barcode.svg"
)
def location_barcode(location_id):
    location = db.get_or_404(
        Location,
        location_id,
    )

    output = BytesIO()

    code = barcode.get(
        "code128",
        location.internal_code,
        writer=SVGWriter(),
    )

    code.write(
        output,
        options={
            "write_text": False,
            "module_height": 12.0,
            "quiet_zone": 2.0,
        },
    )

    return Response(
        output.getvalue(),
        mimetype="image/svg+xml",
        headers={
            "Cache-Control": "no-store",
        },
    )


@admin_bp.route(
    "/locations/<int:location_id>/label"
)
def location_label(location_id):
    location = db.get_or_404(
        Location,
        location_id,
    )

    return render_template(
        "admin/locations/label.html",
        location=location,
        back_url=url_for(
            "admin.locations"
        ),
    )


@admin_bp.route(
    "/locations/labels"
)
def location_labels():
    rows = (
        Location.query
        .filter_by(is_active=True)
        .order_by(
            Location.sort_order,
            Location.name,
        )
        .all()
    )

    tree = build_location_tree(
        rows
    )

    locations = [
        row["location"]
        for row in tree
    ]

    return render_template(
        "admin/locations/labels.html",
        locations=locations,
        back_url=url_for(
            "admin.locations"
        ),
    )

@admin_bp.route("/items")
def items():
    rows = (
        Item.query
        .order_by(
            Item.name,
        )
        .all()
    )

    return render_template(
        "admin/items/list.html",
        items=rows,
        back_url=url_for("admin.index"),
    )


@admin_bp.route(
    "/items/new",
    methods=["GET", "POST"],
)
def item_new():
    item_types = (
        ItemType.query
        .filter_by(is_active=True)
        .order_by(
            ItemType.sort_order,
            ItemType.name,
        )
        .all()
    )

    if request.method == "POST":
        name = (
            request.form.get("name", "")
            .strip()
        )

        item_type_id = request.form.get(
            "item_type_id",
            type=int,
        )

        description = (
            request.form.get(
                "description",
                "",
            )
            .strip()
        )

        barcode_value = (
            request.form.get(
                "barcode_value",
                "",
            )
            .strip()
        )

        if not name:
            flash(
                "A megnevezés kötelező.",
                "error",
            )

        elif item_type_id is None:
            flash(
                "A tételtípus kiválasztása kötelező.",
                "error",
            )

        else:
            item_type = db.session.get(
                ItemType,
                item_type_id,
            )

            if (
                item_type is None
                or not item_type.is_active
            ):
                flash(
                    "Érvénytelen tételtípus.",
                    "error",
                )

            elif (
                barcode_value
                and ItemIdentifier.query
                .filter_by(
                    identifier_value=barcode_value
                )
                .first()
                is not None
            ):
                flash(
                    "Ez a vonalkód már egy másik tételhez tartozik.",
                    "error",
                )

            else:
                item = Item(
                    item_type=item_type,
                    name=name,
                    description=(
                        description or None
                    ),
                    is_active=True,
                )

                db.session.add(item)
                db.session.flush()

                if barcode_value:
                    identifier = ItemIdentifier(
                        item=item,
                        identifier_type="BARCODE",
                        identifier_value=barcode_value,
                        is_primary=True,
                        is_active=True,
                    )

                    db.session.add(identifier)

                db.session.commit()

                flash(
                    (
                        "A tétel létrejött. "
                        f"Saját kód: {item.internal_code}"
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "admin.items"
                    )
                )

    return render_template(
        "admin/items/form.html",
        item=None,
        item_types=item_types,
        barcode_value="",
        back_url=url_for("admin.items"),
    )


@admin_bp.route(
    "/items/<int:item_id>/edit",
    methods=["GET", "POST"],
)
def item_edit(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    item_types = (
        ItemType.query
        .order_by(
            ItemType.sort_order,
            ItemType.name,
        )
        .all()
    )

    primary_identifier = (
        ItemIdentifier.query
        .filter_by(
            item_id=item.id,
            is_primary=True,
            is_active=True,
        )
        .first()
    )

    if request.method == "POST":
        name = (
            request.form.get("name", "")
            .strip()
        )

        item_type_id = request.form.get(
            "item_type_id",
            type=int,
        )

        description = (
            request.form.get(
                "description",
                "",
            )
            .strip()
        )

        barcode_value = (
            request.form.get(
                "barcode_value",
                "",
            )
            .strip()
        )

        if not name:
            flash(
                "A megnevezés kötelező.",
                "error",
            )

        elif item_type_id is None:
            flash(
                "A tételtípus kiválasztása kötelező.",
                "error",
            )

        else:
            item_type = db.session.get(
                ItemType,
                item_type_id,
            )

            duplicate = None

            if barcode_value:
                duplicate = (
                    ItemIdentifier.query
                    .filter(
                        ItemIdentifier.identifier_value
                        == barcode_value,
                        ItemIdentifier.item_id
                        != item.id,
                    )
                    .first()
                )

            if item_type is None:
                flash(
                    "Érvénytelen tételtípus.",
                    "error",
                )

            elif duplicate is not None:
                flash(
                    "Ez a vonalkód már egy másik tételhez tartozik.",
                    "error",
                )

            else:
                item.name = name
                item.item_type = item_type
                item.description = (
                    description or None
                )

                if barcode_value:
                    if primary_identifier is None:
                        primary_identifier = (
                            ItemIdentifier(
                                item=item,
                                identifier_type="BARCODE",
                                identifier_value=barcode_value,
                                is_primary=True,
                                is_active=True,
                            )
                        )

                        db.session.add(
                            primary_identifier
                        )
                    else:
                        primary_identifier.identifier_value = (
                            barcode_value
                        )
                        primary_identifier.is_active = True

                elif primary_identifier is not None:
                    primary_identifier.is_active = False

                image_files = [
                    image_file
                    for image_file
                    in request.files.getlist(
                        "image_files"
                    )
                    if (
                        image_file
                        and image_file.filename
                    )
                ]

                camera_image = request.files.get(
                    "camera_image"
                )

                if (
                    camera_image
                    and camera_image.filename
                ):
                    image_files.insert(
                        0,
                        camera_image,
                    )

                saved_image_files = []

                try:
                    next_sort_order = (
                        max(
                            (
                                image.sort_order
                                for image
                                in item.images
                            ),
                            default=-1,
                        )
                        + 1
                    )

                    for image_file in image_files:
                        (
                            filename,
                            original_filename,
                        ) = save_item_image(
                            image_file
                        )

                        saved_image_files.append(
                            filename
                        )

                        image = ItemImage(
                            item=item,
                            filename=filename,
                            original_filename=(
                                original_filename
                            ),
                            sort_order=(
                                next_sort_order
                            ),
                        )

                        db.session.add(image)

                        next_sort_order += 1

                    db.session.commit()

                except ImageUploadError as exc:
                    db.session.rollback()

                    for filename in saved_image_files:
                        delete_item_image_file(
                            filename
                        )

                    flash(
                        str(exc),
                        "error",
                    )

                    return render_template(
                        "admin/items/form.html",
                        item=item,
                        item_types=item_types,
                        barcode_value=(
                            primary_identifier.identifier_value
                            if primary_identifier
                            else ""
                        ),
                        back_url=url_for(
                            "admin.items"
                        ),
                    )

                flash(
                    "A tétel módosítva.",
                    "success",
                )

                return redirect(
                    url_for(
                        "admin.items"
                    )
                )

    return render_template(
        "admin/items/form.html",
        item=item,
        item_types=item_types,
        barcode_value=(
            primary_identifier.identifier_value
            if primary_identifier
            else ""
        ),
        back_url=url_for("admin.items"),
    )


@admin_bp.route(
    "/items/<int:item_id>/images/<int:image_id>/delete",
    methods=["POST"],
)
def item_image_delete(
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

    filename = image.filename

    db.session.delete(image)
    db.session.commit()

    delete_item_image_file(
        filename
    )

    flash(
        "A kép törölve.",
        "success",
    )

    return redirect(
        url_for(
            "admin.item_edit",
            item_id=item.id,
        )
    )


@admin_bp.route(
    "/items/<int:item_id>/toggle",
    methods=["POST"],
)
def item_toggle(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    item.is_active = (
        not item.is_active
    )

    db.session.commit()

    flash(
        (
            "A tétel aktiválva."
            if item.is_active
            else "A tétel inaktiválva."
        ),
        "success",
    )

    return redirect(
        url_for("admin.items")
    )

@admin_bp.route(
    "/items/<int:item_id>/barcode.svg"
)
def item_barcode(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    output = BytesIO()

    code = barcode.get(
        "code128",
        item.internal_code,
        writer=SVGWriter(),
    )

    code.write(
        output,
        options={
            "write_text": False,
            "module_height": 12.0,
            "quiet_zone": 2.0,
        },
    )

    return Response(
        output.getvalue(),
        mimetype="image/svg+xml",
        headers={
            "Cache-Control": "no-store",
        },
    )

@admin_bp.route(
    "/items/<int:item_id>/label",
    methods=["GET", "POST"],
)
def item_label(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    return_to = (
        request.args.get(
            "return_to",
            "",
        )
        .strip()
    )

    if not return_to.startswith("/"):
        return_to = url_for(
            "admin.items"
        )

    quantity = request.args.get(
        "quantity",
        default=1,
        type=int,
    )

    if request.method == "POST":
        quantity = request.form.get(
            "quantity",
            type=int,
        )

        if quantity is None or quantity < 1:
            flash(
                "A darabszám legalább 1 legyen.",
                "error",
            )

            quantity = 1

        elif quantity > 200:
            flash(
                "Egyszerre legfeljebb 200 címke nyomtatható.",
                "error",
            )

            quantity = 200

        else:
            return redirect(
                url_for(
                    "admin.item_label_print",
                    item_id=item.id,
                    quantity=quantity,
                    return_to=return_to,
                )
            )

    return render_template(
        "admin/items/label_quantity.html",
        item=item,
        quantity=quantity,
        back_url=return_to,
    )


@admin_bp.route(
    "/items/<int:item_id>/label/print"
)
def item_label_print(item_id):
    item = db.get_or_404(
        Item,
        item_id,
    )

    return_to = (
        request.args.get(
            "return_to",
            "",
        )
        .strip()
    )

    if not return_to.startswith("/"):
        return_to = url_for(
            "admin.items"
        )

    quantity = request.args.get(
        "quantity",
        default=1,
        type=int,
    )

    quantity = max(
        1,
        min(quantity, 200),
    )

    return render_template(
        "admin/items/label_print.html",
        item=item,
        quantity=quantity,
        back_url=return_to,
    )


@admin_bp.route(
    "/items/<int:item_id>/images/<int:image_id>"
)
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


@admin_bp.route(
    "/items/<int:item_id>/images/<int:image_id>/delete-confirm"
)
def item_image_delete_confirm(
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

    return render_template(
        "admin/items/image_delete_confirm.html",
        item=item,
        image=image,
        back_url=url_for(
            "admin.item_edit",
            item_id=item.id,
        ),
    )
