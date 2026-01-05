import os
from huggingface_hub import hf_hub_download

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Unduh model Whisper
hf_hub_download(
    repo_id="openai/whisper-small",
    filename="pytorch_model.bin",
    local_dir=MODEL_DIR,
    local_dir_use_symlinks=False
)
hf_hub_download(
    repo_id="openai/whisper-medium",
    filename="pytorch_model.bin",
    local_dir=MODEL_DIR,
    local_dir_use_symlinks=False
)
print("✅ Model berhasil diunduh ke folder 'models/'")