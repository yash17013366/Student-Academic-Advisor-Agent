"""
feedback_db.py
--------------
Unit III - Feedback Database Operations

Manages the course_feedback table used for the Act -> Observe -> Reflect -> Adjust loop.
Works alongside the existing academic_advisor.db without altering existing tables.

Table: course_feedback
    id              INTEGER PRIMARY KEY AUTOINCREMENT
    student_id      TEXT NOT NULL
    course_id       TEXT NOT NULL
    feedback_type   TEXT NOT NULL  -- "too_difficult", "not_interested", "too_theoretical", "already_familiar"
    feedback_note   TEXT           -- Optional free-text note
    timestamp       TEXT NOT NULL  -- ISO timestamp string
"""

import sqlite3
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database.database import get_connection


# ---------------------------------------------------------
# FEEDBACK TYPE CONSTANTS
# ---------------------------------------------------------

FEEDBACK_TYPES = {
    "too_difficult"    : "Too Difficult",
    "not_interested"   : "Not Interested",
    "too_theoretical"  : "Too Theoretical",
    "already_familiar" : "Already Familiar",
    "too_easy"         : "Too Easy",
}

# Score penalty applied during reflection for each feedback type.
# Eligibility constraints (prerequisites) are NEVER affected by these.
FEEDBACK_SCORE_ADJUSTMENTS = {
    "too_difficult"    : -25,
    "not_interested"   : -30,
    "too_theoretical"  : -15,
    "already_familiar" : -20,
    "too_easy"         : -10,
}


def create_feedback_table():
    """
    Creates the course_feedback table if it does not already exist.
    Safe to call multiple times (IF NOT EXISTS).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_feedback (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    TEXT NOT NULL,
            course_id     TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            feedback_note TEXT DEFAULT '',
            timestamp     TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_feedback(student_id, course_id, feedback_type, feedback_note=""):
    """
    Persists a piece of feedback for a student-course pair.

    Allows multiple feedback entries per student-course pair (history is kept).
    Prerequisite and eligibility constraints are NEVER touched here.

    Args:
        student_id    (str): e.g., "S001"
        course_id     (str): e.g., "EL101"
        feedback_type (str): One of the FEEDBACK_TYPES keys
        feedback_note (str): Optional free-text note

    Returns:
        dict: {"success": True/False, "message": "...", "id": row_id}
    """
    if feedback_type not in FEEDBACK_TYPES:
        return {
            "success": False,
            "message": (
                f"Invalid feedback type '{feedback_type}'. "
                f"Valid types: {list(FEEDBACK_TYPES.keys())}"
            )
        }

    try:
        create_feedback_table()
        conn   = get_connection()
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO course_feedback
                (student_id, course_id, feedback_type, feedback_note, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, course_id, feedback_type, feedback_note or "", timestamp))

        conn.commit()
        row_id = cursor.lastrowid
        conn.close()

        return {
            "success"  : True,
            "message"  : (
                f"Feedback '{FEEDBACK_TYPES[feedback_type]}' saved for course "
                f"{course_id} by student {student_id}."
            ),
            "id"       : row_id,
            "timestamp": timestamp
        }

    except sqlite3.Error as e:
        return {"success": False, "message": f"DB error saving feedback: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {e}"}


def get_feedback_for_student(student_id):
    """
    Retrieves all feedback records for a student.

    Returns:
        list of dicts with keys: id, student_id, course_id, feedback_type, feedback_note, timestamp
    """
    try:
        create_feedback_table()
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, student_id, course_id, feedback_type, feedback_note, timestamp
            FROM   course_feedback
            WHERE  student_id = ?
            ORDER  BY timestamp DESC
        """, (student_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []


def get_feedback_for_course(student_id, course_id):
    """
    Retrieves all feedback for a specific student-course pair.

    Returns:
        list of dicts (most recent first)
    """
    try:
        create_feedback_table()
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, course_id, feedback_type, feedback_note, timestamp
            FROM   course_feedback
            WHERE  student_id = ? AND course_id = ?
            ORDER  BY timestamp DESC
        """, (student_id, course_id))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []


def get_cumulative_adjustment(student_id, course_id):
    """
    Calculates the cumulative score adjustment for a student-course pair
    based on ALL persisted feedback entries.

    The adjustment is additive (multiple feedbacks compound).
    The caller is responsible for clamping the final score >= 0.

    Args:
        student_id (str): e.g., "S001"
        course_id  (str): e.g., "EL101"

    Returns:
        int: Total score adjustment (usually negative, e.g., -25)
    """
    feedbacks = get_feedback_for_course(student_id, course_id)
    total_adjustment = 0
    for fb in feedbacks:
        fb_type    = fb.get("feedback_type", "")
        adjustment = FEEDBACK_SCORE_ADJUSTMENTS.get(fb_type, 0)
        total_adjustment += adjustment
    return total_adjustment
