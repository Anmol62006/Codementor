"""
CodeMentor - Hint-First Learning Engine (8 Progressive Stages)
Guides students to think, hypothesize, and debug before viewing complete solutions.
Supports English & Hinglish, live AI providers (Gemini / OpenAI), and deterministic
pedagogical fallback for seamless hackathon demos.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
import database
import code_executor
import analyzer

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()

def get_ai_provider_status() -> Dict[str, Any]:
    """Returns the current status of AI integrations."""
    if GEMINI_API_KEY:
        return {
            "configured": True,
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "mode_label": f"Live Gemini AI Active ({GEMINI_MODEL})"
        }
    elif OPENAI_API_KEY:
        return {
            "configured": True,
            "provider": "openai",
            "model": OPENAI_MODEL,
            "mode_label": f"Live OpenAI Active ({OPENAI_MODEL})"
        }
    else:
        return {
            "configured": False,
            "provider": "deterministic_engine",
            "model": "codementor-heuristic-v1",
            "mode_label": "Demo Mode (Rule-Based Pedagogical Engine)"
        }

def call_live_ai(prompt: str, system_instruction: str = "") -> Optional[str]:
    """Calls Gemini or OpenAI REST API using Python's standard library urllib."""
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"System: {system_instruction}\n\nUser: {prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 600
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
                return None
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            print(f"[AI Warning] Gemini API HTTP {e.code}: {err_msg}. Falling back to deterministic engine.")
            return None
        except Exception as e:
            print(f"[AI Warning] Gemini API call failed: {e}. Falling back to deterministic engine.")
            return None

    if OPENAI_API_KEY:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 600
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "").strip()
                return None
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            print(f"[AI Warning] OpenAI API HTTP {e.code}: {err_msg}. Falling back to deterministic engine.")
            return None
        except Exception as e:
            print(f"[AI Warning] OpenAI API call failed: {e}. Falling back to deterministic engine.")
            return None

    return None

