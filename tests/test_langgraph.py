"""
test_langgraph.py
-----------------
PHASE 2B - LangGraph Workflow Test

This script tests the full LangGraph-orchestrated pipeline.

It verifies:
    1. The StateGraph runs Agent 1 -> Agent 2 -> Agent 3 in sequence
    2. State is correctly passed between nodes
    3. S001 (Aanya Sharma) gets correct Top 3 recommendations
    4. S999 (invalid ID) is handled gracefully without crashing

Usage:
    python tests/test_langgraph.py
"""

import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import the single entry point for our LangGraph workflow
from workflow.advisor_graph import run_advisor


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

def bar(char="=", width=50):
    print(char * width)

def section(title):
    print()
    bar("-", 50)
    print(f"  {title}")
    bar("-", 50)


# ─────────────────────────────────────────────
# MAIN TEST FUNCTION
# ─────────────────────────────────────────────

def test_langgraph_workflow(student_id):
    """
    Runs the LangGraph advisor workflow for a given student
    and prints the results in a clean, readable format.

    Args:
        student_id (str): e.g., "S001" or "S999"
    """

    bar("=", 50)
    print(f"  LANGGRAPH ADVISOR WORKFLOW")
    print(f"  Student ID : {student_id}")
    bar("=", 50)

    # ── Run the full LangGraph workflow ───────────────────────────────────────
    # run_advisor() internally:
    #   1. Builds the StateGraph
    #   2. Sets initial state = {"student_id": student_id}
    #   3. Runs all three nodes in sequence
    #   4. Returns the final state dictionary
    final_state = run_advisor(student_id)

    # ── Extract results from the final state ──────────────────────────────────
    profile         = final_state.get("profile", {})
    course_analysis = final_state.get("course_analysis", [])
    recommendation  = final_state.get("recommendation", {})

    # ── AGENT 1 STATUS ────────────────────────────────────────────────────────
    section("1  Academic Profile Agent")

    if profile.get("error"):
        print(f"  [ERROR] {profile.get('message')}")
        bar("=", 50)
        print("  Workflow ended early due to invalid student ID.")
        bar("=", 50)
        return

    print(f"  [OK] Profile retrieved successfully\n")
    print(f"  Student   : {profile['name']}")
    print(f"  Program   : {profile['program']}")
    print(f"  Semester  : {profile['semester']}")
    print(f"\n  Completed Subjects:")
    for subj in profile["completed_subjects"]:
        grade = profile["grades"].get(subj, "?")
        print(f"    - {subj}  (Grade: {grade})")
    print(f"\n  Career Goal        : {profile['career_goal']}")
    print(f"  Preferred Domain   : {profile['preferred_domain']}")
    print(f"  Difficulty Pref.   : {profile['difficulty_preference']}")

    # ── AGENT 2 STATUS ────────────────────────────────────────────────────────
    section("2  Course Analysis Agent")

    if not course_analysis:
        print("  [WARN] No courses analyzed.")
    else:
        eligible   = [c for c in course_analysis if c["eligible"]]
        ineligible = [c for c in course_analysis if not c["eligible"]]
        eligible.sort(key=lambda c: c["score"], reverse=True)

        print(f"  [OK] Courses analyzed: {len(course_analysis)} total\n")
        print(f"  Eligible ({len(eligible)}):")
        for c in eligible:
            print(f"    + {c['course_name']:<32} {c['score']}/100")

        print(f"\n  Ineligible ({len(ineligible)}) - missing prerequisites:")
        for c in ineligible:
            missing = [r for r in c["reasons"] if "missing" in r.lower()]
            print(f"    - {c['course_name']:<32} {'; '.join(missing)}")

    # ── AGENT 3 STATUS ────────────────────────────────────────────────────────
    section("3  Recommendation Agent")

    if recommendation.get("no_results"):
        print(f"  [INFO] {recommendation.get('message')}")
        bar("=", 50)
        return

    recs = recommendation.get("recommendations", [])
    print(f"  [OK] {len(recs)} recommendation(s) generated\n")

    # ── PRINT FINAL RECOMMENDATIONS ───────────────────────────────────────────
    bar("-", 50)
    print(f"  FINAL RECOMMENDATIONS FOR: {profile['name'].upper()}")
    bar("-", 50)

    for rec in recs:
        print(f"\n  {rec['rank']}. {rec['course_name']}  --  {rec['score']}/100")
        print(f"     Domain     : {rec['domain']}")
        print(f"     Difficulty : {rec['difficulty']}")
        print(f"     Explanation: {rec['explanation']}")

    bar("=", 50)
    print(f"  LANGGRAPH WORKFLOW COMPLETE")
    bar("=", 50)
    print()


# ─────────────────────────────────────────────
# RUN TESTS
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # ── TEST 1: Valid student — S001 Aanya Sharma (AI) ───────────────────────
    test_langgraph_workflow("S001")

    print("\n\n")

    # ── TEST 2: Valid student — S009 Ishaan Tiwari (Blockchain) ──────────────
    test_langgraph_workflow("S009")

    print("\n\n")

    # ── TEST 3: Invalid student — graceful error handling ─────────────────────
    print("Testing with invalid student ID (S999):")
    test_langgraph_workflow("S999")
