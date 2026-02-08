import os
import time
import random
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton
from PyQt6.QtCore import QFileSystemWatcher
from shader_generator import ProceduralShaderGenerator

class FXMixin:
    def init_style_watcher(self):
        """Initialise la surveillance du dossier glsl pour rechargement auto"""
        self.watcher = QFileSystemWatcher(self)
        glsl_dir = ProceduralShaderGenerator.get_glsl_dir()
        if os.path.exists(glsl_dir):
            self.watcher.addPath(glsl_dir)
            self.watcher.directoryChanged.connect(self.refresh_styles)
            self.watcher.fileChanged.connect(self.refresh_styles)
            self.log(f"👀 Surveillance active du dossier: {glsl_dir}")

    def refresh_styles(self, path=None):
        """Recharge les styles et met à jour l'interface"""
        ProceduralShaderGenerator.reload()
        self.available_styles = ProceduralShaderGenerator.get_available_styles()
        
        current = self.style_combo.currentText()
        self.style_combo.blockSignals(True)
        self.style_combo.clear()
        self.style_combo.addItems(self.available_styles)
        
        idx = self.style_combo.findText(current)
        if idx >= 0: self.style_combo.setCurrentIndex(idx)
        elif self.style_combo.count() > 0: self.style_combo.setCurrentIndex(0)
        
        self.style_combo.blockSignals(False)
        self.log("♻️ Styles mis à jour automatiquement !")

    def update_preview_style(self, text):
        self.preview_widget.set_style(text)
        if self.performance_window:
            self.performance_window.preview_widget.set_style(text)
        if self.shader_editor_window:
            self.shader_editor_window.load_style(text)

    def update_modulations(self):
        self.modulations = []
        if hasattr(self, 'mod_rows'):
            for src_combo, tgt_combo, amt_spin in self.mod_rows:
                src = src_combo.currentText()
                tgt = tgt_combo.currentText()
                amt = amt_spin.value()
                if src != "None" and tgt != "None" and amt != 0.0:
                    self.modulations.append({'source': src, 'target': tgt, 'amount': amt})
        self.update_preview_params()

    def update_preview_params(self):
        params = {
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
            'feedback_decay': self.feedback_spin.value(),
            'modulations': self.modulations,
            'compute_particles': self.compute_check.isChecked(),
            'particle_gravity': self.particle_gravity_spin.value(),
            'particle_life': self.particle_life_spin.value(),
            'particle_turbulence': self.particle_turb_spin.value(),
            'particle_color': self.particle_color,
            'particle_mode': self.particle_mode_combo.currentText().lower(),
            'particle_size': self.particle_size_spin.value(),
            'vr_mode': self.vr_check.isChecked(),
            'model_base_scale': self.model_base_scale_spin.value(),
            'model_enabled': self.model_enable_check.isChecked(),
            'model_speed': self.model_speed_spin.value(),
            'light2_color': self.light2_color,
            'model_wireframe': self.model_wireframe_check.isChecked(),
            'model_flat_shading': self.model_flat_shading_check.isChecked(),
            'model_deformation': self.model_deformation_spin.value(),
            'model_reflection': self.model_reflection_spin.value(),
            'model_ghosting': self.model_ghosting_spin.value(),
            'distort_user_texture': self.distort_texture_check.isChecked(),
            'texture_blend_mode': self.texture_blend_combo.currentText()
        }
        
        self.preview_widget.update_params(**params)
        if self.performance_window:
            self.performance_window.preview_widget.update_params(**params)

    def update_particle_count(self):
        count = self.particle_count_spin.value()
        self.preview_widget.update_particle_count(count)
        if self.performance_window:
            self.performance_window.preview_widget.update_particle_count(count)

    def reset_fx_params(self):
        self.push_state()
        self.bloom_spin.setValue(0.5)
        self.aberration_spin.setValue(0.1)
        self.grain_spin.setValue(0.05)
        self.glitch_spin.setValue(0.0)
        self.vignette_spin.setValue(0.0)
        self.scanline_spin.setValue(0.0)
        self.contrast_spin.setValue(1.0)
        self.saturation_spin.setValue(1.0)
        self.brightness_spin.setValue(0.0)
        self.gamma_spin.setValue(1.0)
        self.exposure_spin.setValue(1.0)
        self.strobe_spin.setValue(0.0)
        self.light_leak_spin.setValue(0.0)
        self.mirror_spin.setValue(0.0)
        self.pixelate_spin.setValue(0.0)
        self.posterize_spin.setValue(0.0)
        self.solarize_spin.setValue(0.0)
        self.hue_shift_spin.setValue(0.0)
        self.invert_spin.setValue(0.0)
        self.sepia_spin.setValue(0.0)
        self.thermal_spin.setValue(0.0)
        self.edge_spin.setValue(0.0)
        self.fisheye_spin.setValue(0.0)
        self.twist_spin.setValue(0.0)
        self.ripple_spin.setValue(0.0)
        self.mirror_quad_spin.setValue(0.0)
        self.rgb_split_spin.setValue(0.0)
        self.bleach_spin.setValue(0.0)
        self.vhs_spin.setValue(0.0)
        self.neon_spin.setValue(0.0)
        self.cartoon_spin.setValue(0.0)
        self.sketch_spin.setValue(0.0)
        self.vibrate_spin.setValue(0.0)
        self.drunk_spin.setValue(0.0)
        self.pinch_spin.setValue(0.0)
        self.zoom_blur_spin.setValue(0.0)
        self.aura_spin.setValue(0.0)
        self.psycho_spin.setValue(0.0)
        self.feedback_spin.setValue(0.0)

    def is_param_locked(self, widget_name):
        lock_name = f"lock_{widget_name}"
        if hasattr(self, lock_name):
            btn = getattr(self, lock_name)
            return btn.isChecked()
        return False

    def randomize_fx_params(self):
        self.push_state()
        def biased_random(max_val, probability=0.3):
            return random.uniform(0.0, max_val) if random.random() < probability else 0.0

        def set_val(name, val):
            if name in self.randomize_exclusions:
                return
            if not self.is_param_locked(name):
                getattr(self, name).setValue(val)

        set_val("bloom_spin", random.uniform(0.0, 1.0))
        set_val("aberration_spin", random.uniform(0.0, 0.5))
        set_val("grain_spin", random.uniform(0.0, 0.15))
        set_val("vignette_spin", random.uniform(0.0, 0.6))
        set_val("contrast_spin", random.uniform(0.8, 1.2))
        set_val("saturation_spin", random.uniform(0.5, 1.5))
        set_val("brightness_spin", random.uniform(-0.1, 0.1))
        set_val("gamma_spin", random.uniform(0.8, 1.2))
        
        set_val("glitch_spin", biased_random(0.5))
        set_val("scanline_spin", biased_random(0.5))
        set_val("strobe_spin", 0.0)
        set_val("light_leak_spin", biased_random(0.5))
        set_val("mirror_spin", biased_random(0.5, 0.2))
        set_val("pixelate_spin", biased_random(0.5, 0.2))
        set_val("posterize_spin", biased_random(0.5, 0.2))
        set_val("solarize_spin", biased_random(0.5, 0.2))
        set_val("hue_shift_spin", biased_random(1.0, 0.3))
        set_val("invert_spin", biased_random(1.0, 0.1))
        set_val("sepia_spin", biased_random(1.0, 0.2))
        set_val("thermal_spin", biased_random(1.0, 0.1))
        set_val("edge_spin", biased_random(0.5, 0.1))
        set_val("fisheye_spin", biased_random(0.5, 0.2))
        set_val("twist_spin", biased_random(0.5, 0.2))
        set_val("ripple_spin", biased_random(0.5, 0.2))
        set_val("mirror_quad_spin", biased_random(0.5, 0.2))
        set_val("rgb_split_spin", biased_random(0.05, 0.2))
        set_val("bleach_spin", biased_random(1.0, 0.2))
        set_val("vhs_spin", biased_random(0.5, 0.2))
        set_val("neon_spin", biased_random(1.0, 0.1))
        set_val("cartoon_spin", biased_random(1.0, 0.1))
        set_val("sketch_spin", biased_random(1.0, 0.1))
        set_val("vibrate_spin", biased_random(0.5, 0.1))
        set_val("drunk_spin", biased_random(0.5, 0.2))
        set_val("pinch_spin", biased_random(0.5, 0.2))
        set_val("zoom_blur_spin", biased_random(0.5, 0.2))
        set_val("aura_spin", biased_random(1.0, 0.2))
        set_val("psycho_spin", biased_random(1.0, 0.1))
        set_val("feedback_spin", biased_random(0.9, 0.1))
        
        self.log("🎲 FX Randomized!")

    def randomize_all_params(self):
        self.randomize_fx_params()
        if self.available_styles:
            new_style = random.choice(self.available_styles)
            self.style_combo.setCurrentText(new_style)
        self.log("🎲 ALL Randomized (Style + FX)!")

    def start_morph_fx(self):
        self.morph_data = {}
        def biased_random(max_val, probability=0.3):
            return random.uniform(0.0, max_val) if random.random() < probability else 0.0

        targets = {
            "bloom_spin": random.uniform(0.0, 1.0), "aberration_spin": random.uniform(0.0, 0.5),
            "grain_spin": random.uniform(0.0, 0.15), "vignette_spin": random.uniform(0.0, 0.6),
            "contrast_spin": random.uniform(0.8, 1.2), "saturation_spin": random.uniform(0.5, 1.5),
            "brightness_spin": random.uniform(-0.1, 0.1), "gamma_spin": random.uniform(0.8, 1.2),
            "glitch_spin": biased_random(0.5), "scanline_spin": biased_random(0.5), "strobe_spin": 0.0,
            "light_leak_spin": biased_random(0.5), "mirror_spin": biased_random(0.5, 0.2),
            "pixelate_spin": biased_random(0.5, 0.2), "posterize_spin": biased_random(0.5, 0.2),
            "solarize_spin": biased_random(0.5, 0.2), "hue_shift_spin": biased_random(1.0, 0.3),
            "invert_spin": biased_random(1.0, 0.1), "sepia_spin": biased_random(1.0, 0.2),
            "thermal_spin": biased_random(1.0, 0.1), "edge_spin": biased_random(0.5, 0.1),
            "fisheye_spin": biased_random(0.5, 0.2), "twist_spin": biased_random(0.5, 0.2),
            "ripple_spin": biased_random(0.5, 0.2), "mirror_quad_spin": biased_random(0.5, 0.2),
            "rgb_split_spin": biased_random(0.05, 0.2), "bleach_spin": biased_random(1.0, 0.2),
            "vhs_spin": biased_random(0.5, 0.2), "neon_spin": biased_random(1.0, 0.1),
            "cartoon_spin": biased_random(1.0, 0.1), "sketch_spin": biased_random(1.0, 0.1),
            "vibrate_spin": biased_random(0.5, 0.1), "drunk_spin": biased_random(0.5, 0.2),
            "pinch_spin": biased_random(0.5, 0.2), "zoom_blur_spin": biased_random(0.5, 0.2),
            "aura_spin": biased_random(1.0, 0.2), "psycho_spin": biased_random(1.0, 0.1),
            "feedback_spin": biased_random(0.9, 0.1)
        }

        for name, target_val in targets.items():
            if not self.is_param_locked(name):
                widget = getattr(self, name)
                self.morph_data[name] = (widget.value(), target_val)
        
        if self.morph_data:
            self.morph_start_time = time.time()
            self.morph_timer.start(16)
            self.log("🌊 Morphing FX started...")

    def update_morph_step(self):
        elapsed = time.time() - self.morph_start_time
        progress = min(1.0, elapsed / self.morph_duration)
        t = progress * progress * (3.0 - 2.0 * progress)
        
        for name, (start, end) in self.morph_data.items():
            getattr(self, name).setValue(start + (end - start) * t)
            
        if progress >= 1.0:
            self.morph_timer.stop()
            self.log("🌊 Morphing FX complete.")

    def check_single_style(self, style_name):
        dummy_profile = {'tempo': 120, 'energy': 0.5}
        try:
            final_code = ProceduralShaderGenerator.generate_shader(style_name, dummy_profile)
            return self.preview_widget.check_shader_code(final_code)
        except Exception as e:
            return f"Shader Generation Error: {e}"

    def check_shaders(self):
        self.log("🔍 Vérification des shaders...")
        QApplication.processEvents()
        styles = ProceduralShaderGenerator.get_available_styles()
        broken = self.preview_widget.check_all_shaders(styles)
        
        if broken:
            self.log(f"⚠️ {len(broken)} shaders cassés.")
            for name, err in broken:
                err_short = str(err).split('\\n')[0] if '\\n' in str(err) else str(err)
                self.log(f"❌ {name}: {err_short}")
            QMessageBox.warning(self, "Shaders Cassés", f"{len(broken)} shaders contiennent des erreurs.\nConsultez la console pour les détails.")
        else:
            self.log("✅ Tous les shaders sont valides !")
            QMessageBox.information(self, "Succès", "Tous les shaders sont valides.")

    def assign_quick_preset(self, index, style_name):
        if 0 <= index < len(self.quick_presets_map):
            self.quick_presets_map[index] = style_name
            self.update_quick_presets_tooltips()
            self.log(f"💾 Preset {index+1} assigné à : {style_name}")

    def update_quick_presets_tooltips(self):
        for i in range(8):
            btn = getattr(self, f"btn_quick_{i}", None)
            if btn:
                style = self.quick_presets_map[i]
                btn.setToolTip(f"Style: {style} (Clic-Droit pour assigner)")

    def activate_quick_preset(self, index):
        if index < len(self.quick_presets_map):
            style = self.quick_presets_map[index]
            index_in_combo = self.style_combo.findText(style)
            if index_in_combo >= 0:
                self.style_combo.setCurrentIndex(index_in_combo)
                
            if self.is_recording_macro:
                elapsed = time.time() - self.macro_start_time
                self.macro_events.append({'time': elapsed, 'type': 'style', 'value': style})

    def randomize_quick_presets(self):
        if not self.available_styles: return
        for i in range(8):
            style = random.choice(self.available_styles)
            self.quick_presets_map[i] = style
        self.update_quick_presets_tooltips()
        self.log("🎲 Presets aléatoires générés !")

    def reset_model_rotation(self):
        self.preview_widget.reset_model_rotation()
