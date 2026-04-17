"""Intentionally vulnerable Flask app for Stored XSS training."""
import sqlite3
import os

from flask import Flask, request, render_template_string, make_response
from markupsafe import Markup

app = Flask(__name__)
FLAG = os.environ.get("CTF_FLAG", "FLAG{stored_xss_cookie_theft}")

DB_PATH = "/tmp/guestbook.db"

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Guestbook</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 700px; margin: 0 auto; padding: 30px 20px; }
  h1 { text-align: center; color: #e94560; margin-bottom: 8px; }
  .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
  .card { background: #16213e; border-radius: 8px; padding: 24px; margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  input, textarea { width: 100%%; padding: 10px; margin: 8px 0; border: 1px solid #333;
                    border-radius: 4px; background: #0f3460; color: #e0e0e0; }
  textarea { height: 80px; resize: vertical; }
  button { width: 100%%; padding: 10px; background: #e94560; color: white; border: none;
           border-radius: 4px; cursor: pointer; font-size: 15px; margin-top: 8px; }
  button:hover { background: #c73652; }
  .comment { background: #0f3460; border-radius: 6px; padding: 16px; margin-bottom: 12px; }
  .comment .author { color: #e94560; font-weight: bold; margin-bottom: 6px; }
  .comment .text { color: #ccc; line-height: 1.5; }
  .comment .time { color: #666; font-size: 12px; margin-top: 6px; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
</style>
</head>
<body>
<div class="container">
  <h1>Guestbook</h1>
  <p class="subtitle">Online guestbook system</p>

  <div class="info">
    Admin periodically reviews all comments on this page.
    Admin's browser has a cookie with sensitive data.
  </div>

  <div class="card">
    <h3 style="margin-bottom: 12px; color: #e94560;">New Comment</h3>
    <form method="POST" action="/comment">
      <input name="author" placeholder="Name" required maxlength="50">
      <textarea name="text" placeholder="Comment..." required></textarea>
      <button type="submit">Submit</button>
    </form>
  </div>

  <h3 style="margin-bottom: 16px;">Comments ({{ comments|length }})</h3>
  {% for c in comments %}
  <div class="comment">
    <div class="author">{{ c[1] }}</div>
    <div class="text">{{ c[2] }}</div>
    <div class="time">{{ c[3] }}</div>
  </div>
  {% endfor %}

  {% if not comments %}
  <p style="text-align:center; color:#555;">No comments yet.</p>
  {% endif %}
</div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Admin Panel</title>
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0;
         display: flex; justify-content: center; align-items: center; min-height: 100vh; }
  .card { background: #16213e; padding: 30px; border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,.3); text-align: center; }
  h2 { color: #e94560; margin-bottom: 12px; }
  p { color: #888; }
</style>
</head>
<body>
<div class="card">
  <h2>Admin Panel</h2>
  <p>Admin session active. Cookie set.</p>
  <p style="color: #555; font-size: 12px; margin-top: 16px;">
    Admin reviews guestbook comments every few minutes.
  </p>
</div>
</body>
</html>
"""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS comments "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, text TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, author, text, created_at FROM comments ORDER BY id DESC")
    comments = c.fetchall()
    conn.close()

    # VULNERABLE: comments rendered without escaping using Markup()
    rendered_comments = []
    for comment in comments:
        rendered_comments.append(
            (comment[0], Markup(comment[1]), Markup(comment[2]), comment[3])
        )

    return render_template_string(PAGE_HTML, comments=rendered_comments)


@app.route("/comment", methods=["POST"])
def add_comment():
    author = request.form.get("author", "Anonymous")
    text = request.form.get("text", "")

    if author and text:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # VULNERABLE: storing raw user input, no sanitization
        c.execute("INSERT INTO comments (author, text) VALUES (?, ?)", (author, text))
        conn.commit()
        conn.close()

    return render_template_string(
        '<script>window.location="/";</script>'
    )


@app.route("/admin")
def admin():
    # Set a cookie with the flag - simulating admin's session
    resp = make_response(render_template_string(ADMIN_HTML))
    resp.set_cookie("admin_flag", FLAG, httponly=False)  # httponly=False is intentional
    return resp


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
