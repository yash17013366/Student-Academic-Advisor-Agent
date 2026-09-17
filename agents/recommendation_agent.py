"""
recommendation_agent.py
-----------------------
AGENT 3 - Recommendation Agent (Phase 2C — Ollama Enhanced)

Responsibility:
    Generate the final Top 3 elective recommendations from the
    course analysis results produced by Agent 2, then use Ollama
    to generate a personalized natural-language explanation for each.

Input:
    - student_profile (dict)    : Profile from Agent 1
    - analyzed_courses (list)   : Analysis results from Agent 2

Output:
    A recommendation dictionary containing:
        - student_id and student name
        - Top 3 ranked recommendations (or fewer if less than 3 eligible)
        - Each recommendation includes rank, course info, score, and explanation
        - A clear message if no eligible courses were found

ARCHITECTURE (Phase 2C):

    Agent 2 scores + ranks courses    <-- deterministic Python, UNCHANGED
          |
          v
    Agent 3 filters & selects Top 3   <-- deterministic Python, UNCHANGED
          |
          v
    Ollama generates explanation       <-- NEW: LLM layer, explanation only
          |
          v
    Final output with LLM explanation

IMPORTANT:
    - Ollama does NOT change scores, rankings, or eligibility.
    - If Ollama is unavailable, the rule-based explanation is used as fallback.
    - The system NEVER crashes due to an Ollama failure.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import the Ollama client — handles all LLM calls and error handling
from llm.ollama_client import generate_explanation as ollama_generate


class RecommendationAgent:
    """
    Agent 3: Recommendation Agent

    Takes:
        - Student profile (from Agent 1)
        - Analyzed course list (from Agent 2)

    Does:
        1. Filters out ineligible courses            [Python — deterministic]
        2. Sorts eligible courses by score           [Python — deterministic]
        3. Picks the Top 3                           [Python — deterministic]
        4. Builds a structured prompt for Ollama     [Python — new in Phase 2C]
        5. Calls Ollama for natural-language explanation [Ollama — Phase 2C]
        6. Falls back to rule-based explanation if Ollama fails [Python fallback]
        7. Returns a structured recommendation dictionary
    """

    def __init__(self):
        self.agent_name = "Recommendation Agent"

    def run(self, student_profile, analyzed_courses):
        """
        Main method: Generates Top 3 elective recommendations.

        Args:
            student_profile (dict): Profile from AcademicProfileAgent
            analyzed_courses (list): Results from CourseAnalysisAgent

        Returns:
            dict: Final recommendation output
        """
        print(f"\n[Agent 3] {self.agent_name} - Generating recommendations...")

        # Safety check: invalid profile
        if student_profile.get("error"):
            return {
                "error"  : True,
                "message": student_profile["message"]
            }

        student_id   = student_profile["student_id"]
        student_name = student_profile["name"]

        # ══════════════════════════════════════════════════════════════════════
        # STEP 1: Filter — keep only eligible courses
        # This logic is DETERMINISTIC PYTHON. Ollama has no role here.
        # ══════════════════════════════════════════════════════════════════════
        eligible_courses = [
            course for course in analyzed_courses
            if course["eligible"] is True
        ]

        # ══════════════════════════════════════════════════════════════════════
        # STEP 2: Sort eligible courses by score (highest first)
        # Again, this is pure Python sorting. Ollama does NOT rank courses.
        # ══════════════════════════════════════════════════════════════════════
        eligible_courses.sort(key=lambda course: course["score"], reverse=True)

        # ── Handle case where NO eligible courses exist ────────────────────────
        if not eligible_courses:
            print(f"[Agent 3] No eligible courses found for {student_name}.")
            return {
                "student_id"      : student_id,
                "student_name"    : student_name,
                "error"           : False,
                "no_results"      : True,
                "message"         : (
                    f"No eligible electives found for {student_name}. "
                    "Consider completing more prerequisite subjects."
                ),
                "recommendations" : []
            }

        # ══════════════════════════════════════════════════════════════════════
        # STEP 3: Select Top 3 (or fewer if less than 3 eligible)
        # Python selects. Ollama does NOT select.
        # ══════════════════════════════════════════════════════════════════════
        top_courses = eligible_courses[:3]

        print(f"[Agent 3] Top {len(top_courses)} course(s) selected by scoring system.")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 4 + 5: Build prompt and call Ollama for ALL Top 3 together
        # One single Ollama call for all 3 courses — more efficient and coherent
        # ══════════════════════════════════════════════════════════════════════
        print(f"[Agent 3] Requesting explanations from Ollama ({', '.join(c['course_name'] for c in top_courses)})...")

        ollama_result = self._get_ollama_explanations(student_profile, top_courses)

        # ollama_result is a dict: { "EL101": "explanation text", ... }
        # or None if Ollama failed (fallback will be used instead)
        llm_used = ollama_result is not None

        if llm_used:
            print(f"[Agent 3] Ollama explanations received successfully.")
        else:
            print(f"[Agent 3] Ollama unavailable — using rule-based fallback explanations.")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 6: Build final recommendation list
        # ══════════════════════════════════════════════════════════════════════
        recommendations = []

        for rank, course in enumerate(top_courses, start=1):
            course_id = course["course_id"]

            # Use Ollama explanation if available, else fallback to Python rules
            if llm_used and ollama_result.get(course_id):
                explanation      = ollama_result[course_id]
                explanation_source = "llm"
            else:
                explanation      = self._rule_based_explanation(course, student_profile, rank)
                explanation_source = "rule-based"

            recommendations.append({
                "rank"               : rank,
                "course_id"          : course_id,
                "course_name"        : course["course_name"],
                "domain"             : course["domain"],
                "difficulty"         : course["difficulty"],
                "score"              : course["score"],      # Python score — NOT changed by Ollama
                "explanation"        : explanation,
                "explanation_source" : explanation_source,   # "llm" or "rule-based"
                "reasons"            : course["reasons"]     # Scoring reasons from Agent 2
            })

        print(f"[Agent 3] Recommendations ready for {student_name}.")

        return {
            "student_id"      : student_id,
            "student_name"    : student_name,
            "error"           : False,
            "no_results"      : False,
            "llm_used"        : llm_used,
            "recommendations" : recommendations
        }

    # ══════════════════════════════════════════════════════════════════════════
    # PRIVATE HELPER: Build prompt and call Ollama
    # ══════════════════════════════════════════════════════════════════════════

    def _get_ollama_explanations(self, profile, top_courses):
        """
        Builds a structured prompt containing student and course data,
        sends it to Ollama, and parses the response into per-course explanations.

        The prompt explicitly instructs Ollama:
            - Only use the information provided
            - Do not invent prerequisites, courses, or student information
            - Do not change the ranking or scores
            - Keep explanations concise (2-4 sentences each)

        Args:
            profile (dict): Student profile from Agent 1
            top_courses (list): Top 3 course dicts from Agent 2 scoring

        Returns:
            dict: { course_id: explanation_text, ... }
            or None if Ollama failed
        """

        # ── Build student context section of the prompt ──────────────────────
        subjects_str  = ", ".join(profile["completed_subjects"])
        interests_str = ", ".join(profile["interests"]) if profile["interests"] else "Not specified"
        grades_str    = ", ".join(
            f"{subj}: {grade}"
            for subj, grade in profile["grades"].items()
        )

        # ── Build course sections ─────────────────────────────────────────────
        courses_section = ""
        for i, course in enumerate(top_courses, start=1):
            reasons_str = "\n".join(f"        - {r}" for r in course["reasons"])
            courses_section += f"""
    Course {i}: {course['course_name']} (ID: {course['course_id']})
        Domain         : {course['domain']}
        Difficulty     : {course['difficulty']}
        Suitability    : {course['score']}/100 (calculated by the scoring system — do not change)
        Scoring Reasons:
{reasons_str}
"""

        # ── Assemble the full prompt ──────────────────────────────────────────
        prompt = f"""You are a university academic advisor helping a student choose elective courses.

