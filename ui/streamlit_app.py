"""
streamlit_app.py
----------------
Streamlit UI for the Student Academic Advisor Agent System
Multi-Agent Collaborative System with Feedback Adaptation (Units I-IV)

ARCHITECTURE:
    Streamlit (UI)
        |
        v
    run_advisor(student_id)  <- LangGraph 8-Node Workflow
        |
        +-> Agent 1: Academic Profile Agent
        +-> Agent 2: Course Analysis Agent (Prerequisites & Rules)
        +-> Agent 3: Recommendation Agent (Scoring & Ollama/Rule Explanations)
        +-> Agent 4: Reflection Agent (Unit III - Feedback Adaptation)
        +-> Agent 5a: Academic Performance Agent (Unit IV)
        +-> Agent 5b: Career & Skill-Gap Agent (Unit IV)
        +-> Agent 5c: Workload Feasibility Agent (Unit IV)
        +-> Agent 6: Advisory Coordinator Agent (Unit IV - Synthesis & Plan)
        |
        v
    SQLite Persistence (academic_advisor.db: preferences & recommendation_feedback)

Run with:
    streamlit run ui/streamlit_app.py
"""

import sys
import os
import time
from html import escape
from textwrap import dedent

# ── Add project root so all existing modules are importable ──────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

# ── Project imports ───────────────────────────────────────────────────────────
from database.database         import get_all_students, get_all_electives, get_connection
from database.feedback_db      import (save_feedback, get_feedback_for_student,
                                       get_feedback_for_course, FEEDBACK_TYPES,
                                       create_feedback_table)
from agents.academic_profile_agent     import AcademicProfileAgent
from agents.course_analysis_agent      import CourseAnalysisAgent
from agents.recommendation_agent       import RecommendationAgent
from agents.reflection_agent           import ReflectionAgent
from agents.academic_performance_agent import AcademicPerformanceAgent
from agents.career_skill_gap_agent     import CareerSkillGapAgent
from agents.workload_feasibility_agent import WorkloadFeasibilityAgent
from agents.advisory_coordinator_agent import AdvisoryCoordinatorAgent
from workflow.advisor_graph           import run_advisor, build_graph
from memory.preference_memory         import PreferenceMemory
from llm.ollama_client                import is_ollama_running, is_model_available, OLLAMA_MODEL


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title    = "Student Academic Advisor",
    page_icon     = "🎓",
    layout        = "wide",
    initial_sidebar_state = "expanded"
)


# =============================================================================
# DESIGN SYSTEM — PREMIUM ACADEMIC SAAS CSS
# =============================================================================

