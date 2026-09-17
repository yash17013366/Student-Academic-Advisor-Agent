"""
advisor_graph.py
----------------
PHASE 2B - LangGraph Orchestration

This file wires the three existing agents into a sequential
LangGraph workflow using a StateGraph.

WHAT LANGGRAPH DOES HERE:
    - Manages the shared state (data) that flows between agents
    - Executes the agents in order: Agent 1 -> Agent 2 -> Agent 3
    - Ensures each node only runs after the previous one completes

THE AGENTS ARE NOT CHANGED.
The agents still contain all their own logic.
LangGraph only calls them and passes results through the state.

WORKFLOW:
    START
      |
      v
    [Node 1] academic_profile_node   --> calls AcademicProfileAgent
      |
      v
    [Node 2] course_analysis_node    --> calls CourseAnalysisAgent
      |
      v
    [Node 3] recommendation_node     --> calls RecommendationAgent
      |
      v
    END
"""

import sys
import os

# Add project root to path so we can import agents and database modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── LangGraph imports ──────────────────────────────────────────────────────────
# StateGraph  : The main class for building a graph of nodes
# START, END  : Special markers for the beginning and end of the graph
from langgraph.graph import StateGraph, START, END

# ── TypedDict: defines the shape of the shared state object ───────────────────
# TypedDict is a standard Python type hint tool — no extra library needed
from typing import TypedDict

# ── Import our three existing agents ──────────────────────────────────────────
# These agents are NOT modified — LangGraph simply calls them
from agents.academic_profile_agent import AcademicProfileAgent
from agents.course_analysis_agent  import CourseAnalysisAgent
from agents.recommendation_agent   import RecommendationAgent


# =============================================================================
# STEP 1: DEFINE THE SHARED STATE
# =============================================================================
#
# AdvisorState is a TypedDict — think of it as a structured dictionary
# that gets passed through every node in the graph.
#
# Each node can READ from this state and WRITE new values into it.
#
# Fields:
#   student_id      : The ID entered by the user (e.g., "S001")
#   profile         : Set by Node 1 — the student's academic profile dict
#   course_analysis : Set by Node 2 — list of analyzed courses with scores
#   recommendation  : Set by Node 3 — final Top 3 recommendations dict
#
# total=False means all fields are optional (safe for partial state updates)
# ─────────────────────────────────────────────────────────────────────────────

class AdvisorState(TypedDict, total=False):
    student_id      : str   # Input: provided before the graph starts
    profile         : dict  # Output of Node 1 (Agent 1)
    course_analysis : list  # Output of Node 2 (Agent 2)
    recommendation  : dict  # Output of Node 3 (Agent 3)


# =============================================================================
# STEP 2: DEFINE THE THREE GRAPH NODES
# =============================================================================
#
# Each node is a simple Python function that:
#   - Receives the current state (a dictionary)
#   - Does some work (calls an agent)
#   - Returns a dictionary of new/updated state values
#
# LangGraph merges the returned dictionary into the existing state automatically.
# ─────────────────────────────────────────────────────────────────────────────


def academic_profile_node(state: AdvisorState) -> dict:
    """
    NODE 1 — Academic Profile Node

    What it does:
        - Reads the student_id from the shared state
        - Creates an AcademicProfileAgent and calls its run() method
        - Returns the profile dict to be stored in state["profile"]

    Input from state : state["student_id"]
    Output to state  : {"profile": <profile dict>}
    """
    print("\n[LangGraph] Running Academic Profile Agent...")

    # Read the student_id that was set when the graph was invoked
    student_id = state["student_id"]

    # Create the agent and run it
    agent   = AcademicProfileAgent()
    profile = agent.run(student_id)

    # Return only the new data — LangGraph merges this into the state
    return {"profile": profile}


def course_analysis_node(state: AdvisorState) -> dict:
    """
    NODE 2 — Course Analysis Node

    What it does:
        - Reads the student profile from state["profile"]
        - Creates a CourseAnalysisAgent and calls its run() method
        - Returns the analysis list to be stored in state["course_analysis"]

    Input from state : state["profile"]
    Output to state  : {"course_analysis": <list of course results>}
    """
    print("\n[LangGraph] Running Course Analysis Agent...")

    # Read the profile that Node 1 stored in the state
    profile = state["profile"]

    # If Node 1 returned an error, propagate it gracefully
    if profile.get("error"):
        print("[LangGraph] Skipping course analysis — invalid student profile.")
        return {"course_analysis": []}

    # Create the agent and run it
    agent    = CourseAnalysisAgent()
    analysis = agent.run(profile)

    # Return the analysis list to be stored in state
    return {"course_analysis": analysis}


