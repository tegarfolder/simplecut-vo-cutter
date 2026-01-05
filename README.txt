SimpleCut – Voice-Over Cutter (Dev Beta)
========================================

A lightweight tool for precise voice-over editing with Whisper AI integration.


Project Migration Guide
-----------------------

IMPORTANT: Never copy the 'venv' folder!
Virtual environments are system-specific and must be recreated on each machine.


Step 1: On the Source Computer
------------------------------
1. Open a terminal in your project directory.
2. Activate the virtual environment:
     venv\Scripts\activate
3. Export dependencies:
     pip freeze > requirements.txt


Step 2: On the New Computer
---------------------------
1. Copy all project files EXCEPT the 'venv' folder.
2. Ensure Python 3.12 is installed.
3. Open a terminal in the project directory.
4. Create a new virtual environment:
     python -m venv venv
5. Activate it:
     venv\Scripts\activate


Step 3: Install Dependencies
----------------------------
1. Install core packages:
     pip install -r requirements.txt

2. Reinstall PyTorch (required for GPU acceleration):

   - For NVIDIA GPU (CUDA 11.8 – recommended):
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

   - For CPU-only systems:
        pip install torch torchvision torchaudio


Step 4: Additional Setup
------------------------

FFmpeg
------
- Launch SimpleCut.
- If you see an "Install FFmpeg" button, click it for automatic installation.
- Alternatively, download FFmpeg manually and add it to your system PATH.

Audacity Integration
--------------------
- If using "Import to Audacity", enable scripting in Audacity:
    • Go to Edit > Preferences > Modules
    • Enable 'mod-script-pipe'
    • Restart Audacity


Whisper AI Models
-----------------

The 'models/' directory contains OpenAI’s Whisper models.
These are NOT included in the repository due to their large file size.

How to Download Models
----------------------
Run the following script to download required models automatically:

    python download_models.py

> The script uses 'huggingface_hub' to fetch official Whisper models.
> Make sure 'huggingface-hub' is listed in your requirements.txt.


Project: SimpleCut (Dev Beta)
Designed for developers and content creators who need fast, accurate voice-over segmentation.
