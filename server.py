"""
CodeMentor - Core REST API & Web Application Server
Production-ready Python HTTP server with zero third-party dependencies,
serving the modern single-page educational application and all REST API endpoints.
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import mimetypes

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import database
import code_executor
import analyzer
import tutor_engine

DEFAULT_HOST = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
HOST = os.environ.get("HOST", DEFAULT_HOST)
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_static_dir() -> str:
    """Finds the static directory even if nested or deployed in varying structures."""
    candidates = [
        os.path.join(BASE_DIR, "static"),
        os.path.join(BASE_DIR, "Hackathon Project", "static"),
        os.path.join(os.getcwd(), "static"),
        os.path.join(os.getcwd(), "Hackathon Project", "static"),
        os.path.join(os.path.dirname(BASE_DIR), "static"),
    ]
    for cand in candidates:
        if os.path.isdir(cand) and os.path.isfile(os.path.join(cand, "index.html")):
            return cand

    try:
        for root, dirs, files in os.walk(BASE_DIR):
            if "index.html" in files:
                return root
        parent_dir = os.path.dirname(BASE_DIR)
        for root, dirs, files in os.walk(parent_dir):
            if "index.html" in files:
                return root
    except Exception:
        pass

    return os.path.join(BASE_DIR, "static")

STATIC_DIR = get_static_dir()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class CodeMentorHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable aggressive caching for API
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        if self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Route API requests
        if path.startswith("/api/"):
            self.handle_api_get(path, query)
            return

        # Serve static frontend files
        static_dir = get_static_dir()
        if path == "/" or path == "":
            self.serve_file(os.path.join(static_dir, "index.html"), "text/html; charset=utf-8")
            return

        clean_path = path.lstrip("/")
        file_path = os.path.join(static_dir, clean_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.serve_file(file_path, mime_type or "application/octet-stream")
        else:
            # Fallback to index.html for SPA client-side routing
            self.serve_file(os.path.join(static_dir, "index.html"), "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(body) if body.strip() else {}
        except Exception:
            self.send_json_error(400, "Malformed JSON request body")
            return

        self.handle_api_post(path, query, payload)

    # ------------------ API Route Handlers ------------------

    def handle_api_get(self, path: str, query: dict):
        # 1. Health & Status
        if path == "/api/health":
            ai_status = tutor_engine.get_ai_provider_status()
            gcc_avail = os.path.exists(code_executor.get_gcc_path())
            javac_avail = os.path.exists(code_executor.get_javac_path())
            self.send_json_response(200, {
                "status": "healthy",
                "service": "CodeMentor AI Learning Platform",
                "ai_provider": ai_status,
                "compilers": {
                    "gcc_c": gcc_avail,
                    "python": True,
                    "javac_java": javac_avail
                }
            })
            return

        # 2. Users List (for student switching in demo)
        if path == "/api/users":
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT id, username, display_name, created_at FROM users ORDER BY id ASC")
            users = [dict(r) for r in c.fetchall()]
            conn.close()
            self.send_json_response(200, {"users": users})
            return

        # 3. Mistake Categories Taxonomy
        if path == "/api/categories":
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM mistake_categories ORDER BY id ASC")
            cats = [dict(r) for r in c.fetchall()]
            conn.close()
            self.send_json_response(200, {"categories": cats})
            return

        # 4. Problems Catalog
        if path == "/api/problems":
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("""
            SELECT id, slug, title, language, difficulty, concept, mistake_category_slug, description
            FROM problems ORDER BY id ASC
            """)
            problems = [dict(r) for r in c.fetchall()]
            conn.close()
            self.send_json_response(200, {"problems": problems})
            return

        # 5. Single Problem Details
        if path.startswith("/api/problems/"):
            slug_or_id = path.split("/api/problems/")[1].strip()
            conn = database.get_connection()
            c = conn.cursor()
            if slug_or_id.isdigit():
                c.execute("SELECT * FROM problems WHERE id = ?", (int(slug_or_id),))
            else:
                c.execute("SELECT * FROM problems WHERE slug = ?", (slug_or_id,))
            prob = c.fetchone()
            conn.close()
            if not prob:
                self.send_json_error(404, "Problem not found")
                return
            prob_dict = dict(prob)
            prob_dict["test_cases"] = json.loads(prob_dict["test_cases_json"])
            self.send_json_response(200, {"problem": prob_dict})
            return

        # 6. Student Debugging DNA
        if path.startswith("/api/dna/"):
            parts = path.split("/api/dna/")[1].strip().split("/")
            user_id = int(parts[0]) if parts[0].isdigit() else 1
            dna = analyzer.get_student_dna(user_id)
            self.send_json_response(200, dna)
            return

        # 7. Get Attempt Details
        if path.startswith("/api/attempts/"):
            parts = path.split("/api/attempts/")[1].strip().split("/")
            attempt_id = int(parts[0]) if parts[0].isdigit() else 0
            lang = query.get("lang", ["en"])[0]
            stage = int(query.get("stage", [0])[0]) or None
            stage_content = tutor_engine.get_stage_content(attempt_id, target_stage=stage, lang=lang)
            if "error" in stage_content:
                self.send_json_error(404, stage_content["error"])
                return
            self.send_json_response(200, {"attempt_stage": stage_content})
            return

        self.send_json_error(404, "Endpoint not found")

    def handle_api_post(self, path: str, query: dict, payload: dict):
        # 1. Register User
        if path == "/api/auth/register":
            username = payload.get("username", "").strip()
            display_name = payload.get("display_name", "").strip() or username
            password = payload.get("password", "").strip()
            if not username or not password:
                self.send_json_error(400, "Username and password are required")
                return
            conn = database.get_connection()
            c = conn.cursor()
            try:
                c.execute("""
                INSERT INTO users (username, display_name, password_hash)
                VALUES (?, ?, ?)
                """, (username, display_name, database.hash_password(password)))
                conn.commit()
                new_id = c.lastrowid
                conn.close()
                self.send_json_response(201, {
                    "success": True,
                    "user": {"id": new_id, "username": username, "display_name": display_name}
                })
            except Exception as e:
                conn.close()
                self.send_json_error(409, "Username already exists")
            return

        # 2. Login User
        if path == "/api/auth/login":
            username = payload.get("username", "").strip()
            password = payload.get("password", "").strip()
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT id, username, display_name, password_hash FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            conn.close()
            if not user or user["password_hash"] != database.hash_password(password):
                self.send_json_error(401, "Invalid username or password")
                return
            self.send_json_response(200, {
                "success": True,
                "user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"]}
            })
            return

        # 3. Start a Debugging Session (on a curated problem)
        if path == "/api/attempts/start":
            user_id = payload.get("user_id", 1)
            problem_id = payload.get("problem_id")
            if not problem_id:
                self.send_json_error(400, "problem_id is required")
                return

            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
            prob = c.fetchone()
            if not prob:
                conn.close()
                self.send_json_error(404, "Problem not found")
                return

            prob = dict(prob)
            initial_code = prob["buggy_code"]
            lang = prob["language"]

            # Classify initial bug
            classification = analyzer.classify_mistakes(
                initial_code, lang, expected_category=prob["mistake_category_slug"]
            )
            categories_json = json.dumps(classification["categories"])

            c.execute("""
            INSERT INTO attempts (user_id, problem_id, language, initial_code, current_code,
                                  mistake_categories_json, current_stage, hints_used, is_solved,
                                  solved_independently, solution_unlocked, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, 0, 0, 'unverified')
            """, (user_id, problem_id, lang, initial_code, initial_code, categories_json))
            attempt_id = c.lastrowid
            conn.commit()
            conn.close()

            stage_data = tutor_engine.get_stage_content(attempt_id, 1, lang=payload.get("lang", "en"))
            self.send_json_response(201, {
                "attempt_id": attempt_id,
                "problem": prob,
                "classification": classification,
                "stage": stage_data
            })
            return

        # 4. Custom Code Debugging Submission
        if path == "/api/custom-debug":
            user_id = payload.get("user_id", 1)
            code = payload.get("code", "")
            language = payload.get("language", "python").strip()
            title = payload.get("title", "").strip()
            question_or_error = payload.get("description", "").strip()

            if not code or not code.strip():
                self.send_json_error(400, "Code snippet cannot be empty")
                return

            if len(code) > 100000:
                self.send_json_error(400, "Code snippet exceeds maximum allowed size (100KB)")
                return

            custom_title = title or question_or_error or "Custom Debugging Snippet"

            # Classify mistake
            classification = analyzer.classify_mistakes(
                code=code,
                language=language,
                error_message=question_or_error
            )
            categories_json = json.dumps(classification["categories"])

            conn = database.get_connection()
            c = conn.cursor()
            c.execute("""
            INSERT INTO attempts (user_id, problem_id, custom_title, language, initial_code, current_code,
                                  mistake_categories_json, current_stage, hints_used, is_solved,
                                  solved_independently, solution_unlocked, verification_status)
            VALUES (?, NULL, ?, ?, ?, ?, ?, 1, 0, 0, 0, 0, 'unverified')
            """, (user_id, custom_title, language, code, code, categories_json))
            attempt_id = c.lastrowid
            conn.commit()
            conn.close()

            stage_data = tutor_engine.get_stage_content(attempt_id, 1, lang=payload.get("lang", "en"))
            self.send_json_response(201, {
                "attempt_id": attempt_id,
                "classification": classification,
                "stage": stage_data
            })
            return

        # 5. Interact Within Attempt Stage
        if path.startswith("/api/attempts/") and path.endswith("/interact"):
            parts = path.split("/api/attempts/")[1].split("/")
            if not parts[0].isdigit():
                self.send_json_error(400, "Invalid attempt ID")
                return
            attempt_id = int(parts[0])
            user_input = payload.get("user_input", "")
            action = payload.get("action", "")
            lang = payload.get("lang", "en")

            result = tutor_engine.interact_stage(attempt_id, user_input, action, lang)
            self.send_json_response(200, result)
            return

        # 6. Verify Student Code Correction
        if path.startswith("/api/attempts/") and path.endswith("/verify"):
            parts = path.split("/api/attempts/")[1].split("/")
            if not parts[0].isdigit():
                self.send_json_error(400, "Invalid attempt ID")
                return
            attempt_id = int(parts[0])
            code = payload.get("code", "")
            lang = payload.get("lang", "en")

            if not code or not code.strip():
                self.send_json_error(400, "Submitted code cannot be empty")
                return

            if len(code) > 100000:
                self.send_json_error(400, "Submitted code exceeds maximum allowed size (100KB)")
                return

            result = tutor_engine.verify_student_code(attempt_id, code, lang)
            self.send_json_response(200, result)
            return

        # 7. Jump or Select Stage Directly
        if path.startswith("/api/attempts/") and path.endswith("/stage"):
            parts = path.split("/api/attempts/")[1].split("/")
            if not parts[0].isdigit():
                self.send_json_error(400, "Invalid attempt ID")
                return
            attempt_id = int(parts[0])
            stage_num = int(payload.get("stage", 1))
            lang = payload.get("lang", "en")

            result = tutor_engine.get_stage_content(attempt_id, stage_num, lang)
            self.send_json_response(200, result)
            return

        self.send_json_error(404, "Endpoint not found")

    # ------------------ Utility Helpers ------------------

    def send_json_response(self, status: int, data: dict):
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json_error(self, status: int, message: str):
        self.send_json_response(status, {"error": message, "status": status})

    def serve_file(self, full_path: str, content_type: str):
        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            if full_path.endswith("index.html"):
                self.serve_missing_static_page(full_path)
                return
            self.send_json_error(404, f"File not found: {str(e)}")

    def serve_missing_static_page(self, missing_path: str):
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CodeMentor — Static Frontend Folder Missing</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0b0f19;
      color: #e2e8f0;
      padding: 40px 20px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 80vh;
      margin: 0;
    }}
    .box {{
      max-width: 640px;
      background: #131b2e;
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 32px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }}
    h1 {{ color: #f59e0b; font-size: 22px; margin-top: 0; }}
    code {{ background: #080d1a; color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
    ol {{ line-height: 1.8; color: #cbd5e1; padding-left: 20px; }}
    .status {{ display: inline-block; background: #059669; color: white; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="status">✓ Python Backend Running Successfully</div>
    <h1>⚠️ Static Frontend Folder Missing in Repository</h1>
    <p>Render started your application, but could not find <code>index.html</code> at <code>{missing_path}</code>.</p>
    <p>This happens when only the Python files were uploaded to GitHub without the <code>static/</code> directory.</p>
    <h3>👉 How to fix in 1 minute:</h3>
    <ol>
      <li>Open your project repository on <b>GitHub</b>.</li>
      <li>Click <b>Add file</b> &gt; <b>Upload files</b>.</li>
      <li>Drag and drop the entire <code>static</code> folder (which includes <code>index.html</code>, <code>app.js</code>, and <code>style.css</code>).</li>
      <li>Click <b>Commit changes</b>. Render will automatically redeploy and load the application!</li>
    </ol>
  </div>
</body>
</html>"""
        payload = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

def run_server():
    database.init_db()
    server_address = (HOST, PORT)
    try:
        httpd = ThreadedHTTPServer(server_address, CodeMentorHandler)
    except OSError as e:
        if getattr(e, "winerror", None) == 10048 or "Address already in use" in str(e):
            print(f"\n❌ [CodeMentor Error] Port {PORT} is already in use by another process.")
            print(f"👉 You can run with another port, for example:")
            print(f"   $env:PORT=8080; python server.py  (PowerShell)")
            print(f"   set PORT=8080 && python server.py (CMD)")
            return
        raise

    display_host = "localhost" if HOST in ("0.0.0.0", "") else HOST
    print(f"\n=============================================================")
    print(f"🚀 CodeMentor Platform running successfully!")
    print(f"   👉 Open in Browser: http://localhost:{PORT}")
    print(f"   👉 Network URL:     http://{display_host}:{PORT}")
    print(f"   - Database:    {database.DB_PATH}")
    print(f"   - Active Mode: {tutor_engine.get_ai_provider_status()['mode_label']}")
    print(f"   - Press Ctrl+C to stop the server")
    print(f"=============================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[CodeMentor] Shutting down gracefully...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
