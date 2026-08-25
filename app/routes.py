from flask import Blueprint, jsonify, render_template
from sqlalchemy import text

from .extensions import db


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))

        return jsonify(
            {
                "status": "ok",
                "database": "ok",
                "application": "heni-inventory",
            }
        )
    except Exception as exc:
        return (
            jsonify(
                {
                    "status": "error",
                    "database": "error",
                    "message": str(exc),
                }
            ),
            500,
        )
