from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox, 
                             QGridLayout, QLabel, QSpinBox, QComboBox, QPushButton, QHBoxLayout, QWidget, QScrollArea, QListWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import webbrowser
import audio_analysis
from gui_threads import CURRENT_VERSION
from gui_theme import QSS_THEME

class FavoritesDialog(QDialog):
    def __init__(self, available_styles, current_favorites, parent=None):
        super().__init__(parent)
        self.setWindowTitle(parent.tr("favorites_dialog_title"))
        self.resize(300, 400)
        self.layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        for style in available_styles:
            item = QListWidgetItem(style)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if style in current_favorites else Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
            
        self.layout.addWidget(self.list_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def get_selected(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count()) if self.list_widget.item(i).checkState() == Qt.CheckState.Checked]

class RandomizeExclusionsDialog(QDialog):
    def __init__(self, all_effects, excluded_effects, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Randomization")
        self.resize(300, 500)
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Uncheck effects to exclude them from Randomize:"))
        
        self.list_widget = QListWidget()
        for effect_widget_name in all_effects:
            # Make it human-readable
            display_name = effect_widget_name.replace('_spin', '').replace('_', ' ').title()
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, effect_widget_name) # Store original name
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # If it's NOT in the exclusion list, it's checked (included).
            is_included = effect_widget_name not in excluded_effects
            item.setCheckState(Qt.CheckState.Checked if is_included else Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
            
        self.layout.addWidget(self.list_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def get_excluded_effects(self):
        excluded = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Unchecked:
                excluded.append(item.data(Qt.ItemDataRole.UserRole))
        return excluded

class FFTConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFT Frequency Bands Configuration")
        self.resize(400, 350)
        self.layout = QVBoxLayout(self)
        
        grid = QGridLayout()
        self.spinboxes = {}
        
        # Define order for display
        order = ['sub_bass', 'bass', 'low_mid', 'mid', 'high_mid', 'presence', 'brilliance']
        
        row = 0
        for band in order:
            if band in audio_analysis.FREQUENCY_BANDS:
                low, high = audio_analysis.FREQUENCY_BANDS[band]
                
                lbl = QLabel(band.replace('_', ' ').title())
                
                spin_low = QSpinBox()
                spin_low.setRange(0, 22000)
                spin_low.setValue(int(low))
                
                spin_high = QSpinBox()
                spin_high.setRange(0, 22000)
                spin_high.setValue(int(high))
                
                self.spinboxes[band] = (spin_low, spin_high)
                
                grid.addWidget(lbl, row, 0)
                grid.addWidget(spin_low, row, 1)
                grid.addWidget(QLabel("-"), row, 2)
                grid.addWidget(spin_high, row, 3)
                grid.addWidget(QLabel("Hz"), row, 4)
                row += 1
                
        self.layout.addLayout(grid)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def apply_changes(self):
        for band, (spin_low, spin_high) in self.spinboxes.items():
            audio_analysis.FREQUENCY_BANDS[band] = (spin_low.value(), spin_high.value())

class DMXMappingDialog(QDialog):
    def __init__(self, current_mapping, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DMX Mapping")
        self.resize(450, 400)
        self.layout = QVBoxLayout(self)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addStretch() # Push items to top
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
        self.features = ["None", "sub_bass", "bass", "low_mid", "mid", "high_mid", "presence", "brilliance", 
                         "beat_strength", "intensity", "glitch_intensity", "spectral_centroid", "spectral_flux"]
        
        self.rows = []
        
        # Load existing (sorted by channel)
        sorted_mapping = sorted(current_mapping.items())
        for channel, feature in sorted_mapping:
            self.add_row(channel, feature)
            
        # Add button
        self.btn_add = QPushButton("+ Add Mapping")
        self.btn_add.clicked.connect(lambda: self.add_row(1, "None"))
        self.layout.addWidget(self.btn_add)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def add_row(self, channel=1, feature="None"):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        spin = QSpinBox()
        spin.setRange(1, 512)
        spin.setValue(int(channel))
        spin.setPrefix("Ch: ")
        
        combo = QComboBox()
        combo.addItems(self.features)
        combo.setCurrentText(feature)
        
        btn_del = QPushButton("X")
        btn_del.setFixedWidth(30)
        btn_del.setStyleSheet("background-color: #440000; color: #FF0000; font-weight: bold;")
        btn_del.clicked.connect(lambda: self.remove_row(row_widget))
        
        row_layout.addWidget(spin)
        row_layout.addWidget(combo)
        row_layout.addWidget(btn_del)
        
        # Insert before the stretch item
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, row_widget)
        self.rows.append((row_widget, spin, combo))
        
    def remove_row(self, row_widget):
        for i, (w, s, c) in enumerate(self.rows):
            if w == row_widget:
                self.scroll_layout.removeWidget(w)
                w.deleteLater()
                self.rows.pop(i)
                break
                
    def get_mapping(self):
        mapping = {}
        for _, spin, combo in self.rows:
            feat = combo.currentText()
            if feat != "None":
                mapping[spin.value()] = feat
        return mapping

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.resize(400, 450)
        self.setStyleSheet(QSS_THEME)
        layout = QVBoxLayout(self)
        
        self.lbl_logo = QLabel()
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            self.lbl_logo.setPixmap(logo_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.lbl_logo)
        
        self.lbl_title = QLabel("KYMATIX STUDIO")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00FF00;")
        
        self.lbl_version = QLabel(f"Version {CURRENT_VERSION}")
        self.lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_desc = QLabel("Procedural Generation...")
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setWordWrap(True)
        
        self.btn_website = QPushButton("Website")
        self.btn_website.clicked.connect(lambda: webbrowser.open("https://sandefjord.netlify.app"))
        
        self.btn_soundcloud = QPushButton("SoundCloud")
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_version)
        layout.addWidget(self.lbl_desc)
        layout.addStretch()
        layout.addWidget(self.btn_website)
        layout.addWidget(self.btn_soundcloud)
        
        # Initial translation
        self.lbl_title.setText(parent.tr("about_title"))
        self.lbl_version.setText(parent.tr("about_version", version=CURRENT_VERSION))
        self.lbl_desc.setText(parent.tr("about_desc"))
        self.btn_website.setText(parent.tr("about_website"))
        self.btn_soundcloud.setText(parent.tr("about_soundcloud"))