#!/bin/bash

# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier que nous sommes bien dans le bon dossier
if [ ! -f "macamp.py" ]; then
    echo "Erreur : macamp.py non trouvé dans le dossier courant"
    exit 1
fi

# Nettoyer les anciennes versions
rm -rf dist build MacAmp.iconset MacAmp.icns temp_large.png

# Créer le dossier pour l'icône
mkdir -p MacAmp.iconset

# Convertir le SVG en PNG haute résolution
if [ ! -f "iconMacamp.svg" ]; then
    echo "Erreur : iconMacamp.svg non trouvé"
    exit 1
fi

# Convertir le SVG en PNG haute résolution avec une taille réduite
sips -s format png -Z 1024 iconMacamp.svg --out temp_large.png

# Générer les différentes tailles d'icônes
for size in 16 32 128 256 512; do
    sips -z $size $size temp_large.png --out "MacAmp.iconset/icon_${size}x${size}.png"
    sips -z $((size*2)) $((size*2)) temp_large.png --out "MacAmp.iconset/icon_${size}x${size}@2x.png"
done

# Créer le fichier .icns
iconutil -c icns MacAmp.iconset

# Vérifier que l'icône a été créée
if [ ! -f "MacAmp.icns" ]; then
    echo "Erreur : Échec de la création de MacAmp.icns"
    exit 1
fi

# Créer l'application avec PyInstaller
pyinstaller --name MacAmp \
            --icon MacAmp.icns \
            --windowed \
            --noconfirm \
            --clean \
            --noupx \
            --exclude-module _tkinter \
            --exclude-module tkinter \
            --exclude-module Tcl \
            --exclude-module Tk \
            --exclude-module PIL._tkinter_finder \
            --add-data "shuffle-solid.svg:." \
            --add-data "repeat-solid.svg:." \
            --add-data "iconMacamp.svg:." \
            --target-arch x86_64 \
            --target-arch arm64 \
            --codesign-identity - \
            --osx-bundle-identifier com.macamp.app \
            macamp.py

# Vérifier que l'application a été créée
if [ ! -d "dist/MacAmp.app" ]; then
    echo "Erreur : L'application n'a pas été créée correctement"
    exit 1
fi

# Nettoyer les fichiers temporaires
rm -rf MacAmp.iconset temp_large.png MacAmp.spec build MacAmp.icns

# Nettoyage agressif des attributs étendus
echo "Nettoyage agressif des attributs étendus..."
find dist/MacAmp.app -type f -exec xattr -c {} \;
find dist/MacAmp.app -type d -exec xattr -c {} \;
dot_clean dist/MacAmp.app

# Nettoyer spécifiquement les frameworks et les fichiers binaires
echo "Nettoyage des frameworks et fichiers binaires..."
find dist/MacAmp.app -name "*.framework" -type d -exec xattr -cr {} \;
find dist/MacAmp.app -name "*.dylib" -type f -exec xattr -cr {} \;
find dist/MacAmp.app -name "Python3" -type f -exec xattr -cr {} \;
find dist/MacAmp.app -name "MacAmp" -type f -exec xattr -cr {} \;
find dist/MacAmp.app -type f -exec file {} \; | grep "Mach-O" | cut -d: -f1 | xargs -I{} xattr -cr {}

# Définir les permissions correctes
echo "Configuration des permissions..."
chmod -R u+w dist/MacAmp.app
find dist/MacAmp.app -type f -exec chmod 644 {} \;
find dist/MacAmp.app -type d -exec chmod 755 {} \;

# Vérifier s'il reste des attributs étendus
echo "Vérification des attributs étendus restants..."
find dist/MacAmp.app -exec xattr {} + | sort | uniq -c

echo "Signature de l'application..."
codesign --force --deep --sign - dist/MacAmp.app

echo "Installation terminée !" 