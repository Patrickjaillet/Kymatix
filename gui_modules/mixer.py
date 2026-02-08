from PyQt6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
                             QLabel, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QGridLayout, 
                             QSlider, QAbstractSpinBox, QMenu)
from PyQt6.QtCore import Qt
from .base import BaseModule

class MixerModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_visual_mixer"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 15, 5, 5)

        # Style Selector
        row1 = QHBoxLayout()
        self.mw.style_combo = QComboBox()
        self.mw.style_combo.addItems(self.mw.available_styles)
        self.mw.style_combo.currentTextChanged.connect(self.mw.update_preview_style)
        self.mw.btn_fav = QPushButton("★")
        self.mw.btn_fav.setFixedWidth(20)
        self.mw.btn_fav.clicked.connect(self.mw.manage_favorites)
        
        self.mw.btn_refresh = QPushButton("↻")
        self.mw.btn_refresh.setFixedWidth(20)
        self.mw.btn_refresh.setToolTip("Recharger les styles (.glsl)")
        self.mw.btn_refresh.clicked.connect(self.mw.refresh_styles)
        
        self.mw.btn_edit_shader = QPushButton("✎")
        self.mw.btn_edit_shader.setFixedWidth(20)
        self.mw.btn_edit_shader.setToolTip("Éditer le code GLSL du style")
        self.mw.btn_edit_shader.clicked.connect(self.mw.toggle_shader_editor)
        
        self.mw.btn_check_shaders = QPushButton("✓")
        self.mw.btn_check_shaders.setFixedWidth(20)
        self.mw.btn_check_shaders.setToolTip("Vérifier tous les shaders")
        self.mw.btn_check_shaders.clicked.connect(self.mw.check_shaders)
        
        row1.addWidget(QLabel("STYLE"))
        row1.addWidget(self.mw.style_combo)
        row1.addWidget(self.mw.btn_refresh)
        row1.addWidget(self.mw.btn_edit_shader)
        row1.addWidget(self.mw.btn_check_shaders)
        row1.addWidget(self.mw.btn_fav)
        layout.addLayout(row1)
        
        # User Texture
        tex_layout = QHBoxLayout()
        tex_layout.setSpacing(2)
        self.mw.user_texture_input = QLineEdit()
        self.mw.user_texture_input.setPlaceholderText("Texture (Image)...")
        self.mw.user_texture_input.setReadOnly(True)
        self.mw.btn_browse_texture = QPushButton("...")
        self.mw.btn_browse_texture.setFixedWidth(25)
        self.mw.btn_browse_texture.clicked.connect(self.mw.browse_user_texture)
        self.mw.btn_clear_texture = QPushButton("X")
        self.mw.btn_clear_texture.setFixedWidth(20)
        self.mw.btn_clear_texture.clicked.connect(self.mw.clear_user_texture)
        tex_layout.addWidget(QLabel("TEX:"))
        tex_layout.addWidget(self.mw.user_texture_input)
        tex_layout.addWidget(self.mw.btn_browse_texture)
        tex_layout.addWidget(self.mw.btn_clear_texture)
        
        self.mw.distort_texture_check = QCheckBox("DST")
        self.mw.distort_texture_check.setToolTip("Appliquer les distorsions (Twist, Ripple...) à la texture")
        self.mw.distort_texture_check.toggled.connect(self.mw.update_preview_params)
        tex_layout.addWidget(self.mw.distort_texture_check)
        
        self.mw.texture_blend_combo = QComboBox()
        self.mw.texture_blend_combo.addItems(["Mix", "Add", "Multiply", "Screen"])
        self.mw.texture_blend_combo.setToolTip("Mode de fusion de la texture")
        self.mw.texture_blend_combo.currentTextChanged.connect(self.mw.update_preview_params)
        self.mw.texture_blend_combo.setFixedWidth(70)
        tex_layout.addWidget(self.mw.texture_blend_combo)
        layout.addLayout(tex_layout)
        
        # Macro Recorder
        self.mw.btn_rec_macro = QPushButton("● REC MACRO")
        self.mw.btn_rec_macro.setCheckable(True)
        self.mw.btn_rec_macro.clicked.connect(self.mw.toggle_macro_recording)
        layout.addWidget(self.mw.btn_rec_macro)

        # Dynamic Style
        self.mw.dynamic_style_check = QCheckBox("AUTO-SWITCH (Dynamic)")
        layout.addWidget(self.mw.dynamic_style_check)

        # Particle Count
        pc_layout = QHBoxLayout()
        pc_layout.addWidget(QLabel("COUNT:"))
        self.mw.particle_count_spin = QSpinBox()
        self.mw.particle_count_spin.setRange(1000, 1000000)
        self.mw.particle_count_spin.setSingleStep(10000)
        self.mw.particle_count_spin.setValue(100000)
        self.mw.particle_count_spin.valueChanged.connect(self.mw.update_particle_count)
        pc_layout.addWidget(self.mw.particle_count_spin)
        
        self.mw.btn_particle_color = QPushButton("COLOR")
        self.mw.btn_particle_color.setFixedWidth(50)
        self.mw.btn_particle_color.clicked.connect(self.mw.choose_particle_color)
        pc_layout.addWidget(self.mw.btn_particle_color)
        layout.addLayout(pc_layout)

        # Particle Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("MODE:"))
        self.mw.particle_mode_combo = QComboBox()
        self.mw.particle_mode_combo.addItems(["Rain", "Emit"])
        self.mw.particle_mode_combo.currentTextChanged.connect(self.mw.update_preview_params)
        mode_layout.addWidget(self.mw.particle_mode_combo)
        layout.addLayout(mode_layout)

        # Gravity
        grav_layout = QHBoxLayout()
        grav_layout.addWidget(QLabel("GRAVITY:"))
        self.mw.particle_gravity_spin = QDoubleSpinBox()
        self.mw.particle_gravity_spin.setRange(-2.0, 2.0)
        self.mw.particle_gravity_spin.setSingleStep(0.1)
        self.mw.particle_gravity_spin.setValue(0.5)
        self.mw.particle_gravity_spin.valueChanged.connect(self.mw.update_preview_params)
        grav_layout.addWidget(self.mw.particle_gravity_spin)

        grav_layout.addWidget(QLabel("LIFE:"))
        self.mw.particle_life_spin = QDoubleSpinBox()
        self.mw.particle_life_spin.setRange(0.1, 10.0)
        self.mw.particle_life_spin.setSingleStep(0.1)
        self.mw.particle_life_spin.setValue(3.0)
        self.mw.particle_life_spin.valueChanged.connect(self.mw.update_preview_params)
        grav_layout.addWidget(self.mw.particle_life_spin)

        grav_layout.addWidget(QLabel("TURB:"))
        self.mw.particle_turb_spin = QDoubleSpinBox()
        self.mw.particle_turb_spin.setRange(0.0, 10.0)
        self.mw.particle_turb_spin.setSingleStep(0.1)
        self.mw.particle_turb_spin.setValue(1.0)
        self.mw.particle_turb_spin.valueChanged.connect(self.mw.update_preview_params)
        grav_layout.addWidget(self.mw.particle_turb_spin)
        
        grav_layout.addWidget(QLabel("SIZE:"))
        self.mw.particle_size_spin = QDoubleSpinBox()
        self.mw.particle_size_spin.setRange(0.1, 50.0)
        self.mw.particle_size_spin.setSingleStep(0.5)
        self.mw.particle_size_spin.setValue(2.0)
        self.mw.particle_size_spin.valueChanged.connect(self.mw.update_preview_params)
        grav_layout.addWidget(self.mw.particle_size_spin)
        
        layout.addLayout(grav_layout)

        # --- AUTO-PILOT ---
        ap_layout = QHBoxLayout()
        ap_layout.setSpacing(2)
        
        self.mw.autopilot_check = QCheckBox("AUTO-PILOT")
        self.mw.autopilot_check.setToolTip("Change de style automatiquement")
        
        self.mw.autopilot_timer_spin = QSpinBox()
        self.mw.autopilot_timer_spin.setRange(5, 300)
        self.mw.autopilot_timer_spin.setValue(15)
        self.mw.autopilot_timer_spin.setSuffix("s")
        self.mw.autopilot_timer_spin.setToolTip("Intervalle de temps (secondes)")
        self.mw.autopilot_timer_spin.setFixedWidth(50)
        
        self.mw.autopilot_drop_check = QCheckBox("ON DROP")
        self.mw.autopilot_drop_check.setToolTip("Changer sur les drops (impacts)")
        
        ap_layout.addWidget(self.mw.autopilot_check)
        ap_layout.addWidget(self.mw.autopilot_timer_spin)
        ap_layout.addWidget(self.mw.autopilot_drop_check)
        layout.addLayout(ap_layout)
        # ------------------

        # Sliders Grid
        sliders_layout = QGridLayout()
        sliders_layout.setSpacing(2)
        
        # Helper to create vertical slider with label
        def create_v_slider(label, attr_name, min_v, max_v, default_v, step):
            v_layout = QVBoxLayout()
            v_layout.setSpacing(0)
            
            # Lock Button
            lock_attr_name = f"lock_{attr_name}"
            lock_btn = QPushButton("🔓")
            lock_btn.setCheckable(True)
            lock_btn.setFixedSize(16, 16)
            lock_btn.setToolTip("Verrouiller ce paramètre (Lock)")
            lock_btn.setStyleSheet("""
                QPushButton { border: none; background: transparent; color: #444; font-size: 10px; }
                QPushButton:checked { color: #FF4444; }
                QPushButton:hover { color: #888; }
            """)
            lock_btn.toggled.connect(lambda checked, b=lock_btn: b.setText("🔒" if checked else "🔓"))
            setattr(self.mw, lock_attr_name, lock_btn)
            
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 8px; color: #888;")
            
            slider = QDoubleSpinBox() # Using SpinBox for precision in this dense layout, or could use QSlider mapped
            # Let's use QDoubleSpinBox styled as compact value box for "Modul8" feel
            slider.setRange(min_v, max_v)
            slider.setSingleStep(step)
            slider.setValue(default_v)
            slider.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            slider.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider.valueChanged.connect(self.mw.update_preview_params)
            setattr(self.mw, attr_name, slider)
            
            # Visual Slider (Fake analog feel)
            qslider = QSlider(Qt.Orientation.Vertical)
            qslider.setRange(int(min_v*100), int(max_v*100))
            qslider.setValue(int(default_v*100))
            qslider.valueChanged.connect(lambda v: slider.setValue(v/100.0))
            slider.valueChanged.connect(lambda v: qslider.setValue(int(v*100)))
            
            # Context Menu for MIDI Learn
            qslider.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            qslider.customContextMenuRequested.connect(
                lambda pos, s=slider, name=attr_name: self.mw.show_control_context_menu(pos, qslider, name))

            v_layout.addWidget(lock_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            v_layout.addWidget(qslider, alignment=Qt.AlignmentFlag.AlignCenter)
            v_layout.addWidget(slider)
            v_layout.addWidget(lbl)
            return v_layout

        # Adding sliders
        sliders_layout.addLayout(create_v_slider("BLOOM", "bloom_spin", 0.0, 3.0, 0.5, 0.1), 0, 0)
        sliders_layout.addLayout(create_v_slider("ABERR", "aberration_spin", 0.0, 2.0, 0.1, 0.05), 0, 1)
        sliders_layout.addLayout(create_v_slider("GRAIN", "grain_spin", 0.0, 0.5, 0.05, 0.01), 0, 2)
        sliders_layout.addLayout(create_v_slider("GLITCH", "glitch_spin", 0.0, 1.0, 0.0, 0.05), 0, 3)
        sliders_layout.addLayout(create_v_slider("VIGNET", "vignette_spin", 0.0, 1.0, 0.0, 0.05), 0, 4)
        sliders_layout.addLayout(create_v_slider("SCAN", "scanline_spin", 0.0, 1.0, 0.0, 0.05), 0, 5)
        
        # Row 2
        sliders_layout.addLayout(create_v_slider("CONTR", "contrast_spin", 0.0, 2.0, 1.0, 0.1), 1, 0)
        sliders_layout.addLayout(create_v_slider("SAT", "saturation_spin", 0.0, 2.0, 1.0, 0.1), 1, 1)
        sliders_layout.addLayout(create_v_slider("BRIGHT", "brightness_spin", -0.5, 0.5, 0.0, 0.05), 1, 2)
        sliders_layout.addLayout(create_v_slider("GAMMA", "gamma_spin", 0.1, 3.0, 1.0, 0.1), 1, 3)
        sliders_layout.addLayout(create_v_slider("STROBE", "strobe_spin", 0.0, 1.0, 0.0, 0.05), 1, 4)
        sliders_layout.addLayout(create_v_slider("MIRROR", "mirror_spin", 0.0, 1.0, 0.0, 0.05), 1, 5)
        
        # Row 3 (New Effects)
        sliders_layout.addLayout(create_v_slider("PIXEL", "pixelate_spin", 0.0, 1.0, 0.0, 0.05), 2, 0)
        sliders_layout.addLayout(create_v_slider("POSTER", "posterize_spin", 0.0, 1.0, 0.0, 0.05), 2, 1)
        sliders_layout.addLayout(create_v_slider("SOLAR", "solarize_spin", 0.0, 1.0, 0.0, 0.05), 2, 2)
        sliders_layout.addLayout(create_v_slider("HUE", "hue_shift_spin", 0.0, 1.0, 0.0, 0.05), 2, 3)
        sliders_layout.addLayout(create_v_slider("INVERT", "invert_spin", 0.0, 1.0, 0.0, 0.05), 2, 4)
        sliders_layout.addLayout(create_v_slider("SEPIA", "sepia_spin", 0.0, 1.0, 0.0, 0.05), 2, 5)

        # Row 4 (New Effects)
        sliders_layout.addLayout(create_v_slider("THERM", "thermal_spin", 0.0, 1.0, 0.0, 0.05), 3, 0)
        sliders_layout.addLayout(create_v_slider("EDGE", "edge_spin", 0.0, 1.0, 0.0, 0.05), 3, 1)
        sliders_layout.addLayout(create_v_slider("FISH", "fisheye_spin", 0.0, 1.0, 0.0, 0.05), 3, 2)
        sliders_layout.addLayout(create_v_slider("TWIST", "twist_spin", 0.0, 1.0, 0.0, 0.05), 3, 3)
        sliders_layout.addLayout(create_v_slider("RIPPLE", "ripple_spin", 0.0, 1.0, 0.0, 0.05), 3, 4)
        sliders_layout.addLayout(create_v_slider("QUAD", "mirror_quad_spin", 0.0, 1.0, 0.0, 0.05), 3, 5)

        # Row 5 (New Effects Set 2)
        sliders_layout.addLayout(create_v_slider("RGB", "rgb_split_spin", 0.0, 0.1, 0.0, 0.005), 4, 0)
        sliders_layout.addLayout(create_v_slider("BLEACH", "bleach_spin", 0.0, 1.0, 0.0, 0.05), 4, 1)
        sliders_layout.addLayout(create_v_slider("VHS", "vhs_spin", 0.0, 1.0, 0.0, 0.05), 4, 2)
        sliders_layout.addLayout(create_v_slider("NEON", "neon_spin", 0.0, 1.0, 0.0, 0.05), 4, 3)
        sliders_layout.addLayout(create_v_slider("TOON", "cartoon_spin", 0.0, 1.0, 0.0, 0.05), 4, 4)
        sliders_layout.addLayout(create_v_slider("SKETCH", "sketch_spin", 0.0, 1.0, 0.0, 0.05), 4, 5)

        # Row 6 (New Effects Set 2)
        sliders_layout.addLayout(create_v_slider("VIBE", "vibrate_spin", 0.0, 1.0, 0.0, 0.05), 5, 0)
        sliders_layout.addLayout(create_v_slider("DRUNK", "drunk_spin", 0.0, 1.0, 0.0, 0.05), 5, 1)
        sliders_layout.addLayout(create_v_slider("PINCH", "pinch_spin", 0.0, 1.0, 0.0, 0.05), 5, 2)
        sliders_layout.addLayout(create_v_slider("ZOOM", "zoom_blur_spin", 0.0, 1.0, 0.0, 0.05), 5, 3)
        sliders_layout.addLayout(create_v_slider("AURA", "aura_spin", 0.0, 1.0, 0.0, 0.05), 5, 4)
        sliders_layout.addLayout(create_v_slider("PSYCHO", "psycho_spin", 0.0, 1.0, 0.0, 0.05), 5, 5)
        
        # Row 7 (Feedback)
        sliders_layout.addLayout(create_v_slider("FEEDBACK", "feedback_spin", 0.0, 0.99, 0.0, 0.01), 6, 0)
        # Placeholder for alignment
        sliders_layout.addWidget(QLabel(""), 6, 1)
        sliders_layout.addWidget(QLabel(""), 6, 2)
        sliders_layout.addWidget(QLabel(""), 6, 3)
        sliders_layout.addWidget(QLabel(""), 6, 4)
        sliders_layout.addWidget(QLabel(""), 6, 5)

        # Hidden but required params
        self.mw.exposure_spin = QDoubleSpinBox()
        self.mw.exposure_spin.setValue(1.0)
        self.mw.exposure_spin.setVisible(False)
        self.mw.light_leak_spin = QDoubleSpinBox()
        self.mw.light_leak_spin.setValue(0.0)
        self.mw.light_leak_spin.setVisible(False)

        layout.addLayout(sliders_layout)
        
        # Reset Button
        self.mw.btn_reset_fx = QPushButton("RESET FX")
        self.mw.btn_reset_fx.clicked.connect(self.mw.reset_fx_params)

        # Randomize Button
        self.mw.btn_random_fx = QPushButton("🎲 RANDOMIZE FX")
        self.mw.btn_random_fx.clicked.connect(self.mw.randomize_fx_params)

        # Randomize All Button
        self.mw.btn_random_all = QPushButton("🎲 RANDOMIZE ALL")
        self.mw.btn_random_all.clicked.connect(self.mw.randomize_all_params)

        # Randomize settings button
        self.mw.btn_random_settings = QPushButton("⚙")
        self.mw.btn_random_settings.setToolTip("Configure Randomization Exclusions")
        self.mw.btn_random_settings.setFixedSize(24, 24)
        self.mw.btn_random_settings.clicked.connect(self.mw.open_randomize_settings)

        # Morph Button
        self.mw.btn_morph_fx = QPushButton("🌊 MORPH FX")
        self.mw.btn_morph_fx.clicked.connect(self.mw.start_morph_fx)

        # Sequencer Button
        self.mw.btn_sequencer = QPushButton("🎹 SEQUENCER")
        self.mw.btn_sequencer.setToolTip("Ouvre la fenêtre des Scènes et de la Playlist")
        self.mw.btn_sequencer.clicked.connect(self.mw.toggle_sequencer_window)

        random_layout = QHBoxLayout()
        random_layout.addWidget(self.mw.btn_random_fx)
        random_layout.addWidget(self.mw.btn_random_all)
        random_layout.addWidget(self.mw.btn_random_settings)

        layout.addWidget(self.mw.btn_reset_fx)
        layout.addLayout(random_layout)
        layout.addWidget(self.mw.btn_morph_fx)
        layout.addWidget(self.mw.btn_sequencer)

class PerformanceModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_performance"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        # Compute Shaders (moving from MixerModule)
        self.mw.compute_check = QCheckBox("GPU PARTICLES (Compute Shader)")
        self.mw.compute_check.setToolTip("Enable GPU-based particle simulation (requires OpenGL 4.3+)")
        self.mw.compute_check.toggled.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.compute_check)

        # PBO Toggle
        self.mw.pbo_check = QCheckBox("ASYNC READBACK (PBO)")
        self.mw.pbo_check.setToolTip("Enable faster pixel reading from GPU for recording/export. (Recommended)")
        self.mw.pbo_check.setChecked(True) # Default is on
        self.mw.pbo_check.toggled.connect(self.mw.toggle_pbo_usage)
        layout.addWidget(self.mw.pbo_check)
        
        layout.addStretch()

