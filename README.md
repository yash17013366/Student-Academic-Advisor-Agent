# 🎓 Student Academic Advisor Agent

An intelligent, multi-agent academic advisory system that provides personalized, prerequisite-verified elective course recommendations for university students using **LangGraph**, **SQLite**, **Local Ollama LLM (`qwen2.5:3b`)**, and **Streamlit**.

---

## 🌟 Key Highlights & Design Philosophy

- **Zero LLM Hallucination for Eligibility & Scoring**: Prerequisite checking, student eligibility, suitability scoring (0–100 points), and course ranking are computed using **100% deterministic Python logic** over SQLite.
- **Local Generative Explanation Layer**: The local LLM (**Ollama** running `qwen2.5:3b`) is used **strictly as an explanation generator** to verbalize why the top courses fit the student. The LLM cannot alter scores or rankings.
- **Fail-Safe Fallback**: If Ollama is offline or unavailable, the system automatically falls back to deterministic rule-based explanations without interrupting the user experience.
- **Stateful Graph Orchestration**: Agents are connected via **LangGraph** (`StateGraph`) using a typed shared state (`AdvisorState`).
- **Persistent Memory Feedback Loop**: Student preferences are managed by a dedicated CRUD `PreferenceMemory` service over SQLite.

---

## 🏗️ System Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT WEB DASHBOARD                         │
│   [Student Selector]  [Profile View]  [Preferences]  [Recommendations] │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Invokes run_advisor(student_id)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      LANGGRAPH STATEGRAPH WORKFLOW                     │
│                                                                        │
│   ┌──────────────────────┐   ┌─────────────────────┐   ┌────────────┐  │
│   │ [Node 1]             │   │ [Node 2]            │   │ [Node 3]   │  │
│   │ Academic Profile     │──>│ Course Analysis     │──>│ Recommender│  │
│   │ Agent                │   │ Agent               │   │ Agent      │  │
│   └──────────┬───────────┘   └──────────┬──────────┘   └──────┬─────┘  │
│              │                          │                     │        │
│        reads │                    reads │               calls │        │
│              ▼                          ▼                     ▼        │
│   ┌──────────────────────┐   ┌─────────────────────┐   ┌────────────┐  │
│   │ PreferenceMemory     │   │ Electives Catalog   │   │ Local LLM  │  │
│   │ & Student History    │   │ (Prerequisites, etc)│   │(qwen2.5:3b)│  │
│   └──────────┬───────────┘   └──────────┬──────────┘   └──────┬─────┘  │
└──────────────┼──────────────────────────┼─────────────────────┼────────┘
               │                          │                     │
               ▼                          ▼                     │ Fallback
