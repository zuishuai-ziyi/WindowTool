@echo off
echo Packaging...
cd /d "%~dp0"
pyinstaller main.py --noconsole --add-data "data;data" -i "./data\icon\window.png" --add-binary "./uia.dll;."
echo Packaging completed.
timeout 5
