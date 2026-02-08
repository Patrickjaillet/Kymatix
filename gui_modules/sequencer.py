from PyQt6.QtWidgets import (QPushButton, QApplication, QListWidget, QAbstractItemView, QGroupBox, 
                             QGridLayout, QMenu, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QCheckBox, QSpinBox)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag
from .base import BaseModule

class SceneButton(QPushButton):
    """Bouton de scène qui supporte le Drag & Drop"""
    def __init__(self, text, index, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setCheckable(True)
        self.setFixedHeight(30)
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_pos:
            if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(str(self.index))
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.CopyAction)
                self.drag_start_pos = None
                return
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

class PlaylistList(QListWidget):
    """Liste de lecture qui accepte le drop de scènes"""
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.itemDoubleClicked.connect(self.edit_item_duration)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() == self:
            super().dropEvent(event)
        else:
            idx_str = event.mimeData().text()
            try:
                idx = int(idx_str)
                self.mw.add_scene_to_playlist(idx)
                event.accept()
            except ValueError:
                event.ignore()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.selectedItems():
                self.takeItem(self.row(item))
        else:
            super().keyPressEvent(event)

    def edit_item_duration(self, item):
        self.mw.edit_playlist_item_duration(item)

class ScenesModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_scenes"))
        self.mw = mw
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)

        for i in range(8):
            btn = SceneButton(f"{i+1}", i)
            btn.setToolTip(f"Scene {i+1} (Vide - Cliquer pour sauvegarder)")
            btn.setProperty("scene_index", i)
            
            # Menu contextuel
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, b=btn: self.mw.show_scene_context_menu(pos, b))
            
            btn.clicked.connect(lambda _, idx=i: self.mw.trigger_scene(idx))
            
            layout.addWidget(btn, i // 4, i % 4) # 2 rangées de 4
            setattr(self.mw, f"btn_scene_{i}", btn)

class PlaylistModule(BaseModule):
    def __init__(self, mw):
        super().__init__(mw.tr("module_playlist"))
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(5, 15, 5, 5)
        
        self.mw.playlist_list = PlaylistList(mw)
        layout.addWidget(self.mw.playlist_list)
        
        controls = QHBoxLayout()
        self.mw.btn_playlist_play = QPushButton("▶")
        self.mw.btn_playlist_stop = QPushButton("■")
        self.mw.playlist_duration_spin = QDoubleSpinBox()
        self.mw.playlist_duration_spin.setRange(0.1, 60.0)
        self.mw.playlist_duration_spin.setValue(4.0)
        self.mw.playlist_duration_spin.setSuffix("s")
        self.mw.playlist_loop_check = QCheckBox("Loop")
        self.mw.playlist_crossfade_check = QCheckBox("X-Fade")
        
        controls.addWidget(self.mw.btn_playlist_play)
        controls.addWidget(self.mw.btn_playlist_stop)
        controls.addWidget(self.mw.playlist_duration_spin)
        controls.addWidget(self.mw.playlist_loop_check)
        controls.addWidget(self.mw.playlist_crossfade_check)
        layout.addLayout(controls)

        # Controls Row 2 (Beat Sync & Export)
        controls2 = QHBoxLayout()
        self.mw.playlist_beat_sync_check = QCheckBox("Beat Sync")
        self.mw.playlist_bars_spin = QSpinBox()
        self.mw.playlist_bars_spin.setRange(1, 64)
        self.mw.playlist_bars_spin.setValue(4)
        self.mw.playlist_bars_spin.setSuffix(" Bars")
        self.mw.playlist_bars_spin.setToolTip("Durée en mesures (4 temps)")
        
        self.mw.btn_playlist_export = QPushButton("EXPORT VIDEO")
        self.mw.btn_playlist_export.clicked.connect(self.mw.export_playlist)
        self.mw.btn_playlist_export.setStyleSheet("background-color: #004400; color: #00FF00; border: 1px solid #00FF00; font-weight: bold;")
        
        controls2.addWidget(self.mw.playlist_beat_sync_check)
        controls2.addWidget(self.mw.playlist_bars_spin)
        controls2.addStretch()
        controls2.addWidget(self.mw.btn_playlist_export)
        layout.addLayout(controls2)
        
        # Controls Row 3 (File & Shuffle)
        controls3 = QHBoxLayout()
        self.mw.btn_save_playlist = QPushButton("SAVE")
        self.mw.btn_save_playlist.clicked.connect(self.mw.save_playlist)
        self.mw.btn_load_playlist = QPushButton("LOAD")
        self.mw.btn_load_playlist.clicked.connect(self.mw.load_playlist)
        
        self.mw.playlist_shuffle_check = QCheckBox("Shuffle")
        self.mw.playlist_shuffle_check.setToolTip("Lecture aléatoire intelligente (évite les répétitions)")
        
        controls3.addWidget(self.mw.btn_save_playlist)
        controls3.addWidget(self.mw.btn_load_playlist)
        controls3.addWidget(self.mw.playlist_shuffle_check)
        layout.addLayout(controls3)
        
        self.mw.btn_playlist_play.clicked.connect(self.mw.start_playlist)
        self.mw.btn_playlist_stop.clicked.connect(self.mw.stop_playlist)