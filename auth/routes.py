from flask import render_template, request, redirect, url_for, session
from auth import auth_bp
from models import users, find_user, get_pending_count



@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', '')

        # Validate
        error = None
        if not username or not password:
            error = 'All fields are required.'

        elif find_user(username):
            error = f'Username "{username}" is already taken.'

        if error:
            # Re-render keeping what the user already typed
            return render_template('auth/register.html',
                                   error=error, username=username, role=role)

        # Save new user as pending
        users.append({
            'username': username,
            'password': password,
            'role':     role,
            'status':   'pending'  # admin must approve before they can log in
        })

        # Pass a one-time message to the login page
        session['flash'] = 'Account requested! Please wait for admin approval.'
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', error=None, username='', role='')


# ── LOGIN ──────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Pop reads the flash message once and deletes it from session
    flash = session.pop('flash', None)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = find_user(username)

        # Wrong username or password
        if not user or user['password'] != password:
            return render_template('auth/login.html',
                                   error='Invalid username or password.', flash=None)

        # Correct credentials — check status
        if user['status'] == 'pending':
            return render_template('auth/login.html',
                                   error='Your account is awaiting admin approval.', flash=None)

        if user['status'] == 'rejected':
            return render_template('auth/login.html',
                                   error='Your registration was rejected.', flash=None)

        # All good — store in session (this is how Flask remembers who is logged in)
        session['username'] = user['username']
        session['role']     = user['role']

        if user['role'] == 'admin':
            return redirect(url_for('auth.admin_users'))
        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html', error=None, flash=flash)


# ── LOGOUT ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    session.clear()  # wipe the session — user is now logged out
    return redirect(url_for('auth.login'))


# ── ADMIN USER MANAGEMENT ──────────────────────────────────────────────────────

@auth_bp.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    return render_template('auth/admin_users.html',
                           pending  = [u for u in users if u['status'] == 'pending'],
                           approved = [u for u in users if u['status'] == 'approved' and u['role'] != 'admin'],
                           rejected = [u for u in users if u['status'] == 'rejected'],
                           pending_count = get_pending_count())


@auth_bp.route('/admin/approve/<username>', methods=['POST'])
def approve_user(username):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    user = find_user(username)
    if user:
        user['status'] = 'approved'
    return redirect(url_for('auth.admin_users'))


@auth_bp.route('/admin/reject/<username>', methods=['POST'])
def reject_user(username):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    user = find_user(username)
    if user:
        user['status'] = 'rejected'
    return redirect(url_for('auth.admin_users'))