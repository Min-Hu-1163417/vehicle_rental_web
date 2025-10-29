from flask import Flask

from .controllers.auth import bp as auth_bp
from .controllers.rentals import bp as rentals_bp
from .controllers.staff import bp as admin_bp
from .controllers.views import bp as views_bp
from .models.store import Store


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    Store.instance()  # load data.pkl or init default
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(rentals_bp)
    app.register_blueprint(admin_bp)
    return app
