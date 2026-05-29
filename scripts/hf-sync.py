"""Sync TransitSight repo to Hugging Face Spaces via API, then rebuild."""
import os
import time
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

print("Uploading files...")
upload_folder(
    folder_path=".",
    path_in_repo=".",
    repo_id="zakir-my/transitsight",
    repo_type="space",
    ignore_patterns=IGNORE,
)
print("Upload complete!")

# Trigger Docker rebuild
print("Restarting Space to trigger rebuild...")
runtime = api.restart_space(repo_id="zakir-my/transitsight")
print(f"  Stage: {runtime.stage}")

# Poll until running
for _ in range(30):
    time.sleep(10)
    runtime = api.get_space_runtime(repo_id="zakir-my/transitsight")
    print(f"  Stage: {runtime.stage}")
    if runtime.stage == "RUNNING":
        print("Space is live!")
        break
else:
    print("Warning: Space didn't reach RUNNING within 5 minutes")
