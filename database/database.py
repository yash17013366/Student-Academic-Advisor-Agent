"""
database.py
-----------
This module handles all database operations for the Student Academic Advisor system.

It provides:
- A connection to the SQLite database
- Functions to create the four required tables
- Helper functions to query students, subjects, electives, and preferences

The database file is: academic_advisor.db
"""

import sqlite3  # Built-in Python library — no installation needed
import os

# ─────────────────────────────────────────────
# DATABASE FILE PATH
# ─────────────────────────────────────────────

# Get the directory where THIS file (database.py) lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The database file will be stored inside the /database folder
DB_PATH = os.path.join(BASE_DIR, "academic_advisor.db")


# ─────────────────────────────────────────────
# CONNECTION FUNCTION
# ─────────────────────────────────────────────

def get_connection():
    """
    Creates and returns a connection to the SQLite database.

    sqlite3.connect() will:
    - Open the database if it already exists
    - Create the database file if it doesn't exist yet

    Returns:
        conn (sqlite3.Connection): An active database connection
    """
    conn = sqlite3.connect(DB_PATH)

    # This makes rows behave like dictionaries (row["column_name"])
    # instead of tuples (row[0], row[1], ...) — much easier to read!
    conn.row_factory = sqlite3.Row

    return conn


# ─────────────────────────────────────────────
# TABLE CREATION FUNCTIONS
# ─────────────────────────────────────────────

def create_tables():
    """
    Creates all four tables in the database if they don't already exist.

    Tables:
        1. students          - Basic student info (id, name, program, semester)
        2. completed_subjects - Which subjects a student has finished
        3. electives          - All available elective courses
        4. preferences        - Student interests and goals

    This function is safe to run multiple times.
    'IF NOT EXISTS' prevents errors if the table already exists.
    """
    conn = get_connection()
    cursor = conn.cursor()  # A cursor is used to send SQL commands

    # ── TABLE 1: students ──────────────────────────────────────────────────────
    # Stores the basic profile of each student.
    # student_id is the PRIMARY KEY — it uniquely identifies each student.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id  TEXT PRIMARY KEY,   -- e.g., "S001"
            name        TEXT NOT NULL,       -- Full name of the student
            program     TEXT NOT NULL,       -- e.g., "B.Tech Computer Science"
            semester    INTEGER NOT NULL     -- Current semester number (1–8)
        )
    """)

    # ── TABLE 2: completed_subjects ────────────────────────────────────────────
    # Stores subjects that each student has already completed.
    # FOREIGN KEY links this table back to the students table.
    # One student can have MANY completed subjects (one-to-many relationship).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS completed_subjects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT, -- Auto-generated unique row ID
            student_id      TEXT NOT NULL,                     -- Links to students.student_id
            subject_name    TEXT NOT NULL,                     -- e.g., "Machine Learning"
            grade           TEXT NOT NULL,                     -- e.g., "A", "B", "C"
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    # ── TABLE 3: electives ─────────────────────────────────────────────────────
    # Stores all available elective courses students can take.
    # prerequisites, skills, and career_paths are stored as comma-separated text
    # for simplicity (avoids needing extra join tables).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS electives (
            course_id       TEXT PRIMARY KEY,   -- e.g., "EL101"
            course_name     TEXT NOT NULL,       -- e.g., "Natural Language Processing"
            description     TEXT NOT NULL,       -- Short summary of what the course covers
            prerequisites   TEXT NOT NULL,       -- Comma-separated list of required subjects
            domain          TEXT NOT NULL,       -- e.g., "Artificial Intelligence"
            skills          TEXT NOT NULL,       -- Comma-separated skills gained
            career_paths    TEXT NOT NULL,       -- Comma-separated career options
            difficulty      TEXT NOT NULL        -- "Easy", "Medium", or "Hard"
        )
    """)

    # ── TABLE 4: preferences ───────────────────────────────────────────────────
    # Stores student preferences as key-value pairs.
    # preference_type = "career_goal", "interest", "learning_style", etc.
    # preference_value = the actual value, e.g., "AI Engineer"
    # One student can have MANY preferences (one-to-many relationship).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id          TEXT NOT NULL,    -- Links to students.student_id
            preference_type     TEXT NOT NULL,    -- e.g., "career_goal"
            preference_value    TEXT NOT NULL,    -- e.g., "AI Engineer"
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    # Save all changes to the database file
    conn.commit()
    conn.close()

    print("[OK] All 4 tables created successfully.")


# ─────────────────────────────────────────────
# QUERY HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_all_students():
    """
    Retrieves all students from the database.

    Returns:
        list of sqlite3.Row objects (each row represents one student)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()  # Gets all rows as a list
    conn.close()
    return students


def get_student_by_id(student_id):
    """
    Retrieves a single student by their ID.

    Args:
        student_id (str): e.g., "S001"

    Returns:
        sqlite3.Row or None if student not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    # The '?' placeholder safely inserts the value (prevents SQL injection)
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()  # Gets just one row
    conn.close()
    return student


def get_completed_subjects(student_id):
    """
    Retrieves all completed subjects for a specific student.

    Args:
        student_id (str): e.g., "S001"

    Returns:
        list of sqlite3.Row objects (each row = one completed subject)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM completed_subjects WHERE student_id = ?",
        (student_id,)
    )
    subjects = cursor.fetchall()
    conn.close()
    return subjects


def get_all_electives():
    """
    Retrieves all available elective courses from the database.

    Returns:
        list of sqlite3.Row objects (each row = one elective)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM electives")
    electives = cursor.fetchall()
    conn.close()
    return electives


def get_electives_by_domain(domain):
    """
    Retrieves electives filtered by a specific domain.

    Args:
        domain (str): e.g., "Artificial Intelligence"

    Returns:
        list of sqlite3.Row objects
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM electives WHERE domain = ?", (domain,))
    electives = cursor.fetchall()
    conn.close()
    return electives


def get_preferences(student_id):
    """
    Retrieves all preferences for a specific student.

    Args:
        student_id (str): e.g., "S001"

    Returns:
        list of sqlite3.Row objects (each row = one preference entry)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM preferences WHERE student_id = ?",
        (student_id,)
    )
    prefs = cursor.fetchall()
    conn.close()
    return prefs


# ─────────────────────────────────────────────
# QUICK SELF-TEST (run this file directly to verify DB setup)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[DB] Database will be stored at: {DB_PATH}")
    create_tables()
    print("[DONE] Database setup complete!")