class Model3DModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_3d_model"), collapsible=True)
        self.mw = mw
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        # Enable Checkbox
        self.mw.model_enable_check = QCheckBox("ENABLE")
        self.mw.model_enable_check.setChecked(False)
        self.mw.model_enable_check.toggled.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_enable_check, 0, 0, 1, 1)
        
        # Wireframe Checkbox
        self.mw.model_wireframe_check = QCheckBox("WIREFRAME")
        self.mw.model_wireframe_check.toggled.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_wireframe_check, 0, 1, 1, 1)

        # Flat Shading Checkbox
        self.mw.model_flat_shading_check = QCheckBox("FLAT")
        self.mw.model_flat_shading_check.toggled.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_flat_shading_check, 0, 2, 1, 1)

        # Base Scale
        layout.addWidget(QLabel("SCALE:"), 1, 0)
        self.mw.model_base_scale_spin = QDoubleSpinBox()
        self.mw.model_base_scale_spin.setRange(0.1, 10.0)
        self.mw.model_base_scale_spin.setSingleStep(0.1)
        self.mw.model_base_scale_spin.setValue(1.0)
        self.mw.model_base_scale_spin.setToolTip("Définit la taille de base du modèle 3D.")
        self.mw.model_base_scale_spin.valueChanged.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_base_scale_spin, 1, 1)

        # Rotation Speed
        layout.addWidget(QLabel("SPEED:"), 2, 0)
        self.mw.model_speed_spin = QDoubleSpinBox()
        self.mw.model_speed_spin.setRange(0.0, 10.0)
        self.mw.model_speed_spin.setSingleStep(0.1)
        self.mw.model_speed_spin.setValue(0.5)
        self.mw.model_speed_spin.valueChanged.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_speed_spin, 2, 1)

        # Deformation Slider
        layout.addWidget(QLabel("DEFORM:"), 3, 0)
        self.mw.model_deformation_spin = QDoubleSpinBox()
        self.mw.model_deformation_spin.setRange(0.0, 2.0)
        self.mw.model_deformation_spin.setSingleStep(0.1)
        self.mw.model_deformation_spin.setValue(0.0)
        self.mw.model_deformation_spin.valueChanged.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_deformation_spin, 3, 1)

        # Reflection Slider
        layout.addWidget(QLabel("REFLECT:"), 4, 0)
        self.mw.model_reflection_spin = QDoubleSpinBox()
        self.mw.model_reflection_spin.setRange(0.0, 1.0)
        self.mw.model_reflection_spin.setSingleStep(0.1)
        self.mw.model_reflection_spin.setValue(0.0)
        self.mw.model_reflection_spin.valueChanged.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_reflection_spin, 4, 1)

        # Ghosting Slider
        layout.addWidget(QLabel("GHOST:"), 5, 0)
        self.mw.model_ghosting_spin = QDoubleSpinBox()
        self.mw.model_ghosting_spin.setRange(0.0, 1.0)
        self.mw.model_ghosting_spin.setSingleStep(0.1)
        self.mw.model_ghosting_spin.setValue(0.0)
        self.mw.model_ghosting_spin.valueChanged.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.model_ghosting_spin, 5, 1)

        # Reset Rotation Button
        self.mw.btn_reset_rot = QPushButton("RESET ROT")
        self.mw.btn_reset_rot.clicked.connect(self.mw.reset_model_rotation)
        layout.addWidget(self.mw.btn_reset_rot, 6, 0, 1, 2)

        # Light 2 Color
        self.mw.btn_light2_color = QPushButton("LIGHT 2 COLOR")
        self.mw.btn_light2_color.clicked.connect(self.mw.choose_light2_color)
        layout.addWidget(self.mw.btn_light2_color, 7, 0, 1, 2)

        # Generate Assets Button
        self.mw.btn_gen_assets = QPushButton("GENERATE ASSETS")
        self.mw.btn_gen_assets.setToolTip("Générer les modèles 3D par défaut dans /assets")
        self.mw.btn_gen_assets.clicked.connect(self.mw.generate_assets)
        layout.addWidget(self.mw.btn_gen_assets, 8, 0, 1, 2)

class ModulationModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_audio_modulation"), collapsible=True)
        self.mw = mw
        layout = QGridLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 15, 5, 5)

        self.sources = ["None", "sub_bass", "bass", "low_mid", "mid", "high_mid", "presence", "brilliance", "beat_strength", "intensity", "kick", "snare", "hi_hats"]
        self.targets = ["None", "bloom_strength", "aberration_strength", "grain_strength", "glitch_strength", 
                        "vignette_strength", "scanline_strength", "contrast_strength", "saturation_strength", 
                        "brightness_strength", "gamma_strength", "exposure_strength", "strobe_strength", 
                        "light_leak_strength", "mirror_strength", "pixelate_strength", "posterize_strength", 
                        "solarize_strength", "hue_shift_strength", "invert_strength", "sepia_strength", 
                        "thermal_strength", "edge_strength", "fisheye_strength", "twist_strength",
                        "ripple_strength", "mirror_quad_strength", "rgb_split_strength", "bleach_strength",
                        "vhs_strength", "neon_strength", "cartoon_strength", "sketch_strength", "vibrate_strength",
                        "drunk_strength", "pinch_strength", "zoom_blur_strength", "aura_strength", "psycho_strength"]

        self.mw.mod_rows = []
        for i in range(4):
            src_combo = QComboBox()
            src_combo.addItems(self.sources)
            src_combo.setFixedWidth(70)
            
            tgt_combo = QComboBox()
            tgt_combo.addItems(self.targets)
            tgt_combo.setFixedWidth(100)
            
            amt_spin = QDoubleSpinBox()
            amt_spin.setRange(-5.0, 5.0)
            amt_spin.setSingleStep(0.1)
            amt_spin.setValue(0.0)
            amt_spin.setFixedWidth(50)
            
            layout.addWidget(src_combo, i, 0)
            layout.addWidget(QLabel("→"), i, 1)
            layout.addWidget(tgt_combo, i, 2)
            layout.addWidget(amt_spin, i, 3)
            
            self.mw.mod_rows.append((src_combo, tgt_combo, amt_spin))
            
            src_combo.currentTextChanged.connect(self.mw.update_modulations)
            tgt_combo.currentTextChanged.connect(self.mw.update_modulations)
            amt_spin.valueChanged.connect(self.mw.update_modulations)

        # FFT Configuration
        self.mw.btn_config_fft = QPushButton("⚙ FFT BANDS")
        self.mw.btn_config_fft.setToolTip("Configurer les bandes de fréquences personnalisées")
        self.mw.btn_config_fft.clicked.connect(self.mw.open_fft_config)
        layout.addWidget(self.mw.btn_config_fft, 4, 0, 1, 4)

class QuickPresetsModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_quick_presets"))
        self.mw = mw
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)
        
        # Container pour les boutons de presets
        presets_layout = QGridLayout()
        presets_layout.setSpacing(4)
        
        for i in range(8):
            btn = QPushButton(str(i+1))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setFixedHeight(40)
            btn.setToolTip("Clic-Droit pour assigner le style actuel")

            # Style spécifique pour ressembler à des pads de MPC/Table de mixage
            btn.setStyleSheet("""
                QPushButton { 
                    background-color: #222; color: #888; font-size: 14px; font-weight: bold; border: 1px solid #444;
                }
                QPushButton:hover { 
                    background-color: #333; color: #FFF; border-color: #666;
                }
                QPushButton:checked { 
                    background-color: #00FF00; color: #000; border: 1px solid #00FF00;
                }
            """)
            
            btn.clicked.connect(lambda _, idx=i: self.mw.activate_quick_preset(idx))
            
            # Menu contextuel pour assignation
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, idx=i, b=btn: self.show_context_menu(pos, idx, b))
            
            presets_layout.addWidget(btn, i // 4, i % 4)
            setattr(self.mw, f"btn_quick_{i}", btn)

        layout.addLayout(presets_layout)

        # Boutons de contrôle (Randomize & Performance View)
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(2)
        
        self.mw.btn_random_presets = QPushButton("🎲")
        self.mw.btn_random_presets.setToolTip("Randomize Presets")
        self.mw.btn_random_presets.setFixedSize(24, 19)
        self.mw.btn_random_presets.clicked.connect(self.mw.randomize_quick_presets)
        
        self.mw.btn_perf_view = QPushButton("↗")
        self.mw.btn_perf_view.setToolTip("Performance View (Fenêtre flottante)")
        self.mw.btn_perf_view.setFixedSize(24, 19)
        self.mw.btn_perf_view.clicked.connect(self.mw.toggle_performance_view)
        
        controls_layout.addWidget(self.mw.btn_random_presets)
        controls_layout.addWidget(self.mw.btn_perf_view)
        layout.addLayout(controls_layout)

    def show_context_menu(self, pos, index, btn):
        menu = QMenu(self)
        current_style = self.mw.style_combo.currentText()
        action = menu.addAction(f"Assigner: {current_style}")
        action_midi = menu.addAction("MIDI Learn")
        action.triggered.connect(lambda: self.mw.assign_quick_preset(index, current_style))
        action_midi.triggered.connect(lambda: self.mw.enable_midi_learn(f"btn_quick_{index}"))
        menu.exec(btn.mapToGlobal(pos))

class MaskModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_masking"), collapsible=True)
        self.mw = mw
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)

        self.mw.mask_enable_check = QCheckBox("Enable")
        self.mw.mask_enable_check.toggled.connect(self.mw.toggle_mask_enabled)
        layout.addWidget(self.mw.mask_enable_check, 0, 0)

        self.mw.mask_mode_combo = QComboBox()
        self.mw.mask_mode_combo.addItems(["Inside", "Outside"])
        self.mw.mask_mode_combo.currentTextChanged.connect(self.mw.set_mask_mode)
        layout.addWidget(self.mw.mask_mode_combo, 0, 1)

        self.mw.mask_draw_btn = QPushButton("Draw Mask")
        self.mw.mask_draw_btn.setCheckable(True)
        self.mw.mask_draw_btn.toggled.connect(self.mw.toggle_mask_drawing)
        layout.addWidget(self.mw.mask_draw_btn, 1, 0)

        self.mw.mask_clear_btn = QPushButton("Clear")
        self.mw.mask_clear_btn.clicked.connect(self.mw.clear_mask)
        layout.addWidget(self.mw.mask_clear_btn, 1, 1)

class StyleTransferModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_ai_style"), collapsible=True)
        self.mw = mw
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        
        self.mw.ai_enable_check = QCheckBox("ENABLE AI")
        self.mw.ai_enable_check.setToolTip("Enable AI Style Transfer (Slow on CPU!)")
        layout.addWidget(self.mw.ai_enable_check, 0, 0)
        
        self.mw.ai_model_combo = QComboBox()
        self.mw.ai_model_combo.setToolTip("Select Style Model")
        layout.addWidget(self.mw.ai_model_combo, 0, 1)
        
        self.mw.btn_refresh_ai = QPushButton("↻")
        self.mw.btn_refresh_ai.setFixedWidth(25)
        self.mw.btn_refresh_ai.clicked.connect(self.mw.refresh_ai_models)
        layout.addWidget(self.mw.btn_refresh_ai, 0, 2)
        
        layout.addWidget(QLabel("STRENGTH:"), 1, 0)
        self.mw.ai_strength_spin = QDoubleSpinBox()
        self.mw.ai_strength_spin.setRange(0.0, 1.0)
        self.mw.ai_strength_spin.setSingleStep(0.1)
        self.mw.ai_strength_spin.setValue(1.0)
        layout.addWidget(self.mw.ai_strength_spin, 1, 1, 1, 2)