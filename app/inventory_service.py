from sqlalchemy import select

from .extensions import db
from .models import (
    InventoryMovement,
    InventoryStock,
    Item,
    Location,
)


class InventoryError(Exception):
    pass


def _validate_quantity(quantity):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise InventoryError(
            "A mennyiség csak egész szám lehet."
        )

    if quantity <= 0:
        raise InventoryError(
            "A mennyiségnek pozitívnak kell lennie."
        )

    return quantity


def _get_item(item_id):
    item = db.session.get(
        Item,
        item_id,
    )

    if item is None:
        raise InventoryError(
            "A tétel nem található."
        )

    if not item.is_active:
        raise InventoryError(
            "Inaktív tételen nem végezhető készletmozgás."
        )

    return item


def _get_stock_location(location_id):
    location = db.session.get(
        Location,
        location_id,
    )

    if location is None:
        raise InventoryError(
            "A tárhely nem található."
        )

    if not location.is_active:
        raise InventoryError(
            "Inaktív tárhely nem használható."
        )

    if not location.can_hold_stock:
        raise InventoryError(
            "Ezen a helyen nem tárolható készlet."
        )

    return location


def _get_stock_position(
    item_id,
    location_id,
    create=False,
):
    statement = (
        select(InventoryStock)
        .where(
            InventoryStock.item_id == item_id,
            InventoryStock.location_id == location_id,
        )
        .with_for_update()
    )

    stock = (
        db.session.execute(statement)
        .scalar_one_or_none()
    )

    if stock is None and create:
        stock = InventoryStock(
            item_id=item_id,
            location_id=location_id,
            quantity=0,
        )

        db.session.add(stock)
        db.session.flush()

    return stock

def receipt(
    item_id,
    location_id,
    quantity,
    user_id,
    note=None,
    commit=True,
):
    quantity = _validate_quantity(quantity)

    _get_item(item_id)
    _get_stock_location(location_id)

    try:
        stock = _get_stock_position(
            item_id,
            location_id,
            create=True,
        )

        before = stock.quantity

        stock.quantity += quantity

        movement = InventoryMovement(
            item_id=item_id,
            movement_type=(
                InventoryMovement.TYPE_RECEIPT
            ),
            from_location_id=None,
            to_location_id=location_id,
            quantity=quantity,
            source_quantity_before=None,
            source_quantity_after=None,
            destination_quantity_before=before,
            destination_quantity_after=stock.quantity,
            created_by_user_id=user_id,
            note=note or None,
        )

        db.session.add(movement)

        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return movement

    except Exception:
        db.session.rollback()
        raise


def move(
    item_id,
    from_location_id,
    to_location_id,
    quantity,
    user_id,
    note=None,
):
    quantity = _validate_quantity(quantity)

    if from_location_id == to_location_id:
        raise InventoryError(
            "A forrás és a cél tárhely nem lehet azonos."
        )

    _get_item(item_id)
    _get_stock_location(from_location_id)
    _get_stock_location(to_location_id)

    try:
        source = _get_stock_position(
            item_id,
            from_location_id,
            create=False,
        )

        if source is None:
            raise InventoryError(
                "A forrás tárhelyen nincs ebből a tételből készlet."
            )

        if source.quantity < quantity:
            raise InventoryError(
                "Nincs elegendő készlet a forrás tárhelyen."
            )

        destination = _get_stock_position(
            item_id,
            to_location_id,
            create=True,
        )

        source_before = source.quantity
        destination_before = destination.quantity

        source.quantity -= quantity
        destination.quantity += quantity

        movement = InventoryMovement(
            item_id=item_id,
            movement_type=(
                InventoryMovement.TYPE_MOVE
            ),
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            source_quantity_before=source_before,
            source_quantity_after=source.quantity,
            destination_quantity_before=(
                destination_before
            ),
            destination_quantity_after=(
                destination.quantity
            ),
            created_by_user_id=user_id,
            note=note or None,
        )

        db.session.add(movement)
        db.session.commit()

        return movement

    except Exception:
        db.session.rollback()
        raise


def issue(
    item_id,
    location_id,
    quantity,
    user_id,
    note=None,
):
    quantity = _validate_quantity(quantity)

    _get_item(item_id)
    _get_stock_location(location_id)

    try:
        stock = _get_stock_position(
            item_id,
            location_id,
            create=False,
        )

        if stock is None:
            raise InventoryError(
                "Ezen a tárhelyen nincs ebből a tételből készlet."
            )

        if stock.quantity < quantity:
            raise InventoryError(
                "Nincs elegendő készlet a kiadáshoz."
            )

        before = stock.quantity

        stock.quantity -= quantity

        movement = InventoryMovement(
            item_id=item_id,
            movement_type=(
                InventoryMovement.TYPE_ISSUE
            ),
            from_location_id=location_id,
            to_location_id=None,
            quantity=quantity,
            source_quantity_before=before,
            source_quantity_after=stock.quantity,
            destination_quantity_before=None,
            destination_quantity_after=None,
            created_by_user_id=user_id,
            note=note or None,
        )

        db.session.add(movement)
        db.session.commit()

        return movement

    except Exception:
        db.session.rollback()
        raise


def set_counted_quantity(
    item_id,
    location_id,
    counted_quantity,
    user_id,
    note=None,
):
    try:
        counted_quantity = int(
            counted_quantity
        )
    except (TypeError, ValueError):
        raise InventoryError(
            "A tényleges mennyiség csak egész szám lehet."
        )

    if counted_quantity < 0:
        raise InventoryError(
            "A tényleges mennyiség nem lehet negatív."
        )

    _get_item(item_id)
    _get_stock_location(location_id)

    try:
        stock = _get_stock_position(
            item_id,
            location_id,
            create=True,
        )

        before = stock.quantity

        difference = counted_quantity - before

        if difference == 0:
            raise InventoryError(
                "A megadott mennyiség megegyezik a jelenlegi készlettel."
            )

        stock.quantity = counted_quantity

        if difference > 0:
            movement_type = (
                InventoryMovement.TYPE_CORRECTION_PLUS
            )
            quantity = difference
        else:
            movement_type = (
                InventoryMovement.TYPE_CORRECTION_MINUS
            )
            quantity = abs(difference)

        movement = InventoryMovement(
            item_id=item_id,
            movement_type=movement_type,
            from_location_id=(
                location_id
                if difference < 0
                else None
            ),
            to_location_id=(
                location_id
                if difference > 0
                else None
            ),
            quantity=quantity,
            source_quantity_before=(
                before
                if difference < 0
                else None
            ),
            source_quantity_after=(
                counted_quantity
                if difference < 0
                else None
            ),
            destination_quantity_before=(
                before
                if difference > 0
                else None
            ),
            destination_quantity_after=(
                counted_quantity
                if difference > 0
                else None
            ),
            created_by_user_id=user_id,
            note=note or None,
        )

        db.session.add(movement)
        db.session.commit()

        return movement

    except Exception:
        db.session.rollback()
        raise
