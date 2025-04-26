#!/bin/bash

# Vérifier si ImageMagick est installé
command_exists() {
    type "$1" &> /dev/null
}

if ! command_exists "magick"; then
    echo "Installation de ImageMagick..."
    brew install imagemagick
fi

# Définir le chemin de l'application
APP_NAME="MacAmp.app"
APP_PATH="dist/$APP_NAME"
CONTENTS_PATH="$APP_PATH/Contents"
MACOS_PATH="$CONTENTS_PATH/MacOS"
RESOURCES_PATH="$CONTENTS_PATH/Resources"
APP_FILES_PATH="$RESOURCES_PATH/MacAmp"

# Obtenir le chemin absolu du dossier actuel
CURRENT_DIR="$(pwd)"

# Créer la structure de l'application
mkdir -p dist
mkdir -p "$MACOS_PATH"
mkdir -p "$RESOURCES_PATH"
mkdir -p "$APP_FILES_PATH"

# Créer le dossier pour l'icône
mkdir -p MacAmp.iconset

# D'abord convertir le SVG en PNG haute résolution avec une taille réduite
sips -s format png -Z 512 iconMacamp.svg --out temp_large.png

# Générer les différentes tailles d'icônes
sips -z 16 16     temp_large.png --out MacAmp.iconset/icon_16x16.png
sips -z 32 32     temp_large.png --out MacAmp.iconset/icon_16x16@2x.png
sips -z 32 32     temp_large.png --out MacAmp.iconset/icon_32x32.png
sips -z 64 64     temp_large.png --out MacAmp.iconset/icon_32x32@2x.png
sips -z 128 128   temp_large.png --out MacAmp.iconset/icon_128x128.png
sips -z 256 256   temp_large.png --out MacAmp.iconset/icon_128x128@2x.png
sips -z 256 256   temp_large.png --out MacAmp.iconset/icon_256x256.png
sips -z 512 512   temp_large.png --out MacAmp.iconset/icon_256x256@2x.png
sips -z 512 512   temp_large.png --out MacAmp.iconset/icon_512x512.png
sips -z 512 512   temp_large.png --out MacAmp.iconset/icon_512x512@2x.png

# Créer le fichier .icns
iconutil -c icns MacAmp.iconset

# Nettoyer
rm -rf MacAmp.iconset temp_large.png

# Copier l'icône dans les ressources
cp MacAmp.icns "$RESOURCES_PATH/AppIcon.icns"

# Copier les fichiers nécessaires
cp -r "$CURRENT_DIR/macamp.py" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/requirements.txt" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/iconMacamp.svg" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/shuffle-solid.svg" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/repeat-solid.svg" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/venv" "$APP_FILES_PATH/venv"

# Créer le script de lancement
cat > "$MACOS_PATH/MacAmp" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
cd ../Resources/MacAmp
export PATH="\$PATH:/usr/local/bin:/opt/homebrew/bin"
export QT_MAC_WANTS_LAYER=1
source venv/bin/activate
exec python3 macamp.py
EOL

# Rendre le script exécutable
chmod +x "$MACOS_PATH/MacAmp"

# Créer le fichier Info.plist
cat > "$CONTENTS_PATH/Info.plist" << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>MacAmp</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.macamp.app</string>
    <key>CFBundleName</key>
    <string>MacAmp</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.10</string>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOL

echo "Application créée dans le dossier dist : $APP_PATH"
echo "Vous pouvez maintenant double-cliquer sur MacAmp.app pour lancer l'application" 