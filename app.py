import sqlite3
from flask import Flask, render_template, request, g, session, redirect, url_for, escape, abort, Response
from functools import wraps

DATABASE = "./assignment3.db"

# database code from in-lecture demo
# connects to the database
def get_db():
    db = getattr(g, "_database", None)
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

# returns the student number of the associated utorid
def get_student_num(utorid):
    sql="""
    SELECT student_num
    FROM users
    WHERE utorid = ?
    """
    return query_db(sql, (utorid,), True)[0]

# returns the name of the currently logged in user
def get_user_name():
    sql="""
    SELECT name
    FROM users
    WHERE utorid = ?
    """
    return query_db(sql, (session["utorid"],), True)[0]

app = Flask(__name__)
app.secret_key=b"xd"

# Custom flask decorator from https://pythonise.com/series/learning-flask/custom-flask-decorators
def login_or_role_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "utorid" not in session:
                return redirect(url_for("login"))
            elif role is not None and not session["role"] == role:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# this function gets called when the Flask app shuts down
# tears down the database connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        # close the database if we are connected to it
        db.close()

@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        sql = """
        SELECT users.utorid, user_password.password, roles.role_name
        FROM users
        INNER JOIN user_password
        ON users.utorid = user_password.utorid
        INNER JOIN roles
        ON users.role_id = roles.role_id
        WHERE users.utorid = ?;
        """
        results = query_db(sql, (request.form["uname"],))
        for result in results:
            if result[1] == request.form["pw"]:
                session["utorid"] = request.form["uname"]
                session["role"] = result[2]
                return redirect(url_for("home"))
        return "Incorrect utorid or password."
    elif "utorid" in session:
        return redirect(url_for("home"))
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("utorid", None)
    return redirect(url_for("login"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        utorid = request.form["utorid"]
        student_num = request.form["snum"]
        name = request.form["name"]
        password = request.form["pw"]
        c_password = request.form["c-pw"]
        role_name = request.form["acc-type"]

        if password != c_password:
            # Do some js stuff maybe? Let the user know the two pw fields aren"t the same
            r = Response()
            return r, 204
        
        sql_role_id = """
        SELECT role_id
        FROM roles
        WHERE role_name = ?
        """
        role_id = int(query_db(sql_role_id, (role_name,), True)[0])

        sql_users = """
        INSERT INTO users (utorid, student_num, name, role_id)
        VALUES (?, ?, ?, ?)
        """
        query_db(sql_users, (utorid, student_num, name, role_id))

        sql_user_password = """
        INSERT INTO user_password (utorid, password)
        VALUES (?, ?)
        """
        query_db(sql_user_password, (utorid, password))

        get_db().commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/index")
@login_or_role_required()
def home():
    return render_template("index.html", role = session["role"])

@app.route("/assignments")
@login_or_role_required()
def assignments():
    return render_template("assignments.html", role = session["role"])

@app.route("/feedback", methods=["GET","POST"])
@login_or_role_required()
def feedback():
    if request.method == "POST":
        feedback_text = request.form["message"]
        sql="""
        INSERT INTO anon_feedback(feedback_text)
        VALUES (?)
        """
        query_db(sql, (feedback_text,))
        get_db().commit()
    return render_template("feedback.html", role = session["role"])

@app.route("/labs")
@login_or_role_required()
def labs():
    return render_template("labs.html", role = session["role"])

@app.route("/team")
@login_or_role_required()
def team():
    return render_template("team.html", role = session["role"])

@app.route("/calendar")
@login_or_role_required()
def calendar():
    return render_template("calendar.html", role = session["role"])

@app.route("/student-home")
@login_or_role_required("student")
def student_home():
    sql = """
    SELECT assignment_name, mark
    FROM grades
    INNER JOIN assignments
    ON grades.assignment_id = assignments.assignment_id
    WHERE utorid = ?
    """
    grades_tuples = query_db(sql, (session["utorid"],))
    grades = {}
    for assignment_id, mark in grades_tuples:
        grades.setdefault(assignment_id, mark)
    return render_template("student-home.html", student_name = get_user_name(), grades = grades)

@app.route("/student-feedback", methods=["GET","POST"])
@login_or_role_required("student")
def student_feedback():
    sql_instructors = """
    SELECT utorid, name
    FROM users
    WHERE role_id = 1
    """
    instructors = query_db(sql_instructors)

    if request.method == "POST":
        values = ()
        instructor_id = request.form["regrade-id"]
        values += (instructor_id,)
        for i in range(1, 5):
            values += (request.form["feedback" + str(i)],)
        sql = """
        INSERT INTO student_feedback (instructor_id, feedback1, feedback2, feedback3, feedback4)
        VALUES (?, ?, ?, ?, ?)
        """
        query_db(sql, values)
        get_db().commit()
    return render_template("student-feedback.html", instructors = instructors)

@app.route("/regrade", methods=["GET","POST"])
@login_or_role_required("student")
def regrade_request():
    sql_assignments = """
    SELECT *
    FROM assignments
    ORDER BY assignment_id ASC
    """
    assignments = query_db(sql_assignments)

    if request.method == "POST":
        utorid = session["utorid"]
        student_num = get_student_num(utorid)
        assignment_id = request.form["regrade-id"]
        regrade_reason = request.form["regrade-reason"]

        sql = """
        INSERT INTO regrade_requests (utorid, student_num, assignment_id, regrade_reason)
        VALUES (?, ?, ?, ?)
        """
        query_db(sql, (utorid, student_num, assignment_id, regrade_reason))
        get_db().commit()
    return render_template("regrade.html", assignments = assignments)

@app.route("/instructor-home")
@login_or_role_required("instructor")
def instructor_home():
    return render_template("instructor-home.html", instructor_name = get_user_name())

@app.route("/instructor-viewfeedback")
@login_or_role_required("instructor")
def instructor_feedback():
    return render_template("instructor-home.html")

@app.route("/instructor-viewgrades")
@login_or_role_required("instructor")
def instructor_viewgrades():
    return render_template("instructor-home.html")

@app.route("/instructor-viewregrade")
@login_or_role_required("instructor")
def instructor_regrades():
    return render_template("instructor-home.html")

@app.route("/instructor-grading")
@login_or_role_required("instructor")
def instructor_grading():
    return render_template("instructor-home.html")

if __name__ == "__main__":
	app.run(debug = True)