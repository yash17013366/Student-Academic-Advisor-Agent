"""
workload_feasibility_agent.py
------------------------------
Unit IV - Specialist Agent 3: Workload Feasibility Agent

Responsibility:
    Estimate whether the recommended courses are feasible for the student
    given their current semester, past academic performance, and the
    difficulty levels of eligible courses.

Uses ONLY existing database data (student profile + course analysis).
Does NOT invent workload metrics or academic policies.

Output:
    dict with:
        - feasibility_rating  : "High" / "Moderate" / "Low"
        - load_score          : int (0-100, higher = more manageable)
        - per_course_analysis : list of per-course feasibility notes
        - recommendations     : list of actionable workload suggestions
        - feasibility_notes   : list of plain-English observations
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# Difficulty weights for load calculation
DIFFICULTY_LOAD = {
    "Easy"   : 1,
    "Medium" : 2,
    "Hard"   : 3,
}

# Semester-based capacity: students in higher semesters typically handle more
SEMESTER_CAPACITY = {
    range(1, 3) : 4,   # Sem 1-2: Light capacity
    range(3, 5) : 5,   # Sem 3-4: Moderate
    range(5, 9) : 6,   # Sem 5-8: Full capacity
}


class WorkloadFeasibilityAgent:
    """
    Specialist Agent (Unit IV) — Workload Feasibility Analysis

    Evaluates whether the top recommended courses are manageable
    given the student's profile, past performance, and course difficulty.
    """

    def __init__(self):
        self.agent_name = "Workload Feasibility Agent"

    def run(self, student_profile, analyzed_courses, performance_report=None):
        """
        Main method: evaluates workload feasibility.

        Args:
            student_profile   (dict): Profile from AcademicProfileAgent
            analyzed_courses  (list): Analysis results from CourseAnalysisAgent
            performance_report (dict, optional): From AcademicPerformanceAgent

        Returns:
            dict: Workload feasibility analysis
        """
        print(f"\n[WorkloadAgent] Evaluating workload for: "
              f"{student_profile.get('name', 'Unknown')}")

        if student_profile.get("error"):
            return {"error": True, "message": "Invalid student profile."}

        semester       = student_profile.get("semester", 5)
        diff_pref      = student_profile.get("difficulty_preference", "Medium")
        learning_style = student_profile.get("learning_style", "Not specified")

        # Get eligible courses only (sorted by score descending)
        eligible_courses = [
            c for c in analyzed_courses if c.get("eligible")
        ]
        eligible_courses.sort(key=lambda c: c["score"], reverse=True)
        top3 = eligible_courses[:3]

        # ── Determine semester capacity ────────────────────────────────────────
        capacity = 6  # default
        for sem_range, cap in SEMESTER_CAPACITY.items():
            if semester in sem_range:
                capacity = cap
                break

        # ── Derive performance factor from performance report ─────────────────
        perf_tier = "Good"
        gpa       = 7.0
        if performance_report and not performance_report.get("error"):
            perf_tier = performance_report.get("performance_tier", "Good")
            gpa       = performance_report.get("gpa_estimate", 7.0)

        # GPA-based difficulty tolerance
        if gpa >= 8.0:
            difficulty_tolerance = 3   # can handle Hard
        elif gpa >= 6.5:
            difficulty_tolerance = 2   # handle Medium
        else:
            difficulty_tolerance = 1   # stick to Easy/Medium

        # ── Per-course feasibility analysis ───────────────────────────────────
        per_course = []
        total_load = 0
        challenges = []

        for course in top3:
            diff       = course.get("difficulty", "Medium")
            load_pts   = DIFFICULTY_LOAD.get(diff, 2)
            total_load += load_pts

            # Is difficulty manageable given GPA?
            is_manageable = (load_pts <= difficulty_tolerance + 1)

            # Feedback from preference
            pref_match = diff.lower() == diff_pref.lower()

            # Notes per course
            c_notes = []
            if not is_manageable:
                c_notes.append(
                    f"'{diff}' difficulty may be challenging given current GPA ({gpa}/10)."
                )
                challenges.append(course["course_name"])
            else:
                c_notes.append(
                    f"'{diff}' difficulty is feasible given current academic performance."
                )

            if pref_match:
                c_notes.append(f"Matches difficulty preference '{diff_pref}'.")
            else:
                c_notes.append(
                    f"Note: Difficulty '{diff}' differs from stated preference '{diff_pref}'."
                )

            per_course.append({
                "course_id"    : course["course_id"],
                "course_name"  : course["course_name"],
                "difficulty"   : diff,
                "load_points"  : load_pts,
                "is_manageable": is_manageable,
                "course_notes" : c_notes,
            })

        # ── Overall feasibility rating ─────────────────────────────────────────
        # Score based on:
        #   1. GPA vs difficulty tolerance (main factor)
        #   2. Number of challenging courses
        base_score = 80  # Start optimistic

        if len(top3) == 0:
            base_score = 50

        # Penalize for each Hard course the student's GPA may not support
        for course in top3:
            diff     = course.get("difficulty", "Medium")
            load_pts = DIFFICULTY_LOAD.get(diff, 2)
            if load_pts > difficulty_tolerance + 1:
                base_score -= 20   # Each incompatible Hard course -20

        # Bonus for matching difficulty preference
        matching_pref = sum(
            1 for c in top3
            if c.get("difficulty", "").lower() == diff_pref.lower()
        )
        base_score += matching_pref * 5

        load_score = max(10, min(100, base_score))

        if load_score >= 65:
            feasibility_rating = "High"
        elif load_score >= 45:
            feasibility_rating = "Moderate"
        else:
            feasibility_rating = "Low"

        # ── Observations and recommendations ──────────────────────────────────
        notes = []
        suggestions = []

        notes.append(
            f"Semester {semester} student with '{perf_tier}' academic performance. "
            f"Estimated workload capacity: {capacity} courses."
        )

        if len(top3) == 0:
            notes.append("No eligible courses found for feasibility analysis.")
        else:
            hard_count = sum(1 for c in top3 if c.get("difficulty") == "Hard")
            notes.append(
                f"Top {len(top3)} recommended course(s): "
                f"{hard_count} Hard, {len(top3) - hard_count} Medium/Easy."
            )

        if challenges:
            notes.append(
                f"Potentially challenging course(s): {', '.join(challenges)}."
            )
            suggestions.append(
                "Consider taking at most one 'Hard' difficulty course per semester."
            )
        else:
            notes.append(
                "All recommended courses appear feasible given current performance."
            )

        if learning_style.lower() in ["project-based", "hands-on", "practical"]:
            suggestions.append(
                "Your hands-on learning style suits project-based courses — "
                "look for courses with applied skills."
            )

        if gpa < 6.5:
            suggestions.append(
                "Focus on building prerequisite strength before taking Hard difficulty courses."
            )

        print(f"[WorkloadAgent] Feasibility={feasibility_rating}, "
              f"LoadScore={load_score}, TotalLoad={total_load}")

        return {
            "error"              : False,
            "feasibility_rating" : feasibility_rating,
            "load_score"         : load_score,
            "total_load"         : total_load,
            "semester_capacity"  : capacity,
            "per_course_analysis": per_course,
            "recommendations"    : suggestions,
            "feasibility_notes"  : notes,
        }
