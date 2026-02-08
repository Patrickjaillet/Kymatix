import os
import json
import librosa
import urllib.request
import cv2
import time
import numpy as np
import pyaudio # New import
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from video_exporter import AdvancedVideoExporter, RenderConfig
from audio_analysis import RealTimeAudioAnalyzer, AdvancedAudioFeatures # New import

CURRENT_VERSION = "1.0.0"
UPDATE_URL = "https://raw.githubusercontent.com/Patrick/MusicVideoGen/main/version.json"

class UpdateCheckerThread(QThread):
    update_available = pyqtSignal(str, str)
    
    def run(self):
        try:
            # Vérification silencieuse
            req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if data.get('version', '0.0.0') > CURRENT_VERSION:
                    self.update_available.emit(data['version'], data['url'])
        except Exception:
            pass

class AudioLoaderThread(QThread):
    """Thread pour charger l'audio pour la preview sans bloquer l'UI"""
    loaded = pyqtSignal(object, str) # data, path_for_playback
    
    def __init__(self, path, main_window=None):
        super().__init__()
        self.path = path
        self.mw = main_window
        
    def run(self):
        path_for_playback = self.path
        try:
            # Chargement en stéréo pour le goniomètre, SR moyen pour perf/qualité
            y, _ = librosa.load(self.path, sr=22050, mono=False)

            # Apply VST if enabled
            if self.mw and self.mw.vst_enable_check.isChecked():
                vst_path = self.mw.vst_manager.found_plugins.get(self.mw.vst_plugin_combo.currentText())
                if vst_path:
                    if self.mw.vst_manager.load_plugin(vst_path):
                        import soundfile as sf
                        y = self.mw.vst_manager.process_buffer(y, sr=22050, wet_dry_mix=self.mw.vst_mix_spin.value())
                        
                        # Save processed audio to a temp file for pygame to load
                        path_for_playback = "temp_vst_preview.wav"
                        sf.write(path_for_playback, y.T, 22050) # soundfile expects (samples, channels)

            self.loaded.emit(y, path_for_playback)
        except ImportError:
            if self.mw: self.mw.log("❌ VST/Audio processing requires 'soundfile' and 'librosa'. Please run 'pip install soundfile librosa'.")
            self.loaded.emit(None, self.path)
        except Exception as e:
            print(f"AudioLoaderThread Error: {e}")
            self.loaded.emit(None, self.path)

class AnalysisThread(QThread):
    """Thread pour l'analyse audio complète sans bloquer l'UI"""
    analysis_complete = pyqtSignal(object)
    log_signal = pyqtSignal(str)

    def __init__(self, audio_path, audio_preset):
        super().__init__()
        self.audio_path = audio_path
        self.audio_preset = audio_preset

    def run(self):
        try:
            from audio_analysis import AdvancedAudioAnalyzer
            analyzer = AdvancedAudioAnalyzer(self.audio_path, audio_preset=self.audio_preset, logger=self.log_signal.emit)
            self.analysis_complete.emit(analyzer)
        except Exception as e:
            self.log_signal.emit(f"❌ Analysis Error: {e}")
            self.analysis_complete.emit(None)

class DMXThread(QThread):
    """Thread dédié à l'envoi DMX (sACN) avec régulation de débit"""
    def __init__(self):
        super().__init__()
        self.running = False
        self.sender = None
        self.universe = 1
        self.data = [0] * 512
        self.lock = QMutex()
        self.fps = 30 # Taux de rafraîchissement DMX standard

    def run(self):
        try:
            import sacn
            self.sender = sacn.sACNsender()
            self.sender.start()
            self.sender.activate_output(self.universe)
            self.sender[self.universe].multicast = True
            
            self.running = True
            while self.running:
                with QMutexLocker(self.lock):
                    # Copie thread-safe des données
                    current_data = tuple(self.data)
                
                self.sender[self.universe].dmx_data = current_data
                time.sleep(1.0 / self.fps)

            self.sender.stop()
        except ImportError:
            print("❌ Module 'sacn' manquant. DMX désactivé.")
        except Exception as e:
            print(f"❌ Erreur DMX Thread: {e}")

    def set_channel(self, channel, value):
        """Met à jour le buffer DMX de manière thread-safe"""
        if 1 <= channel <= 512:
            with QMutexLocker(self.lock):
                self.data[channel-1] = int(max(0, min(255, value)))

    def stop(self):
        self.running = False
        self.wait()

