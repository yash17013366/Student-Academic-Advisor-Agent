"""
test_agents.py
--------------
Integration test for the three agents in Phase 2A.

This script manually connects the three agents in sequence:
    Agent 1 -> Agent 2 -> Agent 3

It tests the full pipeline for two students:
    - S001 (Aanya Sharma) - AI student, primary test
    - S005 (Sneha Patil)  - Cyber Security student, secondary test

In Phase 3, LangGraph will replace this manual chaining.

Usage:
    python tests/test_agents.py
"""

import sys
import os

# Add project root so we can import from agents/ and database/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import all three agents
from agents.academic_profile_agent  import AcademicProfileAgent
from agents.course_analysis_agent   import CourseAnalysisAgent
from agents.recommendation_agent    import RecommendationAgent


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

def line(char="=", width=54):
    """Prints a full separator line."""
    print(char * width)

def section(title):
    """Prints a section header."""
    print()
    line()
    print(f"  {title}")
    line()


# ─────────────────────────────────────────────
# MAIN TEST FUNCTION
# ─────────────────────────────────────────────

def run_agent_test(student_id):
    """
    Runs the full 3-agent pipeline for a given student.

    Flow:
        1. AcademicProfileAgent.run(student_id)       -> profile
        2. CourseAnalysisAgent.run(profile)            -> analysis
        3. RecommendationAgent.run(profile, analysis)  -> recommendations

    Args:
        student_id (str): e.g., "S001"
    """

    line("=")
    print(f"  STUDENT ACADEMIC ADVISOR - AGENT PIPELINE TEST")
    print(f"  Testing for Student ID: {student_id}")
    line("=")

    # ─────────────────────────────────────────
    # AGENT 1: Academic Profile Agent
    # ─────────────────────────────────────────
    section("AGENT 1 - Academic Profile Agent")

    profile_agent = AcademicProfileAgent()
    profile = profile_agent.run(student_id)

    # Check if profile was retrieved successfully
    if profile.get("error"):
        print(f"\n  [ERROR] {profile['message']}")
        print("  Cannot proceed. Please check the student ID.")
        return

    # Print the student profile
    print(f"\n  Student     : {profile['name']}")
    print(f"  Program     : {profile['program']}")
    print(f"  Semester    : {profile['semester']}")
    print(f"\n  Completed Subjects ({len(profile['completed_subjects'])} total):")
    for subject in profile["completed_subjects"]:
        grade = profile["grades"].get(subject, "?")
        print(f"    - {subject}  (Grade: {grade})")
    print(f"\n  Interests          : {', '.join(profile['interests']) if profile['interests'] else 'None'}")
    print(f"  Career Goal        : {profile['career_goal']}")
    print(f"  Learning Style     : {profile['learning_style']}")
    print(f"  Preferred Domain   : {profile['preferred_domain']}")
    print(f"  Difficulty Pref.   : {profile['difficulty_preference']}")

    # ─────────────────────────────────────────
    # AGENT 2: Course Analysis Agent
    # ─────────────────────────────────────────
    section("AGENT 2 - Course Analysis Agent")
    print("  Analyzing available electives...\n")

    analysis_agent = CourseAnalysisAgent()
    analysis = analysis_agent.run(profile)

    if not analysis:
        print("  [ERROR] No analysis results returned.")
        return

    # Separate eligible and ineligible courses
    eligible   = [c for c in analysis if c["eligible"]]
    ineligible = [c for c in analysis if not c["eligible"]]

    # Sort eligible by score descending
    eligible.sort(key=lambda c: c["score"], reverse=True)

    # Print eligible courses
    print(f"  Eligible Courses ({len(eligible)}):")
    for i, course in enumerate(eligible, 1):
        print(f"    {i}. {course['course_name']:<30} Score: {course['score']}/100")

    # Print ineligible courses
    print(f"\n  Ineligible Courses ({len(ineligible)}) - Missing prerequisites:")
    if ineligible:
        for course in ineligible:
            missing = [r for r in course["reasons"] if "missing" in r.lower()]
            missing_str = ", ".join(missing) if missing else "Prerequisites not met"
            print(f"    - {course['course_name']:<30} [{missing_str}]")
    else:
        print("    None - student is eligible for all courses!")

    # Print detailed scoring for eligible courses
    print(f"\n  --- Detailed Scoring ---")
    for course in eligible:
        print(f"\n  [{course['course_id']}] {course['course_name']} - {course['score']}/100")
        for reason in course["reasons"]:
            print(f"        + {reason}")

    # ─────────────────────────────────────────
    # AGENT 3: Recommendation Agent
    # ─────────────────────────────────────────
    section("AGENT 3 - Recommendation Agent")
    print("  Generating Top 3 recommendations...\n")

    rec_agent = RecommendationAgent()
    result = rec_agent.run(profile, analysis)

    # Handle no eligible courses
    if result.get("no_results"):
        print(f"  [INFO] {result['message']}")
        line("=")
        return

    # Print top recommendations
    recs = result["recommendations"]
    print(f"  TOP {len(recs)} RECOMMENDED ELECTIVES FOR {profile['name'].upper()}\n")
    line("-", 54)

    for rec in recs:
        print(f"\n  RANK {rec['rank']}: {rec['course_name']}")
        print(f"  Domain     : {rec['domain']}")
        print(f"  Difficulty : {rec['difficulty']}")
        print(f"  Score      : {rec['score']}/100")
        print(f"\n  Why recommended:")
        print(f"  {rec['explanation']}")
        print(f"\n  Detailed reasons:")
        for reason in rec["reasons"]:
            print(f"    + {reason}")
        line("-", 54)

    # ─────────────────────────────────────────
    # DONE
    # ─────────────────────────────────────────
    line("=")
    print(f"  AGENT PIPELINE TEST COMPLETE FOR: {profile['name']}")
    line("=")
    print()


# ─────────────────────────────────────────────
# ENTRY POINT - Tests multiple students
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # ── TEST CASE 1: S001 - Aanya Sharma (AI student) ─────────────────────────
    run_agent_test("S001")

    print("\n\n")

    # ── TEST CASE 2: S005 - Sneha Patil (Cyber Security student) ──────────────
    run_agent_test("S005")

    print("\n\n")

    # ── TEST CASE 3: Invalid student ID ───────────────────────────────────────
    print("Testing with an invalid student ID (S999):")
    run_agent_test("S999")
