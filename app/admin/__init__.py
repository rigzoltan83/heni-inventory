from flask import Blueprint

from ..permissions import admin_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


@admin_bp.before_request
@admin_required
def require_admin():
    pass


from . import routes  # noqa: E402, F401
