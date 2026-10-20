"""
career_skill_gap_agent.py
--------------------------
Unit IV - Specialist Agent 2: Career & Skill-Gap Analysis Agent

Responsibility:
    Analyze the gap between the student's current skills (from completed
    subjects and the course skills in the DB) and the skills required
    for their stated career goal.

Uses ONLY existing database data (electives + student profile).
Does NOT invent skills, jobs, or career paths.

Output:
    dict with:
        - career_goal         : str
        - current_skills      : list inferred from completed subjects / eligible courses
        - relevant_courses    : list of courses aligned with career_goal
        - skill_gaps          : list of skills not yet acquired
        - alignment_score     : int (0-100) career alignment percentage
        - career_notes        : list of observations
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database.database import get_all_electives


# Subject -> skill mapping inferred from course catalog
# Only uses actual skills listed in the electives table
SUBJECT_SKILL_MAP = {
    "Python Programming"           : ["Python", "Scripting", "OOP"],
    "Machine Learning"             : ["Machine Learning", "Scikit-learn", "Model Training"],
    "Data Structures"              : ["Algorithms", "Data Structures", "Problem Solving"],
    "Statistics"                   : ["Statistical Analysis", "Probability", "Data Preprocessing"],
    "Mathematics"                  : ["Linear Algebra", "Calculus", "Optimization"],
    "Database Management Systems"  : ["SQL/NoSQL", "Database Design", "DBMS"],
    "Computer Networks"            : ["Networking", "Network Security", "Protocols"],
    "Operating Systems"            : ["OS Concepts", "Process Management", "Linux"],
    "Object Oriented Programming"  : ["OOP", "Design Patterns", "Java/C++"],
    "Web Development"              : ["HTML/CSS", "JavaScript", "Frontend Development"],
}


class CareerSkillGapAgent:
    """
    Specialist Agent (Unit IV) — Career & Skill-Gap Analysis

    Looks at what the student wants to become (career_goal) and what
    skills the recommended courses offer, then identifies gaps.
    """

    def __init__(self):
        self.agent_name = "Career & Skill-Gap Analysis Agent"

    def run(self, student_profile, analyzed_courses):
        """
        Main method: performs career and skill-gap analysis.

        Args:
            student_profile  (dict): Profile from AcademicProfileAgent
            analyzed_courses (list): Analysis results from CourseAnalysisAgent

        Returns:
            dict: Career and skill-gap analysis result
        """
        print(f"\n[CareerSkillGapAgent] Analyzing career alignment for: "
              f"{student_profile.get('name', 'Unknown')}")

        if student_profile.get("error"):
            return {"error": True, "message": "Invalid student profile."}

        career_goal        = student_profile.get("career_goal", "Not specified")
        completed_subjects = student_profile.get("completed_subjects", [])
        interests          = student_profile.get("interests", [])

        # ── Step 1: Collect current skills from completed subjects ─────────────
        current_skills_set = set()
        for subj in completed_subjects:
            for skill in SUBJECT_SKILL_MAP.get(subj, []):
                current_skills_set.add(skill)

        current_skills = sorted(current_skills_set)

        # ── Step 2: Load all electives for skill data ─────────────────────────
        try:
            all_electives = get_all_electives()
            elective_data = {
                e["course_id"]: {
                    "course_name" : e["course_name"],
                    "skills"      : [s.strip() for s in e["skills"].split(",") if s.strip()],
                    "career_paths": [c.strip() for c in e["career_paths"].split(",") if c.strip()],
                    "domain"      : e["domain"],
                    "difficulty"  : e["difficulty"],
                }
                for e in all_electives
            }
        except Exception:
            elective_data = {}

        # ── Step 3: Find courses relevant to career goal ──────────────────────
        career_goal_lower = career_goal.lower()
        relevant_courses  = []

        # Domain keywords for broader matching (career -> domain)
        CAREER_DOMAIN_MAP = {
            "ai"         : ["artificial intelligence", "data science"],
            "engineer"   : ["artificial intelligence", "data science", "software development",
                            "cloud computing", "iot", "blockchain"],
            "data"       : ["data science", "artificial intelligence"],
            "security"   : ["cyber security"],
            "cloud"      : ["cloud computing"],
            "web"        : ["software development"],
            "blockchain" : ["blockchain"],
            "iot"        : ["iot"],
            "nlp"        : ["artificial intelligence"],
            "vision"     : ["artificial intelligence"],
            "developer"  : ["software development", "artificial intelligence"],
        }

        def is_career_relevant(career_lower, edata):
            """Check if this course/elective is relevant to the given career goal."""
            # Direct career path text match
            career_paths_lower = [cp.lower() for cp in edata["career_paths"]]
            if any(career_lower in cp or cp in career_lower for cp in career_paths_lower):
                return True
            # Keyword overlap with career paths
            kws = [w for w in career_lower.split() if len(w) > 3]
            if any(kw in " ".join(career_paths_lower) for kw in kws):
                return True
            # Domain-level match using career keyword -> domain mapping
            domain_lower = edata["domain"].lower()
            for career_kw, domains in CAREER_DOMAIN_MAP.items():
                if career_kw in career_lower:
                    if any(d in domain_lower for d in domains):
                        return True
            # Interest-based domain match
            for interest in interests:
                if interest.lower() in domain_lower or domain_lower in interest.lower():
                    return True
            return False

        for course_id, edata in elective_data.items():
            if is_career_relevant(career_goal_lower, edata):
                relevant_courses.append({
                    "course_id"  : course_id,
                    "course_name": edata["course_name"],
                    "skills"     : edata["skills"],
                    "domain"     : edata["domain"],
                })

        # ── Step 4: Identify skill gaps ───────────────────────────────────────
        # Skills needed by relevant courses that the student doesn't have yet
        # Limit to skills of the top 3 most relevant courses to avoid inflating gaps
        desired_skills_set = set()
        for rc in relevant_courses[:3]:
            for skill in rc["skills"]:
                desired_skills_set.add(skill)

        skill_gaps = sorted(desired_skills_set - current_skills_set)

        # ── Step 5: Calculate alignment score (0-100) ─────────────────────────
        # Based on: completed subjects + interests matching relevant domains
        if desired_skills_set:
            acquired = desired_skills_set.intersection(current_skills_set)
            raw_score = round(len(acquired) / len(desired_skills_set) * 100)
        else:
            raw_score = 0

        # Bonus: interest alignment (up to +30 points)
        interest_bonus = 0
        if relevant_courses:
            relevant_domains = {rc["domain"].lower() for rc in relevant_courses}
            for interest in interests:
                if any(interest.lower() in d or d in interest.lower() for d in relevant_domains):
                    interest_bonus = min(30, interest_bonus + 15)
        # Career-goal specified bonus
        career_bonus = 20 if career_goal != "Not specified" else 0

        alignment_score = min(100, raw_score + interest_bonus + career_bonus)

        # ── Step 6: Build observations ────────────────────────────────────────
        notes = []
        if career_goal == "Not specified":
            notes.append("No career goal specified in the student profile.")
        else:
            notes.append(
                f"Career goal '{career_goal}' identified. "
                f"Found {len(relevant_courses)} relevant elective(s) in the course catalog."
            )

        if current_skills:
            notes.append(
                f"Student has acquired skills in: {', '.join(current_skills[:5])}"
                + (" (and more)" if len(current_skills) > 5 else "") + "."
            )

        if skill_gaps:
            notes.append(
                f"Skill gaps for '{career_goal}': {', '.join(skill_gaps[:5])}"
                + (" (and more)" if len(skill_gaps) > 5 else "") + "."
            )
        else:
            notes.append(
                "No significant skill gaps identified for the stated career goal "
                "based on available course catalog."
            )

        if interests:
            notes.append(
                f"Student interests ({', '.join(interests)}) "
                f"inform course selection alongside career goal."
            )

        print(f"[CareerSkillGapAgent] Alignment={alignment_score}%, "
              f"Gaps={len(skill_gaps)}, Relevant={len(relevant_courses)}")

        return {
            "error"          : False,
            "career_goal"    : career_goal,
            "current_skills" : current_skills,
            "relevant_courses": relevant_courses,
            "skill_gaps"     : skill_gaps,
            "alignment_score": alignment_score,
            "career_notes"   : notes,
        }
