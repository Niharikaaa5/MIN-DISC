"""
Module: MIN-DISC Fresh Passport Application Workflow View
Provides the dedicated UI for the Fresh Passport Application domain structured
into 10 academic demonstration steps:
1. Select synthetic applicant (U001 - U010).
2. Display relevant Passport requirements (retrieved from RAG).
3. Show applicant documents and metadata (simulated repository).
4. Show which documents were accessed and why (access decision log).
5. Show attribute matching.
6. Show minimum-disclosure plan (approved vs excluded attributes).
7. Show policy verification (Passed/Blocked).
8. Require user approval (human gating).
9. Demonstrate mock API submission.
10. Show evaluation results (10 synthetic profiles, access reduction, disclosure reduction).
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from src.repository_controller import RepositoryAccessController
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
        # =====================================================================
        # STEP 1: SELECT SYNTHETIC APPLICANT (U001 - U010) & CONFIGURE REQUEST
        # =====================================================================
        st.markdown("""
        <div class="stage-box">
            <div class="stage-title">
                <span class="stage-badge">STEP 1</span> Select Synthetic Applicant & Request Parameters
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

        run_analysis = st.button("🔍 Analyze Requirements & Plan Disclosure", key="btn_run_passport_analysis", type="primary", use_container_width=True)

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

        if run_analysis:
            with st.spinner("Retrieving authoritative evidence, minimizing repository access, and formulating privacy plan..."):
                try:
                    retrieved_chunks = retriever.retrieve(task_input, top_k=5)
                    llm_client = LLMClient()
                    extracted_reqs = extract_requirements(retrieved_chunks, task_name=task_input, llm_client=llm_client)

                    # Layer 1: Task-Aware Repository Access Minimisation
                    repo_controller = RepositoryAccessController()
                    access_res = repo_controller.retrieve_documents_for_requirements(
                        user_id=selected_user_id,
                        extracted_requirements=extracted_reqs,
                        requires_non_ecr=requires_non_ecr
                    )

                    # Layer 2: User Attribute Matching and Minimum Disclosure Planning
                    matched_data = match_user_attributes(
                        extracted_reqs,
                        target_user,
                        accessed_documents=access_res["accessed_documents"]
                    )
                    plan = create_disclosure_plan(
                        task_name="fresh passport application",
                        extracted_requirements=extracted_reqs,
                        matched_data=matched_data,
                        user_profile=target_user,
                        requires_non_ecr=requires_non_ecr
                    )
                    policy_res = verify_privacy_policy(
                        plan=plan,
                        matched_data=matched_data,
                        user_profile=target_user,
                        requires_non_ecr=requires_non_ecr,
                        repository_access_log=access_res["access_decision_log"]
                    )

                    # Inspect repository metadata for display in Step 3
                    user_repo_files = repo_controller.list_repository_files(selected_user_id)

                    st.session_state.passport_pipeline_data = {
                        "target_user": target_user,
                        "task_input": task_input,
                        "applicant_category": applicant_category,
                        "application_type": application_type,
                        "requires_non_ecr": requires_non_ecr,
                        "retrieved_chunks": retrieved_chunks,
                        "extracted_reqs": extracted_reqs,
                        "access_res": access_res,
                        "matched_data": matched_data,
                        "disclosure_plan": plan,
                        "policy_res": policy_res,
                        "user_repo_files": user_repo_files,
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
        # STEPS 2 TO 9: EXECUTION AND PRIVACY REVIEW RESULTS
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
            access_res = p_data.get("access_res", {})
            access_metrics = access_res.get("metrics", {})
            access_log = access_res.get("access_decision_log", [])
            user_repo_files = p_data.get("user_repo_files", [])

            # =================================================================
            # STEP 2: DISPLAY RELEVANT PASSPORT REQUIREMENTS (RETRIEVED FROM RAG)
            # =================================================================
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 2</span> Relevant Passport Requirements (Retrieved from RAG)
                </div>
            """, unsafe_allow_html=True)
            st.caption("Extracted from official Ministry of External Affairs Passport booklets via isolated vector retrieval:")

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

            with st.expander("📄 View Authoritative Retrieval Excerpts & Citations", expanded=False):
                for idx, c in enumerate(retrieved_chunks, 1):
                    tag = "📘 Primary Instruction Booklet" if c.get("is_primary") else "📄 Supporting Document"
                    st.markdown(f"**Chunk #{idx}** (`{c.get('chunk_id')}`) — `{c.get('file_name')}` (Page {c.get('page_number')}) — {tag}")
                    st.text(c.get("text", ""))
                    st.markdown("---")

            st.markdown("</div>", unsafe_allow_html=True)

            # =================================================================
            # STEP 3: SHOW APPLICANT DOCUMENTS & METADATA (SIMULATED REPOSITORY)
            # =================================================================
            st.markdown(f"""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 3</span> Applicant Documents & Metadata (Personal Cloud Repository)
                </div>
            """, unsafe_allow_html=True)
            st.caption(f"Simulated Google Drive repository for **{analyzed_user['name']}** ({analyzed_user['user_id']}) containing {len(user_repo_files)} personal files:")

            drive_table = []
            for f in user_repo_files:
                drive_table.append({
                    "File ID": f["file_id"],
                    "Document Name": f["file_name"],
                    "Category": f["category"],
                    "Document Type": f["document_type"],
                    "Issuer": f["issuer"],
                    "Issue Date": f["issue_date"]
                })

            with st.expander(f"📁 View Repository Metadata Catalog ({len(user_repo_files)} Files)", expanded=True):
                st.dataframe(pd.DataFrame(drive_table), use_container_width=True, hide_index=True)
                st.caption("🔒 *Default-deny access policy active: All files have metadata inspected, but contents remain unopened pending task justification.*")

            st.markdown("</div>", unsafe_allow_html=True)

            # =================================================================
            # STEP 4: SELECTIVE ACCESS DECISIONS & AUDIT LOG (LAYER 1)
            # =================================================================
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 4</span> Selective Access Decisions & Audit Log (Access Minimisation)
                </div>
            """, unsafe_allow_html=True)
            st.caption("Task-aware access controller grants access strictly to task-required documents; sensitive documents (medical, banking, tax) remain unopened.")

            if access_metrics:
                acc_c1, acc_c2, acc_c3, acc_c4 = st.columns(4)
                acc_c1.metric("Personal Drive Files", f"{access_metrics.get('total_repository_files', 0)}")
                acc_c2.metric("Metadata Inspected Only", f"{access_metrics.get('inspected_metadata_files', 0)}")
                acc_c3.metric("Authorized Opened", f"{access_metrics.get('accessed_files_count', 0)}")
                acc_c4.metric("Access Reduction Ratio", f"{access_metrics.get('access_reduction_percentage', 0.0)}%")
                sensitive_opened_single = sum(
                    1 for a in access_log
                    if a.get("category") in RepositoryAccessController.FORBIDDEN_CATEGORIES
                    and (a.get("opened") or a.get("decision") == "ACCESSED")
                )
                st.caption(f"Default-deny access control: {sensitive_opened_single} sensitive documents (medical, banking, tax) opened. Total documents unopened: {access_metrics.get('unopened_files_count', 0)}.")

            if access_log:
                audit_rows = []
                for a in access_log:
                    audit_rows.append({
                        "Document File": a["file_name"],
                        "Category": a["category"],
                        "Access Decision": "🟢 OPENED" if a["decision"] == "ACCESSED" else "🔒 NOT ACCESSED (PROTECTED)",
                        "Policy Justification": a["justification"]
                    })
                st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # =================================================================
            # STEP 5: ATTRIBUTE MATCHING
            # =================================================================
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 5</span> Requirement to User-Attribute Matching
                </div>
            """, unsafe_allow_html=True)
            st.caption("Maps extracted task requirements to tokens extracted from opened documents and applicant profile attributes:")

            match_table_data = []
            for req_name, details in matched_data.get("mapping", {}).items():
                val = details["value"] if details["value"] is not None else "MISSING / NULL"
                src_tag = f"📂 Drive: {details.get('document_file')}" if details.get("accessed_from_repository") else "👤 Profile Form Field"
                match_table_data.append({
                    "Task Requirement": req_name,
                    "Category": details.get("type", "supporting_document"),
                    "Status": details.get("status", "mandatory").upper(),
                    "Profile Attribute": str(details.get("attribute_key")),
                    "Document Origin": src_tag,
                    "Present": "Yes" if details.get("present_in_profile") else "Missing",
                    "Attribute Value": str(val)
                })
            st.dataframe(pd.DataFrame(match_table_data), use_container_width=True, hide_index=True)

            missing_reqs = plan.get("missing_mandatory_attributes") or matched_data.get("missing_mandatory_attributes", [])
            if missing_reqs:
                st.warning(f"⚠️ **Missing Mandatory Requirement(s)**: `{missing_reqs}`. Profile lacks statutory documentary proof.")

            st.markdown("</div>", unsafe_allow_html=True)

            # =================================================================
            # STEP 6: MINIMUM-DISCLOSURE PLAN (LAYER 2)
            # =================================================================
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 6</span> Minimum-Disclosure Plan & Metrics (Disclosure Minimisation)
                </div>
            """, unsafe_allow_html=True)
            st.caption("Synthesizes minimal transmission payload, eliminating unneeded attributes (income, banking, medical, employment):")

            base_count = plan["total_user_attributes_count"]
            min_count = plan["disclosed_attributes_count"] if policy_res["approved"] else 0
            prevented_count = base_count - min_count
            reduction_pct = round((1 - (min_count / base_count)) * 100, 1) if base_count > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Available Profile Attributes", f"{base_count}")
            m2.metric("Approved for Proposed Payload", f"{min_count}")
            m3.metric("Baseline Attributes Not Disclosed", f"{prevented_count}")
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

            with st.expander("🔍 View Per-Attribute Exclusion Justifications & Quarantined Fields", expanded=False):
                st.markdown("**Granular Exclusion Justifications:**")
                for attr, just in plan.get("exclusion_justifications", {}).items():
                    st.markdown(f"- **`{attr}`**: {just}")
                st.markdown("---")
                st.markdown("**Quarantined Internal Document Fields (Never Transmitted):**")
                st.caption(f"`{', '.join(plan.get('quarantined_document_fields', []))}`")

            st.markdown("**Proposed Disclosure Payload Preview:**")
            if policy_res["approved"]:
                st.json(plan["approved_payload"])
            else:
                st.warning("⚠️ No payload generated. Request failed deterministic policy verification.")

            st.markdown("</div>", unsafe_allow_html=True)

            # =================================================================
            # STEP 7: DETERMINISTIC POLICY VERIFICATION
            # =================================================================
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 7</span> Deterministic Privacy Policy Verification
                </div>
            """, unsafe_allow_html=True)

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

            st.markdown("</div>", unsafe_allow_html=True)

            # =================================================================
            # STEP 8: REQUIRE USER APPROVAL (HUMAN GATING)
            # =================================================================
            st.markdown("""
            <div class="stage-box">
                <div class="stage-title">
                    <span class="stage-badge">STEP 8</span> Human-in-the-Loop Approval Gating
                </div>
            """, unsafe_allow_html=True)

            if not policy_res["approved"]:
                st.error("⛔ **Submission Blocked**: Policy verification failed. External service execution cannot proceed.")
                st.caption("Zero attributes have been or will be transmitted to external endpoints.")
            elif is_stale:
                st.warning("⚠️ **Submission Disabled**: Settings modified. Re-run analysis to generate an up-to-date plan.")
            else:
                if not st.session_state.passport_executed:
                    st.info("ℹ️ Privacy review complete. Review the approved minimal payload above and authorize dispatch to Mock Passport API.")
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

            # =================================================================
            # STEP 9: DEMONSTRATE MOCK API SUBMISSION & RESULT
            # =================================================================
            if st.session_state.passport_executed and st.session_state.passport_api_response:
                api_res = st.session_state.passport_api_response
                st.markdown("""
                <div class="stage-box">
                    <div class="stage-title">
                        <span class="stage-badge">STEP 9</span> Mock Service Execution Result
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
    # TAB 2: STEP 10: EVALUATION RESULTS (10 SYNTHETIC PROFILES)
    # =========================================================================
    with tab_bench:
        st.subheader("📊 Step 10: Evaluation Results (10 Synthetic Profiles)")
        st.caption("Evaluates both Layer 1 (Access Minimisation) and Layer 2 (Disclosure Minimisation) across 10 synthetic test profiles.")

        if st.button("Run Full Passport Benchmark Suite", key="btn_run_pass_bench", type="secondary"):
            with st.spinner("Running evaluation benchmark across all 10 profiles..."):
                retrieved_chunks = retriever.retrieve("I want to apply for a fresh passport.", top_k=5)
                extracted_reqs = extract_requirements(retrieved_chunks, task_name="fresh passport application")
                eval_results = run_evaluation_suite(extracted_reqs)

                df_rows = []
                total_repo_files = 0
                total_accessed_files = 0
                total_baseline = 0
                total_min = 0
                total_prevented = 0

                for r in eval_results:
                    tot_f = r.get("total_repository_files", 7)
                    acc_f = r.get("accessed_files_count", 0)
                    acc_red = r.get("access_reduction_pct", 0.0)
                    b_disc = r["baseline_disclosed"]
                    m_disc = r["min_disc_disclosed"]
                    prevented = r["attributes_prevented"]

                    total_repo_files += tot_f
                    total_accessed_files += acc_f
                    total_baseline += b_disc
                    total_min += m_disc
                    total_prevented += prevented

                    df_rows.append({
                        "User ID": r["user_id"],
                        "Applicant Name": r["user_name"],
                        "Drive Files (Opened/Total)": f"{acc_f}/{tot_f}",
                        "Access Reduction %": f"{acc_red}%",
                        "Profile Attrs (Disclosed/Total)": f"{m_disc}/{b_disc}",
                        "Disclosure Reduction %": f"{r['disclosure_reduction_pct']}%",
                        "Policy Check": "PASSED" if r["policy_approved"] else "BLOCKED",
                        "Final Status": "PASSED" if r["policy_approved"] else "BLOCKED"
                    })

                st.dataframe(pd.DataFrame(df_rows), use_container_width=True, hide_index=True)

                st.markdown("#### 📈 Benchmark Summary Metrics")
                avg_acc_reduction = round((1 - (total_accessed_files / total_repo_files)) * 100, 1) if total_repo_files > 0 else 0
                avg_disc_reduction = round((1 - (total_min / total_baseline)) * 100, 1) if total_baseline > 0 else 0

                total_sensitive_docs = 0
                total_sensitive_opened = 0
                for r in eval_results:
                    for a in r.get("access_decision_log", []):
                        if a.get("category") in RepositoryAccessController.FORBIDDEN_CATEGORIES:
                            total_sensitive_docs += 1
                            if a.get("opened") or a.get("decision") == "ACCESSED":
                                total_sensitive_opened += 1
                total_unopened_files = total_repo_files - total_accessed_files

                st.markdown("**Layer 1: Task-Aware Access Minimisation**")
                bm1, bm2, bm3, bm4 = st.columns(4)
                bm1.metric("Total Drive Files", total_repo_files)
                bm2.metric("Total Files Opened", total_accessed_files)
                bm3.metric("Total Files Unopened", total_unopened_files)
                bm4.metric("Average Access Reduction", f"{avg_acc_reduction}%")

                st.caption(f"Across {total_repo_files} documents, {total_sensitive_docs} are sensitive (banking, tax, medical) and {total_sensitive_opened} sensitive documents were opened. {total_unopened_files} total documents were kept unopened.")

                st.markdown("**Layer 2: Minimum-Disclosure Planning**")
                dm1, dm2, dm3, dm4 = st.columns(4)
                dm1.metric("Baseline Attributes Disclosed", total_baseline)
                dm2.metric("MIN-DISC Attributes Disclosed", total_min)
                dm3.metric("Baseline Attributes Not Disclosed", total_prevented)
                dm4.metric("Overall Attribute Disclosure Reduction", f"{avg_disc_reduction}%")

                st.caption(f"Across the 10 synthetic evaluation cases, MIN-DISC kept {avg_acc_reduction}% of personal drive files unopened and {total_prevented} baseline attributes were not disclosed by MIN-DISC (yielding an overall {avg_disc_reduction}% attribute disclosure reduction).")
        else:
            st.info("ℹ️ Click **'Run Full Passport Benchmark Suite'** to compute metrics across U001 - U010.")
