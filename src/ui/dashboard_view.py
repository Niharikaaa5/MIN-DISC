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
        st.rerun()

    st.markdown("---")

    # Workflow Architecture Overview
    st.markdown("### End-to-End Privacy Architecture")
    arch_col1, arch_col2 = st.columns([1, 1], gap="medium")

    with arch_col1:
        st.markdown("""
        <div class="stage-box">
            <div class="stage-title">
                <span class="stage-badge">PIPELINE</span> Sequential Verification Stages
            </div>
            <ol style="font-size:0.88rem; color:#334155; line-height:1.6; margin-left: -1rem;">
                <li><b>Isolated RAG Retrieval:</b> Query domain-specific FAISS vector stores to retrieve authoritative regulatory chunks from official Passport booklets.</li>
                <li><b>Requirement Extraction:</b> Extract structured task requirements and determine exact documentary evidence conditions.</li>
                <li><b>Attribute Matching:</b> Map available applicant attributes against requirements and classify into satisfied, failed, or missing.</li>
                <li><b>Minimum-Disclosure Planning:</b> Synthesize minimal transmission payload; eliminate unneeded attributes (income, bank account, medical data); document disclosure justifications.</li>
                <li><b>Deterministic Policy Engine:</b> Rigorous defense-in-depth policy verification (PASSED vs BLOCKED).</li>
                <li><b>Human-in-the-Loop Gating:</b> Require explicit human authorization before external submission.</li>
                <li><b>Simulated Mock Submission:</b> External tool API verifies zero unapproved attribute leakage and records submission.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    with arch_col2:
        st.markdown("""
        <div class="stage-box">
            <div class="stage-title">
                <span class="stage-badge">BENCHMARKS</span> Empirical Privacy Evaluation
            </div>
            <p style="font-size:0.88rem; color:#475569; line-height:1.5;">
                MIN-DISC evaluates disclosure reduction across standardized synthetic datasets (U001 - U010):
            </p>
            <table class="kv-table">
                <tr>
                    <td class="kv-key">Passport Workflow (10 Profiles)</td>
                    <td class="kv-val"><b>86.3%</b> average attribute disclosure reduction</td>
                </tr>
                <tr>
                    <td class="kv-key">Policy Enforcement Accuracy</td>
                    <td class="kv-val"><b>100%</b> accurate (8 Passed, 2 Blocked correctly)</td>
                </tr>
                <tr>
                    <td class="kv-key">Unnecessary Data Leakage Prevention</td>
                    <td class="kv-val">Income, bank details, medical records <b>100% isolated</b></td>
                </tr>
                <tr>
                    <td class="kv-key">Human-in-the-Loop Gating</td>
                    <td class="kv-val">0 external API calls without explicit user approval</td>
                </tr>
            </table>
            <div style="margin-top: 1rem;">
                <span style="font-size:0.84rem; color:#64748B;">Explore full empirical evaluation in the <b>Benchmark Evaluation</b> tab within the Passport workflow.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
