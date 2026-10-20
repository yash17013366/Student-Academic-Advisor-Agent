"""
advisory_coordinator_agent.py
------------------------------
Unit IV - Advisory Coordinator Agent

Responsibility:
    Synthesize the findings from all three specialist agents
    (Academic Performance, Career & Skill-Gap, Workload Feasibility)
    into a single, personalized final academic plan.

    The coordinator does NOT re-run agents. It reads their outputs
    and produces a structured synthesis with clear reasoning.

Input:
    - student_profile      (dict): From AcademicProfileAgent
    - recommendations      (dict): From RecommendationAgent (original top-3)
    - performance_report   (dict): From AcademicPerformanceAgent
    - career_analysis      (dict): From CareerSkillGapAgent
    - workload_report      (dict): From WorkloadFeasibilityAgent
    - reflection_result    (dict): From ReflectionAgent (feedback-adjusted)

Output:
    dict with:
        - final_plan         : list of final recommended courses with reasoning
        - coordinator_summary: plain-English synthesis paragraph
        - specialist_signals : dict of key signals from each specialist
        - reasoning_chain    : ordered list explaining coordinator's logic
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class AdvisoryCoordinatorAgent:
    """
    Unit IV — Advisory Coordinator Agent

    Combines findings from three specialist agents to produce
    the final personalized academic recommendation plan.

    USES ONLY data from the specialist agents' actual outputs.
    Does NOT invent facts, grades, or course details.
    """

    def __init__(self):
        self.agent_name = "Advisory Coordinator Agent"

    def run(
        self,
        student_profile,
        recommendations,
        performance_report,
        career_analysis,
        workload_report,
        reflection_result=None,
    ):
        """
        Synthesizes all specialist outputs into a final academic plan.

        Args:
            student_profile    (dict): From AcademicProfileAgent
            recommendations    (dict): From RecommendationAgent
            performance_report (dict): From AcademicPerformanceAgent
            career_analysis    (dict): From CareerSkillGapAgent
            workload_report    (dict): From WorkloadFeasibilityAgent
            reflection_result  (dict): From ReflectionAgent (optional)

        Returns:
            dict: Coordinator synthesis result
        """
        print(f"\n[CoordinatorAgent] Synthesizing findings for: "
              f"{student_profile.get('name', 'Unknown')}")

        if student_profile.get("error"):
            return {"error": True, "message": "Invalid student profile."}

        student_name = student_profile.get("name", "Student")
        career_goal  = student_profile.get("career_goal", "Not specified")
        semester     = student_profile.get("semester", 5)

        # ── Extract key signals from each specialist ──────────────────────────
        signals = self._extract_signals(
            performance_report, career_analysis, workload_report
        )

        # ── Determine final course list ────────────────────────────────────────
        # Use feedback-adjusted ranking if available and has feedback applied,
        # else use original recommendation ranking
        final_courses = self._determine_final_courses(
            recommendations, reflection_result, workload_report
        )

        # ── Build reasoning chain ──────────────────────────────────────────────
        reasoning_chain = self._build_reasoning_chain(
            student_profile, signals, final_courses, reflection_result
        )

        # ── Build coordinator summary paragraph ────────────────────────────────
        coordinator_summary = self._build_summary(
            student_name, career_goal, semester, signals,
            final_courses, reasoning_chain, reflection_result
        )

        print(f"[CoordinatorAgent] Final plan has {len(final_courses)} course(s).")

        return {
            "error"              : False,
            "student_name"       : student_name,
            "final_plan"         : final_courses,
            "coordinator_summary": coordinator_summary,
            "specialist_signals" : signals,
            "reasoning_chain"    : reasoning_chain,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_signals(self, performance_report, career_analysis, workload_report):
        """
        Extracts the key signals from each specialist agent's output.
        Returns a structured dict of summary signals.
        """
        signals = {}

        # Academic Performance signals
        if performance_report and not performance_report.get("error"):
            signals["performance_tier"]  = performance_report.get("performance_tier", "N/A")
            signals["gpa_estimate"]      = performance_report.get("gpa_estimate", 0.0)
            signals["strengths_count"]   = len(performance_report.get("strengths", []))
            signals["weak_areas_count"]  = len(performance_report.get("weak_areas", []))
            signals["grade_summary"]     = performance_report.get("grade_summary", {})
            signals["academic_notes"]    = performance_report.get("academic_notes", [])
        else:
            signals["performance_tier"] = "Unknown"
            signals["gpa_estimate"]     = 0.0
            signals["academic_notes"]   = []

        # Career & Skill-Gap signals
        if career_analysis and not career_analysis.get("error"):
            signals["career_goal"]        = career_analysis.get("career_goal", "Not specified")
            signals["alignment_score"]    = career_analysis.get("alignment_score", 0)
            signals["skill_gaps_count"]   = len(career_analysis.get("skill_gaps", []))
            signals["skill_gaps"]         = career_analysis.get("skill_gaps", [])
            signals["relevant_courses"]   = career_analysis.get("relevant_courses", [])
            signals["career_notes"]       = career_analysis.get("career_notes", [])
            signals["current_skills"]     = career_analysis.get("current_skills", [])
        else:
            signals["career_goal"]     = "Not specified"
            signals["alignment_score"] = 0
            signals["career_notes"]    = []

        # Workload Feasibility signals
        if workload_report and not workload_report.get("error"):
            signals["feasibility_rating"]    = workload_report.get("feasibility_rating", "N/A")
            signals["load_score"]            = workload_report.get("load_score", 50)
            signals["workload_suggestions"]  = workload_report.get("recommendations", [])
            signals["feasibility_notes"]     = workload_report.get("feasibility_notes", [])
        else:
            signals["feasibility_rating"]   = "Unknown"
            signals["load_score"]           = 50
            signals["workload_suggestions"] = []
            signals["feasibility_notes"]    = []

        return signals

    def _determine_final_courses(self, recommendations, reflection_result, workload_report):
        """
        Determines the final prioritized course list.

        Priority order:
        1. Feedback-adjusted ranking (if feedback was applied)
        2. Original recommendation ranking (fallback)

        Prerequisites are ALWAYS respected (only eligible courses appear here).
        """
        final_courses = []

        # Decide which ranking to use
        if (reflection_result
                and not reflection_result.get("error")
                and reflection_result.get("feedback_applied")):
            source  = "feedback-adjusted"
            ranking = reflection_result.get("adjusted_ranking", [])[:3]
        else:
            source  = "original"
            recs    = recommendations.get("recommendations", [])
            ranking = [
                {
                    "rank"          : r.get("rank", i+1),
                    "course_id"     : r.get("course_id"),
                    "course_name"   : r.get("course_name"),
                    "score"         : r.get("score"),
                    "original_score": r.get("score"),
                    "adjustment"    : 0,
                    "adj_reasons"   : [],
                    "domain"        : r.get("domain", ""),
                    "difficulty"    : r.get("difficulty", ""),
                }
                for i, r in enumerate(recs[:3])
            ]

        # Build workload feasibility lookup
        workload_lookup = {}
        if workload_report and not workload_report.get("error"):
            for pc in workload_report.get("per_course_analysis", []):
                workload_lookup[pc["course_id"]] = pc

        # Build final plan entries
        for i, course in enumerate(ranking):
            cid     = course.get("course_id", "")
            c_notes = workload_lookup.get(cid, {}).get("course_notes", [])

            final_courses.append({
                "rank"          : i + 1,
                "course_id"     : cid,
                "course_name"   : course.get("course_name", ""),
                "score"         : course.get("score", 0),
                "original_score": course.get("original_score", course.get("score", 0)),
                "adjustment"    : course.get("adjustment", 0),
                "adj_reasons"   : course.get("adj_reasons", []),
                "domain"        : course.get("domain", ""),
                "difficulty"    : course.get("difficulty", ""),
                "is_manageable" : workload_lookup.get(cid, {}).get("is_manageable", True),
                "workload_notes": c_notes,
                "ranking_source": source,
            })

        return final_courses

    def _build_reasoning_chain(
        self, student_profile, signals, final_courses, reflection_result
    ):
        """
        Builds a numbered, ordered list explaining the coordinator's logic.
        """
        chain = []
        step  = 1

        # Step 1: Academic performance context
        tier = signals.get("performance_tier", "Good")
        gpa  = signals.get("gpa_estimate", 7.0)
        chain.append(
            f"Step {step}: Academic Performance — Student shows '{tier}' tier "
            f"performance (est. GPA {gpa}/10). "
            + ("Eligible for challenging courses."
               if gpa >= 7.0 else "Recommending moderate difficulty courses.")
        )
        step += 1

        # Step 2: Career alignment
        alignment = signals.get("alignment_score", 0)
        career    = signals.get("career_goal", "Not specified")
        gaps      = signals.get("skill_gaps_count", 0)
        chain.append(
            f"Step {step}: Career Alignment — Career goal '{career}' has "
            f"{alignment}% skill alignment. {gaps} skill gap(s) identified."
        )
        step += 1

        # Step 3: Workload feasibility
        feasibility = signals.get("feasibility_rating", "Moderate")
        chain.append(
            f"Step {step}: Workload Feasibility — Overall workload rated '{feasibility}'. "
            + (", ".join(signals.get("workload_suggestions", [])) or "No concerns.")
        )
        step += 1

        # Step 4: Feedback reflection
        if reflection_result and reflection_result.get("feedback_applied"):
            adj_count     = len(reflection_result.get("adjustments", []))
            changed       = reflection_result.get("ranking_changed", False)
            chain.append(
                f"Step {step}: Feedback Reflection — {adj_count} course(s) had "
                f"score adjusted based on student feedback. "
                f"Ranking {'changed' if changed else 'maintained same order'}."
            )
        else:
            chain.append(
                f"Step {step}: Feedback Reflection — No prior feedback found. "
                "Using original scoring for final recommendations."
            )
        step += 1

        # Step 5: Final synthesis
        top_course = final_courses[0]["course_name"] if final_courses else "None"
        chain.append(
            f"Step {step}: Final Synthesis — Coordinator prioritized '{top_course}' "
            f"as the primary recommendation after integrating all specialist inputs."
        )

        return chain

    def _build_summary(
        self, student_name, career_goal, semester,
        signals, final_courses, reasoning_chain, reflection_result
    ):
        """
        Builds a plain-English summary paragraph of the coordinator's synthesis.
        """
        parts = []

        # Opening
        tier        = signals.get("performance_tier", "Good")
        gpa         = signals.get("gpa_estimate", 7.0)
        parts.append(
            f"{student_name} (Semester {semester}) demonstrates {tier.lower()} "
            f"academic performance with an estimated GPA of {gpa}/10."
        )

        # Career alignment sentence
        alignment = signals.get("alignment_score", 0)
        gaps      = signals.get("skill_gaps_count", 0)
        if career_goal and career_goal != "Not specified":
            parts.append(
                f"Career alignment with '{career_goal}' is at {alignment}%, "
                f"with {gaps} skill gap(s) to address through coursework."
            )

        # Workload sentence
        feasibility = signals.get("feasibility_rating", "Moderate")
        parts.append(
            f"Workload feasibility is rated '{feasibility}', "
            + ("making the recommended courses a manageable academic load."
               if feasibility in ["High", "Moderate"]
               else "so careful course selection is advised.")
        )

        # Feedback sentence
        if reflection_result and reflection_result.get("feedback_applied"):
            parts.append(
                "Student feedback was incorporated through the Reflection Agent, "
                "adjusting course scores to better match stated preferences."
            )

        # Final recommendation sentence
        if final_courses:
            top3_names = [c["course_name"] for c in final_courses[:3]]
            parts.append(
                f"The coordinator's final recommendation prioritizes: "
                f"{', '.join(top3_names)}."
            )

        # Workload suggestions
        suggestions = signals.get("workload_suggestions", [])
        if suggestions:
            parts.append("Advisory note: " + " ".join(suggestions))

        return " ".join(parts)
