from PyQt6.QtWidgets import (QGroupBox, QGridLayout, QLineEdit, QFontComboBox, QPushButton, 
                             QComboBox, QCheckBox, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
                             QTextEdit, QProgressBar, QTabWidget, QWidget, QMenu)
from gui_widgets import GoniometerWidget
from .base import BaseModule

class OverlayModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_overlays"))
        self.mw = mw
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        # Text Scroller
        self.mw.title_input = QLineEdit()
        self.mw.title_input.setPlaceholderText("TITLE")
        self.mw.artist_input = QLineEdit()
        self.mw.artist_input.setPlaceholderText("ARTIST")
        layout.addWidget(self.mw.title_input, 0, 0, 1, 2)
        layout.addWidget(self.mw.artist_input, 0, 2, 1, 2)

        self.mw.font_combo = QFontComboBox()
        self.mw.btn_scroller_color = QPushButton("COLOR")
        self.mw.btn_scroller_color.clicked.connect(self.mw.choose_scroller_color)
        self.mw.text_effect_combo = QComboBox()
        self.mw.text_effect_combo.addItems(["Scroll", "Wave", "Glitch", "Neon", "Bounce"])
        
        layout.addWidget(self.mw.font_combo, 1, 0, 1, 2)
        layout.addWidget(self.mw.btn_scroller_color, 1, 2)
        layout.addWidget(self.mw.text_effect_combo, 1, 3)

        # Extra Overlays
        self.mw.spectrogram_check = QCheckBox("SPECTRO")
        self.mw.btn_spec_color = QPushButton("BG")
        self.mw.btn_spec_color.clicked.connect(self.mw.choose_spectrogram_color)
        self.mw.spec_pos_combo = QComboBox()
        self.mw.spec_pos_combo.addItems(["Bas", "Haut"])
        
        layout.addWidget(self.mw.spectrogram_check, 2, 0)
        layout.addWidget(self.mw.btn_spec_color, 2, 1)
        layout.addWidget(self.mw.spec_pos_combo, 2, 2, 1, 2)

        # Files
        self.mw.logo_input = QLineEdit()
        self.mw.logo_input.setPlaceholderText("LOGO.PNG")
        self.mw.btn_logo = QPushButton("...")
        self.mw.btn_logo.setFixedWidth(20)
        self.mw.btn_logo.clicked.connect(self.mw.browse_logo)
        
        self.mw.srt_input = QLineEdit()
        self.mw.srt_input.setPlaceholderText("LYRICS.SRT")
        self.mw.btn_srt = QPushButton("...")
        self.mw.btn_srt.setFixedWidth(20)
        self.mw.btn_srt.clicked.connect(self.mw.browse_srt)

        layout.addWidget(self.mw.logo_input, 3, 0, 1, 3)
        layout.addWidget(self.mw.btn_logo, 3, 3)
        layout.addWidget(self.mw.srt_input, 4, 0, 1, 3)
        layout.addWidget(self.mw.btn_srt, 4, 3)
        
        self.mw.json_check = QCheckBox("SAVE JSON")
        layout.addWidget(self.mw.json_check, 5, 0, 1, 2)
        
        self.mw.btn_border_color = QPushButton("UI THEME")
        self.mw.btn_border_color.setToolTip("Changer la couleur des bordures")
        
        # Menu is now managed by MainWindow.update_theme_menu()
        layout.addWidget(self.mw.btn_border_color, 5, 2, 1, 2)

class ConnectivityModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_connectivity"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        # MIDI Device Selector (Moved below logs)
        midi_layout = QHBoxLayout()
        self.mw.midi_combo.addItem("No MIDI Device", -1)
        self.mw.midi_combo.currentIndexChanged.connect(self.mw.change_midi_device)
        
        self.mw.btn_midi_monitor.setFixedWidth(30)
        self.mw.btn_midi_monitor.setToolTip("Ouvrir le moniteur MIDI")
        self.mw.btn_midi_monitor.clicked.connect(self.mw.toggle_midi_monitor)
        
        midi_layout.addWidget(QLabel("MIDI IN"))
        midi_layout.addWidget(self.mw.midi_combo)
        midi_layout.addWidget(self.mw.btn_midi_monitor)
        layout.addLayout(midi_layout)
        
        # OSC
        osc_layout = QHBoxLayout()
        self.mw.osc_port_spin.setRange(1024, 65535)
        self.mw.osc_port_spin.setValue(8000)
        self.mw.osc_port_spin.setPrefix("Port: ")
        self.mw.btn_osc_toggle.setCheckable(True)
        self.mw.btn_osc_toggle.clicked.connect(self.mw.toggle_osc)
        
        osc_layout.addWidget(self.mw.osc_port_spin)
        osc_layout.addWidget(self.mw.btn_osc_toggle)
        layout.addLayout(osc_layout)
        
        # Ableton Link
        self.mw.btn_link = QPushButton("ABLETON LINK")
        self.mw.btn_link.setCheckable(True)
        self.mw.btn_link.setToolTip("Synchronisation via Ableton Link (Carabiner)")
        self.mw.btn_link.clicked.connect(self.mw.toggle_link)
        layout.addWidget(self.mw.btn_link)

        # DMX
        dmx_layout = QHBoxLayout()
        self.mw.dmx_universe_spin = QSpinBox()
        self.mw.dmx_universe_spin.setRange(1, 63999)
        self.mw.dmx_universe_spin.setValue(1)
        self.mw.dmx_universe_spin.setPrefix("Univ: ")
        self.mw.btn_dmx = QPushButton("ENABLE DMX")
        self.mw.btn_dmx.setCheckable(True)
        self.mw.btn_dmx.setToolTip("Activer la sortie DMX (sACN)")
        self.mw.btn_dmx.clicked.connect(self.mw.toggle_dmx)
        
        self.mw.btn_dmx_map = QPushButton("MAP")
        self.mw.btn_dmx_map.setFixedWidth(40)
        self.mw.btn_dmx_map.setToolTip("Configurer le mapping DMX")
        self.mw.btn_dmx_map.clicked.connect(self.mw.open_dmx_mapping)
        
        dmx_layout.addWidget(self.mw.dmx_universe_spin)
        dmx_layout.addWidget(self.mw.btn_dmx)
        dmx_layout.addWidget(self.mw.btn_dmx_map)
        layout.addLayout(dmx_layout)

        # Spout / NDI
        self.mw.output_combo = QComboBox()
        self.mw.output_combo.addItems(["No Output", "Spout"])
        self.mw.output_combo.currentTextChanged.connect(self.mw.change_output_mode)
        layout.addWidget(QLabel("VIDEO OUTPUT"))
        layout.addWidget(self.mw.output_combo)

        # Recording
        self.mw.btn_record_output.setCheckable(True)
        self.mw.btn_record_output.clicked.connect(self.mw.toggle_output_recording)
        self.mw.btn_record_output.setStyleSheet("background-color: #440000; color: #FF0000; font-weight: bold;")
        layout.addWidget(self.mw.btn_record_output)

class ConsoleModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_console"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        
        self.mw.log_area = QTextEdit()
        self.mw.log_area.setReadOnly(True)
        layout.addWidget(self.mw.log_area)
        
        self.mw.btn_clear_log = QPushButton("CLEAR LOG")
        self.mw.btn_clear_log.clicked.connect(self.mw.log_area.clear)
        layout.addWidget(self.mw.btn_clear_log)
        
        self.mw.progress_bar = QProgressBar()
        self.mw.progress_bar.setFixedHeight(10)
        layout.addWidget(self.mw.progress_bar)
        
        self.mw.merge_progress = QProgressBar()
        self.mw.merge_progress.setVisible(False)
        layout.addWidget(self.mw.merge_progress)
        
        # Dummy placeholders for compatibility
        self.mw.worker = None
        self.mw.tabs = QTabWidget() # Hidden dummy
        self.mw.tabs.setVisible(False)
        self.mw.about_content = QWidget() # Dummy container
        
        # Fix: Ajout des onglets fantômes pour éviter les erreurs d'index dans retranslate_ui
        for _ in range(4): self.mw.tabs.addTab(QWidget(), "")
        
        # Fix: Ajout des widgets enfants fantômes pour que findChild ne renvoie pas None
        QLabel(self.mw.about_content).setObjectName("title")
        QLabel(self.mw.about_content).setObjectName("version")
        QLabel(self.mw.about_content).setObjectName("desc")
        QPushButton(self.mw.about_content).setObjectName("website")
        QPushButton(self.mw.about_content).setObjectName("soundcloud")
        
        self.mw.general_groups = []
        self.mw.fx_groups = []
        self.mw.overlay_groups = []
        self.mw.btn_expand_general = QPushButton()
        self.mw.btn_collapse_general = QPushButton()
        self.mw.btn_expand_fx = QPushButton()
        self.mw.btn_collapse_fx = QPushButton()
        self.mw.btn_expand_ov = QPushButton()
        self.mw.btn_collapse_ov = QPushButton()
        self.mw.group_file = QGroupBox()
        self.mw.group_info = QGroupBox()
        self.mw.group_render_settings = QGroupBox()
        self.mw.style_group = QGroupBox()
        self.mw.light_fx_group = QGroupBox()
        self.mw.optics_fx_group = QGroupBox()
        self.mw.color_fx_group = QGroupBox()
        self.mw.glitch_fx_group = QGroupBox()
        self.mw.fx_options_group = QGroupBox()
        self.mw.scroller_group = QGroupBox()
        self.mw.overlays_group = QGroupBox()
        self.mw.lbl_mode = QLabel()
        self.mw.lbl_audio = QLabel()
        self.mw.lbl_output = QLabel()
        self.mw.lbl_title = QLabel()
        self.mw.lbl_artist = QLabel()
        self.mw.lbl_resolution = QLabel()
        self.mw.lbl_fps = QLabel()
        self.mw.lbl_audio_preset = QLabel()
        self.mw.btn_save_defaults = QPushButton()
        self.mw.lbl_bloom = QLabel()
        self.mw.lbl_brightness = QLabel()
        self.mw.lbl_gamma = QLabel()
        self.mw.lbl_exposure = QLabel()
        self.mw.lbl_strobe = QLabel()
        self.mw.lbl_light_leak = QLabel()
        self.mw.lbl_aberration = QLabel()
        self.mw.lbl_grain = QLabel()
        self.mw.lbl_vignette = QLabel()
        self.mw.lbl_scanlines = QLabel()
        self.mw.lbl_mirror = QLabel()
        self.mw.lbl_contrast = QLabel()
        self.mw.lbl_saturation = QLabel()
        self.mw.lbl_glitch = QLabel()
        self.mw.preview_check = QCheckBox()
        self.mw.preview_check.setChecked(True)
        self.mw.lbl_font = QLabel()
        self.mw.lbl_effect = QLabel()
        self.mw.lbl_lyrics = QLabel()
        self.mw.lbl_preset = QLabel()
        self.mw.preset_combo = QComboBox()
        self.mw.btn_save_preset = QPushButton()
        self.mw.lang_combo = QComboBox()

class GoniometerModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_stereo_field"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        
        self.mw.goniometer = GoniometerWidget()
        layout.addWidget(self.mw.goniometer)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Lissajous", "Polar"])
        self.mode_combo.currentTextChanged.connect(self.mw.goniometer.set_mode)
        layout.addWidget(self.mode_combo)