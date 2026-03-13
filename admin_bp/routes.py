from flask import render_template, redirect, url_for, session
from functools import wraps
from . import admin_bp
from jenkins_bp.fetcher import check_connection


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/admin/dashboard')
@admin_only
def dashboard():
    connected = check_connection()
    return render_template('admin/dashboard.html', connected=connected)