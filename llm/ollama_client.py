"""
ollama_client.py
----------------
Simple Ollama client for the Student Academic Advisor system.

This module is the ONLY place in the project that talks to Ollama.

Responsibilities:
    - Define the model name in one place (easy to change later)
    - Provide a single generate_explanation(prompt) function
    - Handle ALL connection and model errors gracefully
    - NEVER crash the rest of the application

IMPORTANT ARCHITECTURE NOTE:
    Ollama is used ONLY to generate natural-language explanations.
    It does NOT make any decisions about:
        - Which student is eligible for what course
        - Prerequisite checking
        - Scoring or ranking
        - Top 3 selection

    All of those decisions are made by deterministic Python logic
    in Agents 1, 2, and 3. Ollama is the very last step — purely
    for generating a human-friendly explanation of already-decided results.
"""

import ollama   # Official Ollama Python library (pip install ollama)


# =============================================================================
# CONFIGURATION — Change the model name here and nowhere else
# =============================================================================

OLLAMA_MODEL = "qwen2.5:3b"  # The local model we pulled with: ollama pull qwen2.5:3b


# =============================================================================
# MAIN FUNCTION: generate_explanation
# =============================================================================

def generate_explanation(prompt: str) -> dict:
    """
    Sends a prompt to the local Ollama model and returns the response.

    This function uses a try/except block to catch ANY error from Ollama
    (connection refused, model not found, timeout, etc.) and returns a
    fallback dict instead of crashing.

    Args:
        prompt (str): The full prompt to send to the model.

    Returns:
        dict with two keys:
            {
                "success"  : True / False
                "text"     : The LLM response text, OR an error message
            }

    Usage:
        result = generate_explanation("Explain why NLP suits this student...")
        if result["success"]:
            print(result["text"])
        else:
            print("Fallback:", result["text"])
    """
    try:
        # ollama.chat() sends a message to the running Ollama server.
        # It works like a chat API — we send a list of messages.
        # "role": "user" means this is the human's turn in the conversation.
        response = ollama.chat(
            model    = OLLAMA_MODEL,
            messages = [
                {
                    "role"   : "user",
                    "content": prompt
                }
            ]
        )

        # Extract the text from the response
        # response["message"]["content"] contains the model's reply
        generated_text = response["message"]["content"].strip()

        return {
            "success": True,
            "text"   : generated_text
        }

    except ollama.ResponseError as e:
        # This happens when the model name is wrong or model isn't pulled
        error_msg = f"Ollama model error: {str(e)}"
        print(f"[OllamaClient] ERROR - {error_msg}")
        return {
            "success": False,
            "text"   : "LLM explanation unavailable. Showing rule-based explanation."
        }

    except ConnectionError as e:
        # This happens when Ollama server is not running at all
        error_msg = f"Cannot connect to Ollama: {str(e)}"
        print(f"[OllamaClient] ERROR - {error_msg}")
        return {
            "success": False,
            "text"   : "LLM explanation unavailable. Showing rule-based explanation."
        }

    except Exception as e:
        # Catch-all for any other unexpected error
        # We never want Ollama issues to crash the recommendation system
        error_msg = f"Unexpected Ollama error: {str(e)}"
        print(f"[OllamaClient] ERROR - {error_msg}")
        return {
            "success": False,
            "text"   : "LLM explanation unavailable. Showing rule-based explanation."
        }


# =============================================================================
# CHECK FUNCTIONS — Used by the test script
# =============================================================================

def is_ollama_running() -> bool:
    """
    Checks whether the Ollama server is currently running.

    Returns:
        True if Ollama responds, False otherwise
    """
    try:
        # ollama.list() returns the list of available local models.
        # If this call succeeds, Ollama is running.
        ollama.list()
        return True
    except Exception:
        return False


def is_model_available(model_name: str = OLLAMA_MODEL) -> bool:
    """
    Checks whether a specific model is available locally.

    Args:
        model_name (str): The model to check (default: OLLAMA_MODEL)

    Returns:
        True if the model is found in the local list, False otherwise
    """
    try:
        models_response = ollama.list()
        # The response contains a list of model objects
        # Each model has a 'model' key with the full model name
        available_models = [m.model for m in models_response.models]
        return model_name in available_models
    except Exception:
        return False


# =============================================================================
# QUICK SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print(f"Ollama model configured: {OLLAMA_MODEL}")
    print(f"Ollama running         : {is_ollama_running()}")
    print(f"Model available        : {is_model_available()}")

    if is_ollama_running() and is_model_available():
        result = generate_explanation(
            "In one sentence, why is Machine Learning important for AI students?"
        )
        print(f"Response: {result['text']}")
    else:
        print("Ollama not available for self-test.")
