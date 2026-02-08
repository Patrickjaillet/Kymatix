import pygame
import time
import numpy as np
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from gui_threads import AudioLoaderThread, AnalysisThread
from vst_manager import VSTManager
class AudioUpdateThread(QThread):
    """Thread dedicated to audio synchronization and feature extraction"""
    update_signal = pyqtSignal(float, object, object) # time, features, spectrum

    def __init__(self, analyzer, audio_loaded, playback_offset=0):
        super().__init__()
        self.analyzer = analyzer
        self.audio_loaded = audio_loaded
        self.playback_offset = playback_offset
        self.running = False
        self.paused = False
        self.start_time = 0
        
    def run(self):
        self.running = True
        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue
                
            current_time = 0.0
            if self.audio_loaded:
                try:
                    if pygame.mixer.get_init():
                        pos = pygame.mixer.music.get_pos()
                        if pos != -1:
                            current_time = (pos + self.playback_offset) / 1000.0
                except:
                    pass
            else:
                current_time = time.time() - self.start_time

            features = None
            spectrum = None
            if self.analyzer:
                # This is the heavy part we want off the main thread
                features = self.analyzer.get_features_at_time(current_time)
                spectrum = self.analyzer.get_spectrum_at_time(current_time)
            
            self.update_signal.emit(current_time, features, spectrum)
            time.sleep(0.016) # ~60 FPS

    def stop(self):
        self.running = False
        self.wait()

