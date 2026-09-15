import io
import os
import streamlit as st
from groq import Groq
from pypdf import PdfReader

from workflow import run_workflow
from prompts import PROMPTS

st.set_page_config(page_title="AI Study Pack Generator", page_icon="📚", layout="wide")


def get_api_key():
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "").strip()


def get_client():
    key = get_api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it in Streamlit Cloud → Settings → Secrets.")
    return Groq(api_key=key)


def extract_file_text(uploaded_file):
    if uploaded_file is None:
        return ""
    data = uploaded_file.getvalue()
    name = uploaded_file.name.lower()
    try:
        if name.endswith((".txt", ".md", ".csv")):
            return data.decode("utf-8", errors="ignore")
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        raise ValueError("Unsupported file type.")
    except Exception as e:
        raise RuntimeError(f"Could not read {uploaded_file.name}: {e}") from e


def clean_text(text, max_chars=30000):
    text = (text or "").strip()
    return text if len(text) <= max_chars else text[:max_chars] + "\n\n[Source material truncated.]"


def md_list(items):
    return "_None_" if not items else "\n".join(f"- {item}" for item in items)


def to_markdown(pack):
    lines = [
        f"# {pack.get('title', 'AI Study Pack')}", "",
        "## Overview", pack.get("overview", ""), "",
        "## Key Concepts", md_list(pack.get("key_concepts", [])), "",
        "## Important Terms", md_list(pack.get("important_terms", [])), "",
        "## Study Notes",
    ]
    for i, note in enumerate(pack.get("study_notes", []), 1):
        lines += [f"### Note {i}", str(note), ""]
    lines += ["## Flashcards", ""]
    for i, card in enumerate(pack.get("flashcards", []), 1):
        lines += [f"### Flashcard {i}", f"**Question:** {card.get('question', '')}", f"**Answer:** {card.get('answer', '')}", ""]
    lines += ["## Practice Questions", ""]
    for i, q in enumerate(pack.get("practice_questions", []), 1):
        lines += [
            f"### Question {i}", f"**Type:** {q.get('type', '')}",
            f"**Difficulty:** {q.get('difficulty', '')}", q.get("question", ""), "",
            f"**Answer:** {q.get('answer', '')}", "",
            f"**Explanation:** {q.get('explanation', '')}", "",
        ]
    lines += ["## Exam Tips", md_list(pack.get("exam_tips", [])), "", "## Study Plan", md_list(pack.get("study_plan", [])), "", "## Quality Note", pack.get("quality_note", "")]
    return "\n".join(lines)


if "results" not in st.session_state:
    st.session_state.results = None
if "statuses" not in st.session_state:
    st.session_state.statuses = {stage: "Waiting" for stage in ["Planning", "Content Generation", "Assessment", "Review", "Refinement"]}

st.title("📚 AI Study Pack Generator")
st.caption("Multi-stage AI workflow: Planning → Content Generation → Assessment → Review → Refinement")

with st.sidebar:
    st.header("🎓 Student Profile")
    subject = st.text_input("Subject", placeholder="e.g. Machine Learning")
    topic = st.text_input("Topic", placeholder="e.g. Neural Networks")
    level = st.selectbox("Student Level", ["School", "College", "University", "Graduate"])
    learning_goal = st.text_area("Learning Goal", placeholder="e.g. Understand concepts and prepare for an exam", height=90)
    difficulty = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
    study_time = st.selectbox("Available Study Time", ["30 minutes", "1 hour", "2 hours", "3+ hours"])
    pack_type = st.selectbox("Study Pack Type", ["Complete Study Pack", "Exam Preparation", "Revision Pack", "Flashcards + Practice", "Concept Learning"])
    question_count = st.slider("Practice Questions", 3, 20, 8)

