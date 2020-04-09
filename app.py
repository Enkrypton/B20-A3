from functools import wraps
from flask import (Flask, render_template, request, g, session, redirect,
                   url_for, escape, abort, Response)
import sqlite3

DATABASE = "./assignment3.db"

# database code from in-lecture demo


def get_db():
    # Connects to the database
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def query_db(query, args=(), one=False):
    # Given a query, executes and returns the result
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_student_num(utorid):
    # Returns the student number of the associated utorid
    sql = """
    SELECT student_num
    FROM users
    WHERE utorid = ?
    """
    return query_db(sql, (utorid,), True)[0]


def get_utorid(student_num):
    # Returns the utorid of the assiciated student number
    sql = """
    SELECT utorid
    FROM users
    WHERE student_num = ?
    """
    return query_db(sql, (student_num,), True)[0]


def get_user_name():
    # Returns the name of the currently logged in user
    sql = """
    SELECT name
    FROM users
    WHERE utorid = ?
    """
    return query_db(sql, (session["utorid"],), True)[0]


def get_assignments():
    # returns all the assignments
    sql_assignments = """
    SELECT *
    FROM assignments
    ORDER BY assignment_id ASC
    """
    return query_db(sql_assignments)


app = Flask(__name__)
app.secret_key = b"xd"


def login_or_role_required(role=None):
    # Custom flask decorator from
    # https://pythonise.com/series/learning-flask/custom-flask-decorators
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


@app.teardown_appcontext
def close_connection(exception):
    # This function gets called when the Flask app shuts down
    # Tears down the database connection
    db = getattr(g, "_database", None)
    if db is not None:
        # close the database if we are connected to it
        db.close()


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
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
        return render_template("login.html", error=True)
    elif "utorid" in session:
        return redirect(url_for("home"))
    else:
        return render_template("login.html", error=False)


@app.route("/logout")
def logout():
    session.pop("utorid", None)
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        utorid = request.form["utorid"]
        student_num = request.form["snum"]
        name = request.form["name"]
        password = request.form["pw"]
        c_password = request.form["c-pw"]
        role_name = request.form["acc-type"]

        if password != c_password:
            # Do some js stuff maybe?
            # Let the user know the two pw fields aren't the same
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
    return render_template("index.html", role=session["role"])


@app.route("/assignments")
@login_or_role_required()
def assignments():
    return render_template("assignments.html", role=session["role"])


@app.route("/feedback", methods=["GET", "POST"])
@login_or_role_required()
def feedback():
    if request.method == "POST":
        feedback_text = request.form["message"]
        sql = """
        INSERT INTO anon_feedback(feedback_text)
        VALUES (?)
        """
        query_db(sql, (feedback_text,))
        get_db().commit()
    return render_template("feedback.html", role=session["role"])


@app.route("/labs")
@login_or_role_required()
def labs():
    return render_template("labs.html", role=session["role"])


@app.route("/team")
@login_or_role_required()
def team():
    return render_template("team.html", role=session["role"])


@app.route("/calendar")
@login_or_role_required()
def calendar():
    return render_template("calendar.html", role=session["role"])


@app.route("/student-home")
@login_or_role_required("student")
def student_home():
    sql = """
    SELECT assignment_id, mark
    FROM grades
    WHERE utorid = ?
    """
    grades_tuples = query_db(sql, (session["utorid"],))
    grades = {}
    for assignment_id, mark in grades_tuples:
        grades.setdefault(assignment_id, mark)
    assignments = get_assignments()
    return render_template("student-home.html",
                           student_name=get_user_name(),
                           grades=grades,
                           assignments=assignments)


