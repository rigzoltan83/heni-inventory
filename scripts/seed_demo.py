import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app import create_app
from app.extensions import db
from app.inventory_service import (
    issue,
    move,
    receipt,
    set_counted_quantity,
)
from app.models import (
    InventoryMovement,
    InventoryStock,
    Item,
    ItemIdentifier,
    ItemType,
    Location,
    User,
)


app = create_app()


def make_location(
    name,
    location_type,
    parent=None,
    can_hold_stock=False,
    sort_order=0,
    description=None,
):
    location = Location(
        name=name,
        location_type=location_type,
        parent=parent,
        can_hold_stock=can_hold_stock,
        sort_order=sort_order,
        description=description,
        is_active=True,
    )

    db.session.add(location)
    db.session.flush()

    return location


def make_item(
    item_type,
    name,
    description,
    barcode=None,
):
    item = Item(
        item_type=item_type,
        name=name,
        description=description,
        is_active=True,
    )

    db.session.add(item)
    db.session.flush()

    if barcode:
        db.session.add(
            ItemIdentifier(
                item=item,
                identifier_type="BARCODE",
                identifier_value=barcode,
                is_primary=True,
                is_active=True,
            )
        )

    db.session.flush()

    return item


with app.app_context():
    if User.query.first() is not None:
        raise SystemExit(
            "Demo seed requires an empty database."
        )

    if Item.query.first() is not None:
        raise SystemExit(
            "Demo seed requires an empty database."
        )

    print("Creating demo users...")

    admin = User(
        username="demo",
        display_name="Demo Administrator",
        role=User.ROLE_ADMIN,
        preferred_language="en",
        is_enabled=True,
    )
    admin.set_password("demo12345")

    editor = User(
        username="warehouse",
        display_name="Warehouse Operator",
        role=User.ROLE_EDITOR,
        preferred_language="en",
        is_enabled=True,
    )
    editor.set_password("demo12345")

    viewer = User(
        username="viewer",
        display_name="Inventory Viewer",
        role=User.ROLE_VIEWER,
        preferred_language="en",
        is_enabled=True,
    )
    viewer.set_password("demo12345")

    db.session.add_all(
        [
            admin,
            editor,
            viewer,
        ]
    )
    db.session.flush()

    print("Creating item types...")

    consumable = ItemType(
        code="CONSUMABLE",
        name="Consumable",
        sort_order=10,
        is_active=True,
    )

    cable = ItemType(
        code="CABLE",
        name="Cable",
        sort_order=20,
        is_active=True,
    )

    adapter = ItemType(
        code="ADAPTER",
        name="Adapter",
        sort_order=30,
        is_active=True,
    )

    tool = ItemType(
        code="TOOL",
        name="Tool",
        sort_order=40,
        is_active=True,
    )

    spare = ItemType(
        code="SPARE",
        name="Spare part",
        sort_order=50,
        is_active=True,
    )

    db.session.add_all(
        [
            consumable,
            cable,
            adapter,
            tool,
            spare,
        ]
    )
    db.session.flush()

    print("Creating location hierarchy...")

    workshop = make_location(
        "Workshop",
        Location.TYPE_ROOM,
        can_hold_stock=False,
        sort_order=10,
    )

    electronics = make_location(
        "Electronics area",
        Location.TYPE_SHELF,
        parent=workshop,
        can_hold_stock=False,
        sort_order=10,
    )

    electronics_a = make_location(
        "Shelf A",
        Location.TYPE_STORAGE,
        parent=electronics,
        can_hold_stock=True,
        sort_order=10,
    )

    electronics_b = make_location(
        "Shelf B",
        Location.TYPE_STORAGE,
        parent=electronics,
        can_hold_stock=True,
        sort_order=20,
    )

    tool_area = make_location(
        "Tool cabinet",
        Location.TYPE_SHELF,
        parent=workshop,
        can_hold_stock=False,
        sort_order=20,
    )

    tool_drawer = make_location(
        "Drawer 1",
        Location.TYPE_STORAGE,
        parent=tool_area,
        can_hold_stock=True,
        sort_order=10,
    )

    warehouse = make_location(
        "Storage room",
        Location.TYPE_ROOM,
        can_hold_stock=False,
        sort_order=20,
    )

    rack_a = make_location(
        "Rack A",
        Location.TYPE_SHELF,
        parent=warehouse,
        can_hold_stock=False,
        sort_order=10,
    )

    rack_a_1 = make_location(
        "Bin A1",
        Location.TYPE_STORAGE,
        parent=rack_a,
        can_hold_stock=True,
        sort_order=10,
    )

    rack_a_2 = make_location(
        "Bin A2",
        Location.TYPE_STORAGE,
        parent=rack_a,
        can_hold_stock=True,
        sort_order=20,
    )

    rack_b = make_location(
        "Rack B",
        Location.TYPE_SHELF,
        parent=warehouse,
        can_hold_stock=False,
        sort_order=20,
    )

    rack_b_1 = make_location(
        "Bin B1",
        Location.TYPE_STORAGE,
        parent=rack_b,
        can_hold_stock=True,
        sort_order=10,
    )

    rack_b_2 = make_location(
        "Bin B2",
        Location.TYPE_STORAGE,
        parent=rack_b,
        can_hold_stock=True,
        sort_order=20,
    )

    print("Creating demo items...")

    usb_c_1m = make_item(
        cable,
        "USB-C cable 1 m",
        "General-purpose USB-C charging and data cable.",
        "5900000000011",
    )

    usb_c_2m = make_item(
        cable,
        "USB-C cable 2 m",
        "Two-metre USB-C charging cable.",
        "5900000000028",
    )

    hdmi = make_item(
        cable,
        "HDMI cable 2 m",
        "Standard HDMI cable for displays and test equipment.",
        "5900000000035",
    )

    ethernet = make_item(
        cable,
        "CAT6 patch cable 1 m",
        "CAT6 Ethernet patch cable.",
        "5900000000042",
    )

    usb_adapter = make_item(
        adapter,
        "USB-C to USB-A adapter",
        "Compact adapter for USB-A peripherals.",
        "5900000000059",
    )

    hdmi_adapter = make_item(
        adapter,
        "USB-C to HDMI adapter",
        "Display adapter for USB-C devices.",
        "5900000000066",
    )

    batteries = make_item(
        consumable,
        "AA alkaline batteries",
        "AA alkaline batteries stored individually.",
        "5900000000073",
    )

    cable_ties = make_item(
        consumable,
        "Cable ties 200 mm",
        "Black reusable workshop cable ties.",
        "5900000000080",
    )

    screws = make_item(
        consumable,
        "M4 x 20 mm screws",
        "General-purpose M4 machine screws.",
        "5900000000097",
    )

    screwdriver = make_item(
        tool,
        "Precision screwdriver set",
        "Small screwdriver set for electronics work.",
        "5900000000103",
    )

    multimeter = make_item(
        tool,
        "Digital multimeter",
        "General-purpose workshop multimeter.",
        "5900000000110",
    )

    fan = make_item(
        spare,
        "120 mm cooling fan",
        "Replacement 12 V equipment cooling fan.",
        "5900000000127",
    )

    db.session.commit()

    print("Creating inventory history...")

    receipt(
        usb_c_1m.id,
        rack_a_1.id,
        40,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        usb_c_2m.id,
        rack_a_1.id,
        24,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        hdmi.id,
        rack_a_2.id,
        18,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        ethernet.id,
        rack_a_2.id,
        60,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        usb_adapter.id,
        rack_b_1.id,
        32,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        hdmi_adapter.id,
        rack_b_1.id,
        14,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        batteries.id,
        rack_b_2.id,
        120,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        cable_ties.id,
        rack_b_2.id,
        250,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        screws.id,
        rack_b_2.id,
        400,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        screwdriver.id,
        tool_drawer.id,
        6,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        multimeter.id,
        tool_drawer.id,
        3,
        admin.id,
        "Initial demo stock",
    )

    receipt(
        fan.id,
        electronics_b.id,
        12,
        admin.id,
        "Initial demo stock",
    )

    move(
        usb_c_1m.id,
        rack_a_1.id,
        electronics_a.id,
        8,
        editor.id,
        "Workshop replenishment",
    )

    move(
        usb_adapter.id,
        rack_b_1.id,
        electronics_a.id,
        5,
        editor.id,
        "Workshop replenishment",
    )

    move(
        fan.id,
        electronics_b.id,
        rack_b_1.id,
        4,
        editor.id,
        "Moved to spare-parts storage",
    )

    issue(
        ethernet.id,
        rack_a_2.id,
        7,
        editor.id,
        "Network installation",
    )

    issue(
        batteries.id,
        rack_b_2.id,
        16,
        editor.id,
        "Workshop use",
    )

    issue(
        cable_ties.id,
        rack_b_2.id,
        35,
        editor.id,
        "Workshop use",
    )

    set_counted_quantity(
        screws.id,
        rack_b_2.id,
        392,
        admin.id,
        "Demo cycle count",
    )

    print()
    print("Demo database created.")
    print()
    print("Login:")
    print("  username: demo")
    print("  password: demo12345")
    print()
    print(
        "Items:",
        Item.query.count(),
    )
    print(
        "Locations:",
        Location.query.count(),
    )
    print(
        "Stock positions:",
        InventoryStock.query.count(),
    )
    print(
        "Movements:",
        InventoryMovement.query.count(),
    )
