#!/bin/bash

echo "Installation de MacAmp..."

# Définir les chemins
APP_NAME="MacAmp.app"
APPS_DIR="$HOME/Applications"
APP_PATH="$APPS_DIR/$APP_NAME"
CONTENTS_PATH="$APP_PATH/Contents"
MACOS_PATH="$CONTENTS_PATH/MacOS"
RESOURCES_PATH="$CONTENTS_PATH/Resources"
APP_FILES_PATH="$RESOURCES_PATH/MacAmp"
LOG_FILE="$HOME/Library/Logs/MacAmp.log"

# Créer le fichier de log
touch "$LOG_FILE"
echo "$(date): Début de l'installation" >> "$LOG_FILE"

# Créer le dossier Applications utilisateur si nécessaire
mkdir -p "$APPS_DIR"

# Supprimer l'ancienne version si elle existe
if [ -d "$APP_PATH" ]; then
    echo "Suppression de l'ancienne version..."
    rm -rf "$APP_PATH"
fi

echo "Création de la structure de l'application..."
mkdir -p "$MACOS_PATH"
mkdir -p "$APP_FILES_PATH"

# Créer un nouvel environnement virtuel
echo "Création d'un nouvel environnement virtuel..."
python3 -m venv "$APP_FILES_PATH/venv"
source "$APP_FILES_PATH/venv/bin/activate"

echo "Installation des dépendances..."
pip install --upgrade pip
pip install PyQt6 pygame librosa mutagen eyed3 Pillow

echo "Copie des fichiers..."
cp macamp.py "$APP_FILES_PATH/"

# Créer le script Python de lancement
cat > "$APP_FILES_PATH/launcher.py" << 'EOL'
#!/usr/bin/env python3
import sys
import os
import traceback
import datetime
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import signal
import atexit

def setup_logging():
    try:
        log_dir = os.path.expanduser("~/Library/Logs")
        log_file = os.path.join(log_dir, "MacAmp.log")
        
        # S'assurer que le dossier des logs existe
        os.makedirs(log_dir, exist_ok=True)
        
        # Créer le fichier de log s'il n'existe pas
        if not os.path.exists(log_file):
            open(log_file, 'a').close()
        
        # Configuration du logger
        logger = logging.getLogger('MacAmp')
        logger.setLevel(logging.DEBUG)
        
        # Handler pour le fichier
        file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        file_handler.setLevel(logging.DEBUG)
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # Format des logs
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Ajout des handlers au logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    except Exception as e:
        print(f"Erreur lors de la configuration des logs : {e}")
        traceback.print_exc()
        sys.exit(1)

def cleanup(logger):
    logger.info("Fermeture de l'application")

def main():
    try:
        logger = setup_logging()
        atexit.register(cleanup, logger)
        
        # Gestionnaire de signaux
        def signal_handler(signum, frame):
            logger.info(f"Signal reçu : {signum}")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("=== Démarrage de MacAmp ===")
        logger.info(f"Version de Python : {sys.version}")
        logger.info(f"Chemin Python : {sys.executable}")
        logger.info(f"Répertoire courant : {os.getcwd()}")
        logger.info(f"Arguments : {sys.argv}")
        
        # Vérifier les permissions du répertoire courant
        logger.info("Vérification des permissions :")
        try:
            subprocess.run(['ls', '-la'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des permissions : {e}")
        
        # Vérifier les variables d'environnement
        logger.info("Variables d'environnement :")
        for key, value in os.environ.items():
            if 'python' in key.lower() or 'path' in key.lower():
                logger.info(f"ENV: {key}={value}")
        
        # Importer et lancer l'application
        logger.info("Importation du module macamp")
        import macamp
        
        logger.info("Lancement de l'application")
        macamp.main()
        
    except ImportError as e:
        logger.error(f"Erreur d'importation : {e}")
        logger.error("Traceback :")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
        logger.error("Traceback :")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
EOL

chmod +x "$APP_FILES_PATH/launcher.py"

# Créer le script de lancement
cat > "$MACOS_PATH/MacAmp" << 'EOL'
#!/bin/bash

# Chemin vers l'application
APP_PATH="$(dirname "$0")/../Resources/MacAmp"

# Activer l'environnement virtuel
source "$APP_PATH/venv/bin/activate"

# Lancer l'application via le launcher Python
cd "$APP_PATH"
exec python3 "$APP_PATH/launcher.py"
EOL

chmod +x "$MACOS_PATH/MacAmp"

# Créer le fichier Info.plist
echo "Configuration des métadonnées..."
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
    <key>LSEnvironment</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOL

# Créer une icône
echo "Utilisation de l'icône personnalisée..."
cp iconMacamp.svg "$RESOURCES_PATH/AppIcon.svg"

# Convertir le SVG en icns
echo "Conversion de l'icône en format icns..."
sips -s format icns "$RESOURCES_PATH/AppIcon.svg" --out "$RESOURCES_PATH/AppIcon.icns" 2>/dev/null || {
    echo "Erreur lors de la conversion de l'icône, utilisation de l'icône par défaut..."
    # Icône par défaut si la conversion échoue
    cat > "$RESOURCES_PATH/AppIcon.svg" << EOL
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="512" height="512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#1a1a1a"/>
  <text x="256" y="256" font-family="Arial" font-size="200" fill="white" text-anchor="middle" dominant-baseline="middle">🎵</text>
</svg>
EOL
    sips -s format icns "$RESOURCES_PATH/AppIcon.svg" --out "$RESOURCES_PATH/AppIcon.icns" 2>/dev/null || true
}

# Créer un lien symbolique sur le bureau
echo "Création du raccourci sur le bureau..."
ln -sf "$APP_PATH" "$HOME/Desktop/$APP_NAME"

# Configuration des permissions spéciales pour macOS
echo "Configuration des permissions spéciales pour macOS..."
chmod -R +x "$APP_PATH"
chmod -R +w "$HOME/Library/Logs"
chmod 755 "$MACOS_PATH/MacAmp"
chmod 755 "$APP_FILES_PATH/launcher.py"
chmod 644 "$CONTENTS_PATH/Info.plist"
xattr -cr "$APP_PATH"
xattr -d com.apple.quarantine "$APP_PATH" 2>/dev/null || true
codesign --force --deep --sign - "$APP_PATH"

# Ajouter l'application à la liste des applications autorisées
echo "Ajout de l'application aux applications autorisées..."
spctl --add "$APP_PATH"
spctl --enable
spctl --add --label "MacAmp" "$APP_PATH"

echo "Installation terminée !"
echo "L'application a été installée dans $APP_PATH"
echo "Un raccourci a été créé sur votre bureau"
echo "Les logs seront disponibles dans $LOG_FILE"
echo "Vous pouvez maintenant lancer MacAmp en double-cliquant sur l'icône"

echo "$(date): Installation terminée" >> "$LOG_FILE" 