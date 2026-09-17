"""
preference_memory.py
--------------------
PHASE 2D - Persistent Preference Memory

This module provides the PreferenceMemory class — a simple service
that reads and writes student preferences to the existing SQLite
preferences table.

IMPORTANT ARCHITECTURE NOTE:
    PreferenceMemory is a SERVICE, not an agent.

    It is a tool/utility that agents call to read or write data.
    It contains NO recommendation logic, NO scoring, and NO LLM calls.

    Just clean CRUD operations on the existing preferences table.

    Memory Table Used:
        preferences (student_id, preference_type, preference_value)
        ← This already exists from Phase 1. Nothing new is created.

WHAT IT DOES:
    save_preference()   - Insert new, or update if preference_type already exists
    get_preferences()   - Read all preferences for a student as a list of dicts
    update_preference() - Explicitly update an existing preference value
    delete_preference() - Remove a specific preference_type for a student

DUPLICATE HANDLING:
    save_preference() uses "upsert" logic:
        - Check if (student_id + preference_type) already exists
        - If YES  → UPDATE the existing value
        - If NO   → INSERT a new row
    This prevents the same preference_type from having multiple rows.
"""

import sqlite3
import os
import sys

# Add project root to path so we can import from /database
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database.database import get_connection


class PreferenceMemory:
    """
    A simple service class for managing student preferences in SQLite.

    Uses the EXISTING 'preferences' table — no new tables or databases.

    All methods:
        - Open their own database connection
        - Execute their query
        - Close the connection
        - Handle errors with try/except (never crash the caller)
    """

    def __init__(self):
        self.service_name = "PreferenceMemory"

    # ══════════════════════════════════════════════════════════════════════════
    # SAVE (UPSERT): Insert new preference OR update if already exists
    # ══════════════════════════════════════════════════════════════════════════

    def save_preference(
        self,
        student_id       : str,
        preference_type  : str,
        preference_value : str
    ) -> dict:
        """
        Saves a preference for a student.

        Uses UPSERT logic:
            - If (student_id + preference_type) does NOT exist → INSERT
            - If (student_id + preference_type) ALREADY exists  → UPDATE

        This prevents duplicate preference_type rows for the same student.

        Args:
            student_id       (str): e.g., "S001"
            preference_type  (str): e.g., "learning_style", "career_goal"
            preference_value (str): e.g., "Project-based", "AI Engineer"

        Returns:
            dict: {"success": True/False, "action": "inserted"/"updated", "message": ...}
        """

        # ── Input validation ────────────────────────────────────────────────────
        if not student_id or not student_id.strip():
            return {"success": False, "action": None, "message": "student_id cannot be empty."}
        if not preference_type or not preference_type.strip():
            return {"success": False, "action": None, "message": "preference_type cannot be empty."}
        if not preference_value or not preference_value.strip():
            return {"success": False, "action": None, "message": "preference_value cannot be empty."}

        try:
            conn   = get_connection()
            cursor = conn.cursor()

            # ── STEP 1: Check if this preference_type already exists for this student
            cursor.execute("""
                SELECT id FROM preferences
                WHERE student_id = ? AND preference_type = ?
            """, (student_id, preference_type))

            existing_row = cursor.fetchone()

            if existing_row:
                # ── STEP 2a: Already exists → UPDATE the value ─────────────────
                cursor.execute("""
                    UPDATE preferences
                    SET preference_value = ?
                    WHERE student_id = ? AND preference_type = ?
                """, (preference_value, student_id, preference_type))

                conn.commit()
                conn.close()
                return {
                    "success": True,
                    "action" : "updated",
                    "message": (
                        f"Updated '{preference_type}' to '{preference_value}' "
                        f"for student {student_id}."
                    )
                }

            else:
                # ── STEP 2b: Does not exist → INSERT a new row ─────────────────
                cursor.execute("""
                    INSERT INTO preferences (student_id, preference_type, preference_value)
                    VALUES (?, ?, ?)
                """, (student_id, preference_type, preference_value))

                conn.commit()
                conn.close()
                return {
                    "success": True,
                    "action" : "inserted",
                    "message": (
                        f"Saved new preference '{preference_type}' = '{preference_value}' "
                        f"for student {student_id}."
                    )
                }

        except sqlite3.Error as e:
            return {
                "success": False,
                "action" : None,
                "message": f"Database error while saving preference: {str(e)}"
            }

        except Exception as e:
            return {
                "success": False,
                "action" : None,
                "message": f"Unexpected error while saving preference: {str(e)}"
            }

    # ══════════════════════════════════════════════════════════════════════════
    # GET: Retrieve all preferences for a student
    # ══════════════════════════════════════════════════════════════════════════

    def get_preferences(self, student_id: str) -> dict:
        """
        Retrieves all stored preferences for a student.

        Args:
            student_id (str): e.g., "S001"

        Returns:
            dict:
                {
                    "success"    : True / False,
                    "preferences": [
                        {"preference_type": "learning_style", "preference_value": "Project-based"},
                        {"preference_type": "career_goal",    "preference_value": "AI Engineer"},
                        ...
                    ],
                    "message"    : "..." (only on error)
                }
        """
        if not student_id or not student_id.strip():
            return {"success": False, "preferences": [], "message": "student_id cannot be empty."}

        try:
            conn   = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT preference_type, preference_value
                FROM preferences
                WHERE student_id = ?
                ORDER BY preference_type
            """, (student_id,))

            rows = cursor.fetchall()
            conn.close()

            # Convert sqlite3.Row objects to plain dicts for easier use
            preferences = [
                {
                    "preference_type" : row["preference_type"],
                    "preference_value": row["preference_value"]
                }
                for row in rows
            ]

            return {
                "success"    : True,
                "preferences": preferences,
                "message"    : f"Retrieved {len(preferences)} preference(s) for student {student_id}."
            }

        except sqlite3.Error as e:
            return {
                "success"    : False,
                "preferences": [],
                "message"    : f"Database error while retrieving preferences: {str(e)}"
            }

        except Exception as e:
            return {
                "success"    : False,
                "preferences": [],
                "message"    : f"Unexpected error while retrieving preferences: {str(e)}"
            }

    # ══════════════════════════════════════════════════════════════════════════
    # UPDATE: Explicitly update an existing preference
    # ══════════════════════════════════════════════════════════════════════════

    def update_preference(
        self,
        student_id       : str,
        preference_type  : str,
        preference_value : str
    ) -> dict:
        """
        Explicitly updates an existing preference.

        Differs from save_preference() in that it ONLY updates —
        it does NOT insert if the preference doesn't exist yet.

        Args:
            student_id       (str): e.g., "S001"
            preference_type  (str): e.g., "learning_style"
            preference_value (str): The new value, e.g., "Theoretical"

        Returns:
            dict: {"success": True/False, "message": "..."}
        """
        if not student_id or not preference_type or not preference_value:
            return {
                "success": False,
                "message": "student_id, preference_type, and preference_value are all required."
            }

        try:
            conn   = get_connection()
            cursor = conn.cursor()

            # Check the preference exists before updating
            cursor.execute("""
                SELECT id FROM preferences
                WHERE student_id = ? AND preference_type = ?
            """, (student_id, preference_type))

            row = cursor.fetchone()

            if not row:
                conn.close()
                return {
                    "success": False,
                    "message": (
                        f"No preference of type '{preference_type}' found for student {student_id}. "
                        "Use save_preference() to create it first."
                    )
                }

            # Perform the update
            cursor.execute("""
                UPDATE preferences
                SET preference_value = ?
                WHERE student_id = ? AND preference_type = ?
            """, (preference_value, student_id, preference_type))

            conn.commit()
            conn.close()
            return {
                "success": True,
                "message": (
                    f"Updated '{preference_type}' to '{preference_value}' "
                    f"for student {student_id}."
                )
            }

        except sqlite3.Error as e:
            return {"success": False, "message": f"Database error during update: {str(e)}"}

        except Exception as e:
            return {"success": False, "message": f"Unexpected error during update: {str(e)}"}

    # ══════════════════════════════════════════════════════════════════════════
    # DELETE: Remove a specific preference
    # ══════════════════════════════════════════════════════════════════════════

    def delete_preference(self, student_id: str, preference_type: str) -> dict:
        """
        Deletes a specific preference type for a student.

        Only deletes the specified preference_type — other preferences
        for the same student are NOT affected.

        Args:
            student_id      (str): e.g., "S001"
            preference_type (str): e.g., "learning_style"

        Returns:
            dict: {"success": True/False, "message": "..."}
        """
        if not student_id or not preference_type:
            return {
                "success": False,
                "message": "Both student_id and preference_type are required."
            }

        try:
            conn   = get_connection()
            cursor = conn.cursor()

            # Check it exists first
            cursor.execute("""
                SELECT id FROM preferences
                WHERE student_id = ? AND preference_type = ?
            """, (student_id, preference_type))

            row = cursor.fetchone()

            if not row:
                conn.close()
                return {
                    "success": False,
                    "message": (
                        f"No preference of type '{preference_type}' found "
                        f"for student {student_id}. Nothing to delete."
                    )
                }

            # Delete only this specific preference
            cursor.execute("""
                DELETE FROM preferences
                WHERE student_id = ? AND preference_type = ?
            """, (student_id, preference_type))

            conn.commit()
            conn.close()
            return {
                "success": True,
                "message": (
                    f"Deleted preference '{preference_type}' "
                    f"for student {student_id}."
                )
            }

        except sqlite3.Error as e:
            return {"success": False, "message": f"Database error during delete: {str(e)}"}

        except Exception as e:
            return {"success": False, "message": f"Unexpected error during delete: {str(e)}"}

    # ══════════════════════════════════════════════════════════════════════════
    # HELPER: Get a single preference value by type
    # ══════════════════════════════════════════════════════════════════════════

    def get_preference_value(self, student_id: str, preference_type: str) -> str | None:
        """
        Convenience method: returns the value of one specific preference type.

        Args:
            student_id      (str): e.g., "S001"
            preference_type (str): e.g., "career_goal"

        Returns:
            str: The preference value, or None if not found
        """
        result = self.get_preferences(student_id)
        if not result["success"]:
            return None

        for pref in result["preferences"]:
            if pref["preference_type"] == preference_type:
                return pref["preference_value"]

        return None


# =============================================================================
# QUICK SELF-TEST (run this file directly)
# =============================================================================

if __name__ == "__main__":
    memory = PreferenceMemory()

    print("--- Reading S001 preferences ---")
    result = memory.get_preferences("S001")
    for p in result["preferences"]:
        print(f"  {p['preference_type']:<22} : {p['preference_value']}")

    print("\n--- Saving a test preference ---")
    r = memory.save_preference("S001", "test_pref", "test_value")
    print(f"  {r['action']}: {r['message']}")

    print("\n--- Updating it ---")
    r = memory.update_preference("S001", "test_pref", "updated_value")
    print(f"  {r['message']}")

    print("\n--- Deleting it ---")
    r = memory.delete_preference("S001", "test_pref")
    print(f"  {r['message']}")

    print("\n--- S001 preferences after cleanup ---")
    result = memory.get_preferences("S001")
    print(f"  {len(result['preferences'])} preferences remaining")
