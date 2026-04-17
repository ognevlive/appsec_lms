"""Flask app for Secrets in Code CTF task - git history analysis with web terminal."""
import os
import subprocess
import shlex
import html

from flask import Flask, request, jsonify

app = Flask(__name__)

REPO_PATH = "/repo"

# Allowed commands for the web terminal (whitelist)
ALLOWED_COMMANDS = [
    "git", "ls", "cat", "head", "tail", "grep", "find", "wc",
    "echo", "pwd", "whoami", "env", "printenv", "file", "xxd",
    "strings", "hexdump", "diff", "less", "more", "tree",
]


def run_git(args):
    """Run a git command in the repo directory."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error: {e}"


def run_shell(cmd_str):
    """Run a whitelisted shell command in the repo directory."""
    try:
        parts = shlex.split(cmd_str)
    except ValueError as e:
        return f"Parse error: {e}"

    if not parts:
        return ""

    binary = parts[0]
    if binary not in ALLOWED_COMMANDS:
        return f"Command not allowed: {binary}\nAllowed: {', '.join(sorted(ALLOWED_COMMANDS))}"

    # Block dangerous git subcommands
    if binary == "git" and len(parts) > 1:
        dangerous = {"push", "remote", "fetch", "pull", "clone", "config", "rebase", "reset", "checkout"}
        if parts[1] in dangerous:
            return f"git {parts[1]} is not allowed in this environment."

    try:
        result = subprocess.run(
            parts,
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout
        if result.stderr:
            output += result.stderr
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out (10s limit)"
    except FileNotFoundError:
        return f"Command not found: {binary}"
    except Exception as e:
        return f"Error: {e}"


PAGE_HTML = r"""<!DOCTYPE html>
<html>
<head>
<title>Git Repository Browser</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
         background: #0c0e14; color: #e5e4ed; min-height: 100vh; }
  .container { max-width: 960px; margin: 0 auto; padding: 24px 20px; }
  h1 { color: #8eff71; margin-bottom: 4px; font-size: 22px; letter-spacing: -0.5px; }
  .subtitle { color: #aaaab3; margin-bottom: 20px; font-size: 12px; text-transform: uppercase;
              letter-spacing: 0.15em; }
  .info { background: #11131a; border-left: 2px solid #8eff71; padding: 12px 16px;
          font-size: 13px; color: #aaaab3; margin-bottom: 20px; line-height: 1.5; }
  .info code { background: #171921; padding: 1px 5px; color: #59e3fe; }
  .nav { display: flex; gap: 2px; margin-bottom: 20px; background: #11131a; padding: 2px; }
  .nav a { color: #aaaab3; text-decoration: none; padding: 8px 16px; font-size: 11px;
           text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;
           transition: all 0.15s; flex: 1; text-align: center; }
  .nav a:hover { background: #1d1f27; color: #e5e4ed; }
  .nav a.active { background: #8eff71; color: #0c0e14; }
  .card { background: #11131a; padding: 16px 20px; margin-bottom: 16px; }
  .card h3 { color: #8eff71; margin-bottom: 12px; font-size: 11px; text-transform: uppercase;
             letter-spacing: 0.2em; font-weight: 700; }
  pre { background: #000; padding: 14px; overflow-x: auto; font-size: 12px; line-height: 1.6;
        color: #aaaab3; white-space: pre-wrap; word-break: break-all; max-height: 500px;
        overflow-y: auto; }
  .file-list { list-style: none; }
  .file-list li { padding: 7px 12px; border-bottom: 1px solid #171921; }
  .file-list li:last-child { border-bottom: none; }
  .file-list a { color: #59e3fe; text-decoration: none; font-size: 13px; }
  .file-list a:hover { color: #8eff71; }
  .file-list .icon { color: #aaaab3; margin-right: 8px; }
  .commit { padding: 8px 0; border-bottom: 1px solid #171921; font-size: 13px; }
  .commit:last-child { border-bottom: none; }
  .commit-hash { color: #ff8b9f; font-family: monospace; cursor: pointer; }
  .commit-hash:hover { text-decoration: underline; }
  .commit-msg { color: #e5e4ed; }
  .commit-date { color: #46484f; font-size: 11px; display: block; margin-top: 2px; }
  /* Terminal */
  .terminal { background: #000; border: 1px solid #23262e; padding: 0; }
  .terminal-header { background: #171921; padding: 6px 12px; font-size: 10px;
                     text-transform: uppercase; letter-spacing: 0.15em; color: #aaaab3;
                     display: flex; justify-content: space-between; align-items: center; }
  .terminal-body { padding: 12px; min-height: 300px; max-height: 500px; overflow-y: auto;
                   font-size: 12px; line-height: 1.5; }
  .terminal-output { color: #aaaab3; white-space: pre-wrap; word-break: break-all; }
  .terminal-output .cmd { color: #8eff71; }
  .terminal-output .err { color: #ff8b9f; }
  .terminal-input { display: flex; align-items: center; background: #0c0e14;
                    border-top: 1px solid #23262e; padding: 8px 12px; }
  .terminal-input .prompt { color: #8eff71; margin-right: 8px; font-size: 13px; white-space: nowrap; }
  .terminal-input input { flex: 1; background: transparent; border: none; color: #e5e4ed;
                          font-family: inherit; font-size: 13px; outline: none; }
  .terminal-input input::placeholder { color: #46484f; }
  .hint { background: #171921; padding: 8px 12px; font-size: 11px; color: #46484f;
          margin-top: 8px; }
  .hint b { color: #aaaab3; }
  .diff-add { color: #8eff71; }
  .diff-del { color: #ff8b9f; }
  .diff-hdr { color: #59e3fe; }
  button, .btn { padding: 6px 16px; background: #8eff71; color: #0c0e14; border: none;
                 font-family: inherit; font-size: 11px; font-weight: 700; cursor: pointer;
                 text-transform: uppercase; letter-spacing: 0.1em; }
  button:hover { filter: brightness(1.1); }
  input[type=text] { width: 100%; padding: 8px 12px; background: #000; color: #e5e4ed;
                     border: 1px solid #23262e; font-family: inherit; font-size: 13px;
                     margin: 6px 0; }
  input[type=text]:focus { border-color: #8eff71; outline: none; }
</style>
</head>
<body>
<div class="container">
  <h1>&#9760; Git Repository Browser</h1>
  <p class="subtitle">Project: awesome-webapp &mdash; /repo</p>

  <div class="info">
    Исследуйте git-репозиторий проекта. Разработчики могли случайно закоммитить
    чувствительные данные. Используйте <code>git log</code>, <code>git show</code>,
    <code>git diff</code> для анализа истории коммитов.
  </div>

  <div class="nav">
    <a href="/" id="nav-files">Файлы</a>
    <a href="/log" id="nav-log">Git Log</a>
    <a href="/diff" id="nav-diff">Diff Viewer</a>
    <a href="/terminal" id="nav-terminal">Терминал</a>
  </div>

  <div id="content">CONTENT_PLACEHOLDER</div>
</div>
<script>
// Highlight active nav
const path = location.pathname;
document.querySelectorAll('.nav a').forEach(a => {
  const href = a.getAttribute('href');
  if (path === href || (href !== '/' && path.startsWith(href))) {
    a.classList.add('active');
  } else if (href === '/' && (path === '/' || path === '/file')) {
    a.classList.add('active');
  }
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    files_output = run_git(["ls-tree", "--name-only", "HEAD"])
    files = [f for f in files_output.strip().split("\n") if f]
    items = ""
    for f in files:
        icon = "&#128196;" if "." in f else "&#128193;"
        items += f'<li><span class="icon">{icon}</span><a href="/file?name={html.escape(f)}">{html.escape(f)}</a></li>\n'
    content = f'<div class="card"><h3>Repository Files (HEAD)</h3><ul class="file-list">{items}</ul></div>'
    return PAGE_HTML.replace("CONTENT_PLACEHOLDER", content)


@app.route("/file")
def view_file():
    filename = request.args.get("name", "")
    if ".." in filename or filename.startswith("/"):
        return "Invalid filename", 400
    file_content = run_git(["show", f"HEAD:{filename}"])
    escaped = html.escape(file_content)
    content = (
        f'<div class="card"><h3>{html.escape(filename)}</h3>'
        f'<pre>{escaped}</pre></div>'
        f'<a href="/" style="color:#59e3fe;font-size:12px;">&larr; Назад к файлам</a>'
    )
    return PAGE_HTML.replace("CONTENT_PLACEHOLDER", content)


@app.route("/log")
def git_log():
    log_output = run_git(["log", "--pretty=format:%H|%s|%an|%ad", "--date=short"])
    commits_html = ""
    for line in log_output.strip().split("\n"):
        if "|" not in line:
            continue
        parts = line.split("|", 3)
        full_hash = html.escape(parts[0])
        short_hash = full_hash[:12]
        msg = html.escape(parts[1])
        author = html.escape(parts[2])
        date = html.escape(parts[3]) if len(parts) > 3 else ""
        commits_html += (
            f'<div class="commit">'
            f'<a class="commit-hash" href="/diff?commit={full_hash}">{short_hash}</a> '
            f'<span class="commit-msg">{msg}</span>'
            f'<span class="commit-date">{date} &mdash; {author}</span>'
            f'</div>\n'
        )
    hint = (
        '<div class="hint">Нажмите на хеш коммита, чтобы увидеть diff. '
        'Или используйте <b>Терминал</b> для команд <b>git show</b>, '
        '<b>git log -p</b>, <b>git diff</b>.</div>'
    )
    content = f'<div class="card"><h3>Commit History</h3>{commits_html}</div>{hint}'
    return PAGE_HTML.replace("CONTENT_PLACEHOLDER", content)


@app.route("/diff")
def diff_viewer():
    commit_hash = request.args.get("commit", "")
    diff_html = ""
    if commit_hash:
        # Sanitize: only allow hex chars
        safe_hash = "".join(c for c in commit_hash if c in "0123456789abcdefABCDEF")
        if safe_hash:
            raw = run_git(["show", "--patch", "--stat", safe_hash])
            # Color-code the diff
            lines = []
            for line in raw.split("\n"):
                escaped = html.escape(line)
                if line.startswith("+") and not line.startswith("+++"):
                    lines.append(f'<span class="diff-add">{escaped}</span>')
                elif line.startswith("-") and not line.startswith("---"):
                    lines.append(f'<span class="diff-del">{escaped}</span>')
                elif line.startswith("@@"):
                    lines.append(f'<span class="diff-hdr">{escaped}</span>')
                elif line.startswith("diff ") or line.startswith("index "):
                    lines.append(f'<span class="diff-hdr">{escaped}</span>')
                else:
                    lines.append(escaped)
            diff_html = f'<pre>{"<br>".join(lines)}</pre>'

    form = (
        '<form method="GET" action="/diff" style="margin-bottom:12px;">'
        '<label style="color:#aaaab3;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;">'
        'Commit hash:</label>'
        f'<input type="text" name="commit" placeholder="Введите хеш коммита..." '
        f'value="{html.escape(commit_hash)}">'
        '<button type="submit" style="margin-top:4px;">Показать Diff</button>'
        '</form>'
    )
    content = f'<div class="card"><h3>Diff Viewer</h3>{form}{diff_html}</div>'
    return PAGE_HTML.replace("CONTENT_PLACEHOLDER", content)


@app.route("/terminal")
def terminal_page():
    content = """
    <div class="terminal">
      <div class="terminal-header">
        <span>&#9617; web terminal &mdash; /repo</span>
        <span style="color:#8eff71;">&#9679; connected</span>
      </div>
      <div class="terminal-body" id="term-body">
        <div class="terminal-output" id="term-output">
<span style="color:#59e3fe;">Welcome to the Git Repository Terminal.</span>
<span style="color:#aaaab3;">Working directory: /repo</span>
<span style="color:#aaaab3;">Allowed commands: git, ls, cat, grep, find, head, tail, strings, diff, tree...</span>
<span style="color:#46484f;">Type a command and press Enter.</span>
</div>
      </div>
      <div class="terminal-input">
        <span class="prompt">repo $</span>
        <input type="text" id="term-input" placeholder="git log --oneline" autofocus
               autocomplete="off" spellcheck="false">
      </div>
    </div>
    <div class="hint" style="margin-top:8px;">
      <b>Подсказки:</b> <code>git log --oneline</code> &middot;
      <code>git show &lt;hash&gt;</code> &middot;
      <code>git diff HEAD~3 HEAD -- config.py</code> &middot;
      <code>grep -r "FLAG" .</code> (searches current files only)
    </div>
    <script>
    const input = document.getElementById('term-input');
    const output = document.getElementById('term-output');
    const body = document.getElementById('term-body');
    const history = [];
    let histIdx = -1;

    input.addEventListener('keydown', async function(e) {
      if (e.key === 'Enter') {
        const cmd = input.value.trim();
        if (!cmd) return;
        history.unshift(cmd);
        histIdx = -1;

        output.innerHTML += '\\n<span class="cmd">repo $ ' + escapeHtml(cmd) + '</span>\\n';
        input.value = '';
        input.disabled = true;

        try {
          const resp = await fetch('/api/exec', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cmd: cmd})
          });
          const data = await resp.json();
          if (data.output) {
            output.innerHTML += escapeHtml(data.output);
          }
        } catch(err) {
          output.innerHTML += '<span class="err">Connection error</span>\\n';
        }

        input.disabled = false;
        input.focus();
        body.scrollTop = body.scrollHeight;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (histIdx < history.length - 1) {
          histIdx++;
          input.value = history[histIdx];
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (histIdx > 0) {
          histIdx--;
          input.value = history[histIdx];
        } else {
          histIdx = -1;
          input.value = '';
        }
      }
    });

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
    </script>
    """
    return PAGE_HTML.replace("CONTENT_PLACEHOLDER", content)


@app.route("/api/exec", methods=["POST"])
def api_exec():
    """Execute a whitelisted command and return output."""
    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd", "").strip()

    if not cmd:
        return jsonify({"output": ""})

    if len(cmd) > 500:
        return jsonify({"output": "Error: command too long (max 500 chars)"})

    # Block pipes and redirects for security
    # But allow | for grep pipelines which are common in git analysis
    if any(c in cmd for c in [";", "&&", "||", ">", "<", "`", "$("]):
        return jsonify({"output": "Error: pipes (;, &&, ||, >, <) are not allowed.\n"
                                   "Use individual commands instead."})

    # Handle simple pipe: cmd1 | cmd2
    if "|" in cmd:
        pipe_parts = [p.strip() for p in cmd.split("|", 1)]
        out1 = run_shell(pipe_parts[0])
        if pipe_parts[1]:
            # Feed output to second command via stdin
            try:
                parts2 = shlex.split(pipe_parts[1])
                if not parts2 or parts2[0] not in ALLOWED_COMMANDS:
                    return jsonify({"output": f"Piped command not allowed: {parts2[0] if parts2 else '(empty)'}"})
                result = subprocess.run(
                    parts2,
                    input=out1,
                    cwd=REPO_PATH,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return jsonify({"output": result.stdout + result.stderr})
            except Exception as e:
                return jsonify({"output": f"Pipe error: {e}"})
        return jsonify({"output": out1})

    output = run_shell(cmd)
    return jsonify({"output": output})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