PREMIUM_DESIGN_CSS = """
<style>
/* ── Typography: Google Fonts ───────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap');

/* ── Core Design Tokens ─────────────────────────────────────── */
:root {
    --bg-canvas:     #F8F6F0;
    --bg-card:       #FFFFFF;
    --bg-sidebar:    #F1EDE4;
    --bg-subtle:     #FAF7F2;
    --bg-hover:      #F5EFE6;

    --text-primary:  #0F172A;
    --text-secondary:#475569;
    --text-muted:    #64748B;
    --text-subtle:   #94A3B8;

    --border-light:  #E8E1D5;
    --border-medium: #DDD4C6;
    --border-focus:  #8B6F4E;

    --accent-bronze: #8B6F4E;
    --accent-dark:   #6E5338;
    --accent-light:  #C4A882;
    --accent-subtle: #F7F2EB;

    --success-text:  #15803D;
    --success-bg:    #F0FDF4;
    --success-border:#BBF7D0;

    --warning-text:  #B45309;
    --warning-bg:    #FEFCE8;
    --warning-border:#FEF08A;

    --danger-text:   #B91C1C;
    --danger-bg:     #FEF2F2;
    --danger-border: #FECACA;

    --shadow-sm:     0 1px 2px rgba(15, 23, 42, 0.05);
    --shadow-md:     0 4px 12px -2px rgba(15, 23, 42, 0.08), 0 2px 6px -1px rgba(15, 23, 42, 0.04);
    --shadow-lg:     0 12px 28px -4px rgba(15, 23, 42, 0.12), 0 6px 14px -3px rgba(15, 23, 42, 0.06);
    --radius-sm:     6px;
    --radius-md:     10px;
    --radius-lg:     14px;
}

/* ── Global Styles ──────────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--bg-canvas) !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
}

/* ── Main Container ─────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] {
    max-width: 1360px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
}

/* ── Header Bar ─────────────────────────────────────────────── */
header[data-testid="stHeader"] {
    background: var(--bg-canvas) !important;
    border-bottom: 1px solid var(--border-light) !important;
}

#MainMenu, footer {
    visibility: hidden;
}

[data-testid="stSidebarCollapsedControl"] button,
header[data-testid="stHeader"] [data-testid="stBaseButton-headerNoPadding"],
[data-testid="collapsedControl"] button {
    background: var(--accent-bronze) !important;
    border: 1px solid var(--accent-dark) !important;
    border-radius: var(--radius-sm) !important;
    color: #FFFFFF !important;
}

/* ── Sidebar Styling ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-medium) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] span {
    color: var(--text-secondary) !important;
}

/* ── COMPREHENSIVE FIX FOR SELECTBOX & DROPDOWN MENUS ───────── */
/* Native select trigger */
div[data-baseweb="select"],
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1.5px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
}

div[data-baseweb="select"]:hover,
div[data-baseweb="select"]:focus-within {
    border-color: var(--accent-bronze) !important;
    box-shadow: 0 0 0 3px rgba(139, 111, 78, 0.14) !important;
}

div[data-baseweb="select"] * {
    color: var(--text-primary) !important;
    background-color: transparent !important;
}

div[data-baseweb="select"] svg {
    fill: var(--accent-bronze) !important;
    stroke: var(--accent-bronze) !important;
}

/* Floating Popover / Virtual Dropdown List (Fixes dark background issue) */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[data-testid="stSelectboxVirtualDropdown"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-lg) !important;
    z-index: 999999 !important;
    overflow: hidden !important;
}

div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] ul[role="listbox"] {
    background-color: #FFFFFF !important;
    padding: 6px !important;
    border: none !important;
}

div[data-baseweb="popover"] li,
div[data-baseweb="popover"] li[role="option"],
div[data-baseweb="popover"] div[role="option"] {
    background-color: #FFFFFF !important;
    color: var(--text-primary) !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    border-radius: var(--radius-sm) !important;
    padding: 9px 12px !important;
    margin-bottom: 2px !important;
    transition: background-color 0.15s ease, color 0.15s ease !important;
}

div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] li[aria-selected="true"],
div[data-baseweb="popover"] div[role="option"]:hover,
div[data-baseweb="popover"] div[role="option"][aria-selected="true"] {
    background-color: var(--accent-subtle) !important;
    color: var(--accent-bronze) !important;
    font-weight: 600 !important;
}

/* ── Form Inputs & Textareas ────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: #FFFFFF !important;
    border: 1.5px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-size: 0.9rem !important;
    padding: 10px 14px !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent-bronze) !important;
    box-shadow: 0 0 0 3px rgba(139, 111, 78, 0.14) !important;
    outline: none !important;
}

.stSelectbox label,
.stTextInput label,
.stTextArea label {
    color: var(--text-secondary) !important;
    font-size: 0.76rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}

/* ── Buttons ────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #8B6F4E 0%, #725638 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid #6E5338 !important;
    border-radius: var(--radius-md) !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 0.65rem 1.4rem !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 2px 5px rgba(110, 83, 56, 0.2) !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #7A6042 0%, #63492F 100%) !important;
    box-shadow: 0 5px 12px rgba(110, 83, 56, 0.28) !important;
    transform: translateY(-1px);
}

.stButton > button:active {
    transform: translateY(0);
}

/* ── Modern Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    gap: 8px !important;
    border-bottom: 2px solid var(--border-medium) !important;
    padding-bottom: 0 !important;
    margin-bottom: 1.4rem !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: var(--bg-subtle) !important;
    border: 1px solid var(--border-light) !important;
    border-bottom: none !important;
    border-radius: 8px 8px 0 0 !important;
    color: var(--text-secondary) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: #FFFFFF !important;
    color: var(--accent-bronze) !important;
}

.stTabs [aria-selected="true"] {
    background-color: #FFFFFF !important;
    color: var(--accent-bronze) !important;
    border-color: var(--accent-bronze) var(--accent-bronze) #FFFFFF var(--accent-bronze) !important;
    border-top: 3px solid var(--accent-bronze) !important;
    font-weight: 700 !important;
}

/* ── Expanders ──────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-light) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm) !important;
    margin-bottom: 1rem !important;
    overflow: hidden !important;
}

div[data-testid="stExpander"] summary {
    background-color: #FAF8F4 !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 11px 16px !important;
    border-bottom: 1px solid var(--border-light) !important;
}

div[data-testid="stExpander"] summary:hover {
    border-color: var(--accent-bronze) !important;
    background-color: var(--accent-subtle) !important;
    color: var(--accent-bronze) !important;
}

div[data-testid="stExpander"] > div[role="region"] {
    padding: 16px 18px !important;
    background-color: #FFFFFF !important;
}

/* ── Dividers ───────────────────────────────────────────────── */
hr {
    border-color: var(--border-light) !important;
    margin: 1rem 0 !important;
}

/* ── Responsive adjustments ─────────────────────────────────── */
@media (max-width: 900px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}
</style>
"""

st.markdown(PREMIUM_DESIGN_CSS, unsafe_allow_html=True)


# =============================================================================
# REUSABLE COMPONENT HELPERS
# =============================================================================

def render_html(content: str) -> None:
    """Render intentional UI markup cleanly without markdown distortion."""
    st.html(dedent(content).strip())


def display_text(text: object) -> str:
    """Escape data values safely for HTML interpolation."""
    return escape("" if text is None else str(text), quote=True)


def display_paragraph(text: object) -> str:
    """Convert multi-line text into clean readable HTML breaks."""
    return display_text(text).replace("\n", "<br>")


