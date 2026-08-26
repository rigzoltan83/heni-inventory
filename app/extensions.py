from flask_babel import Babel
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
babel = Babel()

login_manager.login_view = "auth.login"
login_manager.login_message = (
    "A funkció használatához be kell jelentkezni."
)
login_manager.login_message_category = "error"
