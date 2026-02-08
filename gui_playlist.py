import json
import os
import random
from PyQt6.QtWidgets import QListWidgetItem, QInputDialog, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from audio_analysis import AdvancedAudioAnalyzer

class PlaylistMixin:
    def add_scene_to_playlist(self, index):
        if str(index) not in self.scenes:
            self.log(f"⚠️ Scène {index+1} vide, impossible d'ajouter à la playlist.")
            return
            
        duration = self.playlist_duration_spin.value()
        item = QListWidgetItem(f"Scène {index+1} ({duration}s)")
        item.setData(Qt.ItemDataRole.UserRole, index)
        item.setData(Qt.ItemDataRole.UserRole + 1, duration)
        self.playlist_list.addItem(item)

    def start_playlist(self):
        if self.playlist_list.count() == 0: return
        self.playlist_running = True
        self.playlist_index = -1
        self.last_played_index = -1
        self.btn_playlist_play.setStyleSheet("background-color: #00FF00; color: black;")
        self.next_playlist_item()

    def stop_playlist(self):
        self.playlist_running = False
        self.playlist_timer.stop()
        self.btn_playlist_play.setStyleSheet("")

    def next_playlist_item(self):
        if not self.playlist_running: return
        
        count = self.playlist_list.count()
        if count == 0:
            self.stop_playlist()
            return

        if self.playlist_shuffle_check.isChecked() and count > 1:
            new_index = random.randint(0, count - 1)
            while new_index == self.last_played_index:
                new_index = random.randint(0, count - 1)
            self.playlist_index = new_index
        else:
            self.playlist_index += 1
            if self.playlist_index >= count:
                if self.playlist_loop_check.isChecked():
                    self.playlist_index = 0
                else:
                    self.stop_playlist()
                    return
        
        self.playlist_list.setCurrentRow(self.playlist_index)
        item = self.playlist_list.item(self.playlist_index)
        
        self.last_played_index = self.playlist_index
        
        scene_idx = item.data(Qt.ItemDataRole.UserRole)
        duration = item.data(Qt.ItemDataRole.UserRole + 1)
        
        if self.playlist_beat_sync_check.isChecked():
            duration = (60.0 / self.detected_bpm) * 4 * self.playlist_bars_spin.value()
        
        transition_time = 0.0
        if self.playlist_crossfade_check.isChecked():
            transition_time = min(duration * 0.5, 2.0)
            
        self.trigger_scene(scene_idx, transition_duration=transition_time)
        self.playlist_timer.start(int(duration * 1000))

    def edit_playlist_item_duration(self, item):
        current_duration = item.data(Qt.ItemDataRole.UserRole + 1)
        val, ok = QInputDialog.getDouble(self, "Durée", "Durée de la scène (secondes):", current_duration, 0.1, 3600, 1)
        if ok:
            item.setData(Qt.ItemDataRole.UserRole + 1, val)
            scene_idx = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"Scène {scene_idx+1} ({val}s)")

    def export_playlist(self):
        if self.playlist_list.count() == 0:
            QMessageBox.warning(self, "Playlist vide", "Ajoutez des scènes à la playlist avant d'exporter.")
            return

        audio_path = self.audio_input.text()
        if not os.path.exists(audio_path):
            QMessageBox.critical(self, "Erreur", "Fichier audio introuvable pour l'analyse BPM.")
            return

        output_path, _ = QFileDialog.getSaveFileName(self, "Exporter Playlist", "", "Video Files (*.mp4)")
        if not output_path:
            return

        self.log("📊 Analyse du BPM pour l'export playlist...")
        try:
            analyzer = AdvancedAudioAnalyzer(audio_path)
            self.detected_bpm = analyzer.tempo
            self.log(f"BPM Détecté: {self.detected_bpm}")
        except Exception as e:
            self.log(f"Erreur analyse BPM: {e}. Utilisation de 120 BPM.")
            self.detected_bpm = 120.0

        macro_data = []
        current_time = 0.0
        
        float_keys = [
            'bloom', 'aberration', 'grain', 'glitch', 'vignette', 'scanline',
            'contrast', 'saturation', 'brightness', 'gamma', 'exposure', 'strobe',
            'light_leak', 'mirror', 'pixelate', 'posterize', 'solarize', 'hue_shift',
            'invert', 'sepia', 'thermal', 'edge', 'fisheye', 'twist', 'ripple', 'mirror_quad'
        ]

        for i in range(self.playlist_list.count()):
            item = self.playlist_list.item(i)
            scene_idx = item.data(Qt.ItemDataRole.UserRole)
            idx_str = str(scene_idx)
            
            if idx_str in self.scenes:
                scene_data = self.scenes[idx_str]
                
                duration = item.data(Qt.ItemDataRole.UserRole + 1)
                if self.playlist_beat_sync_check.isChecked():
                    bars = self.playlist_bars_spin.value()
                    duration = (60.0 / self.detected_bpm) * 4 * bars
                
                if 'style' in scene_data:
                    macro_data.append({'time': current_time, 'type': 'style', 'value': scene_data['style']})
                
                for key in float_keys:
                    if key in scene_data:
                        param_name = f"{key}_strength"
                        macro_data.append({'time': current_time, 'type': 'param', 'name': param_name, 'value': scene_data[key]})
                
                current_time += duration

        self.log(f"🚀 Lancement de l'export playlist ({current_time:.1f}s)")
        self._initiate_render(max_duration=current_time, macro_data=macro_data, output_override=output_path)

    def save_playlist(self):
        if self.playlist_list.count() == 0: return
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder Playlist", "", "JSON Files (*.json)")
        if path:
            playlist_data = []
            for i in range(self.playlist_list.count()):
                item = self.playlist_list.item(i)
                scene_idx = item.data(Qt.ItemDataRole.UserRole)
                duration = item.data(Qt.ItemDataRole.UserRole + 1)
                playlist_data.append({"scene_index": scene_idx, "duration": duration})
            
            try:
                with open(path, 'w') as f:
                    json.dump(playlist_data, f, indent=4)
                self.log(f"💾 Playlist sauvegardée: {os.path.basename(path)}")
            except Exception as e:
                self.log(f"❌ Erreur sauvegarde playlist: {e}")

    def load_playlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger Playlist", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    playlist_data = json.load(f)
                
                self.playlist_list.clear()
                for item_data in playlist_data:
                    self.add_scene_to_playlist(item_data["scene_index"])
                    last_item = self.playlist_list.item(self.playlist_list.count() - 1)
                    if last_item and "duration" in item_data:
                        last_item.setData(Qt.ItemDataRole.UserRole + 1, item_data["duration"])
                        last_item.setText(f"Scène {item_data['scene_index']+1} ({item_data['duration']}s)")
                
                self.log(f"📂 Playlist chargée: {os.path.basename(path)}")
            except Exception as e:
                self.log(f"❌ Erreur chargement playlist: {e}")
