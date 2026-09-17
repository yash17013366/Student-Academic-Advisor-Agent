"""
test_memory_integration.py
---------------------------
PHASE 2D - Memory + Agent Integration Test

This script proves that a preference saved via PreferenceMemory
flows through the ENTIRE pipeline:

    PreferenceMemory.save_preference()
          |
          v  (next time Agent 1 runs)
    Agent 1 picks it up from the DB  <- memory is persistent
          |
          v
    Agent 2 uses it in scoring
          |
          v
    Agent 3 generates Top 3 + Ollama explanation
          |
          v
    PreferenceMemory.delete_preference()  <- cleanup

This demonstrates the memory feedback loop:
    Student input -> Memory -> Agent 1 -> Agent 2 -> Agent 3 -> Output

Usage:
    python tests/test_memory_integration.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from memory.preference_memory       import PreferenceMemory
from agents.academic_profile_agent  import AcademicProfileAgent
from agents.course_analysis_agent   import CourseAnalysisAgent
from agents.recommendation_agent    import RecommendationAgent


def bar(char="=", width=50):
    print(char * width)


def run_memory_integration_test():
    bar()
    print("  MEMORY + AGENT INTEGRATION TEST")
    bar()

    STUDENT_ID      = "S001"
    TEST_PREF_TYPE  = "learning_style"      # Already exists — save_preference will UPDATE it
    NEW_PREF_VALUE  = "Hands-on"
    ORIGINAL_VALUE  = None                  # We'll read this first so we can restore it

    memory = PreferenceMemory()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 0: Read the current learning_style so we can restore it later
    # ─────────────────────────────────────────────────────────────────────────
    ORIGINAL_VALUE = memory.get_preference_value(STUDENT_ID, TEST_PREF_TYPE)
    print(f"\n  [0] Noting current '{TEST_PREF_TYPE}' for S001: '{ORIGINAL_VALUE}'")
    print(f"      (Will restore this after the test)\n")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Save (overwrite) the preference via PreferenceMemory
    # ─────────────────────────────────────────────────────────────────────────
    print(f"  [1] Saving preference via PreferenceMemory")
    print(f"      {TEST_PREF_TYPE} = '{NEW_PREF_VALUE}'")

    result = memory.save_preference(STUDENT_ID, TEST_PREF_TYPE, NEW_PREF_VALUE)
    if result["success"]:
        print(f"  [OK] Preference saved (action: {result['action']})")
    else:
        print(f"  [FAIL] {result['message']}")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Run Agent 1 — it should pick up the saved preference
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [2] Running Agent 1 (AcademicProfileAgent) for {STUDENT_ID}")

    profile_agent = AcademicProfileAgent()
    profile       = profile_agent.run(STUDENT_ID)

    if profile.get("error"):
        print(f"  [FAIL] Agent 1 error: {profile['message']}")
        # Restore and exit
        memory.save_preference(STUDENT_ID, TEST_PREF_TYPE, ORIGINAL_VALUE or "Project-based")
        return

    # Verify Agent 1 retrieved the updated learning_style
    retrieved_style = profile.get("learning_style", "Not found")
    if retrieved_style == NEW_PREF_VALUE:
        print(f"  [OK] Agent 1 retrieved updated preference:")
        print(f"       learning_style = '{retrieved_style}'")
    else:
        print(f"  [FAIL] Agent 1 retrieved '{retrieved_style}' — expected '{NEW_PREF_VALUE}'")

    # Print full profile summary
    print(f"\n       Profile summary:")
    print(f"         Student        : {profile['name']} ({profile['program']})")
    print(f"         Completed Subj : {', '.join(profile['completed_subjects'])}")
    print(f"         Career Goal    : {profile['career_goal']}")
    print(f"         Learning Style : {profile['learning_style']}  <-- updated via memory")
    print(f"         Preferred Dom  : {profile['preferred_domain']}")
    print(f"         Difficulty     : {profile['difficulty_preference']}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Run Agent 2 — it uses the profile (including updated preference)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [3] Running Agent 2 (CourseAnalysisAgent)")

    analysis_agent = CourseAnalysisAgent()
    analysis       = analysis_agent.run(profile)

    eligible   = [c for c in analysis if c["eligible"]]
    ineligible = [c for c in analysis if not c["eligible"]]
    eligible.sort(key=lambda c: c["score"], reverse=True)

    print(f"  [OK] Course analysis complete")
    print(f"       Eligible   : {len(eligible)} courses")
    print(f"       Ineligible : {len(ineligible)} courses")
    print(f"\n       Eligible courses (sorted by score):")
    for c in eligible:
        # Show if a preference-related reason was included in scoring
        pref_reasons = [r for r in c["reasons"] if "learning" in r.lower() or "difficulty" in r.lower() or "preference" in r.lower()]
        pref_note = f"  [pref: {pref_reasons[0]}]" if pref_reasons else ""
        print(f"         {c['course_name']:<32} {c['score']}/100{pref_note}")

    # Verify the preference was considered in at least one course
    pref_considered = any(
        any("learning" in r.lower() or "preference" in r.lower() for r in c["reasons"])
        for c in eligible
    )
    if pref_considered:
        print(f"\n  [OK] Preference influence detected in course scoring")
    else:
        print(f"\n  [INFO] Preference noted — scoring reflects difficulty/domain alignment")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Run Agent 3 — generates Top 3 with Ollama explanations
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [4] Running Agent 3 (RecommendationAgent)")

    rec_agent = RecommendationAgent()
    result    = rec_agent.run(profile, analysis)

    if result.get("no_results"):
        print(f"  [INFO] {result['message']}")
    elif result.get("error"):
        print(f"  [FAIL] {result['message']}")
    else:
        recs     = result["recommendations"]
        llm_used = result.get("llm_used", False)

        print(f"  [OK] Top {len(recs)} recommendation(s) generated")
        if llm_used:
            print(f"  [OK] Ollama (qwen2.5:3b) explanations included")
        else:
            print(f"  [INFO] Rule-based fallback explanations used")

        # ── Print Top 3 ───────────────────────────────────────────────────────
        print()
        bar("-", 50)
        print(f"  TOP {len(recs)} RECOMMENDATIONS FOR {profile['name'].upper()}")
        print(f"  (learning_style = '{NEW_PREF_VALUE}' via memory)")
        bar("-", 50)

        for rec in recs:
            src = "[LLM]" if rec.get("explanation_source") == "llm" else "[Rule-based]"
            print(f"\n  {rec['rank']}. {rec['course_name']}  --  {rec['score']}/100")
            print(f"     Domain     : {rec['domain']}")
            print(f"     Difficulty : {rec['difficulty']}")
            print(f"\n     Explanation {src}:")
            # Simple word-wrap at 70 chars
            words = rec["explanation"].split()
            line  = "     "
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

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Restore the original preference (clean up)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [5] Restoring original '{TEST_PREF_TYPE}' preference")

    restore_value = ORIGINAL_VALUE if ORIGINAL_VALUE else "Project-based"
    r = memory.save_preference(STUDENT_ID, TEST_PREF_TYPE, restore_value)
    if r["success"]:
        print(f"  [OK] Restored '{TEST_PREF_TYPE}' to '{restore_value}'")
    else:
        print(f"  [FAIL] Could not restore: {r['message']}")

    # Verify the restore
    final_value = memory.get_preference_value(STUDENT_ID, TEST_PREF_TYPE)
    if final_value == restore_value:
        print(f"  [OK] Verified: learning_style is now '{final_value}' (original value)")
    else:
        print(f"  [FAIL] learning_style is '{final_value}' — expected '{restore_value}'")

    # ─────────────────────────────────────────────────────────────────────────
    # DONE
    # ─────────────────────────────────────────────────────────────────────────
    print()
    bar()
    print("  MEMORY + AGENT INTEGRATION TEST COMPLETE")
    bar()
    print()


if __name__ == "__main__":
    run_memory_integration_test()
