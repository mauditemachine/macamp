#!/bin/bash

# Vérification de la présence de Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Création du dossier du projet s'il n'existe pas
PROJECT_DIR="$(pwd)"
if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
fi

# Création de l'environnement virtuel dans le dossier du projet
echo "Création de l'environnement virtuel..."
python3 -m venv "$PROJECT_DIR/venv"

# Activation de l'environnement virtuel
source "$PROJECT_DIR/venv/bin/activate"

# Mise à jour de pip dans l'environnement virtuel
pip install --upgrade pip

# Installation des dépendances
echo "Installation des dépendances..."
pip install -r requirements.txt

# Création du script de lancement
echo "Création du script de lancement..."
cat > run.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
python "$SCRIPT_DIR/macamp.py"
EOF

# Rendre le script exécutable
chmod +x run.sh

# Création d'un fichier .gitignore pour éviter de versionner l'environnement virtuel
echo "venv/" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

echo "Installation terminée !"
echo "L'application est installée dans : $PROJECT_DIR"
echo "Pour lancer l'application, utilisez : ./run.sh"
echo "Tout est isolé dans le dossier du projet, rien n'est installé globalement." 