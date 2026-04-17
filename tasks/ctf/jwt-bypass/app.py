"""Intentionally vulnerable Flask app for JWT Bypass training."""
import os
import json
import base64
import hmac
import hashlib
import time

from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
FLAG = os.environ.get("CTF_FLAG", "FLAG{jwt_none_algorithm_bypass}")
SECRET_KEY = os.environ.get("JWT_SECRET", "super-secret-key-2024")


def base64url_encode(data):
    """Base64url encode without padding."""
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def base64url_decode(data):
    """Base64url decode with padding restoration."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt(payload):
    """Create a JWT token with HS256."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header))
    payload_b64 = base64url_encode(json.dumps(payload))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token):
    """Verify JWT token - VULNERABLE: accepts alg:none."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64 = parts[0]
        payload_b64 = parts[1]
        signature_b64 = parts[2]

        header = json.loads(base64url_decode(header_b64))
        payload = json.loads(base64url_decode(payload_b64))

        alg = header.get("alg", "HS256")

        # VULNERABLE: accepting "none" algorithm - skips signature verification
        if alg.lower() == "none" or alg == "":
            return payload

        # Normal HS256 verification
        if alg == "HS256":
            signing_input = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
            ).digest()
            actual_sig = base64url_decode(signature_b64)
            if hmac.compare_digest(expected_sig, actual_sig):
                return payload

        return None
    except Exception:
        return None


# Generate a user token on startup
USER_TOKEN = create_jwt({"sub": "user", "role": "user", "iat": int(time.time())})

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>JWT Auth Service</title>
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
        font-size: 13px; line-height: 1.5; color: #ccc; word-break: break-all; white-space: pre-wrap; }
  code { color: #7ec8e3; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
  input[type="text"], textarea { width: 100%%; padding: 10px; background: #0f3460; color: #e0e0e0;
                                  border: 1px solid #333; border-radius: 4px; font-family: monospace;
                                  font-size: 13px; }
  textarea { height: 80px; resize: vertical; }
  button { padding: 10px 20px; background: #e94560; color: white; border: none;
           border-radius: 4px; cursor: pointer; font-size: 14px; margin-top: 8px; }
  button:hover { background: #c73652; }
  .result { margin-top: 12px; }
  .section-label { color: #aaa; font-size: 12px; margin-bottom: 4px; }
  table { width: 100%%; border-collapse: collapse; }
  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #0f3460; color: #ccc; font-size: 13px; }
  th { color: #e94560; }
</style>
</head>
<body>
<div class="container">
  <h1>JWT Authentication Service</h1>
  <p class="subtitle">API with JWT-based access control</p>

  <div class="info">
    You have received a valid JWT token for the <code>user</code> role.<br>
    The <code>/api/admin</code> endpoint requires <code>role: admin</code> in the token.<br>
    Find a way to bypass the JWT verification and access the admin endpoint.
  </div>

  <div class="card">
    <h3>Your JWT Token</h3>
    <pre>{{ user_token }}</pre>
    <p style="color: #666; font-size: 12px; margin-top: 8px;">
      Tip: JWT = Base64(header).Base64(payload).Base64(signature)
    </p>
  </div>

  <div class="card">
    <h3>Decoded Token</h3>
    <p class="section-label">Header:</p>
    <pre>{{ header_decoded }}</pre>
    <p class="section-label" style="margin-top: 8px;">Payload:</p>
    <pre>{{ payload_decoded }}</pre>
  </div>

  <div class="card">
    <h3>API Endpoints</h3>
    <table>
      <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
      <tr><td><code>/api/profile</code></td><td>GET</td><td>Returns user profile (any valid token)</td></tr>
      <tr><td><code>/api/admin</code></td><td>GET</td><td>Admin panel - requires role=admin</td></tr>
    </table>
    <pre style="margin-top: 12px;">Authorization: Bearer &lt;your_jwt_token&gt;</pre>
  </div>

  <div class="card">
    <h3>Test Token</h3>
    <textarea id="token-input" placeholder="Paste your JWT token here...">{{ user_token }}</textarea>
    <div style="display: flex; gap: 8px; margin-top: 8px;">
      <button onclick="testProfile()">Test /api/profile</button>
      <button onclick="testAdmin()">Test /api/admin</button>
      <button onclick="decodeToken()">Decode</button>
    </div>
    <pre id="result" style="margin-top: 12px; display: none;"></pre>
  </div>
</div>

<script>
async function testEndpoint(path) {
    const token = document.getElementById('token-input').value.trim();
    const res = await fetch(path, {
        headers: {'Authorization': 'Bearer ' + token}
    });
    const data = await res.json();
    const el = document.getElementById('result');
    el.style.display = 'block';
    el.textContent = JSON.stringify(data, null, 2);
}
function testProfile() { testEndpoint('/api/profile'); }
function testAdmin() { testEndpoint('/api/admin'); }
function decodeToken() {
    const token = document.getElementById('token-input').value.trim();
    const parts = token.split('.');
    if (parts.length !== 3) {
        document.getElementById('result').style.display = 'block';
        document.getElementById('result').textContent = 'Invalid JWT format (need 3 parts separated by dots)';
        return;
    }
    try {
        const header = JSON.parse(atob(parts[0].replace(/-/g,'+').replace(/_/g,'/')));
        const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
        const el = document.getElementById('result');
        el.style.display = 'block';
        el.textContent = 'Header: ' + JSON.stringify(header, null, 2) + '\\n\\nPayload: ' + JSON.stringify(payload, null, 2);
    } catch(e) {
        document.getElementById('result').style.display = 'block';
        document.getElementById('result').textContent = 'Decode error: ' + e.message;
    }
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    # Decode token parts for display
    parts = USER_TOKEN.split(".")
    try:
        header_decoded = json.dumps(json.loads(base64url_decode(parts[0])), indent=2)
        payload_decoded = json.dumps(json.loads(base64url_decode(parts[1])), indent=2)
    except Exception:
        header_decoded = "Error decoding"
        payload_decoded = "Error decoding"

    return render_template_string(
        PAGE_HTML,
        user_token=USER_TOKEN,
        header_decoded=header_decoded,
        payload_decoded=payload_decoded,
    )


@app.route("/api/profile")
def api_profile():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing Authorization header"}), 401

    token = auth[7:]
    payload = verify_jwt(token)
    if not payload:
        return jsonify({"error": "Invalid or expired token"}), 401

    return jsonify({
        "user": payload.get("sub", "unknown"),
        "role": payload.get("role", "unknown"),
        "message": f"Welcome, {payload.get('sub', 'unknown')}!",
    })


@app.route("/api/admin")
def api_admin():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing Authorization header"}), 401

    token = auth[7:]
    payload = verify_jwt(token)
    if not payload:
        return jsonify({"error": "Invalid or expired token"}), 401

    if payload.get("role") != "admin":
        return jsonify({
            "error": "Access denied",
            "message": f"Your role is '{payload.get('role', 'unknown')}', but 'admin' is required.",
        }), 403

    return jsonify({
        "message": "Welcome to the admin panel!",
        "flag": FLAG,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
