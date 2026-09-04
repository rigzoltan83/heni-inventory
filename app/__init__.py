import os

from dotenv import load_dotenv
from flask import Flask, request, session
from flask_login import current_user
from flask_babel import get_locale

from .extensions import (
    babel,
    db,
    login_manager,
    migrate,
)
from .middleware import PrefixMiddleware


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ[
        "SECRET_KEY"
    ]

    app.config["SESSION_COOKIE_NAME"] = (
        "heni_inventory_session"
    )

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = os.environ[
        "DATABASE_URL"
    ]

    app.config[
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    ] = False

    default_upload_folder = os.path.abspath(
        os.path.join(
            app.root_path,
            "..",
            "uploads",
            "items",
        )
    )

    app.config["ITEM_UPLOAD_FOLDER"] = (
        os.environ.get(
            "ITEM_UPLOAD_FOLDER",
            default_upload_folder,
        )
    )

    app.config["MAX_CONTENT_LENGTH"] = (
        50 * 1024 * 1024
    )

    app_prefix = os.environ.get(
        "APP_PREFIX",
        "",
    ).rstrip("/")

    db.init_app(app)

    from . import models

    migrate.init_app(app, db)

    login_manager.init_app(app)
    app.config["BABEL_DEFAULT_LOCALE"] = "hu"
    app.config["BABEL_SUPPORTED_LOCALES"] = [
        "hu",
        "en",
    ]

    app.config[
        "BABEL_TRANSLATION_DIRECTORIES"
    ] = "../translations"

    def select_locale():
        requested_language = (
            request.values.get(
                "lang",
                "",
            )
            .strip()
            .lower()
        )

        if requested_language in {
            "hu",
            "en",
        }:
            return requested_language

        if (
            current_user.is_authenticated
            and current_user.preferred_language
            in {"hu", "en"}
        ):
            return current_user.preferred_language

        language = session.get(
            "preferred_language",
            "hu",
        )

        if language not in {
            "hu",
            "en",
        }:
            return "hu"

        return language

    babel.init_app(
        app,
        locale_selector=select_locale,
    )

    app.jinja_env.globals[
        "get_locale"
    ] = get_locale

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None

        return db.session.get(
            models.User,
            user_id,
        )

    from .routes import main_bp
    from .admin import admin_bp
    from .auth import auth_bp
    from .inventory import inventory_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(inventory_bp)

    app.wsgi_app = PrefixMiddleware(
        app.wsgi_app,
        prefix=app_prefix,
    )

    return app
