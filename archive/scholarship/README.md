# Archived Workflow: PM-USP Central Sector Scheme of Scholarship (CSSS)

This directory preserves all code, datasets, evaluation test cases, PDFs, and vector store indices for the PM-USP CSSS Scholarship workflow developed during Phase 1-5 of the MIN-DISC project.

## Archive Contents

- `src/scholarship/`: Complete backend pipeline (extractor, matcher, planner, deterministic policy engine, mock NSP/PFMS API, and RAG builder).
- `src/ui/scholarship_view.py`: Dedicated 8-stage Streamlit UI view with full credential masking and decoupled payment tracking.
- `data/requirements/scholarship/`:
  - Official CSSS Guidelines PDF
  - Official DoHE FAQ PDF
  - NSP Training of Users Manual PDF
  - FAISS index (`faiss_index.bin`) & metadata store (`chunks_metadata.json`)
  - Fitted TF-IDF vectorizer (`tfidf_vectorizer.pkl`)
  - Detailed requirement inventory (`scholarship_requirement_inventory.md`)
- `data/users/scholarship_users.json`: 15 synthetic applicant profiles (SCH001 - SCH015).
- `tests/`: Scholarship unit and integration test suite (`test_scholarship_*.py`).

## Restoration Instructions
To restore the Scholarship workflow:
1. Move `src/scholarship` back to `src/scholarship`.
2. Move `src/ui/scholarship_view.py` back to `src/ui/scholarship_view.py`.
3. Move `data/requirements/scholarship` back to `data/requirements/scholarship`.
4. Move `data/users/scholarship_users.json` back to `data/users/scholarship_users.json`.
5. Move `tests/test_scholarship_*.py` back to `tests/`.
6. Restore configuration entries in `src/config.py` and navigation in `app.py` / `src/ui/dashboard_view.py`.
