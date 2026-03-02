#!/bin/bash

set -e

APPNAME="macamp"
ICON="icon.icns"   # Mets ici le nom de ton icône orange (ex: MacAmp.icns)
PYFILE="macamp.py"
REQS="requirements.txt"
SRC_DIR="$HOME/Desktop/MacAmpBuild"
BUILDDIR="$HOME/Desktop/MacAmpBuild/dist_build"

# Nettoyage du dossier de build
rm -rf "$BUILDDIR"
mkdir -p "$BUILDDIR"
cd "$BUILDDIR"

# Copie des fichiers nécessaires
cp "$SRC_DIR/$PYFILE" .
cp "$SRC_DIR/$ICON" .
cp "$SRC_DIR/$REQS" .

# Création et activation du venv
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances
pip install --upgrade pip
pip install -r $REQS

# Nettoyage des attributs étendus sur l'icône
xattr -c $ICON || true

# Build PyInstaller en mode onefile, sans la police Inter
pyinstaller --windowed --onefile --icon=$ICON $PYFILE

# Nettoyage du bundle généré
xattr -cr dist/${APPNAME}.app || true

# Signature du bundle
codesign --force --deep --sign - dist/${APPNAME}.app

echo "Ton app est disponible ici : $BUILDDIR/dist/${APPNAME}.app"
echo "Tu peux la déplacer dans Applications ou la lancer directement !" 