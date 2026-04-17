"""Intentionally vulnerable Flask app for CSRF training."""
import os
import json

from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "csrf-demo-secret-key-2024")
FLAG = os.environ.get("CTF_FLAG", "FLAG{csrf_no_token_validation}")

# In-memory bank accounts
accounts = {
    1: {"id": 1, "username": "admin", "password": "admin123", "balance": 10000},
    2: {"id": 2, "username": "user", "password": "user123", "balance": 500},
}

# Transfer log
transfers = []

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>SecureBank</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 700px; margin: 0 auto; padding: 30px 20px; }
  h1 { text-align: center; color: #e94560; margin-bottom: 8px; }
  .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
  .card { background: #16213e; border-radius: 8px; padding: 24px; margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  .card h3 { color: #e94560; margin-bottom: 12px; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
  input, select { width: 100%%; padding: 10px; margin: 6px 0; background: #0f3460; color: #e0e0e0;
                  border: 1px solid #333; border-radius: 4px; }
  button { width: 100%%; padding: 10px; background: #e94560; color: white; border: none;
           border-radius: 4px; cursor: pointer; font-size: 15px; margin-top: 8px; }
  button:hover { background: #c73652; }
  .balance { font-size: 32px; color: #2ecc71; font-weight: bold; text-align: center; padding: 20px 0; }
  .nav { display: flex; gap: 10px; margin-bottom: 20px; justify-content: center; }
  .nav a { color: #e94560; text-decoration: none; padding: 8px 16px; border: 1px solid #e94560;
           border-radius: 4px; font-size: 14px; }
  .nav a:hover { background: #e94560; color: white; }
  pre { background: #0f3460; padding: 16px; border-radius: 6px; overflow-x: auto;
        font-size: 13px; line-height: 1.5; color: #ccc; }
  .transfer-log { list-style: none; }
  .transfer-log li { padding: 8px 0; border-bottom: 1px solid #0f3460; color: #aaa; font-size: 13px; }
  .msg { padding: 12px; border-radius: 4px; margin-bottom: 16px; }
  .msg-success { background: #1b4332; color: #6fcf97; }
  .msg-error { background: #4a1c1c; color: #e94560; }
  textarea { width: 100%%; padding: 10px; height: 120px; background: #0f3460; color: #e0e0e0;
             border: 1px solid #333; border-radius: 4px; font-family: monospace; font-size: 13px;
             resize: vertical; }
</style>
</head>
<body>
<div class="container">
  <h1>SecureBank</h1>
  <p class="subtitle">Online Banking System</p>

  {% if not session.get('user_id') %}
  <!-- Login page -->
  <div class="info">
    You are not logged in. The CSRF challenge requires you to be logged in as <code>user</code>.<br>
    Credentials: <code>user / user123</code><br><br>
    Your goal: craft an HTML page that, when visited by admin, will make a transfer from admin's account to yours.
  </div>

  <div class="card">
    <h3>Login</h3>
    {% if error %}<div class="msg msg-error">{{ error }}</div>{% endif %}
    <form method="POST" action="/login">
      <input name="username" placeholder="Username" required>
      <input name="password" type="password" placeholder="Password" required>
      <button type="submit">Login</button>
    </form>
  </div>

  {% else %}
  <!-- Dashboard -->
  <div class="nav">
    <a href="/dashboard">Dashboard</a>
    <a href="/transfer">Transfer</a>
    <a href="/attack">Craft Attack</a>
    <a href="/logout">Logout</a>
  </div>
  {{ content }}
  {% endif %}
</div>
</body>
</html>
"""

DASHBOARD_HTML = """
<div class="card">
  <h3>Account: {{ username }}</h3>
  <div class="balance">${{ balance }}</div>
</div>

<div class="card">
  <h3>Transfer History</h3>
  <ul class="transfer-log">
    {% for t in transfers %}
    <li>Account #{{ t.from_id }} -> Account #{{ t.to_id }}: ${{ t.amount }}
        {% if t.get('note') %}<em>({{ t.note }})</em>{% endif %}</li>
    {% endfor %}
    {% if not transfers %}
    <li>No transfers yet.</li>
    {% endif %}
  </ul>
</div>

<div class="info">
  <strong>Transfer endpoint:</strong><br>
  <code>POST /transfer</code> with parameters: <code>to_account</code>, <code>amount</code><br>
  Note: there is NO CSRF token protection on this endpoint.
</div>
"""

TRANSFER_HTML = """
{% if msg %}<div class="msg {{ msg_class }}">{{ msg }}</div>{% endif %}

<div class="card">
  <h3>Transfer Funds</h3>
  <form method="POST" action="/transfer">
    <label style="color: #aaa; font-size: 13px;">To Account ID:</label>
    <input type="number" name="to_account" min="1" required placeholder="Account ID">
    <label style="color: #aaa; font-size: 13px;">Amount ($):</label>
    <input type="number" name="amount" min="1" required placeholder="Amount">
    <button type="submit">Send Transfer</button>
  </form>
</div>
"""

ATTACK_HTML = """
<div class="info">
  Craft a malicious HTML page below. When the admin "visits" it, the page should
  automatically submit a POST request to <code>/transfer</code> to send money
  from admin's account to yours (account #2).<br><br>
  Click "Simulate Admin Visit" to test if your attack works. The system will simulate
  the admin being logged in and visiting your HTML page.
</div>

<div class="card">
  <h3>Craft CSRF Payload</h3>
  <form method="POST" action="/simulate">
    <label style="color: #aaa; font-size: 13px;">Your malicious HTML:</label>
    <textarea name="html_payload" placeholder='<html>
<body>
  <form method="POST" action="http://localhost/transfer">
    <input type="hidden" name="to_account" value="2">
    <input type="hidden" name="amount" value="1000">
  </form>
  <script>document.forms[0].submit();</script>
</body>
</html>'>{{ payload }}</textarea>
    <button type="submit">Simulate Admin Visit</button>
  </form>
  {% if sim_result %}<div class="msg {{ sim_class }}">{{ sim_result }}</div>{% endif %}
</div>

<div class="card">
  <h3>Example CSRF Payload</h3>
  <pre>&lt;html&gt;
&lt;body&gt;
  &lt;form method="POST" action="http://TARGET/transfer"&gt;
    &lt;input type="hidden" name="to_account" value="YOUR_ID"&gt;
    &lt;input type="hidden" name="amount" value="1000"&gt;
  &lt;/form&gt;
  &lt;script&gt;document.forms[0].submit();&lt;/script&gt;
&lt;/body&gt;
&lt;/html&gt;</pre>
</div>
"""


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect("/dashboard")
    return render_template_string(PAGE_HTML, content="", error=None)


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    for uid, acc in accounts.items():
        if acc["username"] == username and acc["password"] == password:
            session["user_id"] = uid
            return redirect("/dashboard")

    return render_template_string(PAGE_HTML, content="", error="Invalid credentials")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard")
def dashboard():
    uid = session.get("user_id")
    if not uid:
        return redirect("/")
    acc = accounts.get(uid, {})
    user_transfers = [t for t in transfers if t["from_id"] == uid or t["to_id"] == uid]
    content = render_template_string(
        DASHBOARD_HTML,
        username=acc.get("username"),
        balance=acc.get("balance"),
        transfers=user_transfers,
    )
    return render_template_string(PAGE_HTML, content=content)


@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    uid = session.get("user_id")
    if not uid:
        return redirect("/")

    msg = None
    msg_class = ""

    if request.method == "POST":
        # VULNERABLE: no CSRF token validation
        try:
            to_account = int(request.form.get("to_account", 0))
            amount = int(request.form.get("amount", 0))
        except (ValueError, TypeError):
            to_account = 0
            amount = 0

        if to_account not in accounts:
            msg = "Destination account not found."
            msg_class = "msg-error"
        elif to_account == uid:
            msg = "Cannot transfer to yourself."
            msg_class = "msg-error"
        elif amount <= 0:
            msg = "Invalid amount."
            msg_class = "msg-error"
        elif accounts[uid]["balance"] < amount:
            msg = "Insufficient funds."
            msg_class = "msg-error"
        else:
            accounts[uid]["balance"] -= amount
            accounts[to_account]["balance"] += amount
            transfers.append({"from_id": uid, "to_id": to_account, "amount": amount})
            msg = f"Transfer of ${amount} to account #{to_account} successful!"
            msg_class = "msg-success"

    content = render_template_string(TRANSFER_HTML, msg=msg, msg_class=msg_class)
    return render_template_string(PAGE_HTML, content=content)


@app.route("/attack")
def attack_page():
    uid = session.get("user_id")
    if not uid:
        return redirect("/")
    content = render_template_string(ATTACK_HTML, payload="", sim_result=None, sim_class="")
    return render_template_string(PAGE_HTML, content=content)


@app.route("/simulate", methods=["POST"])
def simulate():
    """Simulate admin visiting the malicious page.
    We check if the HTML payload contains a form posting to /transfer
    with to_account and amount parameters.
    """
    uid = session.get("user_id")
    if not uid:
        return redirect("/")

    html_payload = request.form.get("html_payload", "")

    # Simple simulation: check if the payload would cause a transfer
    # In reality, we just check if money arrives in user's account
    payload_lower = html_payload.lower()

    # Check for basic CSRF indicators
    has_form = "<form" in payload_lower and "transfer" in payload_lower
    has_to_account = "to_account" in payload_lower
    has_amount = "amount" in payload_lower
    has_submit = "submit()" in payload_lower or 'type="submit"' in payload_lower

    if has_form and has_to_account and has_amount and has_submit:
        # Extract target account from payload (simple parsing)
        import re
        to_match = re.search(r'name=["\']to_account["\'].*?value=["\'](\d+)["\']', html_payload, re.IGNORECASE)
        amount_match = re.search(r'name=["\']amount["\'].*?value=["\'](\d+)["\']', html_payload, re.IGNORECASE)

        if not to_match or not amount_match:
            # Try reverse order: value before name
            to_match = re.search(r'value=["\'](\d+)["\'].*?name=["\']to_account["\']', html_payload, re.IGNORECASE)
            amount_match = re.search(r'value=["\'](\d+)["\'].*?name=["\']amount["\']', html_payload, re.IGNORECASE)

        if to_match and amount_match:
            to_account = int(to_match.group(1))
            amount = int(amount_match.group(1))

            if to_account == uid and amount > 0:
                # Simulate the transfer from admin
                admin_id = 1
                if accounts[admin_id]["balance"] >= amount:
                    accounts[admin_id]["balance"] -= amount
                    accounts[to_account]["balance"] += amount
                    transfers.append({
                        "from_id": admin_id,
                        "to_id": to_account,
                        "amount": amount,
                        "note": "CSRF attack",
                    })
                    sim_result = (
                        f"CSRF attack successful! Admin transferred ${amount} to your account. "
                        f"Flag: {FLAG}"
                    )
                    sim_class = "msg-success"
                else:
                    sim_result = "Admin has insufficient funds."
                    sim_class = "msg-error"
            else:
                sim_result = "The payload should transfer money to YOUR account (account #2)."
                sim_class = "msg-error"
        else:
            sim_result = "Could not parse to_account/amount values from your payload."
            sim_class = "msg-error"
    else:
        missing = []
        if not has_form:
            missing.append("form with action to /transfer")
        if not has_to_account:
            missing.append("to_account field")
        if not has_amount:
            missing.append("amount field")
        if not has_submit:
            missing.append("auto-submit mechanism")
        sim_result = f"Invalid CSRF payload. Missing: {', '.join(missing)}"
        sim_class = "msg-error"

    content = render_template_string(
        ATTACK_HTML, payload=html_payload, sim_result=sim_result, sim_class=sim_class
    )
    return render_template_string(PAGE_HTML, content=content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
