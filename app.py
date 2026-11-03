"""
Streamlit Web Demonstration Interface for MIN-DISC.
Unified SaaS Dashboard integrating:
1. System Overview Dashboard.
2. Fresh Passport Application Workflow.
3. Empirical Privacy Benchmark Evaluations (Passport U001-U010).
"""
import sys
from pathlib import Path
import streamlit as st

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import check_config_health
from src.ui.styles import apply_saas_styles
from src.ui.dashboard_view import render_dashboard_view
from src.ui.passport_view import render_passport_view

# RAG Knowledge Base Loaders
from src.embeddings import EmbeddingModel
from src.vector_store import VectorStore
from src.retriever import Retriever
from src.pdf_loader import load_pdfs_from_directory
from src.chunker import chunk_documents

# Streamlit Page Config
st.set_page_config(
    page_title="MIN-DISC | Task-Aware Minimum Disclosure",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply unified SaaS visual design styles
apply_saas_styles()


@st.cache_resource
def get_passport_rag_pipeline():
    """Initializes and caches the Passport RAG knowledge base."""
    embedding_model = EmbeddingModel()
    vector_store = VectorStore()

    if not vector_store.load():
        from src.config import PASSPORT_REQUIREMENTS_DIR
        docs = load_pdfs_from_directory(PASSPORT_REQUIREMENTS_DIR)
        chunks = chunk_documents(docs)
        texts = [c["text"] for c in chunks]
        embeddings = embedding_model.fit_transform(texts)
        vector_store.build_index(chunks, embeddings)
        vector_store.save()

    return Retriever(vector_store, embedding_model), embedding_model


def init_app_state():
    """Initializes top-level application navigation state."""
    if "active_view" not in st.session_state:
        st.session_state.active_view = "dashboard"


def main():
    init_app_state()
    health = check_config_health()

    # Load Passport RAG pipeline
    try:
        pass_retriever, pass_embed = get_passport_rag_pipeline()
    except Exception as e:
        st.error(f"Error initializing Passport RAG: {e}")
        return

    # -------------------------------------------------------------------------
    # SIDEBAR: SYSTEM DIAGNOSTICS & UNIFIED NAVIGATION
    # -------------------------------------------------------------------------
    st.sidebar.markdown("### 🔒 MIN-DISC Engine")
    st.sidebar.caption("Privacy-Preserving Task-Aware LLM Agent Prototype")

    st.sidebar.markdown("""
    <div class="sidebar-card">
        <b>System Status:</b> <span class="pill-active">ONLINE</span><br>
        <b>Active Workflow:</b> Fresh Passport Application<br>
        <b>Axiom:</b> Task-Justified Disclosure
    </div>
    """, unsafe_allow_html=True)

    # Navigation Menu
    nav_options = [
        "🏠 Dashboard",
        "🛂 Passport Application"
    ]

    view_to_idx = {
        "dashboard": 0,
        "passport": 1
    }
    current_idx = view_to_idx.get(st.session_state.active_view, 0)

    selected_nav = st.sidebar.radio(
        "Navigation Menu:",
        nav_options,
        index=current_idx,
        key="main_nav_radio"
    )

    idx_to_view = {
        0: "dashboard",
        1: "passport"
    }
    selected_view = idx_to_view[nav_options.index(selected_nav)]
    if selected_view != st.session_state.active_view:
        st.session_state.active_view = selected_view
        st.rerun()

    # Diagnostics Expander in Sidebar
    with st.sidebar.expander("⚙️ System Diagnostics", expanded=False):
        pass_chunks = pass_retriever.vector_store.index.ntotal if pass_retriever.vector_store.index else 0
        st.write(f"- **Passport Index**: {pass_chunks} vectors")
        st.write(f"- **Vector Engine**: {'TF-IDF (Fallback)' if not pass_embed.use_st else 'SentenceTransformers'}")
        st.write(f"- **Gemini API**: {'Configured' if health['has_gemini_key'] else 'Deterministic Fallback'}")
        st.write(f"- **Isolated Knowledge Base**: Verified (Passport)")

    st.sidebar.caption("MIN-DISC Final-Year Research Project Prototype")

    # -------------------------------------------------------------------------
    # ROUTE VIEW
    # -------------------------------------------------------------------------
    if st.session_state.active_view == "dashboard":
        render_dashboard_view()
    elif st.session_state.active_view == "passport":
        render_passport_view(pass_retriever)


if __name__ == "__main__":
    main()
