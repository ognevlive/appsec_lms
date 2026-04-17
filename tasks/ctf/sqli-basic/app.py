"""Intentionally vulnerable Flask app for SQL injection training."""
import sqlite3
import os

from flask import Flask, request, render_template_string

app = Flask(__name__)
FLAG = os.environ.get("CTF_FLAG", "FLAG{sql_injection_is_dangerous}")

DB_PATH = "/tmp/app.db"

HTML = """
<!DOCTYPE html>
<html>
<head><title>Login Portal</title>
<style>
  body { font-family: sans-serif; max-width: 500px; margin: 60px auto; background: #f5f5f5; }
  .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  input { width: 100%%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
  button { width: 100%%; padding: 10px; background: #1a73e8; color: white; border: none; border-radius: 4px; cursor: pointer; }
  .error { color: #d32f2f; margin: 10px 0; }
  .success { color: #2e7d32; margin: 10px 0; }
  h1 { text-align: center; }
</style>
</head>
<body>
<div class="card">
  <h1>Login Portal</h1>
  <p style="color:#888; text-align:center;">Internal admin panel</p>
  <form method="POST" action="/login">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <button type="submit">Login</button>
  </form>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  {% if flag %}<div class="success">Welcome, admin! Here is your flag: <b>{{ flag }}</b></div>{% endif %}
</div>
</body>
</html>
"""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES (1, 'admin', 'sup3r_s3cr3t_p@ss!', 'admin')")
        c.execute("INSERT INTO users VALUES (2, 'user', 'password123', 'user')")
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template_string(HTML, error=None, flag=None)


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # VULNERABLE: SQL injection here
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    try:
        c.execute(query)
        user = c.fetchone()
    except Exception as e:
        conn.close()
        return render_template_string(HTML, error=f"SQL Error: {e}", flag=None)

    conn.close()

    if user:
        return render_template_string(HTML, error=None, flag=FLAG)
    else:
        return render_template_string(HTML, error="Invalid credentials", flag=None)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
