"""
test_router.py — Phase 26 Routing Accuracy Test
Tests 35+ user inputs to verify fast_route() correctly classifies intents.
Run from project root: python src/test_router.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from router import fast_route

# Test cases: (user_input, expected_action)
TEST_CASES = [
    # --- Battery (should route to BATTERY, not QA) ---
    ("what is my battery percentage?", "ACTION:BATTERY"),
    ("how much battery do I have?", "ACTION:BATTERY"),
    ("battery status", "ACTION:BATTERY"),
    ("battery level", "ACTION:BATTERY"),
    ("is it charging?", "ACTION:BATTERY"),
    ("check battery", "ACTION:BATTERY"),
    ("what's my battery level", "ACTION:BATTERY"),
    ("charging status", "ACTION:BATTERY"),
    ("am i charging", "ACTION:BATTERY"),

    # --- Processes (should route to PROCESSES, not QA) ---
    ("list top 10 running processes", "ACTION:PROCESSES"),
    ("show me what is running", "ACTION:PROCESSES"),
    ("list top 10 processes", "ACTION:PROCESSES"),
    ("show running programs", "ACTION:PROCESSES"),
    ("what is running", "ACTION:PROCESSES"),
    ("active processes", "ACTION:PROCESSES"),
    ("task list", "ACTION:PROCESSES"),
    ("running apps", "ACTION:PROCESSES"),

    # --- General QA (should remain QA) ---
    ("what is machine learning?", "ACTION:QA"),
    ("who invented the telephone?", "ACTION:QA"),
    ("explain quantum computing", "ACTION:QA"),
    ("what is python?", "ACTION:QA"),
    ("how does gravity work?", "ACTION:QA"),
    ("tell me about AI", "ACTION:QA"),

    # --- System commands ---
    ("shutdown", "ACTION:SHUTDOWN"),
    ("turn off computer", "ACTION:SHUTDOWN"),
    ("restart pc", "ACTION:RESTART"),
    ("reboot my laptop", "ACTION:RESTART"),
    ("put computer to sleep", "ACTION:SLEEP"),
    ("cancel shutdown", "ACTION:CANCEL_SHUTDOWN"),

    # --- Greetings ---
    ("hi", "ACTION:QA"),
    ("hello", "ACTION:QA"),
    ("good morning", "ACTION:QA"),

    # --- File operations ---
    ("rename file test.txt", "ACTION:RENAME_FILE"),
    ("delete file old.txt", "ACTION:DELETE_FILE"),
    ("list files", "ACTION:LIST_FILES"),

    # --- Clear/Reset ---
    ("clear chat", "ACTION:CLEAR_HISTORY"),
    ("reset training", "ACTION:RESET_TRAINING"),

    # --- Web/URL ---
    ("open google.com", "ACTION:OPEN_URL"),
    ("search the web for python tutorials", "ACTION:SEARCH_WEB"),

    # --- Stock ---
    ("stock price of reliance", "ACTION:FETCH_STOCK"),
]

def run_tests():
    passed = 0
    failed = 0
    total = len(TEST_CASES)

    print(f"\n{'='*70}")
    print(f"  NEXUS Router Test — Phase 26 Intent Classification Fix")
    print(f"  Testing {total} inputs...")
    print(f"{'='*70}\n")

    for user_input, expected in TEST_CASES:
        result = fast_route(user_input)
        actual = result[0] if result else "None (→ LLM)"

        if actual == expected:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        # Only print failures and a summary
        if actual != expected:
            print(f"  {status}: \"{user_input}\"")
            print(f"         Expected: {expected}")
            print(f"         Got:      {actual}")
            print()

    accuracy = (passed / total) * 100
    print(f"{'='*70}")
    print(f"  Results: {passed}/{total} passed ({accuracy:.1f}% accuracy)")
    if failed > 0:
        print(f"  {failed} test(s) FAILED")
    else:
        print(f"  ALL TESTS PASSED!")
    print(f"{'='*70}\n")

    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
