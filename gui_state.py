import os
import json
import random
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QColorDialog
from PyQt6.QtGui import QFont, QColor

class StateMixin:
    def init_undo_redo(self):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50
        self.is_undoing = False

    def push_state(self):
        """Captures the current state and pushes it to the undo stack."""
        if getattr(self, 'is_undoing', False): return
        
        state = self.get_current_state()
        if not hasattr(self, 'undo_stack'): self.undo_stack = []
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        if hasattr(self, 'redo_stack'): self.redo_stack.clear()
        self.update_undo_redo_actions()

    def undo(self):
        """Reverts to the previous state."""
        if not hasattr(self, 'undo_stack') or not self.undo_stack: return
        
        self.is_undoing = True
        current_state = self.get_current_state()
        self.redo_stack.append(current_state)
        
        prev_state = self.undo_stack.pop()
        self.apply_state(prev_state)
        
        self.is_undoing = False
        self.update_undo_redo_actions()
        if hasattr(self, 'log'): self.log("↩️ Undo")

    def redo(self):
        """Re-applies a reverted state."""
        if not hasattr(self, 'redo_stack') or not self.redo_stack: return
        
        self.is_undoing = True
        current_state = self.get_current_state()
        self.undo_stack.append(current_state)
        
        next_state = self.redo_stack.pop()
        self.apply_state(next_state)
        
        self.is_undoing = False
        self.update_undo_redo_actions()
        if hasattr(self, 'log'): self.log("↪️ Redo")

    def update_undo_redo_actions(self):
        if hasattr(self, 'action_undo'):
            count = len(self.undo_stack) if hasattr(self, 'undo_stack') else 0
            self.action_undo.setEnabled(count > 0)
            self.action_undo.setText(f"{self.tr('action_undo')} ({count})")
        if hasattr(self, 'action_redo'):
            count = len(self.redo_stack) if hasattr(self, 'redo_stack') else 0
            self.action_redo.setEnabled(count > 0)
            self.action_redo.setText(f"{self.tr('action_redo')} ({count})")

    def _init_presets(self):
        self.presets_file = "presets.json"
        self.presets = {
            "Full HD (1080p 60fps)": {"width": 1920, "height": 1080, "fps": 60, "style": "Auto-détection"},
            "4K Ultra HD (2160p 60fps)": {"width": 3840, "height": 2160, "fps": 60, "style": "Auto-détection"},
            "Instagram/TikTok (1080x1920 30fps)": {"width": 1080, "height": 1920, "fps": 30, "style": "Auto-détection"},
            "Retro (640x480 24fps)": {"width": 640, "height": 480, "fps": 24, "style": "vaporwave"}
        }
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    saved = json.load(f)
                    self.presets.update(saved)
            except Exception as e:
                print(f"Erreur chargement presets: {e}")

    def update_preset_combo(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem(self.tr("preset_dialog_select"))
        self.preset_combo.addItems(list(self.presets.keys()))
        self.preset_combo.blockSignals(False)

    def load_preset(self, name):
        self.push_state()
        if name in self.presets:
            p = self.presets[name]
            self.width_spin.setValue(p.get("width", 1920))
            self.height_spin.setValue(p.get("height", 1080))
            self.fps_spin.setValue(p.get("fps", 60))
            style = p.get("style", "Auto-détection")
            index = self.style_combo.findText(style)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)

    def save_preset(self):
        name, ok = QInputDialog.getText(self, self.tr("preset_dialog_save_title"), self.tr("preset_dialog_save_label"))
        if ok and name:
            self.presets[name] = {
                "width": self.width_spin.value(),
                "height": self.height_spin.value(),
                "fps": self.fps_spin.value(),
                "style": self.style_combo.currentText()
            }
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=4)
            self.update_preset_combo()
            self.preset_combo.setCurrentText(name)

    def save_layout(self):
        self.save_ui_state(force_layout=True)
        if hasattr(self, 'log'):
            self.log("💾 Disposition des fenêtres sauvegardée.")

    def save_ui_state(self, force_layout=False):
        settings = {}
        if os.path.exists("user_settings.json"):
            try:
                with open("user_settings.json", 'r') as f:
                    settings = json.load(f)
            except Exception:
                pass
        
        def get_expanded_titles(groups):
            return [g.title() for g in groups if g.isChecked()]

        settings['expanded_general'] = get_expanded_titles(self.general_groups)
        settings['expanded_fx'] = get_expanded_titles(self.fx_groups)
        settings['expanded_overlay'] = get_expanded_titles(self.overlay_groups)
        settings['language'] = self.current_lang
        
        if hasattr(self, 'action_lock_layout'):
            settings['lock_layout'] = self.action_lock_layout.isChecked()
        
        if hasattr(self, 'action_auto_save_layout'):
            settings['auto_save_layout'] = self.action_auto_save_layout.isChecked()
        
        # Sauvegarde des modules repliables (BaseModule)
        collapsed_modules = []
        from gui_modules.base import BaseModule
        for widget in self.findChildren(BaseModule):
            if widget.collapsible and widget.is_collapsed:
                collapsed_modules.append(widget.__class__.__name__)
        settings['collapsed_modules'] = collapsed_modules
        settings['custom_themes'] = getattr(self, 'custom_themes', {})
        settings['workspaces'] = getattr(self, 'workspaces', {})
        
        # Sauvegarde des géométries des fenêtres (Seulement si forcé ou auto-save activé)
        should_save_layout = force_layout
        if hasattr(self, 'action_auto_save_layout') and self.action_auto_save_layout.isChecked():
            should_save_layout = True
            
        if should_save_layout:
            settings['geometry_main'] = self.saveGeometry().toHex().data().decode()
            settings['state_main'] = self.saveState().toHex().data().decode()
            
            if self.performance_window:
                settings['geometry_perf'] = self.performance_window.saveGeometry().toHex().data().decode()
                settings['visible_perf'] = self.performance_window.isVisible()
            else:
                settings['visible_perf'] = False
                
            if self.sequencer_window:
                settings['geometry_seq'] = self.sequencer_window.saveGeometry().toHex().data().decode()
                settings['visible_seq'] = self.sequencer_window.isVisible()
            else:
                settings['visible_seq'] = False
                
            if self.connectivity_window:
                settings['geometry_conn'] = self.connectivity_window.saveGeometry().toHex().data().decode()
                settings['visible_conn'] = self.connectivity_window.isVisible()
            else:
                settings['visible_conn'] = False
                
            if self.shader_editor_window:
                settings['geometry_editor'] = self.shader_editor_window.saveGeometry().toHex().data().decode()
                settings['visible_editor'] = self.shader_editor_window.isVisible()
            else:
                settings['visible_editor'] = False
                
            if self.midi_debug_window:
                settings['geometry_midi'] = self.midi_debug_window.saveGeometry().toHex().data().decode()
                settings['visible_midi'] = self.midi_debug_window.isVisible()
            else:
                settings['visible_midi'] = False

        try:
            with open("user_settings.json", 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception:
            pass

    def save_defaults(self):
        collapsed_modules = []
        from gui_modules.base import BaseModule
        for widget in self.findChildren(BaseModule):
            if widget.collapsible and widget.is_collapsed:
                collapsed_modules.append(widget.__class__.__name__)

        settings = {
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'fps': self.fps_spin.value(),
            'style': self.style_combo.currentText(),
            'bloom': self.bloom_spin.value(),
            'aberration': self.aberration_spin.value(),
            'grain': self.grain_spin.value(),
            'glitch': self.glitch_spin.value(),
            'vignette': self.vignette_spin.value(),
            'scanline': self.scanline_spin.value(),
            'contrast': self.contrast_spin.value(),
            'saturation': self.saturation_spin.value(),
            'brightness': self.brightness_spin.value(),
            'gamma': self.gamma_spin.value(),
            'exposure': self.exposure_spin.value(),
            'strobe': self.strobe_spin.value(),
            'light_leak': self.light_leak_spin.value(),
            'mirror': self.mirror_spin.value(),
            'dynamic_style': self.dynamic_style_check.isChecked(),
            'autopilot': self.autopilot_check.isChecked(),
            'autopilot_timer': self.autopilot_timer_spin.value(),
            'autopilot_on_drop': self.autopilot_drop_check.isChecked(),
            'scroller_font': self.font_combo.currentFont().family(),
            'scroller_color': self.scroller_color,
            'text_effect': self.text_effect_combo.currentText(),
            'audio_preset': self.audio_preset_combo.currentText(),
            'favorites': self.favorite_styles,
            'spectrogram': self.spectrogram_check.isChecked(),
            'logo_path': self.logo_input.text(),
            'spectrogram_bg_color': self.spectrogram_bg_color,
            'spectrogram_position': self.spec_pos_combo.currentText(),
            'quick_presets': self.quick_presets_map,
            'midi_mapping': self.midi_mapping,
            'osc_mapping': self.osc_mapping,
            'controller_mapping': getattr(self, 'controller_mapping', {}),
            'invert_y_axis': getattr(self, 'invert_y_axis', False),
            'controller_deadzone': getattr(self, 'controller_deadzone', 0.1),
            'controller_axis_calibration': getattr(self, 'controller_axis_calibration', {}),
            'controller_button_hold': getattr(self, 'controller_button_hold', False),
            'playlist_beat_sync': self.playlist_beat_sync_check.isChecked(),
            'playlist_bars': self.playlist_bars_spin.value(),
            'modulations': self.modulations,
            'particle_gravity': self.particle_gravity_spin.value(),
            'particle_life': self.particle_life_spin.value(),
            'particle_turbulence': self.particle_turb_spin.value(),
            'particle_color': self.particle_color,
            'particle_mode': self.particle_mode_combo.currentText(),
            'particle_size': self.particle_size_spin.value(),
            'vr_mode': self.vr_check.isChecked(),
            'dmx_mapping': {str(k): v for k, v in self.dmx_mapping.items()},
            'randomize_exclusions': self.randomize_exclusions,
            'distort_user_texture': self.distort_texture_check.isChecked(),
            'model_wireframe': self.preview_widget.model_wireframe,
            'texture_blend_mode': self.texture_blend_combo.currentText(),
            'collapsed_modules': collapsed_modules,
            'module_border_color': self.module_border_color,
            'ui_theme': getattr(self, 'ui_theme', 'Dark'),
            'custom_themes': getattr(self, 'custom_themes', {})
        }
        try:
            with open("user_settings.json", 'w') as f:
                json.dump(settings, f, indent=4)
            QMessageBox.information(self, self.tr("save_defaults_success_title"), self.tr("save_defaults_success_text"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("save_defaults_error_title"), self.tr("save_defaults_error_text", e=e))

    def load_defaults(self):
        if os.path.exists("user_settings.json"):
            try:
                with open("user_settings.json", 'r') as f:
                    settings = json.load(f)
                    self.width_spin.setValue(settings.get('width', 1920))
                    self.height_spin.setValue(settings.get('height', 1080))
                    self.fps_spin.setValue(settings.get('fps', 60))
                    self.bloom_spin.setValue(settings.get('bloom', 0.5))
                    self.aberration_spin.setValue(settings.get('aberration', 0.1))
                    self.grain_spin.setValue(settings.get('grain', 0.05))
                    self.glitch_spin.setValue(settings.get('glitch', 0.0))
                    self.vignette_spin.setValue(settings.get('vignette', 0.0))
                    self.scanline_spin.setValue(settings.get('scanline', 0.0))
                    self.contrast_spin.setValue(settings.get('contrast', 1.0))
                    self.saturation_spin.setValue(settings.get('saturation', 1.0))
                    self.brightness_spin.setValue(settings.get('brightness', 0.0))
                    self.gamma_spin.setValue(settings.get('gamma', 1.0))
                    self.exposure_spin.setValue(settings.get('exposure', 1.0))
                    self.strobe_spin.setValue(settings.get('strobe', 0.0))
                    self.light_leak_spin.setValue(settings.get('light_leak', 0.0))
                    self.mirror_spin.setValue(settings.get('mirror', 0.0))
                    self.rgb_split_spin.setValue(settings.get('rgb_split', 0.0))
                    self.bleach_spin.setValue(settings.get('bleach', 0.0))
                    self.vhs_spin.setValue(settings.get('vhs', 0.0))
                    self.neon_spin.setValue(settings.get('neon', 0.0))
                    self.cartoon_spin.setValue(settings.get('cartoon', 0.0))
                    self.sketch_spin.setValue(settings.get('sketch', 0.0))
                    self.vibrate_spin.setValue(settings.get('vibrate', 0.0))
                    self.drunk_spin.setValue(settings.get('drunk', 0.0))
                    self.pinch_spin.setValue(settings.get('pinch', 0.0))
                    self.zoom_blur_spin.setValue(settings.get('zoom_blur', 0.0))
                    self.aura_spin.setValue(settings.get('aura', 0.0))
                    self.psycho_spin.setValue(settings.get('psycho', 0.0))
                    self.feedback_spin.setValue(settings.get('feedback', 0.0))
                    self.dynamic_style_check.setChecked(settings.get('dynamic_style', False))
                    self.autopilot_check.setChecked(settings.get('autopilot', False))
                    self.autopilot_timer_spin.setValue(settings.get('autopilot_timer', 15))
                    self.autopilot_drop_check.setChecked(settings.get('autopilot_on_drop', False))
                    self.style_combo.setCurrentText(settings.get('style', 'Auto-détection'))
                    self.font_combo.setCurrentFont(QFont(settings.get('scroller_font', 'Arial')))
                    self.scroller_color = tuple(settings.get('scroller_color', [255, 255, 255]))
                    self.text_effect_combo.setCurrentText(settings.get('text_effect', 'Scroll'))
                    self.audio_preset_combo.setCurrentText(settings.get('audio_preset', 'Flat'))
                    self.spectrogram_check.setChecked(settings.get('spectrogram', False))
                    self.logo_input.setText(settings.get('logo_path', ''))
                    self.spectrogram_bg_color = tuple(settings.get('spectrogram_bg_color', [0, 0, 0, 128]))
                    self.spec_pos_combo.setCurrentText(settings.get('spectrogram_position', 'Bas'))
                    self.favorite_styles = settings.get('favorites', self.available_styles)
                    
                    self.quick_presets_map = settings.get('quick_presets', self.quick_presets_map)
                    self.update_quick_presets_tooltips()
                    self.midi_mapping = settings.get('midi_mapping', {})
                    self.osc_mapping = settings.get('osc_mapping', {})
                    self.controller_mapping = settings.get('controller_mapping', {})
                    self.invert_y_axis = settings.get('invert_y_axis', False)
                    self.controller_deadzone = settings.get('controller_deadzone', 0.1)
                    self.controller_axis_calibration = settings.get('controller_axis_calibration', {})
                    self.controller_button_hold = settings.get('controller_button_hold', False)
                    if hasattr(self, 'action_invert_y'):
                        self.action_invert_y.setChecked(self.invert_y_axis)
                    if hasattr(self, 'action_button_hold'):
                        self.action_button_hold.setChecked(self.controller_button_hold)
                    
                    wireframe = settings.get('model_wireframe', False)
                    self.preview_widget.model_wireframe = wireframe
                    if hasattr(self, 'action_wireframe'):
                        self.action_wireframe.setChecked(wireframe)

                    self.playlist_beat_sync_check.setChecked(settings.get('playlist_beat_sync', False))
                    self.playlist_bars_spin.setValue(settings.get('playlist_bars', 4))
                    self.particle_gravity_spin.setValue(settings.get('particle_gravity', 0.5))
                    self.particle_life_spin.setValue(settings.get('particle_life', 3.0))
                    self.particle_turb_spin.setValue(settings.get('particle_turbulence', 1.0))
                    self.particle_color = tuple(settings.get('particle_color', [0.2, 0.5, 1.0]))
                    self.particle_mode_combo.setCurrentText(settings.get('particle_mode', 'Rain'))
                    self.particle_size_spin.setValue(settings.get('particle_size', 2.0))
                    c = QColor.fromRgbF(*self.particle_color)
                    self.btn_particle_color.setStyleSheet(f"background-color: {c.name()}; color: {'black' if c.lightness() > 128 else 'white'}; font-weight: bold;")
                    self.vr_check.setChecked(settings.get('vr_mode', False))
                    
                    dmx_map = settings.get('dmx_mapping', {})
                    if dmx_map:
                        self.dmx_mapping = {int(k): v for k, v in dmx_map.items()}

                    self.randomize_exclusions = settings.get('randomize_exclusions', ['glitch_spin', 'strobe_spin'])
                    self.distort_texture_check.setChecked(settings.get('distort_user_texture', False))
                    self.texture_blend_combo.setCurrentText(settings.get('texture_blend_mode', 'Mix'))
                    self.vst_enable_check.setChecked(settings.get('vst_enabled', False))
                    self.vst_plugin_combo.setCurrentText(settings.get('vst_model', ''))
                    self.vst_mix_spin.setValue(settings.get('vst_mix', 1.0))
                    self.ai_enable_check.setChecked(settings.get('ai_enabled', False))
                    self.ai_model_combo.setCurrentText(settings.get('ai_model', ''))
                    self.ai_strength_spin.setValue(settings.get('ai_strength', 1.0))
                    
                    self.module_border_color = settings.get('module_border_color', '#333')
                    self.update_module_theme()
                    
                    self.ui_theme = settings.get('ui_theme', 'Dark')
                    if self.ui_theme == "Neon":
                        self.apply_neon_theme()
                        
                    self.custom_themes = settings.get('custom_themes', {})
                    
                    self.workspaces = settings.get('workspaces', {})
                    
                    # Restauration des fenêtres
                    if 'geometry_main' in settings:
                        self.restoreGeometry(bytes.fromhex(settings['geometry_main']))
                    if 'state_main' in settings:
                        self.restoreState(bytes.fromhex(settings['state_main']))
                        
                    if settings.get('visible_perf', False):
                        self.toggle_performance_view()
                        if self.performance_window and 'geometry_perf' in settings:
                            self.performance_window.restoreGeometry(bytes.fromhex(settings['geometry_perf']))
                            
                    if settings.get('visible_seq', False):
                        self.toggle_sequencer_window()
                        if self.sequencer_window and 'geometry_seq' in settings:
                            self.sequencer_window.restoreGeometry(bytes.fromhex(settings['geometry_seq']))
                            
                    if settings.get('visible_conn', False):
                        self.toggle_connectivity_window()
                        if self.connectivity_window and 'geometry_conn' in settings:
                            self.connectivity_window.restoreGeometry(bytes.fromhex(settings['geometry_conn']))
                            
                    if settings.get('visible_editor', False):
                        self.toggle_shader_editor()
                        if self.shader_editor_window and 'geometry_editor' in settings:
                            self.shader_editor_window.restoreGeometry(bytes.fromhex(settings['geometry_editor']))
                            
                    if settings.get('visible_midi', False):
                        self.toggle_midi_monitor()
                        if self.midi_debug_window and 'geometry_midi' in settings:
                            self.midi_debug_window.restoreGeometry(bytes.fromhex(settings['geometry_midi']))

                    collapsed_modules = settings.get('collapsed_modules', [])
                    from gui_modules.base import BaseModule
                    for widget in self.findChildren(BaseModule):
                        if widget.collapsible:
                            # Check both class name (robust) and title (legacy support)
                            is_collapsed = (widget.__class__.__name__ in collapsed_modules) or (widget.title() in collapsed_modules)
                            widget.set_collapsed(is_collapsed, animate=False)

                    self.modulations = settings.get('modulations', [])
                    if hasattr(self, 'mod_rows'):
                        for i, mod in enumerate(self.modulations):
                            if i < len(self.mod_rows):
                                src, tgt, amt = self.mod_rows[i]
                                src.setCurrentText(mod['source'])
                                tgt.setCurrentText(mod['target'])
                                amt.setValue(mod['amount'])
                    
                    self.current_lang = settings.get('language', 'fr')
                    self.lang_combo.setCurrentIndex(self.lang_combo.findData(self.current_lang))

                    if hasattr(self, 'action_lock_layout'):
                        locked = settings.get('lock_layout', False)
                        self.action_lock_layout.setChecked(locked)
                        self.toggle_lock_docks(locked)

                    if hasattr(self, 'action_auto_save_layout'):
                        self.action_auto_save_layout.setChecked(settings.get('auto_save_layout', True))

                    def restore_groups(groups, key):
                        if key not in settings: return
                        expanded = settings[key]
                        if isinstance(expanded, str): expanded = [expanded]
                        for g in groups:
                            g.setChecked(g.title() in expanded)

                    restore_groups(self.general_groups, 'expanded_general')
                    restore_groups(self.fx_groups, 'expanded_fx')
                    restore_groups(self.overlay_groups, 'expanded_overlay')
            except Exception:
                pass

    def get_current_state(self):
        return {
            'style': self.style_combo.currentText(),
            'bloom': self.bloom_spin.value(),
            'aberration': self.aberration_spin.value(),
            'grain': self.grain_spin.value(),
            'glitch': self.glitch_spin.value(),
            'vignette': self.vignette_spin.value(),
            'scanline': self.scanline_spin.value(),
            'contrast': self.contrast_spin.value(),
            'saturation': self.saturation_spin.value(),
            'brightness': self.brightness_spin.value(),
            'gamma': self.gamma_spin.value(),
            'exposure': self.exposure_spin.value(),
            'strobe': self.strobe_spin.value(),
            'light_leak': self.light_leak_spin.value(),
            'mirror': self.mirror_spin.value(),
            'pixelate': self.pixelate_spin.value(),
            'posterize': self.posterize_spin.value(),
            'solarize': self.solarize_spin.value(),
            'hue_shift': self.hue_shift_spin.value(),
            'invert': self.invert_spin.value(),
            'sepia': self.sepia_spin.value(),
            'thermal': self.thermal_spin.value(),
            'edge': self.edge_spin.value(),
            'fisheye': self.fisheye_spin.value(),
            'twist': self.twist_spin.value(),
            'ripple': self.ripple_spin.value(),
            'mirror_quad': self.mirror_quad_spin.value(),
            'rgb_split': self.rgb_split_spin.value(),
            'bleach': self.bleach_spin.value(),
            'vhs': self.vhs_spin.value(),
            'neon': self.neon_spin.value(),
            'cartoon': self.cartoon_spin.value(),
            'sketch': self.sketch_spin.value(),
            'vibrate': self.vibrate_spin.value(),
            'drunk': self.drunk_spin.value(),
            'pinch': self.pinch_spin.value(),
            'zoom_blur': self.zoom_blur_spin.value(),
            'aura': self.aura_spin.value(),
            'psycho': self.psycho_spin.value(),
            'feedback': self.feedback_spin.value(),
            'vst_enabled': self.vst_enable_check.isChecked(),
            'vst_model': self.vst_plugin_combo.currentText(),
            'vst_mix': self.vst_mix_spin.value(),
            'particle_life': self.particle_life_spin.value(),
            'particle_turbulence': self.particle_turb_spin.value(),
            'particle_mode': self.particle_mode_combo.currentText(),
            'particle_size': self.particle_size_spin.value(),
            'dynamic_style': self.dynamic_style_check.isChecked(),
            'autopilot': self.autopilot_check.isChecked(),
            'title': self.title_input.text(),
            'artist': self.artist_input.text(),
            'scroller_font': self.font_combo.currentFont().family(),
            'scroller_color': self.scroller_color,
            'text_effect': self.text_effect_combo.currentText(),
            'spectrogram': self.spectrogram_check.isChecked(),
            'spectrogram_bg_color': self.spectrogram_bg_color,
            'spectrogram_position': self.spec_pos_combo.currentText(),
            'vr_mode': self.vr_check.isChecked(),
            'distort_user_texture': self.distort_texture_check.isChecked(),
            'texture_blend_mode': self.texture_blend_combo.currentText()
        }

    def apply_state(self, state):
        if 'style' in state: self.style_combo.setCurrentText(state['style'])
        if 'bloom' in state: self.bloom_spin.setValue(state['bloom'])
        if 'aberration' in state: self.aberration_spin.setValue(state['aberration'])
        if 'grain' in state: self.grain_spin.setValue(state['grain'])
        if 'glitch' in state: self.glitch_spin.setValue(state['glitch'])
        if 'vignette' in state: self.vignette_spin.setValue(state['vignette'])
        if 'scanline' in state: self.scanline_spin.setValue(state['scanline'])
        if 'contrast' in state: self.contrast_spin.setValue(state['contrast'])
        if 'saturation' in state: self.saturation_spin.setValue(state['saturation'])
        if 'brightness' in state: self.brightness_spin.setValue(state['brightness'])
        if 'gamma' in state: self.gamma_spin.setValue(state['gamma'])
        if 'exposure' in state: self.exposure_spin.setValue(state['exposure'])
        if 'strobe' in state: self.strobe_spin.setValue(state['strobe'])
        if 'light_leak' in state: self.light_leak_spin.setValue(state['light_leak'])
        if 'mirror' in state: self.mirror_spin.setValue(state['mirror'])
        if 'pixelate' in state: self.pixelate_spin.setValue(state['pixelate'])
        if 'posterize' in state: self.posterize_spin.setValue(state['posterize'])
        if 'solarize' in state: self.solarize_spin.setValue(state['solarize'])
        if 'hue_shift' in state: self.hue_shift_spin.setValue(state['hue_shift'])
        if 'invert' in state: self.invert_spin.setValue(state['invert'])
        if 'sepia' in state: self.sepia_spin.setValue(state['sepia'])
        if 'thermal' in state: self.thermal_spin.setValue(state['thermal'])
        if 'edge' in state: self.edge_spin.setValue(state['edge'])
        if 'fisheye' in state: self.fisheye_spin.setValue(state['fisheye'])
        if 'twist' in state: self.twist_spin.setValue(state['twist'])
        if 'ripple' in state: self.ripple_spin.setValue(state['ripple'])
        if 'mirror_quad' in state: self.mirror_quad_spin.setValue(state['mirror_quad'])
        if 'rgb_split' in state: self.rgb_split_spin.setValue(state['rgb_split'])
        if 'bleach' in state: self.bleach_spin.setValue(state['bleach'])
        if 'vhs' in state: self.vhs_spin.setValue(state['vhs'])
        if 'neon' in state: self.neon_spin.setValue(state['neon'])
        if 'cartoon' in state: self.cartoon_spin.setValue(state['cartoon'])
        if 'sketch' in state: self.sketch_spin.setValue(state['sketch'])
        if 'vibrate' in state: self.vibrate_spin.setValue(state['vibrate'])
        if 'drunk' in state: self.drunk_spin.setValue(state['drunk'])
        if 'pinch' in state: self.pinch_spin.setValue(state['pinch'])
        if 'zoom_blur' in state: self.zoom_blur_spin.setValue(state['zoom_blur'])
        if 'aura' in state: self.aura_spin.setValue(state['aura'])
        if 'psycho' in state: self.psycho_spin.setValue(state['psycho'])
        if 'feedback' in state: self.feedback_spin.setValue(state['feedback'])
        if 'vst_enabled' in state: self.vst_enable_check.setChecked(state['vst_enabled'])
        if 'vst_model' in state: self.vst_plugin_combo.setCurrentText(state['vst_model'])
        if 'vst_mix' in state: self.vst_mix_spin.setValue(state['vst_mix'])
        if 'particle_life' in state: self.particle_life_spin.setValue(state['particle_life'])
        if 'particle_turbulence' in state: self.particle_turb_spin.setValue(state['particle_turbulence'])
        if 'particle_mode' in state: self.particle_mode_combo.setCurrentText(state['particle_mode'])
        if 'particle_size' in state: self.particle_size_spin.setValue(state['particle_size'])
        if 'dynamic_style' in state: self.dynamic_style_check.setChecked(state['dynamic_style'])
        if 'autopilot' in state: self.autopilot_check.setChecked(state['autopilot'])
        if 'title' in state: self.title_input.setText(state['title'])
        if 'artist' in state: self.artist_input.setText(state['artist'])
        if 'scroller_font' in state: self.font_combo.setCurrentFont(QFont(state['scroller_font']))
        if 'scroller_color' in state: self.scroller_color = tuple(state['scroller_color'])
        if 'text_effect' in state: self.text_effect_combo.setCurrentText(state['text_effect'])
        if 'spectrogram' in state: self.spectrogram_check.setChecked(state['spectrogram'])
        if 'spectrogram_bg_color' in state: self.spectrogram_bg_color = tuple(state['spectrogram_bg_color'])
        if 'spectrogram_position' in state: self.spec_pos_combo.setCurrentText(state['spectrogram_position'])
        if 'vr_mode' in state: self.vr_check.setChecked(state['vr_mode'])
        if 'distort_user_texture' in state: self.distort_texture_check.setChecked(state['distort_user_texture'])
        if 'texture_blend_mode' in state: self.texture_blend_combo.setCurrentText(state['texture_blend_mode'])
        
        if 'modulations' in state:
            self.modulations = state['modulations']
            if hasattr(self, 'mod_rows'):
                for i in range(len(self.mod_rows)):
                    src, tgt, amt = self.mod_rows[i]
                    if i < len(self.modulations):
                        src.setCurrentText(self.modulations[i]['source'])
                        tgt.setCurrentText(self.modulations[i]['target'])
                        amt.setValue(self.modulations[i]['amount'])
                    else:
                        src.setCurrentIndex(0)
                        tgt.setCurrentIndex(0)
                        amt.setValue(0.0)

        self.update_preview_params()

    def save_workspace(self, name):
        if not hasattr(self, 'workspaces'):
            self.workspaces = {}
            
        layout = {}
        
        # Main Window
        layout['geometry_main'] = self.saveGeometry().toHex().data().decode()
        layout['state_main'] = self.saveState().toHex().data().decode()
        
        # Sub Windows Helper
        def save_sub(key, win):
            if win:
                layout[f'geometry_{key}'] = win.saveGeometry().toHex().data().decode()
                layout[f'visible_{key}'] = win.isVisible()
            else:
                layout[f'visible_{key}'] = False
                
        save_sub('perf', self.performance_window)
        save_sub('seq', self.sequencer_window)
        save_sub('conn', self.connectivity_window)
        save_sub('editor', self.shader_editor_window)
        save_sub('midi', self.midi_debug_window)
        
        # Collapsed Modules
        collapsed_modules = []
        from gui_modules.base import BaseModule
        for widget in self.findChildren(BaseModule):
            if widget.collapsible and widget.is_collapsed:
                collapsed_modules.append(widget.__class__.__name__)
        layout['collapsed_modules'] = collapsed_modules
        
        self.workspaces[name] = layout
        self.save_ui_state() # Persist
        
        if hasattr(self, 'log'):
            self.log(f"💾 Workspace '{name}' sauvegardé.")

    def load_workspace(self, name):
        if not hasattr(self, 'workspaces') or name not in self.workspaces:
            return
            
        layout = self.workspaces[name]
        
        # Main Window
        if 'geometry_main' in layout:
            self.restoreGeometry(bytes.fromhex(layout['geometry_main']))
        if 'state_main' in layout:
            self.restoreState(bytes.fromhex(layout['state_main']))
            
        # Sub Windows Helper
        def restore_sub(key, win_attr, toggle_func):
            should_be_visible = layout.get(f'visible_{key}', False)
            current_win = getattr(self, win_attr)
            is_visible = current_win is not None
            
            if should_be_visible != is_visible:
                toggle_func()
                current_win = getattr(self, win_attr) # Refresh ref
            
            if should_be_visible and current_win and f'geometry_{key}' in layout:
                current_win.restoreGeometry(bytes.fromhex(layout[f'geometry_{key}']))

        restore_sub('perf', 'performance_window', self.toggle_performance_view)
        restore_sub('seq', 'sequencer_window', self.toggle_sequencer_window)
        restore_sub('conn', 'connectivity_window', self.toggle_connectivity_window)
        restore_sub('editor', 'shader_editor_window', self.toggle_shader_editor)
        restore_sub('midi', 'midi_debug_window', self.toggle_midi_monitor)
        
        # Collapsed Modules
        if 'collapsed_modules' in layout:
            collapsed_modules = layout['collapsed_modules']
            from gui_modules.base import BaseModule
            for widget in self.findChildren(BaseModule):
                if widget.collapsible:
                    # Check both class name (robust) and title (legacy support)
                    is_collapsed = (widget.__class__.__name__ in collapsed_modules) or (widget.title() in collapsed_modules)
                    widget.set_collapsed(is_collapsed, animate=True)
                    
        if hasattr(self, 'log'):
            self.log(f"🖥️ Workspace '{name}' chargé.")

    def delete_workspace(self, name):
        if hasattr(self, 'workspaces') and name in self.workspaces:
            del self.workspaces[name]
            self.save_ui_state()
            if hasattr(self, 'log'):
                self.log(f"🗑️ Workspace '{name}' supprimé.")

    def choose_scroller_color(self):
        color = QColorDialog.getColor(title=self.tr("scroller_color_dialog_title"))
        if color.isValid():
            self.scroller_color = (color.red(), color.green(), color.blue())
            self.btn_scroller_color.setStyleSheet(f"background-color: {color.name()}; color: {'black' if color.lightness() > 128 else 'white'}; font-weight: bold;")

    def choose_spectrogram_color(self):
        color = QColorDialog.getColor(QColor(*self.spectrogram_bg_color), self, self.tr("spectrogram_color_dialog_title"), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.spectrogram_bg_color = (color.red(), color.green(), color.blue(), color.alpha())
            self.btn_spec_color.setStyleSheet(f"background-color: {color.name()}; color: {'black' if color.lightness() > 128 else 'white'}; font-weight: bold;")

    def choose_particle_color(self):
        color = QColorDialog.getColor(QColor(int(self.particle_color[0]*255), int(self.particle_color[1]*255), int(self.particle_color[2]*255)), self, "Particle Color")
        if color.isValid():
            self.particle_color = (color.redF(), color.greenF(), color.blueF())
            self.btn_particle_color.setStyleSheet(f"background-color: {color.name()}; color: {'black' if color.lightness() > 128 else 'white'}; font-weight: bold;")
            self.update_preview_params()

    def choose_light2_color(self):
        color = QColorDialog.getColor(QColor(int(self.light2_color[0]*255), int(self.light2_color[1]*255), int(self.light2_color[2]*255)), self, "Light 2 Color")
        if color.isValid():
            self.light2_color = (color.redF(), color.greenF(), color.blueF())
            self.update_preview_params()