STUDENT INFORMATION:
    Name              : {profile['name']}
    Program           : {profile['program']}
    Semester          : {profile['semester']}
    Completed Subjects: {subjects_str}
    Grades            : {grades_str}
    Interests         : {interests_str}
    Career Goal       : {profile['career_goal']}
    Learning Style    : {profile['learning_style']}
    Preferred Domain  : {profile['preferred_domain']}
    Difficulty Pref.  : {profile['difficulty_preference']}

TOP RECOMMENDED ELECTIVES (already ranked and scored by the system):
{courses_section}

TASK:
Write a short, personalized explanation (2-4 sentences) for why each course is recommended for this student.

STRICT RULES — YOU MUST FOLLOW THESE:
    1. Use ONLY the information provided above. Do not invent any facts.
    2. Do NOT mention specific grade percentages or fabricate outcomes.
    3. Do NOT change, re-rank, or re-score the courses.
    4. Do NOT invent prerequisites, career statistics, or course features not listed above.
    5. Keep each explanation concise — 2 to 4 sentences maximum.
    6. Focus on: academic fit, interest alignment, career relevance.

OUTPUT FORMAT — respond ONLY in this exact format, nothing else:

COURSE_1_EXPLANATION:
[Your explanation for Course 1 here]

COURSE_2_EXPLANATION:
[Your explanation for Course 2 here]

