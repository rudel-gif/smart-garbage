from flask import Flask, request, render_template, redirect, url_for, session # type: ignore
import mysql.connector # type: ignore

app = Flask(__name__)
app.secret_key = "secret123"

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Rudrayani@123",
        database="collector"
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            phone VARCHAR(15),
            vehicle_no VARCHAR(20),
            address TEXT,
            email VARCHAR(100) UNIQUE,
            area VARCHAR(50),
            password VARCHAR(255)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            description TEXT,
            location VARCHAR(255),
            status ENUM('pending','accepted','completed') DEFAULT 'pending',
            collector_id INT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email,password))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user :
            session['user_id'] = user['id']
            session['name'] = user['name']
            return redirect(url_for('index'))

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        vehicle_no = request.form.get("vehicle_no")
        address = request.form.get("address")
        email = request.form.get("email")
        area = request.form.get("area")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Check if email already exists
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template("register.html", error="Email already registered")

            # Insert new user
            cur.execute("""
                INSERT INTO users (name, phone, vehicle_no, address, email, area, password)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (name, phone, vehicle_no, address, email, area, password))

            conn.commit()
            user_id = cur.lastrowid
            cur.close()
            conn.close()

            # Set session
            session["user_id"] = user_id
            session["name"] = name

            return redirect(url_for("index"))

        except Exception as e:
            return f"Error: {e}"

    return render_template("register.html")


@app.route("/tasks")
def tasks():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND collector_id IS NULL
    """)
    tasks = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("tasks.html", tasks=tasks)

@app.route("/accept_task/<int:task_id>", methods=["POST"])
def accept_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    collector_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tasks
        SET status = 'accepted',
            collector_id = %s
        WHERE id = %s
          AND status = 'pending'
          AND collector_id IS NULL
    """, (collector_id, task_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("index"))

@app.route("/complete_task/<int:task_id>")
def complete_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tasks
        SET status='completed'
        WHERE id=%s
    """, (task_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("tasks"))

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    collector_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT name, phone, email, vehicle_no, area
        FROM users
        WHERE id = %s
    """, (collector_id,))
    collector = cur.fetchone()

    cur.execute("""
        SELECT
            SUM(status='accepted') AS accepted_tasks,
            SUM(status='pending') AS pending_tasks,
            SUM(status='completed') AS completed_tasks
        FROM tasks
        WHERE collector_id = %s
    """, (collector_id,))
    stats = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "profile.html",
        collector=collector,
        stats=stats
    )


@app.route("/index")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    collector_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # 1️Pending tasks (NOT accepted by anyone)
    cur.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
    """)
    pending_tasks = cur.fetchall()

    # 2️My accepted tasks
    cur.execute("""
        SELECT * FROM tasks
        WHERE collector_id = %s AND status = 'accepted'
    """, (collector_id,))
    my_tasks = cur.fetchall()

    # 3️ Completed tasks count
    cur.execute("""
        SELECT COUNT(*) AS completed_count
        FROM tasks
        WHERE collector_id = %s AND status = 'completed'
    """, (collector_id,))
    completed = cur.fetchone()["completed_count"]

    # 4 Pending count
    pending_count = len(pending_tasks)

    # 5Accepted count
    accepted_count = len(my_tasks)

    cur.close()
    conn.close()

    return render_template(
        "index.html",
        username=session["name"],
        pending_tasks=pending_tasks,
        my_tasks=my_tasks,
        pending_count=pending_count,
        accepted_count=accepted_count,
        completed_count=completed
    )



@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

@app.route("/")
def home():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)

