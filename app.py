from flask import Flask, session, redirect, url_for
from config import Config

def create_app():
    app= Flask(__name__)
    app.config.from_object(Config)

    from auth import auth_bp
    app.register_blueprint(auth_bp)

    from flask import Blueprint, render_template
    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        return redirect(url_for('auth.login'))

    @main_bp.route('/dashboard')
    def dashboard():
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return render_template('dashboard_placeholder.html', username=session['username'],role=session['role'])
    app.register_blueprint(main_bp)

    #to display the number of pending users in the navbar badge

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