class AudioMixin:
    def init_audio(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception as e:
            self.log(f"⚠️ Pygame Mixer init failed: {e}")
        self.analyzer = None
        self.audio_loaded = False
        self.is_playing = False
        self.audio_thread = None
        self.playback_offset = 0
        self.audio_data = None
        self.sim_start_time = 0
        self.sim_pause_time = 0

    def on_audio_loaded_for_preview(self, data, path_for_playback):
        self.audio_data = data

        # Load the (potentially processed) audio into pygame for playback
        try:
            pygame.mixer.music.load(path_for_playback)
            self.audio_loaded = True
            self.log("🔊 Audio loaded for preview playback.")
        except Exception as e:
            self.log(f"❌ Could not load audio for preview: {e}")
            self.audio_loaded = False

        # Update waveform display
        if data is not None and data.ndim == 2:
            mono = np.mean(data, axis=0)
            self.waveform.set_data(mono)
        else:
            self.waveform.set_data(data)
            
        if self.timeline_widget:
            self.timeline_widget.set_audio_data(data)

        # Start analysis on the original audio file path
        self.log("📊 Starting full audio analysis for preview...")
        self.analysis_thread = AnalysisThread(self.audio_input.text(), self.audio_preset_combo.currentText())
        self.analysis_thread.log_signal.connect(self.log)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.start()

    def on_analysis_complete(self, analyzer):
        if analyzer:
            self.analyzer = analyzer
            self.preview_widget.set_analyzer(analyzer)
            self.seek_slider.setRange(0, int(self.analyzer.duration * 1000))
            
            tot_sec = int(self.analyzer.duration)
            self.lbl_time.setText(f"00:00 / {tot_sec//60:02d}:{tot_sec%60:02d}")
            
            self.log("✅ Analysis complete. Ready for preview.")
            
            self.btn_play.setEnabled(True)
            if not self.audio_loaded:
                self.log("⚠️ Audio playback disabled (Load failed), using simulated timing.")
        else:
            self.log("❌ Analysis failed. Switching to simulation mode.")
            class DummyAnalyzer:
                def __init__(self):
                    self.duration = 180.0
                    self.tempo = 120.0
                def get_features_at_time(self, t):
                    from audio_analysis import AdvancedAudioFeatures
                    return AdvancedAudioFeatures(intensity=0.5, beat_strength=0.5)
                def get_spectrum_at_time(self, t):
                    return np.zeros(100)
            
            self.analyzer = DummyAnalyzer()
            self.preview_widget.set_analyzer(self.analyzer)
            self.seek_slider.setRange(0, int(self.analyzer.duration * 1000))
            self.btn_play.setEnabled(True)
            self.audio_loaded = False

    def play_audio(self):
        if self.analyzer:
            try:
                if self.is_playing:
                    if self.audio_loaded:
                        pygame.mixer.music.stop()
                    if self.audio_thread:
                        self.audio_thread.stop()
                
                start_pos = self.seek_slider.value() / 1000.0
                self.playback_offset = start_pos * 1000.0
                
                if self.audio_loaded:
                    pygame.mixer.music.play(start=start_pos)
                else:
                    self.sim_start_time = time.time() - start_pos

                # Start Thread
                self.audio_thread = AudioUpdateThread(self.analyzer, self.audio_loaded, self.playback_offset)
                self.audio_thread.start_time = self.sim_start_time # For sim mode
                self.audio_thread.update_signal.connect(self.on_audio_update)
                self.audio_thread.start()

                self.is_playing = True
                self.btn_pause.setChecked(False)
                self.btn_pause.setText("❚❚ PAUSE")
                
                # Stop main UI timer to avoid conflict/double update
                if hasattr(self, 'vu_timer'): self.vu_timer.stop()
            except Exception as e:
                self.log(f"❌ Playback Error: {e}")

    def on_audio_update(self, current_time, features, spectrum):
        # Update UI elements
        val = int(current_time * 1000)
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(val)
        self.seek_slider.blockSignals(False)
        
        self.preview_widget.set_playback_time(current_time)
        
        # Push features to preview widget to avoid redundant calculation in paintGL
        if features:
            self.preview_widget.set_audio_features(features)
            if self.performance_window:
                self.performance_window.preview_widget.set_audio_features(features)
        
        if self.analyzer:
            tot_sec = int(self.analyzer.duration)
            cur_sec = int(current_time)
            self.lbl_time.setText(f"{cur_sec//60:02d}:{cur_sec%60:02d} / {tot_sec//60:02d}:{tot_sec%60:02d}")
        
        # Handle Loop
        if self.analyzer and current_time > self.analyzer.duration:
             if self.btn_loop.isChecked():
                 self.seek_audio(0)
             else:
                 self.stop_audio()
                 return

        # Timeline Effects
        if self.timeline_widget:
            effects = self.timeline_widget.get_active_effects(current_time)
            self.preview_widget.set_timeline_effects(effects)
            if self.performance_window:
                self.performance_window.preview_widget.set_timeline_effects(effects)

        # Update VU Meter & DMX
        if features:
            l_level = features.intensity
            r_level = features.intensity
            self.vu_meter.set_levels(l_level, r_level)
            if hasattr(self, 'vu_meter_left'):
                self.vu_meter_left.set_levels(l_level, r_level)
                
            # Goniometer
            if self.audio_data is not None and self.audio_data.ndim == 2:
                idx = int(current_time * 22050)
                if idx < self.audio_data.shape[1]:
                    chunk = self.audio_data[:, idx:idx+1024]
                    if chunk.shape[1] > 0:
                        self.goniometer.set_samples(chunk)
            
            # DMX
            if self.dmx_thread:
                for channel, feature_name in self.dmx_mapping.items():
                    if hasattr(features, feature_name):
                        val = getattr(features, feature_name)
                        if isinstance(val, (int, float)):
                            self.dmx_thread.set_channel(int(channel), val * 255)

    def pause_audio(self, checked):
        if not self.analyzer: return
        if self.is_playing:
            if self.audio_loaded:
                pygame.mixer.music.pause()
            
            if self.audio_thread:
                self.audio_thread.paused = True
                
            self.is_playing = False
            self.btn_pause.setText("▶ RESUME")
        else:
            if self.audio_loaded:
                if pygame.mixer.music.get_pos() > 0:
                    pygame.mixer.music.unpause()
            
            if self.audio_thread:
                self.audio_thread.paused = False
                if not self.audio_loaded:
                     start_pos = self.seek_slider.value() / 1000.0
                     self.audio_thread.start_time = time.time() - start_pos

            self.is_playing = True
            self.btn_pause.setText("❚❚ PAUSE")

    def stop_audio(self):
        if self.audio_loaded:
            pygame.mixer.music.stop()
        
        if self.audio_thread:
            self.audio_thread.stop()
            self.audio_thread = None
            
        self.is_playing = False
        self.seek_slider.setValue(0)
        self.playback_offset = 0
        self.preview_widget.set_playback_time(0)
        self.btn_pause.setChecked(False)
        self.btn_pause.setText("❚❚ PAUSE")
        
        total_duration_ms = self.analyzer.duration * 1000 if self.analyzer else 0
        tot_sec = int(total_duration_ms / 1000)
        self.lbl_time.setText(f"00:00 / {tot_sec//60:02d}:{tot_sec%60:02d}")
        
        # Restart idle timer
        if hasattr(self, 'vu_timer'): self.vu_timer.start(30)

    def seek_audio(self, position_ms):
        if self.analyzer:
            try:
                start_pos = position_ms / 1000.0
                self.playback_offset = position_ms
                
                if self.is_playing and self.audio_loaded:
                    pygame.mixer.music.play(start=start_pos)
                    
                    if self.audio_thread:
                        self.audio_thread.playback_offset = position_ms
                        if not self.audio_loaded:
                            self.audio_thread.start_time = time.time() - start_pos
                else:
                    self.preview_widget.set_playback_time(start_pos)
                    val = int(position_ms)
                    self.seek_slider.blockSignals(True)
                    self.seek_slider.setValue(val)
                    self.seek_slider.blockSignals(False)
            except Exception:
                pass
