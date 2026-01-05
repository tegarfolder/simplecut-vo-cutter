@echo off
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo Instalasi Selesai!
pause