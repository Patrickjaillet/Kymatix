import json
import os
import time
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class SceneMixin:
    def trigger_scene(self, index, transition_duration=0.0):
        # Only push state if triggered manually, not by playlist automation
        if not getattr(self, 'playlist_running', False):
            self.push_state()
        idx_str = str(index)
        if idx_str in self.scenes:
            target_state = self.scenes[idx_str]
            
            if transition_duration > 0.0:
                self.transition_start_state = self.get_current_state()
                self.transition_target_state = target_state
                self.transition_duration = transition_duration
                self.transition_start_time = time.time()
                self.transition_timer.start(16) # ~60 FPS
                
                # Appliquer immédiatement les éléments non interpolables
                if 'style' in target_state: self.style_combo.setCurrentText(target_state['style'])
                if 'title' in target_state: self.title_input.setText(target_state['title'])
                if 'artist' in target_state: self.artist_input.setText(target_state['artist'])
                if 'scroller_font' in target_state: self.font_combo.setCurrentFont(QFont(target_state['scroller_font']))
                if 'scroller_color' in target_state: self.scroller_color = tuple(target_state['scroller_color'])
                if 'text_effect' in target_state: self.text_effect_combo.setCurrentText(target_state['text_effect'])
                if 'spectrogram' in target_state: self.spectrogram_check.setChecked(target_state['spectrogram'])
                if 'spectrogram_bg_color' in target_state: self.spectrogram_bg_color = tuple(target_state['spectrogram_bg_color'])
                if 'spectrogram_position' in target_state: self.spec_pos_combo.setCurrentText(target_state['spectrogram_position'])
                if 'dynamic_style' in target_state: self.dynamic_style_check.setChecked(target_state['dynamic_style'])
                if 'autopilot' in target_state: self.autopilot_check.setChecked(target_state['autopilot'])
                if 'vr_mode' in target_state: self.vr_check.setChecked(target_state['vr_mode'])
                
            else:
                self.apply_state(target_state)
            self.log(f"📂 Scène {index+1} chargée")
        else:
            self.scenes[idx_str] = self.get_current_state()
            self.save_scenes_to_disk()
            self.update_scene_buttons()
            self.log(f"💾 Scène {index+1} sauvegardée")

    def update_transition(self):
        elapsed = time.time() - self.transition_start_time
        progress = min(1.0, elapsed / self.transition_duration)
        
        float_keys = [
            'bloom', 'aberration', 'grain', 'glitch', 'vignette', 'scanline',
            'contrast', 'saturation', 'brightness', 'gamma', 'exposure', 'strobe',
            'light_leak', 'mirror', 'pixelate', 'posterize', 'solarize', 'hue_shift',
            'invert', 'sepia', 'thermal', 'edge', 'fisheye', 'twist', 'ripple', 'mirror_quad'
        ]
        
        for key in float_keys:
            start_val = self.transition_start_state.get(key, 0.0)
            end_val = self.transition_target_state.get(key, 0.0)
            current_val = start_val + (end_val - start_val) * progress
            
            widget_name = f"{key}_spin"
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                widget.blockSignals(True)
                widget.setValue(current_val)
                widget.blockSignals(False)
        
        self.update_preview_params()
        
        if progress >= 1.0:
            self.transition_timer.stop()

    def show_scene_context_menu(self, pos, btn):
        index = btn.property("scene_index")
        idx_str = str(index)
        menu = QMenu(self)
        
        if idx_str in self.scenes:
            action_load = menu.addAction("Charger")
            action_update = menu.addAction("Mettre à jour (Écraser)")
            action_clear = menu.addAction("Effacer")
            
            action = menu.exec(btn.mapToGlobal(pos))
            if action == action_load:
                self.trigger_scene(index)
            elif action == action_update:
                self.scenes[idx_str] = self.get_current_state()
                self.save_scenes_to_disk()
                self.log(f"💾 Scène {index+1} mise à jour")
            elif action == action_clear:
                del self.scenes[idx_str]
                self.save_scenes_to_disk()
                self.update_scene_buttons()
                self.log(f"🗑️ Scène {index+1} effacée")
        else:
            action_save = menu.addAction("Sauvegarder")
            action = menu.exec(btn.mapToGlobal(pos))
            if action == action_save:
                self.trigger_scene(index)

    def save_scenes_to_disk(self):
        try:
            with open("scenes.json", 'w') as f:
                json.dump(self.scenes, f, indent=4)
        except Exception as e:
            self.log(f"Erreur sauvegarde scènes: {e}")

    def load_scenes(self):
        if os.path.exists("scenes.json"):
            try:
                with open("scenes.json", 'r') as f:
                    self.scenes = json.load(f)
                self.update_scene_buttons()
            except Exception:
                pass

    def update_scene_buttons(self):
        for i in range(8):
            btn = getattr(self, f"btn_scene_{i}", None)
            if btn:
                if str(i) in self.scenes:
                    btn.setStyleSheet("background-color: #00E5FF; color: #000; font-weight: bold;")
                    btn.setToolTip(f"Scène {i+1} (Chargée)")
                else:
                    btn.setStyleSheet("")
                    btn.setToolTip(f"Scène {i+1} (Vide - Cliquer pour sauvegarder)")
