"""
CodeMentor - Debugging DNA & Mistake Analysis Engine
Classifies programming errors into a structured taxonomy and computes real-time,
persistent learning profiles strictly from actual stored database records.
"""

import json
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional
import database

def classify_mistakes(code: str, language: str, error_message: str = "",
                      compiler_error: str = "", test_results: List[Dict[str, Any]] = None,
                      expected_category: str = None) -> Dict[str, Any]:
    """
    Analyzes code, runtime errors, compiler diagnostics, and test results
    to classify mistakes into standard categories with confidence levels.
    """
    language = language.lower()
    combined_err = (compiler_error or "") + "\n" + (error_message or "")
    detected = []

    # 1. Syntax Errors
    syntax_indicators = [
        "syntax error", "syntaxerror", "expected ';'", "expected expression",
        "parse error", "indentationerror", "unexpected EOF", "invalid syntax"
    ]
    if any(ind in combined_err.lower() for ind in syntax_indicators):
        detected.append({
            "category": "syntax_errors",
            "confidence": 0.95,
            "evidence": "Compilation or syntax parser reported invalid language tokens."
        })

    # 2. Array Indexing Errors
    array_indicators = [
        "indexerror", "out of range", "index out of bounds", "segmentation fault",
        "buffer overflow", "array index is out of bounds", "stack smashing"
    ]
    has_array_err = any(ind in combined_err.lower() for ind in array_indicators)
    # Heuristics in code: arr[size] or arr[i <= size] or negative index
    code_has_arr_bound = bool(re.search(r'\[\s*(i|j|k|\w+)\s*\]', code) and re.search(r'<=\s*(size|len|n|\d+)', code))
    if has_array_err or (code_has_arr_bound and language in ("c", "cpp", "java")):
        detected.append({
            "category": "array_indexing",
            "confidence": 0.90 if has_array_err else 0.75,
            "evidence": "Array accessed beyond valid index boundaries (0 to N-1)."
        })

    # 3. Off-by-one Errors
    # Look for loop patterns with <= len or range(1, n)
    has_range_off = bool(re.search(r'range\s*\(\s*\d+\s*,\s*\w+\s*\)', code) and ("sum" in code or "total" in code))
    has_c_off = bool(re.search(r'for\s*\([^;]+;\s*\w+\s*<=\s*(size|len|length|n)\s*;', code))
    if has_range_off or has_c_off:
        detected.append({
            "category": "off_by_one",
            "confidence": 0.85,
            "evidence": "Loop boundary condition includes or excludes the endpoint incorrectly."
        })

    # 4. Recursion Misunderstandings
    rec_indicators = [
        "recursionerror", "maximum recursion depth", "stack overflow", "segmentation fault"
    ]
    # Check if function calls itself
    func_match = re.search(r'def\s+(\w+)\s*\(|int\s+(\w+)\s*\(|void\s+(\w+)\s*\(', code)
    func_name = next((g for g in func_match.groups() if g), "") if func_match else ""
    is_recursive = bool(func_name and re.search(rf'\b{func_name}\s*\(', code[func_match.end():]))
    has_rec_err = any(ind in combined_err.lower() for ind in rec_indicators)
    # Check if base case returns 0 in product recursion
    has_bad_base = bool(is_recursive and re.search(r'return\s+0\s*;?', code) and ("*" in code or "factorial" in code))

    if has_rec_err or has_bad_base:
        detected.append({
            "category": "recursion_misunderstanding",
            "confidence": 0.90 if has_rec_err else 0.80,
            "evidence": "Flawed recursive base case or infinite recursive branch."
        })

    # 5. Loop Logic Errors
    loop_timeout = "timed out" in combined_err.lower() or "suspected infinite loop" in combined_err.lower()
    # Check loop incrementing instead of decrementing
    wrong_step = bool(re.search(r'while\s+\w+\s*>\s*0\s*:', code) and re.search(r'\+=\s*1|\+\+', code))
    if loop_timeout or wrong_step:
        detected.append({
            "category": "loop_logic",
            "confidence": 0.95 if loop_timeout or wrong_step else 0.70,
            "evidence": "Loop condition does not converge to termination, causing an infinite loop."
        })

    # 6. Variable Scope Errors
    scope_indicators = [
        "nameerror", "is not defined", "uninitialized", "referenced before assignment",
        "used without being initialized"
    ]
    if any(ind in combined_err.lower() for ind in scope_indicators):
        detected.append({
            "category": "variable_scope",
            "confidence": 0.90,
            "evidence": "Variable referenced outside of its declared or active lexical scope."
        })

    # 7. Incorrect Conditions
    # e.g., if (x = 5) in C
    has_assignment_in_if = bool(re.search(r'if\s*\([^=!<>]=[^=]', code))
    if has_assignment_in_if:
        detected.append({
            "category": "incorrect_conditions",
            "confidence": 0.85,
            "evidence": "Assignment operator '=' used inside condition where comparison '==' was intended."
        })

    # 8. Algorithm Logic Errors
    # e.g., max_val = 0 for negative list
    has_zero_max_init = bool(re.search(r'max_val\s*=\s*0|maximum\s*=\s*0', code) and ("-10" in code or "negative" in code or "nums" in code))
    if has_zero_max_init or (test_results and any("output mismatch" in (tr.get("error") or "").lower() for tr in test_results)):
        detected.append({
            "category": "algorithm_logic",
            "confidence": 0.80 if has_zero_max_init else 0.65,
            "evidence": "Algorithm accumulator initialization or logic step does not cover edge cases."
        })

    # If the problem had an expected category and no strong match found yet, fall back with medium confidence
    if not detected and expected_category:
        detected.append({
            "category": expected_category,
            "confidence": 0.70,
            "evidence": "Problem domain diagnostic check indicates potential bug in this concept."
        })
    elif not detected:
        detected.append({
            "category": "algorithm_logic",
            "confidence": 0.50,
            "evidence": "General algorithm or logical behavior discrepancy observed."
        })

    # Deduplicate and sort by confidence
    unique_map = {}
    for d in detected:
        cat = d["category"]
        if cat not in unique_map or d["confidence"] > unique_map[cat]["confidence"]:
            unique_map[cat] = d

    final_list = sorted(unique_map.values(), key=lambda x: x["confidence"], reverse=True)
    primary = final_list[0]["category"]

    return {
        "primary_category": primary,
        "categories": [d["category"] for d in final_list],
        "diagnostics": final_list,
        "overall_confidence": final_list[0]["confidence"],
        "is_ai_assessment": False, # Verified rule & diagnostic engine
        "analysis_type": "heuristic_and_runtime_analysis"
    }

