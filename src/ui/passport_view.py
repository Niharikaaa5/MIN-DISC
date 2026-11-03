"""
Module: MIN-DISC Fresh Passport Application Workflow View
Provides the dedicated UI for the Fresh Passport Application domain:
- Applicant profile selection (U001 - U010).
- Isolated Passport RAG retrieval & requirement extraction.
- Attribute matching & minimum-disclosure planning.
- Deterministic policy verification.
- Human-in-the-loop approval gating & mock passport submission.
- Full 10-profile empirical evaluation benchmark.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from src.llm import LLMClient
from src.requirement_extractor import extract_requirements
from src.attribute_matcher import match_user_attributes
from src.disclosure_planner import create_disclosure_plan
from src.policy_checker import verify_privacy_policy
from src.mock_passport_api import execute_mock_api_call
from src.evaluation import run_evaluation_suite, load_users


def init_passport_session_state():
    """Initializes session state for the Passport workflow."""
    if "passport_analysis_done" not in st.session_state:
        st.session_state.passport_analysis_done = False
    if "passport_executed" not in st.session_state:
        st.session_state.passport_executed = False
    if "passport_pipeline_data" not in st.session_state:
        st.session_state.passport_pipeline_data = None
    if "passport_api_response" not in st.session_state:
        st.session_state.passport_api_response = None
    if "passport_analyzed_config" not in st.session_state:
        st.session_state.passport_analyzed_config = None
    if "passport_execution_error" not in st.session_state:
        st.session_state.passport_execution_error = None


def render_passport_view(retriever):
    """Renders the complete Fresh Passport application workflow."""
    init_passport_session_state()
    users = load_users()

    st.markdown("""
    <div class="brand-header">
        <div class="brand-title">🛂 Fresh Passport Application Workflow</div>
        <div class="brand-subtitle">Standardized Minimum-Disclosure Pipeline for Indian Ordinary Passports</div>
    </div>
    """, unsafe_allow_html=True)

    tab_app, tab_bench = st.tabs(["🚀 Application & Privacy Pipeline", "📊 Benchmark Evaluation (U001 - U010)"])

    with tab_app:
        # ---------------------------------------------------------------------
        # STAGE 1: REQUEST CONFIGURATION
        # ---------------------------------------------------------------------
        st.markdown("""
        <div class="stage-box">
            <div class="stage-title">
                <span class="stage-badge">STAGE 1</span> Applicant Selection & Request Configuration
            </div>
        """, unsafe_allow_html=True)

        user_options = {f"{u['user_id']} - {u['name']}": u['user_id'] for u in users}
        form_col1, form_col2 = st.columns([1, 1], gap="medium")

        with form_col1:
            st.markdown("**1. Synthetic Applicant Profile**")
            selected_user_label = st.selectbox(
                "Select Applicant Record:",
                list(user_options.keys()),
                key="passport_user_select",
                help="Select one of the 10 standardized synthetic applicant profiles."
            )
            selected_user_id = user_options[selected_user_label]
            target_user = next((u for u in users if u["user_id"] == selected_user_id), None)

            if target_user:
                non_null_attrs = [k for k, v in target_user.items() if v is not None and k not in ["user_id", "name"]]
                has_addr = bool(target_user.get("address_proof"))
                has_dob = bool(target_user.get("date_of_birth_proof"))
                has_acad = bool(target_user.get("academic_record"))

                with st.expander(f"👤 Profile Attributes: {target_user['name']} ({target_user['user_id']})", expanded=False):
                    st.caption(f"**Available Profile Keys ({len(non_null_attrs)})**: `{', '.join(non_null_attrs)}`")
                    p_c1, p_c2, p_c3 = st.columns(3)
                    p_c1.markdown(f"Address Proof: **{'✅ Present' if has_addr else '❌ Missing'}**")
                    p_c2.markdown(f"DOB Proof: **{'✅ Present' if has_dob else '❌ Missing'}**")
                    p_c3.markdown(f"Non-ECR Proof: **{'✅ Present' if has_acad else '❌ Missing'}**")

            st.markdown("**2. Natural Language Request**")
            task_input = st.text_input(
                "User Task Description:",
                value="I want to apply for a fresh passport.",
                key="passport_task_input"
            )

        with form_col2:
            st.markdown("**3. Scope & Eligibility Settings**")
            cat_c1, cat_c2 = st.columns(2)
            with cat_c1:
                applicant_category = st.selectbox(
                    "Applicant Category:",
                    ["Adult (18+)", "Minor (Under 18)"],
                    index=0,
                    key="passport_cat_select"
                )
            with cat_c2:
                application_type = st.selectbox(
                    "Application Type:",
                    ["Normal", "Tatkaal"],
                    index=0,
                    key="passport_type_select"
                )

            st.caption("📍 **Target Scope**: Fresh Passport | Adult (18+) | Ordinary Case | Citizen of India by birth | Normal")

            st.markdown("**4. Conditional Non-ECR Requirement**")
            requires_non_ecr = st.checkbox(
                "Explicitly require Non-ECR proof",
                value=False,
                key="passport_non_ecr_check",
                help="Check only if applicant task explicitly establishes need for Non-ECR documentary proof."
            )
            st.caption("When enabled, documentary proof of Non-ECR eligibility (academic record) becomes a required supporting document.")

        st.markdown("</div>", unsafe_allow_html=True)

        current_config = {
            "user_id": selected_user_id,
            "task_input": task_input,
            "applicant_category": applicant_category,
            "application_type": application_type,
            "requires_non_ecr": requires_non_ecr,
        }

        is_stale = (
            st.session_state.passport_analysis_done
            and st.session_state.passport_analyzed_config is not None
            and st.session_state.passport_analyzed_config != current_config
        )

        # ---------------------------------------------------------------------
        # STAGE 2: ANALYSIS & PRIVACY REVIEW TRIGGER
        # ---------------------------------------------------------------------
        st.markdown("""
        <div class="stage-box">
            <div class="stage-title">
                <span class="stage-badge">STAGE 2</span> Requirement Analysis & Disclosure Planning
            </div>
            <p style="font-size:0.88rem; color:#475569; margin-bottom: 0.8rem;">
                Retrieves authoritative requirement evidence from official passport booklets (RAG), matches attributes,
                formulates a minimum-disclosure plan, and enforces deterministic privacy policy checks. No external tool is invoked.
            </p>
        """, unsafe_allow_html=True)

        run_analysis = st.button("🔍 Analyze Requirements & Plan Disclosure", key="btn_run_passport_analysis", type="primary", use_container_width=True)

        if run_analysis:
            with st.spinner("Retrieving authoritative evidence, matching attributes, and formulating privacy plan..."):
                try:
                    retrieved_chunks = retriever.retrieve(task_input, top_k=5)
                    llm_client = LLMClient()
                    extracted_reqs = extract_requirements(retrieved_chunks, task_name=task_input, llm_client=llm_client)
                    matched_data = match_user_attributes(extracted_reqs, target_user)
                    plan = create_disclosure_plan(
                        task_name="fresh passport application",
                        extracted_requirements=extracted_reqs,
                        matched_data=matched_data,
                        user_profile=target_user,
                        requires_non_ecr=requires_non_ecr
                    )
                    policy_res = verify_privacy_policy(plan, matched_data, target_user, requires_non_ecr=requires_non_ecr)

                    st.session_state.passport_pipeline_data = {
                        "target_user": target_user,
                        "task_input": task_input,
                        "applicant_category": applicant_category,
                        "application_type": application_type,
                        "requires_non_ecr": requires_non_ecr,
                        "retrieved_chunks": retrieved_chunks,
                        "extracted_reqs": extracted_reqs,
                        "matched_data": matched_data,
                        "disclosure_plan": plan,
                        "policy_res": policy_res,
                    }
                    st.session_state.passport_analyzed_config = current_config
                    st.session_state.passport_analysis_done = True
                    st.session_state.passport_executed = False
                    st.session_state.passport_api_response = None
                    st.session_state.passport_execution_error = None
                    is_stale = False
                except Exception as err:
                    st.error(f"Error during analysis pipeline: {err}")

        st.markdown("</div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # STAGE 2 RESULTS
        # ---------------------------------------------------------------------
        if not st.session_state.passport_analysis_done or st.session_state.passport_pipeline_data is None:
            st.info("ℹ️ Select an applicant profile above and click **'Analyze Requirements & Plan Disclosure'** to run the pipeline.")
        else:
            if is_stale:
                st.warning("⚠️ **Configuration Changed**: Request settings have been modified. Please re-run analysis before submitting.")

            p_data = st.session_state.passport_pipeline_data
            analyzed_user = p_data["target_user"]
            extracted_reqs = p_data["extracted_reqs"]
            matched_data = p_data["matched_data"]
            plan = p_data["disclosure_plan"]
            policy_res = p_data["policy_res"]
            retrieved_chunks = p_data["retrieved_chunks"]

            st.markdown(f"#### Privacy Review for Applicant: **{analyzed_user['name']}** (`{analyzed_user['user_id']}`)")

            # A. Extracted Requirements
            st.markdown("##### A. Extracted Requirements & Authoritative Evidence")
            req_table_rows = []
            for req in extracted_reqs.get("requirements", []):
                req_type = req.get("type", "supporting_document")
                doc_no = req.get("document_no")
                doc_str = f"Doc #{doc_no}: " if doc_no is not None else ""
                full_req_title = f"{doc_str}{req['requirement']}"
                status_display = "Mandatory" if req.get("status") == "mandatory" else "Conditional"
                mapped_attr = req.get("mapped_attribute") or "None"
                src_file = req.get("source_file") or "Passport Document Standard"
                src_page = f"p. {req.get('source_page')}" if req.get("source_page") is not None else "—"

                req_table_rows.append({
                    "Requirement": full_req_title,
                    "Category": req_type,
                    "Status": status_display,
                    "Mapped Profile Key": mapped_attr,
                    "Authoritative Source": src_file,
                    "Page": src_page,
                    "Chunk ID": req.get("source_chunk_id") or "—"
                })

            st.dataframe(pd.DataFrame(req_table_rows), use_container_width=True, hide_index=True)

            with st.expander("📄 View Authoritative Retrieval Excerpts", expanded=False):
                for idx, c in enumerate(retrieved_chunks, 1):
                    tag = "📘 Primary Instruction Booklet" if c.get("is_primary") else "📄 Supporting Document"
                    st.markdown(f"**Chunk #{idx}** (`{c.get('chunk_id')}`) — `{c.get('file_name')}` (Page {c.get('page_number')}) — {tag}")
                    st.text(c.get("text", ""))
                    st.markdown("---")

            # B. Attribute Matching
            st.markdown("##### B. Requirement to User-Attribute Matching")
            match_table_data = []
            for req_name, details in matched_data.get("mapping", {}).items():
                val = details["value"] if details["value"] is not None else "MISSING / NULL"
                match_table_data.append({
                    "Task Requirement": req_name,
                    "Category": details.get("type", "supporting_document"),
                    "Status": details.get("status", "mandatory").upper(),
                    "Profile Attribute": str(details.get("attribute_key")),
                    "Present in Profile": "Yes" if details.get("present_in_profile") else "Missing",
                    "Attribute Value": str(val)
                })
            st.table(pd.DataFrame(match_table_data))

            missing_reqs = plan.get("missing_mandatory_attributes") or matched_data.get("missing_mandatory_attributes", [])
            if missing_reqs:
                st.warning(f"⚠️ **Missing Mandatory Requirement(s)**: `{missing_reqs}`. Profile lacks documentary proof.")

            # C. Minimum Disclosure Metrics
            st.markdown("##### C. Minimum-Disclosure Plan & Metrics")
            base_count = plan["total_user_attributes_count"]
            min_count = plan["disclosed_attributes_count"] if policy_res["approved"] else 0
            prevented_count = base_count - min_count
            reduction_pct = round((1 - (min_count / base_count)) * 100, 1) if base_count > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Available Profile Attributes", f"{base_count}")
            m2.metric("Approved for Proposed Payload", f"{min_count}")
            m3.metric("Excluded from Proposed Payload", f"{prevented_count}")
            m4.metric("Disclosure Reduction Ratio", f"{reduction_pct}%")

            plan_c1, plan_c2 = st.columns(2, gap="medium")
            with plan_c1:
                st.markdown("**Approved for Transmission:**")
                if policy_res["approved"]:
                    st.success(f"Attributes ({len(plan['approved_attributes'])}): `{plan['approved_attributes']}`")
                else:
                    st.error("None (Transmission Blocked by Policy Engine)")

            with plan_c2:
                st.markdown("**Excluded to Prevent Over-Disclosure:**")
                st.info(f"Attributes ({len(plan['excluded_attributes'])}): `{plan['excluded_attributes']}`")

            # D. Policy Validation
            st.markdown("##### D. Deterministic Privacy Policy Decision")
            if policy_res["approved"]:
                st.markdown(f"""
                <div class="card-passed">
                    <h4 style="margin-top:0;">Policy Verification PASSED</h4>
                    <p style="margin-bottom:4px;"><b>Decision:</b> Disclosure Plan Approved for Tool Transmission.</p>
                    <p style="margin-bottom:4px;"><b>Policy Justification:</b> {policy_res['reason']}</p>
                    <p style="margin-bottom:0;"><b>Approved Attributes:</b> <code>{plan['approved_attributes']}</code></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="card-blocked">
                    <h4 style="margin-top:0;">Policy Verification BLOCKED</h4>
                    <p style="margin-bottom:4px;"><b>Decision:</b> Tool Execution Prohibited.</p>
                    <p style="margin-bottom:4px;"><b>Blocking Reason:</b> {policy_res['reason']}</p>
                    <p style="margin-bottom:0;"><b>Transmission Status:</b> 0 attributes authorized for transmission.</p>
                </div>
                """, unsafe_allow_html=True)

            # E. Proposed Payload
            st.markdown("##### E. Proposed Disclosure Payload Preview")
            if policy_res["approved"]:
                st.json(plan["approved_payload"])
            else:
                st.warning("⚠️ No payload generated. Request failed deterministic policy verification.")

            st.markdown("---")

            # -----------------------------------------------------------------
            # STAGE 3: SUBMISSION AUTHORIZATION
            # -----------------------------------------------------------------
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STAGE 3</span> Submission Authorization
                </div>
            """, unsafe_allow_html=True)

            if not policy_res["approved"]:
                st.error("⛔ **Submission Blocked**: Policy verification failed. External service execution cannot proceed.")
                st.caption("Zero attributes have been or will be transmitted to external endpoints.")
            elif is_stale:
                st.warning("⚠️ **Submission Disabled**: Settings modified. Re-run analysis to generate an up-to-date plan.")
            else:
                if not st.session_state.passport_executed:
                    st.info("ℹ️ Privacy review complete. Review the approved payload above and authorize dispatch to Mock Passport API.")
                    submit_btn = st.button("🚀 Authorize & Submit to Mock Passport API", key="btn_passport_submit", type="primary", use_container_width=True)
                    if submit_btn:
                        try:
                            with st.spinner("Submitting approved payload to simulated mock passport service..."):
                                api_res = execute_mock_api_call(plan["approved_payload"])
                                st.session_state.passport_api_response = api_res
                                st.session_state.passport_executed = True
                                st.rerun()
                        except Exception as e:
                            st.error(f"Mock service submission failed: {e}")
                else:
                    st.success("✅ **Submission Authorized and Dispatched**: Approved minimal payload transmitted to Mock Passport API.")

            st.markdown("</div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # STAGE 4: SERVICE EXECUTION RESULT
            # -----------------------------------------------------------------
            if st.session_state.passport_executed and st.session_state.passport_api_response:
                api_res = st.session_state.passport_api_response
                st.markdown("""
                <div class="stage-box">
                    <div class="stage-title">
                        <span class="stage-badge">STAGE 4</span> Mock Service Execution Result
                    </div>
                    <div class="card-passed">
                        <h4 style="margin-top:0;">Mock External Service Response</h4>
                        <p style="margin-bottom:4px;"><b>Service Status:</b> SUBMITTED</p>
                        <p style="margin-bottom:4px;"><b>Message:</b> Application registered successfully.</p>
                        <p style="margin-bottom:0;"><b>Attributes Received:</b> {count} (<code>{attrs}</code>)</p>
                    </div>
                """.format(
                    count=api_res.get('received_attributes_count', len(api_res.get('received_attributes', []))),
                    attrs=api_res.get('received_attributes', [])
                ), unsafe_allow_html=True)
                st.caption("Simulated Response Payload:")
                st.json(api_res)
                st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: BENCHMARK EVALUATION (U001 - U010)
    # =========================================================================
    with tab_bench:
        st.subheader("📊 Full System Evaluation Benchmark (U001 - U010)")
        st.caption("Compares Baseline (Full Profile Disclosure) vs MIN-DISC across all 10 synthetic test profiles.")

        if st.button("Run Full Passport Benchmark Suite", key="btn_run_pass_bench", type="secondary"):
            with st.spinner("Running evaluation benchmark across all 10 profiles..."):
                retrieved_chunks = retriever.retrieve("I want to apply for a fresh passport.", top_k=5)
                extracted_reqs = extract_requirements(retrieved_chunks, task_name="fresh passport application")
                eval_results = run_evaluation_suite(extracted_reqs)

                df_rows = []
                total_baseline = 0
                total_min = 0
                total_prevented = 0

                for r in eval_results:
                    b_disc = r["baseline_disclosed"]
                    m_disc = r["min_disc_disclosed"]
                    prevented = r["attributes_prevented"]

                    total_baseline += b_disc
                    total_min += m_disc
                    total_prevented += prevented

                    df_rows.append({
                        "User ID": r["user_id"],
                        "Applicant Name": r["user_name"],
                        "Full Profile Disclosed": b_disc,
                        "MIN-DISC Disclosed": m_disc,
                        "Policy Check": "PASSED" if r["policy_approved"] else "BLOCKED",
                        "Final Status": r["min_disc_status"],
                        "Reduction %": f"{r['disclosure_reduction_pct']}%"
                    })

                st.dataframe(pd.DataFrame(df_rows), use_container_width=True)

                bm1, bm2, bm3, bm4 = st.columns(4)
                bm1.metric("Total Baseline Disclosures", total_baseline)
                bm2.metric("Total MIN-DISC Disclosures", total_min)
                bm3.metric("Total Attributes Excluded", total_prevented)
                overall_pct = round((1 - (total_min / total_baseline)) * 100, 1) if total_baseline > 0 else 0
                bm4.metric("Overall System Disclosure Reduction", f"{overall_pct}%")

                st.caption(f"Across the 10 synthetic evaluation cases, MIN-DISC reduced disclosed profile attributes by {overall_pct}% relative to full-profile baseline disclosure.")
        else:
            st.info("ℹ️ Click **'Run Full Passport Benchmark Suite'** to compute metrics across U001 - U010.")
