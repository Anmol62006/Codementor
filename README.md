# CodeMentor — AI Programming Learning Platform

CodeMentor is a pedagogical AI platform that helps beginner programmers understand their mistakes, master problem-solving strategies, and build a persistent **Debugging DNA** learning profile over time — rather than simply handing over copy-paste corrected code.

---

## 🚀 Quick Start (Zero External Dependencies)

CodeMentor runs natively on **Python 3.10+ standard library** with zero external `pip` dependencies. It features native compilation support via **GCC (MinGW)**, **Python**, and **Java (JDK)**.

### How to Run in VS Code

You have three easy ways to run this project in VS Code:

#### Option 1: Press F5 (Instant Debug / Run)
1. In VS Code, press **`F5`** (or go to the **Run and Debug** tab in the left sidebar `Ctrl+Shift+D`).
2. Select **`🚀 Run CodeMentor Web Server`**.
3. Open your browser at **`http://localhost:8000`**.

#### Option 2: Integrated Terminal
1. Open the integrated terminal in VS Code: **`Ctrl + \``** (or `Terminal` > `New Terminal`).
2. Run:
   ```powershell
   python server.py
   ```
3. Open your browser at:
   👉 **`http://localhost:8000`**

#### Option 3: Double-Click `run.bat`
- Simply double-click **`run.bat`** in File Explorer (or run `.\run.bat` in the terminal). It starts the server and automatically opens your web browser.

### Run the Automated 46-Point Integration Test Suite

In your VS Code terminal:
```powershell
python test_suite.py
```
Or press `Ctrl+Shift+D` in VS Code and choose **`🧪 Run 46-Point Test Suite`**.

---

## ☁️ Deploying on Render (Web Service)

