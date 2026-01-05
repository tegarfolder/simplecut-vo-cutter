pyinstaller --noconfirm --onedir --windowed ^
 --icon "icon.ico" ^
 --add-data "models;models" ^
 --add-data "icon.ico;." ^
 --add-data "venv/Lib/site-packages/whisper/assets;whisper/assets" ^
 --collect-all tkinterdnd2 ^
 --hidden-import whisper ^
 "simplecut.py"