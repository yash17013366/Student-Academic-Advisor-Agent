"""
reflection_agent.py
-------------------
Unit III - Reflection Agent (Act -> Observe -> Reflect -> Adjust)

Responsibility:
    Interpret persisted student feedback and produce adjusted course scores.
    Shows clear before-and-after rankings with explanations.

IMPORTANT CONSTRAINTS:
    - NEVER overrides prerequisite or academic eligibility decisions.
    - Only adjusts suitability scores of ELIGIBLE courses.
    - INELIGIBLE courses remain ineligible regardless of feedback.
    - Adjustment logic is fully deterministic (no LLM needed).

Input:
    - student_id       (str):  e.g., "S001"
    - analyzed_courses (list): Full list from CourseAnalysisAgent (Agent 2)

Output:
    dict containing:
        - original_ranking  : list of eligible courses before adjustment
        - adjusted_ranking  : list of eligible courses after feedback adjustments
        - adjustments       : per-course detail of what changed and why
        - feedback_applied  : True/False
        - summary           : human-readable explanation of what changed
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database.feedback_db import (
    get_feedback_for_student,
    get_cumulative_adjustment,
    FEEDBACK_TYPES,
    FEEDBACK_SCORE_ADJUSTMENTS,
)


class ReflectionAgent:
    """
    Unit III Agent — Reflection Agent

    Implements the feedback reflection loop:
        ACT    -> Student gets recommendations (from Agent 3)
        OBSERVE -> Student submits feedback (via UI / feedback_db)
        REFLECT -> This agent interprets all feedback
        ADJUST  -> Recalculates scores and re-ranks eligible courses
    """

    def __init__(self):
        self.agent_name = "Reflection Agent"

    def run(self, student_id, analyzed_courses):
        """
        Main method: reflects on feedback and produces adjusted rankings.

        Args:
            student_id       (str):  Student whose feedback to use
            analyzed_courses (list): Raw analysis from CourseAnalysisAgent

        Returns:
            dict: Reflection result with before/after rankings and explanations
        """
        print(f"\n[ReflectionAgent] Processing feedback for student: {student_id}")

        # Step 1: Separate eligible from ineligible (eligibility NEVER changes)
        eligible_courses   = [c for c in analyzed_courses if c.get("eligible")]
        ineligible_courses = [c for c in analyzed_courses if not c.get("eligible")]

        if not eligible_courses:
            return {
                "student_id"      : student_id,
                "feedback_applied": False,
                "original_ranking": [],
                "adjusted_ranking": [],
                "adjustments"     : [],
                "summary"         : "No eligible courses to adjust.",
                "ineligible_count": len(ineligible_courses),
            }

        # Step 2: Load all feedback for this student from DB
        all_feedback = get_feedback_for_student(student_id)
        feedback_by_course = {}
        for fb in all_feedback:
            cid = fb["course_id"]
            if cid not in feedback_by_course:
                feedback_by_course[cid] = []
            feedback_by_course[cid].append(fb)

        # Step 3: Build "before" ranking (original scores, sorted)
        original_ranking = sorted(
            eligible_courses,
            key=lambda c: c["score"],
            reverse=True
        )

        # Step 4: Apply feedback adjustments to eligible courses only
        adjustments = []
        adjusted_courses = []

        for course in eligible_courses:
            course_id    = course["course_id"]
            original_score = course["score"]

            # Get total adjustment from all persisted feedback for this course
            total_adj  = get_cumulative_adjustment(student_id, course_id)
            course_feedbacks = feedback_by_course.get(course_id, [])

            # Calculate adjusted score, clamp to [0, 100]
            adjusted_score = max(0, min(100, original_score + total_adj))

            # Build per-course adjustment detail
            adj_reasons = []
            for fb in course_feedbacks:
                fb_type   = fb["feedback_type"]
                fb_label  = FEEDBACK_TYPES.get(fb_type, fb_type)
                adj_val   = FEEDBACK_SCORE_ADJUSTMENTS.get(fb_type, 0)
                adj_str   = f"{adj_val:+d}"
                adj_reasons.append(
                    f"'{fb_label}' feedback → {adj_str} pts"
                )

            adjusted_course = dict(course)  # shallow copy
            adjusted_course["score"]          = adjusted_score
            adjusted_course["original_score"] = original_score
            adjusted_course["adjustment"]     = total_adj
            adjusted_course["adj_reasons"]    = adj_reasons
            adjusted_course["feedback_count"] = len(course_feedbacks)

            adjusted_courses.append(adjusted_course)

            if total_adj != 0 or course_feedbacks:
                adjustments.append({
                    "course_id"     : course_id,
                    "course_name"   : course["course_name"],
                    "original_score": original_score,
                    "adjusted_score": adjusted_score,
                    "total_adj"     : total_adj,
                    "adj_reasons"   : adj_reasons,
                })

        # Step 5: Sort adjusted courses by new score (re-rank)
        adjusted_ranking = sorted(
            adjusted_courses,
            key=lambda c: c["score"],
            reverse=True
        )

        # Step 6: Check whether ranking order changed
        orig_order     = [c["course_id"] for c in original_ranking]
        adjusted_order = [c["course_id"] for c in adjusted_ranking]
        ranking_changed = (orig_order != adjusted_order)
        feedback_applied = len(adjustments) > 0

        # Step 7: Build human-readable summary
        summary = self._build_summary(
            student_id, adjustments, ranking_changed,
            original_ranking, adjusted_ranking, feedback_applied
        )

        print(f"[ReflectionAgent] Feedback applied: {feedback_applied}, "
              f"Ranking changed: {ranking_changed}")

        return {
            "student_id"      : student_id,
            "feedback_applied": feedback_applied,
            "ranking_changed" : ranking_changed,
            "original_ranking": [
                {
                    "rank"       : i + 1,
                    "course_id"  : c["course_id"],
                    "course_name": c["course_name"],
                    "score"      : c["score"],
                    "domain"     : c.get("domain", ""),
                    "difficulty" : c.get("difficulty", ""),
                }
                for i, c in enumerate(original_ranking)
            ],
            "adjusted_ranking": [
                {
                    "rank"          : i + 1,
                    "course_id"     : c["course_id"],
                    "course_name"   : c["course_name"],
                    "score"         : c["score"],
                    "original_score": c.get("original_score", c["score"]),
                    "adjustment"    : c.get("adjustment", 0),
                    "adj_reasons"   : c.get("adj_reasons", []),
                    "domain"        : c.get("domain", ""),
                    "difficulty"    : c.get("difficulty", ""),
                    "feedback_count": c.get("feedback_count", 0),
                }
                for i, c in enumerate(adjusted_ranking)
            ],
            "adjustments"     : adjustments,
            "summary"         : summary,
            "ineligible_count": len(ineligible_courses),
        }

    def _build_summary(
        self, student_id, adjustments, ranking_changed,
        original_ranking, adjusted_ranking, feedback_applied
    ):
        """
        Produces a plain-English explanation of what the reflection loop did.
        """
        if not feedback_applied:
            return (
                "No feedback has been submitted yet. "
                "Submit feedback on recommended courses to activate the "
                "Act -> Observe -> Reflect -> Adjust loop."
            )

        lines = [
            f"Reflection loop processed {len(adjustments)} course adjustment(s):"
        ]
        for adj in adjustments:
            delta     = adj["total_adj"]
            delta_str = f"{delta:+d}"
            lines.append(
                f"  - {adj['course_name']}: "
                f"{adj['original_score']} -> {adj['adjusted_score']} "
                f"({delta_str} pts due to {', '.join(adj['adj_reasons'])})"
            )

        if ranking_changed:
            new_top = adjusted_ranking[0]["course_name"] if adjusted_ranking else "N/A"
            lines.append(
                f"\nRanking ORDER changed after adjustment. "
                f"New top recommendation: '{new_top}'."
            )
        else:
            lines.append(
                "\nScore values changed but ranking ORDER remains the same."
            )

        lines.append(
            "\nNote: Prerequisite eligibility constraints were NOT affected "
            "by any feedback adjustments."
        )

        return "\n".join(lines)


# =============================================================================
# QUICK SELF-TEST
# =============================================================================

if __name__ == "__main__":
    # Must have already run a recommendation for S001 and submitted feedback
    from agents.academic_profile_agent import AcademicProfileAgent
    from agents.course_analysis_agent  import CourseAnalysisAgent

    profile  = AcademicProfileAgent().run("S001")
    analysis = CourseAnalysisAgent().run(profile)
    result   = ReflectionAgent().run("S001", analysis)

    print("\n=== Before Feedback ===")
    for c in result["original_ranking"][:5]:
        print(f"  Rank {c['rank']}: {c['course_name']} ({c['score']}/100)")

    print("\n=== After Reflection ===")
    for c in result["adjusted_ranking"][:5]:
        adj = c.get("adjustment", 0)
        print(f"  Rank {c['rank']}: {c['course_name']} "
              f"({c['original_score']} -> {c['score']}/100, adj={adj:+d})")

    print(f"\nSummary:\n{result['summary']}")
