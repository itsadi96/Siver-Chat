@echo off
title Antigravity Gemini Bridge (Vertex AI)
echo ================================================
echo  Starting Antigravity Bridge on port 18795...
echo ================================================

:: Activate the Siver1 virtual environment
call "C:\Users\ASUS\Desktop\Ad\Projects\Siverly New\Siver1\siver-venv\Scripts\activate.bat"

:: Run the Vertex AI bridge
python "C:\Users\ASUS\Desktop\Ad\Projects\Siverly New\Siver1\scratch\antigravity_bridge_vertex.py"

pause
