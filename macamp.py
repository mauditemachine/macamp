import sys
import os
import numpy as np
import librosa
from PIL import Image
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
                            QLabel, QSlider, QListWidget, QFrame, QToolTip,
                            QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QMimeData, QRect
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QPen, QImage, QLinearGradient, 
                        QBrush, QDragEnterEvent, QDropEvent, QFont)
import pygame
import eyed3
from mutagen import File
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import time

class PlaylistWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setColumnCount(2)
        self.setHeaderLabels(["Titre", "Durée"])
        self.setAlternatingRowColors(True)
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.mp3', '.wav', '.ogg', '.aiff')):
                files.append(path)
        if files:
            self.parent().parent().add_files(files)

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform = None
        self.current_position = 0
        self.hover_position = None
        self.duration = 0
        self.is_dragging = False
        self.current_file = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-radius: 8px;
                margin: 0px;
                padding: 0px;
            }
        """)
        
    def format_time(self, seconds):
        return time.strftime('%M:%S', time.gmtime(seconds))
        
    def set_position(self, position):
        self.current_position = position
        self.update()
        
    def set_waveform(self, waveform, duration):
        self.waveform = waveform
        self.duration = duration
        self.current_file = self.parent().parent().current_file
        self.update()
        
    def get_current_file(self):
        # Obtenir le fichier actuel depuis MacAmp
        return self.parent().parent().current_file
        
    def seek_to_position(self, position):
        if self.waveform is not None:
            try:
                print(f"Tentative de déplacement vers la position {position}")
                position = max(0, min(1, position))
                seek_time = position * self.duration
                print(f"Temps calculé: {seek_time} secondes")
                
                # Mettre à jour la position dans MacAmp
                main_window = self.parent().parent()
                main_window.current_position = seek_time
                
                # Si en lecture, redémarrer à la nouvelle position
                if main_window.is_playing:
                    main_window.play_from_position(seek_time)
                
                self.current_position = position
                self.update()
                print("Déplacement terminé avec succès")
                
            except Exception as e:
                print(f"Erreur lors du déplacement: {e}")
        else:
            print("Impossible de se déplacer: pas de waveform")
        
    def mousePressEvent(self, event):
        if self.waveform is not None:
            x = event.position().x()
            width = self.width()
            position = max(0, min(1, x / width))
            print(f"Clic à la position {position}")
            self.is_dragging = True
            self.seek_to_position(position)
            
    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            x = event.position().x()
            width = self.width()
            position = max(0, min(1, x / width))
            print(f"Relâchement à la position {position}")
            self.seek_to_position(position)
        self.is_dragging = False
            
    def mouseMoveEvent(self, event):
        x = event.position().x()
        width = self.width()
        position = max(0, min(1, x / width))
        hover_time = position * self.duration
        
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            print(f"Glissement à la position {position}")
            self.seek_to_position(position)
            
        QToolTip.showText(
            event.globalPosition().toPoint(),
            self.format_time(hover_time),
            self
        )
            
    def paintEvent(self, event):
        if self.waveform is None:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Fond
        painter.fillRect(0, 0, width, height, QColor(26, 26, 26))
        
        # Nombre de barres à afficher
        bar_width = 4  # Barres plus larges
        gap = 2  # Plus d'espace entre les barres
        num_bars = width // (bar_width + gap)
        samples_per_bar = len(self.waveform) // num_bars
        
        for i in range(num_bars):
            if i * samples_per_bar >= len(self.waveform):
                break
                
            # Calculer l'amplitude moyenne pour cette barre
            start_idx = i * samples_per_bar
            end_idx = min((i + 1) * samples_per_bar, len(self.waveform))
            if end_idx > start_idx:
                amplitude = np.mean(np.abs(self.waveform[start_idx:end_idx]))
                # Amplifier l'amplitude pour des barres plus hautes
                amplitude = min(1.0, amplitude * 2.5)  # Multiplier par 2.5 pour amplifier
            else:
                amplitude = 0
                
            # Position x de la barre
            x = i * (bar_width + gap)
            
            # Hauteur de la barre (symétrique haut/bas)
            bar_height = int(amplitude * height * 0.98)  # Utiliser presque toute la hauteur
            y_center = height // 2
            y_top = y_center - bar_height // 2
            
            # Couleur selon la position
            if x <= self.current_position * width:
                painter.fillRect(x, y_top, bar_width, bar_height, QColor(120, 120, 120))  # Barres plus claires
            else:
                painter.fillRect(x, y_top, bar_width, bar_height, QColor(80, 80, 80))  # Barres plus claires au repos
        
        # Ligne de progression avec glow
        progress_x = int(self.current_position * width)
        
        # Dessiner un effet de glow
        glow_pen = QPen(QColor(200, 50, 50, 30), 8)
        painter.setPen(glow_pen)
        painter.drawLine(progress_x, 0, progress_x, height)
        
        # Ligne principale plus épaisse
        if self.is_dragging:
            line_color = QColor(220, 70, 70)
        else:
            line_color = QColor(200, 50, 50)
            
        painter.setPen(QPen(line_color, 4))
        painter.drawLine(progress_x, 0, progress_x, height)

class RotaryKnob(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 50  # Valeur par défaut (0-100)
        self.setFixedSize(45, 45)  # Augmenté de 35 à 45
        self.is_dragging = False
        self.last_y = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dessiner le fond du bouton
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2d2d2d"))
        painter.drawEllipse(0, 0, self.width(), self.height())
        
        # Dessiner l'arc de progression avec une épaisseur plus importante
        pen = QPen(QColor("#666666"), 4)  # Arc de base en gris
        painter.setPen(pen)
        rect = QRect(4, 4, self.width() - 8, self.height() - 8)
        painter.drawArc(rect, -135 * 16, -270 * 16)
        
        # Dessiner l'arc rempli avec du blanc
        pen.setColor(QColor("#ffffff"))  # Changé de vert à blanc
        pen.setWidth(4)  # Arc plus épais
        painter.setPen(pen)
        span = int(-270 * (self.value / 100.0) * 16)
        painter.drawArc(rect, -135 * 16, span)
        
    def mousePressEvent(self, event):
        self.is_dragging = True
        self.last_y = event.position().y()
        
    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.last_y = None
        
    def mouseMoveEvent(self, event):
        if self.is_dragging and self.last_y is not None:
            delta_y = self.last_y - event.position().y()
            self.value = min(100, max(0, self.value + delta_y * 0.5))
            self.last_y = event.position().y()
            self.update()
            # Émettre le changement de volume
            self.parent().parent().set_volume(self.value)
            
    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120  # 120 = un cran de molette
        self.value = min(100, max(0, self.value + delta * 2))
        self.update()
        # Émettre le changement de volume
        self.parent().parent().set_volume(self.value)

class MacAmp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacAmp")
        self.setGeometry(100, 100, 600, 500)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111111;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(3, 3, 3, 3)
        
        # Zone supérieure (pochette + contrôles)
        top_container = QVBoxLayout()
        top_container.setSpacing(8)
        top_container.setContentsMargins(0, 0, 0, 0)
        
        # Layout horizontal pour cover + waveform
        cover_wave_layout = QHBoxLayout()
        cover_wave_layout.setSpacing(8)
        cover_wave_layout.setContentsMargins(0, 0, 0, 0)
        
        # Pochette d'album
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(180, 180)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setScaledContents(True)
        cover_wave_layout.addWidget(self.cover_label)
        
        # Waveform
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setFixedHeight(180)
        cover_wave_layout.addWidget(self.waveform_widget)
        
        # Ajouter le layout cover + waveform au container principal
        top_container.addLayout(cover_wave_layout)
        
        # Contrôles de lecture
        playback_layout = QHBoxLayout()
        playback_layout.setSpacing(10)
        playback_layout.setContentsMargins(0, 5, 0, 0)  # Réduit de 15 à 5 pixels
        
        # Création des boutons
        button_size = 45  # Augmenté de 35 à 45
        self.prev_button = QPushButton("⏮")
        self.play_button = QPushButton("▶")
        self.stop_button = QPushButton("⏹")
        self.next_button = QPushButton("⏭")
        self.volume_knob = RotaryKnob()
        self.volume_knob.setFixedSize(45, 45)  # Mettre à jour la taille du bouton rotatif
        
        buttons = [
            (self.prev_button, 18),  # Augmenté de 14 à 18
            (self.play_button, 22),  # Augmenté de 18 à 22
            (self.stop_button, 18),  # Augmenté de 14 à 18
            (self.next_button, 18)   # Augmenté de 14 à 18
        ]
        
        # Ajouter un spacer pour pousser les boutons vers le centre
        playback_layout.addStretch()
        
        for button, font_size in buttons:
            button.setFixedSize(button_size, button_size)
            button.setStyleSheet(f"""
                QPushButton {{
                    font-size: {font_size}px;
                    background-color: #2d2d2d;
                    border-radius: {button_size//2}px;
                    padding: 0px;
                    margin: 0px;
                }}
                QPushButton:hover {{
                    background-color: #3d3d3d;
                }}
            """)
            button.setEnabled(False)
            playback_layout.addWidget(button)
            
        # Ajout du bouton rotatif de volume
        playback_layout.addWidget(self.volume_knob)
        
        # Ajouter un autre spacer pour centrer l'ensemble
        playback_layout.addStretch()
        
        # Connecter les boutons à leurs fonctions
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.prev_button.clicked.connect(self.previous_track)
        self.next_button.clicked.connect(self.next_track)
        
        # Ajouter les contrôles au container principal
        top_container.addLayout(playback_layout)
        
        # Ajouter le container principal au layout global
        layout.addLayout(top_container)
        
        # Playlist avec style amélioré
        self.playlist_widget = PlaylistWidget(self)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_track)
        self.playlist_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 4px;
                margin: 1px 0;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3d3d3d;
                color: #ffffff;
                font-weight: bold;
            }
            QTreeWidget::item:hover {
                background-color: #353535;
            }
            QHeaderView::section {
                background-color: transparent;
                color: #ffffff;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Bouton pour ajouter des fichiers
        self.browse_button = QPushButton("Ajouter des fichiers")
        self.browse_button.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 5px;
                background-color: #2d2d2d;
                border-radius: 4px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.browse_button.clicked.connect(self.browse_files)
        
        # Ajout au layout principal
        layout.addWidget(self.playlist_widget)
        layout.addWidget(self.browse_button)
        
        central_widget.setLayout(layout)
        
        pygame.mixer.init()
        self.current_file = None
        self.is_playing = False
        self.playlist = []
        self.current_index = -1
        self.waveform = None
        self.current_position = 0
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.mp3', '.wav', '.ogg', '.aiff')):
                files.append(path)
        if files:
            self.add_files(files)
            
    def get_metadata(self, file_path):
        try:
            metadata = {
                'title': os.path.basename(file_path),
                'duration': '00:00'
            }
            
            audio = File(file_path)
            if isinstance(audio, MP3):
                try:
                    id3 = EasyID3(file_path)
                    metadata['title'] = id3.get('title', [metadata['title']])[0]
                except:
                    pass
                
                duration = audio.info.length
                metadata['duration'] = time.strftime('%M:%S', time.gmtime(duration))
                
            return metadata
        except:
            return {
                'title': os.path.basename(file_path),
                'duration': '00:00'
            }
            
    def add_files(self, files):
        for file_path in files:
            self.playlist.append(file_path)
            metadata = self.get_metadata(file_path)
            item = QTreeWidgetItem([
                metadata['title'],
                metadata['duration']
            ])
            self.playlist_widget.addTopLevelItem(item)
            
        if self.current_index == -1 and self.playlist:
            self.current_index = 0
            self.load_track(self.playlist[0])
            
    def browse_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers audio",
            "",
            "Fichiers audio (*.mp3 *.wav *.ogg *.aiff)"
        )
        
        if file_names:
            self.add_files(file_names)
            
    def load_track(self, file_name):
        try:
            print(f"Chargement de la piste: {file_name}")
            self.current_file = file_name
            
            # Mettre à jour la sélection dans la playlist
            for i in range(self.playlist_widget.topLevelItemCount()):
                item = self.playlist_widget.topLevelItem(i)
                if i == self.current_index:
                    self.playlist_widget.setCurrentItem(item)
                    item.setSelected(True)
                else:
                    item.setSelected(False)
            
            # Charger la waveform
            y, sr = librosa.load(file_name, sr=None)
            duration = len(y) / sr
            self.waveform = librosa.resample(y, orig_sr=sr, target_sr=2000)
            print(f"Waveform chargée, durée: {duration} secondes")
            self.waveform_widget.set_waveform(self.waveform, duration)
            
            # Charger l'audio
            pygame.mixer.music.load(file_name)
            pygame.mixer.music.set_volume(self.volume_knob.value / 100)
            print("Audio chargé et volume réglé")
            
            # Mettre à jour les boutons
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.prev_button.setEnabled(self.current_index > 0)
            self.next_button.setEnabled(self.current_index < len(self.playlist) - 1)
            
            # Réinitialiser la position
            self.current_position = 0
            self.waveform_widget.set_position(0)
            
            # Charger la pochette
            try:
                if file_name.lower().endswith('.mp3'):
                    audio = MP3(file_name)
                    if hasattr(audio, 'tags'):
                        for key in audio.tags.keys():
                            if key.startswith('APIC'):
                                apic = audio.tags[key]
                                img_data = apic.data
                                pixmap = QPixmap()
                                pixmap.loadFromData(img_data)
                                if not pixmap.isNull():
                                    self.cover_label.setPixmap(pixmap)
                                    print("Pochette MP3 chargée")
                                    return

                elif file_name.lower().endswith(('.wav', '.aiff')):
                    # Essayer de charger avec mutagen
                    audio = File(file_name)
                    if audio is not None:
                        # Pour WAV
                        if hasattr(audio, 'tags'):
                            print("Recherche de pochette dans les tags...")
                            for tag in audio.tags.values():
                                if hasattr(tag, 'data') and isinstance(tag.data, bytes):
                                    try:
                                        pixmap = QPixmap()
                                        pixmap.loadFromData(tag.data)
                                        if not pixmap.isNull():
                                            self.cover_label.setPixmap(pixmap)
                                            print(f"Pochette {file_name.split('.')[-1].upper()} chargée via tags")
                                            return
                                    except:
                                        continue

                        # Pour AIFF spécifiquement
                        if file_name.lower().endswith('.aiff'):
                            print("Recherche de pochette AIFF...")
                            if hasattr(audio, 'pictures'):
                                for pic in audio.pictures:
                                    try:
                                        pixmap = QPixmap()
                                        pixmap.loadFromData(pic.data)
                                        if not pixmap.isNull():
                                            self.cover_label.setPixmap(pixmap)
                                            print("Pochette AIFF chargée via pictures")
                                            return
                                    except:
                                        continue

                            # Essayer de trouver un chunk APPL avec des données d'image
                            if hasattr(audio, '_chunks'):
                                print("Recherche dans les chunks AIFF...")
                                for chunk in audio._chunks:
                                    if chunk.id == b'APPL' or chunk.id == b'PIC ':
                                        try:
                                            pixmap = QPixmap()
                                            pixmap.loadFromData(chunk.data)
                                            if not pixmap.isNull():
                                                self.cover_label.setPixmap(pixmap)
                                                print("Pochette AIFF chargée via chunks")
                                                return
                                        except:
                                            continue
                
                # Si pas de pochette trouvée, chercher une image dans le même dossier
                base_path = os.path.dirname(file_name)
                base_name = os.path.splitext(os.path.basename(file_name))[0]
                print(f"Recherche d'image dans le dossier: {base_path}")
                
                # Liste des extensions d'image possibles
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
                possible_names = [
                    'cover', 'folder', 'album', 'front',
                    base_name  # Le nom du fichier audio lui-même
                ]
                
                for name in possible_names:
                    for ext in image_extensions:
                        image_path = os.path.join(base_path, name + ext)
                        if os.path.exists(image_path):
                            try:
                                pixmap = QPixmap(image_path)
                                if not pixmap.isNull():
                                    self.cover_label.setPixmap(pixmap)
                                    print(f"Image trouvée dans le dossier: {image_path}")
                                    return
                            except:
                                continue

                # Si toujours rien trouvé, afficher l'icône par défaut
                print("Aucune pochette trouvée, affichage de l'icône par défaut")
                self.cover_label.setText("🎵")
                self.cover_label.setStyleSheet("""
                    QLabel {
                        background-color: #2d2d2d;
                        border-radius: 8px;
                        padding: 0px;
                        margin: 0px;
                        font-size: 32px;
                        color: #ffffff;
                    }
                """)
                
            except Exception as e:
                print(f"Erreur pochette: {e}")
                self.cover_label.setText("🎵")
                
            self.track_loaded = True
            print("Audio chargé et volume réglé")
            
        except Exception as e:
            print(f"Erreur chargement: {e}")
            
    def play_selected_track(self, item):
        index = self.playlist_widget.indexOfTopLevelItem(item)
        if 0 <= index < len(self.playlist):
            self.current_index = index
            self.load_track(self.playlist[index])
            self.play()
            
    def previous_track(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_track(self.playlist[self.current_index])
            self.play()
            
    def next_track(self):
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.load_track(self.playlist[self.current_index])
            self.play()
            
    def play_from_position(self, position):
        """Démarre la lecture à une position spécifique"""
        try:
            if self.current_file:
                pygame.mixer.music.load(self.current_file)
                pygame.mixer.music.play(start=position)
                self.is_playing = True
                self.play_button.setText("⏸")
                print(f"Lecture démarrée à {position} secondes")
        except Exception as e:
            print(f"Erreur lecture position: {e}")
            
    def play(self):
        self.play_from_position(self.current_position)
            
    def toggle_play(self):
        try:
            if not self.is_playing:
                self.play()
            else:
                pygame.mixer.music.pause()
                self.play_button.setText("▶")
                self.is_playing = False
        except Exception as e:
            print(f"Erreur toggle: {e}")
            
    def stop(self):
        try:
            pygame.mixer.music.stop()
            self.play_button.setText("▶")
            self.is_playing = False
            self.current_position = 0
            self.waveform_widget.set_position(0)
        except Exception as e:
            print(f"Erreur stop: {e}")
            
    def set_volume(self, value):
        try:
            pygame.mixer.music.set_volume(value / 100)
        except Exception as e:
            print(f"Erreur volume: {e}")
            
    def update_position(self):
        try:
            if self.is_playing and pygame.mixer.music.get_busy():
                pos = pygame.mixer.music.get_pos() / 1000.0
                if self.waveform is not None:
                    position = pos / self.waveform_widget.duration
                    self.waveform_widget.set_position(position)
                    self.current_position = pos
        except Exception as e:
            print(f"Erreur update position: {e}")

def main():
    app = QApplication(sys.argv)
    window = MacAmp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 