"""
CodeMentor - End-to-End Integration & Acceptance Test Suite
Runs in-process HTTP simulation of server.CodeMentorHandler, testing the full
API pipeline, database persistence, sandbox execution, and DNA tracking without
requiring external socket permissions.
"""

import io
import sys
import os
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import database
import code_executor
import analyzer
import tutor_engine
import server

class MockSocket:
    def __init__(self, data_bytes=b""):
        self.rfile = io.BytesIO(data_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if "b" in mode:
            if "r" in mode:
                return self.rfile
            return self.wfile
        raise ValueError("Only binary mode supported")

    def sendall(self, b):
        self.wfile.write(b)

class MockServer:
    def __init__(self):
        pass

def invoke_http(method: str, path: str, payload: dict = None):
    body_bytes = json.dumps(payload).encode("utf-8") if payload is not None else b""
    headers = [
        f"{method} {path} HTTP/1.1",
        "Host: localhost",
        f"Content-Length: {len(body_bytes)}",
        "Content-Type: application/json",
        "",
        ""
    ]
    raw_request = "\r\n".join(headers).encode("utf-8") + body_bytes
    mock_sock = MockSocket(raw_request)

    # Instantiate handler with mock socket
    class SubHandler(server.CodeMentorHandler):
        def __init__(self, request, client_address, srv):
            self.request = request
            self.client_address = client_address
            self.server = srv
            self.setup()
            try:
                self.handle()
            finally:
                self.finish()

    handler = SubHandler(mock_sock, ("127.0.0.1", 12345), MockServer())
    raw_response = mock_sock.wfile.getvalue()

    # Parse response
    parts = raw_response.split(b"\r\n\r\n", 1)
    header_part = parts[0].decode("utf-8", errors="replace")
    body_part = parts[1] if len(parts) > 1 else b""

    status_line = header_part.split("\r\n")[0]
    status_code = int(status_line.split(" ")[1])

    try:
        data = json.loads(body_part.decode("utf-8", errors="replace"))
    except Exception:
        data = body_part.decode("utf-8", errors="replace")

    return status_code, data

def run_tests():
    print(f"\n=======================================================")
    print(f"Running CodeMentor Full Verification Test Suite")
    print(f"=======================================================\n")

    passed_count = 0
    total_count = 0

    def assert_test(name: str, condition: bool, extra: str = ""):
        nonlocal passed_count, total_count
        total_count += 1
        if condition:
            passed_count += 1
            print(f"  PASS: {name} {extra}")
        else:
            print(f"  FAIL: {name} - {extra}")
            raise AssertionError(f"Test failed: {name} - {extra}")

    # Initialize / reset DB for clean test run
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM hint_logs")
    c.execute("DELETE FROM attempts WHERE user_id >= 3")
    conn.commit()
    conn.close()
    database.init_db()

    # 1. Health Endpoint
    status, health = invoke_http("GET", "/api/health")
    assert_test("Health Endpoint Returns 200", status == 200)
    assert_test("Health Service Identified", health.get("service") == "CodeMentor AI Learning Platform")
    assert_test("Python Compiler Available", health["compilers"]["python"] is True)
    assert_test("GCC C Compiler Checked", "gcc_c" in health["compilers"])

    # 2. Users Endpoint
    status, users_res = invoke_http("GET", "/api/users")
    assert_test("Users Endpoint Returns 200", status == 200)
    assert_test("Seeded Users Present", len(users_res.get("users", [])) >= 3)

    # 3. DNA Profile for Alex Sharma (User ID 1)
    status, alex_dna = invoke_http("GET", "/api/dna/1")
    assert_test("Alex DNA Returns 200", status == 200)
    assert_test("Alex Is Not Empty State", alex_dna["empty_state"] is False)
    assert_test("Alex Real Solve Rate Calculated", alex_dna["summary"]["solve_rate"] > 0)
    assert_test("Alex Real Insights Present", len(alex_dna["personalized_insights"]) > 0)
    print(f"    -> Alex Solve Rate: {alex_dna['summary']['solve_rate']}%, Top Mistake: {alex_dna['mistake_distribution'][0]['name']}")

    # 4. DNA Profile for Brand New Learner Rohan Verma (User ID 3)
    status, rohan_dna = invoke_http("GET", "/api/dna/3")
    assert_test("Rohan DNA Returns 200", status == 200)
    assert_test("Rohan Empty State True (Zero Fabricated Stats)", rohan_dna["empty_state"] is True)
    assert_test("Rohan Attempts Exactly 0", rohan_dna["summary"]["total_attempts"] == 0)
    assert_test("Rohan Welcome Insight Generated", "Welcome to CodeMentor" in rohan_dna["personalized_insights"][0]["text"])

    # 5. Problems Catalog
    status, probs_res = invoke_http("GET", "/api/problems")
    assert_test("Problems Catalog Returns 200", status == 200)
    assert_test("Problems Catalog Contains Curated Items", len(probs_res["problems"]) >= 5)

    # 6. End-to-End Array Boundary Bug Flow in C (Problem ID 1)
    print("\n--- Testing End-to-End Array Boundary Debugging Flow in C ---")
    start_payload = {
        "user_id": 3, # Use Rohan Verma to test progression from empty state
        "problem_id": 1,
        "lang": "en"
    }
    status, start_res = invoke_http("POST", "/api/attempts/start", start_payload)
    assert_test("Start Attempt Returns 201 Created", status == 201)
    attempt_id = start_res["attempt_id"]
    assert_test("Attempt ID Generated", attempt_id > 0)
    assert_test("Bug Identified in Array Indexing or Off-by-One", start_res["classification"]["primary_category"] in ("array_indexing", "off_by_one"))
    assert_test("Array Indexing Present in Detected Categories", "array_indexing" in start_res["classification"]["categories"])
    assert_test("Initial Stage is Stage 1 (Understand)", start_res["stage"]["stage_number"] == 1)

    # 7. Stage 1 Interaction: Submit Prediction
    predict_payload = {
        "action": "submit_prediction",
        "user_input": "Selected Option 0: Accesses memory outside array",
        "lang": "en"
    }
    status, stage2 = invoke_http("POST", f"/api/attempts/{attempt_id}/interact", predict_payload)
    assert_test("Submit Prediction Advances to Stage 2", stage2["stage_number"] == 2)

    # 8. Request Progressive Hint
    hint_payload = {
        "action": "request_hint",
        "user_input": "Need a hint",
        "lang": "en"
    }
    status, stage3 = invoke_http("POST", f"/api/attempts/{attempt_id}/interact", hint_payload)
    assert_test("Hint Request Advances to Stage 3", stage3["stage_number"] == 3)
    assert_test("Hint Count Incremented to 1", stage3["hints_used"] == 1)

    # 9. Verify Hinglish Multi-Language Support
    status, stage3_hi = invoke_http("GET", f"/api/attempts/{attempt_id}?stage=3&lang=hinglish")
    assert_test("Hinglish Stage 3 Content Available", "dhyan" in stage3_hi["attempt_stage"]["hint"].lower() or "operator" in stage3_hi["attempt_stage"]["hint"].lower())
    print(f"    -> Hinglish Hint Preview: {stage3_hi['attempt_stage']['hint'][:60]}...")

    # 10. Request Stronger Hint
    status, stage4 = invoke_http("POST", f"/api/attempts/{attempt_id}/interact", hint_payload)
    assert_test("Second Hint Request Advances to Stage 4", stage4["stage_number"] == 4)
    assert_test("Hint Count Incremented to 2", stage4["hints_used"] == 2)

    # 11. Submit Incorrect Attempt (Still with <= size bug)
    wrong_code = """#include <stdio.h>
void printArray(int arr[], int size) {
    for (int i = 0; i <= size; i++) {
        printf("%d ", arr[i]);
    }
    printf("\\n");
}
int main() {
    int numbers[5] = {10, 20, 30, 40, 50};
    printArray(numbers, 5);
    return 0;
}
"""
    status, verify_fail = invoke_http("POST", f"/api/attempts/{attempt_id}/verify", {"code": wrong_code, "lang": "en"})
    assert_test("Incorrect Submission Tested in Sandbox", verify_fail["is_solved"] is False)
    assert_test("Verification Status Marked as Failed", verify_fail["execution_result"]["all_passed"] is False)

    # 12. Submit Correct Attempt (Fixed loop condition to i < size)
    fixed_code = """#include <stdio.h>
void printArray(int arr[], int size) {
    for (int i = 0; i < size; i++) {
        printf("%d ", arr[i]);
    }
    printf("\\n");
}
int main() {
    int numbers[5] = {10, 20, 30, 40, 50};
    printArray(numbers, 5);
    return 0;
}
"""
    status, verify_pass = invoke_http("POST", f"/api/attempts/{attempt_id}/verify", {"code": fixed_code, "lang": "en"})
    assert_test("Correct Submission Verified in Sandbox", verify_pass["is_solved"] is True)
    assert_test("All Sandbox Tests Passed", verify_pass["execution_result"]["all_passed"] is True)
    assert_test("Advances to Stage 7 (Explanation)", verify_pass["next_stage_data"]["stage_number"] == 7)

    # 13. Verify Persistent Debugging DNA Update for Rohan (User ID 3)
    status, rohan_dna_updated = invoke_http("GET", "/api/dna/3")
    assert_test("Rohan DNA No Longer Empty State", rohan_dna_updated["empty_state"] is False)
    assert_test("Rohan Has Exactly 1 Attempt Recorded", rohan_dna_updated["summary"]["total_attempts"] == 1)
    assert_test("Rohan Has Exactly 1 Solved Attempt", rohan_dna_updated["summary"]["solved_count"] == 1)
    assert_test("Rohan Solve Rate Is Exactly 100.0%", rohan_dna_updated["summary"]["solve_rate"] == 100.0)
    assert_test("Rohan Hints Recorded as 2", rohan_dna_updated["summary"]["total_hints_used"] == 2)
    rohan_slugs = [d["slug"] for d in rohan_dna_updated["mistake_distribution"]]
    assert_test("Rohan DNA Category Shows Array Indexing", "array_indexing" in rohan_slugs)
    assert_test("Rohan DNA Category Shows Off-by-One", "off_by_one" in rohan_slugs)

    # 14. Custom Code Debugging Submission
    print("\n--- Testing Custom Code Debugger ---")
    custom_payload = {
        "user_id": 1,
        "language": "python",
        "code": "def find_max(nums):\n    max_val = 0\n    for n in nums:\n        if n > max_val: max_val = n\n    return max_val",
        "description": "Fails on negative numbers [-10, -5, -20]",
        "lang": "en"
    }
    status, custom_res = invoke_http("POST", "/api/custom-debug", custom_payload)
    assert_test("Custom Code Submission Returns 201", status == 201)
    assert_test("Custom Mistake Classified into Taxonomy", "algorithm_logic" in custom_res["classification"]["categories"])

    # 15. New Student Registration
    print("\n--- Testing Student Registration & Persistence ---")
    reg_payload = {
        "username": f"hackathon_judge_{int(time.time())}",
        "display_name": "Hackathon Judge",
        "password": "securepassword"
    }
    status, reg_res = invoke_http("POST", "/api/auth/register", reg_payload)
    assert_test("Register New Student Returns 201 Created", status == 201)
    judge_id = reg_res["user"]["id"]
    status, judge_dna = invoke_http("GET", f"/api/dna/{judge_id}")
    assert_test("Registered Student Starts with Clean Empty DNA", judge_dna["empty_state"] is True)

    # 16. Test Python Loop Boundary Problem (Problem ID 3)
    print("\n--- Testing Python Loop Boundary Problem ---")
    py_start = {
        "user_id": 1,
        "problem_id": 3,
        "lang": "en"
    }
    status, py_res = invoke_http("POST", "/api/attempts/start", py_start)
    assert_test("Start Python Loop Problem Returns 201", status == 201)
    py_attempt_id = py_res["attempt_id"]
    # Solve it with correct code
    py_fixed = """def sum_numbers(n):
    total = 0
    for i in range(1, n + 1):
        total += i
    return total

if __name__ == "__main__":
    result = sum_numbers(5)
    print(f"Sum = {result}")
"""
    status, py_verify = invoke_http("POST", f"/api/attempts/{py_attempt_id}/verify", {"code": py_fixed, "lang": "en"})
    assert_test("Python Problem Verified and Solved", py_verify["is_solved"] is True)
    assert_test("Python Test Result Passed", py_verify["execution_result"]["all_passed"] is True)

    print(f"\n=======================================================")
    print(f"ALL {passed_count}/{total_count} INTEGRATION TESTS PASSED PERFECTLY!")
    print(f"=======================================================\n")
    return True

if __name__ == "__main__":
    run_tests()
