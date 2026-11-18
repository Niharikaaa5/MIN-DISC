"""
Main CLI Orchestrator and Demonstration Runner for MIN-DISC.
Exemplifies end-to-end task-aware minimum-disclosure execution and evaluation benchmark.
"""
import sys
import json
from pathlib import Path

# Ensure src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PASSPORT_REQUIREMENTS_DIR, USERS_FILE, check_config_health
from src.pdf_loader import load_pdfs_from_directory
from src.chunker import chunk_documents
from src.embeddings import EmbeddingModel
from src.vector_store import VectorStore
from src.retriever import Retriever
from src.repository_controller import RepositoryAccessController
from src.llm import LLMClient
from src.requirement_extractor import extract_requirements
from src.attribute_matcher import match_user_attributes
from src.disclosure_planner import create_disclosure_plan
from src.policy_checker import verify_privacy_policy
from src.mock_passport_api import execute_mock_api_call
from src.evaluation import run_evaluation_suite, load_users


def print_banner():
    print("\n" + "=" * 75)
    print("  MIN-DISC: Task-Aware Minimum-Disclosure Planning System")
    print("  Privacy-Aware LLM Agent Prototype")
    print("=" * 75 + "\n")


def build_or_load_rag_pipeline() -> Retriever:
    """Initializes RAG Pipeline over official Passport PDF requirement documents."""
    print("\n[STEP 1 & 2] Building/Loading Requirement RAG Pipeline...")

    embedding_model = EmbeddingModel()
    vector_store = VectorStore()

    # Attempt disk load first
    if vector_store.load():
        print("[*] Reusing cached FAISS vector store index.")
        return Retriever(vector_store, embedding_model)

    # Parse PDFs from data/requirements/passport/
    documents = load_pdfs_from_directory(PASSPORT_REQUIREMENTS_DIR)
    if not documents:
        print("[ERROR] No requirement PDFs found! Place official PDFs in data/requirements/passport/")
        sys.exit(1)

    # Chunk text preserving page metadata
    chunks = chunk_documents(documents)

    # Generate embeddings and build FAISS index
    texts = [c["text"] for c in chunks]
    embeddings = embedding_model.fit_transform(texts)
    vector_store.build_index(chunks, embeddings)
    vector_store.save()

    return Retriever(vector_store, embedding_model)


