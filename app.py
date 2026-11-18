from pathlib import Path
import time
import requests
import streamlit as st

from parser.pdf_parser import PDFParser
from parser.text_cleaner import TextCleaner
from parser.section_parser import SectionParser

from graph.graph_builder import GraphBuilder
from graph.neo4j_manager import Neo4jManager
from graph.graph_rag import GraphRAG
from graph.statistics import GraphStatistics

from llm.ollama_client import OllamaClient


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="National Trust Bank - GraphRAG",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================================
# CUSTOM CSS
# ==========================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #0b0f15;
    }

    .main-title {
        color: #60a5fa;
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 25px;
    }

    .record-box {
        background-color: #111827;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }

    .record-title {
        color: #60a5fa;
        font-size: 1rem;
        font-weight: 700;
    }

    .record-meta {
        color: #cbd5e1;
        font-size: 0.9rem;
    }

    .debug-box {
        background-color: #020617;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# POLICY METADATA
# ==========================================================

POLICY_METADATA = {

    "Home_Loan_Policy.pdf": {
        "name": "Home Loan Policy",
        "id": "HLP-001",
        "version": "1.0",
        "department": "Retail Lending",
        "category": "Lending Policy"
    },

    "Education_Loan_Policy.pdf": {
        "name": "Education Loan Policy",
        "id": "ELP-002",
        "version": "1.0",
        "department": "Retail Lending",
        "category": "Education Policy"
    },

    "General_Banking_Policy.pdf": {
        "name": "General Banking Policy",
        "id": "GBP-003",
        "version": "1.0",
        "department": "Branch Operations",
        "category": "Operational Policy"
    }
}


# ==========================================================
# OLLAMA STATUS
# ==========================================================

@st.cache_resource
def check_ollama_status():

    client = OllamaClient()

    try:

        response = requests.get(
            f"{client.url}/api/tags",
            timeout=3
        )

        if response.status_code == 200:

            models = [
                model["name"]
                for model in response.json().get(
                    "models",
                    []
                )
            ]

            return (
                True,
                models,
                client.model
            )

        return (
            False,
            [],
            client.model
        )

    except Exception:

        return (
            False,
            [],
            client.model
        )


# ==========================================================
# NEO4J STATUS
# ==========================================================

@st.cache_resource
def check_neo4j_status():

    manager = Neo4jManager()

    try:

        status = manager.test_connection()

    except Exception as e:

        status = (
            f"Neo4j connection failed: {e}"
        )

    finally:

        manager.close()

    if "Successfully" in status:

        return True, status

    return False, status


# ==========================================================
# GRAPH RAG
# ==========================================================

@st.cache_resource
def get_graphrag():

    return GraphRAG()


# ==========================================================
# CONNECTION CHECK
# ==========================================================

neo4j_ok, neo4j_msg = (
    check_neo4j_status()
)

ollama_ok, ollama_models, active_model = (
    check_ollama_status()
)


# ==========================================================
# SESSION STATE
# ==========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


if "last_rag_result" not in st.session_state:

    st.session_state.last_rag_result = None


# ==========================================================
# INGESTION FUNCTION
# ==========================================================

def run_ingest(filename):

    pdf_path = (
        Path("data/policies")
        / filename
    )

    metadata = POLICY_METADATA[filename]

    pdf = PDFParser()
    cleaner = TextCleaner()
    parser = SectionParser()
    builder = GraphBuilder()

    try:

        # --------------------------------------------------
        # 1. Extract PDF
        # --------------------------------------------------

        text = pdf.extract_text(
            pdf_path
        )

        # --------------------------------------------------
        # 2. Clean text
        # --------------------------------------------------

        cleaned = cleaner.clean(
            text
        )

        # --------------------------------------------------
        # 3. Parse sections
        # --------------------------------------------------

        policy = parser.parse(

            cleaned,

            document_name=metadata["name"],

            document_id=metadata["id"],

            version=metadata["version"],

            department=metadata["department"],

            category=metadata["category"]

        )

        # --------------------------------------------------
        # 4. Build Neo4j graph
        # --------------------------------------------------

        builder.build(policy)

    finally:

        builder.close()


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.header(
        "🏦 Connection Status"
    )


    # ======================================================
    # NEO4J
    # ======================================================

    if neo4j_ok:

        st.success(
            "Neo4j Database Online"
        )

    else:

        st.error(
            "Neo4j Database Offline"
        )

        st.caption(
            "Start your database in Neo4j Desktop."
        )


    # ======================================================
    # OLLAMA
    # ======================================================

    if ollama_ok:

        st.success(
            f"Ollama Active ({active_model})"
        )

    else:

        st.error(
            "Ollama Service Offline"
        )

        st.caption(
            "Make sure Ollama is running."
        )


    st.divider()


    # ======================================================
    # POLICY INGESTION
    # ======================================================

    st.header(
        "📄 Policy Ingestion"
    )

    st.caption(
        "Load policy PDFs into the Neo4j Knowledge Graph."
    )


    policy_dir = Path(
        "data/policies"
    )


    if policy_dir.exists():

        pdf_files = [

            file.name

            for file in policy_dir.glob(
                "*.pdf"
            )

            if file.name in POLICY_METADATA

        ]

    else:

        pdf_files = []


    if pdf_files:

        selected_file = st.selectbox(
            "Select Policy PDF",
            pdf_files
        )

        meta = POLICY_METADATA[
            selected_file
        ]


        st.info(
            f"""
            **Policy:** {meta['name']}

            **ID:** {meta['id']}

            **Category:** {meta['category']}

            **Department:** {meta['department']}
            """
        )


        if st.button(
            "🚀 Ingest & Build Graph",
            disabled=not neo4j_ok,
            use_container_width=True
        ):

            with st.spinner(
                f"Ingesting {meta['name']}..."
            ):

                try:

                    run_ingest(
                        selected_file
                    )

                    st.success(
                        f"{meta['name']} successfully added to Neo4j."
                    )

                    # Clear cached GraphRAG
                    st.cache_resource.clear()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Ingestion failed: {e}"
                    )

    else:

        st.warning(
            "No policy PDFs found in data/policies."
        )


    st.divider()


    # ======================================================
    # CLEAR CHAT
    # ======================================================

    if st.button(
        "🗑 Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.session_state.last_rag_result = None

        st.rerun()


    st.divider()


    # ======================================================
    # GRAPH STATISTICS
    # ======================================================

    st.header(
        "📊 Knowledge Graph"
    )


    if neo4j_ok:

        stats_getter = GraphStatistics()

        try:

            stats = (
                stats_getter.get_stats()
            )

        finally:

            stats_getter.close()


        st.metric(
            "Total Nodes",
            stats.get(
                "total_nodes",
                0
            )
        )


        st.metric(
            "Relationships",
            stats.get(
                "total_relationships",
                0
            )
        )


        st.markdown(
            "**Nodes by Label**"
        )


        for label, count in (
            stats.get(
                "node_counts",
                {}
            ).items()
        ):

            st.write(
                f"🔹 {label}: {count}"
            )

    else:

        st.caption(
            "Statistics unavailable."
        )


# ==========================================================
# MAIN HEADER
# ==========================================================

st.markdown(
    '<div class="main-title">'
    '🏦 National Trust Bank'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'GraphRAG Customer Support Assistant'
    '</div>',
    unsafe_allow_html=True
)


# ==========================================================
# MAIN COLUMNS
# ==========================================================

col_chat, col_inspect = st.columns(
    [1.2, 0.8]
)


# ==========================================================
# CHAT SECTION
# ==========================================================

with col_chat:

    st.subheader(
        "💬 Customer Support Chat"
    )


    # ======================================================
    # WELCOME MESSAGE
    # ======================================================

    if not st.session_state.messages:

        st.info(
            """
            ### 🏦 Welcome to National Trust Bank

            I am your GraphRAG Customer Support Assistant.

            I retrieve information from the **Neo4j Banking
            Knowledge Graph** and use **Gemma 3 1B**
            to generate the answer.

            **Try asking:**

            • What is the eligibility for a home loan?

            • What documents are required for an education loan?

            • What documents are required for an Home loan?

            • What is the interest rate for education Loan?

            • What is the repayment period?
            """
        )


    # ======================================================
    # CHAT HISTORY
    # ======================================================

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )


    # ======================================================
    # USER INPUT
    # ======================================================

    user_query = st.chat_input(
        "Ask a banking policy question..."
    )


    if user_query:

        # --------------------------------------------------
        # USER MESSAGE
        # --------------------------------------------------

        with st.chat_message(
            "user"
        ):

            st.markdown(
                user_query
            )


        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_query
            }
        )


        # --------------------------------------------------
        # ASSISTANT
        # --------------------------------------------------

        with st.chat_message(
            "assistant"
        ):

            if not neo4j_ok or not ollama_ok:

                answer = (
                    "⚠️ Neo4j or Ollama is offline. "
                    "Please check the connection status."
                )

                st.error(
                    answer
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

            else:

                with st.spinner(
                    "🔍 Searching the Knowledge Graph..."
                ):

                    try:

                        # ==================================
                        # GET GRAPH RAG
                        # ==================================

                        rag = get_graphrag()


                        # ==================================
                        # RUN GRAPH RAG
                        # ==================================

                        start = time.time()

                        result = (
                            rag.answer_question(
                                user_query
                            )
                        )

                        elapsed = (
                            time.time() - start
                        )


                        # ==================================
                        # IMPORTANT
                        # ==================================
                        #
                        # Make an independent copy of the
                        # result so the inspector always
                        # displays the EXACT result returned
                        # for this query.
                        #
                        # ==================================

                        if not isinstance(
                            result,
                            dict
                        ):

                            raise TypeError(
                                "GraphRAG returned "
                                "an invalid result. "
                                "Expected dict."
                            )


                        # ----------------------------------
                        # Ensure context exists
                        # ----------------------------------

                        context = result.get(
                            "context",
                            []
                        )


                        if context is None:

                            context = []


                        # ----------------------------------
                        # Store EXACT result
                        # ----------------------------------

                        st.session_state.last_rag_result = {
                            **result,
                            "context": list(context)
                        }


                        # ==================================
                        # DEBUG TERMINAL
                        # ==================================

                        print(
                            "\n"
                            + "=" * 70
                        )

                        print(
                            "===== STREAMLIT RESULT DEBUG ====="
                        )

                        print(
                            "Question:",
                            user_query
                        )

                        print(
                            "Context count:",
                            len(context)
                        )


                        for i, item in enumerate(
                            context,
                            start=1
                        ):

                            print(
                                f"\nCHUNK {i}"
                            )

                            print(
                                "Policy       :",
                                item.get(
                                    "policy"
                                )
                            )

                            print(
                                "Policy ID    :",
                                item.get(
                                    "policy_id"
                                )
                            )

                            print(
                                "Section      :",
                                item.get(
                                    "section"
                                )
                            )

                            print(
                                "Section ID   :",
                                item.get(
                                    "section_id"
                                )
                            )

                            print(
                                "Category     :",
                                item.get(
                                    "category"
                                )
                            )

                            print(
                                "Source Type  :",
                                item.get(
                                    "source_type"
                                )
                            )

                            print(
                                "Content      :"
                            )

                            print(
                                item.get(
                                    "content",
                                    ""
                                )
                                [:1000]
                            )


                        print(
                            "\n"
                            + "=" * 70
                        )

                        print(
                            "===== END STREAMLIT RESULT DEBUG ====="
                        )

                        print(
                            "=" * 70
                            + "\n"
                        )


                        # ==================================
                        # ANSWER
                        # ==================================

                        answer = result.get(
                            "answer",
                            "No answer generated."
                        )


                        # ==================================
                        # DISPLAY ANSWER
                        # ==================================

                        st.markdown(
                            answer
                        )


                        # ==================================
                        # RESPONSE TIME
                        # ==================================

                        st.caption(
                            f"⏱ Response time: "
                            f"{elapsed:.2f} seconds"
                        )


                        # ==================================
                        # RETRIEVAL COUNT
                        # ==================================

                        retrieved_count = len(
                            context
                        )


                        st.success(
                            f"✓ Retrieved "
                            f"{retrieved_count} "
                            f"graph records"
                        )


                        # ==================================
                        # SAVE CHAT
                        # ==================================

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer
                            }
                        )


                    except Exception as e:

                        error_message = (
                            "❌ GraphRAG error: "
                            + str(e)
                        )


                        st.error(
                            error_message
                        )


                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": error_message
                            }
                        )


