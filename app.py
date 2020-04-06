import sqlite3
from flask import Flask, render_template, request, g, session, redirect, url_for, escape
from flask_login import LoginManager
from flask_user import roles_required

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
app.secret_key='xd'

@app.route('/')
def index():
    if 'username' in session:
        return 'Logged in as %s <a href="/logout">Logout</a>' % escape(session['username'])
    return 'You are not logged in'

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        session['username']=request.form['uname']
        return redirect(url_for('home'))
    elif 'username' in session:
        return redirect(url_for('home'))
    else:
        # return '''
        #     <form method="post">
        #     <p><input type=text name=username>
        #     <p><input type=submit value=Login>
        #     </form>
        #     '''
        return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register.html')
def register():
    return render_template("register.html")

@app.route('/index.html')
def home():
    return render_template("index.html")


if __name__ == '__main__':
	app.run(debug = True)