def demonstrate_single_user_flow(user_id: str = "U001", requires_non_ecr: bool = False):
    """Demonstrates complete 8-stage pipeline for a selected user profile."""
    print_banner()

    # Stage 1: User Task
    user_task = "I want to apply for a fresh passport."
    print(f"--- STAGE 1: USER TASK ---")
    print(f"Task: \"{user_task}\"")
    print(f"Target Case: Fresh Passport -> Adult -> Ordinary Case -> Citizen of India by Birth -> Normal\n")

    # Stage 2: RAG Retrieval
    retriever = build_or_load_rag_pipeline()
    retrieved_chunks = retriever.retrieve(user_task, top_k=5)

    print("\n--- STAGE 2: RETRIEVED AUTHORITATIVE REQUIREMENTS ---")
    for idx, c in enumerate(retrieved_chunks, 1):
        primary_tag = "[OFFICIAL BOOKLET PRIMARY]" if c["is_primary"] else "[SUPPORTING DOCUMENT]"
        print(f"  [{idx}] Source: {c['file_name']} (Page {c['page_number']}) {primary_tag}")
        snippet = c["text"][:120].replace('\n', ' ')
        print(f"      Snippet: {snippet}...\n")

    # Stage 3: LLM Requirement Extraction
    llm_client = LLMClient()
    extracted_reqs = extract_requirements(retrieved_chunks, task_name=user_task, llm_client=llm_client)

    print("--- STAGE 3: EXTRACTED STRUCTURED REQUIREMENTS ---")
    print(json.dumps(extracted_reqs, indent=2))
    print()

    # Stage 4A: Personal Repository Access Minimisation
    repo_controller = RepositoryAccessController()
    access_result = repo_controller.retrieve_documents_for_requirements(
        user_id=user_id,
        extracted_requirements=extracted_reqs,
        requires_non_ecr=requires_non_ecr
    )
    access_metrics = access_result["metrics"]
    sensitive_cats = RepositoryAccessController.FORBIDDEN_CATEGORIES
    single_sensitive_opened = sum(
        1 for entry in access_result.get("access_decision_log", [])
        if entry.get("category") in sensitive_cats and (entry.get("opened") or entry.get("decision") == "ACCESSED")
    )

    print(f"--- STAGE 4A: PERSONAL DRIVE REPOSITORY ACCESS (User: {user_id}) ---")
    print(f"Total Repository Documents:     {access_metrics['total_repository_files']}")
    print(f"Inspected Metadata Only:        {access_metrics['inspected_metadata_files']}")
    print(f"Authorized Documents Opened:    {access_metrics['accessed_files_count']}")
    print(f"Total Documents Unopened:       {access_metrics['unopened_files_count']}")
    print(f"Sensitive Documents Opened:     {single_sensitive_opened} (Banking, Tax, Medical strictly protected)")
    print(f"Access Minimisation Ratio:      {access_metrics['access_reduction_percentage']}% unopened")
    print("\nRepository Access Decision Audit Log:")
    for entry in access_result["access_decision_log"]:
        dec_tag = "[OPENED]" if entry["decision"] == "ACCESSED" else "[PROTECTED]"
        print(f"  * {dec_tag:<11} {entry['file_name']:<42} ({entry['category']})")
        print(f"    Justification: {entry['justification']}")
    print()

    # Stage 4B: User Profile & Attribute Matching
    users = load_users()
    target_user = next((u for u in users if u["user_id"] == user_id), None)
    if not target_user:
        print(f"[ERROR] User ID {user_id} not found in users.json")
        return

    print(f"--- STAGE 4B: USER ATTRIBUTE MATCHING (User: {target_user['name']} [{user_id}]) ---")
    matched_data = match_user_attributes(
        extracted_reqs,
        target_user,
        accessed_documents=access_result["accessed_documents"]
    )
    print("Requirement -> User Attribute Map:")
    for req_name, details in matched_data["mapping"].items():
        val_str = details['value'] if details['value'] else "MISSING / NULL"
        src_note = f"(From Drive: {details.get('document_file')})" if details.get("accessed_from_repository") else "(From Profile)"
        print(f"  * Requirement: {req_name}")
        print(f"    -> Target Profile Attribute: '{details['attribute_key']}' [{details['status'].upper()}] {src_note}")
        print(f"    -> Present in Profile: {details['present_in_profile']} (Value: {val_str})")

    if matched_data["missing_mandatory_attributes"]:
        print(f"\n[!] WARNING: Missing mandatory attributes: {matched_data['missing_mandatory_attributes']}")
    print()

    # Stage 5: Minimum Disclosure Planning
    print("--- STAGE 5: MINIMUM-DISCLOSURE PLANNER ---")
    plan = create_disclosure_plan(
        task_name="fresh passport application",
        extracted_requirements=extracted_reqs,
        matched_data=matched_data,
        user_profile=target_user,
        requires_non_ecr=requires_non_ecr
    )

    non_null_profile_keys = [k for k, v in target_user.items() if v is not None and k not in ["user_id", "name"]]
    print(f"Available Profile Attributes ({plan['total_user_attributes_count']}): {non_null_profile_keys}")
    print(f"Approved Attributes for Disclosure ({plan['disclosed_attributes_count']}): {plan['approved_attributes']}")
    print(f"Excluded Unnecessary Attributes ({plan['unnecessary_attributes_excluded_count']}): {plan['excluded_attributes']}")
    print("\nAttribute Exclusion Justifications:")
    for attr, just in plan.get("exclusion_justifications", {}).items():
        print(f"  - {attr:<20}: {just}")
    print()

    # Stage 6: Privacy / Policy Check
    print("--- STAGE 6: PRIVACY / POLICY CHECK ---")
    policy_res = verify_privacy_policy(
        plan=plan,
        matched_data=matched_data,
        user_profile=target_user,
        requires_non_ecr=requires_non_ecr,
        repository_access_log=access_result["access_decision_log"]
    )
    print(f"Policy Check Decision: [{policy_res['status']}]")
    print(f"Reason: {policy_res['reason']}\n")

    # Stage 7: Execution & Mock API Call
    print("--- STAGE 7: MOCK PASSPORT API SUBMISSION ---")
    if policy_res["approved"]:
        payload = plan["approved_payload"]
        print(f"Approved MIN-DISC Payload Sent to API:")
        print(json.dumps(payload, indent=2))

        api_response = execute_mock_api_call(payload)
        print("\nMock External API Result:")
        print(json.dumps(api_response, indent=2))
    else:
        print(f"[BLOCKED] Execution aborted due to policy check failure.")

    # Stage 8: Dual-Layer Privacy Demonstration Summary
    print("\n" + "=" * 80)
    print(f"  DUAL-LAYER PRIVACY DEMONSTRATION: BASELINE vs MIN-DISC ({user_id} - {target_user['name']})")
    print("=" * 80)
    print(f"  Layer 1: Task-Aware Access Minimisation (File Repository)")
    print(f"    * Total Documents in Personal Drive:      {access_metrics['total_repository_files']}")
    print(f"    * Documents Inspected (Metadata Only):    {access_metrics['inspected_metadata_files']}")
    print(f"    * Authorized Documents Opened:            {access_metrics['accessed_files_count']}")
    print(f"    * Total Documents Kept Unopened:          {access_metrics['unopened_files_count']}")
    print(f"    * Sensitive Documents Successfully Opened: {single_sensitive_opened} (Banking, Tax, Medical protected)")
    print(f"    ==> ACCESS REDUCTION RATIO:               {access_metrics['access_reduction_percentage']}%")
    print("-" * 80)
    print(f"  Layer 2: Minimum-Disclosure Planning (External Payload)")
    baseline_disclosed = plan['total_user_attributes_count']
    disclosed_count = plan['disclosed_attributes_count'] if policy_res["approved"] else 0
    unnecessary_prevented = baseline_disclosed - disclosed_count
    pct_reduction = round((1 - (disclosed_count / baseline_disclosed)) * 100, 1) if baseline_disclosed > 0 else 0
    print(f"    * Total Available Attributes:             {baseline_disclosed}")
    print(f"    * Attributes Approved for External Tool:  {disclosed_count}")
    print(f"    * Baseline Attributes Not Disclosed:      {unnecessary_prevented}")
    print(f"    ==> DISCLOSURE REDUCTION RATIO:           {pct_reduction}%")
    print("-" * 80)
    status_str = "SUCCESS" if policy_res["approved"] else "BLOCKED"
    print(f"  Dual-Policy Verification: [{policy_res['status']}]  |  Mock Tool Status: [{status_str}]")
    print("=" * 80 + "\n")


