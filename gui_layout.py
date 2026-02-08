from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QLabel, QPushButton, QProgressBar, QDockWidget, QMainWindow, QTabWidget, QStyle)
from PyQt6.QtCore import Qt
from gui_modules.media import SourceModule, OutputModule, TransportModule, PreviewModule
from gui_modules.mixer import MixerModule, PerformanceModule, Model3DModule, ModulationModule, QuickPresetsModule, MaskModule, StyleTransferModule
from gui_modules.vst import VSTModule
from gui_modules.sequencer import ScenesModule, PlaylistModule
from gui_timeline import TimelineModule
from gui_node_editor import NodeEditorModule
from gui_modules.tools import OverlayModule, ConnectivityModule, ConsoleModule, GoniometerModule

class GUILayout:
    def __init__(self, main_window):
        self.mw = main_window
        self.docks = {}

    def setup_ui(self):
        # 1. Configuration du Docking
        self.mw.setDockOptions(QMainWindow.DockOption.AnimatedDocks | 
                               QMainWindow.DockOption.AllowNestedDocks | 
                               QMainWindow.DockOption.AllowTabbedDocks)
        
        # Position des onglets en haut des docks (plus ergonomique)
        self.mw.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)

        # 2. Pas de widget central fixe (Full Docking)
        self.mw.setCentralWidget(None)

        # 3. Création des Docks
        def create_dock(module_class, title_key, area, obj_name, icon=None):
            # Instanciation du module (QGroupBox)
            module_widget = module_class(self.mw)
            
            # Création du Dock
            dock = QDockWidget(self.mw.tr(title_key), self.mw)
            dock.setObjectName(obj_name) # Crucial pour saveState/restoreState
            dock.setWidget(module_widget)
            dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
            
            if icon:
                dock.setWindowIcon(icon)
            
            # Ajout à la fenêtre principale
            self.mw.addDockWidget(area, dock)
            self.docks[obj_name] = dock
            return dock

        style = self.mw.style()

        # --- Zone Gauche ---
        create_dock(SourceModule, "module_media_source", Qt.DockWidgetArea.LeftDockWidgetArea, "dock_source", style.standardIcon(QStyle.StandardPixmap.SP_DriveCDIcon))
        create_dock(OutputModule, "module_master_output", Qt.DockWidgetArea.LeftDockWidgetArea, "dock_output", style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        create_dock(OverlayModule, "module_overlays", Qt.DockWidgetArea.LeftDockWidgetArea, "dock_overlay", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        create_dock(GoniometerModule, "module_stereo_field", Qt.DockWidgetArea.LeftDockWidgetArea, "dock_goniometer", style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        create_dock(ConsoleModule, "module_console", Qt.DockWidgetArea.LeftDockWidgetArea, "dock_console", style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        create_dock(ConnectivityModule, "module_connectivity", Qt.DockWidgetArea.LeftDockWidgetArea, "dock_connectivity", style.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon))

        # --- Zone Centrale / Droite (Preview) ---
        create_dock(PreviewModule, "group_preview", Qt.DockWidgetArea.RightDockWidgetArea, "dock_preview", style.standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))

        # --- Zone Droite ---
        create_dock(MixerModule, "module_visual_mixer", Qt.DockWidgetArea.RightDockWidgetArea, "dock_mixer", style.standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        create_dock(Model3DModule, "module_3d_model", Qt.DockWidgetArea.RightDockWidgetArea, "dock_model3d", style.standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        create_dock(ModulationModule, "module_audio_modulation", Qt.DockWidgetArea.RightDockWidgetArea, "dock_modulation", style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        create_dock(ScenesModule, "module_scenes", Qt.DockWidgetArea.RightDockWidgetArea, "dock_scenes", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        create_dock(PlaylistModule, "module_playlist", Qt.DockWidgetArea.RightDockWidgetArea, "dock_playlist", style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        create_dock(PerformanceModule, "module_performance", Qt.DockWidgetArea.RightDockWidgetArea, "dock_performance", style.standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        create_dock(MaskModule, "module_masking", Qt.DockWidgetArea.RightDockWidgetArea, "dock_mask", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        create_dock(StyleTransferModule, "module_ai_style", Qt.DockWidgetArea.RightDockWidgetArea, "dock_ai", style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        create_dock(VSTModule, "module_vst", Qt.DockWidgetArea.RightDockWidgetArea, "dock_vst", style.standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        create_dock(TimelineModule, "action_timeline", Qt.DockWidgetArea.BottomDockWidgetArea, "dock_timeline", style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        create_dock(NodeEditorModule, "action_node_editor", Qt.DockWidgetArea.BottomDockWidgetArea, "dock_node_editor", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))

        # --- Zone Bas ---
        create_dock(TransportModule, "module_transport", Qt.DockWidgetArea.BottomDockWidgetArea, "dock_transport", style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        create_dock(QuickPresetsModule, "module_quick_presets", Qt.DockWidgetArea.BottomDockWidgetArea, "dock_quick_presets", style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))

        # Organisation par onglets pour économiser de l'espace par défaut
        self.mw.tabifyDockWidget(self.docks["dock_console"], self.docks["dock_connectivity"])
        self.mw.tabifyDockWidget(self.docks["dock_source"], self.docks["dock_output"])
        self.mw.tabifyDockWidget(self.docks["dock_scenes"], self.docks["dock_playlist"])
        self.mw.tabifyDockWidget(self.docks["dock_model3d"], self.docks["dock_modulation"])
        self.mw.tabifyDockWidget(self.docks["dock_performance"], self.docks["dock_mask"])
        self.mw.tabifyDockWidget(self.docks["dock_mask"], self.docks["dock_ai"])
        self.mw.tabifyDockWidget(self.docks["dock_ai"], self.docks["dock_vst"])
        self.mw.tabifyDockWidget(self.docks["dock_timeline"], self.docks["dock_node_editor"])
        
        # Référence pour l'accès depuis MainWindow
        self.mw.docks = self.docks

        # --- STATUS BAR ---
        self.mw.status_progress = QProgressBar()
        self.mw.status_progress.setRange(0, 100)
        self.mw.status_progress.setVisible(False)
        self.mw.status_progress.setFixedWidth(200)
        self.mw.status_progress.setStyleSheet("QProgressBar { border: 1px solid #333; background: #111; height: 14px; text-align: center; color: #FFF; font-size: 10px; } QProgressBar::chunk { background-color: #00FF00; }")
        self.mw.statusBar().addPermanentWidget(self.mw.status_progress)

        self.mw.model_info_label = QLabel("")
        self.mw.model_info_label.setStyleSheet("color: #AAA; font-size: 10px; margin-right: 10px;")
        self.mw.statusBar().addPermanentWidget(self.mw.model_info_label)

        self.mw.btn_cancel_loading = QPushButton("✖")
        self.mw.btn_cancel_loading.setFixedSize(20, 20)
        self.mw.btn_cancel_loading.setToolTip("Annuler le chargement")
        self.mw.btn_cancel_loading.setVisible(False)
        self.mw.btn_cancel_loading.setStyleSheet("QPushButton { border: none; color: #FF4444; font-weight: bold; background: transparent; } QPushButton:hover { color: #FF8888; }")
        self.mw.btn_cancel_loading.clicked.connect(self.mw.preview_widget.cancel_model_loading)
        self.mw.statusBar().addPermanentWidget(self.mw.btn_cancel_loading)

        self.mw.fps_label = QLabel("FPS: --")
        self.mw.fps_label.setStyleSheet("color: #00FF00; font-weight: bold; margin-right: 10px;")
        self.mw.statusBar().addPermanentWidget(self.mw.fps_label)
        self.mw.statusBar().setStyleSheet("background-color: #1A1A1A; color: #888; border-top: 1px solid #333;")
        
        self.mw.preview_widget.fps_changed.connect(lambda fps: self.mw.fps_label.setText(f"FPS: {fps:.1f}"))
        self.mw.preview_widget.model_loading_progress.connect(self.update_model_progress)
        self.mw.preview_widget.model_info.connect(self.mw.model_info_label.setText)

    def update_model_progress(self, value):
        if 0 < value < 100:
            self.mw.status_progress.setVisible(True)
            self.mw.btn_cancel_loading.setVisible(True)
            self.mw.status_progress.setValue(value)
            self.mw.status_progress.setFormat("Loading 3D Model: %p%")
        else:
            self.mw.status_progress.setVisible(False)
            self.mw.btn_cancel_loading.setVisible(False)
