#!/bin/bash

set -e

APPNAME="macamp"
ICON="icon.icns"   # Mets ici le nom de ton icône orange
PYFILE="macamp.py"
REQS="requirements.txt"

# Nettoyage des anciens builds
rm -rf build dist $APPNAME.spec

# Installation des dépendances (dans le venv courant)
pip install --upgrade pip
pip install -r $REQS
pip install pyinstaller

# Build PyInstaller (mode onedir, .app, icône)
pyinstaller \
  --windowed \
  --name "$APPNAME" \
  --icon "$ICON" \
  "$PYFILE"

# Affichage du résultat
if [ -d "dist/$APPNAME.app" ]; then
  echo "\n== Ton app est prête ici : dist/$APPNAME.app =="
  echo "== Garde tout le dossier dist/ pour que l'app fonctionne ! =="
else
  echo "\n== Ton app est prête ici : dist/$APPNAME == (binaire standalone) =="
fi 