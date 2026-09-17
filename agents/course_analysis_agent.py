"""
course_analysis_agent.py
------------------------
AGENT 2 - Course Analysis Agent

Responsibility:
    Analyze all available electives against a student's academic profile
    and calculate a suitability score for each course using simple Python logic.

Input:
    student_profile (dict) - The dictionary returned by Agent 1

Output:
    A list of dictionaries, one per elective, containing:
        - course details
        - eligibility (True/False based on prerequisites)
        - suitability score (0-100)
        - list of reasons explaining the score

SCORING BREAKDOWN (Total = 100 points):
    1. Domain match with completed subjects  : 30 points
    2. Interest / domain match               : 25 points
    3. Career goal match                     : 20 points
    4. All prerequisites satisfied           : 15 points
    5. Preference match (difficulty/style)   : 10 points

IMPORTANT:
    - This agent does NOT use any LLM.
    - This agent does NOT call Agent 1 or Agent 3.
    - It only reads electives from the database and scores them using Python logic.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database.database import get_all_electives


class CourseAnalysisAgent:
    """
    Agent 2: Course Analysis Agent

    Takes a student profile (from Agent 1) and:
    1. Loads all electives from the database
    2. Checks prerequisites for each elective
    3. Scores eligible courses using transparent, rule-based logic
    4. Returns the full analysis list (eligible + ineligible)
    """

    def __init__(self):
        self.agent_name = "Course Analysis Agent"

    def run(self, student_profile):
        """
        Main method: Analyzes all electives for a given student profile.

        Args:
            student_profile (dict): Profile dictionary from AcademicProfileAgent

        Returns:
            list of dicts: One analysis result per elective course
        """
        print(f"\n[Agent 2] {self.agent_name} - Analyzing courses...")

        # Safety check: if Agent 1 returned an error, propagate it
        if student_profile.get("error"):
            print("[Agent 2] ERROR: Received invalid student profile. Stopping.")
            return []

        # ── Retrieve all electives from the database ──────────────────────────
        electives = get_all_electives()

        # Extract student data we need for scoring (for easy reference below)
        completed_subjects   = student_profile.get("completed_subjects", [])
        interests            = student_profile.get("interests", [])
        career_goal          = student_profile.get("career_goal", "")
        preferred_domain     = student_profile.get("preferred_domain", "")
        difficulty_preference = student_profile.get("difficulty_preference", "")
        learning_style       = student_profile.get("learning_style", "")

        # This will hold one result dictionary per elective
        analysis_results = []

        # ── Analyze each elective one by one ──────────────────────────────────
        for elective in electives:
            result = self._analyze_single_course(
                elective,
                completed_subjects,
                interests,
                career_goal,
                preferred_domain,
                difficulty_preference,
                learning_style
            )
            analysis_results.append(result)

        eligible_count = sum(1 for r in analysis_results if r["eligible"])
        print(f"[Agent 2] Analysis complete. {eligible_count}/{len(analysis_results)} courses eligible.")
        return analysis_results

    def _analyze_single_course(
        self,
        elective,
        completed_subjects,
        interests,
        career_goal,
        preferred_domain,
        difficulty_preference,
        learning_style
    ):
        """
        Analyzes ONE elective course and returns a scoring result dict.

        Args:
            elective: sqlite3.Row object from the electives table
            completed_subjects (list): Subjects the student has already completed
            interests (list): Student's interests
            career_goal (str): Student's career goal
            preferred_domain (str): Student's preferred domain
            difficulty_preference (str): Student's difficulty preference
            learning_style (str): Student's learning style

        Returns:
            dict: Analysis result for this course
        """
        course_id   = elective["course_id"]
        course_name = elective["course_name"]
        domain      = elective["domain"]
        difficulty  = elective["difficulty"]
        career_paths_str = elective["career_paths"]

        # Prerequisites are stored as a comma-separated string in the DB
        # Split them into a Python list for easy comparison
        # e.g., "Python Programming, Machine Learning" -> ["Python Programming", "Machine Learning"]
        prerequisites = [p.strip() for p in elective["prerequisites"].split(",")]

        # Career paths also stored as comma-separated string
        career_paths = [c.strip() for c in career_paths_str.split(",")]

        # ── PREREQUISITE CHECK ─────────────────────────────────────────────────
        # A student is only ELIGIBLE if they have completed ALL prerequisites.
        # We check which prerequisites are missing.
        missing_prerequisites = []
        satisfied_prerequisites = []

        for prereq in prerequisites:
            if prereq in completed_subjects:
                satisfied_prerequisites.append(prereq)
            else:
                missing_prerequisites.append(prereq)

        # If any prerequisite is missing, the course is INELIGIBLE — score = 0
        if missing_prerequisites:
            return {
                "course_id"   : course_id,
                "course_name" : course_name,
                "domain"      : domain,
                "difficulty"  : difficulty,
                "eligible"    : False,
                "score"       : 0,
                "reasons"     : [
                    f"Missing prerequisite: {prereq}"
                    for prereq in missing_prerequisites
                ]
            }

        # ── SCORING (only runs for eligible courses) ───────────────────────────
        score   = 0
        reasons = []

        # Add reasons for prerequisites that ARE satisfied
        for prereq in satisfied_prerequisites:
            reasons.append(f"Prerequisite '{prereq}' completed")

        # ══════════════════════════════════════════════════════════════════
        # SCORING CRITERION 1: Domain match with completed subjects (30 pts)
        # ──────────────────────────────────────────────────────────────────
        # We award points based on how many prerequisites match (relative score)
        # If the student completed all prerequisites, they get full marks.
        # Logic: (completed prereqs / total prereqs) * 30
        prereq_ratio = len(satisfied_prerequisites) / len(prerequisites)
        domain_score = round(prereq_ratio * 30)
        score += domain_score

        if domain_score == 30:
            reasons.append("Strong academic foundation for this course (all prerequisites met)")
        elif domain_score > 0:
            reasons.append(f"Partial academic match - completed {len(satisfied_prerequisites)}/{len(prerequisites)} prerequisites")

        # ══════════════════════════════════════════════════════════════════
        # SCORING CRITERION 2: Interest / Domain match (25 pts)
        # ──────────────────────────────────────────────────────────────────
        # Award 25 points if the elective's domain matches the student's
        # preferred domain or any of their stated interests.
        interest_score = 0

        # Check if preferred domain matches
        if domain.lower() == preferred_domain.lower():
            interest_score = 25
            reasons.append(f"Domain '{domain}' matches your preferred domain")

        # Also check if any interest keyword appears in the domain name
        elif any(interest.lower() in domain.lower() or domain.lower() in interest.lower()
                 for interest in interests):
            interest_score = 20
            reasons.append(f"Course domain '{domain}' aligns with your stated interests")

        # Partial credit if domain is loosely related (e.g., both are tech fields)
        elif interests:
            interest_score = 5
            reasons.append("Moderate interest alignment")

        score += interest_score

        # ══════════════════════════════════════════════════════════════════
        # SCORING CRITERION 3: Career goal match (20 pts)
        # ──────────────────────────────────────────────────────────────────
        # Award 20 points if the student's career goal appears in
        # the elective's listed career paths.
        career_score = 0

        # Check if the career goal text matches any career path
        # We do a case-insensitive substring check
        career_goal_lower = career_goal.lower()
        for path in career_paths:
            if career_goal_lower in path.lower() or path.lower() in career_goal_lower:
                career_score = 20
                reasons.append(f"Relevant to your career goal: '{career_goal}'")
                break

        # Partial credit if there's a keyword overlap
        if career_score == 0:
            career_keywords = career_goal_lower.split()
            for path in career_paths:
                if any(keyword in path.lower() for keyword in career_keywords if len(keyword) > 3):
                    career_score = 10
                    reasons.append(f"Partially relevant to your career goal")
                    break

        score += career_score

        # ══════════════════════════════════════════════════════════════════
        # SCORING CRITERION 4: Prerequisite satisfaction bonus (15 pts)
        # ──────────────────────────────────────────────────────────────────
        # Since we already checked eligibility above, eligible courses
        # automatically get a bonus for having met all prerequisites.
        # This rewards students who are well-prepared for the course.
        prereq_score = 15  # All eligible courses get this
        score += prereq_score
        # (No reason added here — already covered in prerequisite messages above)

        # ══════════════════════════════════════════════════════════════════
        # SCORING CRITERION 5: Preference match (10 pts)
        # ──────────────────────────────────────────────────────────────────
        # Award up to 10 points for matching difficulty preference and
        # learning style keywords.
        pref_score = 0

        # Check difficulty preference match
        if difficulty_preference.lower() == difficulty.lower():
            pref_score += 7
            reasons.append(f"Difficulty level '{difficulty}' matches your preference")
        else:
            # Adjacent difficulty levels get partial credit
            # e.g., if student prefers "Medium" and course is "Hard" -> 3 pts
            adjacent = {
                "easy"   : ["medium"],
                "medium" : ["easy", "hard"],
                "hard"   : ["medium"]
            }
            if difficulty.lower() in adjacent.get(difficulty_preference.lower(), []):
                pref_score += 3
                reasons.append(f"Difficulty level '{difficulty}' is close to your preference")

        # Learning style bonus — check if course skills mention hands-on keywords
        hands_on_keywords = ["project", "practical", "hands-on", "applied", "workshop"]
        course_skills = elective["skills"].lower()
        if learning_style.lower() in ["practical", "project-based", "hands-on"]:
            if any(keyword in course_skills for keyword in hands_on_keywords):
                pref_score += 3
                reasons.append(f"Course suits your '{learning_style}' learning style")

        score += pref_score

        # ── Final cap: ensure score doesn't exceed 100 ─────────────────────────
        score = min(score, 100)

        return {
            "course_id"   : course_id,
            "course_name" : course_name,
            "domain"      : domain,
            "difficulty"  : difficulty,
            "eligible"    : True,
            "score"       : score,
            "reasons"     : reasons
        }


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Import Agent 1 to get a sample profile
    from agents.academic_profile_agent import AcademicProfileAgent

    profile_agent   = AcademicProfileAgent()
    analysis_agent  = CourseAnalysisAgent()

    profile  = profile_agent.run("S001")
    results  = analysis_agent.run(profile)

    print("\nAnalysis Results:")
    for r in results:
        status = "ELIGIBLE" if r["eligible"] else "INELIGIBLE"
        print(f"  [{status}] {r['course_name']} - Score: {r['score']}/100")