@app.route("/student-feedback", methods=["GET", "POST"])
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
        INSERT INTO student_feedback (instructor_id, feedback1, feedback2, 
                                      feedback3, feedback4)
        VALUES (?, ?, ?, ?, ?)
        """
        query_db(sql, values)
        get_db().commit()
    return render_template("student-feedback.html",
                           instructors=instructors)


@app.route("/regrade", methods=["GET", "POST"])
@login_or_role_required("student")
def regrade_request():
    assignments = get_assignments()

    if request.method == "POST":
        utorid = session["utorid"]
        student_num = get_student_num(utorid)
        assignment_id = request.form["regrade-id"]
        regrade_reason = request.form["regrade-reason"]

        sql = """
        INSERT INTO regrade_requests (utorid, student_num, assignment_id, 
                                      regrade_reason)
        VALUES (?, ?, ?, ?)
        """
        query_db(sql, (utorid, student_num, assignment_id, regrade_reason))
        get_db().commit()
    return render_template("regrade.html",
                           assignments=assignments)


@app.route("/instructor-home")
@login_or_role_required("instructor")
def instructor_home():
    return render_template("instructor-home.html",
                           instructor_name=get_user_name())


@app.route("/instructor-viewfeedback")
@login_or_role_required("instructor")
def instructor_feedback():
    sql_feedback = """
    SELECT *
    FROM student_feedback
    WHERE instructor_id = ?
    """
    feedback = query_db(sql_feedback, (session['utorid'],))
    sql_anon_feedback = """
    SELECT *
    FROM anon_feedback
    """
    anon_feedback = query_db(sql_anon_feedback)
    return render_template("instructor-viewfeedback.html",
                           instructor_name=get_user_name(),
                           feedback=feedback,
                           anon_feedback=anon_feedback)


@app.route("/instructor-viewgrades")
@login_or_role_required("instructor")
def instructor_viewgrades():
    sql = """
    SELECT student_num, assignment_id, mark
    FROM grades
    ORDER BY student_num ASC, assignment_id ASC
    """
    grades_tuples = query_db(sql)
    grades = {}
    for student_num, assignment_id, mark in grades_tuples:
        if student_num in grades:
            grades[student_num].setdefault(assignment_id, mark)
        else:
            student_grades = {}
            student_grades.setdefault(assignment_id, mark)
            grades.setdefault(student_num, student_grades)
    assignments = get_assignments()
    return render_template("instructor-viewgrades.html",
                           instructor_name=get_user_name(),
                           grades=grades,
                           assignments=assignments)


@app.route("/instructor-viewregrade")
@login_or_role_required("instructor")
def instructor_regrades():
    sql = """
    SELECT student_num, assignment_name, regrade_reason
    FROM regrade_requests
    INNER JOIN assignments
    ON regrade_requests.assignment_id = assignments.assignment_id
    """
    regrade_requests = query_db(sql)
    return render_template("instructor-viewregrade.html",
                           instructor_name=get_user_name(),
                           regrade_requests=regrade_requests)


def has_mark(utorid, student_num, assignment_id):
    # Return if the student has a mark for the specified
    # assignment in the database
    sql = """
    SELECT *
    FROM grades
    WHERE utorid = ?
    AND student_num = ?
    AND assignment_id = ?
    """
    return query_db(sql, (utorid, student_num, assignment_id), True) is not None


def update_mark(utorid, student_num, assignment_id, new_mark):
    # Update the mark of an existing assignment
    sql = """
    UPDATE grades
    SET mark = ?
    WHERE utorid = ?
    AND student_num = ?
    AND assignment_id = ?
    """
    query_db(sql, (new_mark, utorid, student_num, assignment_id))
    get_db().commit()
    return


def insert_mark(utorid, student_num, assignment_id, mark):
    # Insert a mark for a new assignment
    sql = """
    INSERT INTO grades (utorid, student_num, assignment_id, mark)
    VALUES (?, ?, ?, ?)
    """
    query_db(sql, (utorid, student_num, assignment_id, mark))
    get_db().commit()
    return


@app.route("/instructor-grader", methods=["GET", "POST"])
@login_or_role_required("instructor")
def instructor_grading():
    assignments = get_assignments()
    if request.method == "POST":
        student_num = request.form["snum"]
        utorid = get_utorid(student_num)
        assignment_id = request.form["grade-id"]
        mark = request.form["grade"]
        if has_mark(utorid, student_num, assignment_id):
            update_mark(utorid, student_num, assignment_id, mark)
        else:
            insert_mark(utorid, student_num, assignment_id, mark)
    return render_template("instructor-grader.html",
                           instructor_name=get_user_name(),
                           assignments=assignments)


if __name__ == "__main__":
    app.run(debug=True)
