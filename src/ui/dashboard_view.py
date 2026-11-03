"""
Module: MIN-DISC Landing Dashboard View
Presents the central project overview, explanation of minimum-disclosure planning,
and interactive card for launching the Passport application workflow.
"""
import streamlit as st


def render_dashboard_view():
    """Renders the central landing dashboard."""
    # Top Branding Header
    st.markdown("""
    <div class="brand-header">
        <div class="brand-title">MIN-DISC System Dashboard</div>
        <div class="brand-subtitle">Task-Aware Minimum-Disclosure Planning for Privacy-Aware LLM Agents</div>
        <div class="brand-axiom">
            <b>Core Architectural Axiom:</b> <i>"Data availability must never be treated as data necessity."</i><br>
            MIN-DISC extracts authoritative task requirements from official policy documents via isolated RAG,
            plans a minimal verifiable attribute disclosure set, enforces deterministic defense-in-depth policy checks,
            and gates external tool submission behind explicit human authorization.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="demo-notice">
        <b>Prototype Evaluation Notice:</b> This dashboard operates in an isolated simulation environment.
        All user profiles are fully synthetic test records (U001 - U010). No calls are made to actual government portals (Passport Seva Portal, UIDAI).
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Active Application Workflow")
    st.caption("Launch the privacy-preserving application and disclosure pipeline:")

    st.markdown("""
    <div class="workflow-card">
        <div class="workflow-title">
            <span>🛂 Fresh Passport Application</span>
            <span class="pill-active">ACTIVE WORKFLOW</span>
        </div>
        <div class="workflow-desc">
            Automated document necessity extraction and minimum-disclosure planning for fresh Indian ordinary passport applications.
        </div>
        <div class="workflow-meta-item"><b>Target Scope:</b> Adult (18+) | Ordinary Case | Normal Application</div>
        <div class="workflow-meta-item"><b>Authority Source:</b> Official Passport Rules & Document Booklet (CPV Division, Ministry of External Affairs)</div>
        <div class="workflow-meta-item"><b>Privacy Defenses:</b> Address Proof (mandatory), DOB Proof (mandatory), Non-ECR Proof (conditional matriculation), blocks all unnecessary sensitive demographic attributes.</div>
        <div class="workflow-meta-item"><b>Synthetic Dataset:</b> 10 standardized synthetic profiles (U001 - U010)</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Launch Passport Workflow", key="btn_launch_passport", use_container_width=True, type="primary"):
        st.session_state.active_view = "passport"
        st.session_state.main_nav_radio = "🛂 Passport Application"
        st.rerun()

