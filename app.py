import streamlit as st
import uuid
from controller import StorageController, LLMController

DEFAULT_ID_KEY = "user_id"
current_user_id = st.query_params.get(DEFAULT_ID_KEY, None)
if not current_user_id:
    current_user_id = st.query_params.get(DEFAULT_ID_KEY, str(uuid.uuid4()))
    st.query_params.update({DEFAULT_ID_KEY: current_user_id})
    with st.expander("ℹ️ Važna obavijest", expanded=True):
        st.markdown(
            f"""
                    Dodijeljen vam je nasumični identitet: {current_user_id}. 
                    Ako ste prvi put na ovoj stranici, sačuvajte ovaj identitet.
                    Pristup stranici idući put možete napraviti koristeći link https://chatwithyourknowledge.streamlit.app?user_id={current_user_id}.
                    Bez identiteta, uvijek će vam se nanovo generirati novi identitet bez sačuvanih podataka.
                    """
        )


@st.cache_resource
def get_controller():
    return StorageController()


@st.cache_resource
def get_llm_controller():
    return LLMController()


controller = get_controller()
llm_controller = get_llm_controller()

controller.initialize_user(current_user_id)

# --- Sidebar Navigation ---
st.sidebar.title("📂 Moje znanje")
page = st.sidebar.radio(
    "Idi na",
    [
        "Unesi podatke s Wikipedije",
        "Unesi podatke sam",
        "Pregledaj podatke",
        "Izvezi podatke",
        "ChatBot",
        "Generiraj kviz",
    ],
)

# Sidebar display + option to override
st.sidebar.markdown("### 🔑 Identitet")
user_id = st.sidebar.text_input("Vaš identitet", value=current_user_id)
if st.sidebar.button("Koristi ovaj identitet"):
    # Update the URL with the new user ID (emulates cookie/session behavior)
    st.query_params.update({DEFAULT_ID_KEY: user_id})
    controller.initialize_user(user_id)
    st.rerun()


