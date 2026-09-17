"""
seed_database.py
----------------
This script populates the SQLite database with initial (seed) data.

It reads from the three JSON files in the /data folder:
    - students.json    → inserts into 'students' and 'completed_subjects' tables
    - courses.json     → inserts into 'electives' table
    - preferences.json → inserts into 'preferences' table

Run this script ONCE after creating the database with database.py.
Running it again will skip duplicate entries (safe to re-run).

Usage:
    python database/seed_database.py
"""

import json       # To read .json files
import os         # To build file paths
import sys        # To modify the Python module search path

# ─────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────

# Get the root directory of the project (one level above /database)
# This allows us to import from /database/database.py and find /data/ files
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to sys.path so Python can find our database module
sys.path.insert(0, PROJECT_ROOT)

# Now we can import our database functions
from database.database import get_connection, create_tables

# Path to the /data directory where our JSON files live
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


# ─────────────────────────────────────────────
# HELPER: LOAD JSON FILE
# ─────────────────────────────────────────────

def load_json(filename):
    """
    Loads and parses a JSON file from the /data directory.

    Args:
        filename (str): Name of the JSON file (e.g., "students.json")

    Returns:
        list or dict: Parsed Python object from the JSON file
    """
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# SEED FUNCTION 1: STUDENTS & COMPLETED SUBJECTS
# ─────────────────────────────────────────────

def seed_students(conn):
    """
    Inserts student records and their completed subjects into the database.

    Reads from: data/students.json
    Inserts into:
        - students table (basic profile)
        - completed_subjects table (subjects each student has finished)

    Uses 'INSERT OR IGNORE' to avoid errors on duplicate student_ids.
    """
    cursor = conn.cursor()
    students_data = load_json("students.json")

    for student in students_data:
        # ── Insert basic student profile ──────────────────────────────────────
        cursor.execute("""
            INSERT OR IGNORE INTO students (student_id, name, program, semester)
            VALUES (?, ?, ?, ?)
        """, (
            student["student_id"],
            student["name"],
            student["program"],
            student["semester"]
        ))

        # ── Insert each completed subject for this student ────────────────────
        # We check if the record already exists before inserting.
        # This prevents duplicate rows if seed_database.py is run more than once.
        for subject in student["completed_subjects"]:
            cursor.execute("""
                SELECT COUNT(*) FROM completed_subjects
                WHERE student_id = ? AND subject_name = ?
            """, (student["student_id"], subject["subject_name"]))

            if cursor.fetchone()[0] == 0:  # Only insert if NOT already present
                cursor.execute("""
                    INSERT INTO completed_subjects
                        (student_id, subject_name, grade)
                    VALUES (?, ?, ?)
                """, (
                    student["student_id"],
                    subject["subject_name"],
                    subject["grade"]
                ))

    print(f"[OK] Seeded {len(students_data)} students and their completed subjects.")


# ─────────────────────────────────────────────
# SEED FUNCTION 2: ELECTIVES
# ─────────────────────────────────────────────

def seed_electives(conn):
    """
    Inserts all elective course records into the database.

    Reads from: data/courses.json
    Inserts into: electives table

    Lists (prerequisites, skills, career_paths) are converted to
    comma-separated strings for simple storage in SQLite.
    """
    cursor = conn.cursor()
    courses_data = load_json("courses.json")

    for course in courses_data:
        # Convert Python lists to comma-separated strings for SQLite storage
        # Example: ["Python", "ML"] → "Python, ML"
        prerequisites_str = ", ".join(course["prerequisites"])
        skills_str        = ", ".join(course["skills"])
        career_paths_str  = ", ".join(course["career_paths"])

        cursor.execute("""
            INSERT OR IGNORE INTO electives
                (course_id, course_name, description, prerequisites,
                 domain, skills, career_paths, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            course["course_id"],
            course["course_name"],
            course["description"],
            prerequisites_str,
            course["domain"],
            skills_str,
            career_paths_str,
            course["difficulty"]
        ))

    print(f"[OK] Seeded {len(courses_data)} elective courses.")


# ─────────────────────────────────────────────
# SEED FUNCTION 3: PREFERENCES
# ─────────────────────────────────────────────

def seed_preferences(conn):
    """
    Inserts student preferences into the database.

    Reads from: data/preferences.json
    Inserts into: preferences table

    Each student can have multiple preferences (interest, career_goal, etc.)
    stored as separate rows using the key-value pattern.
    """
    cursor = conn.cursor()
    preferences_data = load_json("preferences.json")

    total_prefs = 0

    for entry in preferences_data:
        student_id = entry["student_id"]

        for pref in entry["preferences"]:
            # Check if this preference already exists before inserting
            cursor.execute("""
                SELECT COUNT(*) FROM preferences
                WHERE student_id = ? AND preference_type = ? AND preference_value = ?
            """, (student_id, pref["preference_type"], pref["preference_value"]))

            if cursor.fetchone()[0] == 0:  # Only insert if NOT already present
                cursor.execute("""
                    INSERT INTO preferences (student_id, preference_type, preference_value)
                    VALUES (?, ?, ?)
                """, (
                    student_id,
                    pref["preference_type"],
                    pref["preference_value"]
                ))
                total_prefs += 1

    print(f"[OK] Seeded {total_prefs} student preferences.")


# ─────────────────────────────────────────────
# MAIN SEED FUNCTION
# ─────────────────────────────────────────────

def seed_all():
    """
    Master function that:
    1. Creates all tables (if not already created)
    2. Seeds students, electives, and preferences data
    3. Commits everything to the database in one transaction

    A single conn.commit() at the end ensures all inserts succeed
    together — if anything fails, nothing is saved (atomicity).
    """
    print("\n[SEED] Starting database seeding process...\n")

    # Step 1: Ensure tables exist
    create_tables()

    # Step 2: Open a single database connection for all inserts
    conn = get_connection()

    # Step 3: Run all three seed functions
    seed_students(conn)
    seed_electives(conn)
    seed_preferences(conn)

    # Step 4: Save all changes in one go
    conn.commit()
    conn.close()

    print("\n[DONE] Database seeding complete! academic_advisor.db is ready to use.\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    seed_all()