COURSE_3_EXPLANATION:
[Your explanation for Course 3 here]
"""

        # ── Call Ollama through our client ────────────────────────────────────
        result = ollama_generate(prompt)

        # If Ollama failed, return None to trigger the fallback
        if not result["success"]:
            return None

        # ── Parse the response into per-course explanations ───────────────────
        return self._parse_ollama_response(result["text"], top_courses)

    def _parse_ollama_response(self, response_text, top_courses):
        """
        Parses Ollama's structured response into a course_id -> explanation dict.

        We look for the COURSE_X_EXPLANATION: markers we asked Ollama to use.
        If parsing fails for any course, we return None for that course and
        the fallback explanation will be used.

        Args:
            response_text (str): Raw text from Ollama
            top_courses (list): The list of Top 3 courses (in order)

        Returns:
            dict: { course_id: explanation_text, ... }
        """
        explanations = {}
        markers = ["COURSE_1_EXPLANATION:", "COURSE_2_EXPLANATION:", "COURSE_3_EXPLANATION:"]

        for i, course in enumerate(top_courses):
            course_id   = course["course_id"]
            marker      = markers[i]
            next_marker = markers[i + 1] if i + 1 < len(markers) else None

            try:
                if marker in response_text:
                    # Find text after this marker
                    start = response_text.index(marker) + len(marker)

                    # Find where it ends (at the next marker, or end of text)
                    if next_marker and next_marker in response_text:
                        end = response_text.index(next_marker)
                        text = response_text[start:end].strip()
                    else:
                        text = response_text[start:].strip()

                    # Clean up any extra blank lines
                    text = " ".join(text.split())  # Collapse whitespace

                    if text:
                        explanations[course_id] = text
                    else:
                        explanations[course_id] = None

                else:
                    # Marker not found in response
                    explanations[course_id] = None

            except Exception:
                explanations[course_id] = None

        return explanations

    # ══════════════════════════════════════════════════════════════════════════
    # PRIVATE HELPER: Rule-based fallback explanation (original Phase 2A logic)
    # ══════════════════════════════════════════════════════════════════════════

    def _rule_based_explanation(self, course, profile, rank):
        """
        Generates a plain-English explanation using Python string logic.
        This is the original Phase 2A implementation.

        Used as FALLBACK when Ollama is unavailable.

        Args:
            course (dict): The analyzed course dict from Agent 2
            profile (dict): The student profile from Agent 1
            rank (int): The recommendation rank (1, 2, or 3)

        Returns:
            str: A human-readable explanation sentence
        """
        course_name = course["course_name"]
        domain      = course["domain"]
        score       = course["score"]
        career_goal = profile["career_goal"]
        interests   = profile["interests"]

        has_interest_match = any(
            "interest" in r.lower() or "domain" in r.lower()
            for r in course["reasons"]
        )
        has_career_match = any("career" in r.lower() for r in course["reasons"])
        has_full_prereqs = any(
            "all prerequisites met" in r.lower() or "foundation" in r.lower()
            for r in course["reasons"]
        )
        has_difficulty_match = any("difficulty" in r.lower() for r in course["reasons"])

        parts = []

        if rank == 1:
            parts.append(f"{course_name} is your top recommendation")
        elif rank == 2:
            parts.append(f"{course_name} is your second recommendation")
        else:
            parts.append(f"{course_name} is also recommended")

        if has_full_prereqs:
            parts.append("because you have completed all required prerequisites")
        if has_interest_match and interests:
            parts.append(f"and it aligns with your interest in {domain}")
        if has_career_match and career_goal != "Not specified":
            parts.append(f"and supports your goal of becoming a {career_goal}")
        if has_difficulty_match:
            parts.append("at a difficulty level that matches your preference")

        parts.append(f"(Suitability score: {score}/100)")

        if len(parts) >= 3:
            explanation = ", ".join(parts[:2]) + ", " + ", ".join(parts[2:]) + "."
        else:
            explanation = " ".join(parts) + "."

        return f"[Rule-based] {explanation}"


# =============================================================================
# QUICK SELF-TEST (run this file directly)
# =============================================================================

if __name__ == "__main__":
    from agents.academic_profile_agent import AcademicProfileAgent
    from agents.course_analysis_agent  import CourseAnalysisAgent

    profile_agent  = AcademicProfileAgent()
    analysis_agent = CourseAnalysisAgent()
    rec_agent      = RecommendationAgent()

    profile  = profile_agent.run("S001")
    analysis = analysis_agent.run(profile)
    result   = rec_agent.run(profile, analysis)

    print("\nFinal Recommendations:")
    for rec in result["recommendations"]:
        src = rec.get("explanation_source", "unknown")
        print(f"\n  Rank {rec['rank']}: {rec['course_name']} ({rec['score']}/100) [{src}]")
        print(f"  Explanation: {rec['explanation']}")