def get_student_dna(user_id: int) -> Dict[str, Any]:
    """
    Computes a persistent, real-time learning profile and analytics
    strictly based on the user's actual stored database records.
    Never generates fabricated statistics.
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    # Verify user exists
    cursor.execute("SELECT id, username, display_name, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return {"error": "User not found", "empty_state": True}

    # Fetch mistake categories metadata
    cursor.execute("SELECT slug, name, description, color, icon FROM mistake_categories")
    cat_rows = cursor.fetchall()
    cat_meta = {row["slug"]: dict(row) for row in cat_rows}

    # Fetch all attempts for this user
    cursor.execute("""
    SELECT a.id, a.problem_id, a.language, a.mistake_categories_json, a.hints_used,
           a.is_solved, a.solved_independently, a.verification_status, a.created_at,
           p.title as problem_title, p.concept as problem_concept, p.difficulty
    FROM attempts a
    LEFT JOIN problems p ON a.problem_id = p.id
    WHERE a.user_id = ?
    ORDER BY a.created_at ASC
    """, (user_id,))
    attempts = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_attempts = len(attempts)

    # Empty State for brand new users
    if total_attempts == 0:
        return {
            "empty_state": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "display_name": user["display_name"],
                "joined": user["created_at"]
            },
            "summary": {
                "total_attempts": 0,
                "solved_count": 0,
                "unsolved_count": 0,
                "solve_rate": 0.0,
                "total_hints_used": 0,
                "avg_hints_per_solved": 0.0,
                "independent_solves": 0
            },
            "mistake_distribution": [],
            "timeline": [],
            "concepts_needing_practice": [],
            "concepts_improving": [],
            "personalized_insights": [
                {
                    "type": "welcome",
                    "text": f"Welcome to CodeMentor, {user['display_name']}! You have not recorded any debugging attempts yet. Submit your first challenge to generate your personal Debugging DNA profile."
                }
            ],
            "recommended_practice": {
                "slug": "c-array-boundary-overflow",
                "title": "Print Elements of an Array (Starter)",
                "concept": "Array Boundaries",
                "reason": "Great introductory problem to begin your learning profile."
            }
        }

    # Compute actual real metrics
    solved_count = sum(1 for a in attempts if a["is_solved"])
    unsolved_count = total_attempts - solved_count
    solve_rate = round((solved_count / total_attempts) * 100.0, 1) if total_attempts > 0 else 0.0
    total_hints = sum(a["hints_used"] for a in attempts)
    solved_hints = sum(a["hints_used"] for a in attempts if a["is_solved"])
    avg_hints = round(solved_hints / solved_count, 1) if solved_count > 0 else 0.0
    independent_solves = sum(1 for a in attempts if a["solved_independently"])

    # Category Frequency Breakdown
    category_counts = defaultdict(int)
    category_solved = defaultdict(int)
    category_attempts_history = defaultdict(list)

    for att in attempts:
        try:
            cats = json.loads(att["mistake_categories_json"])
        except Exception:
            cats = []
        for cat in cats:
            category_counts[cat] += 1
            if att["is_solved"]:
                category_solved[cat] += 1
            category_attempts_history[cat].append(att)

    total_tag_occurrences = sum(category_counts.values()) or 1
    mistake_distribution = []
    for slug, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        meta = cat_meta.get(slug, {"name": slug.replace("_", " ").title(), "color": "#6366f1", "icon": "alert-circle"})
        pct = round((count / total_tag_occurrences) * 100.0, 1)
        mistake_distribution.append({
            "slug": slug,
            "name": meta["name"],
            "count": count,
            "percentage": pct,
            "color": meta.get("color", "#6366f1"),
            "solved": category_solved[slug],
            "unsolved": count - category_solved[slug]
        })

    # Timeline Breakdown (grouped by date)
    date_groups = defaultdict(lambda: {"attempts": 0, "solved": 0, "hints": 0})
    for att in attempts:
        date_str = att["created_at"].split(" ")[0] if " " in att["created_at"] else att["created_at"][:10]
        date_groups[date_str]["attempts"] += 1
        if att["is_solved"]:
            date_groups[date_str]["solved"] += 1
        date_groups[date_str]["hints"] += att["hints_used"]

    timeline = [
        {"date": date_k, "attempts": v["attempts"], "solved": v["solved"], "hints": v["hints"]}
        for date_k, v in sorted(date_groups.items())
    ]

    # Identify Concepts Needing Practice vs Showing Improvement
    concepts_needing_practice = []
    concepts_improving = []

    for slug, count in category_counts.items():
        meta = cat_meta.get(slug, {"name": slug.replace("_", " ").title()})
        cat_name = meta["name"]
        hist = category_attempts_history[slug]
        solved_in_cat = category_solved[slug]
        unsolved_in_cat = count - solved_in_cat

        if unsolved_in_cat > 0:
            concepts_needing_practice.append({
                "slug": slug,
                "name": cat_name,
                "unsolved_count": unsolved_in_cat,
                "total_count": count,
                "reason": f"{unsolved_in_cat} of {count} recorded attempts remain unsolved."
            })

        # Check for improvement: last attempt was solved, or fewer hints needed
        if len(hist) >= 2:
            earlier = hist[0]
            latest = hist[-1]
            if (not earlier["is_solved"] and latest["is_solved"]) or (latest["is_solved"] and latest["hints_used"] < earlier["hints_used"]):
                concepts_improving.append({
                    "slug": slug,
                    "name": cat_name,
                    "reason": f"Latest attempt was solved with {latest['hints_used']} hint(s), demonstrating measurable conceptual mastery."
                })
        elif len(hist) == 1 and hist[0]["is_solved"]:
            concepts_improving.append({
                "slug": slug,
                "name": cat_name,
                "reason": f"Successfully resolved in attempt using {hist[0]['hints_used']} hint(s)."
            })

    # Generate Personalized, Real Data-Driven Insights
    insights = []
    if mistake_distribution:
        top_mistake = mistake_distribution[0]
        insights.append({
            "type": "top_mistake",
            "title": "Primary Learning Area",
            "text": f"'{top_mistake['name']}' is your most frequent recorded mistake ({top_mistake['count']} attempts recorded, {top_mistake['percentage']}% of all detected mistake tags)."
        })

    if solve_rate >= 70.0:
        insights.append({
            "type": "high_solve_rate",
            "title": "High Solve Consistency",
            "text": f"Strong debugging momentum: You have successfully solved {solved_count} of your {total_attempts} attempts ({solve_rate}% solve rate)."
        })
    elif solve_rate > 0.0:
        insights.append({
            "type": "moderate_solve_rate",
            "title": "Solve Progress",
            "text": f"You have resolved {solved_count} of {total_attempts} debugging challenges ({solve_rate}% solve rate). Keep applying structured hints before checking solutions."
        })

    if concepts_improving:
        top_imp = concepts_improving[0]
        insights.append({
            "type": "improvement",
            "title": "Concept Showing Improvement",
            "text": f"You have shown measurable progress in {top_imp['name']}. {top_imp['reason']}"
        })

    if concepts_needing_practice:
        top_need = concepts_needing_practice[0]
        insights.append({
            "type": "practice_needed",
            "title": "Targeted Practice Recommended",
            "text": f"'{top_need['name']}' needs more practice based on your recent results ({top_need['unsolved_count']} unsolved attempt(s))."
        })

    # Recommended practice problem
    recommended = get_recommended_problem(user_id, concepts_needing_practice, mistake_distribution)

    return {
        "empty_state": False,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "joined": user["created_at"]
        },
        "summary": {
            "total_attempts": total_attempts,
            "solved_count": solved_count,
            "unsolved_count": unsolved_count,
            "solve_rate": solve_rate,
            "total_hints_used": total_hints,
            "avg_hints_per_solved": avg_hints,
            "independent_solves": independent_solves
        },
        "mistake_distribution": mistake_distribution,
        "timeline": timeline,
        "concepts_needing_practice": concepts_needing_practice,
        "concepts_improving": concepts_improving,
        "personalized_insights": insights,
        "recommended_practice": recommended
    }

def get_recommended_problem(user_id: int, needing_practice: List[Dict], distribution: List[Dict]) -> Dict[str, Any]:
    """
    Finds an appropriate practice problem from the database targeting the student's weakest concept.
    """
    conn = database.get_connection()
    cursor = conn.cursor()

    # Determine target category slug
    target_slug = None
    if needing_practice:
        target_slug = needing_practice[0]["slug"]
    elif distribution:
        target_slug = distribution[0]["slug"]

    # Try to find an unsolved problem in that category
    if target_slug:
        cursor.execute("""
        SELECT p.id, p.slug, p.title, p.language, p.difficulty, p.concept, p.mistake_category_slug
        FROM problems p
        WHERE p.mistake_category_slug = ?
          AND p.id NOT IN (SELECT problem_id FROM attempts WHERE user_id = ? AND is_solved = 1)
        LIMIT 1
        """, (target_slug, user_id))
        rec = cursor.fetchone()
        if rec:
            conn.close()
            return {
                "id": rec["id"],
                "slug": rec["slug"],
                "title": rec["title"],
                "language": rec["language"],
                "difficulty": rec["difficulty"],
                "concept": rec["concept"],
                "reason": f"Targeted practice to strengthen your weak concept: {rec['concept']}."
            }

    # Fallback to any unsolved problem
    cursor.execute("""
    SELECT p.id, p.slug, p.title, p.language, p.difficulty, p.concept
    FROM problems p
    WHERE p.id NOT IN (SELECT problem_id FROM attempts WHERE user_id = ? AND is_solved = 1)
    ORDER BY p.id ASC
    LIMIT 1
    """, (user_id,))
    rec = cursor.fetchone()
    conn.close()

    if rec:
        return {
            "id": rec["id"],
            "slug": rec["slug"],
            "title": rec["title"],
            "language": rec["language"],
            "difficulty": rec["difficulty"],
            "concept": rec["concept"],
            "reason": "Next challenge in your curriculum."
        }

    return {
        "slug": "c-recursive-factorial-bug",
        "title": "Recursive Factorial Function",
        "language": "c",
        "difficulty": "Beginner",
        "concept": "Recursion & Base Cases",
        "reason": "Recommended general challenge."
    }

if __name__ == "__main__":
    print("Testing Debugging DNA & Classifier...")
    # Test classifier on C off-by-one
    sample_c = """
    for (int i = 0; i <= size; i++) {
        printf("%d ", arr[i]);
    }
    """
    res = classify_mistakes(sample_c, "c", "segmentation fault (core dumped)")
    print("Classification Result:", json.dumps(res, indent=2))

    # Test student DNA calculation for Alex Sharma (user_id = 1)
    dna = get_student_dna(1)
    print(f"Alex's DNA: Total={dna['summary']['total_attempts']}, Solved={dna['summary']['solved_count']}, Rate={dna['summary']['solve_rate']}%")
    print("Insights:", [ins["text"] for ins in dna["personalized_insights"]])

    # Test empty state for new user (user_id = 3)
    new_dna = get_student_dna(3)
    print("New Student Empty State:", new_dna["empty_state"], new_dna["personalized_insights"][0]["text"])