┌────────────────────────────────────────────────────┐          ▼
│                  SQLITE DATABASE                   │   ┌────────────┐
│  • students            • completed_subjects        │   │ Rule-Based │
│  • electives           • preferences               │   │ Explanations
└────────────────────────────────────────────────────┘   └────────────┘
```

---

## 📁 Project Directory Structure

```
student advisor system/
├── agents/
│   ├── academic_profile_agent.py   # Agent 1: Fetches & structures student profile + memory
│   ├── course_analysis_agent.py    # Agent 2: 100-pt prerequisite check & course scoring
│   └── recommendation_agent.py     # Agent 3: Top 3 selection + Ollama explanation & fallback
├── data/
│   ├── students.json               # Seed student records (S001 to S010)
│   ├── courses.json                # Seed elective catalog (EL101 to EL110)
│   └── preferences.json            # Seed student preferences
├── database/
│   ├── academic_advisor.db         # SQLite database storing the 4 relational tables
│   ├── database.py                 # SQLite connection provider & helper query functions
│   └── seed_database.py            # Idempotent JSON-to-SQLite database seeding script
├── llm/
│   └── ollama_client.py            # Safe Ollama client wrapper (model check + fallback)
├── memory/
│   └── preference_memory.py        # CRUD & Upsert service for student preferences
├── tests/
│   ├── test_database.py            # Verifies database tables & query helpers
│   ├── test_agents.py              # Verifies sequential 3-agent manual pipeline
│   ├── test_langgraph.py           # Verifies LangGraph StateGraph orchestration
│   ├── test_memory.py              # Unit tests for PreferenceMemory CRUD
│   ├── test_memory_integration.py  # Tests preference persistence through all 3 agents
│   ├── test_ollama.py              # Verifies Ollama connectivity & model availability
│   └── test_ollama_integration.py  # Full integration test with LangGraph + Ollama
├── ui/
│   └── streamlit_app.py            # Dual-screen Streamlit web application & dashboard
├── main.py                         # Phase 1 entry point for database seeding
├── requirements.txt                # Project dependencies
├── README.md                       # Complete project documentation
└── Student_Academic_Advisor_Complete_Project_Manual.docx  # Full project manual
```

---

## 🗄️ Database Architecture (`academic_advisor.db`)

The SQLite database stores 4 relational tables:

| Table | Primary Key | Foreign Key | Purpose |
| :--- | :--- | :--- | :--- |
| **`students`** | `student_id` (TEXT) | None | Stores student profile (`name`, `program`, `semester`). |
| **`completed_subjects`** | `id` (INTEGER AUTO) | `student_id` | Stores subjects finished and grades achieved (`grade`). |
| **`electives`** | `course_id` (TEXT) | None | Catalog of electives with comma-separated `prerequisites`, `domain`, `skills`, `career_paths`, `difficulty`. |
| **`preferences`** | `id` (INTEGER AUTO) | `student_id` | Key-value store for preferences (`career_goal`, `interest`, `learning_style`, etc.). |

---

## 🤖 The 3 Specialized Agents

### 1. Academic Profile Agent (`AcademicProfileAgent`)
- **Input**: `student_id` (e.g. `"S001"`)
- **Processing**: Reads student profile, completed subjects, grades, and preferences via `PreferenceMemory`.
- **Output**: Structured student profile dictionary.

### 2. Course Analysis Agent (`CourseAnalysisAgent`)
- **Input**: `student_profile` dict from Agent 1.
- **Processing**: Checks prerequisites (marks missing prereqs as ineligible with score `0`). Evaluates eligible courses against the 100-Point scoring model.
- **Output**: List of analyzed elective courses with scores, eligibility flags, and scoring reasons.

#### 📊 100-Point Scoring Breakdown
1. **Domain Match with Completed Subjects (30 pts)**: Proportional to satisfied prerequisites (`completed / total * 30`).
2. **Interest & Domain Alignment (25 pts)**: Preferred domain match (25 pts) or interest keyword match (20 pts).
3. **Career Goal Match (20 pts)**: Substring match between career goal and elective career paths.
4. **Prerequisite Satisfaction Bonus (15 pts)**: Guaranteed bonus for completing all mandatory prerequisites.
5. **Preference & Learning Style Match (10 pts)**: Difficulty match (7 pts) + hands-on/practical learning style match (3 pts).

### 3. Recommendation Agent (`RecommendationAgent`)
- **Input**: `student_profile` dict and `analyzed_courses` list.
- **Processing**: Filters `eligible == True`, sorts by score descending, slices Top 3, calls Ollama `qwen2.5:3b` for personalized explanations, or applies rule-based fallback.
- **Output**: Final recommendation dictionary with Top 3 courses, scores, reasons, and explanations.

---

## 🔄 LangGraph Orchestration

LangGraph manages the shared state across nodes:

```python
class AdvisorState(TypedDict, total=False):
    student_id      : str   # Initial input
    profile         : dict  # Output of Node 1 (Agent 1)
    course_analysis : list  # Output of Node 2 (Agent 2)
    recommendation  : dict  # Output of Node 3 (Agent 3)
```

**Flow**: `START` $\rightarrow$ `academic_profile` $\rightarrow$ `course_analysis` $\rightarrow$ `recommendation` $\rightarrow$ `END`

---

## 🚀 Quick Start & Setup Guide

### 1. Install Dependencies
```bash
pip install langgraph langchain-core ollama streamlit python-docx
```

### 2. Seed the Database
```bash
python main.py
```

### 3. (Optional) Start Ollama for LLM Explanations
```bash
ollama pull qwen2.5:3b
ollama serve
```
*(If Ollama is not running, the app automatically runs in rule-based explanation mode without crashing.)*

### 4. Run the Tests
```bash
python tests/test_database.py
python tests/test_agents.py
python tests/test_langgraph.py
python tests/test_memory_integration.py
python tests/test_ollama_integration.py
```

### 5. Launch the Streamlit Web UI
```bash
streamlit run ui/streamlit_app.py
```

---

## 🎯 Viva Voce & Interview Cheat Sheet

- **Q: Why multi-agent instead of a single ChatGPT prompt?**  
  *A: A single prompt hallucinates prerequisites and gives inconsistent rankings. Our multi-agent system decouples deterministic prerequisite validation (Agent 1 & 2) from language generation (Agent 3 + Ollama), guaranteeing 100% prerequisite accuracy.*

- **Q: How does the system prevent hallucination?**  
  *A: Prerequisite validation, suitability scores (0-100), and rankings are executed in pure Python before the LLM is called. The LLM only receives pre-calculated facts to explain.*

- **Q: What happens if Ollama is offline?**  
  *A: `ollama_client.py` catches connection errors and seamlessly falls back to `_rule_based_explanation()`, ensuring zero system downtime.*

- **Q: What is the difference between an Agent and PreferenceMemory?**  
  *A: An Agent contains autonomous decision-making logic inside the workflow. `PreferenceMemory` is a stateless CRUD service for managing preference records in SQLite.*
