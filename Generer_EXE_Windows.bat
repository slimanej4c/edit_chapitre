@echo off
chcp 65001 >nul
title Générateur EXE Windows - Éditeur de Fiches Pédagogiques
cd /d "%~dp0"

echo ======================================================================
echo    GÉNÉRATEUR DU FICHIER EXÉCUTABLE (.EXE) POUR WINDOWS
echo ======================================================================
echo.

:: 1. Vérification de Python
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERREUR] Python n'est pas détecté sur votre ordinateur.
        echo.
        echo Veuillez installer Python (3.10, 3.11 ou supérieur) depuis :
        echo   https://www.python.org/downloads/
        echo.
        echo IMPORTANT : Pendant l'installation, n'oubliez pas de COCHER :
        echo   "[X] Add Python to PATH" (Ajouter Python au PATH).
        echo.
        pause
        exit /b 1
    )
)

echo [1/3] Python détecté avec succès !
echo.

:: 2. Installation / Mise à jour des dépendances requises
echo [2/3] Installation des modules nécessaires (PyInstaller, PyMuPDF, etc.)...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install pyinstaller pymupdf arabic-reshaper python-bidi reportlab fonttools
if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] Impossible d'installer les bibliothèques requises.
    echo Vérifiez votre connexion Internet et réessayez.
    pause
    exit /b 1
)

echo.
:: 3. Compilation avec PyInstaller
echo [3/3] Compilation du fichier autonome .EXE en cours...
echo (Cette opération peut prendre 1 à 2 minutes, veuillez patienter...)
echo.

%PYTHON_CMD% build_exe.py

if exist "dist\Editeur_Fiches_Pedagogiques.exe" (
    copy /y "dist\Editeur_Fiches_Pedagogiques.exe" "Editeur_Fiches_Pedagogiques.exe" >nul
)

if exist "Editeur_Fiches_Pedagogiques.exe" (
    echo.
    echo ======================================================================
    echo   SUCCÈS ! LE FICHIER EXE A ÉTÉ GÉNÉRÉ AVEC SUCCÈS !
    echo.
    echo   Nom du fichier : Editeur_Fiches_Pedagogiques.exe
    echo   Emplacement    : %~dp0Editeur_Fiches_Pedagogiques.exe
    echo.
    echo   Vous pouvez maintenant double-cliquer directement sur ce fichier
    echo   pour ouvrir l'éditeur (il fonctionne sans console et sans Python !).
    echo ======================================================================
    echo.
    explorer /select,"Editeur_Fiches_Pedagogiques.exe"
) else (
    echo.
    echo [ERREUR] La compilation a échoué. Consultez les messages d'erreur ci-dessus.
    echo.
)

pause