# --- Shared helpers ---
def difficulty_flag(level: str) -> str:
    level = level.lower()
    return {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(level, "⚪️")


# --- Shared language prefix input ---
st.sidebar.markdown("### Postavke jezika (Wikipedija)")
lang_prefix = st.sidebar.text_input("Opcionalni prefiks za jezik", value="en")

# ==============================
# 📥 Unesi podatke s Wikipedije
# ==============================
if page == "Unesi podatke s Wikipedije":
    st.title("📥 Unesi podatke s Wikipedije")

    with st.form("ingest_form"):
        category = st.text_input("Unesi naslov stranice na Wikipediji", value="")
        save_as_category = st.text_input(
            "Spremi s nazivom kategorije (ostavljanje ovog polja kao prazno će spremiti s istim imenom kao naslov)",
            value="",
        )
        ingestion_mode = st.radio(
            "Način uveza",
            options=["Uvezi ispočetka", "Dodaj na postojeće podatke"],
            index=0,
        )
        section_filter = st.text_input(
            "Željena sekcija (e.g. Plot, Reception, Cast)", value=""
        )
        submitted = st.form_submit_button("Ingest")

        if submitted:
            with st.spinner("🔄 Ingesting and creating vector index..."):
                mode = "replace" if ingestion_mode == "Uvezi ispočetka" else "append"
                has_section_filter = (
                    section_filter is not None and len(section_filter) > 0
                )
                method = "detailed" if has_section_filter else "quick"
                section = section_filter
                count = controller.ingest_wikipedia(
                    user_id,
                    category,
                    save_as_category,
                    lang_prefix,
                    mode=mode,
                    method=method,
                    section_filter=section_filter if has_section_filter else None,
                )
                if count is not None:
                    verb = "Zamijenjeno" if mode == "replace" else "Dodano"
                    st.success(
                        f"✅ {verb} {count} paragrafa iz '{category}' u spremnik."
                    )
                else:
                    st.success(
                        f"✅ Paragrafi u kategoriji '{category}' već postoje u spremniku!"
                    )

# ==============================
# ✍️ Unesi podatke sam
# ==============================
elif page == "Unesi podatke sam":
    st.title("✍️ Unesi podatke sam")

    available_categories = controller.get_all_categories(user_id)

    with st.form("custom_ingest_form"):
        st.info(
            "Dodajte vaše podatke. Za jedan paragraf, samo ga kopirajte u okvir. Za više paragrafa, osigurajte da su odvojeni bar jednom praznom crtom."
        )
        user_paragraph = st.text_area("Text to ingest", height=300)

        st.markdown("#### Odaberi pod kojom labelom ćete spremiti podatke")
        existing_label = st.selectbox(
            "Spremi u već postojeću kategoriju:", options=available_categories
        )
        new_label = st.text_input("Ili unesi novu kategoriju?")
        ingestion_mode = st.radio(
            "Ingestion mode",
            options=["Uvezi ispočetka", "Dodaj na postojeće podatke"],
            index=0,
        )

        submitted = st.form_submit_button("📥 Unesi")

        if submitted:
            if not user_paragraph.strip():
                st.warning("⚠️ Nema podataka u tekstu")
            else:
                target_label = (
                    new_label.strip() if new_label.strip() else existing_label
                )
                if not target_label:
                    st.warning("⚠️ Unesite naziv kategorije.")
                else:
                    mode = (
                        "replace" if ingestion_mode == "Uvezi ispočetka" else "append"
                    )
                    with st.spinner("Kodiranje i spremanje..."):
                        count = controller.ingest_custom_text(
                            user_id,
                            target_label,
                            user_paragraph,
                            lang_prefix=lang_prefix,
                            mode=mode,
                        )
                        st.success(f"✅ Uneseno {count} paragrafa u '{target_label}'.")

# ==============================
# 📊 Pregledaj podatke
# ==============================
elif page == "Pregledaj podatke":
    st.title("📊 Pregledaj unešene podatke")

    available_categories = controller.get_all_categories(user_id)
    if not available_categories:
        st.info(
            "ℹ️ Nismo pronašli prije spremljene podatke. Provjerite svoj identitet, ili unesite nove podatke."
        )
    else:
        selected_category = st.selectbox(
            "Biraj između kategorija:", options=available_categories
        )
        if st.button("🔍 Dohvati podatke"):
            with st.spinner(f"Dohvaćam podatke iz '{selected_category}'..."):
                paragraphs = controller.get_all_paragraphs_from_category(
                    user_id, selected_category
                )
                if not paragraphs:
                    st.warning(
                        f"Nismo pronašli podatke za kategoriju '{selected_category}'."
                    )
                else:
                    st.success(f"✅ Pronađeno {len(paragraphs)} paragrafa.")
                    for i, item in enumerate(paragraphs):
                        with st.expander(f"📄 Paragraf {i+1}", expanded=False):
                            st.markdown(item["content"])

# ==============================
# 📦 Izvezi podatke
# ==============================
elif page == "Izvezi podatke":
    st.title("📦 Izvezi podatke")
    st.info(
        "Aplikacija je trenutno u beta-verziji. Zbog toga sačuvanje podataka u slučaju nepredviđenih greški nije garantirano. Zbog toga, svoje podatke možete izvesti i ponovo uvesti kad god hoćete."
    )

    available_categories = controller.get_all_categories(user_id)
    if not available_categories:
        st.info("ℹ️ Nismo pronašli kategorije. Prvo unesite podatke.")
    else:
        selected_category = st.selectbox(
            "Odaberi kategoriju za izvoz:", options=available_categories
        )
        if st.button("📤 Izvezi kao .txt datoteku"):
            with st.spinner(f"Izvoz paragrafa iz '{selected_category}'..."):
                paragraphs = controller.get_all_paragraphs_from_category(
                    user_id, selected_category
                )
                if not paragraphs:
                    st.warning("Nismo pronašli paragrafe u ovoj kategoriji.")
                else:
                    joined_text = "\n\n".join(p["content"] for p in paragraphs)
                    st.download_button(
                        label="📥 Download Text File",
                        data=joined_text,
                        file_name=f"{selected_category}.txt",
                        mime="text/plain",
                    )

# ==============================
# 💬 Chat With Your Knowledge (Chatbot)
# ==============================
elif page == "ChatBot":
    st.title("💬 Tvoj Personalizirani Chatbot")

    available_categories = controller.get_all_categories(user_id)
    if not available_categories:
        st.info("ℹ️ Nismo pronašli kategorije. Prvo unesite podatke.")
    else:
        category = st.selectbox(
            "Odaberi bazu znanja s kojom želite razgovarati:",
            options=available_categories,
        )

        # Initialize chat history in session
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Display previous chat messages
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input box
        user_input = st.chat_input("Postavi pitanje ovoj bazi znanja...")
        if user_input:
            st.chat_message("user").markdown(user_input)
            st.session_state.chat_history.append(
                {"role": "user", "content": user_input}
            )

            # Semantic search
            with st.spinner("🔍 Dohvaćanje relevantnog znanja..."):
                context = controller.get_similar_documents(
                    user_id, category, user_input, 10
                )

            # Generate answer
            with st.spinner("🧠 GPT-4o misli..."):
                answer = llm_controller.answer_question_based_on_excerpts(
                    user_id, user_input, context, lang_prefix
                )

            # Display bot response
            st.chat_message("assistant").markdown(answer)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )

            # Optional: display excerpts in a toggle box
            with st.expander("📚 Pogledaj izvore"):
                for i, excerpt in enumerate(context):
                    st.markdown(f"**Excerpt {i+1}:**")
                    st.markdown(excerpt)


# ==============================
# 🧠 Generiraj kviz
# ==============================
elif page == "Generiraj kviz":
    st.title("🧠 Generiraj kviz iz svoje baze znanja")

    available_categories = controller.get_all_categories(user_id)
    if not available_categories:
        st.info("ℹ️ Nismo pronašli kategorije. Prvo unesite podatke.")
    else:
        category = st.selectbox("Select a page:", options=available_categories)
        number_of_questions = st.number_input(
            "Broj pitanja", min_value=1, max_value=50, value=5, step=1
        )
        better_explanation = st.text_input(
            "Na koji način bi htjeli da se GPT fokusira na pitanje (na engleskom) ?",
            value="No specific kind.",
        )

        if st.button("🎲 Generate Pub Quiz"):
            with st.spinner("Odabir paragrafa i generiranje pub kviza..."):
                quiz = llm_controller.generate_quiz(
                    user_id,
                    category,
                    number_of_questions,
                    lang_prefix,
                    better_explanation,
                )
                if quiz is None:
                    st.warning("Nismo uspjeli generirati kviz!")
                else:
                    for i, qa in enumerate(quiz, 1):
                        st.markdown(
                            f"**{difficulty_flag(qa['difficulty'])} Q{i}:** {qa['question']}"
                        )
                        with st.expander("Pogledaj odgovor", expanded=True):
                            st.markdown(f"**A{i}:** {qa['answer']}")
                        with st.expander("Pogledaj objašnjenje", expanded=True):
                            st.markdown(f"**E{i}:** {qa['explanation']}")
                        st.markdown("---")
