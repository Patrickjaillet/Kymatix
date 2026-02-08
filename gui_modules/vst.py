from PyQt6.QtWidgets import (QGridLayout, QCheckBox, QComboBox, QPushButton, QLabel, QDoubleSpinBox)
from .base import BaseModule

class VSTModule(BaseModule):
    def __init__(self, mw):
        super().__init__("VST Effects", collapsible=True)
        self.mw = mw
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 15, 5, 5)
        
        self.mw.vst_enable_check = QCheckBox("ENABLE VST")
        self.mw.vst_enable_check.setToolTip("Process audio through a VST plugin before analysis.")
        layout.addWidget(self.mw.vst_enable_check, 0, 0, 1, 2)
        
        self.mw.btn_vst_gui = QPushButton("GUI")
        self.mw.btn_vst_gui.clicked.connect(self.mw.open_vst_gui)
        layout.addWidget(self.mw.btn_vst_gui, 0, 2)
        
        self.mw.vst_plugin_combo = QComboBox()
        self.mw.vst_plugin_combo.setToolTip("Select VST Plugin")
        layout.addWidget(self.mw.vst_plugin_combo, 1, 0, 1, 2)
        
        self.mw.btn_rescan_vst = QPushButton("RESCAN")
        self.mw.btn_rescan_vst.clicked.connect(self.mw.refresh_vst_plugins)
        layout.addWidget(self.mw.btn_rescan_vst, 1, 2)
        
        layout.addWidget(QLabel("MIX:"), 2, 0)
        self.mw.vst_mix_spin = QDoubleSpinBox()
        self.mw.vst_mix_spin.setRange(0.0, 1.0)
        self.mw.vst_mix_spin.setSingleStep(0.1)
        self.mw.vst_mix_spin.setValue(1.0)
        self.mw.vst_mix_spin.setToolTip("Wet/Dry Mix (1.0 = 100% VST)")
        layout.addWidget(self.mw.vst_mix_spin, 2, 1, 1, 2)