CodeMentor is pre-configured for instant deployment on [Render](https://render.com) as a **Web Service**:

1. Push this repository to **GitHub** or **GitLab**.
2. In the Render Dashboard, click **New +** -> **Web Service** and connect this repository.
3. Configure the service settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
4. *(Optional)* In the **Environment Variables** tab, add:
   - `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API key.
   - `OPENAI_API_KEY`: *(Optional)* Your OpenAI API key.
   - `DATABASE_PATH`: *(Optional)* Set to `/var/data/codementor.db` if using a Render Persistent Disk.
5. Click **Create Web Service**. Render will automatically supply the `$PORT` and launch the app!

---

## 🌟 Core Features & How They Work

### 1. Feature One: Persistent Debugging DNA Profile
- **Taxonomy Tracking**: Automatically classifies programming mistakes into standard categories:
  - `Off-by-One Errors`
  - `Array Indexing Errors`
  - `Loop Logic Errors`
  - `Recursion Misunderstandings`
  - `Variable Scope Errors`
  - `Syntax Errors`
  - `Incorrect Conditions`
  - `Algorithm & Logic Errors`
- **Zero Fabricated Statistics**: Metrics like solve rate, error frequencies, and hints-per-solve are strictly calculated from persistent SQLite database records (`codementor.db`).
- **Personalized Insights**: Real-time analytical observations based on student history (e.g. *"Array Indexing is your most frequent recorded mistake (2 attempts recorded)"*, *"Improvement detected in Off-by-One Errors"*).
- **Graceful Empty State**: Brand new learners start with a clean onboarding view and 0% made-up stats.
- **Student Profile Switcher**: Switch instantly between *Alex Sharma* (experienced profile with recorded history), *Priya Patel*, and *Rohan Verma* (new learner with empty state), or register a new student.

### 2. Feature Two: Hint-First 8-Stage Learning Journey
Guides students through progressive cognitive milestones before revealing full solutions:
1. **Stage 1 — Understand**: Conceptual problem breakdown with an interactive output prediction quiz.
2. **Stage 2 — Investigate**: Line-by-line inspection to pinpoint the suspicious statement.
3. **Stage 3 — First Hint**: Gentle conceptual clue without revealing code.
4. **Stage 4 — Stronger Hint**: Targeted diagnostic clue focusing on boundaries or operators.
5. **Stage 5 — Attempt**: In-browser code editing with line numbers and tab indentation.
6. **Stage 6 — Verification**: Automated unit test execution in an isolated sandbox (clearly badged as **"Verified Test Execution"**).
7. **Stage 7 — Explanation**: Comprehensive explanation of *why* the fix works and what core concept was learned.
8. **Stage 8 — Unlock Solution**: Full annotated solution code reveal.

- **English & Hinglish Support**: Explanations can be toggled on-the-fly between beginner-friendly English and Hindi/Hinglish (e.g., *"Dhyan do `<=` operator par. Jab `i` 5 banega, to `5 <= 5` TRUE hoga aur `arr[5]` access ho jayega"*).
- **Non-blocking Flexibility**: Students can request a stronger hint or unlock the solution at any time without being trapped in rigid steps.

### 3. Isolated Code Sandbox & Real Test Runner
- Compiles and runs **C** (using `gcc`), **Python**, and **Java** in temporary isolated directories.
- Enforces strict **3.0-second execution timeouts** to guard against student infinite loops or infinite recursion.
- Normalizes stdout and compares against structured unit test cases, returning exact execution times in milliseconds.

### 4. Custom Code Debugger
- Students can paste any arbitrary code snippet in C, Python, or Java and submit observed error messages.
- The classifier automatically categorizes the bug and initiates the 8-stage hint journey.

---

## 🛠️ File Structure

| File / Folder | Role |
|---|---|
| `server.py` | Threaded HTTP server, REST API routing, CORS, and static file dispatching. |
| `database.py` | SQLite3 database schema, migration, and pre-seeded curriculum catalog. |
| `code_executor.py` | Subprocess-isolated compilation & test execution sandbox (C, Python, Java). |
| `analyzer.py` | Mistake taxonomy classifier and persistent Debugging DNA aggregator. |
| `tutor_engine.py` | 8-stage hint-first learning progression, multi-language engine (EN/Hinglish), and AI router. |
| `test_suite.py` | Comprehensive 46-assertion integration test suite. |
| `static/index.html` | Semantic single-page educational application layout. |
| `static/style.css` | Dark/Light themes, IDE split-screen layout, responsive cards, and SVG charts. |
| `static/app.js` | Interactive client-side state management, line-numbered editor, and stepper. |
| `A.java`, `B.java`, `Linklist2example.java` | Preserved original workspace coursework files (untouched). |

---

## 🔑 Environment Variables & AI Configuration

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Port for the HTTP web server. |
| `GEMINI_API_KEY` | *(Optional)* | Google Gemini API key for live generative explanations. |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI API key for live GPT-4o-mini tutoring. |

> **Offline / Demo Mode Guarantee**: If no API key is provided, CodeMentor operates in **Deterministic Pedagogical Mode**, driven by its built-in rule and heuristic engine. Every screen clearly indicates whether feedback originates from live AI or the rule-based pedagogical curriculum.

---

## 🏆 Hackathon Demo Script (3-Minute Presentation)

1. **The Problem (30s)**:
   - *"Current AI tools act as copy-paste answer machines: students copy corrected code without understanding why their original code failed, leading to shallow learning."*
2. **Feature One: Debugging DNA (1m)**:
   - Open `http://localhost:8000` with student *Alex Sharma*.
   - Point out the **DNA Dashboard**: highlight the real mistake distribution chart (Array Indexing vs Off-by-one), the activity timeline, and the personalized insights derived strictly from real DB records.
   - Switch the profile to *Rohan Verma*: show the clean empty state without fabricated percentages.
3. **Feature Two: Hint-First Learning (1m)**:
   - Launch the challenge: **"Print Elements of an Array (C)"**.
   - Show **Stage 1 (Understand)**: interactive output prediction quiz.
   - Switch language to **हिन्दी / Hinglish** to show localized accessible learning.
   - Request a **Progressive Hint (Stage 3 & 4)**: demonstrate how CodeMentor guides the student to reason about valid array bounds (`0` to `size - 1`).
   - Fix code in the editor (`i < size`) and click **Run & Verify Code**.
   - Show the **Verified Test Execution** console badge, millisecond execution time, and pass status.
4. **Closing & Retention (30s)**:
   - Return to the **Debugging DNA Dashboard**: observe that Rohan's learning profile now persistently reflects his successful attempt and hint usage!
