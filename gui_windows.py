from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSizePolicy, QTextEdit)
from PyQt6.QtCore import Qt

from gui_widgets import ShaderPreviewWidget
from gui_layout import ScenesModule, PlaylistModule, ConnectivityModule, MixerModule
from gui_theme import QSS_THEME

class PerformanceWindow(QMainWindow):
    """Fenêtre flottante pour la performance live sur un deuxième écran"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.setWindowTitle("KYMATIX STUDIO - Performance View")
        self.resize(800, 600)
        self.setStyleSheet(QSS_THEME)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # Preview en grand
        self.preview_widget = ShaderPreviewWidget()
        self.preview_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.preview_widget)
        
        # Barre de presets en bas
        presets_widget = QWidget()
        presets_widget.setStyleSheet("background-color: #111; border-top: 1px solid #333;")
        presets_layout = QHBoxLayout(presets_widget)
        presets_layout.setContentsMargins(10, 10, 10, 10)
        presets_layout.setSpacing(5)
        
        for i in range(8):
            btn = QPushButton(str(i+1))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setFixedHeight(60)
            btn.setStyleSheet("QPushButton { font-size: 18px; font-weight: bold; border-radius: 4px; } QPushButton:checked { background-color: #00FF00; color: #000; }")
            btn.clicked.connect(lambda _, idx=i: self.mw.activate_quick_preset(idx))
            presets_layout.addWidget(btn)
            
        layout.addWidget(presets_widget)

    def closeEvent(self, event):
        self.mw.performance_window = None
        event.accept()

class SequencerWindow(QMainWindow):
    """Fenêtre pour les scènes (snapshots) et la playlist"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.setWindowTitle("Sequencer")
        self.resize(350, 700)
        self.setStyleSheet(QSS_THEME)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        layout.addWidget(ScenesModule(self.mw))
        layout.addWidget(PlaylistModule(self.mw))
        layout.addStretch()

    def closeEvent(self, event):
        self.mw.sequencer_window = None
        event.accept()

class ConnectivityWindow(QMainWindow):
    """Fenêtre pour la connectivité (MIDI, OSC, NDI, Spout, Recording)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.setWindowTitle("Connectivity")
        self.resize(400, 400)
        self.setStyleSheet(QSS_THEME)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(ConnectivityModule(self.mw))

    def closeEvent(self, event):
        self.mw.connectivity_window = None
        event.accept()

class MidiDebugWindow(QMainWindow):
    """Fenêtre de visualisation des signaux MIDI entrants"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MIDI Monitor")
        self.resize(400, 300)
        self.setStyleSheet(QSS_THEME)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("font-family: 'Consolas', monospace; font-size: 10pt; background-color: #000; color: #0F0;")
        self.setCentralWidget(self.text_edit)
        
    def log_midi(self, status, data1, data2):
        msg_type = "Unknown"
        if 128 <= status < 144: msg_type = "Note Off"
        elif 144 <= status < 160: msg_type = "Note On"
        elif 176 <= status < 192: msg_type = "CC"
        elif 224 <= status < 240: msg_type = "PitchBend"
        
        chan = (status & 0x0F) + 1
        self.text_edit.append(f"CH:{chan:02d} | {msg_type:<9} | D1:{data1:03d} | D2:{data2:03d}")
        self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())

class MixerWindow(QMainWindow):
    """Fenêtre détachée pour le mixeur visuel"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.setWindowTitle("Visual Mixer")
        self.resize(420, 800)
        self.setStyleSheet(QSS_THEME)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        
        layout.addWidget(MixerModule(self.mw))
        layout.addStretch()

    def closeEvent(self, event):
        # On cache seulement la fenêtre pour ne pas détruire les widgets référencés par MainWindow
        event.ignore()
        self.hide()
