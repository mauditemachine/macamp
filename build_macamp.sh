#!/bin/bash

set -e

# Variables à adapter si besoin
APPNAME="macamp"
ICON="icon.icns"  # Mets ici le nom de ton icône (ex: MacAmp.icns)
FONT="Inter_24pt-Regular.ttf"
PYFILE="macamp.py"
REQS="requirements.txt"
SRC_DIR="$HOME/Desktop/MacAmpBuild"
BUILDDIR="/tmp/MacAmpBuild"

# Nettoyage du dossier de build
rm -rf "$BUILDDIR"
mkdir "$BUILDDIR"
cd "$BUILDDIR"

# Copie des fichiers nécessaires
echo "== Copie des fichiers nécessaires =="
cp "$SRC_DIR/$PYFILE" .
cp "$SRC_DIR/$ICON" .
cp "$SRC_DIR/$FONT" .
cp "$SRC_DIR/$REQS" .

# Création et activation du venv
echo "== Création et activation du venv =="
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances
echo "== Installation des dépendances =="
pip install --upgrade pip
pip install -r $REQS

# Nettoyage des attributs étendus sur les fichiers critiques
echo "== Nettoyage des attributs étendus sur les fichiers critiques =="
xattr -c $FONT || true
xattr -c $ICON || true

# Build PyInstaller
echo "== Build PyInstaller =="
pyinstaller --windowed --icon=$ICON --add-data "$FONT:." $PYFILE

# Nettoyage du bundle généré
echo "== Nettoyage du bundle généré =="
xattr -cr dist/${APPNAME}.app || true

# Signature du bundle
echo "== Signature du bundle =="
codesign --force --deep --sign - dist/${APPNAME}.app

# Résultat
echo "== Résultat =="
echo "Ton app est disponible ici : $BUILDDIR/dist/${APPNAME}.app"
echo "Tu peux la déplacer dans Applications ou la lancer directement !" 