st.header("📝 Study Material")
notes = st.text_area("Paste notes, textbook content, or syllabus", height=220, placeholder="Paste your study material here...")
uploaded_file = st.file_uploader("Or upload a file", type=["pdf", "txt", "md", "csv"])
uploaded_text = ""
if uploaded_file:
    try:
        uploaded_text = extract_file_text(uploaded_file)
        st.success(f"Loaded {uploaded_file.name}")
    except Exception as e:
        st.error(str(e))

source_text = clean_text("\n\n".join(x for x in [notes.strip(), uploaded_text.strip()] if x))
generate_col, clear_col = st.columns(2)
with generate_col:
    generate = st.button("🚀 Generate Study Pack", type="primary", use_container_width=True)
with clear_col:
    clear = st.button("🧹 Clear", use_container_width=True)

if clear:
    st.session_state.results = None
    st.session_state.statuses = {stage: "Waiting" for stage in st.session_state.statuses}
    st.rerun()

st.header("🤖 Workflow Status")
status_cols = st.columns(5)
for col, (stage, status) in zip(status_cols, st.session_state.statuses.items()):
    icon = {"Waiting": "⏳", "Running": "🔄", "Completed": "✅", "Error": "❌"}.get(status, "⏳")
    with col:
        st.metric(stage, f"{icon} {status}")

if generate:
    if not subject.strip():
        st.error("Please enter a subject.")
        st.stop()
    if not topic.strip():
        st.error("Please enter a topic.")
        st.stop()
    if not source_text:
        st.error("Please paste notes or upload study material.")
        st.stop()

    context = {
        "subject": subject.strip(), "topic": topic.strip(), "level": level,
        "learning_goal": learning_goal.strip() or "Understand and revise the topic effectively.",
        "difficulty": difficulty, "study_time": study_time, "pack_type": pack_type,
        "question_count": question_count, "source_text": source_text,
    }
    st.session_state.statuses = {key: "Waiting" for key in st.session_state.statuses}

    def update_stage(stage, status):
        st.session_state.statuses[stage] = status

    try:
        client = get_client()
        with st.status("Running AI Study Pack Workflow...", expanded=True):
            st.write("The workflow is passing context from one stage to the next.")
            results = run_workflow(client, context, PROMPTS, on_stage=update_stage)
            st.write("✅ All five stages completed successfully.")
        st.session_state.results = results
        st.success("🎉 Final study pack generated successfully!")
    except Exception as e:
        st.error(f"Workflow stopped: {e}")
        st.info("Check your GROQ_API_KEY. If the model/API temporarily fails, try Generate again.")

results = st.session_state.results
if results:
    final_pack = results["final"]
    assessment = results["assessment"]
    st.divider()
    st.header("📖 Final Personalized Study Pack")
    score = assessment.get("assessment_score", assessment.get("score", 0))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Assessment Score", f"{score}/100")
    with c2:
        st.metric("Coverage", f"{assessment.get('coverage_score', 0)}/100")
    with c3:
        st.metric("Accuracy", f"{assessment.get('accuracy_score', 0)}/100")
    markdown_pack = to_markdown(final_pack)
    st.markdown(markdown_pack)
    st.download_button("⬇️ Download Study Pack", data=markdown_pack, file_name="personalized_study_pack.md", mime="text/markdown", use_container_width=True)
    with st.expander("🔧 View Workflow Details"):
        st.subheader("1️⃣ Planning")
        st.json(results["plan"])
        st.subheader("2️⃣ Content Generation")
        st.json(results["content"])
        st.subheader("3️⃣ Assessment")
        st.json(results["assessment"])
        st.subheader("4️⃣ Review")
        st.json(results["review"])
    with st.expander("💡 Strengths and Weaknesses"):
        st.write("**Strengths**")
        for item in assessment.get("strengths", []):
            st.write(f"- {item}")
        st.write("**Weaknesses**")
        for item in assessment.get("weaknesses", []):
            st.write(f"- {item}")

st.divider()
st.caption("Built with Python + Streamlit + Groq")
