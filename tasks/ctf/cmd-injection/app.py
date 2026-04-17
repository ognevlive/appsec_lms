"""Intentionally vulnerable Flask app for Command Injection training."""
import os

from flask import Flask, request, render_template_string

app = Flask(__name__)

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Ping Service</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 700px; margin: 0 auto; padding: 30px 20px; }
  h1 { text-align: center; color: #e94560; margin-bottom: 8px; }
  .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
  .card { background: #16213e; border-radius: 8px; padding: 24px; margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  .card h3 { color: #e94560; margin-bottom: 12px; }
  input[type="text"] { width: 100%%; padding: 12px; background: #0f3460; color: #e0e0e0;
                       border: 1px solid #333; border-radius: 4px; font-family: monospace;
                       font-size: 15px; margin-bottom: 12px; }
  button { width: 100%%; padding: 12px; background: #e94560; color: white; border: none;
           border-radius: 4px; cursor: pointer; font-size: 15px; }
  button:hover { background: #c73652; }
  pre { background: #0f3460; padding: 16px; border-radius: 6px; overflow-x: auto;
        font-size: 13px; line-height: 1.5; color: #ccc; white-space: pre-wrap;
        max-height: 400px; overflow-y: auto; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
  .status { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
  .status .dot { width: 10px; height: 10px; border-radius: 50%%; background: #2ecc71; }
  .status span { color: #888; font-size: 13px; }
</style>
</head>
<body>
<div class="container">
  <h1>Ping Service</h1>
  <p class="subtitle">Server availability checker</p>

  <div class="status">
    <div class="dot"></div>
    <span>Service is running</span>
  </div>

  <div class="info">
    Enter an IP address or hostname to check its availability using <code>ping</code>.<br>
    The service executes <code>ping -c 1 &lt;your_input&gt;</code> on the server.
  </div>

  <div class="card">
    <h3>Check Host</h3>
    <form method="POST" action="/ping">
      <input type="text" name="ip" placeholder="Enter IP address (e.g. 8.8.8.8)"
             value="{{ ip }}" required>
      <button type="submit">Ping</button>
    </form>
  </div>

  {% if output %}
  <div class="card">
    <h3>Result</h3>
    <pre>$ ping -c 1 {{ ip }}

{{ output }}</pre>
  </div>
  {% endif %}
</div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE_HTML, ip="", output=None)


@app.route("/ping", methods=["POST"])
def ping():
    ip = request.form.get("ip", "").strip()

    if not ip:
        return render_template_string(PAGE_HTML, ip=ip, output="Error: empty input")

    # VULNERABLE: command injection via unsanitized user input
    cmd = f"ping -c 1 {ip}"
    try:
        output = os.popen(cmd).read()
    except Exception as e:
        output = f"Error: {e}"

    if not output:
        output = "(no output)"

    return render_template_string(PAGE_HTML, ip=ip, output=output)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
