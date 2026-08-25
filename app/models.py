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


class Location(db.Model):
    __tablename__ = "locations"

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
