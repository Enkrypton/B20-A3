import sqlite3
from flask import Flask, render_template, request, g, session, redirect, url_for, escape, abort
from functools import wraps

DATABASE = './assignment3.db'

# database code from in-lecture demo
# connects to the database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# converts the tuples from get_db() into dictionaries
def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

# given a query, executes and returns the result
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

app = Flask(__name__)
app.secret_key=b'xd'

# Custom flask decorator from https://pythonise.com/series/learning-flask/custom-flask-decorators
def login_or_role_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if role is None:
                if 'username' not in session:
                    abort(403)
            elif not session['role'] == role:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# this function gets called when the Flask app shuts down
# tears down the database connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        # close the database if we are connected to it
        db.close()

@app.route('/')
def index():
    if 'username' in session:
        return 'Logged in as %s <a href="/logout">Logout</a>' % escape(session['username'])
    return 'You are not logged in'

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        sql = """
        SELECT users.utorid, user_password.password, roles.role_name
        FROM users
        INNER JOIN user_password
        ON users.utorid = user_password.utorid
        INNER JOIN roles
        ON users.role_id = roles.role_id
        WHERE users.utorid = ?;
        """
        results = query_db(sql, args=(request.form['uname'],), one=False)
        for result in results:
            if result[1] == request.form['pw']:
                session['username'] = request.form['uname']
                session['role'] = result[2]
                return redirect(url_for('home'))
        return "Incorrect username or password."
    elif 'username' in session:
        return redirect(url_for('home'))
    else:
        return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register')
def register():
    return render_template("register.html")

@app.route('/index')
@login_or_role_required()
def home():
    return render_template("index.html", role = session['role'])

@app.route('/assignments')
@login_or_role_required()
def assignments():
    return render_template("assignments.html", role = session['role'])

@app.route('/feedback')
@login_or_role_required()
def feedback():
    return render_template("feedback.html", role = session['role'])

@app.route('/labs')
@login_or_role_required()
def labs():
    return render_template("labs.html", role = session['role'])

@app.route('/team')
@login_or_role_required()
def team():
    return render_template("team.html", role = session['role'])

@app.route('/calendar')
@login_or_role_required()
def calendar():
    return render_template("calendar.html", role = session['role'])

@app.route('/student-home')
@login_or_role_required('student')
def student_home():
    return render_template("student-home.html")

@app.route('/student-feedback')
@login_or_role_required('student')
def student_feedback():
    return render_template("student-home.html")

@app.route('/instructor-panel')
@login_or_role_required('instructor')
def instructor_panel():
    return render_template("index.html")

if __name__ == '__main__':
	app.run(debug = True)