def card(content_html: str, padding: str = "1.25rem 1.5rem", extra_style: str = "") -> str:
    """Generates a cohesive, polished white card."""
    return dedent(f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E8E1D5;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03);
        padding: {padding};
        margin-bottom: 1rem;
        {extra_style}
    ">{content_html}</div>
    """).strip()


def label(text: str) -> str:
    """Renders a standard subtle uppercase field label."""
    return f'<span style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;color:#64748B;text-transform:uppercase;">{display_text(text)}</span>'


def value(text: str, size: str = "0.95rem") -> str:
    """Renders a standard primary data value."""
    return f'<span style="font-size:{size};font-weight:600;color:#0F172A;">{display_text(text)}</span>'


def tag(text: str, color: str = "#8B6F4E", bg: str = "#F7F2EB", border: str = "#E8DFD3") -> str:
    """Renders a modern rounded pill badge."""
    return f'<span style="display:inline-block;background:{bg};color:{color};border:1px solid {border};border-radius:6px;padding:3px 9px;font-size:0.75rem;font-weight:600;margin:2px 4px 2px 0;">{display_text(text)}</span>'


def status_dot(online: bool, text: str) -> str:
    """Renders a bulleted status indicator."""
    color = "#15803D" if online else "#94A3B8"
    dot   = "●"
    return f'<span style="color:{color};font-size:0.85rem;font-weight:600;">{dot} {display_text(text)}</span>'


def check_row(text: str, ok: bool = True) -> str:
    """Renders a clean requirement checklist row."""
    icon  = "✓" if ok else "○"
    color = "#15803D" if ok else "#94A3B8"
    return f'<div style="color:{color};font-size:0.84rem;margin:3px 0;font-weight:500;">{icon} {display_text(text)}</div>'


def section_title(text: str, size: str = "0.76rem") -> str:
    """Renders a consistent modern section heading with accent rule."""
    return f'''<div style="font-size:{size};font-weight:800;letter-spacing:0.12em;
    color:#8B6F4E;text-transform:uppercase;border-bottom:1.5px solid #E8E1D5;
    padding-bottom:5px;margin-bottom:12px;margin-top:6px;">{text}</div>'''


# =============================================================================
# SYSTEM HEALTH CHECKS
# =============================================================================

def check_database() -> bool:
    """Verify the SQLite database is accessible."""
    try:
        conn = get_connection()
        conn.execute("SELECT 1 FROM students LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False

def check_agents() -> bool:
    """Verify all three agents can be instantiated."""
    try:
        AcademicProfileAgent()
        CourseAnalysisAgent()
        RecommendationAgent()
        return True
    except Exception:
        return False

def check_langgraph() -> bool:
    """Verify the LangGraph StateGraph can be built."""
    try:
        build_graph()
        return True
    except Exception:
        return False

def check_ollama() -> tuple:
    """Returns (running: bool, model_ok: bool)."""
    try:
        running   = is_ollama_running()
        model_ok  = is_model_available(OLLAMA_MODEL) if running else False
        return running, model_ok
    except Exception:
        return False, False


# =============================================================================
# SESSION STATE INITIALISATION
# =============================================================================

def init_session():
    defaults = {
        "init_stage"      : 0,      # 0-8: init animation progress
        "show_dashboard"  : False,  # True after init completes
        "db_ok"           : False,
        "agents_ok"       : False,
        "langgraph_ok"    : False,
        "ollama_ok"       : False,
        "ollama_model_ok" : False,
        "selected_student": None,
        "profile"         : None,
        "workflow_result" : None,
        "all_students"    : [],
        "pref_type"       : "interest",
        "pref_value"      : "",
        "pref_saved_msg"  : "",
        "activity_log"    : [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# =============================================================================
# SCREEN 1 — AGENT INITIALIZATION
# =============================================================================

def show_init_screen():
    """
    Sequential initialization screen.
    Uses st.session_state.init_stage (0-8) to show cumulative progress.
    Each call to this function renders everything up to the current stage,
    then advances the stage, waits briefly, and triggers st.rerun().
    """
    stage = st.session_state.init_stage

    # ── Run the actual system check at stage 0 ────────────────────────────────
    if stage == 0:
        st.session_state.db_ok           = check_database()
        st.session_state.agents_ok       = check_agents()
        st.session_state.langgraph_ok    = check_langgraph()
        ollama_r, ollama_m               = check_ollama()
        st.session_state.ollama_ok       = ollama_r
        st.session_state.ollama_model_ok = ollama_m
        try:
            students = get_all_students()
            st.session_state.all_students = [dict(s) for s in students]
        except Exception:
            st.session_state.all_students = []

    db_ok     = st.session_state.db_ok
    agents_ok = st.session_state.agents_ok
    lg_ok     = st.session_state.langgraph_ok
    ol_ok     = st.session_state.ollama_ok
    om_ok     = st.session_state.ollama_model_ok

    # ── Layout ────────────────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 2, 1])

    with col:
        # Title
        render_html("""
        <div style="text-align:center; padding: 3rem 0 2rem 0;">
            <div style="font-family:'Playfair Display',serif; font-size:2rem;
                 font-weight:700; color:#2C241F; letter-spacing:0.04em;">
                STUDENT ACADEMIC ADVISOR
            </div>
            <div style="font-size:0.88rem; color:#75685D; margin-top:8px;
                 letter-spacing:0.06em; text-transform:uppercase;">
                Initializing intelligent advisory system
            </div>
            <div style="width:60px;height:2px;background:#8B6F4E;margin:16px auto 0;"></div>
        </div>
        """)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # ── Stage 1+: Agent 1 ONLINE ──────────────────────────────────────────
        if stage >= 1:
            color = "#4A7C59" if agents_ok else "#C0392B"
            status_text = "ONLINE" if agents_ok else "ERROR"
            render_html(card(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:0.7rem;letter-spacing:0.1em;color:#75685D;text-transform:uppercase;">Agent 1</div>
                    <div style="font-size:1rem;font-weight:600;color:#2C241F;margin-top:2px;">Academic Profile Agent</div>
                </div>
                <div style="background:{'#EBF4EE' if agents_ok else '#FDEAEA'};border:1px solid {'#4A7C59' if agents_ok else '#C0392B'};
                     border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;color:{color};">
                    ● {status_text}
                </div>
            </div>
            """, "1rem 1.4rem"))

        # ── Stage 2+: Agent 2 ONLINE ──────────────────────────────────────────
        if stage >= 2:
            color = "#4A7C59" if agents_ok else "#C0392B"
            status_text = "ONLINE" if agents_ok else "ERROR"
            render_html(card(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:0.7rem;letter-spacing:0.1em;color:#75685D;text-transform:uppercase;">Agent 2</div>
                    <div style="font-size:1rem;font-weight:600;color:#2C241F;margin-top:2px;">Course Analysis Agent</div>
                </div>
                <div style="background:{'#EBF4EE' if agents_ok else '#FDEAEA'};border:1px solid {'#4A7C59' if agents_ok else '#C0392B'};
                     border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;color:{color};">
                    ● {status_text}
                </div>
            </div>
            """, "1rem 1.4rem"))

        # ── Stage 3+: Agent 3 ONLINE ──────────────────────────────────────────
        if stage >= 3:
            color = "#4A7C59" if agents_ok else "#C0392B"
            status_text = "ONLINE" if agents_ok else "ERROR"
            render_html(card(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:0.7rem;letter-spacing:0.1em;color:#75685D;text-transform:uppercase;">Agent 3</div>
                    <div style="font-size:1rem;font-weight:600;color:#2C241F;margin-top:2px;">Recommendation Agent</div>
                </div>
                <div style="background:{'#EBF4EE' if agents_ok else '#FDEAEA'};border:1px solid {'#4A7C59' if agents_ok else '#C0392B'};
                     border-radius:20px;padding:4px 14px;font-size:0.78rem;font-weight:600;color:{color};">
                    ● {status_text}
                </div>
            </div>
            """, "1rem 1.4rem"))

        # ── Stage 4+: Connecting diagram ──────────────────────────────────────
        if stage >= 4:
            render_html("""
            <div style="text-align:center;padding:0.6rem 0;color:#A89887;font-size:0.8rem;
                 letter-spacing:0.06em;text-transform:uppercase;">
                ─ ─ ─ &nbsp; Connecting Agents &nbsp; ─ ─ ─
            </div>
            """)
            render_html(card("""
            <div style="text-align:center;font-size:0.82rem;color:#75685D;line-height:2.2;">
                Academic Profile Agent<br>
                <span style="color:#8B6F4E;font-size:1rem;">│</span><br>
                <span style="color:#8B6F4E;font-size:0.7rem;letter-spacing:0.08em;">CONNECTED</span><br>
                <span style="color:#8B6F4E;font-size:1rem;">▼</span><br>
                Course Analysis Agent<br>
                <span style="color:#8B6F4E;font-size:1rem;">│</span><br>
                <span style="color:#8B6F4E;font-size:0.7rem;letter-spacing:0.08em;">CONNECTED</span><br>
                <span style="color:#8B6F4E;font-size:1rem;">▼</span><br>
                Recommendation Agent
            </div>
            """, "1rem 1.4rem"))

        # ── Stage 5+: DB + LangGraph status ───────────────────────────────────
        if stage >= 5:
            rows_html = ""
            rows_html += check_row(f"Database Connected  ({db_ok})", db_ok)
            rows_html += check_row(f"LangGraph Connected", lg_ok)
            render_html(card(rows_html, "0.9rem 1.4rem"))

        # ── Stage 6+: Ollama status ────────────────────────────────────────────
        if stage >= 6:
            if ol_ok and om_ok:
                ollama_html  = check_row(f"Ollama Connected", True)
                ollama_html += check_row(f"{OLLAMA_MODEL} Ready", True)
            elif ol_ok and not om_ok:
                ollama_html  = check_row("Ollama Connected", True)
                ollama_html += f'<div style="color:#8B6914;font-size:0.88rem;margin:3px 0;">⚠ {OLLAMA_MODEL} not found — pull it with: ollama pull {OLLAMA_MODEL}</div>'
            else:
                ollama_html  = f'<div style="color:#8B6914;font-size:0.88rem;margin:3px 0;">⚠ Ollama unavailable — Rule-based explanation mode active</div>'
            render_html(card(ollama_html, "0.9rem 1.4rem"))

        # ── Stage 7+: ALL SYSTEMS READY ───────────────────────────────────────
        if stage >= 7:
            render_html("""
            <div style="text-align:center;padding:1.2rem 0 0.5rem 0;">
                <div style="font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;
                     color:#4A7C59;font-weight:700;">● ALL SYSTEMS READY</div>
                <div style="font-size:0.8rem;color:#A89887;margin-top:8px;">
                    Launching advisor dashboard…
                </div>
            </div>
            """)

    # ── Advance stage and rerun ────────────────────────────────────────────────
    DELAYS = [0.0, 0.5, 0.45, 0.45, 0.5, 0.4, 0.5, 0.6, 0.7]

    if stage < 7:
        delay = DELAYS[stage] if stage < len(DELAYS) else 0.4
        time.sleep(delay)
        st.session_state.init_stage += 1
        st.rerun()
    else:
        time.sleep(0.9)
        st.session_state.init_stage    += 1
        st.session_state.show_dashboard = True
        # Set default student
        if st.session_state.all_students:
            st.session_state.selected_student = st.session_state.all_students[0]["student_id"]
        st.rerun()