def run_full_evaluation_benchmark():
    """Runs evaluation benchmark over synthetic test users U001 through U010."""
    print_banner()
    print("[EVALUATION SUITE] Running MIN-DISC Evaluation Benchmark across Users U001 - U010...\n")

    retriever = build_or_load_rag_pipeline()
    retrieved_chunks = retriever.retrieve("I want to apply for a fresh passport.", top_k=5)
    extracted_reqs = extract_requirements(retrieved_chunks, task_name="fresh passport application")

    eval_results = run_evaluation_suite(extracted_reqs)

    print("\n" + "=" * 105)
    print(f" {'User ID':<8} | {'User Name':<20} | {'Files (Acc/Tot)':<15} | {'Acc Red%':<10} | {'Attrs (Disc/Tot)':<16} | {'Disc Red%':<10} | {'Result':<10}")
    print("=" * 105)

    total_repo_files = 0
    total_accessed_files = 0
    total_baseline_attrs = 0
    total_min_disc_attrs = 0
    total_prevented_attrs = 0

    for res in eval_results:
        uid = res["user_id"]
        name = res["user_name"]
        tot_f = res.get("total_repository_files", 7)
        acc_f = res.get("accessed_files_count", 0)
        acc_red = res.get("access_reduction_pct", 0.0)
        b_disc = res["baseline_disclosed"]
        m_disc = res["min_disc_disclosed"]
        status = "PASSED" if res["policy_approved"] else "BLOCKED"
        prevented = res["attributes_prevented"]
        disc_red = res["disclosure_reduction_pct"]

        total_repo_files += tot_f
        total_accessed_files += acc_f
        total_baseline_attrs += b_disc
        total_min_disc_attrs += m_disc
        total_prevented_attrs += prevented

        files_str = f"{acc_f}/{tot_f}"
        attrs_str = f"{m_disc}/{b_disc}"
        print(f" {uid:<8} | {name:<20} | {files_str:<15} | {acc_red:>7.1f}%   | {attrs_str:<16} | {disc_red:>7.1f}%   | {status:<10}")

    sensitive_cats = RepositoryAccessController.FORBIDDEN_CATEGORIES
    total_sensitive_docs = 0
    sensitive_docs_opened = 0
    for res in eval_results:
        for entry in res.get("access_decision_log", []):
            if entry.get("category") in sensitive_cats:
                total_sensitive_docs += 1
                if entry.get("opened") or entry.get("decision") == "ACCESSED":
                    sensitive_docs_opened += 1

    print("=" * 105)
    print(f" DUAL-LAYER PRIVACY BENCHMARK SUMMARY (10 Synthetic Applicants):")
    avg_acc_reduction = round((1 - (total_accessed_files / total_repo_files)) * 100, 1) if total_repo_files > 0 else 0
    avg_disc_reduction = round((1 - (total_min_disc_attrs / total_baseline_attrs)) * 100, 1) if total_baseline_attrs > 0 else 0
    print(f"  [Layer 1: Access Minimisation]")
    print(f"   * Total User Drive Documents:              {total_repo_files}")
    print(f"   * Total Sensitive Documents (Bank/Tax/Med): {total_sensitive_docs}")
    print(f"   * Total Sensitive Documents Opened:         {sensitive_docs_opened}")
    print(f"   * Total Authorized Documents Opened:        {total_accessed_files}")
    print(f"   * Total Documents Kept Unopened:            {total_repo_files - total_accessed_files}")
    print(f"   * Average Document Access Reduction:        {avg_acc_reduction}%")
    print(f"  [Layer 2: Disclosure Minimisation]")
    print(f"   * Total Baseline Profile Disclosures:       {total_baseline_attrs}")
    print(f"   * Total MIN-DISC Tool Disclosures:          {total_min_disc_attrs}")
    print(f"   * Baseline Attributes Not Disclosed:        {total_prevented_attrs} ({total_prevented_attrs} baseline attributes not disclosed by MIN-DISC)")
    print(f"   * Overall Attribute Disclosure Reduction:   {avg_disc_reduction}%")
    print("=" * 105 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--eval":
        run_full_evaluation_benchmark()
    else:
        user_param = sys.argv[1] if len(sys.argv) > 1 else "U001"
        demonstrate_single_user_flow(user_param, requires_non_ecr=False)
