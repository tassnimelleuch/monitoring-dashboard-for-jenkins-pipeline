from flask import Flask, session, redirect, url_for, Blueprint
from config import Config
from jenkins_bp import jenkins_bp
from auth import auth_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(jenkins_bp)

    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        return redirect(url_for('auth.login'))

    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_globals():
        from models import get_pending_count
        count = 0
        if session.get('role') == 'admin':
            count = get_pending_count()
        return {'pending_count': count}

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)