from flask_login import UserMixin
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from .extensions import db

class ItemType(db.Model):
    __tablename__ = "item_types"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    code = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    sort_order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    items = db.relationship(
        "Item",
        back_populates="item_type",
    )


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    item_type_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "item_types.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    name = db.Column(
        db.String(255),
        nullable=False,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    item_type = db.relationship(
        "ItemType",
        back_populates="items",
    )

    identifiers = db.relationship(
        "ItemIdentifier",
        back_populates="item",
        cascade="all, delete-orphan",
    )

    images = db.relationship(
        "ItemImage",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ItemImage.sort_order, ItemImage.id",
    )

    @property
    def internal_code(self):
        if self.id is None:
            return None

        return f"ITEM-{self.id:06d}"


class ItemIdentifier(db.Model):
    __tablename__ = "item_identifiers"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    identifier_type = db.Column(
        db.String(30),
        nullable=False,
        default="BARCODE",
    )

    identifier_value = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    is_primary = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    item = db.relationship(
        "Item",
        back_populates="identifiers",
    )


class ItemImage(db.Model):
    __tablename__ = "item_images"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    filename = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )

    original_filename = db.Column(
        db.String(255),
        nullable=True,
    )

    sort_order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    item = db.relationship(
        "Item",
        back_populates="images",
    )


class Location(db.Model):
    __tablename__ = "locations"

    TYPE_ROOM = "room"
    TYPE_SHELF = "shelf"
    TYPE_STORAGE = "storage"

    VALID_TYPES = {
        TYPE_ROOM,
        TYPE_SHELF,
        TYPE_STORAGE,
    }

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    parent_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    location_type = db.Column(
        db.String(30),
        nullable=False,
        default="storage",
        index=True,
    )

    can_hold_stock = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    sort_order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    parent = db.relationship(
        "Location",
        remote_side=[id],
        back_populates="children",
    )

    children = db.relationship(
        "Location",
        back_populates="parent",
    )

    @property
    def internal_code(self):
        if self.id is None:
            return None

        return f"LOC-{self.id:06d}"

    @property
    def full_path(self):
        names = []
        current = self

        visited = set()

        while current is not None:
            if current.id in visited:
                break

            visited.add(current.id)
            names.append(current.name)
            current = current.parent

        return " > ".join(
            reversed(names)
        )

class User(UserMixin, db.Model):
    __tablename__ = "users"

    ROLE_ADMIN = "admin"
    ROLE_EDITOR = "editor"
    ROLE_VIEWER = "viewer"

    VALID_ROLES = {
        ROLE_ADMIN,
        ROLE_EDITOR,
        ROLE_VIEWER,
    }

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    username = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    display_name = db.Column(
        db.String(150),
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default=ROLE_VIEWER,
        index=True,
    )

    preferred_language = db.Column(
        db.String(2),
        nullable=False,
        default="hu",
        server_default="hu",
    )

    is_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    @property
    def is_active(self):
        return self.is_enabled

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def can_edit(self):
        return self.role in {
            self.ROLE_ADMIN,
            self.ROLE_EDITOR,
        }

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password,
        )

class InventoryStock(db.Model):
    __tablename__ = "inventory_stock"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    location_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    item = db.relationship(
        "Item",
        backref="stock_positions",
    )

    location = db.relationship(
        "Location",
        backref="stock_positions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "item_id",
            "location_id",
            name="uq_inventory_stock_item_location",
        ),
        db.CheckConstraint(
            "quantity >= 0",
            name="ck_inventory_stock_quantity_nonnegative",
        ),
    )


class InventoryMovement(db.Model):
    __tablename__ = "inventory_movements"

    TYPE_RECEIPT = "RECEIPT"
    TYPE_MOVE = "MOVE"
    TYPE_ISSUE = "ISSUE"
    TYPE_CORRECTION_PLUS = "CORRECTION_PLUS"
    TYPE_CORRECTION_MINUS = "CORRECTION_MINUS"

    VALID_TYPES = {
        TYPE_RECEIPT,
        TYPE_MOVE,
        TYPE_ISSUE,
        TYPE_CORRECTION_PLUS,
        TYPE_CORRECTION_MINUS,
    }

    id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    item_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    movement_type = db.Column(
        db.String(30),
        nullable=False,
        index=True,
    )

    from_location_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    to_location_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
    )

    source_quantity_before = db.Column(
        db.Integer,
        nullable=True,
    )

    source_quantity_after = db.Column(
        db.Integer,
        nullable=True,
    )

    destination_quantity_before = db.Column(
        db.Integer,
        nullable=True,
    )

    destination_quantity_after = db.Column(
        db.Integer,
        nullable=True,
    )

    note = db.Column(
        db.Text,
        nullable=True,
    )

    created_by_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        index=True,
    )

    item = db.relationship(
        "Item",
        backref="movements",
    )

    from_location = db.relationship(
        "Location",
        foreign_keys=[from_location_id],
    )

    to_location = db.relationship(
        "Location",
        foreign_keys=[to_location_id],
    )

    created_by = db.relationship(
        "User",
        backref="inventory_movements",
    )

    __table_args__ = (
        db.CheckConstraint(
            "quantity > 0",
            name="ck_inventory_movements_quantity_positive",
        ),
    )
