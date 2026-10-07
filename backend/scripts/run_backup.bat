@echo off
cd /d D:\git\squareclouds_portal\backend
call venv\Scripts\activate.bat
python scripts\backup_database.py
pause
