#!/bin/bash

# Vérifier si le fichier SVG existe
if [ ! -f "iconMacamp.svg" ]; then
    echo "Erreur : Le fichier iconMacamp.svg n'existe pas"
    exit 1
fi

# Créer le dossier iconset
rm -rf MacAmp.iconset
mkdir -p MacAmp.iconset

# Convertir le SVG en PNG avec les noms exacts requis par iconutil
echo "Conversion des icônes..."

# 16x16
echo "Création de icon_16x16.png..."
magick iconMacamp.svg -background none -resize 16x16 "MacAmp.iconset/icon_16x16.png"
echo "Création de icon_16x16@2x.png..."
magick iconMacamp.svg -background none -resize 32x32 "MacAmp.iconset/icon_16x16@2x.png"

# 32x32
echo "Création de icon_32x32.png..."
magick iconMacamp.svg -background none -resize 32x32 "MacAmp.iconset/icon_32x32.png"
echo "Création de icon_32x32@2x.png..."
magick iconMacamp.svg -background none -resize 64x64 "MacAmp.iconset/icon_32x32@2x.png"

# 128x128
echo "Création de icon_128x128.png..."
magick iconMacamp.svg -background none -resize 128x128 "MacAmp.iconset/icon_128x128.png"
echo "Création de icon_128x128@2x.png..."
magick iconMacamp.svg -background none -resize 256x256 "MacAmp.iconset/icon_128x128@2x.png"

# 256x256
echo "Création de icon_256x256.png..."
magick iconMacamp.svg -background none -resize 256x256 "MacAmp.iconset/icon_256x256.png"
echo "Création de icon_256x256@2x.png..."
magick iconMacamp.svg -background none -resize 512x512 "MacAmp.iconset/icon_256x256@2x.png"

# 512x512
echo "Création de icon_512x512.png..."
magick iconMacamp.svg -background none -resize 512x512 "MacAmp.iconset/icon_512x512.png"
echo "Création de icon_512x512@2x.png..."
magick iconMacamp.svg -background none -resize 1024x1024 "MacAmp.iconset/icon_512x512@2x.png"

# Vérifier que tous les fichiers ont été créés
echo "Vérification des fichiers créés..."
ls -l MacAmp.iconset/

# Créer le fichier .icns
echo "Création du fichier .icns..."
if ! iconutil -c icns -o AppIcon.icns MacAmp.iconset; then
    echo "Erreur lors de la création du fichier .icns"
    echo "Contenu du dossier iconset :"
    ls -l MacAmp.iconset/
    rm -rf MacAmp.iconset
    exit 1
fi

# Nettoyer
rm -rf MacAmp.iconset

echo "Fichier .icns créé avec succès !" 