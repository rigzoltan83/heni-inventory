import os

from dotenv import load_dotenv
from flask import Flask

from .extensions import db, migrate


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ[
        "DATABASE_URL"
    ]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from .routes import main_bp

    app.register_blueprint(main_bp)

    return app
