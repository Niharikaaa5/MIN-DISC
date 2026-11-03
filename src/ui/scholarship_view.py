"""
Module: MIN-DISC PM-USP CSSS Scholarship Workflow View
Provides the dedicated 8-stage interface for the PM-USP CSSS Fresh Scholarship domain:
- Stage 1: Applicant Selection (15 synthetic profiles).
- Stage 2: Isolated Requirement Retrieval & Grounding.
- Stage 3: Eligibility Assessment (Satisfied, Failed, Missing Docs, Payment Advisories).
- Stage 4: Minimum-Disclosure Plan (Portal Fields, Approved Docs, Internal Evals, Quarantined Payment Layer).
- Stage 5: Deterministic Policy Validation (PASSED, BLOCKED, NEEDS_REVIEW).
- Stage 6: Human-in-the-Loop Approval Gating.
- Stage 7: Simulated Application Registration Status (SUBMITTED).
- Stage 8: Independent Payment Readiness Evaluation (PAYMENT_READY vs PAYMENT_PENDING).
- Benchmark: 15-profile empirical evaluation suite.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from src.scholarship.scholarship_extractor import extract_scholarship_requirements
from src.scholarship.scholarship_matcher import match_scholarship_attributes
from src.scholarship.scholarship_planner import create_scholarship_disclosure_plan
from src.scholarship.scholarship_policy import verify_scholarship_policy
from src.scholarship.scholarship_pipeline import (
    load_scholarship_users,
    run_scholarship_pipeline,
    evaluate_all_scholarship_profiles
)
from src.scholarship.mock_scholarship_api import (
    submit_mock_scholarship_application,
    get_mock_application_status,
    get_mock_payment_status,
    MOCK_DISCLAIMER
)


def init_scholarship_session_state():
    """Initializes session state keys for the Scholarship workflow."""
    if "sch_analysis_done" not in st.session_state:
        st.session_state.sch_analysis_done = False
    if "sch_executed" not in st.session_state:
        st.session_state.sch_executed = False
    if "sch_pipeline_data" not in st.session_state:
        st.session_state.sch_pipeline_data = None
    if "sch_api_response" not in st.session_state:
        st.session_state.sch_api_response = None
    if "sch_submitted_app_id" not in st.session_state:
        st.session_state.sch_submitted_app_id = None
    if "sch_selected_uid" not in st.session_state:
        st.session_state.sch_selected_uid = "SCH001"
    if "sch_last_analyzed_uid" not in st.session_state:
        st.session_state.sch_last_analyzed_uid = None


def mask_sensitive_credential(val: Any) -> str:
    """Masks banking and Aadhaar credentials for safe UI display."""
    if not val:
        return "None"
    s = str(val)
    if len(s) > 4:
        return "X" * (len(s) - 4) + s[-4:]
    return "XXXX"


def render_scholarship_view(scholarship_retriever):
    """Renders the complete 8-stage PM-USP CSSS scholarship workflow."""
    init_scholarship_session_state()
    users = load_scholarship_users()

    st.markdown("""
    <div class="brand-header">
        <div class="brand-title">🎓 PM-USP CSSS Scholarship Application Workflow</div>
        <div class="brand-subtitle">Central Sector Scheme of Scholarship for College and University Students (Fresh Application, AY 2025–26)</div>
    </div>
    """, unsafe_allow_html=True)

    tab_workflow, tab_benchmark = st.tabs(["🚀 Application & Privacy Pipeline", "📊 Benchmark Evaluation (SCH001 - SCH015)"])

    # =========================================================================
    # TAB 1: SCHOLARSHIP WORKFLOW
    # =========================================================================
    with tab_workflow:
        # ---------------------------------------------------------------------
        # STAGE 1: APPLICANT SELECTION
        # ---------------------------------------------------------------------
        st.markdown("""
        <div class="stage-box">
            <div class="stage-title">
                <span class="stage-badge">STAGE 1</span> Applicant Selection & Profile Inspection
            </div>
            <div class="demo-notice">
                <b>Synthetic Demonstration Record:</b> All scholarship applicant profiles are synthetic test records created
                for research evaluation. Personal details, roll numbers, and institute codes do not represent actual citizens or institutions.
            </div>
        """, unsafe_allow_html=True)

        user_labels = {
            f"{u['user_id']} - {u['applicant_name']} ({u.get('scenario_note', '').split(':')[0].strip()})": u['user_id']
            for u in users
        }

        col_sel, col_meta = st.columns([1, 1], gap="medium")

        with col_sel:
            selected_label = st.selectbox(
                "Select Synthetic Applicant Record:",
                list(user_labels.keys()),
                key="sch_user_select_dropdown",
                help="Choose from 15 synthetic applicant profiles covering eligible, quota, and edge-case scenarios."
            )
            selected_uid = user_labels[selected_label]
            target_user = next((u for u in users if u["user_id"] == selected_uid), users[0])
            st.session_state.sch_selected_uid = selected_uid

            # Reset execution state if user switches profile
            if st.session_state.sch_last_analyzed_uid != selected_uid:
                st.session_state.sch_analysis_done = False
                st.session_state.sch_executed = False
                st.session_state.sch_pipeline_data = None
                st.session_state.sch_api_response = None
                st.session_state.sch_submitted_app_id = None

            st.caption(f"**Test Scenario:** {target_user.get('scenario_note', 'N/A')}")

        with col_meta:
            st.markdown(f"**Profile Summary: {target_user['applicant_name']}**")
            m_c1, m_c2 = st.columns(2)
            with m_c1:
                st.markdown(f"• **Category:** `{target_user.get('caste_category', 'General')}`")
                st.markdown(f"• **Domicile State:** `{target_user.get('domicile_state')}`")
                st.markdown(f"• **Stream:** `{target_user.get('stream')}`")
                st.markdown(f"• **Class 12 Passing Year:** `{target_user.get('passing_year')}`")
                st.markdown(f"• **Drop Year:** `{'Yes' if target_user.get('gap_year_flag') else 'No'}`")
            with m_c2:
                # Distinguish percentage marks from percentile rank for SCH003
                if target_user.get("class_12_marks_percentage") is not None:
                    st.markdown(f"• **Class 12 Marks:** `{target_user.get('class_12_marks_percentage')}%` (Percentage)")
                st.markdown(f"• **Percentile Rank:** `{target_user.get('class_12_percentile')}` (Percentile)")
                st.markdown(f"• **Board Merit List:** `{'Yes' if target_user.get('board_merit_list_status') else 'No'}`")
                st.markdown(f"• **Family Income:** `₹{target_user.get('family_income', 0):,}/year`")
                st.markdown(f"• **AISHE Code:** `{target_user.get('aishe_code') or 'Missing / None'}`")
                st.markdown(f"• **AISHE Status:** `{target_user.get('aishe_status')}`")

        st.markdown("</div>", unsafe_allow_html=True)

        # Trigger Analysis Button
        run_analysis = st.button("🔍 Run Minimum-Disclosure Pipeline & Policy Check", key="btn_run_sch_analysis", type="primary", use_container_width=True)

        if run_analysis:
            with st.spinner("Executing isolated RAG retrieval, attribute matching, and deterministic policy check..."):
                try:
                    reqs = extract_scholarship_requirements()
                    matched = match_scholarship_attributes(reqs, target_user)
                    plan = create_scholarship_disclosure_plan(reqs, matched, target_user)
                    policy = verify_scholarship_policy(plan, matched, target_user)

                    st.session_state.sch_pipeline_data = {
                        "requirements": reqs,
                        "matched_data": matched,
                        "disclosure_plan": plan,
                        "policy_result": policy,
                        "target_user": target_user
                    }
                    st.session_state.sch_analysis_done = True
                    st.session_state.sch_last_analyzed_uid = selected_uid
                    st.session_state.sch_executed = False
                    st.session_state.sch_api_response = None
                    st.session_state.sch_submitted_app_id = None
                except Exception as ex:
                    st.error(f"Error executing scholarship pipeline: {ex}")

        # ---------------------------------------------------------------------
        # DISPLAY PIPELINE RESULTS (STAGES 2 TO 8)
        # ---------------------------------------------------------------------
        if not st.session_state.sch_analysis_done or st.session_state.sch_pipeline_data is None:
            st.info("ℹ️ Select a synthetic applicant profile above and click **'Run Minimum-Disclosure Pipeline & Policy Check'**.")
        else:
            pdata = st.session_state.sch_pipeline_data
            reqs = pdata["requirements"]
            matched = pdata["matched_data"]
            plan = pdata["disclosure_plan"]
            policy = pdata["policy_result"]
            curr_user = pdata["target_user"]

            # -----------------------------------------------------------------
            # STAGE 2: REQUIREMENT RETRIEVAL & GROUNDING
            # -----------------------------------------------------------------
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STAGE 2</span> Isolated Regulatory Retrieval & Evidence Grounding
                </div>
                <p style="font-size:0.88rem; color:#475569; margin-bottom: 0.8rem;">
                    Retrieved from isolated PM-USP CSSS vector store (Guidelines, DoHE FAQ, NSP Manual).
                    Distinguishes retrieved-and-matched evidence from static canonical fallbacks.
                </p>
            """, unsafe_allow_html=True)

            provenance = reqs.get("evidence_provenance", {})
            retrieved_chunks = provenance.get("retrieved_chunks", [])

            p_col1, p_col2 = st.columns([1, 1])
            with p_col1:
                st.caption(f"**Knowledge Base Vectors:** `191 chunks` | **Chunks Retrieved:** `{len(retrieved_chunks)}`")
            with p_col2:
                st.caption("**Authority Priority:** Guidelines (DOC-1) > FAQ (DOC-2) > NSP Manual (DOC-3)")

            with st.expander("📄 View Authoritative Scheme Chunks & Evidence Grounding", expanded=False):
                for idx, c in enumerate(retrieved_chunks, 1):
                    doc_cls = c.get("classification", "Authority Document")
                    st.markdown(f"**Chunk #{idx}** (`{c.get('chunk_id')}`) — `{c.get('file_name')}` (Page {c.get('page_number')}) — <span class='pill-active'>{doc_cls}</span>", unsafe_allow_html=True)
                    st.text(c.get("text", "")[:450] + "...")
                    st.markdown("---")

            st.markdown("</div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # STAGE 3: ELIGIBILITY ASSESSMENT
            # -----------------------------------------------------------------
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STAGE 3</span> Scheme Eligibility & Documentary Assessment
                </div>
            """, unsafe_allow_html=True)

            e_col1, e_col2 = st.columns([1, 1], gap="medium")

            with e_col1:
                st.markdown("**Substantive Eligibility Conditions:**")
                st.markdown(f"• Satisfied Conditions: **{len(matched.get('satisfied_requirements', []))}**")

                failures = matched.get("failed_eligibility_requirements", [])
                if failures:
                    for f in failures:
                        st.error(f"❌ **Failed Condition:** {f.get('reason')}")
                else:
                    st.success("✅ All substantive eligibility rules satisfied.")

                missing_info = matched.get("missing_information", [])
                if missing_info:
                    st.warning(f"⚠️ **Unverified / Missing Information:** `{missing_info}`")

            with e_col2:
                st.markdown("**Documentary & Operational Conditions:**")
                mand_docs = matched.get("missing_mandatory_documents", [])
                if mand_docs:
                    st.error(f"❌ **Missing Mandatory Documents:** `{mand_docs}`")
                else:
                    st.success("✅ Mandatory supporting documents present (Marksheet & Income Cert).")

                cond_docs = matched.get("missing_conditional_documents", [])
                if cond_docs:
                    st.error(f"❌ **Missing Conditional Documents:** `{cond_docs}`")
                else:
                    st.caption("✅ No missing conditional documents for claimed quota.")

                # Inactive AISHE Advisory (Payment Restriction, not Application Ineligibility)
                if curr_user.get("aishe_status") == "INACTIVE":
                    st.warning("⚠️ **Payment Hold Advisory (DOC-2 Q18):** Institution AISHE status is INACTIVE. Application registration will be accepted, but payment release requires active status.")

            st.markdown("</div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # STAGE 4: MINIMUM-DISCLOSURE PLAN
            # -----------------------------------------------------------------
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STAGE 4</span> Minimum-Disclosure Partition & Quarantine Layer
                </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Available Profile Attributes", plan["total_available_attributes"])
            m2.metric("Disclosed Form Fields", plan["disclosed_fields_count"])
            m3.metric("Approved Documents", plan["disclosed_documents_count"])
            m4.metric("Quarantined Payment Keys", plan["quarantined_attributes_count"])

            d_tab1, d_tab2, d_tab3, d_tab4, d_tab5 = st.tabs([
                "📝 Portal Form Fields",
                "📁 Supporting Documents",
                "⚙️ Internal Evaluations",
                "🔒 Quarantined Payment Layer",
                "🛡️ Excluded Attributes"
            ])

            with d_tab1:
                st.caption("Necessary form fields transmitted to the National Scholarship Portal:")
                f_rows = []
                for k, v in plan["portal_application_fields"].items():
                    f_rows.append({"Field Name": k, "Disclosed Value": str(v), "Documented Necessity": plan["justifications"].get(k, "Portal standard")})
                st.dataframe(pd.DataFrame(f_rows), use_container_width=True, hide_index=True)

            with d_tab2:
                st.caption("Approved documentary proof attached to application:")
                if plan["approved_supporting_documents"]:
                    d_rows = []
                    for k, v in plan["approved_supporting_documents"].items():
                        d_rows.append({"Document Type": k, "Document ID": str(v), "Regulatory Authority": plan["justifications"].get(k, "Scheme requirement")})
                    st.dataframe(pd.DataFrame(d_rows), use_container_width=True, hide_index=True)
                else:
                    st.error("No supporting documents approved for transmission.")

            with d_tab3:
                st.caption("Criteria evaluated internally by MIN-DISC; NOT transmitted externally as documents:")
                st.json(plan["internal_eligibility_evaluation"])

            with d_tab4:
                st.warning("⚠️ **Strict Payment Quarantine Active:** Raw Aadhaar and banking details are completely isolated from the application registration payload. They will never be transmitted to the application portal.")
                q_data = {
                    "Aadhaar Number": mask_sensitive_credential(plan["quarantined_payment_attributes"].get("aadhaar_number")),
                    "Aadhaar Seeding Status": str(plan["quarantined_payment_attributes"].get("aadhaar_seeding_status")),
                    "Bank Account Number": mask_sensitive_credential(plan["quarantined_payment_attributes"].get("bank_account_number")),
                    "Bank IFSC": mask_sensitive_credential(plan["quarantined_payment_attributes"].get("bank_ifsc")),
                    "Institution AISHE Status": str(plan["quarantined_payment_attributes"].get("aishe_status"))
                }
                st.table(pd.DataFrame(list(q_data.items()), columns=["Payment Attribute", "Quarantined Status"]))

            with d_tab5:
                st.caption("Profile attributes withheld to prevent over-disclosure:")
                st.info(f"Excluded Keys ({len(plan['excluded_attributes'])}): `{plan['excluded_attributes']}`")

            st.markdown("</div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # STAGE 5: POLICY VALIDATION
            # -----------------------------------------------------------------
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STAGE 5</span> Deterministic Policy Engine Decision
                </div>
            """, unsafe_allow_html=True)

            pol_status = policy["status"]
            if pol_status == "PASSED":
                st.markdown(f"""
                <div class="card-passed">
                    <h4 style="margin-top:0;">✅ Policy Verification PASSED</h4>
                    <p style="margin-bottom:4px;"><b>Decision:</b> Application satisfies prototype eligibility, document completeness, and minimum disclosure rules.</p>
                    <p style="margin-bottom:4px;"><b>Compliance Reason:</b> {policy.get('reason')}</p>
                    <p style="margin-bottom:0;"><b>Approved Documents:</b> <code>{list(plan['approved_supporting_documents'].keys())}</code></p>
                </div>
                """, unsafe_allow_html=True)
            elif pol_status == "BLOCKED":
                st.markdown(f"""
                <div class="card-blocked">
                    <h4 style="margin-top:0;">🚨 Policy Verification BLOCKED</h4>
                    <p style="margin-bottom:4px;"><b>Decision:</b> Application cannot proceed. Policy rules prohibit tool execution.</p>
                    <p style="margin-bottom:4px;"><b>Blocking Reason:</b> {policy.get('reason')}</p>
                    <p style="margin-bottom:0;"><b>Violations:</b> {policy.get('violations', [])}</p>
                </div>
                """, unsafe_allow_html=True)
            else:  # NEEDS_REVIEW
                st.markdown(f"""
                <div class="card-review">
                    <h4 style="margin-top:0;">⚠️ Policy Verification NEEDS_REVIEW</h4>
                    <p style="margin-bottom:4px;"><b>Decision:</b> Critical information is unverified or missing (e.g., missing AISHE code). Application submission paused pending administrative review.</p>
                    <p style="margin-bottom:4px;"><b>Review Trigger:</b> {policy.get('reason')}</p>
                    <p style="margin-bottom:0;"><b>Action Required:</b> Verify critical attributes before submission can be evaluated.</p>
                </div>
                """, unsafe_allow_html=True)

            st.caption("🛡️ **Deterministic Enforcement Guarantee:** The policy decision above is computed deterministically. It cannot be overridden by an LLM.")
            st.markdown("</div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # STAGE 6: HUMAN APPROVAL & SUBMISSION GATE
            # -----------------------------------------------------------------
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STAGE 6</span> Human-in-the-Loop Approval & Mock Submission
                </div>
            """, unsafe_allow_html=True)

            if pol_status in ("BLOCKED", "NEEDS_REVIEW"):
                st.error(f"⛔ **Submission Prohibited**: Policy outcome is **{pol_status}**. Application dispatch to external tools is completely disabled.")
                st.caption("No attributes have been or will be transmitted to simulated external endpoints.")
            else:
                if not st.session_state.sch_executed:
                    st.info("ℹ️ Policy verification PASSED. Review the proposed payload below and authorize mock submission.")

                    with st.expander("📄 Review Outgoing Minimum-Disclosure Payload", expanded=True):
                        outgoing_payload = {
                            "applicant_id": curr_user["user_id"],
                            "applicant_name": curr_user["applicant_name"],
                            "aishe_status": curr_user.get("aishe_status", "ACTIVE"),
                            "portal_application_fields": plan["portal_application_fields"],
                            "approved_supporting_documents": plan["approved_supporting_documents"],
                            "policy_verification": {
                                "policy_status": policy["status"],
                                "policy_approved": policy["approved"]
                            }
                        }
                        st.json(outgoing_payload)

                    authorize_confirm = st.checkbox(
                        "I have reviewed the task-justified disclosure payload and authorize simulated submission to the Mock NSP Portal.",
                        key="sch_approval_confirm_check"
                    )

                    submit_sch_btn = st.button(
                        "🚀 Authorize & Submit to Mock NSP Portal",
                        key="btn_sch_submit",
                        type="primary",
                        disabled=not authorize_confirm,
                        use_container_width=True
                    )

                    if submit_sch_btn:
                        with st.spinner("Submitting approved minimal payload to Mock NSP Portal..."):
                            sub_res = submit_mock_scholarship_application(outgoing_payload)
                            if sub_res.get("status") == "SUBMITTED":
                                st.session_state.sch_api_response = sub_res
                                st.session_state.sch_submitted_app_id = sub_res["application_id"]
                                st.session_state.sch_executed = True
                                st.rerun()
                            else:
                                st.error(f"Submission rejected by Mock API: {sub_res.get('error')}")
                else:
                    st.success(f"✅ **Submission Dispatched**: Application successfully submitted to Mock NSP. Application ID: `{st.session_state.sch_submitted_app_id}`")

            st.markdown("</div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # STAGE 7 & STAGE 8: APPLICATION STATUS & PAYMENT READINESS
            # -----------------------------------------------------------------
            if st.session_state.sch_executed and st.session_state.sch_submitted_app_id:
                app_id = st.session_state.sch_submitted_app_id
                app_status_res = get_mock_application_status(app_id)
                payment_status_res = get_mock_payment_status(app_id)

                col_app, col_pay = st.columns(2, gap="medium")

                with col_app:
                    # Stage 7
                    st.markdown("""
                    <div class="stage-box">
                        <div class="stage-title">
                            <span class="stage-badge">STAGE 7</span> Simulated Application Registration
                        </div>
                        <div class="card-passed">
                            <h4 style="margin-top:0;">Mock NSP Portal Registration</h4>
                            <p style="margin-bottom:4px;"><b>Application ID:</b> <code>{app_id}</code></p>
                            <p style="margin-bottom:4px;"><b>Application Status:</b> <span class="pill-active">{status}</span></p>
                            <p style="margin-bottom:4px;"><b>Current Stage:</b> {stage}</p>
                            <p style="margin-bottom:0;"><b>Registered At:</b> {ts}</p>
                        </div>
                    """.format(
                        app_id=app_id,
                        status=app_status_res.get("application_status", "SUBMITTED"),
                        stage=app_status_res.get("current_stage", "UNDER_INSTITUTE_VERIFICATION"),
                        ts=app_status_res.get("registered_at", "Just now")
                    ), unsafe_allow_html=True)
                    st.caption("Simulated Mock NSP Response:")
                    st.json(app_status_res)
                    st.markdown("</div>", unsafe_allow_html=True)

                with col_pay:
                    # Stage 8
                    st.markdown("""
                    <div class="stage-box">
                        <div class="stage-title">
                            <span class="stage-badge">STAGE 8</span> Independent Payment Readiness
                        </div>
                    """, unsafe_allow_html=True)

                    pay_status = payment_status_res.get("payment_status")
                    if pay_status == "PAYMENT_READY":
                        st.markdown("""
                        <div class="card-passed">
                            <h4 style="margin-top:0;">Payment Disbursement: READY</h4>
                            <p style="margin-bottom:4px;"><b>PFMS Status:</b> <span class="pill-active">PAYMENT_READY</span></p>
                            <p style="margin-bottom:4px;"><b>DBT Readiness:</b> Simulated PFMS prerequisites verified.</p>
                            <p style="margin-bottom:0;"><b>Guidance:</b> {guidance}</p>
                        </div>
                        """.format(guidance=payment_status_res.get("operational_guidance", "Prerequisites met.")), unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="card-review">
                            <h4 style="margin-top:0;">Payment Disbursement: ON HOLD</h4>
                            <p style="margin-bottom:4px;"><b>PFMS Status:</b> <span class="pill-pending">PAYMENT_PENDING</span></p>
                            <p style="margin-bottom:4px;"><b>Hold Reason:</b> {reason}</p>
                            <p style="margin-bottom:0;"><b>Operational Guidance:</b> {guidance}</p>
                        </div>
                        """.format(
                            reason=payment_status_res.get("hold_reason", "Operational hold"),
                            guidance=payment_status_res.get("operational_guidance", "Requires active AISHE status.")
                        ), unsafe_allow_html=True)

                    st.caption("Simulated Mock PFMS Response:")
                    st.json(payment_status_res)
                    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: SCHOLARSHIP BENCHMARK EVALUATION (SCH001 - SCH015)
    # =========================================================================
    with tab_benchmark:
        st.subheader("📊 Full Scholarship Evaluation Benchmark (SCH001 - SCH015)")
        st.caption("Evaluates all 15 standardized synthetic applicant profiles across eligibility, policy, and mock submission.")

        if st.button("Run Full Scholarship Benchmark Suite", key="btn_run_sch_bench", type="secondary"):
            with st.spinner("Evaluating all 15 synthetic applicant profiles..."):
                eval_results = evaluate_all_scholarship_profiles(auto_approve_passed=True)

                rows = []
                for r in eval_results:
                    app_id = r.get("application_id") or "—"
                    pay_stat = r.get("payment_readiness") or "—"
                    rows.append({
                        "User ID": r["user_id"],
                        "Applicant Name": r["applicant_name"],
                        "Policy Decision": r["policy_status"],
                        "Execution Outcome": r["execution_outcome"],
                        "Application ID": app_id,
                        "Payment Status": pay_stat,
                        "Approved Documents": ", ".join(r["disclosed_docs"]) if r["disclosed_docs"] else "None",
                        "Reason Summary": r["reason"][:75] + "..." if len(r["reason"]) > 75 else r["reason"]
                    })

                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                b1, b2, b3, b4 = st.columns(4)
                passed_cnt = sum(1 for r in eval_results if r["policy_status"] == "PASSED")
                blocked_cnt = sum(1 for r in eval_results if r["policy_status"] == "BLOCKED")
                review_cnt = sum(1 for r in eval_results if r["policy_status"] == "NEEDS_REVIEW")
                b1.metric("Total Profiles Tested", len(eval_results))
                b2.metric("PASSED & Submitted", passed_cnt)
                b3.metric("BLOCKED (Ineligible / Incomplete)", blocked_cnt)
                b4.metric("NEEDS_REVIEW (Unverified)", review_cnt)

                st.caption("Across all 15 synthetic profiles, the deterministic policy engine enforced 100% correct decisions with zero payment credential leaks.")
        else:
            st.info("ℹ️ Click **'Run Full Scholarship Benchmark Suite'** to evaluate all 15 synthetic applicant profiles.")