def recommendation_node(state: AdvisorState) -> dict:
    """
    NODE 3 — Recommendation Node

    What it does:
        - Reads state["profile"] and state["course_analysis"]
        - Creates a RecommendationAgent and calls its run() method
        - Returns the recommendation dict to be stored in state["recommendation"]

    Input from state : state["profile"], state["course_analysis"]
    Output to state  : {"recommendation": <recommendation dict>}
    """
    print("\n[LangGraph] Running Recommendation Agent...")

    # Read both pieces of data that previous nodes stored in the state
    profile         = state["profile"]
    course_analysis = state.get("course_analysis", [])

    # If no eligible courses were analyzed, handle gracefully
    if not course_analysis and profile.get("error"):
        return {
            "recommendation": {
                "error"           : True,
                "message"         : profile.get("message", "Invalid student profile."),
                "recommendations" : []
            }
        }

    # Create the agent and run it with both profile and analysis
    agent          = RecommendationAgent()
    recommendation = agent.run(profile, course_analysis)

    # Return the recommendation dict to be stored in state
    return {"recommendation": recommendation}


# =============================================================================
# STEP 3: BUILD AND COMPILE THE GRAPH
# =============================================================================
#
# Here we wire the nodes together into a directed graph.
#
# StateGraph(AdvisorState) creates a graph that uses AdvisorState as its state.
#
# add_node()  : Registers a node (function) with a name in the graph
# add_edge()  : Draws an arrow from one node to another (defines the order)
# compile()   : Locks the graph and makes it ready to run
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    """
    Builds and compiles the LangGraph StateGraph.

    Graph structure:
        START -> academic_profile -> course_analysis -> recommendation -> END

    Returns:
        CompiledGraph: The compiled, runnable LangGraph graph
    """

    # Create the state graph — it will use AdvisorState as the shared state
    graph_builder = StateGraph(AdvisorState)

    # ── Register the three nodes ──────────────────────────────────────────────
    # Each node is given a name and linked to its function
    graph_builder.add_node("academic_profile", academic_profile_node)
    graph_builder.add_node("course_analysis",  course_analysis_node)
    graph_builder.add_node("recommendation",   recommendation_node)

    # ── Connect nodes with edges (defines execution order) ────────────────────
    # START -> academic_profile -> course_analysis -> recommendation -> END
    graph_builder.add_edge(START,              "academic_profile")
    graph_builder.add_edge("academic_profile", "course_analysis")
    graph_builder.add_edge("course_analysis",  "recommendation")
    graph_builder.add_edge("recommendation",   END)

    # ── Compile the graph ─────────────────────────────────────────────────────
    # compile() validates the graph and makes it runnable
    compiled_graph = graph_builder.compile()

    return compiled_graph


# =============================================================================
# STEP 4: PUBLIC ENTRY FUNCTION
# =============================================================================

def run_advisor(student_id: str) -> dict:
    """
    Main entry point for the LangGraph advisor workflow.

    Initializes the state with the student_id, runs the full graph,
    and returns the final state containing all results.

    Args:
        student_id (str): The ID of the student, e.g., "S001"

    Returns:
        dict: The final AdvisorState containing:
              - profile         (from Agent 1)
              - course_analysis (from Agent 2)
              - recommendation  (from Agent 3)
    """
    print(f"\n[LangGraph] Starting advisor workflow for student: {student_id}")

    # Build the compiled graph
    graph = build_graph()

    # The initial state only has student_id — the rest is filled by the nodes
    initial_state = {
        "student_id": student_id
    }

    # Invoke the graph — LangGraph runs all nodes in sequence
    # The final state is returned after all nodes have completed
    final_state = graph.invoke(initial_state)

    print("\n[LangGraph] Workflow complete.")
    return final_state


# =============================================================================
# QUICK SELF-TEST (run this file directly)
# =============================================================================

if __name__ == "__main__":
    result = run_advisor("S001")

    recommendation = result.get("recommendation", {})
    recs = recommendation.get("recommendations", [])

    print("\n--- Quick Test Results ---")
    print(f"Student: {result.get('profile', {}).get('name', 'Unknown')}")
    print(f"Recommendations: {len(recs)}")
    for rec in recs:
        print(f"  Rank {rec['rank']}: {rec['course_name']} ({rec['score']}/100)")
