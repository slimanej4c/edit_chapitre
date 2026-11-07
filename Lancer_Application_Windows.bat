@echo off
chcp 65001 >nul
title Éditeur de Fiches Pédagogiques
cd /d "%~dp0"

set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERREUR] Python n'est pas détecté. Veuillez installer Python depuis https://www.python.org/
        pause
        exit /b 1
    )
)

%PYTHON_CMD% -m pip install -q pymupdf arabic-reshaper python-bidi reportlab fonttools
%PYTHON_CMD% editeur_desktop.py
