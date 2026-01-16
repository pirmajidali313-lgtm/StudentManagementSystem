from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"
DB_NAME = "students.db"

# ----------------- Database Connection -----------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------- Create Tables -----------------
def create_tables():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            marks INTEGER
        )
    """)
    # Create default admin if not exists
    admin = conn.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )
    conn.commit()
    conn.close()

# ----------------- Routes -----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect(url_for("students"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = "user"  # all new users are normal users

        hashed = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)",
                (username, hashed, role)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            return render_template("signup.html", error="Username already exists")
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------------- Students -----------------
@app.route("/students")
def students():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("students.html", students=students, role=session["role"])

@app.route("/add", methods=["GET","POST"])
def add_student():
    if session.get("role") != "admin":
        return redirect(url_for("students"))

    if request.method == "POST":
        name = request.form["name"]
        marks = int(request.form["marks"])

        conn = get_db()
        conn.execute("INSERT INTO students (name,marks) VALUES (?,?)", (name, marks))
        conn.commit()
        conn.close()
        return redirect(url_for("students"))
    return render_template("add_student.html")

@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit_student(id):
    if session.get("role") != "admin":
        return redirect(url_for("students"))

    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    if request.method == "POST":
        name = request.form["name"]
        marks = int(request.form["marks"])
        conn.execute("UPDATE students SET name=?, marks=? WHERE id=?", (name, marks, id))
        conn.commit()
        conn.close()
        return redirect(url_for("students"))
    conn.close()
    return render_template("edit_student.html", student=student)

@app.route("/delete/<int:id>")
def delete_student(id):
    if session.get("role") != "admin":
        return redirect(url_for("students"))

    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("students"))

# ----------------- Filter Pass/Fail -----------------
@app.route("/filter/<status>")
def filter_students(status):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    if status=="pass":
        students = conn.execute("SELECT * FROM students WHERE marks>=300").fetchall()
    elif status=="fail":
        students = conn.execute("SELECT * FROM students WHERE marks<300").fetchall()
    else:
        students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("students.html", students=students, role=session["role"])

# ----------------- Run App -----------------
if __name__ == "__main__":
    create_tables()
    app.run()