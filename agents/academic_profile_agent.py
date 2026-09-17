"""
academic_profile_agent.py
--------------------------
AGENT 1 - Academic Profile Agent

Responsibility:
    Retrieve and structure a student's complete academic profile
    from the SQLite database into a clean Python dictionary.

Input:
    student_id (str) - e.g., "S001"

Output:
    A Python dictionary containing:
        - Basic info (name, program, semester)
        - List of completed subject names
        - Grades dictionary (subject -> grade)
        - Parsed preferences (interests, career_goal, learning_style, etc.)

Phase 2D change:
    Preferences are now retrieved through PreferenceMemory (the memory service)
    instead of calling the database query function directly.
    The profile structure returned is IDENTICAL to before.
    Only the retrieval mechanism changed.

This agent does NOT call Agent 2 or Agent 3.
It only reads from the database and returns structured data.
"""

import sys
import os

# Add project root to path so we can import from /database and /memory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import the database query helper functions we built in Phase 1
from database.database import (
    get_student_by_id,
    get_completed_subjects
)

# Phase 2D: Import PreferenceMemory service to retrieve stored preferences
# This replaces the direct get_preferences() DB call.
# The preference data returned is the same — the path to get it changed.
from memory.preference_memory import PreferenceMemory


class AcademicProfileAgent:
    """
    Agent 1: Academic Profile Agent

    This agent's only job is to:
    1. Accept a student_id
    2. Query the database for all relevant info about that student
    3. Return a clean, structured Python dictionary (the "student profile")

    This dictionary is then passed to Agent 2 for analysis.
    """

    def __init__(self):
        """
        Initialize the agent.
        No database connection is stored here — connections are created
        per query inside the database.py functions (keeps it simple).
        """
        self.agent_name = "Academic Profile Agent"

    def run(self, student_id):
        """
        Main method: retrieves and returns the complete student profile.

        Args:
            student_id (str): The ID of the student to look up, e.g., "S001"

        Returns:
            dict: A structured student profile dictionary,
                  or an error dict if the student is not found.
        """
        print(f"\n[Agent 1] {self.agent_name} - Processing student: {student_id}")

        # ── STEP 1: Fetch basic student info ──────────────────────────────────
        student = get_student_by_id(student_id)

        # If student not found, return an error dictionary (no crash)
        if student is None:
            print(f"[Agent 1] ERROR: Student '{student_id}' not found in database.")
            return {
                "error": True,
                "message": f"Student with ID '{student_id}' does not exist in the database."
            }

        # ── STEP 2: Fetch completed subjects ──────────────────────────────────
        # Returns list of rows: each row has student_id, subject_name, grade
        subject_rows = get_completed_subjects(student_id)

        # Extract just the subject names as a list
        completed_subjects = [row["subject_name"] for row in subject_rows]

        # Build a dictionary of {subject_name: grade} for easy lookup
        grades = {row["subject_name"]: row["grade"] for row in subject_rows}

        # ── STEP 3: Fetch preferences via PreferenceMemory service ────────────
        # Phase 2D: Agent 1 now reads preferences through the PreferenceMemory
        # service, which wraps the same SQLite preferences table.
        # This means any preference saved via save_preference() is automatically
        # picked up here the next time the student's profile is loaded.
        memory_service = PreferenceMemory()
        memory_result  = memory_service.get_preferences(student_id)

        # Extract the list of preference dicts
        # Each dict: {"preference_type": "...", "preference_value": "..."}
        preference_rows = memory_result.get("preferences", [])

        # We'll build a dictionary from the key-value preference pairs
        # e.g., {"career_goal": "AI Engineer", "interest": "NLP", ...}
        preferences = {}
        interests   = []  # A student might have multiple interests

        for pref in preference_rows:
            pref_type  = pref["preference_type"]
            pref_value = pref["preference_value"]

            if pref_type == "interest":
                # Collect all interests into a list
                interests.append(pref_value)
            else:
                # All other preferences stored as simple key-value
                preferences[pref_type] = pref_value

        # ── STEP 4: Assemble the final profile dictionary ─────────────────────
        profile = {
            "error": False,                                         # No error
            "student_id": student["student_id"],
            "name": student["name"],
            "program": student["program"],
            "semester": student["semester"],
            "completed_subjects": completed_subjects,               # List of subject names
            "grades": grades,                                       # {subject: grade}
            "interests": interests,                                 # List of interests
            "career_goal": preferences.get("career_goal", "Not specified"),
            "learning_style": preferences.get("learning_style", "Not specified"),
            "preferred_domain": preferences.get("preferred_domain", "Not specified"),
            "difficulty_preference": preferences.get("difficulty_preference", "Not specified")
        }

        print(f"[Agent 1] Profile retrieved successfully for: {profile['name']}")
        return profile


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    agent = AcademicProfileAgent()

    # Test with a valid student
    profile = agent.run("S001")
    print("\nRetrieved Profile:")
    for key, value in profile.items():
        print(f"  {key}: {value}")

    # Test with an invalid student ID
    print("\n--- Testing invalid student ---")
    error_profile = agent.run("S999")
    print(error_profile)