# =============================================================================
# SIDEBAR
# =============================================================================

def show_sidebar():
    with st.sidebar:
        # Brand
        render_html("""
        <div style="padding: 0.5rem 0 1.2rem 0;">
            <div style="font-family:'Playfair Display',serif;font-size:1.1rem;
                 font-weight:700;color:#2C241F;letter-spacing:0.02em;">
                🎓 Academic Advisor
            </div>
            <div style="font-size:0.72rem;color:#A89887;letter-spacing:0.06em;
                 text-transform:uppercase;margin-top:3px;">
                AI-Powered Advisory System
            </div>
        </div>
        """)

        st.markdown('<hr style="border-color:#DED5C8;margin:0 0 1rem 0;">', unsafe_allow_html=True)

        # System status
        st.markdown(section_title("System Status"), unsafe_allow_html=True)

        db_ok  = st.session_state.db_ok
        lg_ok  = st.session_state.langgraph_ok
        ol_ok  = st.session_state.ollama_ok
        om_ok  = st.session_state.ollama_model_ok

        render_html(f"""
        <div style="font-size:0.85rem;line-height:2.1;">
            {status_dot(db_ok,  "Database")}  <span style="color:#A89887;font-size:0.75rem;">SQLite</span><br>
            {status_dot(lg_ok,  "LangGraph")} <span style="color:#A89887;font-size:0.75rem;">StateGraph</span><br>
            {status_dot(ol_ok,  "Ollama")}    <span style="color:#A89887;font-size:0.75rem;">{OLLAMA_MODEL if om_ok else "unavailable"}</span>
        </div>
        """)

        st.markdown('<hr style="border-color:#DED5C8;margin:1rem 0;">', unsafe_allow_html=True)

        # Agents
        st.markdown(section_title("Agents"), unsafe_allow_html=True)
        agents_ok = st.session_state.agents_ok
        render_html(f"""
        <div style="font-size:0.85rem;line-height:2.1;">
            {status_dot(agents_ok, "Academic Profile Agent")}<br>
            {status_dot(agents_ok, "Course Analysis Agent")}<br>
            {status_dot(agents_ok, "Recommendation Agent")}
        </div>
        """)

        if not st.session_state.ollama_ok:
            st.markdown('<hr style="border-color:#DED5C8;margin:1rem 0;">', unsafe_allow_html=True)
            render_html(f"""
            <div style="background:#FDF6E3;border:1px solid #DED5C8;border-radius:6px;
                 padding:0.7rem;font-size:0.78rem;color:#8B6914;">
                ⚠ Ollama offline<br>
                <span style="color:#A89887;">Using rule-based explanations</span>
            </div>
            """)

        st.markdown('<hr style="border-color:#DED5C8;margin:1rem 0;">', unsafe_allow_html=True)
        st.markdown(section_title("Architecture"), unsafe_allow_html=True)
        render_html("""
        <div style="font-size:0.78rem;color:#75685D;line-height:2;">
            Streamlit UI<br>
            <span style="color:#DED5C8;">  ↓</span><br>
            LangGraph<br>
            <span style="color:#DED5C8;">  ↓</span><br>
            Agent 1 → Agent 2 → Agent 3<br>
            <span style="color:#DED5C8;">  ↓</span><br>
            Ollama (explanations)<br>
            <span style="color:#DED5C8;">  ↓</span><br>
            PreferenceMemory (SQLite)
        </div>
        """)


