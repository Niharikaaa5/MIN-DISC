"""
Module: MIN-DISC Landing Dashboard View
Presents the central project overview, explanation of minimum-disclosure planning,
and interactive cards for navigating to the Passport and Scholarship workflows.
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
        All user profiles are fully synthetic test records. No calls are made to actual government portals (Passport Seva, NSP, PFMS, UIDAI).
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Supported Application Workflows")
    st.caption("Select a workflow card to launch the privacy-preserving application and disclosure pipeline:")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="workflow-card">
            <div class="workflow-title">
                <span>🛂 Fresh Passport Application</span>
                <span class="pill-active">ACTIVE PROTOTYPE</span>
            </div>
            <div class="workflow-desc">
                Automated document necessity extraction and minimum-disclosure planning for fresh Indian ordinary passport applications.
            </div>
            <div class="workflow-meta-item"><b>Target Scope:</b> Adult (18+) | Ordinary Case | Normal Application</div>
            <div class="workflow-meta-item"><b>Authority Source:</b> Official Passport Rules & Document Booklet (CPV Division)</div>
            <div class="workflow-meta-item"><b>Privacy Defenses:</b> Address Proof (mandatory), DOB Proof (mandatory), Non-ECR Proof (conditional matriculation), blocks all unnecessary sensitive demographic attributes.</div>
            <div class="workflow-meta-item"><b>Synthetic Dataset:</b> 10 standardized synthetic profiles (U001 - U010)</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Launch Passport Workflow", key="btn_launch_passport", use_container_width=True, type="primary"):
            st.session_state.active_view = "passport"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="workflow-card">
            <div class="workflow-title">
                <span>🎓 PM-USP CSSS Scholarship</span>
                <span class="pill-active">ACTIVE PROTOTYPE</span>
            </div>
            <div class="workflow-desc">
                Minimum-disclosure planning and deterministic policy engine for the Central Sector Scheme of Scholarship for College and University Students.
            </div>
            <div class="workflow-meta-item"><b>Target Scope:</b> Fresh Application | Academic Year 2025–26</div>
            <div class="workflow-meta-item"><b>Authority Sources:</b> Official CSSS Guidelines (DOC-1) > DoHE Official FAQ (DOC-2) > NSP Training Manual (DOC-3)</div>
            <div class="workflow-meta-item"><b>Privacy Defenses:</b> Payment Layer Quarantine (raw Aadhaar/IFSC/Account isolated), over-disclosure prevention (General barred from caste docs; non-PwD barred from medical docs), decoupled application status vs payment readiness.</div>
            <div class="workflow-meta-item"><b>Synthetic Dataset:</b> 15 standardized synthetic profiles (SCH001 - SCH015)</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Launch Scholarship Workflow", key="btn_launch_scholarship", use_container_width=True, type="primary"):
            st.session_state.active_view = "scholarship"
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
                <li><b>Isolated RAG Retrieval:</b> Query domain-specific FAISS vector stores to retrieve authoritative regulatory chunks.</li>
                <li><b>Requirement Extraction:</b> Extract structured task requirements and determine exact documentary evidence conditions.</li>
                <li><b>Attribute Matching:</b> Map available applicant attributes against requirements and classify into satisfied, failed, or missing.</li>
                <li><b>Minimum-Disclosure Planning:</b> Synthesize minimal transmission payload; quarantine sensitive banking details; document disclosure reasons.</li>
                <li><b>Deterministic Policy Engine:</b> Rigorous defense-in-depth policy verification (PASSED, BLOCKED, NEEDS_REVIEW).</li>
                <li><b>Human-in-the-Loop Gating:</b> Require explicit human authorization before external submission.</li>
                <li><b>Simulated Mock Submission:</b> External tool API verifies zero payment credential leakage and records registration.</li>
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
                MIN-DISC evaluates disclosure reduction across standardized synthetic datasets:
            </p>
            <table class="kv-table">
                <tr>
                    <td class="kv-key">Passport Workflow (10 Profiles)</td>
                    <td class="kv-val"><b>86.3%</b> average attribute disclosure reduction</td>
                </tr>
                <tr>
                    <td class="kv-key">Scholarship Workflow (15 Profiles)</td>
                    <td class="kv-val"><b>100%</b> accurate policy enforcement; 0 payment credential leaks</td>
                </tr>
                <tr>
                    <td class="kv-key">Quarantined Payment Layer</td>
                    <td class="kv-val">Raw Aadhaar, Bank Account, IFSC isolated across 100% of cases</td>
                </tr>
                <tr>
                    <td class="kv-key">Over-Disclosure Defense</td>
                    <td class="kv-val">Blocks unneeded reservation/disability documents with 0 false passes</td>
                </tr>
            </table>
            <div style="margin-top: 1rem;">
                <span style="font-size:0.84rem; color:#64748B;">Explore full results in the <b>Benchmark Evaluation</b> tabs in the sidebar.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
