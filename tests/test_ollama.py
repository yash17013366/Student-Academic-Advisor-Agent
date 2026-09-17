"""
test_ollama.py
--------------
PHASE 2C - Ollama Connection Test

This script verifies:
    1. Ollama server is running
    2. qwen2.5:3b model is available locally
    3. The model can receive a prompt and return a response

Usage:
    python tests/test_ollama.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from llm.ollama_client import (
    OLLAMA_MODEL,
    is_ollama_running,
    is_model_available,
    generate_explanation
)


def bar(char="=", width=46):
    print(char * width)


def run_ollama_test():
    bar()
    print("  OLLAMA CONNECTION TEST")
    bar()
    print(f"\n  Model configured : {OLLAMA_MODEL}\n")

    # ── CHECK 1: Is Ollama server running? ─────────────────────────────────────
    running = is_ollama_running()
    if running:
        print("  [OK] Ollama server is running")
    else:
        print("  [FAIL] Cannot connect to Ollama server.")
        print("         Make sure Ollama is installed and the server is running.")
        print("         Start it with:  ollama serve")
        bar()
        return

    # ── CHECK 2: Is the model available? ──────────────────────────────────────
    available = is_model_available(OLLAMA_MODEL)
    if available:
        print(f"  [OK] Model '{OLLAMA_MODEL}' is available")
    else:
        print(f"  [FAIL] Model '{OLLAMA_MODEL}' is not available locally.")
        print(f"         Pull it with:  ollama pull {OLLAMA_MODEL}")
        bar()
        return

    # ── CHECK 3: Send a test prompt and get a response ────────────────────────
    print(f"\n  Sending test prompt to {OLLAMA_MODEL}...")
    test_prompt = (
        "You are a university academic advisor. "
        "In exactly one sentence, why is Python Programming important "
        "as a foundation for AI and Data Science courses?"
    )

    result = generate_explanation(test_prompt)

    if result["success"]:
        print("  [OK] Response received\n")
        bar("-", 46)
        print("  Response:")
        bar("-", 46)
        print(f"\n  {result['text']}\n")
        bar("-", 46)
    else:
        print(f"  [FAIL] Could not get a response: {result['text']}")

    bar()
    print("  OLLAMA TEST COMPLETE")
    bar()


if __name__ == "__main__":
    run_ollama_test()
