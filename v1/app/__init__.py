from flask import Flask

def create_app():

    app = Flask(__name__)

    app.secret_key = "ifsas_secret_key"

    app.permanent_session_lifetime = 86400 * 7  # 7 μέρες

    from .routes import main
    app.register_blueprint(main)

    from .scheduler import start_scheduler
    start_scheduler()

    return app
