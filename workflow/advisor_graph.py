"""
advisor_graph.py
----------------
PHASE 2B + Unit III + Unit IV - LangGraph Orchestration

ORIGINAL WORKFLOW (preserved):
    START -> academic_profile -> course_analysis -> recommendation -> END

UNIT III EXTENSION:
    After recommendation: -> reflection -> END
    (Reflection Agent interprets persisted feedback and re-ranks eligible courses)

UNIT IV EXTENSION:
    After reflection (or recommendation if no feedback):
        -> acad_performance + career_skill_gap + workload_feasibility (parallel)
        -> advisory_coordinator -> END
    Specialist agents run after the core recommendation is complete.
    Their findings are synthesized by the coordinator into a final plan.

IMPORTANT:
    - The original 3-agent pipeline is NOT modified.
    - All original outputs are preserved in the final state.
    - Specialist agents use ONLY existing database data.
    - LangGraph StateGraph is the orchestration mechanism.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional, List

# ── Original 3 agents (unchanged) ────────────────────────────────────────────
from agents.academic_profile_agent  import AcademicProfileAgent
from agents.course_analysis_agent   import CourseAnalysisAgent
from agents.recommendation_agent    import RecommendationAgent

# ── Unit III: Reflection Agent ────────────────────────────────────────────────
from agents.reflection_agent        import ReflectionAgent

# ── Unit IV: Specialist Agents + Coordinator ──────────────────────────────────
from agents.academic_performance_agent  import AcademicPerformanceAgent
from agents.career_skill_gap_agent      import CareerSkillGapAgent
from agents.workload_feasibility_agent  import WorkloadFeasibilityAgent
from agents.advisory_coordinator_agent  import AdvisoryCoordinatorAgent


# =============================================================================
# SHARED STATE DEFINITION
# =============================================================================

class AdvisorState(TypedDict, total=False):
    # Input
    student_id          : str   # e.g. "S001"

    # Original pipeline outputs (unchanged)
    profile             : dict  # Agent 1 output
    course_analysis     : list  # Agent 2 output
    recommendation      : dict  # Agent 3 output

    # Unit III: Reflection
    reflection_result   : dict  # ReflectionAgent output

    # Unit IV: Specialist outputs
    performance_report  : dict  # AcademicPerformanceAgent output
    career_analysis_out : dict  # CareerSkillGapAgent output
    workload_report     : dict  # WorkloadFeasibilityAgent output

    # Unit IV: Coordinator synthesis
    coordinator_result  : dict  # AdvisoryCoordinatorAgent output


# =============================================================================
# ORIGINAL PIPELINE NODES (unchanged logic)
# =============================================================================

def academic_profile_node(state: AdvisorState) -> dict:
    """NODE 1 — Academic Profile Agent (original, unchanged)."""
    print("\n[LangGraph] Running Academic Profile Agent...")
    student_id = state["student_id"]
    agent      = AcademicProfileAgent()
    profile    = agent.run(student_id)
    return {"profile": profile}


def course_analysis_node(state: AdvisorState) -> dict:
    """NODE 2 — Course Analysis Agent (original, unchanged)."""
    print("\n[LangGraph] Running Course Analysis Agent...")
    profile = state["profile"]
    if profile.get("error"):
        print("[LangGraph] Skipping course analysis — invalid student profile.")
        return {"course_analysis": []}
    agent    = CourseAnalysisAgent()
    analysis = agent.run(profile)
    return {"course_analysis": analysis}


def recommendation_node(state: AdvisorState) -> dict:
    """NODE 3 — Recommendation Agent (original, unchanged)."""
    print("\n[LangGraph] Running Recommendation Agent...")
    profile         = state["profile"]
    course_analysis = state.get("course_analysis", [])
    if not course_analysis and profile.get("error"):
        return {
            "recommendation": {
                "error"           : True,
                "message"         : profile.get("message", "Invalid student profile."),
                "recommendations" : []
            }
        }
    agent          = RecommendationAgent()
    recommendation = agent.run(profile, course_analysis)
    return {"recommendation": recommendation}


# =============================================================================
# UNIT III: REFLECTION NODE
# =============================================================================

def reflection_node(state: AdvisorState) -> dict:
    """
    NODE 4 — Reflection Agent (Unit III)

    Reads persisted feedback from the DB and produces before/after rankings.
    NEVER modifies prerequisite eligibility.
    """
    print("\n[LangGraph] Running Reflection Agent (Unit III)...")
    student_id      = state["student_id"]
    course_analysis = state.get("course_analysis", [])

    if not course_analysis:
        return {
            "reflection_result": {
                "student_id"      : student_id,
                "feedback_applied": False,
                "original_ranking": [],
                "adjusted_ranking": [],
                "adjustments"     : [],
                "summary"         : "No course analysis available for reflection.",
            }
        }

    agent  = ReflectionAgent()
    result = agent.run(student_id, course_analysis)
    return {"reflection_result": result}


# =============================================================================
# UNIT IV: SPECIALIST NODES
# =============================================================================

def academic_performance_node(state: AdvisorState) -> dict:
    """
    NODE 5a — Academic Performance Specialist (Unit IV)
    Runs in parallel with the other two specialist nodes.
    """
    print("\n[LangGraph] Running Academic Performance Agent (Unit IV)...")
    profile = state["profile"]
    agent   = AcademicPerformanceAgent()
    result  = agent.run(profile)
    return {"performance_report": result}


def career_skill_gap_node(state: AdvisorState) -> dict:
    """
    NODE 5b — Career & Skill-Gap Specialist (Unit IV)
    Runs in parallel with the other two specialist nodes.
    """
    print("\n[LangGraph] Running Career & Skill-Gap Agent (Unit IV)...")
    profile         = state["profile"]
    course_analysis = state.get("course_analysis", [])
    agent           = CareerSkillGapAgent()
    result          = agent.run(profile, course_analysis)
    return {"career_analysis_out": result}


def workload_feasibility_node(state: AdvisorState) -> dict:
    """
    NODE 5c — Workload Feasibility Specialist (Unit IV)
    Runs after performance_report is available (uses it for GPA context).
    """
    print("\n[LangGraph] Running Workload Feasibility Agent (Unit IV)...")
    profile            = state["profile"]
    course_analysis    = state.get("course_analysis", [])
    performance_report = state.get("performance_report", {})
    agent              = WorkloadFeasibilityAgent()
    result             = agent.run(profile, course_analysis, performance_report)
    return {"workload_report": result}


def advisory_coordinator_node(state: AdvisorState) -> dict:
    """
    NODE 6 — Advisory Coordinator (Unit IV)

    Synthesizes all specialist outputs into a final academic plan.
    Integrates feedback-adjusted rankings from the Reflection Agent if available.
    """
    print("\n[LangGraph] Running Advisory Coordinator Agent (Unit IV)...")
    profile           = state["profile"]
    recommendation    = state.get("recommendation", {})
    performance_report= state.get("performance_report", {})
    career_analysis   = state.get("career_analysis_out", {})
    workload_report   = state.get("workload_report", {})
    reflection_result = state.get("reflection_result", {})

    agent  = AdvisoryCoordinatorAgent()
    result = agent.run(
        profile,
        recommendation,
        performance_report,
        career_analysis,
        workload_report,
        reflection_result,
    )
    return {"coordinator_result": result}


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def build_graph():
    """
    Builds and compiles the extended LangGraph StateGraph.

    Full graph structure:
        START
          -> academic_profile
          -> course_analysis
          -> recommendation
          -> reflection              (Unit III)
          -> academic_performance    (Unit IV specialist 1)
          -> career_skill_gap        (Unit IV specialist 2)
          -> workload_feasibility    (Unit IV specialist 3)
          -> advisory_coordinator    (Unit IV coordinator)
          -> END

    NOTE: Specialists run sequentially after reflection for simplicity
    (LangGraph parallel branching requires additional complexity not
    needed for this academic demo). academic_performance runs first
    so workload_feasibility can use the GPA estimate.
    """
    graph_builder = StateGraph(AdvisorState)

    # ── Register all nodes ─────────────────────────────────────────────────────
    graph_builder.add_node("academic_profile",     academic_profile_node)
    graph_builder.add_node("course_analysis",      course_analysis_node)
    graph_builder.add_node("recommendation",       recommendation_node)
    graph_builder.add_node("reflection",           reflection_node)          # Unit III
    graph_builder.add_node("academic_performance", academic_performance_node) # Unit IV
    graph_builder.add_node("career_skill_gap",     career_skill_gap_node)    # Unit IV
    graph_builder.add_node("workload_feasibility", workload_feasibility_node) # Unit IV
    graph_builder.add_node("advisory_coordinator", advisory_coordinator_node) # Unit IV

    # ── Connect edges (execution order) ──────────────────────────────────────
    graph_builder.add_edge(START,                  "academic_profile")
    graph_builder.add_edge("academic_profile",     "course_analysis")
    graph_builder.add_edge("course_analysis",      "recommendation")
    graph_builder.add_edge("recommendation",       "reflection")          # Unit III
    graph_builder.add_edge("reflection",           "academic_performance") # Unit IV chain
    graph_builder.add_edge("academic_performance", "career_skill_gap")
    graph_builder.add_edge("career_skill_gap",     "workload_feasibility")
    graph_builder.add_edge("workload_feasibility", "advisory_coordinator")
    graph_builder.add_edge("advisory_coordinator", END)

    compiled_graph = graph_builder.compile()
    return compiled_graph


# =============================================================================
# PUBLIC ENTRY FUNCTION
# =============================================================================

def run_advisor(student_id: str) -> dict:
    """
    Main entry point for the full LangGraph advisor workflow.

    Runs all 8 nodes and returns the complete final state.

    Args:
        student_id (str): e.g., "S001"

    Returns:
        dict: Final AdvisorState with all agent outputs
    """
    print(f"\n[LangGraph] Starting advisor workflow for student: {student_id}")

    graph         = build_graph()
    initial_state = {"student_id": student_id}
    final_state   = graph.invoke(initial_state)

    print("\n[LangGraph] Full workflow complete.")
    return final_state


# =============================================================================
# QUICK SELF-TEST
# =============================================================================

if __name__ == "__main__":
    result = run_advisor("S001")

    print("\n--- Core Recommendations ---")
    recs = result.get("recommendation", {}).get("recommendations", [])
    for r in recs:
        print(f"  Rank {r['rank']}: {r['course_name']} ({r['score']}/100)")

    print("\n--- Reflection (Unit III) ---")
    refl = result.get("reflection_result", {})
    print(f"  Feedback applied: {refl.get('feedback_applied')}")
    for c in refl.get("adjusted_ranking", [])[:3]:
        print(f"  Rank {c['rank']}: {c['course_name']} "
              f"({c.get('original_score', c['score'])} -> {c['score']})")

    print("\n--- Coordinator Summary (Unit IV) ---")
    coord = result.get("coordinator_result", {})
    print(f"  {coord.get('coordinator_summary', 'N/A')}")
    print("\n--- Reasoning Chain ---")
    for step in coord.get("reasoning_chain", []):
        print(f"  {step}")
