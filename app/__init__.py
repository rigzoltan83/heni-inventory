import os

from dotenv import load_dotenv
from flask import Flask

from .extensions import (
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

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = os.environ[
        "DATABASE_URL"
    ]

    app.config[
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    ] = False

    app_prefix = os.environ.get(
        "APP_PREFIX",
        "",
    ).rstrip("/")

    db.init_app(app)

    from . import models

    migrate.init_app(app, db)

    login_manager.init_app(app)

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