class RenderThread(QThread):
    """Thread séparé pour ne pas bloquer l'interface"""
    progress_signal = pyqtSignal(int)
    merge_signal = pyqtSignal()
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, params, batch_files=None):
        super().__init__()
        self.params = params
        self.batch_files = batch_files
        self.is_cancelled = False

    def run(self):
        try:
            tasks = []
            if self.batch_files:
                tasks = self.batch_files
            else:
                tasks = [(self.params['audio'], self.params['output'])]
            
            total = len(tasks)
            
            for i, (audio_path, out_path) in enumerate(tasks):
                if self.is_cancelled: break
                
                if total > 1:
                    self.log_signal.emit(f"\n📦 [BATCH {i+1}/{total}] Traitement: {os.path.basename(audio_path)}")
                    
                    # Auto-détection titre/artiste basique pour le batch
                    filename = os.path.splitext(os.path.basename(audio_path))[0]
                    if " - " in filename:
                        parts = filename.split(" - ", 1)
                        artist = parts[0]
                        title = parts[1]
                    else:
                        artist = ""
                        title = filename
                else:
                    artist = self.params['artist']
                    title = self.params['title']

                # Création de la configuration
                config = RenderConfig(
                    audio_path=audio_path,
                    output_path=out_path,
                    width=self.params['width'],
                    height=self.params['height'],
                    fps=self.params['fps'],
                    auto_detect_style=self.params['auto_style'],
                    forced_style=self.params['style'],
                    save_json=self.params['save_json'],
                    song_title=title,
                    artist_name=artist,
                    bloom_strength=self.params.get('bloom', 0.5),
                    aberration_strength=self.params.get('aberration', 0.1),
                    grain_strength=self.params.get('grain', 0.05),
                    glitch_strength=self.params.get('glitch', 0.0),
                    vignette_strength=self.params.get('vignette', 0.0),
                    scanline_strength=self.params.get('scanline', 0.0),
                    contrast_strength=self.params.get('contrast', 1.0),
                    saturation_strength=self.params.get('saturation', 1.0),
                    brightness_strength=self.params.get('brightness', 0.0),
                    gamma_strength=self.params.get('gamma', 1.0),
                    exposure_strength=self.params.get('exposure', 1.0),
                    strobe_strength=self.params.get('strobe', 0.0),
                    light_leak_strength=self.params.get('light_leak', 0.0),
                    mirror_strength=self.params.get('mirror', 0.0),
                    pixelate_strength=self.params.get('pixelate', 0.0),
                    posterize_strength=self.params.get('posterize', 0.0),
                    solarize_strength=self.params.get('solarize', 0.0),
                    hue_shift_strength=self.params.get('hue_shift', 0.0),
                    invert_strength=self.params.get('invert', 0.0),
                    sepia_strength=self.params.get('sepia', 0.0),
                    thermal_strength=self.params.get('thermal', 0.0),
                    edge_strength=self.params.get('edge', 0.0),
                    fisheye_strength=self.params.get('fisheye', 0.0),
                    twist_strength=self.params.get('twist', 0.0),
                    ripple_strength=self.params.get('ripple', 0.0),
                    mirror_quad_strength=self.params.get('mirror_quad', 0.0),
                    dynamic_style=self.params.get('dynamic_style', False),
                    autopilot=self.params.get('autopilot', False),
                    autopilot_timer=self.params.get('autopilot_timer', 15),
                    autopilot_on_drop=self.params.get('autopilot_on_drop', False),
                    modulations=self.params.get('modulations', []),
                    text_effect=self.params.get('text_effect', "Scroll"),
                    srt_path=self.params.get('srt_path', None),
                    scroller_font=self.params.get('scroller_font', "Arial"),
                    scroller_color=self.params.get('scroller_color', (255, 255, 255)),
                    allowed_styles=self.params.get('allowed_styles', None),
                    spectrogram_bg_color=self.params.get('spectrogram_bg_color', (0, 0, 0, 128)),
                    spectrogram_position=self.params.get('spectrogram_position', "Bas"),
                    logo_path=self.params.get('logo_path', None),
                    spectrogram_enabled=self.params.get('spectrogram', False),
                    audio_preset=self.params.get('audio_preset', "Flat"),
                    pbo_enabled=self.params.get('pbo_enabled', True),
                    vr_mode=self.params.get('vr_mode', False),
                    user_texture_path=self.params.get('user_texture'),
                    distort_user_texture=self.params.get('distort_user_texture', False),
                    texture_blend_mode=self.params.get('texture_blend_mode', "Mix"),
                    codec=self.params.get('codec', "H.264 (MP4)"),
                    video_bitrate=self.params.get('bitrate', "High Quality (CRF 18)"),
                    export_format=self.params.get('export_format', "video"),
                    export_audio=self.params.get('export_audio', False),
                    ai_enabled=self.params.get('ai_enabled', False),
                    ai_model=self.params.get('ai_model', None),
                    ai_strength=self.params.get('ai_strength', 1.0),
                    vst_enabled=self.params.get('vst_enabled', False),
                    vst_model=self.params.get('vst_model', None),
                    vst_mix=self.params.get('vst_mix', 1.0)
                )
                
                # Création de l'exporteur dans le thread
                exporter = AdvancedVideoExporter(config, logger=self.log_signal.emit)
                
                if self.params.get('realtime', False):
                    exporter.visualize(
                        check_cancel=lambda: self.is_cancelled,
                        output_path=self.params.get('output') if self.params.get('output') else None,
                        input_device_index=self.params.get('input_device'),
                        merge_callback=self.merge_signal.emit
                    )
                else:
                    exporter.export(
                        preview_window=self.params['preview'],
                        progress_callback=lambda p: self.progress_signal.emit(int(p)),
                        check_cancel=lambda: self.is_cancelled,
                        merge_callback=self.merge_signal.emit,
                        max_duration=self.params.get('max_duration'),
                        macro_data=self.params.get('macro_data')
                    )
                
            self.finished_signal.emit()
        except Exception as e:
            import traceback
            self.error_signal.emit(str(e) + "\n" + traceback.format_exc())

    def cancel(self):
        self.is_cancelled = True

class VideoCaptureThread(QThread):
    """Thread dédié à la capture vidéo pour ne pas bloquer l'UI"""
    frame_ready = pyqtSignal(object) # Envoie un numpy array (l'image)

    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self.running = False
        self.cap = None

    def run(self):
        self.running = True
        self.cap = cv2.VideoCapture(self.source)
        
        fps = 30.0
        if self.cap.isOpened():
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        delay = 1.0 / fps

        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            # Gestion de la boucle (Loop) si fin de fichier
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()

            if ret:
                self.frame_ready.emit(frame)
            
            time.sleep(delay) # Respect du framerate pour ne pas surcharger le CPU

        if self.cap:
            self.cap.release()

    def stop(self):
        self.running = False
        self.wait()
