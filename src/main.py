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

    # Stage 4: User Profile & Attribute Matching
    users = load_users()
    target_user = next((u for u in users if u["user_id"] == user_id), None)
    if not target_user:
        print(f"[ERROR] User ID {user_id} not found in users.json")
        return

    print(f"--- STAGE 4: USER ATTRIBUTE MATCHING (User: {target_user['name']} [{user_id}]) ---")
    matched_data = match_user_attributes(extracted_reqs, target_user)
    print("Requirement -> User Attribute Map:")
    for req_name, details in matched_data["mapping"].items():
        val_str = details['value'] if details['value'] else "MISSING / NULL"
        print(f"  * Requirement: {req_name}")
        print(f"    -> Target Profile Attribute: '{details['attribute_key']}' [{details['status'].upper()}]")
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
    print(f"Excluded Unnecessary Attributes ({plan['unnecessary_attributes_excluded_count']}): {plan['excluded_attributes']}\n")

    # Stage 6: Privacy / Policy Check
    print("--- STAGE 6: PRIVACY / POLICY CHECK ---")
    policy_res = verify_privacy_policy(plan, matched_data, target_user, requires_non_ecr=requires_non_ecr)
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

    # Stage 8: Privacy Demonstration Comparison
    print("\n" + "=" * 75)
    print(f"  PRIVACY DEMONSTRATION: FULL DISCLOSURE vs MIN-DISC ({user_id} - {target_user['name']})")
    print("=" * 75)
    print(f"  Metric                                | Full Disclosure | MIN-DISC")
    print("-" * 75)
    baseline_disclosed = plan['total_user_attributes_count']
    disclosed_count = plan['disclosed_attributes_count'] if policy_res["approved"] else 0
    unnecessary_prevented = baseline_disclosed - disclosed_count
    print(f"  Total Profile Attributes Disclosed   | {baseline_disclosed:<15} | {disclosed_count:<15}")
    print(f"  Attributes Prevented from Leakage    | 0               | {unnecessary_prevented:<15}")
    print(f"  Privacy Policy Verification          | BYPASSED        | {policy_res['status']:<15}")
    status_str = "SUCCESS" if policy_res["approved"] else "BLOCKED"
    print(f"  Mock Tool Application Result         | SUCCESS         | {status_str:<15}")
    pct_reduction = round((1 - (disclosed_count / baseline_disclosed)) * 100, 1) if baseline_disclosed > 0 else 0
    print("-" * 75)
    print(f"  ==> DISCLOSURE REDUCTION: {pct_reduction}% REDUCTION IN EXPOSED DATA")
    print("=" * 75 + "\n")


def run_full_evaluation_benchmark():
    """Runs evaluation benchmark over synthetic test users U001 through U010."""
    print_banner()
    print("[EVALUATION SUITE] Running MIN-DISC Evaluation Benchmark across Users U001 - U010...\n")

    retriever = build_or_load_rag_pipeline()
    retrieved_chunks = retriever.retrieve("I want to apply for a fresh passport.", top_k=3)
    extracted_reqs = extract_requirements(retrieved_chunks, task_name="fresh passport application")

    eval_results = run_evaluation_suite(extracted_reqs)

    print("\n" + "=" * 95)
    print(f" {'User ID':<8} | {'User Name':<20} | {'Full Disc.':<10} | {'MIN-DISC':<10} | {'Policy':<8} | {'Result':<10}")
    print("=" * 95)

    total_baseline_attrs = 0
    total_min_disc_attrs = 0
    total_prevented_attrs = 0

    for res in eval_results:
        uid = res["user_id"]
        name = res["user_name"]
        b_disc = res["baseline_disclosed"]
        m_disc = res["min_disc_disclosed"]
        pol = "PASSED" if res["policy_approved"] else "BLOCKED"
        status = res["min_disc_status"]
        prevented = res["attributes_prevented"]

        total_baseline_attrs += b_disc
        total_min_disc_attrs += m_disc
        total_prevented_attrs += prevented

        print(f" {uid:<8} | {name:<20} | {b_disc:<10} | {m_disc:<10} | {pol:<8} | {status:<10}")

    print("=" * 95)
    print(f" SUMMARY METRICS ACROSS ALL EVALUATION CASES:")
    print(f"  * Total Baseline Disclosures (Full Profile):           {total_baseline_attrs}")
    print(f"  * Total MIN-DISC Disclosures:                         {total_min_disc_attrs}")
    print(f"  * Total Attributes Prevented from Leakage:             {total_prevented_attrs}")
    avg_reduction = round((1 - (total_min_disc_attrs / total_baseline_attrs)) * 100, 1) if total_baseline_attrs > 0 else 0
    print(f"  * Overall Disclosure Reduction:                        {avg_reduction}%")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--eval":
        run_full_evaluation_benchmark()
    else:
        user_param = sys.argv[1] if len(sys.argv) > 1 else "U001"
        demonstrate_single_user_flow(user_param, requires_non_ecr=False)
