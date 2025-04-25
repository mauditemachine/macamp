#!/bin/bash

# Définir le chemin de l'application
APP_NAME="MacAmp.app"
APP_PATH="$HOME/Desktop/$APP_NAME"
CONTENTS_PATH="$APP_PATH/Contents"
MACOS_PATH="$CONTENTS_PATH/MacOS"
RESOURCES_PATH="$CONTENTS_PATH/Resources"
APP_FILES_PATH="$RESOURCES_PATH/MacAmp"

# Obtenir le chemin absolu du dossier actuel
CURRENT_DIR="$(pwd)"

# Créer la structure de l'application
mkdir -p "$MACOS_PATH"
mkdir -p "$RESOURCES_PATH"
mkdir -p "$APP_FILES_PATH"

# Copier les fichiers nécessaires
cp -r "$CURRENT_DIR/macamp.py" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/requirements.txt" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/run.sh" "$APP_FILES_PATH/"
cp -r "$CURRENT_DIR/venv" "$APP_FILES_PATH/venv"

# Créer le script de lancement
cat > "$MACOS_PATH/MacAmp" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
cd ../Resources/MacAmp
source venv/bin/activate
python3 macamp.py
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

# Créer une icône simple (un carré noir avec du texte blanc)
cat > "$RESOURCES_PATH/AppIcon.svg" << EOL
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="512" height="512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#1a1a1a"/>
  <text x="256" y="256" font-family="Arial" font-size="200" fill="white" text-anchor="middle" dominant-baseline="middle">🎵</text>
</svg>
EOL

# Convertir le SVG en icône
sips -s format icns "$RESOURCES_PATH/AppIcon.svg" --out "$RESOURCES_PATH/AppIcon.icns" 2>/dev/null || true

echo "Application créée sur le bureau : $APP_PATH"
echo "Vous pouvez maintenant double-cliquer sur MacAmp.app pour lancer l'application" 