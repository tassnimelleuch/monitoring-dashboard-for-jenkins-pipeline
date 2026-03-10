from flask import session, redirect, url_for, jsonify
from jenkins_bp import jenkins_bp
from .fetcher import check_connection, get_kpis



#dashboard

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@jenkins_bp.route('/kpis')
@admin_only
def kpis():
    data = get_kpis()
    return jsonify(data)

@jenkins_bp.route('/status')
@admin_only
def status():
    return jsonify({'connected': check_connection()})

