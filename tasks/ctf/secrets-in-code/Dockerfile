FROM python:3.12-alpine

RUN apk add --no-cache git tree && \
    pip install --no-cache-dir flask

WORKDIR /app
COPY app.py .

# Create a realistic git repository with secrets buried in history
RUN mkdir -p /repo && cd /repo && \
    git init && \
    git config user.email "dev@awesome-webapp.io" && \
    git config user.name "Alexei Petrov" && \
    \
    # Commit 1: initial project structure
    printf '# Awesome WebApp\n\nA modern web application for managing tasks.\n\n## Setup\n\n```\npip install -r requirements.txt\npython app.py\n```\n' > README.md && \
    printf 'flask==3.0.0\nrequests==2.31.0\nsqlalchemy==2.0.23\n' > requirements.txt && \
    printf 'from flask import Flask, jsonify\n\napp = Flask(__name__)\n\n@app.route("/")\ndef index():\n    return jsonify({"status": "ok", "app": "awesome-webapp"})\n\n@app.route("/health")\ndef health():\n    return jsonify({"healthy": True})\n\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", port=5000)\n' > app.py && \
    git add -A && \
    GIT_AUTHOR_DATE="2024-11-10T09:15:00" GIT_COMMITTER_DATE="2024-11-10T09:15:00" \
    git commit -m "Initial commit: project scaffolding" && \
    \
    # Commit 2: add config with SECRETS (the vulnerable commit)
    printf 'import os\n\n# Database\nDATABASE_URL = "postgresql://webapp_admin:Pr0d_p@ssw0rd!@db.internal:5432/webapp_prod"\n\n# API Keys\nAPI_KEY = "FLAG{secrets_in_git_history_are_forever}"\nSTRIPE_SECRET_KEY = "sk_live_4eC39HqLyjWDarjtT1zdp7dc"\nSENDGRID_API_KEY = "SG.xxxxxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"\n\n# AWS\nAWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\nAWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\nAWS_REGION = "us-east-1"\n\n# JWT\nJWT_SECRET = "super-secret-jwt-key-do-not-share-2024"\n' > config.py && \
    printf 'from sqlalchemy import create_engine, Column, Integer, String\nfrom sqlalchemy.orm import declarative_base, sessionmaker\nfrom config import DATABASE_URL\n\nBase = declarative_base()\n\nclass User(Base):\n    __tablename__ = "users"\n    id = Column(Integer, primary_key=True)\n    username = Column(String(100), unique=True)\n    email = Column(String(200))\n\nclass Task(Base):\n    __tablename__ = "tasks"\n    id = Column(Integer, primary_key=True)\n    title = Column(String(255))\n    owner_id = Column(Integer)\n\nengine = create_engine(DATABASE_URL)\nSession = sessionmaker(bind=engine)\n' > models.py && \
    sed -i 's/from flask import Flask, jsonify/from flask import Flask, jsonify\nfrom config import API_KEY/' app.py && \
    git add -A && \
    GIT_AUTHOR_DATE="2024-11-12T14:30:00" GIT_COMMITTER_DATE="2024-11-12T14:30:00" \
    git commit -m "feat: add database models and API configuration" && \
    \
    # Commit 3: add more features (covers up the secrets a bit)
    printf 'import unittest\nfrom app import app\n\nclass TestApp(unittest.TestCase):\n    def setUp(self):\n        self.client = app.test_client()\n\n    def test_index(self):\n        resp = self.client.get("/")\n        self.assertEqual(resp.status_code, 200)\n\n    def test_health(self):\n        resp = self.client.get("/health")\n        data = resp.get_json()\n        self.assertTrue(data["healthy"])\n\nif __name__ == "__main__":\n    unittest.main()\n' > test_app.py && \
    printf 'FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD ["python", "app.py"]\n' > Dockerfile && \
    git add -A && \
    GIT_AUTHOR_DATE="2024-11-15T11:00:00" GIT_COMMITTER_DATE="2024-11-15T11:00:00" \
    git commit -m "feat: add unit tests and Dockerfile" && \
    \
    # Commit 4: SECURITY FIX — remove hardcoded secrets (but history remains!)
    printf 'import os\n\n# All secrets are now loaded from environment variables.\n# See .env.example for required variables.\n\nDATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")\nAPI_KEY = os.environ.get("API_KEY", "")\nSTRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")\nSENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")\nAWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")\nAWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")\nAWS_REGION = os.environ.get("AWS_REGION", "us-east-1")\nJWT_SECRET = os.environ.get("JWT_SECRET", "")\n' > config.py && \
    printf '# Required environment variables\nDATABASE_URL=postgresql://user:pass@localhost:5432/webapp\nAPI_KEY=\nSTRIPE_SECRET_KEY=\nSENDGRID_API_KEY=\nAWS_ACCESS_KEY_ID=\nAWS_SECRET_ACCESS_KEY=\nAWS_REGION=us-east-1\nJWT_SECRET=\n' > .env.example && \
    printf '.env\n*.pyc\n__pycache__/\n.venv/\n' > .gitignore && \
    git add -A && \
    GIT_AUTHOR_DATE="2024-11-18T16:45:00" GIT_COMMITTER_DATE="2024-11-18T16:45:00" \
    git commit -m "security: move all secrets to environment variables" && \
    \
    # Commit 5: minor cleanup
    printf '# Awesome WebApp\n\nA modern web application for managing tasks.\n\n## Setup\n\n1. Copy `.env.example` to `.env` and fill in your secrets\n2. `pip install -r requirements.txt`\n3. `python app.py`\n\n## Tests\n\n```\npython -m pytest test_app.py\n```\n\n## Security\n\nNever commit secrets to the repository.\nAll sensitive configuration is loaded from environment variables.\n' > README.md && \
    git add -A && \
    GIT_AUTHOR_DATE="2024-11-19T10:00:00" GIT_COMMITTER_DATE="2024-11-19T10:00:00" \
    git commit -m "docs: update README with setup instructions"

EXPOSE 80

CMD ["python", "/app/app.py"]
