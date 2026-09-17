"""
main.py
-------
Entry point for the Student Academic Advisor Agent system.

Currently (Phase 1): Runs the database setup and seeding process.

Future phases will add:
    - Phase 2: Agent logic (Academic Profile, Course Analysis, Recommendation)
    - Phase 3: Streamlit UI
    - Phase 4: Ollama LLM integration
    - Phase 5: LangGraph multi-agent workflow

Usage:
    python main.py
"""

import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.seed_database import seed_all


def main():
    print("=" * 52)
    print("  Student Academic Advisor Agent -- Phase 1")
    print("  Database Setup & Seeding")
    print("=" * 52)

    # Run the full database setup and seed process
    seed_all()

    print("Next step: Run the test script to verify the database.")
    print("  -> python tests/test_database.py\n")


if __name__ == "__main__":
    main()
