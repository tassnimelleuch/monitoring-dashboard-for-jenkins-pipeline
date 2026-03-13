from functools import wraps
from flask import session, redirect, url_for, jsonify, render_template
from jenkins_bp import jenkins_bp
from .fetcher import check_connection, get_kpis


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@jenkins_bp.route('/dashboard')
@role_required('admin', 'dev', 'qa')
def dashboard():
    return render_template('admin/dashboard.html',
                           username=session.get('username'),
                           role=session.get('role'))
@jenkins_bp.route('/api/kpis')
@role_required('admin', 'dev', 'qa')
def kpis():
    return jsonify(get_kpis())


@jenkins_bp.route('/api/status')
@role_required('admin', 'dev', 'qa')
def status():
    return jsonify({'connected': check_connection()})