def get_stage_content(attempt_id: int, target_stage: int = None, lang: str = "en") -> Dict[str, Any]:
    """
    Retrieves or advances the content for a specific pedagogical stage in an attempt.
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT a.*, p.title, p.concept, p.difficulty, p.description, p.buggy_code,
           p.solution_code, p.test_cases_json, p.stages_config_json, p.mistake_category_slug
    FROM attempts a
    LEFT JOIN problems p ON a.problem_id = p.id
    WHERE a.id = ?
    """, (attempt_id,))
    attempt = cursor.fetchone()

    if not attempt:
        conn.close()
        return {"error": "Attempt not found"}

    attempt = dict(attempt)
    current_stage = target_stage or attempt["current_stage"]
    current_stage = max(1, min(8, current_stage))

    # Parse stages config from problem or build default for custom code
    stages_config = {}
    if attempt.get("stages_config_json"):
        try:
            stages_config = json.loads(attempt["stages_config_json"])
        except Exception:
            stages_config = {}

    lang = "hinglish" if lang.lower() in ("hi", "hinglish") else "en"
    ai_status = get_ai_provider_status()

    stage_data = {
        "stage_number": current_stage,
        "stage_name": _get_stage_name(current_stage),
        "total_stages": 8,
        "language": lang,
        "ai_provider": ai_status["provider"],
        "ai_label": ai_status["mode_label"],
        "is_ai_live": ai_status["configured"],
        "hints_used": attempt["hints_used"],
        "is_solved": bool(attempt["is_solved"]),
        "solution_unlocked": bool(attempt["solution_unlocked"]),
        "current_code": attempt["current_code"],
        "problem_title": attempt.get("title") or attempt.get("custom_title") or "Custom Code Challenge",
        "concept": attempt.get("concept") or "Programming Logic",
        "mistake_category": attempt.get("mistake_category_slug") or "algorithm_logic"
    }

    # Populate stage-specific content
    if current_stage == 1:
        # Stage 1: Understand
        cfg = stages_config.get("stage1_understand", {})
        prompt_text = cfg.get(lang) or cfg.get("en") or (
            "Socho program kya karne ki koshish kar raha hai aur iska output kya aana chahiye."
            if lang == "hinglish" else
            "Understand the problem statement and trace how the program executes step-by-step."
        )
        stage_data.update({
            "instruction": "Step 1: Understand the Problem",
            "prompt": prompt_text,
            "question": cfg.get("question", "What do you think will happen when this code runs?"),
            "options": cfg.get("options", [
                "The code works as expected",
                "It crashes or produces unexpected results",
                "It causes a compilation error",
                "It enters an infinite loop"
            ]),
            "correct_option_index": cfg.get("correct_option_index", 1),
            "action_text": "Submit Prediction"
        })

    elif current_stage == 2:
        # Stage 2: Investigate
        cfg = stages_config.get("stage2_investigate", {})
        prompt_text = cfg.get(lang) or cfg.get("en") or (
            "Code ko dhyan se padho aur batao kaun si line me gadbad lag rahi hai."
            if lang == "hinglish" else
            "Investigate the code line-by-line. Identify which line appears suspicious or causes abnormal behavior."
        )
        stage_data.update({
            "instruction": "Step 2: Investigate the Code",
            "prompt": prompt_text,
            "suspicious_line": cfg.get("suspicious_line", 3),
            "action_text": "Confirm Suspicious Line"
        })

    elif current_stage == 3:
        # Stage 3: First Hint
        cfg = stages_config.get("stage3_first_hint", {})
        hint_text = cfg.get(lang) or cfg.get("en") or (
            "Pehla Hint: Loop boundaries aur memory boundaries par dhyan do."
            if lang == "hinglish" else
            "First Hint: Check how the loop boundary interacts with the size of data."
        )
        if not cfg and ai_status["configured"]:
            ai_hint = call_live_ai(
                prompt=f"Language: {lang}. Provide a gentle Socratic clue without revealing code for a student debugging this code:\n\n{attempt.get('current_code', '')}",
                system_instruction="You are CodeMentor pedagogical tutor. Guide with a gentle clue. Do not give away the solution."
            )
            if ai_hint:
                hint_text = ai_hint
        stage_data.update({
            "instruction": "Step 3: First Clue (Gentle Hint)",
            "hint": hint_text,
            "action_text": "I Understand, Let Me Attempt"
        })

    elif current_stage == 4:
        # Stage 4: Stronger Hint
        cfg = stages_config.get("stage4_stronger_hint", {})
        hint_text = cfg.get(lang) or cfg.get("en") or (
            "Gehra Hint: Operator ko badal kar dekho taaki boundary cross na ho."
            if lang == "hinglish" else
            "Stronger Hint: Look closely at the comparison operator used in the loop condition."
        )
        if not cfg and ai_status["configured"]:
            ai_hint = call_live_ai(
                prompt=f"Language: {lang}. Provide a targeted diagnostic clue focusing on the bug location or operator without writing the complete solution for this code:\n\n{attempt.get('current_code', '')}",
                system_instruction="You are CodeMentor pedagogical tutor. Guide with a targeted clue."
            )
            if ai_hint:
                hint_text = ai_hint
        stage_data.update({
            "instruction": "Step 4: Targeted Clue (Stronger Hint)",
            "hint": hint_text,
            "action_text": "Proceed to Code Attempt"
        })

    elif current_stage == 5:
        # Stage 5: Attempt
        stage_data.update({
            "instruction": "Step 5: Write Your Correction",
            "prompt": "Apply your fix in the code editor on the right and click 'Verify Correction' to test your solution against our automated test suite.",
            "action_text": "Run & Verify Code"
        })

    elif current_stage == 6:
        # Stage 6: Verification
        stage_data.update({
            "instruction": "Step 6: Test Suite Verification",
            "verification_status": attempt["verification_status"],
            "last_test_results": json.loads(attempt["last_test_results_json"]) if attempt.get("last_test_results_json") else None
        })

    elif current_stage == 7:
        # Stage 7: Explanation
        cfg = stages_config.get("explanation", {})
        expl_text = cfg.get(lang) or cfg.get("en") or (
            "Bahut badiya! Samajhiye ki yeh fix kyun kaam karta hai aur is concept ko yaad rakhiye."
            if lang == "hinglish" else
            "Well done! Here is the conceptual breakdown of why this solution is correct."
        )
        if not cfg and ai_status["configured"]:
            ai_expl = call_live_ai(
                prompt=f"Language: {lang}. Explain conceptually why this solution works and what programming principle was learned:\n\n{attempt.get('current_code', '')}",
                system_instruction="You are CodeMentor pedagogical tutor. Explain the concept and provide a key takeaway."
            )
            if ai_expl:
                expl_text = ai_expl
        stage_data.update({
            "instruction": "Step 7: Conceptual Explanation",
            "explanation": expl_text,
            "takeaway": "Always verify edge conditions and index boundaries when iterating over collections."
        })

    elif current_stage == 8:
        # Stage 8: Unlock Solution
        stage_data.update({
            "instruction": "Step 8: Full Solution Code & Walkthrough",
            "solution_code": attempt.get("solution_code", "// Solution unlocked\n"),
            "action_text": "Solution Unlocked"
        })

    # Log interaction if changing stage
    if target_stage and target_stage != attempt["current_stage"]:
        cursor.execute("""
        UPDATE attempts
        SET current_stage = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (current_stage, attempt_id))
        conn.commit()

    conn.close()
    return stage_data

def interact_stage(attempt_id: int, user_input: str, action: str, lang: str = "en") -> Dict[str, Any]:
    """
    Handles student actions within a stage (submitting predictions, asking for stronger hints,
    skipping, or unlocking).
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,))
    attempt = cursor.fetchone()
    if not attempt:
        conn.close()
        return {"error": "Attempt not found"}

    attempt = dict(attempt)
    curr_stage = attempt["current_stage"]
    hints_used = attempt["hints_used"]

    # Action Handlers:
    if action == "request_hint":
        # Advance to stage 3 (first hint) or stage 4 (stronger hint)
        hints_used += 1
        next_stage = 4 if curr_stage >= 3 else 3
        cursor.execute("""
        UPDATE attempts
        SET current_stage = ?, hints_used = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (next_stage, hints_used, attempt_id))

        cursor.execute("""
        INSERT INTO hint_logs (attempt_id, stage_number, hint_type, prompt_shown, student_response, explanation_lang)
        VALUES (?, ?, 'hint_request', 'Requested progressive hint', ?, ?)
        """, (attempt_id, next_stage, user_input, lang))
        conn.commit()
        conn.close()
        return get_stage_content(attempt_id, next_stage, lang)

    elif action == "submit_prediction":
        # Advance from stage 1 to stage 2
        cursor.execute("""
        UPDATE attempts
        SET current_stage = 2, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (attempt_id,))
        cursor.execute("""
        INSERT INTO hint_logs (attempt_id, stage_number, hint_type, prompt_shown, student_response, explanation_lang)
        VALUES (?, 1, 'prediction', 'Submitted output prediction', ?, ?)
        """, (attempt_id, user_input, lang))
        conn.commit()
        conn.close()
        return get_stage_content(attempt_id, 2, lang)

    elif action == "submit_investigation":
        # Advance from stage 2 to stage 3
        cursor.execute("""
        UPDATE attempts
        SET current_stage = 3, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (attempt_id,))
        cursor.execute("""
        INSERT INTO hint_logs (attempt_id, stage_number, hint_type, prompt_shown, student_response, explanation_lang)
        VALUES (?, 2, 'investigation', 'Submitted suspicious line investigation', ?, ?)
        """, (attempt_id, user_input, lang))
        conn.commit()
        conn.close()
        return get_stage_content(attempt_id, 3, lang)

    elif action == "proceed_to_attempt":
        # Advance directly to stage 5 (Attempt)
        cursor.execute("""
        UPDATE attempts
        SET current_stage = 5, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (attempt_id,))
        conn.commit()
        conn.close()
        return get_stage_content(attempt_id, 5, lang)

    elif action == "unlock_solution":
        # Unlock complete solution (Stage 8)
        cursor.execute("""
        UPDATE attempts
        SET current_stage = 8, solution_unlocked = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (attempt_id,))
        cursor.execute("""
        INSERT INTO hint_logs (attempt_id, stage_number, hint_type, prompt_shown, student_response, explanation_lang)
        VALUES (?, 8, 'solution_unlock', 'Student unlocked full solution', ?, ?)
        """, (attempt_id, user_input, lang))
        conn.commit()
        conn.close()
        return get_stage_content(attempt_id, 8, lang)

    conn.close()
    return get_stage_content(attempt_id, curr_stage, lang)

def verify_student_code(attempt_id: int, code: str, lang: str = "en") -> Dict[str, Any]:
    """
    Compiles and executes student code against problem test cases.
    Updates the attempt record and Debugging DNA with verified results.
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT a.*, p.language as prob_lang, p.test_cases_json, p.mistake_category_slug
    FROM attempts a
    LEFT JOIN problems p ON a.problem_id = p.id
    WHERE a.id = ?
    """, (attempt_id,))
    attempt = cursor.fetchone()

    if not attempt:
        conn.close()
        return {"error": "Attempt not found"}

    attempt = dict(attempt)
    language = attempt.get("prob_lang") or attempt.get("language") or "python"

    test_cases = []
    if attempt.get("test_cases_json"):
        try:
            test_cases = json.loads(attempt["test_cases_json"])
        except Exception:
            test_cases = []

    # Run code in sandbox
    exec_result = code_executor.execute_code(code, language, test_cases)
    is_solved = bool(exec_result["all_passed"])
    status = "verified" if is_solved else "failed"

    # Solved independently if solved with 0 or 1 hints and without unlocking solution
    solved_independently = bool(is_solved and attempt["hints_used"] <= 1 and not attempt["solution_unlocked"])
    next_stage = 7 if is_solved else 5

    cursor.execute("""
    UPDATE attempts
    SET current_code = ?,
        current_stage = ?,
        is_solved = ?,
        solved_independently = ?,
        verification_status = ?,
        last_test_results_json = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        code,
        next_stage,
        1 if is_solved else 0,
        1 if solved_independently else 0,
        status,
        json.dumps(exec_result),
        attempt_id
    ))
    conn.commit()
    conn.close()

    stage_content = get_stage_content(attempt_id, next_stage, lang)
    return {
        "execution_result": exec_result,
        "is_solved": is_solved,
        "solved_independently": solved_independently,
        "next_stage_data": stage_content
    }

def _get_stage_name(stage: int) -> str:
    names = {
        1: "Understand",
        2: "Investigate",
        3: "First Hint",
        4: "Stronger Hint",
        5: "Code Attempt",
        6: "Verification",
        7: "Explanation",
        8: "Unlock Solution"
    }
    return names.get(stage, f"Stage {stage}")

if __name__ == "__main__":
    print("Testing Tutor Engine...")
    print("AI Provider Status:", get_ai_provider_status())
    content = get_stage_content(1, target_stage=1, lang="en")
    print("Stage 1 English:", content["instruction"], content["prompt"])
    content_hi = get_stage_content(1, target_stage=1, lang="hinglish")
    print("Stage 1 Hinglish:", content_hi["prompt"])
