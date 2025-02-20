@echo off
echo Setting up the environment...

:: Create virtual environment if it doesn't exist
if not exist venv (
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install dependencies
E:\MusicBoard\venv\Scripts\python.exe -m pip install --upgrade pip
pip install -r requirements.txt

:: Run PowerShell script to print "Running main.py" in ROYGBIV colors
powershell -ExecutionPolicy Bypass -File color_text.ps1

:: Run the script
python main.py

:: Deactivate virtual environment
deactivate
