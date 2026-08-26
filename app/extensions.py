from flask_babel import (
    Babel,
    lazy_gettext,
)
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
babel = Babel()

login_manager.login_view = "auth.login"
login_manager.login_message = lazy_gettext(
    "A funkció használatához be kell jelentkezni."
)
login_manager.login_message_category = "error"
