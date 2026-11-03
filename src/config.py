import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# LLM Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Path Config
DATA_DIR = BASE_DIR / "data"
PASSPORT_REQUIREMENTS_DIR = DATA_DIR / "requirements" / "passport"
USERS_FILE = DATA_DIR / "users" / "users.json"
EVALUATION_DIR = DATA_DIR / "evaluation"
FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
METADATA_STORE_PATH = DATA_DIR / "chunks_metadata.json"

# Evaluation Data Paths
GROUND_TRUTH_PATH = EVALUATION_DIR / "ground_truth.json"
REQUIREMENT_MAPPING_PATH = EVALUATION_DIR / "requirement_mapping.csv"
EVALUATION_CASES_PATH = EVALUATION_DIR / "evaluation_cases.csv"

# Mock API Config
MOCK_API_HOST = os.getenv("MOCK_API_HOST", "127.0.0.1")
MOCK_API_PORT = int(os.getenv("MOCK_API_PORT", "8000"))
MOCK_API_URL = f"http://{MOCK_API_HOST}:{MOCK_API_PORT}/passport/apply"


def check_config_health() -> dict:
    """Returns system paths health check."""
    return {
        "base_dir": str(BASE_DIR),
        "passport_pdf_dir_exists": PASSPORT_REQUIREMENTS_DIR.exists(),
        "users_file_exists": USERS_FILE.exists(),
        "ground_truth_exists": GROUND_TRUTH_PATH.exists(),
        "evaluation_cases_exists": EVALUATION_CASES_PATH.exists(),
        "has_gemini_key": bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here")
    }
