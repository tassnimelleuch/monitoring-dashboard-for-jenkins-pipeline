from flask import render_template,request, redirect, url_for
app= Flask(__name__)
app.secret_key = 'my-secret-key-change-this-later'
@app.route('/login', methods=['GET', 'POST'])

def login (): 
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return render_template('/auth/login.html', error='not authorized')

    return render_template('/auth/login.html')

@app.route('/dashboard')
def dashboard():
    return '<h1>Welcome to the Dashboard!</h1>'


if __name__ == '__main__':
    app.run(debug=True)