# =============================================================================
# STUDENT PROFILE PANEL
# =============================================================================

def show_student_profile(profile: dict):
    """Renders the student academic profile card."""

    st.markdown(section_title("Student Profile"), unsafe_allow_html=True)

    render_html(card(f"""
    <div style="margin-bottom:0.8rem;">
        <div style="font-family:'Playfair Display',serif;font-size:1.4rem;
             font-weight:700;color:#2C241F;">{display_text(profile['name'])}</div>
        <div style="font-size:0.82rem;color:#75685D;margin-top:3px;">
             {display_text(profile['program'])} &nbsp;·&nbsp; Semester {display_text(profile['semester'])}
        </div>
    </div>
    <hr style="border-color:#DED5C8;margin:0.8rem 0;">
    <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;
         color:#A89887;text-transform:uppercase;margin-bottom:6px;">Completed Subjects</div>
    <div>{''.join(tag(s) for s in profile['completed_subjects'])}</div>
    """))

    c1, c2 = st.columns(2)

    with c1:
        interests_html = "".join(tag(i) for i in profile["interests"]) if profile["interests"] else '<span style="color:#A89887;font-size:0.85rem;">Not specified</span>'
        render_html(card(f"""
        {label("Interests")}<br><div style="margin-top:5px;">{interests_html}</div>
        """, "1rem 1.2rem"))

        render_html(card(f"""
        {label("Career Goal")}<br>
        <div style="margin-top:5px;">{value(profile['career_goal'])}</div>
        """, "1rem 1.2rem"))

    with c2:
        render_html(card(f"""
        {label("Preferred Domain")}<br>
        <div style="margin-top:5px;">{value(profile['preferred_domain'])}</div>
        """, "1rem 1.2rem"))

        render_html(card(f"""
        {label("Difficulty Preference")}<br>
        <div style="margin-top:5px;">
            {value(profile['difficulty_preference'])}
            &nbsp;&nbsp;
            {label("Style")} &nbsp;{value(profile['learning_style'])}
        </div>
        """, "1rem 1.2rem"))


# =============================================================================
# AGENT ACTIVITY LOG
# =============================================================================

