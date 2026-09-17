"""
test_ollama_integration.py
--------------------------
PHASE 2C - Full LangGraph + Ollama Integration Test

This script runs the COMPLETE workflow through LangGraph.

The full pipeline is:
    START
      |
      v (LangGraph)
    Agent 1: AcademicProfileAgent  -> retrieves student profile
      |
      v (LangGraph)
    Agent 2: CourseAnalysisAgent   -> scores all 10 electives
      |
      v (LangGraph)
    Agent 3: RecommendationAgent   -> selects Top 3 + calls Ollama for explanations
      |
      v
    END

Ollama is NOT bypassed. The full chain runs.

Tests:
    1. S001 (Aanya Sharma) — AI student — expect AI electives at top
    2. S999 (invalid)      — graceful error handling

Usage:
    python tests/test_ollama_integration.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import the LangGraph workflow entry point (same as before — unchanged)
from workflow.advisor_graph import run_advisor
from llm.ollama_client import is_ollama_running, is_model_available, OLLAMA_MODEL


def bar(char="=", width=50):
    print(char * width)


def run_integration_test(student_id):
    """
    Runs the full LangGraph + Ollama pipeline for a student and prints results.

    Args:
        student_id (str): e.g., "S001"
    """
    bar()
    print(f"  OLLAMA + LANGGRAPH INTEGRATION TEST")
    print(f"  Student ID : {student_id}")
    bar()

    # Show Ollama status before running
    ollama_ok = is_ollama_running() and is_model_available(OLLAMA_MODEL)
    if ollama_ok:
        print(f"\n  Ollama status : [RUNNING] - {OLLAMA_MODEL} available")
        print("  Explanations  : LLM-generated\n")
    else:
        print(f"\n  Ollama status : [UNAVAILABLE]")
        print("  Explanations  : Rule-based fallback will be used\n")

    # ── Run the complete LangGraph workflow ────────────────────────────────────
    # This calls: Agent 1 -> Agent 2 -> Agent 3 (with Ollama) via LangGraph
    final_state = run_advisor(student_id)

    # ── Extract results from the final LangGraph state ─────────────────────────
    profile         = final_state.get("profile", {})
    course_analysis = final_state.get("course_analysis", [])
    recommendation  = final_state.get("recommendation", {})

    # ── AGENT 1 STATUS ─────────────────────────────────────────────────────────
    print()
    bar("-", 50)
    print("  [LangGraph] Academic Profile Agent")
    bar("-", 50)

    if profile.get("error"):
        print(f"\n  [ERROR] {profile.get('message')}")
        bar()
        return

    print(f"\n  [OK] Profile retrieved")
    print(f"  Student  : {profile['name']} | {profile['program']} | Sem {profile['semester']}")
    print(f"  Subjects : {', '.join(profile['completed_subjects'])}")
    print(f"  Goal     : {profile['career_goal']}")
    print(f"  Domain   : {profile['preferred_domain']}")

    # ── AGENT 2 STATUS ─────────────────────────────────────────────────────────
    print()
    bar("-", 50)
    print("  [LangGraph] Course Analysis Agent")
    bar("-", 50)

    if not course_analysis:
        print("\n  [WARN] No course analysis returned.")
    else:
        eligible   = [c for c in course_analysis if c["eligible"]]
        ineligible = [c for c in course_analysis if not c["eligible"]]
        eligible.sort(key=lambda c: c["score"], reverse=True)
        print(f"\n  [OK] Courses analyzed: {len(course_analysis)} total")
        print(f"  Eligible   : {len(eligible)} courses")
        print(f"  Ineligible : {len(ineligible)} courses (missing prerequisites)")
        print(f"\n  Eligible courses (sorted by score):")
        for c in eligible:
            print(f"    + {c['course_name']:<32} {c['score']}/100")

    # ── AGENT 3 STATUS ─────────────────────────────────────────────────────────
    print()
    bar("-", 50)
    print("  [LangGraph] Recommendation Agent")
    bar("-", 50)

    if recommendation.get("no_results"):
        print(f"\n  [INFO] {recommendation.get('message')}")
        bar()
        return

    recs     = recommendation.get("recommendations", [])
    llm_used = recommendation.get("llm_used", False)

    print(f"\n  [OK] Top {len(recs)} course(s) selected by Python scoring system")
    if llm_used:
        print(f"  [OK] Ollama ({OLLAMA_MODEL}) generated personalized explanations")
    else:
        print(f"  [INFO] Ollama unavailable — rule-based fallback explanations used")

    # ── PRINT FINAL RECOMMENDATIONS ───────────────────────────────────────────
    print()
    bar("-", 50)
    print(f"  FINAL RECOMMENDATIONS FOR: {profile['name'].upper()}")
    bar("-", 50)

    for rec in recs:
        src_label = "[LLM]" if rec.get("explanation_source") == "llm" else "[Rule-based]"
        print(f"\n  {rec['rank']}. {rec['course_name']}  --  {rec['score']}/100")
        print(f"     Domain     : {rec['domain']}")
        print(f"     Difficulty : {rec['difficulty']}")
        print(f"\n     Explanation {src_label}:")
        # Word-wrap the explanation at ~70 chars for readability
        words  = rec["explanation"].split()
        line   = "     "
        for word in words:
            if len(line) + len(word) + 1 > 75:
                print(line)
                line = "     " + word
            else:
                line += (" " if line != "     " else "") + word
        if line.strip():
            print(line)
        print()
        bar("-", 50)

    bar()
    print(f"  INTEGRATION TEST COMPLETE")
    bar()
    print()


if __name__ == "__main__":
    # ── TEST 1: Valid student — S001 Aanya Sharma ─────────────────────────────
    run_integration_test("S001")

    print("\n\n")

    # ── TEST 2: Valid student — S005 Sneha Patil (Cyber Security) ─────────────
    run_integration_test("S005")

    print("\n\n")

    # ── TEST 3: Invalid student — graceful error ───────────────────────────────
    print("Testing graceful error handling with invalid student ID (S999):")
    run_integration_test("S999")