# ==========================================================
# RETRIEVAL INSPECTOR
# ==========================================================

with col_inspect:

    st.subheader(
        "🔍 GraphRAG Retrieval Insights"
    )


    rag_result = (
        st.session_state.last_rag_result
    )


    if rag_result:

        # ==================================================
        # ANSWER
        # ==================================================

        st.markdown(
            "### 🤖 AI Generated Answer"
        )


        answer_text = rag_result.get(
            "answer",
            "No answer generated."
        )


        # IMPORTANT:
        # Do not use st.success() for long LLM answers.
        # Markdown gives correct formatting.

        st.markdown(
            answer_text
        )


        st.divider()


        # ==================================================
        # RETRIEVAL SUMMARY
        # ==================================================

        raw_context = rag_result.get(
            "context",
            []
        )


        st.markdown(
            "### 📦 Retrieval Summary"
        )


        st.metric(
            "Context Records",
            len(raw_context)
        )


        # ==================================================
        # KEYWORDS
        # ==================================================

        st.markdown(
            "### 🔑 Extracted Keywords"
        )


        keywords = rag_result.get(
            "keywords",
            []
        )


        if keywords:

            st.code(
                ", ".join(
                    str(k)
                    for k in keywords
                )
            )

        else:

            st.caption(
                "No keywords detected."
            )


        # ==================================================
        # STATISTICS
        # ==================================================

        st.markdown(
            "### 📊 Retrieval Statistics"
        )


        stats = rag_result.get(
            "stats",
            {}
        )


        policies = stats.get(
            "policies",
            []
        )


        section_count = stats.get(
            "section_count",
            0
        )


        relationship_count = stats.get(
            "relationship_count",
            0
        )


        response_time = stats.get(
            "response_time",
            0
        )


        st.info(
            f"""
            **Policy:** {
                ", ".join(policies)
                if policies
                else "None"
            }

            **Sections Retrieved:** {
                section_count
            }


            **Response Time:** {
                response_time
            } sec
            """
        )


        # ==================================================
        # RETRIEVED KNOWLEDGE GRAPH
        # ==================================================

        st.markdown(
            "### 🕸️ Retrieved Knowledge Graph"
        )


        if raw_context:

            for index, record in enumerate(
                raw_context,
                start=1
            ):

                # ------------------------------------------
                # SAFE FIELD EXTRACTION
                # ------------------------------------------

                policy = record.get(
                    "policy",
                    "Unknown Policy"
                )

                policy_id = record.get(
                    "policy_id",
                    "N/A"
                )

                policy_version = record.get(
                    "policy_version",
                    "N/A"
                )

                loan = record.get(
                    "loan",
                    "N/A"
                )

                section = record.get(
                    "section",
                    "Unknown Section"
                )

                section_id = record.get(
                    "section_id",
                    "N/A"
                )

                category = record.get(
                    "category"
                )

                source_type = record.get(
                    "source_type",
                    "Unknown"
                )

                content = record.get(
                    "content",
                    ""
                )

                retrieval_reason = record.get(
                    "retrieval_reason",
                    ""
                )

                entities = record.get(
                    "entities",
                    []
                )


                # ------------------------------------------
                # DISPLAY CATEGORY
                # ------------------------------------------

                if category is None:

                    category_display = (
                        "Section-level"
                    )

                else:

                    category_display = str(
                        category
                    )


                # ------------------------------------------
                # RECORD EXPANDER
                # ------------------------------------------

                with st.expander(
                    (
                        f"📄 {index}. "
                        f"{policy} → {section}"
                        f" | {category_display}"
                    ),
                    expanded=(index == 1)
                ):

                    # ======================================
                    # BASIC INFORMATION
                    # ======================================

                    st.markdown(
                        "#### 📌 Record Information"
                    )


                    st.write(
                        "**Policy:**",
                        policy
                    )

                    st.write(
                        "**Policy ID:**",
                        policy_id
                    )

                    st.write(
                        "**Policy Version:**",
                        policy_version
                    )

                    st.write(
                        "**Loan:**",
                        loan
                    )

                    st.write(
                        "**Section:**",
                        section
                    )

                    st.write(
                        "**Section ID:**",
                        section_id
                    )

                    st.write(
                        "**Category:**",
                        category_display
                    )

                    st.write(
                        "**Source Type:**",
                        source_type
                    )


                    # ======================================
                    # RETRIEVAL REASON
                    # ======================================

                    if retrieval_reason:

                        st.markdown(
                            "#### 🎯 Retrieval Reason"
                        )

                        st.info(
                            retrieval_reason
                        )


                    # ======================================
                    # CONTENT
                    # ======================================

                    if content:

                        st.markdown(
                            "#### 📄 Retrieved Content"
                        )

                        st.text(
                            content
                        )

                    else:

                        st.caption(
                            "No content available."
                        )


                    # ======================================
                    # GRAPH ENTITIES
                    # ======================================

                    st.markdown(
                        "#### 🔗 Structured Graph Entities"
                    )


                    if entities:

                        for entity_index, entity in enumerate(
                            entities,
                            start=1
                        ):

                            labels = entity.get(
                                "labels",
                                []
                            )

                            relationship = entity.get(
                                "relationship",
                                "RELATED_TO"
                            )

                            properties = entity.get(
                                "properties",
                                {}
                            )


                            label_text = (
                                ", ".join(labels)
                                if labels
                                else "Entity"
                            )


                            st.write(
                                f"**{entity_index}. "
                                f"{relationship} → "
                                f"{label_text}**"
                            )


                            if properties:

                                st.json(
                                    properties
                                )

                    else:

                        st.caption(
                            "No structured entities attached "
                            "to this record."
                        )


        else:

            st.warning(
                "No matching graph nodes were "
                "returned for this question."
            )


        # ==================================================
        # RAW CONTEXT DEBUG
        # ==================================================

        st.markdown(
            "### 🧪 Raw Retrieval Debug"
        )


        st.caption(
            "This is the exact context object returned "
            "by GraphRAG for the current question."
        )


        with st.expander(
            "Show raw context",
            expanded=False
        ):

            for index, record in enumerate(
                raw_context,
                start=1
            ):

                st.markdown(
                    f"#### CHUNK {index}"
                )

                st.json(
                    record
                )


        # ==================================================
        # FORMATTED CONTEXT SENT TO GEMMA
        # ==================================================

        st.markdown(
            "### 📄 Context Sent to Gemma"
        )


        formatted_context = (
            rag_result.get(
                "formatted_context",
                ""
            )
        )


        if formatted_context:

            st.text_area(
                "LLM Context",
                formatted_context,
                height=350,
                disabled=True
            )

        else:

            st.caption(
                "No formatted context available."
            )


    else:

        st.info(
            "Ask a banking question to see "
            "GraphRAG retrieval details."
        )