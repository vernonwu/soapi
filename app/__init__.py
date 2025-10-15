from flask import Flask

from .db import ensure_schema


def create_app():
    app = Flask(__name__)
    app.config.update(
        DB_PATH="database/laundry.db",
    )

    ensure_schema(app.config["DB_PATH"])

    # register routes
    from .routes import bp

    app.register_blueprint(bp)

    return app

