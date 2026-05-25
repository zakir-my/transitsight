"""Sync TransitSight repo to Hugging Face Spaces via API."""
import os
from huggingface_hub import HfApi, upload_folder

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("Error: HF_TOKEN not set")
    exit(1)

api = HfApi(token=HF_TOKEN)

IGNORE = [
    ".git/", ".gitignore", ".github/", ".dockerignore",
    ".env*", "venv/", "__pycache__", "*.pyc",
    "docs/", "scripts/", "*.db", "*.db-wal", "*.db-shm",
]

upload_folder(
    folder_path=".",
    path_in_repo=".",
    repo_id="zakir-my/transitsight",
    repo_type="space",
    ignore_patterns=IGNORE,
)
print("Upload complete!")
