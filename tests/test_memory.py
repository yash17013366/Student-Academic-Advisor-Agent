"""
test_memory.py
--------------
PHASE 2D - Preference Memory CRUD Test

This script tests all four operations of PreferenceMemory:
    1. get_preferences()   - Read current preferences
    2. save_preference()   - Insert a new preference
    3. get_preferences()   - Verify the new one is there
    4. update_preference() - Change the value
    5. get_preference_value() - Verify the update
    6. delete_preference() - Remove the test preference
    7. get_preference_value() - Verify deletion

IMPORTANT:
    - Uses student S001 (Aanya Sharma)
    - Saves a TEMPORARY preference (preference_type = "course_format")
    - Cleans it up at the end
    - The original 5 seeded preferences for S001 are NOT affected

Usage:
    python tests/test_memory.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from memory.preference_memory import PreferenceMemory


def bar(char="=", width=46):
    print(char * width)


def check(condition, success_msg, fail_msg):
    """Prints a pass/fail result."""
    if condition:
        print(f"  [OK] {success_msg}")
    else:
        print(f"  [FAIL] {fail_msg}")
    return condition


def run_memory_test():
    bar()
    print("  PREFERENCE MEMORY TEST")
    bar()

    STUDENT_ID    = "S001"
    TEST_PREF_TYPE  = "course_format"        # Temporary — will be deleted at end
    TEST_PREF_VAL1  = "Project-based"
    TEST_PREF_VAL2  = "Hands-on"

    memory = PreferenceMemory()
    all_passed = True

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Read existing preferences (verify the seeded data is intact)
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [1] Reading existing preferences for {STUDENT_ID}")

    result = memory.get_preferences(STUDENT_ID)
    ok = check(
        result["success"] and len(result["preferences"]) > 0,
        f"Retrieved {len(result['preferences'])} existing preference(s)",
        "Failed to retrieve existing preferences"
    )
    all_passed = all_passed and ok

    if ok:
        print(f"\n       Current preferences:")
        for p in result["preferences"]:
            print(f"         {p['preference_type']:<22} : {p['preference_value']}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Save a NEW temporary preference
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [2] Saving new preference  [{TEST_PREF_TYPE} = {TEST_PREF_VAL1}]")

    result = memory.save_preference(STUDENT_ID, TEST_PREF_TYPE, TEST_PREF_VAL1)
    ok = check(
        result["success"] and result["action"] == "inserted",
        f"Preference saved (action: {result.get('action', '?')})",
        f"Failed to save preference: {result.get('message')}"
    )
    all_passed = all_passed and ok

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Retrieve and verify the new preference exists
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [3] Verifying the saved preference is retrievable")

    saved_value = memory.get_preference_value(STUDENT_ID, TEST_PREF_TYPE)
    ok = check(
        saved_value == TEST_PREF_VAL1,
        f"Retrieved value correctly: '{saved_value}'",
        f"Expected '{TEST_PREF_VAL1}' but got '{saved_value}'"
    )
    all_passed = all_passed and ok

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Update the preference value
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [4] Updating preference  [{TEST_PREF_TYPE}: {TEST_PREF_VAL1} -> {TEST_PREF_VAL2}]")

    result = memory.update_preference(STUDENT_ID, TEST_PREF_TYPE, TEST_PREF_VAL2)
    ok = check(
        result["success"],
        "Preference updated successfully",
        f"Failed to update preference: {result.get('message')}"
    )
    all_passed = all_passed and ok

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Verify the updated value
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [5] Verifying the update")

    updated_value = memory.get_preference_value(STUDENT_ID, TEST_PREF_TYPE)
    ok = check(
        updated_value == TEST_PREF_VAL2,
        f"Value is now: '{updated_value}'",
        f"Expected '{TEST_PREF_VAL2}' but got '{updated_value}'"
    )
    all_passed = all_passed and ok

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5b: Test save_preference() upsert — saving same type again updates it
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [5b] Testing UPSERT — saving same preference_type again (should update, not duplicate)")

    result = memory.save_preference(STUDENT_ID, TEST_PREF_TYPE, "Theoretical")
    ok = check(
        result["success"] and result["action"] == "updated",
        f"Correctly updated existing preference (action: {result.get('action', '?')})",
        f"Expected 'updated' action but got '{result.get('action')}'"
    )
    all_passed = all_passed and ok

    # Confirm only 1 row of this type exists
    all_prefs = memory.get_preferences(STUDENT_ID)
    type_count = sum(
        1 for p in all_prefs["preferences"]
        if p["preference_type"] == TEST_PREF_TYPE
    )
    ok = check(
        type_count == 1,
        f"No duplicate rows — exactly {type_count} row for '{TEST_PREF_TYPE}'",
        f"Duplicate detected — found {type_count} rows for '{TEST_PREF_TYPE}'"
    )
    all_passed = all_passed and ok

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Delete the temporary test preference
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [6] Deleting temporary test preference  [{TEST_PREF_TYPE}]")

    result = memory.delete_preference(STUDENT_ID, TEST_PREF_TYPE)
    ok = check(
        result["success"],
        "Temporary preference deleted",
        f"Failed to delete preference: {result.get('message')}"
    )
    all_passed = all_passed and ok

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Verify it's gone and original prefs are intact
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n  [7] Verifying deletion and original preferences are intact")

    deleted_value = memory.get_preference_value(STUDENT_ID, TEST_PREF_TYPE)
    ok = check(
        deleted_value is None,
        f"Preference '{TEST_PREF_TYPE}' successfully removed",
        f"Preference still exists with value: '{deleted_value}'"
    )
    all_passed = all_passed and ok

    final_prefs = memory.get_preferences(STUDENT_ID)
    ok = check(
        final_prefs["success"] and len(final_prefs["preferences"]) >= 5,
        f"Original preferences intact — {len(final_prefs['preferences'])} preference(s) remain",
        f"Original preferences may have been affected"
    )
    all_passed = all_passed and ok

    if ok:
        print(f"\n       Remaining preferences:")
        for p in final_prefs["preferences"]:
            print(f"         {p['preference_type']:<22} : {p['preference_value']}")

    # ─────────────────────────────────────────────────────────────────────────
    # RESULT
    # ─────────────────────────────────────────────────────────────────────────
    print()
    bar()
    if all_passed:
        print("  MEMORY TEST COMPLETE — ALL TESTS PASSED")
    else:
        print("  MEMORY TEST COMPLETE — SOME TESTS FAILED (review output above)")
    bar()
    print()


if __name__ == "__main__":
    run_memory_test()
