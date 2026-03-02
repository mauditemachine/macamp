import sys
import os
import datetime

def debug_log(msg):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_msg = f"[DEBUG] {timestamp} {msg}"
    print(full_msg, flush=True)
    try:
        with open("/tmp/macamp_debug.log", "a") as f:
            f.write(full_msg + "\n")
    except Exception as e:
        print(f"[DEBUG] Impossible d'écrire dans le log : {e}", flush=True)

print("[LOG] Script macamp.py lancé, sys.argv =", sys.argv, flush=True)
debug_log(f"Script macamp.py lancé, sys.argv = {sys.argv}")
import numpy as np
import librosa
import sounddevice as sd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QLabel)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPainter, QColor, QPen, QFontDatabase, QFont
import time
import threading
import pyglet
import soundfile as sf

# Correction PyInstaller : forcer le chemin des plugins Qt pour le mode standalone
if getattr(sys, 'frozen', False):
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt6', 'plugins', 'platforms')

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform = None
        self.current_position = 0
        self.duration = 0
        self.setMinimumWidth(1000)
        self.setMaximumWidth(1000)
        self.setFixedHeight(180)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
            }
        """)
        self.is_dragging = False
        self.drag_over = False
        self.setAcceptDrops(True)

    def set_position(self, position):
        self.current_position = position
        self.update()

    def set_waveform(self, waveform, duration):
        self.waveform = waveform
        self.duration = duration
        self.update()

    def mousePressEvent(self, event):
        if self.waveform is not None and event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            width = self.width()
            ratio = max(0, min(1, event.position().x() / width))
            print(f"[LOG] mousePressEvent : clic, x={event.position().x()}, ratio={ratio:.3f}", flush=True)
            self.current_position = ratio
            self.update()
            parent = self.parent()
            while parent and not hasattr(parent, 'finalize_seek'):
                parent = parent.parent()
            if parent and hasattr(parent, 'finalize_seek'):
                parent.finalize_seek(ratio)

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.waveform is not None:
            width = self.width()
            ratio = max(0, min(1, event.position().x() / width))
            print(f"[LOG] mouseMoveEvent : drag, x={event.position().x()}, ratio={ratio:.3f}", flush=True)
            self.current_position = ratio
            self.update()
            parent = self.parent()
            while parent and not hasattr(parent, 'finalize_seek'):
                parent = parent.parent()
            if parent and hasattr(parent, 'finalize_seek'):
                parent.finalize_seek(ratio)

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def dragEnterEvent(self, event):
        print('[LOG] dragEnterEvent appelé', flush=True)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                print(f'[LOG] dragEnterEvent url={url.toLocalFile()}', flush=True)
                if url.toLocalFile().lower().endswith((".mp3", ".wav", ".ogg", ".aiff")):
                    event.acceptProposedAction()
                    self.drag_over = True
                    self.update()
                    print('[LOG] dragEnterEvent accepté', flush=True)
                    return
        event.ignore()
        print('[LOG] dragEnterEvent ignoré', flush=True)

    def dragLeaveEvent(self, event):
        self.drag_over = False
        self.update()

    def dropEvent(self, event):
        print('[LOG] dropEvent appelé', flush=True)
        self.drag_over = False
        self.update()
        try:
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    print(f'[LOG] dropEvent file_path={file_path}', flush=True)
                    if file_path.lower().endswith((".mp3", ".wav", ".ogg", ".aiff")):
                        parent = self.parent()
                        while parent and not hasattr(parent, 'load_file'):
                            parent = parent.parent()
                        if parent and hasattr(parent, 'load_file'):
                            print(f'[LOG] dropEvent appel load_file({file_path})', flush=True)
                            parent.load_file(file_path)
                        else:
                            print('[LOG] dropEvent: pas de parent avec load_file', flush=True)
                        break
        except Exception as e:
            import traceback
            print(f'[LOG] Exception dans dropEvent: {e}\n{traceback.format_exc()}', flush=True)

    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width()
        height = self.height()
        # Effet visuel
        # drag-over
        if self.drag_over:
            painter.fillRect(0, 0, width, height, QColor(40, 40, 40))
        else:
            painter.fillRect(0, 0, width, height, QColor(26, 26, 26))
        if self.waveform is None:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar_width = 4
        gap = 2
        num_bars = width // (bar_width + gap)
        samples_per_bar = len(self.waveform) // num_bars
        for i in range(num_bars):
            if i * samples_per_bar >= len(self.waveform):
                break
            start_idx = i * samples_per_bar
            end_idx = min((i + 1) * samples_per_bar, len(self.waveform))
            if end_idx > start_idx:
                amplitude = np.mean(np.abs(self.waveform[start_idx:end_idx]))
                amplitude = min(1.0, amplitude * 2.5)
            else:
                amplitude = 0
            x = i * (bar_width + gap)
            bar_height = int(amplitude * height * 0.98)
            y_center = height // 2
            y_top = y_center - bar_height // 2
            if x <= self.current_position * width:
                painter.fillRect(x, y_top, bar_width, bar_height, QColor("#FFDD00"))
            else:
                painter.fillRect(x, y_top, bar_width, bar_height, QColor(80, 80, 80))
        progress_x = int(self.current_position * width)
        glow_color = QColor("#FFDD00")
        glow_color.setAlpha(30)
        glow_pen = QPen(glow_color, 8)
        painter.setPen(glow_pen)
        painter.drawLine(progress_x, 0, progress_x, height)
        line_color = QColor("#FFDD00")
        painter.setPen(QPen(line_color, 4))
        painter.drawLine(progress_x, 0, progress_x, height)

class LoaderWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, file_name):
        super().__init__()
        self.file_name = file_name
    def run(self):
        import time
        debug_log(f"LoaderWorker.run lancé pour {self.file_name}")
        t0 = time.time()
        try:
            import numpy as np
            import librosa
            import soundfile as sf
            import mutagen
            import pyloudnorm as pyln
            debug_log(f"Début chargement : {self.file_name}")
            info = sf.info(self.file_name)
            debug_log(f"sf.info OK : {info}")
            bit_depth = info.subtype_info if hasattr(info, 'subtype_info') else ''
            bits = None
            if hasattr(info, 'subtype') and 'PCM' in info.subtype:
                if '24' in info.subtype:
                    bits = 24
                elif '16' in info.subtype:
                    bits = 16
                elif '32' in info.subtype:
                    bits = 32
            elif hasattr(info, 'subtype') and 'FLOAT' in info.subtype:
                bits = 32
            else:
                bits = None
            # --- Chargement audio (conversion à la volée si besoin) ---
            temp_wav_path = None
            t3 = time.time()
            if bits == 24:
                y_stereo, sr = sf.read(self.file_name, dtype='float32', always_2d=True)
                if len(y_stereo.shape) == 2:
                    y = np.mean(y_stereo, axis=1)
                else:
                    y = y_stereo
                import tempfile
                tmp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                sf.write(tmp_wav.name, y, sr, subtype='PCM_16')
                temp_wav_path = tmp_wav.name
            else:
                y_stereo, sr = sf.read(self.file_name, dtype='float32', always_2d=True)
                if y_stereo.shape[1] == 1:
                    y = y_stereo[:,0]
                else:
                    y = np.mean(y_stereo, axis=1)
            t4 = time.time()
            debug_log(f"sf.read + conversion : {t4-t3:.3f}s")
            duration = librosa.get_duration(y=y, sr=sr)
            t5 = time.time()
            debug_log(f"librosa.get_duration : {t5-t4:.3f}s")
            y_norm = y / np.max(np.abs(y))
            artiste = titre = ''
            t6 = time.time()
            try:
                audio = mutagen.File(self.file_name, easy=True)
                if audio:
                    artiste = audio.get('artist', [''])[0]
                    titre = audio.get('title', [''])[0]
            except Exception:
                pass
            t7 = time.time()
            debug_log(f"mutagen (métadonnées) : {t7-t6:.3f}s")
            # --- OPTIMISATION : analyses lourdes sur un extrait de 60s max ---
            max_analysis_sec = 60
            if duration > max_analysis_sec:
                n_samples = int(max_analysis_sec * sr)
                y_short = y[:n_samples]
                y_stereo_short = y_stereo[:n_samples, :] if y_stereo.shape[0] >= n_samples else y_stereo
            else:
                y_short = y
                y_stereo_short = y_stereo
            bpm_str = key_str = year_str = ""
            # BPM
            t8 = time.time()
            try:
                tempo, _ = librosa.beat.beat_track(y=y_short, sr=sr)
                bpm_str = f"BPM : {tempo:.1f}"
            except Exception:
                pass
            t9 = time.time()
            debug_log(f"librosa.beat.beat_track (extrait) : {t9-t8:.3f}s")
            # Tonalité
            t10 = time.time()
            try:
                chroma = librosa.feature.chroma_cqt(y=y_short, sr=sr)
                key_idx = chroma.mean(axis=1).argmax()
                key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                key_str = f"Key : {key_names[key_idx]}"
            except Exception:
                pass
            t11 = time.time()
            debug_log(f"librosa.feature.chroma_cqt (extrait) : {t11-t10:.3f}s")
            # Année
            t12 = time.time()
            try:
                audio = mutagen.File(self.file_name)
                year = None
                if audio:
                    if 'date' in audio:
                        year = audio['date'][0]
                    elif 'TDRC' in audio:
                        year = str(audio['TDRC'])
                    elif hasattr(audio, 'tags') and audio.tags:
                        for tag in ['date', 'year', 'TDRC']:
                            if tag in audio.tags:
                                year = str(audio.tags[tag][0])
                                break
                if year:
                    year_str = f"Année : {year}"
            except Exception:
                pass
            t13 = time.time()
            debug_log(f"mutagen (année) : {t13-t12:.3f}s")
            infos = " | ".join([s for s in [bpm_str, key_str, year_str] if s])
            # LUFS
            t14 = time.time()
            try:
                meter = pyln.Meter(sr)
                lufs = meter.integrated_loudness(y_stereo_short)
                lufs_str = f" / LUFS: {lufs:.1f} dB"
            except Exception:
                lufs_str = ""
            t15 = time.time()
            debug_log(f"pyloudnorm (LUFS, extrait) : {t15-t14:.3f}s")
            # Peak
            t16 = time.time()
            try:
                peak = np.max(np.abs(y_stereo_short))
                peak_dbfs = 20 * np.log10(peak) if peak > 0 else -np.inf
                peak_str = f" / Peak : {peak_dbfs:.2f} dBFS"
            except Exception:
                peak_str = ""
            t17 = time.time()
            debug_log(f"Calcul peak (extrait) : {t17-t16:.3f}s")
            # Corrélation
            t18 = time.time()
            try:
                if y_stereo_short.shape[1] == 2:
                    left = y_stereo_short[:,0]
                    right = y_stereo_short[:,1]
                    corr = np.corrcoef(left, right)[0,1]
                    corr_str = f" / Corrélation : {corr:.2f}"
                else:
                    corr_str = ""
            except Exception:
                corr_str = ""
            t19 = time.time()
            debug_log(f"Calcul corrélation (extrait) : {t19-t18:.3f}s")
            quality = f"{int(sr/1000):.1f} kHz"
            t20 = time.time()
            try:
                audio = mutagen.File(self.file_name)
                if audio and hasattr(audio.info, 'bitrate') and audio.info.bitrate:
                    kbps = int(audio.info.bitrate / 1000)
                    quality += f" / {kbps} kbps"
            except Exception:
                pass
            if bits:
                quality += f" / {bits} bits"
            elif bit_depth:
                quality += f" / {bit_depth}"
            quality += lufs_str + peak_str + corr_str
            t21 = time.time()
            debug_log(f"Infos qualité : {t21-t20:.3f}s")
            debug_log(f"Temps total LoaderWorker.run : {t21-t0:.3f}s")
            result = dict(
                y=y,
                y_norm=y_norm,
                sr=sr,
                duration=duration,
                temp_wav_path=temp_wav_path,
                original_file=self.file_name,
                artiste=artiste,
                titre=titre,
                infos=infos,
                quality=quality
            )
            debug_log(f"LoaderWorker.run terminé pour {self.file_name}")
            self.finished.emit(result)
        except Exception as e:
            import traceback
            debug_log(f"Exception dans LoaderWorker.run : {e}\n{traceback.format_exc()}")
            self.error.emit(str(e) + '\n' + traceback.format_exc())

class SimpleAudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacAmp Simple")
        self.setGeometry(100, 100, 1030, 234)
        self.setAcceptDrops(True)
        # Remplacer par la police système par défaut
        self.setStyleSheet("QMainWindow { background-color: #111111; } QLabel { color: #ffffff; }")
        self.current_file = None
        self.is_playing = False
        self.duration = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position)
        self.audio_data = None
        self.sr = None
        self.stream = None
        self.current_frame = 0
        self.requested_position = None
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        self.waveform_widget = WaveformWidget()
        layout.addWidget(self.waveform_widget)
        controls = QHBoxLayout()
        controls.setSpacing(16)
        controls.setContentsMargins(0, 0, 0, 0)
        self.play_button = QPushButton("PLAY")
        self.stop_button = QPushButton("STOP")
        for btn in [self.play_button, self.stop_button]:
            btn.setFixedHeight(30)
            btn.setMinimumWidth(100)
            # Police par défaut ou Cubano pour les boutons
            btn.setFont(QFont("Cubano", 11))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #232323;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 0px;
                    font-family: 'Cubano', sans-serif;
                    font-size: 11px;
                    letter-spacing: 1px;
                }
                QPushButton:hover {
                    background-color: #444444;
                    color: #FFDD00;
                }
                QPushButton:pressed {
                    background-color: #333333;
                }
            """)
            controls.addWidget(btn)
        controls.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #fff; font-size: 13px; margin-left: 32px; font-family: 'Inter', sans-serif;")
        controls.addWidget(self.info_label, stretch=1)
        self.quality_label = QLabel("")
        self.quality_label.setStyleSheet("color: #aaa; font-size: 12px; margin-left: 32px; font-family: 'Inter', sans-serif;")
        controls.addWidget(self.quality_label, stretch=0)
        layout.addLayout(controls)
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.stream_lock = threading.Lock()
        self.seek_pending = False
        self.pending_seek_time = None
        self.pyglet_player = None
        self.pyglet_source = None

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier audio", "", "Audio Files (*.mp3 *.wav *.ogg *.aiff)")
        if file_name:
            self.load_file(file_name)

    def load_file(self, file_name):
        debug_log(f"load_file appelé avec file_name={file_name}")
        self.info_label.setText("Chargement…")
        self.quality_label.setText("")
        self.waveform_widget.set_waveform(None, 0)
        self.waveform_widget.set_position(0)
        # Arrêter et libérer l'ancienne piste si besoin
        if self.pyglet_player:
            print("[LOG] Arrêt et suppression de l'ancienne piste pyglet_player", flush=True)
            self.pyglet_player.pause()
            self.pyglet_player.delete()
            self.pyglet_player = None
            self.pyglet_source = None
        self.current_file = file_name  # Mettre à jour le fichier courant
        # Vérifier l'existence et la lisibilité du fichier
        if not os.path.isfile(file_name):
            debug_log(f"Erreur : fichier introuvable ou illisible : {file_name}")
            self.info_label.setText(f"Erreur : fichier introuvable ou illisible : {file_name}")
            return
        try:
            with open(file_name, 'rb') as f:
                f.read(1)
        except Exception as e:
            debug_log(f"Erreur : impossible de lire le fichier : {e}")
            self.info_label.setText(f"Erreur : impossible de lire le fichier : {e}")
            return
        # Thread
        debug_log(f"Création du thread de chargement audio pour {file_name}")
        self.thread = QThread()
        self.worker = LoaderWorker(file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_load_finished)
        self.worker.error.connect(self.on_load_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_load_finished(self, result):
        debug_log(f"on_load_finished appelé pour {result.get('original_file')}")
        print(f"[LOG] on_load_finished appelé pour {result.get('original_file')}", flush=True)
        y = result['y']
        y_norm = result['y_norm']
        sr = result['sr']
        duration = result['duration']
        temp_wav_path = result['temp_wav_path']
        original_file = result['original_file']
        artiste = result['artiste']
        titre = result['titre']
        infos = result['infos']
        quality = result['quality']
        self.audio_data = y
        self.sr = sr
        self.duration = duration
        # --- Affichage waveform : dynamique réelle simple (valeurs absolues, non normalisées) ---
        y_display = np.abs(y)
        self.waveform_widget.set_waveform(y_display, duration)
        self.waveform_widget.set_position(0)
        self.is_playing = False
        self.play_button.setText("PLUY")
        # --- Pyglet (toujours dans le thread principal !) ---
        if self.pyglet_player:
            print("[LOG] on_load_finished : suppression ancienne instance pyglet_player", flush=True)
            self.pyglet_player.pause()
            self.pyglet_player.delete()
        print("[LOG] Création d'un nouveau pyglet.media.Player", flush=True)
        self.pyglet_player = pyglet.media.Player()
        try:
            if temp_wav_path:
                print(f"[LOG] Chargement source pyglet depuis temp_wav_path={temp_wav_path}", flush=True)
                self.pyglet_source = pyglet.media.load(temp_wav_path, streaming=False)
            else:
                print(f"[LOG] Chargement source pyglet depuis original_file={original_file}", flush=True)
                self.pyglet_source = pyglet.media.load(original_file, streaming=False)
            self.pyglet_player.queue(self.pyglet_source)
            print("[LOG] Lancement automatique de la lecture (play)", flush=True)
            self.pyglet_player.play()  # Démarrer automatiquement la lecture
            self.is_playing = True
            self.play_button.setText("PAUSE")
            self.timer.start(100)
        except Exception as e:
            print(f"[LOG] Erreur lors du chargement ou du lancement pyglet : {e}", flush=True)
            self.info_label.setText(f"Erreur lecture (pyglet) : {e}")
            return
        # --- Infos UI ---
        if artiste and titre:
            self.info_label.setText(f"{artiste} - {titre}")
        else:
            self.info_label.setText(os.path.basename(self.current_file))
        if infos:
            self.info_label.setText(self.info_label.text() + f"\n{infos}")
        self.quality_label.setText(quality)

    def on_load_error(self, message):
        debug_log(f"on_load_error : {message}")
        self.info_label.setText(f"Erreur chargement : {message}")
        self.quality_label.setText("")
        self.waveform_widget.set_waveform(None, 0)
        self.waveform_widget.set_position(0)

    def audio_callback(self, outdata, frames, time, status):
        if self.audio_data is None:
            outdata.fill(0)
            return
        start = self.current_frame
        end = min(start + frames, len(self.audio_data))
        chunk = self.audio_data[start:end]
        if len(chunk) < frames:
            outdata[:len(chunk), 0] = chunk
            outdata[len(chunk):, 0] = 0
            self.stop()
        else:
            outdata[:, 0] = chunk
        self.current_frame += frames

    def play_audio(self, start_pos=0):
        if self.audio_data is None:
            return
        if self.stream is not None:
            self.stream.close()
        self.current_frame = int(start_pos * self.sr)
        self.stream = sd.OutputStream(
            samplerate=self.sr,
            channels=1,
            callback=self.audio_callback,
            finished_callback=self.stop
        )
        self.stream.start()
        self.is_playing = True
        self.play_button.setText("PAUSE")
        self.timer.start(100)

    def toggle_play(self):
        debug_log(f"toggle_play appelé, is_playing={self.is_playing}")
        print(f"[LOG] toggle_play appelé, is_playing={self.is_playing}", flush=True)
        if not self.current_file:
            print("[LOG] Aucun fichier chargé", flush=True)
            return
        if not self.is_playing:
            if self.pyglet_player:
                print("[LOG] pyglet_player.play() appelé", flush=True)
                self.pyglet_player.play()
            self.is_playing = True
            self.play_button.setText("PAUSE")
            self.timer.start(100)
        else:
            if self.pyglet_player:
                print("[LOG] pyglet_player.pause() appelé", flush=True)
                self.pyglet_player.pause()
            self.is_playing = False
            self.play_button.setText("PLUY")
            self.timer.stop()

    def stop(self):
        debug_log(f"stop() appelé")
        print(f"[LOG] stop() appelé", flush=True)
        if self.pyglet_player:
            self.pyglet_player.pause()
            self.pyglet_player.seek(0)
        self.is_playing = False
        self.play_button.setText("PLUY")
        self.waveform_widget.set_position(0)
        self.timer.stop()

    def finalize_seek(self, ratio):
        debug_log(f"finalize_seek appelé avec ratio={ratio:.3f}")
        print(f"[LOG] finalize_seek appelé avec ratio={ratio:.3f}", flush=True)
        if self.pyglet_player:
            seek_time = ratio * self.duration
            self.pyglet_player.seek(seek_time)
            self.waveform_widget.set_position(ratio)

    def update_position(self):
        debug_log(f"update_position appelé")
        if self.pyglet_player and self.is_playing:
            pos = self.pyglet_player.time
            if self.duration > 0:
                self.waveform_widget.set_position(pos / self.duration)
            if pos >= self.duration:
                self.stop()

    def extract_artist_title(self, file_name):
        try:
            import mutagen
            from mutagen.easyid3 import EasyID3
            audio = mutagen.File(file_name, easy=True)
            artiste = ""
            titre = ""
            if audio:
                artiste = audio.get('artist', [''])[0]
                titre = audio.get('title', [''])[0]
            return artiste, titre
        except Exception:
            return "", ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".mp3", ".wav", ".ogg", ".aiff")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith((".mp3", ".wav", ".ogg", ".aiff")):
                    self.load_file(file_path)
                    break

def main():
    debug_log("main() appelé")
    app = QApplication(sys.argv)
    window = SimpleAudioPlayer()
    window.show()
    # Gestion de l'ouverture directe de fichier (Ouvrir avec)
    if len(sys.argv) > 1:
        debug_log(f"Arguments reçus : {sys.argv}")
        file_to_open = sys.argv[1]
        if os.path.isfile(file_to_open):
            debug_log(f"Fichier trouvé : {file_to_open}")
            window.load_file(file_to_open)
        else:
            debug_log(f"Fichier non trouvé ou chemin invalide : {file_to_open}")
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 