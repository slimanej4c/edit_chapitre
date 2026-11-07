#!/bin/bash
PROJECT_DIR="/Users/studio/Documents/MUSTAPHA"
cd "$PROJECT_DIR" || exit 1

PYTHON_EXE="$PROJECT_DIR/.venv/bin/python3"

if [ ! -f "$PYTHON_EXE" ]; then
    echo "Configuration initiale de l'environnement Python..."
    python3 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install pymupdf arabic-reshaper python-bidi reportlab fonttools streamlit
fi

# Lancement de l'application bureau
"$PYTHON_EXE" "$PROJECT_DIR/editeur_desktop.py"
