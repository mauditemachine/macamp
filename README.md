# MacAmp

Un lecteur audio moderne et élégant inspiré des lecteurs audio classiques, développé avec PyQt6.

## Fonctionnalités

- Interface utilisateur moderne et intuitive
- Visualisation de la forme d'onde audio
- Contrôle du volume avec un bouton rotatif
- Support des formats MP3, WAV et AIFF
- Affichage des pochettes d'album
- Playlist avec glisser-déposer
- Navigation intuitive dans les pistes

## Installation

1. Cloner le dépôt :
```bash
git clone git@github.com:mauditemachine/macamp.git
cd macamp
```

2. Créer un environnement virtuel et l'activer :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
# ou
.\venv\Scripts\activate  # Sur Windows
```

3. Installer les dépendances :
```bash
pip install PyQt6 pygame librosa mutagen eyed3
```

## Utilisation

Lancer l'application :
```bash
python macamp.py
```

## Contrôles

- Clic sur la forme d'onde pour naviguer dans la piste
- Bouton rotatif pour le contrôle du volume (glisser vers le haut/bas)
- Boutons de lecture classiques (précédent, lecture/pause, stop, suivant)
- Glisser-déposer des fichiers audio dans la playlist

## Licence

MIT 