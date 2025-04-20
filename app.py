import streamlit as st
from controller import StorageController, LLMController

controller = StorageController()
llm_controller = LLMController()

# --- Sidebar Navigation ---
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["Ingest Wikipedia", "Semantic Search", "Generate Pub Quiz"])

# --- Shared helpers ---
def difficulty_flag(level: str) -> str:
    level = level.lower()
    return {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(level, "⚪️")

# --- Shared language prefix input ---
st.sidebar.markdown("### Language Settings")
lang_prefix = st.sidebar.text_input("Optional language prefix", value="en")

# ==============================
# 📥 Ingest Wikipedia
# ==============================
if page == "Ingest Wikipedia":
    st.title("📥 Ingest Wikipedia Page into Memgraph")

    with st.form("ingest_form"):
        page_title = st.text_input("Enter Wikipedia page title", value="")
        ingestion_mode = st.radio(
            "Ingestion mode",
            options=["Ingest from scratch", "Update dataset"],
            index=0
        )
        ingestion_method = st.selectbox(
            "Ingestion method",
            options=["Quick (entire article)", "Detailed (select section)"]
        )

        section_filter = ""
        if ingestion_method == "Detailed (select section)":
            section_filter = st.text_input("Target section (e.g. Plot, Reception, Cast)", value="")

        submitted = st.form_submit_button("Ingest")

        if submitted:
            with st.spinner("🔄 Ingesting and creating vector index..."):
                mode = "replace" if ingestion_mode == "Ingest from scratch" else "append"
                method = "detailed" if "Detailed" in ingestion_method else "quick"
                count = controller.ingest_wikipedia(
                    page_title,
                    lang_prefix,
                    mode=mode,
                    method=method,
                    section_filter=section_filter if method == "detailed" else None
                )
                if count is not None:
                    verb = "Replaced" if mode == "replace" else "Appended"
                    st.success(f"✅ {verb} {count} paragraphs from '{page_title}' into Memgraph.")
                else:
                    st.success(f"✅ Paragraphs from '{page_title}' already exist in Memgraph!")

# ==============================
# 🔍 Semantic Search
# ==============================
elif page == "Semantic Search":
    st.title("🔍 Ask a Question")

    available_categories = controller.get_all_categories()
    if not available_categories:
        st.info("ℹ️ No pages ingested yet. Please ingest a Wikipedia page first.")
    else:
        category = st.selectbox("Select a page:", options=available_categories)
        query = st.text_input("Enter your question")

        if query:
            st.write("🔍 Searching and generating answer...")
            context = controller.get_similar_documents(category, query, 10)

            with st.spinner("🧠 GPT-4o is generating the answer..."):
                answer = llm_controller.answer_question_based_on_excerpts(query, context, lang_prefix)

            st.markdown("### 💬 Final Answer")
            st.success(answer)

            with st.expander("📚 View source excerpts"):
                for i, excerpt in enumerate(context):
                    st.markdown(f"**Excerpt {i+1}:**")
                    st.markdown(excerpt)

# ==============================
# 🧠 Generate Pub Quiz
# ==============================
elif page == "Generate Pub Quiz":
    st.title("🧠 Generate a Pub Quiz")

    available_categories = controller.get_all_categories()
    if not available_categories:
        st.info("ℹ️ No pages ingested yet. Please ingest a Wikipedia page first.")
    else:
        category = st.selectbox("Select a page:", options=available_categories)
        number_of_questions = st.number_input("Number of questions", min_value=1, max_value=50, value=5, step=1)
        better_explanation = st.text_input("What kind of questions would you like to focus on?", value="No specific kind.")

        if st.button("🎲 Generate Pub Quiz"):
            with st.spinner("Selecting paragraphs and generating quiz..."):
                quiz = llm_controller.generate_quiz(category, number_of_questions, lang_prefix, better_explanation)
                if quiz is None:
                    st.warning("Unable to generate quiz!")
                else:
                    for i, qa in enumerate(quiz, 1):
                        st.markdown(f"**{difficulty_flag(qa['difficulty'])} Q{i}:** {qa['question']}")
                        with st.expander("Show Answer", expanded=True):
                            st.markdown(f"**A{i}:** {qa['answer']}")
                        with st.expander("Show Explanation", expanded=True):
                            st.markdown(f"**E{i}:** {qa['explanation']}")
                        st.markdown("---")
