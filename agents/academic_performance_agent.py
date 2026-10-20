"""
academic_performance_agent.py
------------------------------
Unit IV - Specialist Agent 1: Academic Performance Agent

Responsibility:
    Analyze a student's grade history from the database to produce
    a structured academic performance report.

Uses ONLY existing database data (completed_subjects + grades).
Does NOT invent data, grades, or subject information.

Output:
    dict with:
        - gpa_estimate     : float (estimated on 10-point scale)
        - grade_summary    : {"A": n, "B": n, "C": n, "D": n, "F": n}
        - strengths        : list of subjects where student scored A/B
        - weak_areas       : list of subjects where student scored C or below
        - performance_tier : "Excellent" / "Good" / "Average" / "Needs Improvement"
        - academic_notes   : list of plain-English observations
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# Grade-point map (10-point scale)
GRADE_POINTS = {
    "A+" : 10.0,
    "A"  :  9.0,
    "A-" :  8.5,
    "B+" :  8.0,
    "B"  :  7.0,
    "B-" :  6.5,
    "C+" :  6.0,
    "C"  :  5.5,
    "C-" :  5.0,
    "D"  :  4.0,
    "F"  :  0.0,
}

# Minimum grade points for "strength" category
STRENGTH_THRESHOLD = 7.0   # B and above
WEAK_THRESHOLD     = 5.5   # C and below


class AcademicPerformanceAgent:
    """
    Specialist Agent (Unit IV) — Academic Performance Analysis

    Analyzes the student's grade history from their profile and returns
    a structured performance report used by the Advisory Coordinator.
    """

    def __init__(self):
        self.agent_name = "Academic Performance Agent"

    def run(self, student_profile):
        """
        Analyzes academic performance based on the student profile.

        Args:
            student_profile (dict): Profile dict from AcademicProfileAgent

        Returns:
            dict: Academic performance analysis
        """
        print(f"\n[AcadPerfAgent] Analyzing performance for: "
              f"{student_profile.get('name', 'Unknown')}")

        if student_profile.get("error"):
            return {"error": True, "message": "Invalid student profile."}

        grades = student_profile.get("grades", {})  # {subject_name: grade_str}

        if not grades:
            return {
                "error"           : False,
                "gpa_estimate"    : 0.0,
                "grade_summary"   : {},
                "strengths"       : [],
                "weak_areas"      : [],
                "performance_tier": "No Data",
                "academic_notes"  : ["No completed subjects found in database."],
            }

        # ── Count grades ───────────────────────────────────────────────────────
        grade_summary = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        strengths  = []
        weak_areas = []
        total_pts  = 0.0
        count      = 0

        for subject, grade in grades.items():
            grade_upper = grade.strip().upper()

            # Normalize to A/B/C/D/F bucket
            if grade_upper.startswith("A"):
                grade_summary["A"] += 1
            elif grade_upper.startswith("B"):
                grade_summary["B"] += 1
            elif grade_upper.startswith("C"):
                grade_summary["C"] += 1
            elif grade_upper.startswith("D"):
                grade_summary["D"] += 1
            else:
                grade_summary["F"] += 1

            # Calculate grade points
            pts = GRADE_POINTS.get(grade_upper, GRADE_POINTS.get(grade_upper[0], 5.0))
            total_pts += pts
            count += 1

            # Classify as strength or weak area
            if pts >= STRENGTH_THRESHOLD:
                strengths.append(subject)
            elif pts <= WEAK_THRESHOLD:
                weak_areas.append(subject)

        # ── GPA estimation ─────────────────────────────────────────────────────
        gpa_estimate = round(total_pts / count, 2) if count > 0 else 0.0

        # ── Performance tier ───────────────────────────────────────────────────
        if gpa_estimate >= 8.5:
            tier = "Excellent"
        elif gpa_estimate >= 7.0:
            tier = "Good"
        elif gpa_estimate >= 5.5:
            tier = "Average"
        else:
            tier = "Needs Improvement"

        # ── Academic observations ──────────────────────────────────────────────
        notes = []
        total_subjects = len(grades)

        notes.append(
            f"Completed {total_subjects} subject(s) with an estimated GPA of "
            f"{gpa_estimate}/10 ({tier} tier)."
        )

        if strengths:
            notes.append(
                f"Strong performance in: {', '.join(strengths[:4])}."
                + (" (and more)" if len(strengths) > 4 else "")
            )
        if weak_areas:
            notes.append(
                f"Lower performance in: {', '.join(weak_areas[:3])}."
                + (" (and more)" if len(weak_areas) > 3 else "")
            )

        a_ratio = grade_summary["A"] / total_subjects if total_subjects > 0 else 0
        if a_ratio >= 0.5:
            notes.append("Majority of subjects completed with grade A — "
                         "demonstrates strong academic capability.")
        elif grade_summary["C"] + grade_summary["D"] + grade_summary["F"] > (total_subjects // 2):
            notes.append("Several subjects completed with C or below — "
                         "advisable to choose courses with moderate difficulty.")

        print(f"[AcadPerfAgent] GPA={gpa_estimate}, Tier={tier}, "
              f"Strengths={len(strengths)}, Weak={len(weak_areas)}")

        return {
            "error"           : False,
            "gpa_estimate"    : gpa_estimate,
            "grade_summary"   : grade_summary,
            "strengths"       : strengths,
            "weak_areas"      : weak_areas,
            "performance_tier": tier,
            "academic_notes"  : notes,
        }
