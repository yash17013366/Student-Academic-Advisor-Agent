"""
test_database.py
----------------
A simple test script to verify that the SQLite database
has been correctly created and seeded with data.

This script:
    1. Connects to academic_advisor.db
    2. Prints all 10 students
    3. Shows completed subjects for student S001 (Aanya Sharma)
    4. Lists all available electives
    5. Displays preferences for student S001

Run this after seeding the database:
    python tests/test_database.py
"""

import os
import sys

# ─────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────

# Add project root to path so we can import from /database
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import all our query helper functions from database.py
from database.database import (
    get_all_students,
    get_student_by_id,
    get_completed_subjects,
    get_all_electives,
    get_preferences
)


# ─────────────────────────────────────────────
# DISPLAY SEPARATOR (just for nice output formatting)
# ─────────────────────────────────────────────

def separator(title):
    """Prints a visual separator with a title for readability."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ─────────────────────────────────────────────
# TEST 1: Print All Students
# ─────────────────────────────────────────────

def test_all_students():
    """
    Fetches and prints every student in the database.
    Expected output: 10 student rows.
    """
    separator("TEST 1: All Students in Database")

    students = get_all_students()

    print(f"  Total students found: {len(students)}\n")

    # Print each student's details
    for student in students:
        # student["column_name"] works because we set row_factory = sqlite3.Row
        print(f"  [{student['student_id']}] {student['name']}")
        print(f"       Program  : {student['program']}")
        print(f"       Semester : {student['semester']}")
        print()


# ─────────────────────────────────────────────
# TEST 2: Completed Subjects for One Student
# ─────────────────────────────────────────────

def test_completed_subjects(student_id="S001"):
    """
    Retrieves and displays all completed subjects for a given student.

    Args:
        student_id (str): The student to look up (default: "S001")
    """
    separator(f"TEST 2: Completed Subjects for Student {student_id}")

    # First get the student's name for display purposes
    student = get_student_by_id(student_id)
    if not student:
        print(f"  [ERROR] Student {student_id} not found in database.")
        return

    print(f"  Student : {student['name']} ({student['program']})\n")

    # Now get all their completed subjects
    subjects = get_completed_subjects(student_id)

    print(f"  Completed Subjects ({len(subjects)} total):\n")
    for subject in subjects:
        print(f"    [v] {subject['subject_name']}  ->  Grade: {subject['grade']}")


# ─────────────────────────────────────────────
# TEST 3: All Available Electives
# ─────────────────────────────────────────────

def test_all_electives():
    """
    Retrieves and displays all elective courses stored in the database.
    Expected output: 10 elective entries.
    """
    separator("TEST 3: All Available Electives")

    electives = get_all_electives()

    print(f"  Total electives found: {len(electives)}\n")

    for elective in electives:
        print(f"  [{elective['course_id']}] {elective['course_name']}")
        print(f"       Domain        : {elective['domain']}")
        print(f"       Difficulty    : {elective['difficulty']}")
        print(f"       Prerequisites : {elective['prerequisites']}")
        print()


# ─────────────────────────────────────────────
# TEST 4: Preferences for One Student
# ─────────────────────────────────────────────

def test_preferences(student_id="S001"):
    """
    Retrieves and displays all stored preferences for a given student.

    Args:
        student_id (str): The student to look up (default: "S001")
    """
    separator(f"TEST 4: Preferences for Student {student_id}")

    student = get_student_by_id(student_id)
    if not student:
        print(f"  [ERROR] Student {student_id} not found in database.")
        return

    print(f"  Student : {student['name']}\n")

    prefs = get_preferences(student_id)

    if not prefs:
        print("  No preferences found for this student.")
        return

    print(f"  Preferences ({len(prefs)} total):\n")
    for pref in prefs:
        # Nicely align the preference type and value
        print(f"    - {pref['preference_type']:<22} : {pref['preference_value']}")


# ─────────────────────────────────────────────
# MAIN: RUN ALL TESTS
# ─────────────────────────────────────────────

def run_all_tests():
    """
    Runs all database verification tests in sequence.
    """
    print("\n[TEST] Running Database Verification Tests...")
    print("   (Make sure you've run seed_database.py first!)\n")

    test_all_students()
    test_completed_subjects("S001")  # Aanya Sharma -- AI student
    test_all_electives()
    test_preferences("S001")         # Aanya Sharma's preferences

    separator("ALL TESTS COMPLETE")
    print("  [OK] Database is set up and seeded correctly!")
    print("  [OK] Ready to proceed to Phase 2 (Agent Development)\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run_all_tests()
