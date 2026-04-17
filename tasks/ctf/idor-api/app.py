"""Intentionally vulnerable Flask app for IDOR training."""
import os
import json

from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
FLAG = os.environ.get("CTF_FLAG", "FLAG{idor_access_control_is_broken}")

# Simulated user database
USERS = {
    1: {"id": 1, "username": "admin", "role": "admin", "token": "token-admin-a1b2c3"},
    2: {"id": 2, "username": "user", "role": "user", "token": "token-user-x9y8z7"},
    3: {"id": 3, "username": "guest", "role": "user", "token": "token-guest-m4n5o6"},
}

# Simulated document database
DOCUMENTS = {
    1: {"id": 1, "owner_id": 1, "title": "Confidential Report",
        "content": f"TOP SECRET: {FLAG}", "classification": "secret"},
    2: {"id": 2, "owner_id": 1, "title": "Admin Notes",
        "content": "System maintenance scheduled for next week.", "classification": "internal"},
    3: {"id": 3, "owner_id": 2, "title": "My Report",
        "content": "Quarterly sales report for Q3 2024.", "classification": "normal"},
    4: {"id": 4, "owner_id": 2, "title": "Personal Notes",
        "content": "TODO: finish the security training.", "classification": "normal"},
    5: {"id": 5, "owner_id": 3, "title": "Guest Document",
        "content": "Welcome to the document management system.", "classification": "normal"},
}

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Document Management API</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 800px; margin: 0 auto; padding: 30px 20px; }
  h1 { text-align: center; color: #e94560; margin-bottom: 8px; }
  .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
  .card { background: #16213e; border-radius: 8px; padding: 24px; margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  .card h3 { color: #e94560; margin-bottom: 12px; }
  pre { background: #0f3460; padding: 16px; border-radius: 6px; overflow-x: auto;
        font-size: 13px; line-height: 1.5; color: #ccc; }
  code { color: #7ec8e3; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
  table { width: 100%%; border-collapse: collapse; margin-top: 12px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #0f3460; }
  th { color: #e94560; font-size: 13px; }
  td { color: #ccc; font-size: 13px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
           font-size: 11px; font-weight: bold; }
  .badge-secret { background: #e94560; color: white; }
  .badge-internal { background: #f39c12; color: #333; }
  .badge-normal { background: #2ecc71; color: #333; }
  .try-it { margin-top: 16px; }
  .try-it input { padding: 8px; background: #0f3460; color: #e0e0e0; border: 1px solid #333;
                  border-radius: 4px; width: 60px; text-align: center; }
  .try-it button { padding: 8px 16px; background: #e94560; color: white; border: none;
                   border-radius: 4px; cursor: pointer; }
  #result { margin-top: 12px; }
</style>
</head>
<body>
<div class="container">
  <h1>Document Management System</h1>
  <p class="subtitle">REST API - Authorized as: <strong>user</strong> (user_id=2)</p>

  <div class="info">
    You are logged in as <code>user</code> (user_id=2) with token <code>token-user-x9y8z7</code>.<br>
    Your documents are available via the API. Can you access other users' documents?
  </div>

  <div class="card">
    <h3>Your Documents</h3>
    <table>
      <tr><th>ID</th><th>Title</th><th>Classification</th></tr>
      <tr>
        <td>3</td><td>My Report</td>
        <td><span class="badge badge-normal">normal</span></td>
      </tr>
      <tr>
        <td>4</td><td>Personal Notes</td>
        <td><span class="badge badge-normal">normal</span></td>
      </tr>
    </table>
  </div>

  <div class="card">
    <h3>API Endpoints</h3>
    <pre>GET /api/me
    Returns current user info.
    Header: Authorization: Bearer token-user-x9y8z7

GET /api/documents
    Returns list of your documents.
    Header: Authorization: Bearer token-user-x9y8z7

GET /api/documents/{id}
    Returns document by ID.
    Header: Authorization: Bearer token-user-x9y8z7</pre>
  </div>

  <div class="card">
    <h3>Try API</h3>
    <div class="try-it">
      <label style="color: #aaa;">Document ID:</label>
      <input type="number" id="doc-id" value="3" min="1">
      <button onclick="fetchDoc()">Fetch Document</button>
    </div>
    <pre id="result" style="margin-top: 12px; display: none;"></pre>
  </div>
</div>

<script>
async function fetchDoc() {
    const id = document.getElementById('doc-id').value;
    const res = await fetch('/api/documents/' + id, {
        headers: {'Authorization': 'Bearer token-user-x9y8z7'}
    });
    const data = await res.json();
    const el = document.getElementById('result');
    el.style.display = 'block';
    el.textContent = JSON.stringify(data, null, 2);
}
</script>
</body>
</html>
"""


def get_user_from_token(req):
    """Extract user from Authorization header."""
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        for uid, user in USERS.items():
            if user["token"] == token:
                return user
    return None


@app.route("/")
def docs_page():
    return render_template_string(PAGE_HTML)


@app.route("/api/me")
def api_me():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized. Provide Authorization: Bearer <token>"}), 401
    return jsonify({"id": user["id"], "username": user["username"], "role": user["role"]})


@app.route("/api/documents")
def api_documents():
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    # Only return documents belonging to the current user
    user_docs = [
        {"id": d["id"], "title": d["title"], "classification": d["classification"]}
        for d in DOCUMENTS.values()
        if d["owner_id"] == user["id"]
    ]
    return jsonify({"documents": user_docs})


@app.route("/api/documents/<int:doc_id>")
def api_document(doc_id):
    user = get_user_from_token(request)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    doc = DOCUMENTS.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    # VULNERABLE: No check if the user owns this document (IDOR)
    return jsonify({
        "id": doc["id"],
        "title": doc["title"],
        "content": doc["content"],
        "classification": doc["classification"],
        "owner_id": doc["owner_id"],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
