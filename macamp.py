import sys
import os
import numpy as np
import librosa
from PIL import Image
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
                            QLabel, QSlider, QListWidget, QFrame, QToolTip,
                            QTreeWidget, QTreeWidgetItem, QHeaderView, QStyledItemDelegate,
                            QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QMimeData, QRect, QRectF
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QPen, QImage, QLinearGradient, 
                        QBrush, QDragEnterEvent, QDropEvent, QFont, QFontDatabase, QPainterPath)
from PyQt6.QtSvg import QSvgRenderer
import sounddevice as sd
from scipy.io import wavfile
import pygame
import eyed3
from mutagen import File
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import time

class PlaylistItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        tree_widget = option.widget
        if isinstance(tree_widget, QTreeWidget):
            item = tree_widget.topLevelItem(index.row())
            if item and tree_widget.parent().parent().current_index == index.row():
                option.palette.setColor(option.palette.ColorRole.Text, QColor("#FFDD00"))
            else:
                option.palette.setColor(option.palette.ColorRole.Text, QColor("#FFFFFF"))

class PlaylistWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Inter", 12))
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setColumnCount(2)
        self.setHeaderLabels(["Artiste", "Titre"])
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 120)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Remettre le padding-left de 10px sur le header et les items
        header.setStyleSheet("""
            QHeaderView::section {
                color: #FFFFFF;
                padding-left: 10px;
                padding-bottom: 2px;
                padding-top: 10px;
            }
        """)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 0px;
                margin: 0px;
            }
            QTreeWidget::item {
                padding-left: 10px;
                padding: 2px 4px;
                margin: 0px;
                border-radius: 0px;
                height: 22px;
                font-weight: normal;
                color: #FFFFFF;
            }
            QTreeWidget::item:selected {
                background: none;
            }
            QTreeWidget::item:hover {
                background-color: #333333;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3d3d3d;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)

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
            if hasattr(self.window(), 'add_files'):
                self.window().add_files(files)

    def update_track_colors(self):
        """Met à jour la couleur de la piste active en jaune doré"""
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if i == self.parent().parent().current_index:
                # Piste active en jaune doré et gras
                for col in range(2):
                    font = QFont("Inter", 12)
                    font.setBold(False)
                    item.setFont(col, font)
                    item.setForeground(col, QColor("#FFDD00"))
            else:
                # Autres pistes en blanc et normal
                for col in range(2):
                    font = QFont("Inter", 12)
                    font.setBold(False)
                    item.setFont(col, font)
                    item.setForeground(col, QColor("#FFFFFF"))

    def update_active_track(self):
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if i == self.parent().parent().current_index:
                item.setForeground(0, QColor("#FFDD00"))
                item.setForeground(1, QColor("#FFDD00"))
            else:
                item.setForeground(0, QColor("#FFFFFF"))
                item.setForeground(1, QColor("#FFFFFF"))

    def addTopLevelItem(self, item):
        super().addTopLevelItem(item)
        # Aligner le texte de l'artiste à gauche
        item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Aligner le texte du titre à gauche
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

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
        # Cache pour les barres de la waveform
        self.bar_cache = None
        self.last_width = 0
        self.last_position = -1
        self.bar_heights = None  # Cache pour les hauteurs des barres
        
    def format_time(self, seconds):
        return time.strftime('%M:%S', time.gmtime(seconds))
        
    def set_position(self, position):
        if position != self.current_position:
            self.current_position = position
            self.update()
        
    def set_waveform(self, waveform, duration):
        self.waveform = waveform
        self.duration = duration
        self.current_file = self.parent().parent().current_file
        
        # Précalculer les hauteurs des barres
        width = self.width()
        bar_width = 4
        gap = 2
        num_bars = width // (bar_width + gap)
        samples_per_bar = len(self.waveform) // num_bars
        
        self.bar_heights = np.zeros(num_bars)
        for i in range(num_bars):
            if i * samples_per_bar >= len(self.waveform):
                break
            start_idx = i * samples_per_bar
            end_idx = min((i + 1) * samples_per_bar, len(self.waveform))
            if end_idx > start_idx:
                amplitude = np.mean(np.abs(self.waveform[start_idx:end_idx]))
                self.bar_heights[i] = min(1.0, amplitude * 2.5)
        
        self.update()
        
    def get_current_file(self):
        return self.parent().parent().current_file
        
    def seek_to_position(self, position):
        if self.waveform is not None:
            try:
                position = max(0, min(1, position))
                seek_time = position * self.duration
                
                # Mettre à jour la position dans MacAmp
                main_window = self.parent().parent()
                main_window.current_position = seek_time
                
                # Si en lecture, redémarrer à la nouvelle position immédiatement
                if main_window.is_playing:
                    # Arrêter le stream actuel
                    if main_window.audio_player.stream:
                        main_window.audio_player.stream.stop()
                        main_window.audio_player.stream.close()
                    
                    # Démarrer la nouvelle lecture immédiatement
                    main_window.audio_player.play(start_pos=seek_time)
                
                self.current_position = position
                self.update()
                
            except Exception as e:
                print(f"Erreur lors du déplacement: {e}")
        else:
            print("Impossible de se déplacer: pas de waveform")
        
    def mousePressEvent(self, event):
        if self.waveform is not None:
            x = event.position().x()
            width = self.width()
            position = max(0, min(1, x / width))
            self.is_dragging = True
            self.seek_to_position(position)
            
    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            x = event.position().x()
            width = self.width()
            position = max(0, min(1, x / width))
            self.seek_to_position(position)
        self.is_dragging = False
            
    def mouseMoveEvent(self, event):
        x = event.position().x()
        width = self.width()
        position = max(0, min(1, x / width))
        hover_time = position * self.duration
        
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.seek_to_position(position)
            
        QToolTip.showText(
            event.globalPosition().toPoint(),
            self.format_time(hover_time),
            self
        )
            
    def paintEvent(self, event):
        if self.waveform is None or self.bar_heights is None:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Fond
        painter.fillRect(0, 0, width, height, QColor(26, 26, 26))
        
        # Nombre de barres à afficher
        bar_width = 4
        gap = 2
        num_bars = width // (bar_width + gap)
        
        # Calculer la position de la barre de progression
        progress_x = int(self.current_position * width)
        
        # Dessiner les barres avec les hauteurs précalculées
        for i in range(num_bars):
            if i >= len(self.bar_heights):
                break
                
            x = i * (bar_width + gap)
            bar_height = int(self.bar_heights[i] * height * 0.98)
            y_center = height // 2
            y_top = y_center - bar_height // 2
            
            # Couleur selon la position
            if x <= progress_x:
                painter.fillRect(x, y_top, bar_width, bar_height, QColor("#FFDD00"))
            else:
                painter.fillRect(x, y_top, bar_width, bar_height, QColor(80, 80, 80))
        
        # Ligne de progression avec glow
        glow_color = QColor("#FFDD00")
        glow_color.setAlpha(30)
        glow_pen = QPen(glow_color, 8)
        painter.setPen(glow_pen)
        painter.drawLine(progress_x, 0, progress_x, height)
        
        # Ligne principale plus épaisse
        line_color = QColor("#FFDD00")
        painter.setPen(QPen(line_color, 4))
        painter.drawLine(progress_x, 0, progress_x, height)

class RotaryKnob(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 50  # Valeur par défaut (0-100)
        self.setFixedSize(54, 54)  # 45 * 1.2 = 54
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
        pen = QPen(QColor("#666666"), 6)  # Arc de base en gris, épaisseur 6px
        painter.setPen(pen)
        rect = QRect(4, 4, self.width() - 8, self.height() - 8)
        painter.drawArc(rect, -135 * 16, -270 * 16)
        
        # Dessiner l'arc rempli en jaune doré
        pen.setColor(QColor("#FFDD00"))  # Changé de blanc à jaune doré
        pen.setWidth(6)  # Arc plus épais, 6px
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

class PanKnob(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 50  # Centre = 50
        self.setFixedSize(32, 32)
        self.is_dragging = False
        self.last_y = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def mouseDoubleClickEvent(self, event):
        # Alterner entre gauche (0%), centre (50%) et droite (100%)
        if self.value < 33:  # Si on est vers la gauche, aller au centre
            self.value = 50
            pan = 0.0
        elif self.value < 66:  # Si on est vers le centre, aller à droite
            self.value = 100
            pan = 1.0
        else:  # Si on est vers la droite, aller à gauche
            self.value = 0
            pan = -1.0
            
        self.update()
        self.parent().parent().set_pan(pan)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dessiner le fond rond gris
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2d2d2d"))
        painter.drawEllipse(0, 0, self.width(), self.height())
        
        # Calculer l'angle
        angle = (self.value - 50) * 1.8  # -90 à +90 degrés
        
        # Ligne blanche
        pen = QPen(QColor("#ffffff"), 4)  # Contour blanc, épaisseur 4px
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Ligne du centre vers le haut par défaut
        center_x = self.width() // 2
        center_y = self.height() // 2
        length = 15
        
        # Calculer la position finale de la ligne
        radians = (angle - 90) * 3.14159 / 180
        end_x = center_x + length * np.cos(radians)
        end_y = center_y + length * np.sin(radians)
        
        painter.drawLine(center_x, center_y, int(end_x), int(end_y))
        
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
            # Convertir la valeur (0-100) en balance (-1 à 1)
            pan = (self.value - 50) / 50.0
            self.parent().parent().set_pan(pan)
            
    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120  # 120 = un cran de molette
        self.value = min(100, max(0, self.value + delta * 2))
        self.update()
        # Convertir la valeur (0-100) en balance (-1 à 1)
        pan = (self.value - 50) / 50.0
        self.parent().parent().set_pan(pan)

class ShuffleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.svg_renderer = QSvgRenderer("shuffle-solid.svg")
        self.setCheckable(True)  # Permet au bouton d'être coché/décoché
        self.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border-radius: 20px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:checked {
                background-color: #3d3d3d;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Dessiner le fond rond gris
        painter.setPen(Qt.PenStyle.NoPen)
        if self.isChecked():
            painter.setBrush(QColor("#3d3d3d"))  # Plus foncé quand actif
        else:
            painter.setBrush(QColor("#2d2d2d"))
        painter.drawEllipse(0, 0, self.width(), self.height())
        
        # Calculer la taille et la position de l'icône (plus petite)
        icon_size = min(self.width(), self.height()) * 0.45  # Réduit à 45% du bouton
        x = (self.width() - icon_size) / 2
        y = (self.height() - icon_size) / 2
        
        # Dessiner l'icône SVG
        if self.isChecked():
            # Créer une image temporaire pour l'icône avec une résolution plus élevée
            scale_factor = 2  # Augmenter la résolution
            temp_image = QImage(icon_size * scale_factor, icon_size * scale_factor, QImage.Format.Format_ARGB32)
            temp_image.fill(Qt.GlobalColor.transparent)
            temp_painter = QPainter(temp_image)
            temp_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            temp_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self.svg_renderer.render(temp_painter, QRectF(0, 0, icon_size * scale_factor, icon_size * scale_factor))
            temp_painter.end()
            
            # Convertir l'image en jaune doré
            for i in range(temp_image.width()):
                for j in range(temp_image.height()):
                    color = temp_image.pixelColor(i, j)
                    if color.alpha() > 0:  # Si le pixel n'est pas transparent
                        temp_image.setPixelColor(i, j, QColor("#FFDD00"))
            
            # Dessiner l'image modifiée avec lissage
            painter.drawImage(QRectF(x, y, icon_size, icon_size), temp_image)
        else:
            # Dessiner l'icône en blanc avec lissage
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setBrush(QColor("#FFFFFF"))
            self.svg_renderer.render(painter, QRectF(x, y, icon_size, icon_size))
        
        painter.end()

    def setActive(self, active):
        self.setChecked(active)  # Mettre à jour l'état coché
        self.update()  # Forcer le redessinage

class RepeatButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.svg_renderer = QSvgRenderer("repeat-solid.svg")
        self.setCheckable(True)  # Permet au bouton d'être coché/décoché
        self.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border-radius: 20px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:checked {
                background-color: #3d3d3d;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Dessiner le fond rond gris
        painter.setPen(Qt.PenStyle.NoPen)
        if self.isChecked():
            painter.setBrush(QColor("#3d3d3d"))  # Plus foncé quand actif
        else:
            painter.setBrush(QColor("#2d2d2d"))
        painter.drawEllipse(0, 0, self.width(), self.height())
        
        # Calculer la taille et la position de l'icône (plus petite)
        icon_size = min(self.width(), self.height()) * 0.45  # Réduit à 45% du bouton
        x = (self.width() - icon_size) / 2
        y = (self.height() - icon_size) / 2
        
        # Dessiner l'icône SVG
        if self.isChecked():
            # Créer une image temporaire pour l'icône avec une résolution plus élevée
            scale_factor = 2  # Augmenter la résolution
            temp_image = QImage(icon_size * scale_factor, icon_size * scale_factor, QImage.Format.Format_ARGB32)
            temp_image.fill(Qt.GlobalColor.transparent)
            temp_painter = QPainter(temp_image)
            temp_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            temp_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self.svg_renderer.render(temp_painter, QRectF(0, 0, icon_size * scale_factor, icon_size * scale_factor))
            temp_painter.end()
            
            # Convertir l'image en jaune doré
            for i in range(temp_image.width()):
                for j in range(temp_image.height()):
                    color = temp_image.pixelColor(i, j)
                    if color.alpha() > 0:  # Si le pixel n'est pas transparent
                        temp_image.setPixelColor(i, j, QColor("#FFDD00"))
            
            # Dessiner l'image modifiée avec lissage
            painter.drawImage(QRectF(x, y, icon_size, icon_size), temp_image)
        else:
            # Dessiner l'icône en blanc avec lissage
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setBrush(QColor("#FFFFFF"))
            self.svg_renderer.render(painter, QRectF(x, y, icon_size, icon_size))
        
        painter.end()

    def setActive(self, active):
        self.setChecked(active)  # Mettre à jour l'état coché
        self.update()  # Forcer le redessinage

class AudioPlayer:
    def __init__(self):
        self.audio_data = None
        self.sample_rate = None
        self.is_playing = False
        self.current_frame = 0
        self.stream = None
        self.volume = 1.0
        self.pan = 0.0
        self.repeat_enabled = False
        self.buffer_size = 512
        self.channels = 2
        self.preload_buffer = None
        self.audio_cache = {}
        self.auto_play_next = True  # Activer la lecture automatique par défaut
        
    def load_file(self, file_path):
        try:
            # Vérifier si le fichier est déjà en cache
            if file_path in self.audio_cache:
                self.audio_data, self.sample_rate = self.audio_cache[file_path]
                self.current_frame = 0
                return True
                
            # Charger le fichier audio avec librosa de manière ultra optimisée
            audio_data, sample_rate = librosa.load(file_path, sr=None, mono=False, res_type='kaiser_fast')
            
            # Convertir en stéréo si mono
            if len(audio_data.shape) == 1:
                audio_data = np.vstack((audio_data, audio_data))
            
            # Mettre en cache
            self.audio_cache[file_path] = (audio_data, sample_rate)
            
            self.audio_data = audio_data
            self.sample_rate = sample_rate
            self.current_frame = 0
            
            # Précharger un petit buffer pour une meilleure réactivité
            self.preload_buffer = audio_data[:, :self.buffer_size]
            
            return True
        except Exception as e:
            print(f"Erreur chargement audio: {e}")
            return False
            
    def audio_callback(self, outdata, frames, time, status):
        if self.audio_data is None:
            outdata.fill(0)
            return
            
        if self.current_frame + frames > self.audio_data.shape[1]:
            # Fin du fichier
            remaining = self.audio_data.shape[1] - self.current_frame
            if remaining > 0:
                outdata[:remaining] = self.apply_pan_and_volume(self.audio_data[:, self.current_frame:self.current_frame + remaining].T)
                outdata[remaining:] = 0
                
                # Si repeat est activé, recommencer la piste
                if self.repeat_enabled:
                    self.current_frame = 0
                    if remaining < frames:
                        outdata[remaining:] = self.apply_pan_and_volume(self.preload_buffer[:, :frames-remaining].T)
                    if hasattr(self, 'parent') and hasattr(self.parent, 'waveform_widget'):
                        self.parent.waveform_widget.set_position(0)
                else:
                    self.stream.stop()
                    self.is_playing = False
                    # Passer à la piste suivante si auto_play_next est activé
                    if self.auto_play_next and hasattr(self, 'parent'):
                        self.parent.next_track()
        else:
            # Lecture normale
            chunk = self.audio_data[:, self.current_frame:self.current_frame + frames].T
            outdata[:] = self.apply_pan_and_volume(chunk)
            self.current_frame += frames
            
    def apply_pan_and_volume(self, audio_chunk):
        # Appliquer le volume et le pan de manière ultra optimisée
        audio_chunk = audio_chunk * self.volume
        
        if self.pan != 0:
            if self.pan < 0:  # Pan vers la gauche
                audio_chunk[:, 1] *= (1 + self.pan)
            else:  # Pan vers la droite
                audio_chunk[:, 0] *= (1 - self.pan)
                
        return audio_chunk
            
    def play(self, start_pos=0):
        if self.audio_data is None:
            return
            
        self.current_frame = int(start_pos * self.sample_rate)
        
        try:
            # Arrêter le stream existant s'il y en a un
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            self.stream = sd.OutputStream(
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=self.audio_callback,
                blocksize=self.buffer_size,
                latency='low',  # Réduire la latence
                dtype=np.float32  # Utiliser float32 pour de meilleures performances
            )
            self.stream.start()
            self.is_playing = True
        except Exception as e:
            print(f"Erreur lecture: {e}")
            
    def pause(self):
        if self.stream:
            self.stream.stop()
            self.is_playing = False
            
    def stop(self):
        if self.stream:
            self.stream.stop()
            self.is_playing = False
            self.current_frame = 0
            
    def set_volume(self, volume):
        self.volume = volume
        
    def set_pan(self, pan):
        self.pan = pan
        
    def get_position(self):
        if self.audio_data is None:
            return 0
        return self.current_frame / self.sample_rate
        
    def get_duration(self):
        if self.audio_data is None:
            return 0
        return self.audio_data.shape[1] / self.sample_rate
        
    def clear_cache(self):
        """Nettoie le cache audio"""
        self.audio_cache.clear()

class MacAmp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Charger la police Inter
        font_id = QFontDatabase.addApplicationFont("Inter_24pt-Regular.ttf")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.setFont(QFont(font_family, 12))
        
        self.setWindowTitle("MacAmp")
        self.setGeometry(100, 100, 360, 430)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111111;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        self.is_large = False
        self.repeat_enabled = False
        
        # Initialiser le lecteur audio
        self.audio_player = AudioPlayer()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Zone supérieure (pochette + contrôles)
        top_container = QVBoxLayout()
        top_container.setSpacing(0)
        top_container.setContentsMargins(0, 0, 0, 0)
        
        # Layout horizontal pour cover + waveform
        self.cover_wave_layout = QHBoxLayout()
        self.cover_wave_layout.setSpacing(8)
        self.cover_wave_layout.setContentsMargins(8, 8, 8, 0)
        
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
        self.cover_wave_layout.addWidget(self.cover_label)
        
        # Waveform
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setFixedHeight(180)
        self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cover_wave_layout.addWidget(self.waveform_widget)
        
        # Ajouter le layout cover + waveform au container principal
        top_container.addLayout(self.cover_wave_layout)
        
        # Contrôles de lecture avec hamburger à gauche, autres à droite
        playback_layout = QHBoxLayout()
        playback_layout.setSpacing(5)
        playback_layout.setContentsMargins(8, 0, 8, 0)
        
        button_size = 32
        self.hamburger_button = QPushButton("≡")
        self.hamburger_button.setFixedSize(button_size, button_size)
        self.hamburger_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hamburger_button.setStyleSheet(f"""
            QPushButton {{
                font-size: 16px;
                background-color: #2d2d2d;
                border-radius: {button_size//2}px;
                padding: 0px;
                margin: 0px;
                color: #FFFFFF;
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
                color: #FFDD00;
            }}
        """)
        self.hamburger_button.clicked.connect(self.toggle_playlist)
        playback_layout.addWidget(self.hamburger_button)
        playback_layout.addStretch(1)
        
        self.shuffle_button = ShuffleButton()
        self.prev_button = QPushButton("⏮")
        self.play_button = QPushButton("▶")
        self.stop_button = QPushButton("⏹")
        self.next_button = QPushButton("⏭")
        self.repeat_button = RepeatButton()
        self.volume_knob = RotaryKnob()
        self.pan_knob = PanKnob()
        
        # Activer les boutons shuffle et repeat
        self.shuffle_button.setEnabled(True)
        self.repeat_button.setEnabled(True)
        self.shuffle_button.setCheckable(True)
        self.repeat_button.setCheckable(True)
        
        buttons = [
            (self.prev_button, 14),
            (self.play_button, 16),
            (self.stop_button, 14),
            (self.next_button, 14),
            (self.repeat_button, 14),
            (self.shuffle_button, 16)
        ]
        
        for button, font_size in buttons:
            button.setFixedSize(button_size, button_size)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(f"""
                QPushButton {{
                    font-size: {font_size}px;
                    background-color: #2d2d2d;
                    border-radius: {button_size//2}px;
                    padding: 0px;
                    margin: 0px;
                    color: #FFFFFF;
                }}
                QPushButton:hover {{
                    background-color: #3d3d3d;
                    color: #FFDD00;
                }}
                QPushButton:checked {{
                    background-color: #3d3d3d;
                    color: #FFDD00;
                }}
                QPushButton:pressed {{
                    background-color: #3d3d3d;
                    color: #FFDD00;
                }}
                QPushButton:disabled {{
                    color: #666666;
                }}
            """)
            playback_layout.addWidget(button)
        playback_layout.addWidget(self.pan_knob)
        playback_layout.addSpacing(6)
        playback_layout.addWidget(self.volume_knob)
        
        # Connecter les boutons à leurs fonctions
        self.shuffle_button.clicked.connect(self.toggle_shuffle)
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.prev_button.clicked.connect(self.previous_track)
        self.next_button.clicked.connect(self.next_track)
        self.repeat_button.clicked.connect(self.toggle_repeat)
        
        self.shuffle_enabled = False
        self.shuffle_order = []
        self.shuffle_pos = 0
        
        top_container.addLayout(playback_layout)
        layout.addLayout(top_container)
        
        # --- Playlist dans un container pour masquer/afficher sans changer la taille de la fenêtre ---
        self.playlist_container = QStackedWidget()
        self.playlist_widget = PlaylistWidget(self)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_track)
        self.playlist_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 0px;
                margin: 0px;
            }
            QTreeWidget::item {
                padding-left: -20px;
                padding: 0px;
                margin: 0px;
                border-radius: 0px;
            }
            QTreeWidget::item:selected {
                background: none;
            }
            QTreeWidget::item:hover {
                background: none;
            }
            QHeaderView::section {
                background-color: transparent;
                color: #ffffff;
                padding: 0px;
                margin: 0px;
                border: none;
                font-weight: bold;
            }
        """)
        self.empty_placeholder = QWidget()
        self.empty_placeholder.setStyleSheet("background: #111111;")
        self.playlist_container.addWidget(self.playlist_widget)
        self.playlist_container.addWidget(self.empty_placeholder)
        layout.addWidget(self.playlist_container)
        # --- Fin container ---
        
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
        layout.addWidget(self.browse_button)
        
        central_widget.setLayout(layout)
        
        pygame.mixer.init()
        self.current_file = None
        self.is_playing = False
        self.playlist = []
        self.current_index = -1
        self.waveform = None
        self.current_position = 0
        
        # Playlist visible par défaut
        self.playlist_visible = True
        self._last_full_size = self.size()
    
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
            
    def clean_title(self, artist, title):
        """Nettoie le titre en retirant l'artiste s'il est présent"""
        if artist and artist.lower() in title.lower():
            # Essayer différents formats courants
            patterns = [
                f"{artist} - ",
                f"{artist}-",
                f"[{artist}]",
                f"({artist})",
                f"{artist}:",
                f"{artist}_"
            ]
            for pattern in patterns:
                if pattern.lower() in title.lower():
                    return title.replace(pattern, "").strip()
        return title

    def get_metadata(self, file_path):
        try:
            # Valeurs par défaut
            metadata = {
                'artist': "",
                'title': os.path.basename(file_path),
                'duration': '00:00'
            }
            
            # Extraire le nom de fichier sans extension comme fallback
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Si le nom contient un tiret, on peut essayer d'extraire artiste et titre
            if " - " in base_name:
                parts = base_name.split(" - ", 1)
                metadata['artist'] = parts[0].strip()
                metadata['title'] = parts[1].strip()
            
            # Calculer la durée avec librosa (plus précis)
            try:
                y, sr = librosa.load(file_path, sr=None, duration=5)  # Charger juste les 5 premières secondes pour la détection
                duration = librosa.get_duration(y=y, sr=sr)
                if duration > 0:
                    # Si c'est un extrait, calculer la durée totale
                    total_duration = librosa.get_duration(filename=file_path)
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    metadata['duration'] = f"{minutes:02d}:{seconds:02d}"
            except Exception as e:
                print(f"Erreur librosa: {e}, tentative avec mutagen...")
                
                # Si librosa échoue, essayer avec mutagen
                audio = File(file_path)
                if audio is not None and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                    duration = audio.info.length
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    metadata['duration'] = f"{minutes:02d}:{seconds:02d}"
                
            # Essayer de lire les métadonnées selon le format
            audio = File(file_path)
            if isinstance(audio, MP3):
                try:
                    id3 = EasyID3(file_path)
                    metadata['artist'] = id3.get('artist', [metadata['artist']])[0]
                    raw_title = id3.get('title', [metadata['title']])[0]
                    metadata['title'] = self.clean_title(metadata['artist'], raw_title)
                except:
                    pass
                    
            elif file_path.lower().endswith(('.wav', '.aiff')):
                if audio is not None and hasattr(audio, 'tags'):
                    for tag in audio.tags:
                        if 'artist' in tag.lower():
                            metadata['artist'] = str(audio.tags[tag])
                        elif 'title' in tag.lower():
                            raw_title = str(audio.tags[tag])
                            metadata['title'] = self.clean_title(metadata['artist'], raw_title)
            
            return metadata
            
        except Exception as e:
            print(f"Erreur lecture métadonnées: {e}")
            return {
                'artist': "",
                'title': os.path.basename(file_path),
                'duration': '00:00'
            }
            
    def add_files(self, files):
        for file_path in files:
            self.playlist.append(file_path)
            metadata = self.get_metadata(file_path)
            item = QTreeWidgetItem([
                metadata['artist'].strip(),  # Supprimer tous les espaces en début et fin
                metadata['title'],
            ])
            self.playlist_widget.addTopLevelItem(item)
            # Forcer l'alignement à gauche de la colonne Artiste
            item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if self.current_index == -1 and self.playlist:
            self.current_index = 0
            self.load_track(self.playlist[0])
            self.update_active_track()  # Mise à jour des couleurs pour la première piste
            # Correction : si la cover est absente, forcer le layout pour la waveform
            if not self.cover_label.isVisible():
                QTimer.singleShot(0, self._force_waveform_full_width)
                QTimer.singleShot(30, self._force_waveform_full_width)
                QTimer.singleShot(100, self._force_waveform_full_width)
            
    def browse_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers audio",
            "",
            "Fichiers audio (*.mp3 *.wav *.ogg *.aiff)"
        )
        
        if file_names:
            self.add_files(file_names)
            
    def update_active_track(self):
        for i in range(self.playlist_widget.topLevelItemCount()):
            item = self.playlist_widget.topLevelItem(i)
            if i == self.current_index:
                item.setForeground(0, QColor("#FFDD00"))
                item.setForeground(1, QColor("#FFDD00"))
            else:
                item.setForeground(0, QColor("#FFFFFF"))
                item.setForeground(1, QColor("#FFFFFF"))

    def play_selected_track(self, item):
        index = self.playlist_widget.indexOfTopLevelItem(item)
        if 0 <= index < len(self.playlist):
            self.current_index = index
            if self.shuffle_enabled:
                # Mettre à jour la position dans l'ordre shuffle
                if self.shuffle_order:
                    self.shuffle_pos = self.shuffle_order.index(index)
            self.load_track(self.playlist[index])
            self.play()
            self.update_active_track()
            
    def previous_track(self):
        if not self.playlist:
            return

        if self.shuffle_enabled and len(self.playlist) > 1:
            if self.shuffle_pos > 0:
                self.shuffle_pos -= 1
                self.current_index = self.shuffle_order[self.shuffle_pos]
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()
            elif self.repeat_enabled:
                # Si repeat est activé, aller à la dernière piste
                self.shuffle_pos = len(self.shuffle_order) - 1
                self.current_index = self.shuffle_order[self.shuffle_pos]
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()
        else:
            if self.current_index > 0:
                self.current_index -= 1
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()
            elif self.repeat_enabled:
                # Si repeat est activé, aller à la dernière piste
                self.current_index = len(self.playlist) - 1
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()

    def next_track(self):
        if not self.playlist:
            return

        if self.shuffle_enabled and len(self.playlist) > 1:
            if not self.shuffle_order:
                self.toggle_shuffle()  # (re)générer l'ordre si vide
            if self.shuffle_pos < len(self.shuffle_order) - 1:
                self.shuffle_pos += 1
                self.current_index = self.shuffle_order[self.shuffle_pos]
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()
            elif self.repeat_enabled:
                # Si repeat est activé, recommencer depuis le début
                self.shuffle_pos = 0
                self.current_index = self.shuffle_order[self.shuffle_pos]
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()
        else:
            if self.current_index < len(self.playlist) - 1:
                self.current_index += 1
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()
            elif self.repeat_enabled:
                # Si repeat est activé, recommencer depuis le début
                self.current_index = 0
                self.load_track(self.playlist[self.current_index])
                self.play()
                self.update_active_track()

    def play_from_position(self, position):
        """Démarre la lecture à une position spécifique"""
        try:
            if self.current_file:
                # Arrêter la lecture en cours si elle existe
                if self.is_playing:
                    self.audio_player.stop()
                
                # Démarrer la nouvelle lecture
                self.audio_player.play(start_pos=position)
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
                self.audio_player.pause()
                self.play_button.setText("▶")
                self.is_playing = False
        except Exception as e:
            print(f"Erreur toggle: {e}")
            
    def stop(self):
        try:
            self.audio_player.stop()
            self.play_button.setText("▶")
            self.is_playing = False
            self.current_position = 0
            self.waveform_widget.set_position(0)
        except Exception as e:
            print(f"Erreur stop: {e}")
            
    def set_volume(self, value):
        try:
            self.audio_player.set_volume(value / 100)
        except Exception as e:
            print(f"Erreur volume: {e}")
            
    def set_pan(self, value):
        try:
            self.audio_player.set_pan(value)  # value est déjà entre -1 et 1
        except Exception as e:
            print(f"Erreur pan: {e}")

    def load_track(self, file_name):
        try:
            print(f"Chargement de la piste: {file_name}")
            self.current_file = file_name
            self.update_active_track()
            
            # Charger la waveform de manière optimisée
            y, sr = librosa.load(file_name, sr=None, duration=None, mono=True)  # Charger en mono pour la waveform
            duration = len(y) / sr
            # Réduire la résolution de la waveform pour de meilleures performances
            self.waveform = librosa.resample(y, orig_sr=sr, target_sr=1000)  # Réduit à 1000Hz au lieu de 2000Hz
            print(f"Waveform chargée, durée: {duration} secondes")
            self.waveform_widget.set_waveform(self.waveform, duration)
            
            # Charger l'audio avec le nouveau lecteur de manière asynchrone
            if self.audio_player.load_file(file_name):
                # Appliquer les réglages actuels
                self.audio_player.set_volume(self.volume_knob.value / 100)
                pan = (self.pan_knob.value - 50) / 50.0
                self.audio_player.set_pan(pan)
                print("Audio chargé et volume réglé")
            
            # Mettre à jour les boutons
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.prev_button.setEnabled(self.current_index > 0)
            self.next_button.setEnabled(self.current_index < len(self.playlist) - 1)
            
            # Réinitialiser la position
            self.current_position = 0
            self.waveform_widget.set_position(0)
            
            # Optimiser le chargement de la pochette
            self.load_cover_art(file_name)
            
            self.track_loaded = True
            print("Audio chargé et volume réglé")
            
        except Exception as e:
            print(f"Erreur chargement: {e}")

    def load_cover_art(self, file_name):
        """Charge la pochette de manière optimisée"""
        try:
            # Créer un widget personnalisé pour l'affichage par défaut
            default_cover = QWidget()
            default_cover.setFixedSize(180, 180)
            default_cover.setStyleSheet("""
                background-color: #2d2d2d;
                border-radius: 8px;
            """)
            # Charger la pochette de manière optimisée
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
                                # S'assurer que la cover est dans le layout
                                if self.cover_wave_layout.indexOf(self.cover_label) == -1:
                                    self.cover_wave_layout.insertWidget(0, self.cover_label)
                                self.cover_label.show()
                                self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                                self.cover_label.setPixmap(pixmap)
                                self.cover_label.show()
                                self.waveform_widget.setFixedHeight(180)
                                print("Pochette MP3 chargée")
                                return
            elif file_name.lower().endswith(('.wav', '.aiff')):
                audio = File(file_name)
                if audio is not None:
                    if hasattr(audio, 'tags'):
                        for tag in audio.tags.values():
                            if hasattr(tag, 'data') and isinstance(tag.data, bytes):
                                try:
                                    pixmap = QPixmap()
                                    pixmap.loadFromData(tag.data)
                                    if not pixmap.isNull():
                                        # S'assurer que la cover est dans le layout
                                        if self.cover_wave_layout.indexOf(self.cover_label) == -1:
                                            self.cover_wave_layout.insertWidget(0, self.cover_label)
                                        self.cover_label.show()
                                        self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                                        self.cover_label.setPixmap(pixmap)
                                        self.cover_label.show()
                                        self.waveform_widget.setFixedHeight(180)
                                        print(f"Pochette {file_name.split('.')[-1].upper()} chargée via tags")
                                        return
                                except:
                                    continue
            # Si pas de pochette trouvée, chercher une image dans le même dossier
            base_path = os.path.dirname(file_name)
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            possible_names = [
                'cover', 'folder', 'album', 'front',
                base_name
            ]
            for name in possible_names:
                for ext in image_extensions:
                    image_path = os.path.join(base_path, name + ext)
                    if os.path.exists(image_path):
                        try:
                            pixmap = QPixmap(image_path)
                            if not pixmap.isNull():
                                # S'assurer que la cover est dans le layout
                                if self.cover_wave_layout.indexOf(self.cover_label) == -1:
                                    self.cover_wave_layout.insertWidget(0, self.cover_label)
                                self.cover_label.show()
                                self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                                self.cover_label.setPixmap(pixmap)
                                self.cover_label.show()
                                self.waveform_widget.setFixedHeight(180)
                                print(f"Image trouvée dans le dossier: {image_path}")
                                return
                        except:
                            continue
            # Si toujours rien trouvé, créer une pochette par défaut élégante
            self.create_default_cover()
        except Exception as e:
            print(f"Erreur pochette: {e}")
            self.create_default_cover()

    def create_default_cover(self):
        """Crée une pochette par défaut élégante et affiche la waveform en grand"""
        # Retirer la cover du layout si elle y est
        if self.cover_wave_layout.indexOf(self.cover_label) != -1:
            self.cover_wave_layout.removeWidget(self.cover_label)
        self.cover_label.hide()
        self.waveform_widget.setFixedHeight(180)
        self.waveform_widget.setMinimumWidth(0)
        self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.waveform_widget.updateGeometry()
        self.cover_wave_layout.update()
        if self.centralWidget() is not None:
            self.centralWidget().updateGeometry()
            if self.centralWidget().layout() is not None:
                self.centralWidget().layout().activate()
        self.resize(self.size())
        self.waveform_widget.repaint()
        # Correction Qt : forcer le layout à la prochaine boucle d'événement (plusieurs fois pour fiabiliser)
        QTimer.singleShot(0, self._force_waveform_full_width)
        QTimer.singleShot(30, self._force_waveform_full_width)
        QTimer.singleShot(100, self._force_waveform_full_width)
        QTimer.singleShot(200, self._force_waveform_full_width_final)

    def _force_waveform_full_width(self):
        self.waveform_widget.updateGeometry()
        self.waveform_widget.repaint()
        parent = self.waveform_widget.parentWidget()
        if parent is not None:
            parent.updateGeometry()
        if self.centralWidget() is not None:
            self.centralWidget().updateGeometry()
            if self.centralWidget().layout() is not None:
                self.centralWidget().layout().activate()
        self.resize(self.size())

    def _force_waveform_full_width_final(self):
        self.waveform_widget.updateGeometry()
        self.waveform_widget.repaint()
        parent = self.waveform_widget.parentWidget()
        if parent is not None:
            parent.updateGeometry()
        if self.centralWidget() is not None:
            self.centralWidget().updateGeometry()
            if self.centralWidget().layout() is not None:
                self.centralWidget().layout().activate()
        self.resize(self.size())
        self.adjustSize()

    def toggle_shuffle(self):
        self.shuffle_enabled = not self.shuffle_enabled
        if self.shuffle_enabled:
            import random
            self.shuffle_order = list(range(len(self.playlist)))
            if len(self.shuffle_order) > 1:
                random.shuffle(self.shuffle_order)
                # Mettre la piste courante en premier
                if self.current_index in self.shuffle_order:
                    self.shuffle_order.remove(self.current_index)
                self.shuffle_order.insert(0, self.current_index)
            self.shuffle_pos = 0
        else:
            self.shuffle_order = []
            self.shuffle_pos = 0
        self.shuffle_button.setChecked(self.shuffle_enabled)
        print(f"Shuffle {'activé' if self.shuffle_enabled else 'désactivé'}")

    def toggle_repeat(self):
        """Active/désactive la répétition de la piste en cours"""
        self.repeat_enabled = not self.repeat_enabled
        self.repeat_button.setChecked(self.repeat_enabled)
        self.audio_player.repeat_enabled = self.repeat_enabled  # Synchroniser avec l'audio player
        print(f"Repeat {'activé' if self.repeat_enabled else 'désactivé'}")
        
        # Si repeat est activé et qu'une piste est en cours de lecture, s'assurer qu'elle continue
        if self.repeat_enabled and self.is_playing:
            self.play()  # Utiliser la méthode play au lieu de self.stream.start()
            
        # Ajouter un timer pour vérifier la fin de la piste et réinitialiser la waveform
        if self.repeat_enabled:
            self.check_end_timer = QTimer()
            self.check_end_timer.timeout.connect(self.check_track_end)
            self.check_end_timer.start(100)  # Vérifier toutes les 100ms
        else:
            if hasattr(self, 'check_end_timer'):
                self.check_end_timer.stop()
                
    def check_track_end(self):
        """Vérifie si la piste est terminée et réinitialise la waveform si nécessaire"""
        if self.repeat_enabled and self.is_playing:
            current_pos = self.audio_player.get_position()
            duration = self.audio_player.get_duration()
            # Réinitialiser la waveform juste avant la fin de la piste
            if current_pos >= duration - 0.1:  # 100ms avant la fin
                self.waveform_widget.set_position(0)

    def toggle_playlist(self):
        taille_compacte = QSize(360, 430)
        taille_etendue = QSize(530, 430)
        self.playlist_container.setCurrentWidget(self.playlist_widget)
        self.browse_button.show()
        self.centralWidget().layout().activate()
        if not self.is_large:
            self.resize(taille_etendue)
            self.is_large = True
        else:
            self.resize(taille_compacte)
            self.is_large = False

def main():
    app = QApplication(sys.argv)
    
    # Utiliser une police système moderne par défaut
    app.setFont(QFont("SF Pro", 11))
    
    window = MacAmp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 