def show_agent_activity(result: dict, profile: dict, analysis: list):
    """Shows only high-level workflow completion status after a run."""

    st.markdown(f"<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(section_title("Agent Activity"), unsafe_allow_html=True)

    llm_used = result.get("llm_used", False)

    rows = [
        ("Academic Profile Agent",  True, "Profile retrieved"),
        ("Course Analysis Agent",   True, "Electives analyzed"),
        ("Recommendation Agent",    True, "Top 3 selected"),
        ("Ollama",
         True,
         "Explanation generated" if llm_used else "Rule-based explanation mode active"),
    ]

    rows_html = ""
    for agent_name, ok, detail in rows:
        icon  = "✓" if ok else "✗"
        color = "#4A7C59" if ok else "#C0392B"
        rows_html += f"""
        <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;">
            <span style="color:{color};font-size:0.95rem;font-weight:700;flex-shrink:0;">{icon}</span>
            <div>
                <div style="font-size:0.88rem;font-weight:600;color:#2C241F;">{display_text(agent_name)}</div>
                <div style="font-size:0.78rem;color:#75685D;">{display_text(detail)}</div>
            </div>
        </div>
        """

    render_html(card(rows_html, "1rem 1.4rem"))


# =============================================================================
# RECOMMENDATION CARDS
# =============================================================================

def show_recommendations(recs: list, analysis: list):
    """Renders Top 3 recommendation cards."""

    if not recs:
        render_html(card("""
        <div style="text-align:center;padding:1rem;color:#75685D;font-size:0.9rem;">
            No eligible electives found. Complete more prerequisite subjects.
        </div>
        """))
        return

    st.markdown(f"<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(section_title("Recommended For You"), unsafe_allow_html=True)

    # Build a lookup dict for analysis data by course_id
    analysis_lookup = {c["course_id"]: c for c in analysis}

    # Load elective metadata from DB for skills and career paths
    try:
        all_electives = get_all_electives()
        elective_meta = {e["course_id"]: dict(e) for e in all_electives}
    except Exception:
        elective_meta = {}

    rank_labels = ["01", "02", "03"]
    score_colors = {
        range(80, 101): "#4A7C59",
        range(60, 80) : "#8B6914",
        range(0,  60) : "#8B4E3A",
    }

    def score_color(s):
        for r, c in score_colors.items():
            if s in r:
                return c
        return "#75685D"

    for rec in recs:
        course_id   = rec["course_id"]
        course_name = rec["course_name"]
        domain      = rec["domain"]
        difficulty  = rec["difficulty"]
        score       = rec["score"]
        explanation = rec["explanation"]
        reasons     = rec.get("reasons", [])
        src         = rec.get("explanation_source", "rule-based")
        rank_label  = rank_labels[rec["rank"] - 1] if rec["rank"] <= 3 else str(rec["rank"])
        sc          = score_color(score)

        # Get skills and career paths from elective metadata
        meta       = elective_meta.get(course_id, {})
        skills_str = meta.get("skills", "")
        careers_str = meta.get("career_paths", "")
        desc_str   = meta.get("description", "")
        prereq_str = meta.get("prerequisites", "")

        skills_tags  = "".join(tag(s.strip()) for s in skills_str.split(",") if s.strip()) if skills_str else ""
        career_tags  = "".join(tag(s.strip(), "#4A7C59") for s in careers_str.split(",") if s.strip()) if careers_str else ""
        prereq_tags  = "".join(tag(s.strip(), "#A89887") for s in prereq_str.split(",") if s.strip()) if prereq_str else ""

        # Determine alignment flags from Agent 2 reasons
        has_interest = any("domain" in r.lower() or "interest" in r.lower() for r in reasons)
        has_career   = any("career" in r.lower() for r in reasons)
        has_prereq   = any("foundation" in r.lower() or "prerequisites met" in r.lower() for r in reasons)
        has_pref     = any("difficulty" in r.lower() or "learning" in r.lower() for r in reasons)

        # Explanation label
        exp_label = f'<span style="font-size:0.7rem;color:#A89887;background:#F2EBE0;border:1px solid #DED5C8;border-radius:3px;padding:1px 6px;margin-left:6px;">{"LLM" if src == "llm" else "Rule-based"}</span>'

        card_html = f"""
        <div class="recommendation-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.8rem;">
            <div>
                <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.14em;color:#A89887;text-transform:uppercase;">
                    {rank_label}
                </div>
                <div style="font-family:'Playfair Display',serif;font-size:1.3rem;font-weight:700;
                     color:#2C241F;margin-top:2px;">{display_text(course_name)}</div>
                <div style="font-size:0.8rem;color:#75685D;margin-top:3px;">
                    {display_text(domain)} &nbsp;·&nbsp; {display_text(difficulty)}
                </div>
            </div>
            <div class="recommendation-score" style="text-align:right;">
                <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;color:{sc};">{score}</div>
                <div style="font-size:0.65rem;letter-spacing:0.1em;text-transform:uppercase;color:#A89887;">/ 100 Match</div>
            </div>
        </div>
        <hr style="border-color:#DED5C8;margin:0.8rem 0;">

        <div style="margin-bottom:0.8rem;">
            <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.1em;color:#75685D;
                 text-transform:uppercase;margin-bottom:5px;">Why this course? {exp_label}</div>
            <div style="font-size:0.86rem;color:#2C241F;line-height:1.6;">{display_paragraph(explanation)}</div>
        </div>

        <div class="recommendation-meta" style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:0.8rem;">
            {check_row("Prerequisites satisfied", has_prereq)}
            {check_row("Interest alignment", has_interest)}
            {check_row("Career relevance", has_career)}
            {check_row("Difficulty match", has_pref)}
        </div>
        """

        if prereq_tags:
            card_html += f'<div style="margin-bottom:0.5rem;">{label("Prerequisites")} <div style="margin-top:4px;">{prereq_tags}</div></div>'
        if skills_tags:
            card_html += f'<div style="margin-bottom:0.5rem;">{label("Skills Gained")} <div style="margin-top:4px;">{skills_tags}</div></div>'
        if career_tags:
            card_html += f'<div>{label("Career Paths")} <div style="margin-top:4px;">{career_tags}</div></div>'

        card_html += "</div>"
        render_html(card(card_html, "1.2rem 1.4rem"))


# =============================================================================
# PREFERENCES SECTION
# =============================================================================

def show_preferences_section(student_id: str):
    """Renders the student memory/preferences panel."""

    st.markdown(f"<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown(section_title("Your Preferences"), unsafe_allow_html=True)

    memory = PreferenceMemory()
    result = memory.get_preferences(student_id)
    prefs  = result.get("preferences", [])

    PREF_TYPE_LABELS = {
        "interest"             : "Interest",
        "career_goal"          : "Career Goal",
        "learning_style"       : "Learning Style",
        "preferred_domain"     : "Preferred Domain",
        "difficulty_preference": "Difficulty Preference",
        "course_format"        : "Course Format",
    }

    if prefs:
        pref_html = ""
        for p in prefs:
            ptype  = p["preference_type"]
            pval   = p["preference_value"]
            plabel = PREF_TYPE_LABELS.get(ptype, ptype.replace("_", " ").title())
            pref_html += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:6px 0;border-bottom:1px solid #F0E8DC;">
                <span style="font-size:0.78rem;color:#75685D;font-weight:500;">{plabel}</span>
                 <span style="font-size:0.88rem;font-weight:600;color:#2C241F;">{display_text(pval)}</span>
            </div>
            """
        render_html(card(pref_html, "0.8rem 1.2rem"))
    else:
        render_html(card("""
        <div style="color:#A89887;font-size:0.85rem;text-align:center;padding:0.5rem 0;">
            No preferences stored yet.
        </div>
        """, "0.8rem 1.2rem"))

    # ── Add preference form ───────────────────────────────────────────────────
    with st.expander("＋ Add / Update Preference", expanded=False):
        pref_type_options = {
            "Interest"             : "interest",
            "Career Goal"          : "career_goal",
            "Learning Style"       : "learning_style",
            "Preferred Domain"     : "preferred_domain",
            "Difficulty Preference": "difficulty_preference",
            "Course Format"        : "course_format",
        }

        selected_label = st.selectbox(
            "Preference Type",
            options = list(pref_type_options.keys()),
            key     = "pref_type_select"
        )
        pref_value = st.text_input(
            "Preference Value",
            placeholder = "e.g. Project-based, AI Engineer, Hard…",
            key         = "pref_value_input"
        )

        if st.button("Save Preference", key="save_pref_btn"):
            if pref_value.strip():
                pref_type_key = pref_type_options[selected_label]
                r = memory.save_preference(student_id, pref_type_key, pref_value.strip())
                if r["success"]:
                    action = r.get("action", "saved")
                    st.session_state.pref_saved_msg = f"✓ Preference {action}: {selected_label} → {pref_value}"
                    # Reload profile to reflect the new preference
                    agent = AcademicProfileAgent()
                    st.session_state.profile = agent.run(student_id)
                    st.rerun()
                else:
                    st.error(r.get("message", "Could not save preference."))
            else:
                st.warning("Please enter a preference value.")

    if st.session_state.pref_saved_msg:
        render_html(f"""
        <div style="background:#EBF4EE;border:1px solid #4A7C59;border-radius:6px;
             padding:0.5rem 0.9rem;font-size:0.85rem;color:#4A7C59;margin-top:0.5rem;">
            {display_text(st.session_state.pref_saved_msg)}
        </div>
        """)
        # Also show USED FROM MEMORY note if we have a result
        if st.session_state.workflow_result:
            render_html("""
            <div style="background:#F2EBE0;border:1px solid #DED5C8;border-radius:6px;
                 padding:0.4rem 0.9rem;font-size:0.78rem;color:#8B6F4E;margin-top:4px;">
                📌 USED FROM MEMORY — preferences will influence the next recommendation run
            </div>
            """)


# =============================================================================
# MAIN DASHBOARD
# =============================================================================

def show_main_dashboard():
    """Renders the presentation-ready student advisor dashboard."""
    show_sidebar()

    # ── Header ────────────────────────────────────────────────────────────────
    render_html("""
    <div style="padding: 0.8rem 0 1rem 0;">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;">
            <div>
                <div style="display:inline-block;background:#F7F2EB;color:#8B6F4E;border:1px solid #E8DFD3;
                     border-radius:16px;padding:3px 12px;font-size:0.72rem;font-weight:700;letter-spacing:0.08em;
                     text-transform:uppercase;margin-bottom:8px;">Academic Advising Portal</div>
                <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;color:#0F172A;letter-spacing:0.01em;">
                    Student Academic Advisor
                </div>
                <div style="font-size:0.86rem;color:#475569;margin-top:3px;">
                    Personalized elective planning powered by LangGraph 8-Agent collaboration and feedback adaptation.
                </div>
            </div>
            <div style="text-align:right;">
                <span style="font-size:0.76rem;color:#15803D;font-weight:700;letter-spacing:0.06em;
                     background:#F0FDF4;border:1px solid #BBF7D0;border-radius:20px;padding:5px 14px;display:inline-block;">
                    ● SYSTEM ACTIVE & READY
                </span>
            </div>
        </div>
        <div style="height:2px;background:linear-gradient(to right, #8B6F4E, #DDD4C6, transparent);margin-top:12px;margin-bottom:0.8rem;"></div>
    </div>
    """)

    # ── Student Selector & Advisor Action Bar ─────────────────────────────────
    students      = st.session_state.all_students
    student_ids   = [s["student_id"] for s in students]
    student_names = [f"{s['student_id']}  —  {s['name']} ({s['program']})" for s in students]

    if not student_ids:
        st.error("No students found in the database. Please run main.py to seed the database.")
        return

    # Modern Action Card for Student Selection + Prompt
    hero_col_sel, hero_col_act = st.columns([7, 5], gap="medium")

    with hero_col_sel:
        selected_idx = st.selectbox(
            "Active Student Profile",
            options  = range(len(student_ids)),
            format_func = lambda i: student_names[i],
            key      = "student_selector",
            index    = student_ids.index(st.session_state.selected_student)
                       if st.session_state.selected_student in student_ids else 0
        )
        new_id = student_ids[selected_idx]
        if new_id != st.session_state.selected_student:
            st.session_state.selected_student = new_id
            st.session_state.profile          = None
            st.session_state.workflow_result  = None
            st.session_state.pref_saved_msg   = ""
            st.session_state.feedback_saved_msg = ""
            st.rerun()

    # Load profile when student is selected
    if st.session_state.profile is None or \
       st.session_state.profile.get("student_id") != st.session_state.selected_student:
        with st.spinner("Loading student profile…"):
            agent = AcademicProfileAgent()
            st.session_state.profile = agent.run(st.session_state.selected_student)

    profile = st.session_state.profile
    if profile.get("error"):
        st.error(f"Could not load profile: {profile.get('message')}")
        return

    with hero_col_act:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        run_btn = st.button("🎯  Run Academic Advisory Pipeline", key="run_btn", use_container_width=True)

    # Optional prompt/query
    with st.expander("💬 Optional Advisor Query / Custom Question", expanded=False):
        query = st.text_input(
            label       = "Your question for the advisor",
            placeholder = "e.g. Recommend electives focused on machine learning that match my career goal",
            key         = "advisor_query"
        )

    if run_btn:
        st.session_state.pref_saved_msg     = ""
        st.session_state.feedback_saved_msg = ""
        with st.spinner("Executing 8-Agent Collaborative Workflow…"):
            try:
                final_state = run_advisor(st.session_state.selected_student)
                st.session_state.workflow_result = final_state
                if not final_state.get("profile", {}).get("error"):
                    st.session_state.profile = final_state["profile"]
            except Exception as e:
                st.error(f"Workflow error: {str(e)}")
                st.session_state.workflow_result = None

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Display Agent Activity Pipeline if workflow has run ───────────────────
    if st.session_state.workflow_result:
        wr       = st.session_state.workflow_result
        analysis = wr.get("course_analysis", [])
        rec_data = wr.get("recommendation", {})
        recs     = rec_data.get("recommendations", [])
        p        = wr.get("profile", profile)

        st.markdown(section_title("Multi-Agent Collaborative Pipeline (8 Agents Active)"), unsafe_allow_html=True)
        show_agent_activity(rec_data, p, analysis, wr)

    # ── Dashboard Tabs ────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Recommended Plan",
        "🔬 Specialist Findings (Unit IV)",
        "🔄 Feedback & Reflection (Unit III)",
        "👤 Profile & Preferences"
    ])

    with tab1:
        if st.session_state.workflow_result:
            wr       = st.session_state.workflow_result
            analysis = wr.get("course_analysis", [])
            rec_data = wr.get("recommendation", {})
            recs     = rec_data.get("recommendations", [])

            if rec_data.get("no_results"):
                render_html(card(f"""
                <div style="color:#64748B;font-size:0.9rem;text-align:center;padding:1.5rem;">
                    {display_text(rec_data.get('message', 'No eligible courses found.'))}
                </div>
                """))
            elif rec_data.get("error"):
                st.error(rec_data.get("message", "An error occurred during recommendation generation."))
            else:
                # Coordinator Synthesis at top of recommended plan
                show_coordinator_section(
                    wr.get("coordinator_result", {}),
                    wr.get("reflection_result", {})
                )

                st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                st.markdown(section_title("Top Recommended Electives with Detailed Rationale"), unsafe_allow_html=True)
                show_recommendations(recs, analysis)
        else:
            render_html(card("""
            <div style="text-align:center;padding:2rem 1rem;">
                <div style="font-size:2.2rem;margin-bottom:8px;">🎯</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.3rem;font-weight:700;color:#0F172A;">
                    Advisory Recommendations Ready to Generate
                </div>
                <div style="font-size:0.86rem;color:#64748B;max-width:540px;margin:8px auto 16px auto;line-height:1.6;">
                    Click <strong>'Run Academic Advisory Pipeline'</strong> above to trigger the 8-agent LangGraph workflow,
                    generate course rankings, verify prerequisites, and evaluate specialist findings.
                </div>
            </div>
            """))

    with tab2:
        if st.session_state.workflow_result:
            show_specialist_findings(st.session_state.workflow_result)
        else:
            render_html(card("""
            <div style="text-align:center;padding:2rem 1rem;color:#64748B;font-size:0.88rem;">
                Specialist findings will be displayed once the advisory pipeline runs.
            </div>
            """))

    with tab3:
        if st.session_state.workflow_result:
            wr   = st.session_state.workflow_result
            recs = wr.get("recommendation", {}).get("recommendations", [])
            show_feedback_section(st.session_state.selected_student, recs)
            show_reflection_section(wr.get("reflection_result", {}))
        else:
            render_html(card("""
            <div style="text-align:center;padding:2rem 1rem;color:#64748B;font-size:0.88rem;">
                Run the advisory pipeline to unlock the feedback submission and score adjustment reflection loop.
            </div>
            """))

    with tab4:
        col_prof, col_pref = st.columns([6, 6], gap="large")
        with col_prof:
            st.markdown(section_title("Student Profile Breakdown"), unsafe_allow_html=True)
            show_student_profile(profile)

        with col_pref:
            show_preferences_section(st.session_state.selected_student)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    init_session()

    if not st.session_state.show_dashboard:
        show_init_screen()
    else:
        show_main_dashboard()


if __name__ == "__main__":
    main()
