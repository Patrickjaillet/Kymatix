from PyQt6.QtWidgets import (QGroupBox, QGridLayout, QLabel, QComboBox, QLineEdit, QPushButton, 
                             QCheckBox, QSpinBox, QHBoxLayout, QSlider, QVBoxLayout, QSizePolicy)
from PyQt6.QtCore import Qt
from gui_widgets import WaveformWidget, ShaderPreviewWidget, VUMeterWidget
from .base import BaseModule

class SourceModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_media_source"))
        self.mw = mw
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        # Mode Selector
        self.mw.mode_combo = QComboBox()
        self.mw.mode_combo.addItems(["FILE RENDER", "LIVE INPUT"])
        self.mw.mode_combo.currentIndexChanged.connect(self.mw.toggle_mode)
        layout.addWidget(QLabel("MODE"), 0, 0)
        layout.addWidget(self.mw.mode_combo, 0, 1)

        # Audio Input
        self.mw.audio_input = QLineEdit()
        self.mw.audio_input.setPlaceholderText("No Audio File...")
        self.mw.btn_audio = QPushButton("LOAD")
        self.mw.btn_audio.clicked.connect(self.mw.browse_audio)
        layout.addWidget(QLabel("AUDIO"), 1, 0)
        layout.addWidget(self.mw.audio_input, 1, 1)
        layout.addWidget(self.mw.btn_audio, 1, 2)

        # Device Combo (Hidden by default)
        self.mw.device_combo = QComboBox()
        self.mw.device_combo.setVisible(False)
        layout.addWidget(self.mw.device_combo, 1, 1, 1, 2)

        # Video Input (iChannel0)
        self.mw.video_source_combo = QComboBox()
        self.mw.video_source_combo.addItems(["No Video Input", "Webcam", "Video File", "Spout Receiver"])
        self.mw.video_source_combo.currentIndexChanged.connect(self.mw.change_video_source)
        
        self.mw.video_input_path = QLineEdit()
        self.mw.video_input_path.setPlaceholderText("Video file path...")
        self.mw.video_input_path.setVisible(False)
        self.mw.btn_video_browse = QPushButton("...")
        self.mw.btn_video_browse.setVisible(False)
        self.mw.btn_video_browse.clicked.connect(self.mw.browse_video_input)
        
        layout.addWidget(QLabel("VIDEO IN"), 2, 0)
        layout.addWidget(self.mw.video_source_combo, 2, 1)
        layout.addWidget(self.mw.video_input_path, 2, 1) # Stacked visually via visibility
        layout.addWidget(self.mw.btn_video_browse, 2, 2)

        # Batch Mode
        self.mw.batch_check = QCheckBox("BATCH FOLDER")
        self.mw.batch_check.toggled.connect(self.mw.toggle_batch_mode)
        layout.addWidget(self.mw.batch_check, 3, 0, 1, 3)

        # Waveform
        self.mw.waveform = WaveformWidget()
        self.mw.waveform.setMinimumHeight(40)
        layout.addWidget(self.mw.waveform, 4, 0, 1, 3)
        self.mw.loader_thread = None

class OutputModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_master_output"))
        self.mw = mw
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        # Resolution
        self.mw.width_spin = QSpinBox()
        self.mw.width_spin.setRange(1, 9999)
        self.mw.width_spin.setValue(1920)
        self.mw.height_spin = QSpinBox()
        self.mw.height_spin.setRange(1, 9999)
        self.mw.height_spin.setValue(1080)
        self.mw.btn_swap_res = QPushButton("↔")
        self.mw.btn_swap_res.setFixedWidth(20)
        self.mw.btn_swap_res.clicked.connect(self.mw.swap_resolution)
        
        layout.addWidget(QLabel("RES"), 0, 0)
        layout.addWidget(self.mw.width_spin, 0, 1)
        layout.addWidget(QLabel("x"), 0, 2)
        layout.addWidget(self.mw.height_spin, 0, 3)
        layout.addWidget(self.mw.btn_swap_res, 0, 4)

        # FPS & Preset
        self.mw.fps_spin = QSpinBox()
        self.mw.fps_spin.setValue(60)
        self.mw.audio_preset_combo = QComboBox()
        self.mw.audio_preset_combo.addItems(["Flat", "Bass Boost", "Vocal Boost"])
        
        layout.addWidget(QLabel("FPS"), 1, 0)
        layout.addWidget(self.mw.fps_spin, 1, 1)
        layout.addWidget(QLabel("EQ"), 1, 2)
        layout.addWidget(self.mw.audio_preset_combo, 1, 3)
        
        self.mw.vr_check = QCheckBox("VR 360")
        self.mw.vr_check.setToolTip("Rendu Equirectangulaire pour vidéo 360°")
        self.mw.vr_check.toggled.connect(self.mw.update_preview_params)
        layout.addWidget(self.mw.vr_check, 1, 4)

        # Output Path
        self.mw.output_input = QLineEdit()
        self.mw.btn_out = QPushButton("...")
        self.mw.btn_out.setFixedWidth(25)
        self.mw.btn_out.clicked.connect(self.mw.browse_output)
        layout.addWidget(QLabel("OUT"), 2, 0)
        layout.addWidget(self.mw.output_input, 2, 1, 1, 3)
        layout.addWidget(self.mw.btn_out, 2, 4)

        # Render Buttons
        self.mw.btn_preview = QPushButton("PREVIEW (5s)")
        self.mw.btn_preview.clicked.connect(self.mw.start_preview)
        self.mw.btn_start = QPushButton("RENDER FULL")
        self.mw.btn_start.setStyleSheet("background-color: #004400; color: #00FF00; border: 1px solid #00FF00;")
        self.mw.btn_start.clicked.connect(self.mw.start_render)
        
        layout.addWidget(self.mw.btn_preview, 3, 0, 1, 2)
        layout.addWidget(self.mw.btn_start, 3, 2, 1, 3)

class TransportModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_transport"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 15, 5, 5)
        
        # Timeline
        timeline_layout = QHBoxLayout()
        self.mw.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.mw.seek_slider.setRange(0, 100)
        self.mw.seek_slider.sliderMoved.connect(self.mw.seek_audio)
        
        self.mw.lbl_time = QLabel("00:00 / 00:00")
        self.mw.lbl_time.setStyleSheet("font-family: monospace; font-size: 10px; color: #00FF00;")
        self.mw.lbl_time.setFixedWidth(80)
        self.mw.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        timeline_layout.addWidget(self.mw.seek_slider)
        timeline_layout.addWidget(self.mw.lbl_time)
        layout.addLayout(timeline_layout)
        
        # Buttons
        btns = QHBoxLayout()
        self.mw.btn_play = QPushButton("▶ PLAY")
        self.mw.btn_play.clicked.connect(self.mw.play_audio)
        self.mw.btn_play.setEnabled(False)
        
        self.mw.btn_pause = QPushButton("❚❚ PAUSE")
        self.mw.btn_pause.setCheckable(True)
        self.mw.btn_pause.clicked.connect(self.mw.pause_audio)
        
        self.mw.btn_stop = QPushButton("■ STOP")
        self.mw.btn_stop.clicked.connect(self.mw.stop_audio)
        
        self.mw.btn_loop = QPushButton("🔁")
        self.mw.btn_loop.setCheckable(True)
        self.mw.btn_loop.setFixedWidth(30)
        self.mw.btn_loop.setToolTip("Activer/Désactiver la boucle")
        
        btns.addWidget(self.mw.btn_play)
        btns.addWidget(self.mw.btn_pause)
        btns.addWidget(self.mw.btn_stop)
        btns.addWidget(self.mw.btn_loop)
        layout.addLayout(btns)

class PreviewModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("group_preview"))
        self.mw = mw
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(2, 15, 2, 2)

        self.mw.vu_meter_left = VUMeterWidget()
        layout.addWidget(self.mw.vu_meter_left)
        
        self.mw.preview_widget = ShaderPreviewWidget()
        self.mw.preview_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.mw.preview_widget)
        
        self.mw.vu_meter = VUMeterWidget()
        layout.addWidget(self.mw.vu_meter)