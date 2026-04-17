"""Flask app for Vulnerable Dependencies CTF task - SCA analysis."""
import os

from flask import Flask, request, render_template_string

app = Flask(__name__)
# The flag IS the CVE number itself
EXPECTED_CVE = "CVE-2021-44228"  # Log4Shell - the critical one
FLAG = os.environ.get("CTF_FLAG", f"FLAG{{{EXPECTED_CVE}}}")

# Simulated project files
REQUIREMENTS_TXT = """# Python dependencies
Flask==1.0.2
requests==2.19.1
Jinja2==2.10
Werkzeug==0.14.1
cryptography==2.1.4
PyYAML==3.13
paramiko==2.4.1
urllib3==1.23
Django==2.0.1
"""

PACKAGE_JSON = """{
  "name": "awesome-webapp-frontend",
  "version": "1.0.0",
  "dependencies": {
    "lodash": "4.17.4",
    "express": "4.16.0",
    "minimist": "0.0.8",
    "serialize-javascript": "1.5.0",
    "node-fetch": "2.6.0",
    "handlebars": "4.0.11"
  }
}
"""

POM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>backend-service</artifactId>
  <version>1.0.0</version>

  <dependencies>
    <dependency>
      <groupId>org.apache.logging.log4j</groupId>
      <artifactId>log4j-core</artifactId>
      <version>2.14.1</version>
    </dependency>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>5.2.3.RELEASE</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.9.8</version>
    </dependency>
    <dependency>
      <groupId>commons-collections</groupId>
      <artifactId>commons-collections</artifactId>
      <version>3.2.1</version>
    </dependency>
  </dependencies>
</project>
"""

PROJECT_FILES = {
    "requirements.txt": REQUIREMENTS_TXT,
    "package.json": PACKAGE_JSON,
    "pom.xml": POM_XML,
}

PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>SCA Challenge</title>
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
  .nav { display: flex; gap: 8px; margin-bottom: 20px; justify-content: center; flex-wrap: wrap; }
  .nav a { color: #e94560; text-decoration: none; padding: 8px 14px; border: 1px solid #e94560;
           border-radius: 4px; font-size: 13px; }
  .nav a:hover, .nav a.active { background: #e94560; color: white; }
  .info { background: #1b3a5c; border-left: 3px solid #e94560; padding: 12px 16px;
          border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: #aaa; }
  input[type="text"] { padding: 10px; width: 280px; background: #0f3460; color: #e0e0e0;
                       border: 1px solid #333; border-radius: 4px; font-family: monospace; }
  button { padding: 10px 20px; background: #e94560; color: white; border: none;
           border-radius: 4px; cursor: pointer; font-size: 14px; margin-left: 10px; }
  button:hover { background: #c73652; }
  .result { margin-top: 16px; padding: 12px; border-radius: 4px; font-size: 14px; }
  .result.success { background: #1b4332; color: #6fcf97; }
  .result.error { background: #4a1c1c; color: #e94560; }
</style>
</head>
<body>
<div class="container">
  <h1>SCA: Vulnerable Dependencies</h1>
  <p class="subtitle">Analyze project dependencies and find the critical CVE</p>

  <div class="info">
    This project consists of multiple components (Python, Node.js, Java).<br>
    Analyze all dependency files and find the library with the <strong>CRITICAL</strong> CVE.<br>
    Submit the CVE number in the format: <code>CVE-XXXX-XXXXX</code>
  </div>

  <div class="nav">
    {% for name in files %}
    <a href="/?file={{ name }}" class="{{ 'active' if current_file == name else '' }}">{{ name }}</a>
    {% endfor %}
  </div>

  <div class="card">
    <h3>{{ current_file }}</h3>
    <pre>{{ file_content }}</pre>
  </div>

  <div class="card">
    <h3>Submit CVE</h3>
    <form method="POST" action="/check" style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
      <input type="text" name="cve" placeholder="CVE-XXXX-XXXXX" required
             pattern="CVE-\\d{4}-\\d{4,7}">
      <button type="submit">Check</button>
    </form>
    {% if result %}
    <div class="result {{ result_class }}">{{ result }}</div>
    {% endif %}
  </div>

  <div class="card">
    <h3>Hints</h3>
    <ul style="list-style: none; color: #aaa; font-size: 13px;">
      <li style="padding: 4px 0;">1. Check each dependency version against public vulnerability databases.</li>
      <li style="padding: 4px 0;">2. Pay attention to Java dependencies - some had devastating CVEs.</li>
      <li style="padding: 4px 0;">3. Look for CVEs with CVSS score 10.0 (maximum severity).</li>
      <li style="padding: 4px 0;">4. Tools: <code>pip-audit</code>, <code>npm audit</code>, <code>OWASP Dependency-Check</code></li>
    </ul>
  </div>
</div>
</body>
</html>
"""


@app.route("/")
def index():
    current_file = request.args.get("file", "requirements.txt")
    if current_file not in PROJECT_FILES:
        current_file = "requirements.txt"
    file_content = PROJECT_FILES[current_file]
    return render_template_string(
        PAGE_HTML,
        files=list(PROJECT_FILES.keys()),
        current_file=current_file,
        file_content=file_content,
        result=None,
        result_class="",
    )


@app.route("/check", methods=["POST"])
def check():
    cve = request.form.get("cve", "").strip().upper()
    current_file = request.args.get("file", "requirements.txt")
    if current_file not in PROJECT_FILES:
        current_file = "requirements.txt"

    if cve == EXPECTED_CVE:
        result = f"Correct! {EXPECTED_CVE} (Log4Shell) - CVSS 10.0. Flag: {FLAG}"
        result_class = "success"
    elif cve.startswith("CVE-"):
        result = (
            f"{cve} is a valid CVE, but it is not the CRITICAL one we are looking for. "
            "Hint: look for the CVE with the highest CVSS score (10.0)."
        )
        result_class = "error"
    else:
        result = "Invalid format. Use CVE-XXXX-XXXXX format."
        result_class = "error"

    return render_template_string(
        PAGE_HTML,
        files=list(PROJECT_FILES.keys()),
        current_file=current_file,
        file_content=PROJECT_FILES[current_file],
        result=result,
        result_class=result_class,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
