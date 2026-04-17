"""Flask app for SAST Challenge CTF task - find vulnerabilities in code."""
import os

from flask import Flask, request, render_template_string

app = Flask(__name__)
FLAG = os.environ.get("CTF_FLAG", "FLAG{sast_found_6_vulnerabilities}")

CORRECT_COUNT = 6

# The "vulnerable application" source code that students must analyze
VULNERABLE_CODE = '''import sqlite3
import os
import pickle
import hashlib
from flask import Flask, request, send_file

app = Flask(__name__)

DB_PASSWORD = "admin123"  # Hardcoded credentials (CWE-798)
DB_USER = "root"

def get_db():
    return sqlite3.connect("/tmp/app.db")

@app.route("/search")
def search():
    query = request.args.get("q", "")
    conn = get_db()
    # SQL Injection (CWE-89)
    cursor = conn.execute(f"SELECT * FROM products WHERE name LIKE \'%{query}%\'")
    results = cursor.fetchall()
    return {"results": results}

@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    # Command Injection (CWE-78)
    output = os.popen(f"ping -c 1 {host}").read()
    return {"output": output}

@app.route("/download")
def download():
    filename = request.args.get("file", "")
    # Path Traversal (CWE-22)
    filepath = os.path.join("/var/data/", filename)
    return send_file(filepath)

@app.route("/load_session", methods=["POST"])
def load_session():
    data = request.get_data()
    # Insecure Deserialization (CWE-502)
    session = pickle.loads(data)
    return {"user": session.get("user", "unknown")}

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    # Weak Cryptography - MD5 for password hashing (CWE-327)
    password_hash = hashlib.md5(password.encode()).hexdigest()
    conn = get_db()
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                 (username, password_hash))
    conn.commit()
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(debug=True)
'''

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>SAST Challenge</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 900px; margin: 0 auto; padding: 30px 20px; }
  h1 { text-align: center; color: #e94560; margin-bottom: 8px; }
  .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
  .card { background: #16213e; border-radius: 8px; padding: 24px; margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  .card h3 { color: #e94560; margin-bottom: 12px; }
  pre { background: #0f3460; padding: 16px; border-radius: 6px; overflow-x: auto;
        font-size: 13px; line-height: 1.6; color: #ccc; }
  .line-numbers { color: #555; user-select: none; }
  input[type="number"] { padding: 10px; width: 80px; background: #0f3460; color: #e0e0e0;
                         border: 1px solid #333; border-radius: 4px; text-align: center;
                         font-size: 18px; }
  button { padding: 10px 24px; background: #e94560; color: white; border: none;
           border-radius: 4px; cursor: pointer; font-size: 15px; margin-left: 12px; }
  button:hover { background: #c73652; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
  .result { margin-top: 16px; padding: 12px; border-radius: 4px; font-size: 15px; }
  .result.success { background: #1b4332; color: #6fcf97; }
  .result.error { background: #4a1c1c; color: #e94560; }
  .vuln-list { list-style: none; margin-top: 12px; }
  .vuln-list li { padding: 6px 0; color: #aaa; font-size: 13px; }
  .vuln-list li code { color: #e94560; }
</style>
</head>
<body>
<div class="container">
  <h1>SAST: Code Review Challenge</h1>
  <p class="subtitle">Find all security vulnerabilities in the source code below</p>

  <div class="info">
    Analyze the Python source code below. Find all security vulnerabilities.<br>
    Enter the total count of unique vulnerabilities found.
    Use CWE classification to identify vulnerability types.<br><br>
    Hint: look for OWASP Top 10 issues, hardcoded secrets, weak crypto, and unsafe deserialization.
  </div>

  <div class="card">
    <h3>app.py - Target Application</h3>
    <pre>{{ code }}</pre>
  </div>

  <div class="card">
    <h3>Submit Answer</h3>
    <form method="POST" action="/check" style="display: flex; align-items: center;">
      <label style="margin-right: 12px; color: #aaa;">Number of vulnerabilities:</label>
      <input type="number" name="count" min="1" max="20" required>
      <button type="submit">Check</button>
    </form>
    {% if result %}
    <div class="result {{ result_class }}">{{ result }}</div>
    {% endif %}
  </div>

  <div class="card">
    <h3>Vulnerability Types (CWE Reference)</h3>
    <ul class="vuln-list">
      <li><code>CWE-78</code> - OS Command Injection</li>
      <li><code>CWE-89</code> - SQL Injection</li>
      <li><code>CWE-22</code> - Path Traversal</li>
      <li><code>CWE-327</code> - Use of Broken Crypto Algorithm</li>
      <li><code>CWE-502</code> - Deserialization of Untrusted Data</li>
      <li><code>CWE-798</code> - Hardcoded Credentials</li>
      <li><code>CWE-79</code> - Cross-site Scripting (XSS)</li>
      <li><code>CWE-200</code> - Information Exposure</li>
    </ul>
  </div>
</div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE_HTML, code=VULNERABLE_CODE, result=None, result_class="")


@app.route("/check", methods=["POST"])
def check():
    try:
        count = int(request.form.get("count", 0))
    except (ValueError, TypeError):
        count = 0

    if count == CORRECT_COUNT:
        result = f"Correct! You found all {CORRECT_COUNT} vulnerabilities. Flag: {FLAG}"
        result_class = "success"
    elif count > CORRECT_COUNT:
        result = f"Too many. You said {count}, but some may not be real vulnerabilities. Try again."
        result_class = "error"
    else:
        result = f"Not enough. You found {count}, but there are more. Keep looking!"
        result_class = "error"

    return render_template_string(
        PAGE_HTML, code=VULNERABLE_CODE, result=result, result_class=result_class
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
