#!/bin/bash
PROJECT_DIR="/Users/studio/Documents/MUSTAPHA"
cd "$PROJECT_DIR" || exit 1

PYTHON_EXE="$PROJECT_DIR/.venv/bin/python3"
STREAMLIT_EXE="$PROJECT_DIR/.venv/bin/streamlit"

if [ ! -f "$STREAMLIT_EXE" ]; then
    echo "Configuration initiale de l'environnement Python..."
    python3 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install pymupdf arabic-reshaper python-bidi reportlab fonttools streamlit
fi

# Lancement de l'interface Web Streamlit
"$STREAMLIT_EXE" run "$PROJECT_DIR/app.py"
