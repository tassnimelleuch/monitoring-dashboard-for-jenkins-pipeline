from functools import wraps
from flask import session, redirect, url_for, jsonify, render_template
from jenkins_bp import jenkins_bp
from .fetcher import check_connection, get_kpis, trigger_build, abort_build, get_console_log


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


@jenkins_bp.route('/api/build', methods=['POST'])
@role_required('admin')
def build():
    success, message = trigger_build()
    if success:
        return jsonify({'queued': True, 'message': message})
    else:
        return jsonify({'queued': False, 'error': message}), 500



@jenkins_bp.route('/api/abort/<int:build_number>', methods=['POST'])
@role_required('admin')
def abort(build_number):
    success, message = abort_build(build_number)
    if success:
        return jsonify({'aborted': True, 'message': message})
    else:
        return jsonify({'aborted': False, 'error': message}), 500


@jenkins_bp.route('/api/log/<int:build_number>')
@role_required('admin', 'dev', 'qa')
def log_api(build_number):
    log = get_console_log(build_number)
    return jsonify({'log': log, 'build_number': build_number})



@jenkins_bp.route('/console/<int:build_number>')
@role_required('admin', 'dev', 'qa')
def console(build_number):
    return render_template('admin/console.html',
                           build_number=build_number,
                           username=session.get('username'),
                           role=session.get('role'))

#pipeline kpis 


@jenkins_bp.route('/pipeline_kpis')
@role_required('admin', 'dev', 'qa')
def pipeline_kpis():
    return render_template('admin/pipeline_kpis.html')