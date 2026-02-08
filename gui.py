import sys
import os
import json
import webbrowser
import time
import random
import numpy as np
import re
import collections
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QScrollArea,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QListWidgetItem,
                             QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox, QColorDialog, QCheckBox, QTextEdit,
                             QProgressBar, QFileDialog, QMessageBox, QGroupBox, QSizePolicy, QMenu, QCompleter,
                             QInputDialog, QStyle, QPlainTextEdit, QDialog, QDockWidget)
from PyQt6.QtCore import Qt, QFile, QTextStream, QPropertyAnimation, QEasingCurve, QTimer, QFileSystemWatcher, QSize, QRect, QStringListModel, QEvent
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QTextFormat, QShortcut, QKeySequence, QTextCursor, QTextDocument

from audio_analysis import AdvancedAudioAnalyzer, AdvancedAudioFeatures
from shader_generator import ProceduralShaderGenerator
from gui_translations import TRANSLATIONS
from gui_widgets import WaveformWidget, ShaderPreviewWidget
from gui_dialogs import FavoritesDialog, FFTConfigDialog, DMXMappingDialog, AboutDialog, RandomizeExclusionsDialog
from gui_threads import UpdateCheckerThread, AudioLoaderThread, AnalysisThread, RenderThread, CURRENT_VERSION
from gui_layout import GUILayout, ConnectivityModule
from gui_theme import QSS_THEME
from gui_windows import PerformanceWindow, SequencerWindow, ConnectivityWindow, MidiDebugWindow, MixerWindow
from gui_editor import ShaderEditorWindow
from midi_manager import MidiThread
from gui_audio import AudioMixin
from gui_modules.base import BaseModule
from gui_render import RenderMixin
from gui_state import StateMixin
from gui_input import InputMixin
from gui_fx import FXMixin
from gui_scenes import SceneMixin
from gui_playlist import PlaylistMixin
from vst_manager import VSTManager
import cv2
import pygame

# Injection des traductions pour le nouveau champ Codec
for lang in TRANSLATIONS:
    TRANSLATIONS[lang]['label_codec'] = "Codec"
TRANSLATIONS['fr']['label_codec'] = "Codec Vidéo"
TRANSLATIONS['en']['label_codec'] = "Video Codec"

TRANSLATIONS['fr']['label_bitrate'] = "Bitrate"
TRANSLATIONS['en']['label_bitrate'] = "Bitrate"
TRANSLATIONS['fr']['label_format'] = "Format Export"
TRANSLATIONS['en']['label_format'] = "Export Format"
TRANSLATIONS['fr']['action_node_editor'] = "Éditeur Nodal (Beta)"
TRANSLATIONS['en']['action_node_editor'] = "Node Editor (Beta)"
TRANSLATIONS['fr']['module_masking'] = "MASQUAGE VECTORIEL"
TRANSLATIONS['fr']['action_timeline'] = "Timeline (Beta)"
TRANSLATIONS['en']['action_timeline'] = "Timeline (Beta)"
TRANSLATIONS['fr']['module_vst'] = "EFFETS VST"

class MainWindow(QMainWindow, AudioMixin, RenderMixin, StateMixin, InputMixin, FXMixin, SceneMixin, PlaylistMixin):
    def __init__(self):
        super().__init__()
        self.current_lang = 'fr' 

        self.resize(1280, 850)
        self.center()
        
        font = QFont("sans-serif")
        font.setPixelSize(11)
        QApplication.instance().setFont(font)

        self._init_presets()
        self.check_updates()
        self.available_styles = ProceduralShaderGenerator.get_available_styles()
        self.favorite_styles = self.available_styles.copy()
        self.scroller_color = (255, 255, 255)
        self.spectrogram_bg_color = (0, 0, 0, 128)
        self.spectrogram_position = "Bas"
        self.quick_presets_map = ["fractal", "cyberpunk", "organic", "geometric_tunnel", "vaporwave", "lofi", "crystal", "abstract_line"]
        self.particle_color = (0.2, 0.5, 1.0)
        self.light2_color = (0.8, 0.2, 1.0)
        self.module_border_color = "#333"
        self.custom_themes = {}
        self.workspaces = {}
        self.randomize_exclusions = ['glitch_spin', 'strobe_spin'] # Default exclusions
        
        self.is_recording_macro = False
        self.macro_events = []
        self.macro_start_time = 0.0
        self.performance_window = None
        self.shader_editor_window = None
        self.midi_debug_window = None
        self.sequencer_window = None
        self.connectivity_window = None
        self.about_dialog = None
        self.midi_thread = None
        self.midi_mapping = {} # {(status, data1): target_name}
        self.midi_learn_target = None
        self.scenes = {}
        self.docks = {}
        self.timeline_widget = None # Will be set by TimelineModule
        self.playlist_running = False
        self.playlist_index = -1
        self.detected_bpm = 120.0 # BPM par défaut
        self.transition_timer = QTimer(self)
        self.transition_timer.timeout.connect(self.update_transition)
        self.transition_start_time = 0
        self.last_played_index = -1
        self.modulations = []
        self.osc_thread = None
        self.osc_mapping = {}
        self.osc_learn_target = None
        self.link_thread = None
        self.dmx_thread = None
        self.dmx_mapping = {
            1: 'intensity',
            2: 'bass',
            3: 'mid',
            4: 'brilliance',
            5: 'beat_strength',
            6: 'glitch_intensity'
        }
        self.pbo_enabled = True
        self.video_cap = None
        self.ndi_recv = None
        self.video_timer = QTimer(self)
        self.playback_offset = 0
        self.audio_data = None
        self.user_texture_path = None

        self.init_audio()
        # Create widgets that are used early but live in separate windows
        # to prevent initialization order errors.
        self.midi_combo = QComboBox()
        self.btn_midi_monitor = QPushButton("📶")
        self.osc_port_spin = QSpinBox()
        self.btn_osc_toggle = QPushButton("Start OSC")
        self.btn_record_output = QPushButton("🔴 REC OUTPUT")

        self.mask_enable_check = QCheckBox()
        self.mask_draw_btn = QPushButton()
        self.mask_clear_btn = QPushButton()
        self.mask_mode_combo = QComboBox()
        
        self.ai_enable_check = QCheckBox()
        self.ai_model_combo = QComboBox()
        self.ai_strength_spin = QDoubleSpinBox()

        self.vst_enable_check = QCheckBox()
        self.vst_plugin_combo = QComboBox()
        self.vst_mix_spin = QDoubleSpinBox()
        self.btn_rescan_vst = QPushButton()
        self.btn_vst_gui = QPushButton()
        # Utilisation du layout séparé
        self.ui = GUILayout(self)
        self.ui.setup_ui()

        # --- Injection UI Codec dans Render Settings ---
        # On récupère le layout du groupe Render Settings pour y ajouter le sélecteur
        if hasattr(self, 'group_render_settings'):
            render_layout = self.group_render_settings.layout()
            self.lbl_codec = QLabel(self.tr("label_codec"))
            self.codec_combo = QComboBox()
            self.codec_combo.addItems(["H.264 (MP4)", "ProRes 422 (MOV)", "H.265 (MP4)", "VP9 (WEBM)", "GIF (Animated)"])
            
            # Ajout dans la grille (si c'est un QGridLayout)
            if isinstance(render_layout, QGridLayout):
                row = render_layout.rowCount()
                render_layout.addWidget(self.lbl_codec, row, 0)
                render_layout.addWidget(self.codec_combo, row, 1)
                
                # Bitrate
                self.lbl_bitrate = QLabel(self.tr("label_bitrate"))
                self.bitrate_combo = QComboBox()
                self.bitrate_combo.addItems(["High Quality (CRF 18)", "5 Mbps", "10 Mbps", "20 Mbps", "50 Mbps", "100 Mbps"])
                render_layout.addWidget(self.lbl_bitrate, row+1, 0)
                render_layout.addWidget(self.bitrate_combo, row+1, 1)
                
                # Export Format
                self.lbl_format = QLabel(self.tr("label_format"))
                self.format_combo = QComboBox()
                self.format_combo.addItem("Video File", "video")
                self.format_combo.addItem("Image Sequence (PNG)", "png_seq")
                self.format_combo.addItem("Image Sequence (EXR)", "exr_seq")
                self.format_combo.currentIndexChanged.connect(self.on_export_format_changed)
                render_layout.addWidget(self.lbl_format, row+2, 0)
                render_layout.addWidget(self.format_combo, row+2, 1)
                
                # Export Audio Checkbox
                self.export_audio_check = QCheckBox("Export Audio")
                self.export_audio_check.setVisible(False)
                render_layout.addWidget(self.export_audio_check, row+3, 1)

        # Populate lang combo for state management (hidden but used for settings)
        self.lang_combo.addItem("Français", "fr")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Deutsch", "de")
        self.lang_combo.addItem("Español", "es")
        self.lang_combo.addItem("Українська", "uk")
        self.lang_combo.addItem("Ελληνικά", "el")
        self.lang_combo.addItem("עברית", "he")
        self.lang_combo.addItem("العربية", "ar")

        self.create_menu_bar()
        self.setStyleSheet(QSS_THEME)

        self.load_defaults() 
        self.retranslate_ui() 
        self.update_preview_params() 
        self.load_scenes()
        self.refresh_midi_devices()
        self.init_style_watcher()
        self.update_theme_menu()
        self.refresh_ai_models()
        
        # VST Manager
        self.vst_manager = VSTManager(logger=self.log)
        self.refresh_vst_plugins()
        self.init_undo_redo()
        
        self.init_game_controllers()
        self.controller_timer = QTimer(self)
        self.controller_timer.timeout.connect(self.poll_game_controllers)
        self.controller_timer.start(33)
        
        # Timer pour le VU-mètre (Simulation pour l'UI)
        self.vu_timer = QTimer(self)
        self.vu_timer.timeout.connect(self.update_vu_meter)
        self.vu_timer.start(30)
        
        # Timer pour la playlist
        self.playlist_timer = QTimer(self)
        self.playlist_timer.timeout.connect(self.next_playlist_item)
        
        # Timer pour le Morphing FX
        self.morph_timer = QTimer(self)
        self.morph_timer.timeout.connect(self.update_morph_step)
        self.morph_duration = 2.0
        
        # Timer pour la capture vidéo (Webcam/Fichier)
        self.video_timer.timeout.connect(self.update_video_input)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #1A1A1A; color: #DDD; }
            QMenuBar::item { padding: 5px 10px; background-color: transparent; }
            QMenuBar::item:selected { background-color: #333; }
            QMenu { background-color: #222; border: 1px solid #444; }
            QMenu::item { padding: 5px 20px; color: #DDD; }
            QMenu::item:selected { background-color: #00FF00; color: #000; }
        """)
        
        # --- 1. FILE (Fichier) ---
        file_menu = menubar.addMenu(self.tr("menu_file"))
        
        # Media
        act = file_menu.addAction(self.tr("action_open_audio"), self.browse_audio)
        act.setToolTip("Ouvre un fichier audio pour l'analyse et la génération.")
        act = file_menu.addAction(self.tr("action_open_video"), self.browse_video_input)
        act.setToolTip("Utilise une webcam ou un fichier vidéo comme source.")
        file_menu.addSeparator()
        
        # 3D & Assets
        act = file_menu.addAction(self.tr("action_load_model"), self.browse_3d_model)
        act.setToolTip("Importe un modèle 3D au format .OBJ.")
        act = file_menu.addAction(self.tr("action_load_texture"), self.browse_user_texture)
        act.setToolTip("Applique une image personnalisée sur le modèle 3D.")
        act = file_menu.addAction(self.tr("action_clear_texture"), self.clear_user_texture)
        act.setToolTip("Retire la texture personnalisée du modèle.")
        act = file_menu.addAction(self.tr("action_gen_assets"), self.generate_assets)
        act.setToolTip("Génère des formes 3D de base dans le dossier assets.")
        file_menu.addSeparator()
        
        # Playlist
        playlist_menu = file_menu.addMenu("Playlist")
        playlist_menu.setToolTip("Gestion de la liste de lecture des scènes.")
        act = playlist_menu.addAction(self.tr("action_load_playlist"), self.load_playlist)
        act.setToolTip("Charge une séquence de scènes depuis un fichier JSON.")
        act = playlist_menu.addAction(self.tr("action_save_playlist"), self.save_playlist)
        act.setToolTip("Sauvegarde la séquence actuelle.")
        act = playlist_menu.addAction(self.tr("action_export_playlist"), self.export_playlist)
        act.setToolTip("Rend la playlist complète en une seule vidéo.")
        file_menu.addSeparator()
        
        # Presets
        preset_menu = file_menu.addMenu("Presets")
        act = preset_menu.addAction(self.tr("action_load_preset"), lambda: self.load_preset(self.preset_combo.currentText()))
        act.setToolTip("Charge les paramètres du preset sélectionné.")
        act = preset_menu.addAction(self.tr("action_save_preset"), self.save_preset)
        act.setToolTip("Enregistre les paramètres actuels comme nouveau preset.")
        file_menu.addSeparator()
        
        # System
        act = file_menu.addAction(self.tr("action_save_defaults"), self.save_defaults)
        act.setToolTip("Définit la configuration actuelle comme démarrage par défaut.")
        file_menu.addSeparator()
        act = file_menu.addAction(self.tr("action_exit"), self.close)
        act.setToolTip("Ferme l'application.")
        
        # --- 2. EDIT (Édition) ---
        edit_menu = menubar.addMenu(self.tr("menu_edit"))
        
        self.action_undo = edit_menu.addAction(self.tr("action_undo"), self.undo)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.setEnabled(False)
        
        self.action_redo = edit_menu.addAction(self.tr("action_redo"), self.redo)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.setEnabled(False)
        
        edit_menu.addSeparator()
        act = edit_menu.addAction(self.tr("action_random_fx"), self.randomize_fx_params)
        act.setToolTip("Aléatorise uniquement les curseurs d'effets.")
        act = edit_menu.addAction(self.tr("action_random_all"), self.randomize_all_params)
        act.setToolTip("Aléatorise le style visuel ET les effets.")
        act = edit_menu.addAction(self.tr("action_reset_fx"), self.reset_fx_params)
        act.setToolTip("Remet tous les effets à zéro.")
        edit_menu.addSeparator()
        act = edit_menu.addAction(self.tr("action_config_random"), self.open_randomize_settings)
        act.setToolTip("Choisit quels effets inclure dans l'aléatoire.")
        edit_menu.addSeparator()
        
        self.action_rec_macro = edit_menu.addAction(self.tr("action_rec_macro"))
        self.action_rec_macro.setCheckable(True)
        self.action_rec_macro.setToolTip("Enregistre vos actions pour les rejouer au rendu.")
        self.action_rec_macro.triggered.connect(self.toggle_macro_recording)
        if hasattr(self, 'btn_rec_macro'):
            self.btn_rec_macro.toggled.connect(self.action_rec_macro.setChecked)
        
        # --- 3. VIEW (Affichage) ---
        view_menu = menubar.addMenu(self.tr("menu_view"))
        
        # Windows Submenu
        win_menu = view_menu.addMenu("Windows")
        act = win_menu.addAction(self.tr("action_mixer_win"), lambda: self.toggle_dock("dock_mixer"))
        act.setToolTip("Affiche/Masque la fenêtre principale des contrôles.")
        act = win_menu.addAction(self.tr("action_perf_win"), self.toggle_performance_view)
        act.setToolTip("Ouvre une fenêtre de prévisualisation sans interface.")
        act = win_menu.addAction(self.tr("action_seq_win"), self.toggle_sequencer_window)
        act.setToolTip("Ouvre l'éditeur de playlist et scènes.")
        act = win_menu.addAction(self.tr("action_conn_win"), self.toggle_connectivity_window)
        act.setToolTip("Gère MIDI, OSC, Spout et NDI.")
        act = win_menu.addAction(self.tr("action_midi_mon"), self.toggle_midi_monitor)
        act.setToolTip("Affiche les signaux MIDI entrants.")
        
        # Editors Submenu
        editors_menu = view_menu.addMenu("Editors")
        act = editors_menu.addAction(self.tr("action_shader_editor"), self.toggle_shader_editor)
        act.setToolTip("Modifie le code GLSL du style actuel.")
        act = editors_menu.addAction(self.tr("action_node_editor"), lambda: self.toggle_dock("dock_node_editor"))
        act.setToolTip("Éditeur nodal pour créer des pipelines d'effets.")
        act = editors_menu.addAction(self.tr("action_timeline"), lambda: self.toggle_dock("dock_timeline"))
        act.setToolTip("Éditeur non-linéaire pour séquencer les clips.")
        
        view_menu.addSeparator()
        
        # Layout Submenu
        layout_menu = view_menu.addMenu("Layout")
        self.action_lock_layout = layout_menu.addAction(self.tr("action_lock_docks"))
        self.action_lock_layout.setCheckable(True)
        self.action_lock_layout.toggled.connect(self.toggle_lock_docks)
        self.action_lock_layout.setToolTip("Verrouille la position des fenêtres.")
        
        self.action_auto_save_layout = layout_menu.addAction(self.tr("action_auto_save_layout"))
        self.action_auto_save_layout.setCheckable(True)
        self.action_auto_save_layout.setToolTip("Sauvegarde automatiquement la disposition en quittant.")
        
        act = layout_menu.addAction(self.tr("action_save_layout"), self.save_layout)
        act.setToolTip("Sauvegarde la position des fenêtres.")
        act = layout_menu.addAction(self.tr("action_reset_layout"), self.reset_layout)
        act.setToolTip("Restaure la disposition par défaut.")
        self.workspaces_menu = layout_menu.addMenu(self.tr("menu_workspaces"))
        self.workspaces_menu.aboutToShow.connect(self.populate_workspaces_menu)
        
        view_menu.addSeparator()
        act = view_menu.addAction(self.tr("action_fullscreen"), self.toggle_fullscreen)
        act.setToolTip("Bascule en mode plein écran (F11).")
        act = view_menu.addAction(self.tr("action_presentation"), self.toggle_presentation_mode)
        act.setToolTip("Masque les menus pour une présentation propre.")

        # --- 4. 3D (Nouveau) ---
        threed_menu = menubar.addMenu("3D")
        
        # Settings
        self.action_auto_center = threed_menu.addAction("Auto-Center Model")
        self.action_auto_center.setCheckable(True)
        self.action_auto_center.setToolTip("Centre automatiquement le modèle à l'import.")
        self.action_auto_center.triggered.connect(self.toggle_auto_center)

        self.action_auto_normalize = threed_menu.addAction("Auto-Normalize Scale")
        self.action_auto_normalize.setCheckable(True)
        self.action_auto_normalize.setToolTip("Ajuste la taille du modèle pour qu'il tienne dans la vue.")
        self.action_auto_normalize.triggered.connect(self.toggle_auto_normalize)
        
        threed_menu.addSeparator()
        
        # Display
        self.action_wireframe = threed_menu.addAction("Wireframe Mode")
        self.action_wireframe.setCheckable(True)
        self.action_wireframe.setToolTip("Affiche le modèle en fil de fer.")
        self.action_wireframe.triggered.connect(self.toggle_wireframe)
        
        self.action_show_normals = threed_menu.addAction("Show Vertex Normals")
        self.action_show_normals.setCheckable(True)
        self.action_show_normals.setToolTip("Affiche les normales des sommets (Debug).")
        self.action_show_normals.triggered.connect(self.toggle_show_normals)
        
        self.action_set_normal_len = threed_menu.addAction("Set Normal Length...")
        self.action_set_normal_len.setToolTip("Définit la longueur des lignes de normales.")
        self.action_set_normal_len.triggered.connect(self.set_normal_length)
        
        self.action_show_bbox = threed_menu.addAction("Show Bounding Box")
        self.action_show_bbox.setCheckable(True)
        self.action_show_bbox.setToolTip("Affiche la boîte englobante du modèle.")
        self.action_show_bbox.triggered.connect(self.toggle_show_bbox)
        
        # --- 5. PLAYBACK (Lecture) ---
        play_menu = menubar.addMenu(self.tr("menu_playback"))
        act = play_menu.addAction(self.tr("action_play_pause"), lambda: self.pause_audio(False))
        act.setToolTip("Lance ou met en pause la lecture.")
        act = play_menu.addAction(self.tr("action_stop"), self.stop_audio)
        act.setToolTip("Arrête la lecture et revient au début.")
        
        self.action_loop = play_menu.addAction(self.tr("action_loop"))
        self.action_loop.setCheckable(True)
        self.action_loop.setToolTip("Répète la lecture en boucle.")
        self.action_loop.triggered.connect(lambda c: self.btn_loop.setChecked(c))
        if hasattr(self, 'btn_loop'):
            self.btn_loop.toggled.connect(self.action_loop.setChecked)

        # --- 6. RENDER (Rendu) ---
        render_menu = menubar.addMenu(self.tr("menu_render"))
        act = render_menu.addAction(self.tr("action_start_render"), self.start_render)
        act.setToolTip("Lance le rendu final du projet.")
        act = render_menu.addAction(self.tr("action_preview"), self.start_preview)
        act.setToolTip("Génère un aperçu rapide de 5 secondes.")
        
        # --- 7. TOOLS (Outils) ---
        tools_menu = menubar.addMenu(self.tr("menu_tools"))
        act = tools_menu.addAction(self.tr("action_fft_config"), self.open_fft_config)
        act.setToolTip("Configure les bandes de fréquences pour l'analyse audio.")
        act = tools_menu.addAction(self.tr("action_dmx_map"), self.open_dmx_mapping)
        act.setToolTip("Assigne les canaux DMX aux paramètres audio.")
        act = tools_menu.addAction(self.tr("action_favorites"), self.manage_favorites)
        act.setToolTip("Gère la liste des styles favoris.")
        tools_menu.addSeparator()
        
        gamepad_menu = tools_menu.addMenu("Gamepad")
        self.action_invert_y = gamepad_menu.addAction("Invert Y Axis")
        self.action_invert_y.setCheckable(True)
        self.action_invert_y.setToolTip("Inverse l'axe vertical des joysticks.")
        self.action_invert_y.triggered.connect(self.toggle_invert_y)
        
        self.action_button_hold = gamepad_menu.addAction("Button Mode: Hold (vs Toggle)")
        self.action_button_hold.setCheckable(True)
        self.action_button_hold.setToolTip("Maintenir pour activer (Hold) ou appuyer pour basculer (Toggle).")
        self.action_button_hold.triggered.connect(self.toggle_button_hold_mode)
        
        self.action_deadzone = gamepad_menu.addAction("Set Deadzone...")
        self.action_deadzone.setToolTip("Définit la zone morte des joysticks.")
        self.action_deadzone.triggered.connect(self.set_controller_deadzone)

        self.action_calibrate = gamepad_menu.addAction("Calibrate Axes (Start/Stop)")
        self.action_calibrate.setCheckable(True)
        self.action_calibrate.setToolTip("Lance l'assistant de calibration des manettes.")
        self.action_calibrate.triggered.connect(self.toggle_axis_calibration)
        
        # --- 8. THEME (Thème) ---
        theme_menu = tools_menu.addMenu(self.tr("menu_theme"))
        theme_menu.addAction(self.tr("action_theme_neon"), self.apply_neon_theme)
        theme_menu.addAction(self.tr("action_theme_dark"), self.apply_dark_theme)
        theme_menu.addAction(self.tr("action_theme_custom"), self.choose_border_color)
        theme_menu.addSeparator()
        theme_menu.addAction(self.tr("action_save_theme"), self.save_theme_preset)
        
        self.custom_themes_menu = theme_menu.addMenu(self.tr("menu_load_theme"))
        self.custom_themes_menu.aboutToShow.connect(self.populate_custom_themes_menu)
        
        # --- 9. LANGUAGE (Langue) ---
        self.lang_menu = menubar.addMenu(self.tr("menu_language"))
        self.lang_menu.addAction("Français", lambda: self.set_language('fr'))
        self.lang_menu.addAction("English", lambda: self.set_language('en'))
        self.lang_menu.addAction("Deutsch", lambda: self.set_language('de'))
        self.lang_menu.addAction("Español", lambda: self.set_language('es'))
        self.lang_menu.addAction("Українська", lambda: self.set_language('uk'))
        self.lang_menu.addAction("Ελληνικά", lambda: self.set_language('el'))
        self.lang_menu.addAction("עברית", lambda: self.set_language('he'))
        self.lang_menu.addAction("العربية", lambda: self.set_language('ar'))
        
        # --- 10. HELP (Aide) ---
        help_menu = menubar.addMenu(self.tr("menu_help"))
        act = help_menu.addAction(self.tr("action_docs"), lambda: webbrowser.open("https://github.com/Patrick/MusicVideoGen"))
        act.setToolTip("Ouvre la documentation en ligne.")
        act = help_menu.addAction(self.tr("action_about"), self.show_about)
        act.setToolTip("Affiche les informations sur l'application.")

    def set_language(self, lang_code):
        if lang_code != self.current_lang:
            self.current_lang = lang_code
            self.menuBar().clear()
            self.create_menu_bar()
            self.retranslate_ui()
            idx = self.lang_combo.findData(lang_code)
            if idx != -1: self.lang_combo.setCurrentIndex(idx)

    def toggle_auto_center(self, checked):
        self.preview_widget.auto_center_model = checked
        state = "activé" if checked else "désactivé"
        self.log(f"🎯 Auto-Center {state} pour les prochains chargements.")

    def toggle_auto_normalize(self, checked):
        self.preview_widget.auto_normalize_model = checked
        state = "activé" if checked else "désactivé"
        self.log(f"📏 Auto-Normalize {state} pour les prochains chargements.")

    def toggle_show_normals(self, checked):
        self.preview_widget.show_normals = checked
        self.preview_widget.update()

    def toggle_show_bbox(self, checked):
        self.preview_widget.show_bbox = checked
        self.preview_widget.update()

    def toggle_wireframe(self, checked):
        self.preview_widget.model_wireframe = checked
        self.preview_widget.update()

    def set_normal_length(self):
        val, ok = QInputDialog.getDouble(self, "Normal Length", "Length:", self.preview_widget.normal_length, 0.01, 5.0, 2)
        if ok:
            self.preview_widget.normal_length = val
            self.preview_widget.update()

    def populate_custom_themes_menu(self):
        self.custom_themes_menu.clear()
        if not self.custom_themes:
            self.custom_themes_menu.addAction("No custom themes").setEnabled(False)
            return
        
        for name in self.custom_themes:
            self.custom_themes_menu.addAction(name, lambda n=name: self.load_custom_theme(n))

    def populate_workspaces_menu(self):
        self.workspaces_menu.clear()
        self.workspaces_menu.addAction(self.tr("action_save_workspace_as"), self.save_workspace_dialog)
        self.workspaces_menu.addSeparator()
        
        workspaces = getattr(self, 'workspaces', {})
        if workspaces:
            for name in workspaces:
                self.workspaces_menu.addAction(name, lambda n=name: self.load_workspace(n))
            
            self.workspaces_menu.addSeparator()
            del_menu = self.workspaces_menu.addMenu(self.tr("menu_delete_workspace"))
            for name in workspaces:
                del_menu.addAction(name, lambda n=name: self.delete_workspace(n))
        else:
            self.workspaces_menu.addAction(self.tr("label_no_workspaces")).setEnabled(False)

    def save_workspace_dialog(self):
        name, ok = QInputDialog.getText(self, self.tr("dialog_save_workspace"), self.tr("dialog_workspace_name"))
        if ok and name:
            self.save_workspace(name)

    def open_randomize_settings(self):
        # This list should be maintained to match randomize_fx_params
        all_effects = [
            "bloom_spin", "aberration_spin", "grain_spin", "vignette_spin", "contrast_spin", 
            "saturation_spin", "brightness_spin", "gamma_spin", "glitch_spin", "scanline_spin", 
            "strobe_spin", "light_leak_spin", "mirror_spin", "pixelate_spin", "posterize_spin", 
            "solarize_spin", "hue_shift_spin", "invert_spin", "sepia_spin", "thermal_spin", 
            "edge_spin", "fisheye_spin", "twist_spin", "ripple_spin", "mirror_quad_spin", 
            "rgb_split_spin", "bleach_spin", "vhs_spin", "neon_spin", "cartoon_spin", 
            "sketch_spin", "vibrate_spin", "drunk_spin", "pinch_spin", "zoom_blur_spin", 
            "aura_spin", "psycho_spin"
        ]
        
        dialog = RandomizeExclusionsDialog(all_effects, self.randomize_exclusions, self)
        if dialog.exec():
            self.randomize_exclusions = dialog.get_excluded_effects()
            self.log(f"⚙️ Randomization exclusions updated: {len(self.randomize_exclusions)} effects excluded.")

    def center(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.log("💤 Mode Idle activé (Minimisé)")
                self.set_idle_mode(True)
            elif event.oldState() & Qt.WindowState.WindowMinimized:
                self.log("⚡ Mode Actif restauré")
                self.set_idle_mode(False)
        super().changeEvent(event)

    def set_idle_mode(self, is_idle):
        if is_idle:
            self.vu_timer.stop()
            self.video_timer.stop()
            self.preview_widget.set_render_active(False)
            if self.performance_window:
                self.performance_window.preview_widget.set_render_active(False)
        else:
            self.vu_timer.start(30)
            if self.video_cap or self.ndi_recv:
                self.video_timer.start(33)
            self.preview_widget.set_render_active(True)
            if self.performance_window:
                self.performance_window.preview_widget.set_render_active(True)

    def closeEvent(self, event):
        self.save_ui_state()
        event.accept()
        if self.video_cap: self.video_cap.release()
        if self.osc_thread: self.osc_thread.stop()
        if self.link_thread: self.link_thread.stop()
        if self.dmx_thread: self.dmx_thread.stop()

    def tr(self, key, **kwargs):
        return TRANSLATIONS[self.current_lang].get(key, key).format(**kwargs)

    def panic(self):
        """Stops all playback and resets all effects to default."""
        self.log("🚨 PANIC! Resetting all systems to default.")
        
        # Stop audio and timers
        self.stop_audio()
        self.stop_playlist()
        if self.morph_timer.isActive():
            self.morph_timer.stop()
            self.log("🌊 Morphing FX stopped.")

    def toggle_output_recording(self, checked):
        if checked:
            path, _ = QFileDialog.getSaveFileName(self, "Enregistrer Sortie", "", "Video Files (*.mp4)")
            if path:
                self.preview_widget.toggle_recording(path)
                self.btn_record_output.setStyleSheet("background-color: #FF0000; color: #FFFFFF; font-weight: bold; border: 2px solid #FFFFFF;")
            else:
                self.btn_record_output.setChecked(False)
        else:
            self.preview_widget.toggle_recording(None)
            self.btn_record_output.setStyleSheet("background-color: #440000; color: #FF0000; font-weight: bold;")

    def change_output_mode(self, mode_text):
        self.preview_widget.set_output_mode(mode_text)
        if self.performance_window:
            self.performance_window.preview_widget.set_output_mode(mode_text)
            
    def update_vu_meter(self):
        l_level = 0.0
        r_level = 0.0
        
        if self.analyzer:
            if self.is_playing and self.audio_loaded:
                try:
                    pos = pygame.mixer.music.get_pos()
                    if pos != -1:
                        current_time = (pos + self.playback_offset) / 1000.0
                        features = self.analyzer.get_features_at_time(current_time)
                        l_level = features.intensity
                        r_level = features.intensity
                        
                        # Goniometer & Real Clipping
                        if self.audio_data is not None and self.audio_data.ndim == 2:
                            # sr=22050 from loader
                            idx = int(current_time * 22050)
                            chunk = self.audio_data[:, idx:idx+1024]
                            if chunk.shape[1] > 0:
                                self.goniometer.set_samples(chunk)
                                # Optional: Use real peak from chunk for VU
                        
                        # DMX Output
                        if self.dmx_thread:
                            for channel, feature_name in self.dmx_mapping.items():
                                if hasattr(features, feature_name):
                                    val = getattr(features, feature_name)
                                    if isinstance(val, (int, float)):
                                        self.dmx_thread.set_channel(int(channel), val * 255)
                except Exception:
                    pass
        else:
            # Simulation d'un signal audio basé sur le temps pour l'interface
            t = time.time()
            beat = (np.sin(t * 10) + 1) * 0.5
            noise = np.random.random() * 0.2
            l_level = beat * 0.8 + noise
            r_level = beat * 0.7 + noise
            
        self.vu_meter.set_levels(l_level, r_level)
        if hasattr(self, 'vu_meter_left'):
            self.vu_meter_left.set_levels(l_level, r_level)

    def choose_border_color(self):
        color = QColorDialog.getColor(QColor(self.module_border_color), self, "UI Border Color")
        if color.isValid():
            self.module_border_color = color.name()
            self.update_module_theme()

    def update_module_theme(self):
        for widget in self.findChildren(BaseModule):
            widget.set_border_color(self.module_border_color)
        self.btn_border_color.setStyleSheet(f"border: 1px solid {self.module_border_color}; color: {self.module_border_color};")

    def apply_neon_theme(self):
        self.module_border_color = "#00FFFF"
        self.update_module_theme()
        self.ui_theme = "Neon"
        
        neon_qss = """
            QMainWindow { background-color: #050505; color: #00FFFF; }
            QLabel { color: #00FFFF; }
            QGroupBox { border: 1px solid #00FFFF; margin-top: 10px; }
            QGroupBox::title { color: #00FFFF; }
            QPushButton { 
                background-color: #002222; 
                color: #00FFFF; 
                border: 1px solid #00FFFF; 
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover { 
                background-color: #004444; 
                border: 1px solid #FFFFFF;
                color: #FFFFFF;
            }
            QPushButton:pressed { background-color: #00FFFF; color: #000000; }
            
            QSlider::groove:vertical {
                background: #002222;
                width: 6px;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #00FFFF;
                height: 10px;
                margin: 0 -4px;
                border-radius: 5px;
            }
            QSlider::add-page:vertical { background: #00FFFF; }
            
            QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
                background-color: #001111;
                color: #00FFFF;
                border: 1px solid #005555;
            }
            QCheckBox { color: #00FFFF; }
            QCheckBox::indicator:checked { background-color: #00FFFF; border: 1px solid #00FFFF; }
            QCheckBox::indicator:unchecked { background-color: #000000; border: 1px solid #005555; }
        """
        self.setStyleSheet(neon_qss)
        self.log("🎨 Thème Neon activé !")

    def apply_dark_theme(self):
        self.module_border_color = "#333"
        self.update_module_theme()
        self.ui_theme = "Dark"
        self.setStyleSheet(QSS_THEME)
        self.log("🌑 Thème Sombre (Défaut) activé.")

    def update_theme_menu(self):
        menu = QMenu(self.btn_border_color)
        menu.addAction("Custom Border Color...", self.choose_border_color)
        menu.addAction("Neon Theme", self.apply_neon_theme)
        menu.addAction("Dark Theme (Default)", self.apply_dark_theme)
        
        menu.addSeparator()
        if self.custom_themes:
            for name in self.custom_themes:
                menu.addAction(f"Load: {name}", lambda n=name: self.load_custom_theme(n))
            menu.addSeparator()
            
        menu.addAction("Save Theme As...", self.save_theme_preset)
        self.btn_border_color.setMenu(menu)

    def save_theme_preset(self):
        name, ok = QInputDialog.getText(self, self.tr("dialog_save_theme"), self.tr("dialog_theme_name"))
        if ok and name:
            self.custom_themes[name] = {
                'border_color': self.module_border_color,
                'base_theme': getattr(self, 'ui_theme', 'Dark')
            }
            self.save_ui_state()
            self.update_theme_menu()
            self.log(f"💾 Thème sauvegardé: {name}")

    def load_custom_theme(self, name):
        if name in self.custom_themes:
            data = self.custom_themes[name]
            base = data.get('base_theme', 'Dark')
            if base == 'Neon': self.apply_neon_theme()
            else: self.apply_dark_theme()
            
            self.module_border_color = data.get('border_color', '#333')
            self.update_module_theme()
            self.log(f"🎨 Thème chargé: {name}")

    def check_updates(self):
        self.update_thread = UpdateCheckerThread()
        self.update_thread.update_available.connect(self.show_update_dialog)
        self.update_thread.start()

    def manage_favorites(self):
        dialog = FavoritesDialog(self.available_styles, self.favorite_styles, self)
        if dialog.exec():
            selected = dialog.get_selected()
            if selected:
                self.favorite_styles = selected
            else:
                QMessageBox.warning(self, self.tr("warn_no_favorites_title"), self.tr("warn_no_favorites_text"))

    def open_fft_config(self):
        dialog = FFTConfigDialog(self)
        if dialog.exec():
            dialog.apply_changes()
            self.log("🎚️ Bandes de fréquences FFT mises à jour.")

    def toggle_pbo_usage(self, checked):
        self.pbo_enabled = checked
        self.log(f"⚙️ Asynchronous Readback (PBO) {'activé' if checked else 'désactivé'}.")
        if not checked:
            self.log("⚠️ Désactiver PBO peut sévèrement réduire les performances d'enregistrement/export.")
        # The main renderer is created in the export thread, so we just need
        # to pass the parameter. No direct object to call here.


    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return

        key = event.key()
        
        # F11: Toggle Fullscreen
        if key == Qt.Key.Key_Escape:
            self.panic()
            event.accept()
            return

        if key == Qt.Key.Key_F11: 
            self.toggle_fullscreen()
        
        # Ctrl+M: Toggle Maximized
        elif key == Qt.Key.Key_M and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()
        
        # 1-8: Quick Presets
        elif Qt.Key.Key_1 <= key <= Qt.Key.Key_8:
            idx = key - Qt.Key.Key_1
            btn = getattr(self, f"btn_quick_{idx}", None)
            if btn:
                btn.setChecked(True)
            self.activate_quick_preset(idx)
            
        # Espace: Strobe (Momentané)
        elif key == Qt.Key.Key_Space:
            self.strobe_spin.setValue(1.0)
            
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return

        if event.key() == Qt.Key.Key_Space:
            self.strobe_spin.setValue(0.0)
        else:
            super().keyReleaseEvent(event)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.menuBar().show()
            self.statusBar().show()
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_presentation_mode(self):
        self.menuBar().hide()
        self.statusBar().hide()
        self.showFullScreen()
        self.log("📺 Mode Présentation activé (F11 pour quitter)")

    def reset_layout(self):
        reply = QMessageBox.question(self, self.tr("action_reset_layout"), 
                                     self.tr("confirm_reset_layout_text"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        self.showNormal()
        self.resize(1280, 850)
        self.center()
        
        # Réinitialiser la visibilité des docks
        if hasattr(self, 'docks'):
            for dock in self.docks.values():
                dock.show()
                dock.setFloating(False)
        
        if self.performance_window: self.performance_window.close()
        if self.sequencer_window: self.sequencer_window.close()
        if self.connectivity_window: self.connectivity_window.close()
        if self.shader_editor_window: self.shader_editor_window.close()
        if self.midi_debug_window: self.midi_debug_window.close()
        
        self.log("🖥️ Disposition réinitialisée.")

    def change_language(self):
        new_lang = self.lang_combo.currentData()
        if new_lang != self.current_lang:
            self.current_lang = new_lang
            self.retranslate_ui()

    def toggle_all_groups(self, group_list, state):
        for group in group_list:
            group.setChecked(state)

    def _setup_collapsible_group(self, group):
        if group.layout() and group.layout().count() > 0:
            container = group.layout().itemAt(0).widget()
            if container:
                container.setVisible(group.isChecked())
                group.toggled.connect(container.setVisible)

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("window_title"))
        self.lbl_preset.setText(self.tr("toolbar_preset"))
        self.btn_save_preset.setText(self.tr("toolbar_save"))
        self.btn_preview.setText(self.tr("toolbar_preview"))
        self.tabs.setTabText(0, self.tr("tab_general"))
        self.tabs.setTabText(1, self.tr("tab_fx_studio"))
        self.tabs.setTabText(2, self.tr("tab_overlays"))
        self.tabs.setTabText(3, self.tr("tab_about"))
        
        self.btn_expand_general.setText(self.tr("button_expand_all"))
        self.btn_collapse_general.setText(self.tr("button_collapse_all"))
        self.btn_expand_fx.setText(self.tr("button_expand_all"))
        self.btn_collapse_fx.setText(self.tr("button_collapse_all"))
        self.btn_expand_ov.setText(self.tr("button_expand_all"))
        self.btn_collapse_ov.setText(self.tr("button_collapse_all"))
        
        self.group_file.setTitle(self.tr("group_source_dest"))
        self.lbl_mode.setText(self.tr("label_mode"))
        self.mode_combo.setItemText(0, self.tr("mode_render_video"))
        self.mode_combo.setItemText(1, self.tr("mode_realtime_visualizer"))
        self.batch_check.setText(self.tr("checkbox_batch_mode"))
        self.btn_audio.setText(self.tr("button_browse"))
        self.group_info.setTitle(self.tr("group_info"))
        self.title_input.setPlaceholderText(self.tr("placeholder_info_title"))
        self.artist_input.setPlaceholderText(self.tr("placeholder_info_artist"))
        self.lbl_title.setText(self.tr("label_info_title"))
        self.lbl_artist.setText(self.tr("label_info_artist"))
        self.group_render_settings.setTitle(self.tr("group_render_settings"))
        self.lbl_resolution.setText(self.tr("label_resolution"))
        self.btn_swap_res.setToolTip(self.tr("tooltip_swap_resolution"))
        self.lbl_fps.setText(self.tr("label_fps"))
        self.fps_spin.setSuffix(" FPS")
        self.lbl_audio_preset.setText(self.tr("label_audio_preset"))
        if hasattr(self, 'lbl_codec'): self.lbl_codec.setText(self.tr("label_codec"))
        if hasattr(self, 'lbl_bitrate'): self.lbl_bitrate.setText(self.tr("label_bitrate"))
        if hasattr(self, 'lbl_format'): self.lbl_format.setText(self.tr("label_format"))
        self.audio_preset_combo.clear()
        self.audio_preset_combo.addItems(["Flat", "Bass Boost", "Vocal Boost"]) 
        self.btn_save_defaults.setText(self.tr("button_save_as_default"))
        self.style_group.setTitle(self.tr("group_visual_style"))
        self.style_combo.setItemText(0, self.tr("style_autodetect"))
        self.btn_fav.setText(self.tr("button_favorites"))
        self.light_fx_group.setTitle(self.tr("group_fx_light"))
        self.lbl_bloom.setText(self.tr("label_bloom"))
        self.bloom_spin.setToolTip(self.tr("tooltip_bloom"))
        self.lbl_brightness.setText(self.tr("label_brightness"))
        self.brightness_spin.setToolTip(self.tr("tooltip_brightness"))
        self.lbl_gamma.setText(self.tr("label_gamma"))
        self.gamma_spin.setToolTip(self.tr("tooltip_gamma"))
        self.lbl_exposure.setText(self.tr("label_exposure"))
        self.exposure_spin.setToolTip(self.tr("tooltip_exposure"))
        self.lbl_strobe.setText(self.tr("label_strobe"))
        self.strobe_spin.setToolTip(self.tr("tooltip_strobe"))
        self.lbl_light_leak.setText(self.tr("label_light_leak"))
        self.light_leak_spin.setToolTip(self.tr("tooltip_light_leak"))
        self.optics_fx_group.setTitle(self.tr("group_fx_optics"))
        self.lbl_aberration.setText(self.tr("label_aberration"))
        self.aberration_spin.setToolTip(self.tr("tooltip_aberration"))
        self.lbl_grain.setText(self.tr("label_grain"))
        self.grain_spin.setToolTip(self.tr("tooltip_grain"))
        self.lbl_vignette.setText(self.tr("label_vignette"))
        self.vignette_spin.setToolTip(self.tr("tooltip_vignette"))
        self.lbl_scanlines.setText(self.tr("label_scanlines"))
        self.scanline_spin.setToolTip(self.tr("tooltip_scanlines"))
        self.lbl_mirror.setText(self.tr("label_mirror"))
        self.mirror_spin.setToolTip(self.tr("tooltip_mirror"))
        self.color_fx_group.setTitle(self.tr("group_fx_color"))
        self.lbl_contrast.setText(self.tr("label_contrast"))
        self.contrast_spin.setToolTip(self.tr("tooltip_contrast"))
        self.lbl_saturation.setText(self.tr("label_saturation"))
        self.saturation_spin.setToolTip(self.tr("tooltip_saturation"))
        self.glitch_fx_group.setTitle(self.tr("group_fx_glitch"))
        self.lbl_glitch.setText(self.tr("label_glitch"))
        self.glitch_spin.setToolTip(self.tr("tooltip_glitch"))
        self.fx_options_group.setTitle(self.tr("group_fx_options"))
        self.dynamic_style_check.setText(self.tr("checkbox_dynamic_style"))
        self.preview_check.setText(self.tr("checkbox_show_preview"))
        self.btn_reset_fx.setText(self.tr("button_reset_fx"))
        self.btn_random_fx.setText(self.tr("button_randomize_fx"))
        self.btn_morph_fx.setText(self.tr("button_morph_fx"))
        self.scroller_group.setTitle(self.tr("group_scroller"))
        self.lbl_font.setText(self.tr("label_font"))
        self.btn_scroller_color.setText(self.tr("button_color"))
        self.lbl_effect.setText(self.tr("label_effect"))
        self.overlays_group.setTitle(self.tr("group_overlays"))
        self.spectrogram_check.setText(self.tr("checkbox_spectrogram"))
        self.btn_spec_color.setText(self.tr("button_bg_color"))
        self.spec_pos_combo.clear()
        self.spec_pos_combo.addItems([self.tr("position_bottom"), self.tr("position_top")])
        self.logo_input.setPlaceholderText(self.tr("placeholder_logo"))
        self.lbl_lyrics.setText(self.tr("label_lyrics"))
        self.srt_input.setPlaceholderText(self.tr("placeholder_srt"))
        self.json_check.setText(self.tr("checkbox_save_json"))
        self.toggle_mode(self.mode_combo.currentIndex()) 
        self.toggle_batch_mode(self.batch_check.isChecked()) 
        self.update_preset_combo()
        self.about_content.findChild(QLabel, "title").setText(self.tr("about_title"))
        self.about_content.findChild(QLabel, "version").setText(self.tr("about_version", version=CURRENT_VERSION))
        self.about_content.findChild(QLabel, "desc").setText(self.tr("about_desc"))
        self.about_content.findChild(QPushButton, "website").setText(self.tr("about_website"))
        self.about_content.findChild(QPushButton, "soundcloud").setText(self.tr("about_soundcloud"))
        
        if self.about_dialog:
            self.about_dialog.setWindowTitle(self.tr("about_title"))
            self.about_dialog.lbl_title.setText(self.tr("about_title"))
            self.about_dialog.lbl_version.setText(self.tr("about_version", version=CURRENT_VERSION))
            self.about_dialog.lbl_desc.setText(self.tr("about_desc"))
            self.about_dialog.btn_website.setText(self.tr("about_website"))
            self.about_dialog.btn_soundcloud.setText(self.tr("about_soundcloud"))
        
        # New modules
        if hasattr(self, 'docks') and 'dock_mask' in self.docks:
            self.docks['dock_mask'].setWindowTitle(self.tr("module_masking"))
        if hasattr(self, 'docks') and 'dock_ai' in self.docks:
            self.docks['dock_ai'].setWindowTitle(self.tr("module_ai_style"))
        if hasattr(self, 'docks') and 'dock_vst' in self.docks:
            self.docks['dock_vst'].setWindowTitle(self.tr("module_vst"))

    def set_mask_mode(self, mode):
        self.preview_widget.set_mask_mode(mode)
        if self.performance_window:
            self.performance_window.preview_widget.set_mask_mode(mode)

    def toggle_mask_enabled(self, checked):
        self.preview_widget.set_mask_enabled(checked)
        if self.performance_window:
            self.performance_window.preview_widget.set_mask_enabled(checked)

    def toggle_mask_drawing(self, checked):
        self.preview_widget.set_mask_drawing_mode(checked)

    def clear_mask(self):
        self.preview_widget.clear_mask()

    def refresh_ai_models(self):
        self.ai_model_combo.clear()
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style_models")
        if not os.path.exists(assets_dir):
            try:
                os.makedirs(assets_dir)
            except: pass
            
        if os.path.exists(assets_dir):
            models = [f for f in os.listdir(assets_dir) if f.endswith(('.t7', '.onnx', '.pb'))]
            self.ai_model_combo.addItems(models)
        
        if self.ai_model_combo.count() == 0:
            self.ai_model_combo.addItem("No models found in assets/style_models")

    def refresh_vst_plugins(self):
        self.vst_plugin_combo.clear()
        plugins = self.vst_manager.scan_plugins()
        self.vst_plugin_combo.addItems(list(plugins.keys()))
        if not plugins:
            self.vst_plugin_combo.addItem("No VST plugins found")

    def open_vst_gui(self):
        self.vst_manager.open_editor()

    def get_render_params(self):
        """Surcharge pour inclure le codec sélectionné"""
        params = super().get_render_params()
        params['codec'] = self.codec_combo.currentText() if hasattr(self, 'codec_combo') else "H.264 (MP4)"
        params['bitrate'] = self.bitrate_combo.currentText() if hasattr(self, 'bitrate_combo') else "High Quality (CRF 18)"
        params['export_format'] = self.format_combo.currentData() if hasattr(self, 'format_combo') else "video"
        return params

    def on_export_format_changed(self, index):
        fmt = self.format_combo.currentData()
        is_video = (fmt == "video")
        
        # Désactiver les options vidéo si on exporte des images
        if hasattr(self, 'bitrate_combo'): self.bitrate_combo.setEnabled(is_video)
        if hasattr(self, 'codec_combo'): self.codec_combo.setEnabled(is_video)
        if hasattr(self, 'export_audio_check'): self.export_audio_check.setVisible(not is_video)
        
        if is_video:
            self.lbl_output.setText(self.tr("label_output_file"))
            self.output_input.setPlaceholderText(self.tr("placeholder_output_file"))
        else:
            self.lbl_output.setText(self.tr("label_output_folder"))
            self.output_input.setPlaceholderText("Dossier de destination pour la séquence")

    def toggle_macro_recording(self, checked):
        self.is_recording_macro = checked
        if checked:
            self.macro_events = []
            self.macro_start_time = time.time()
            self.btn_rec_macro.setStyleSheet("background-color: #FF0000; color: white; border: 1px solid #FF0000;")
            self.log("🔴 Enregistrement Macro démarré")
        else:
            self.btn_rec_macro.setStyleSheet("")
            self.log(f"⏹️ Macro terminée: {len(self.macro_events)} événements enregistrés")

    def toggle_dock(self, dock_name):
        if hasattr(self, 'docks') and dock_name in self.docks:
            dock = self.docks[dock_name]
            dock.setVisible(not dock.isVisible())

    def toggle_lock_docks(self, checked=False):
        if checked:
            features = QDockWidget.DockWidgetFeature.DockWidgetClosable
        else:
            features = QDockWidget.DockWidgetFeature.DockWidgetClosable | \
                       QDockWidget.DockWidgetFeature.DockWidgetMovable | \
                       QDockWidget.DockWidgetFeature.DockWidgetFloatable
            
        count = 0
        if hasattr(self, 'docks'):
            for dock in self.docks.values():
                dock.setFeatures(features)
                count += 1
        
        state = "verrouillée" if checked else "déverrouillée"
        self.log(f"🔒 Disposition {state} ({count} fenêtres).")

    def toggle_performance_view(self):
        if self.performance_window is None:
            self.performance_window = PerformanceWindow(self)
            self.performance_window.show()
            # Sync initiale
            self.performance_window.preview_widget.set_style(self.style_combo.currentText())
            self.update_preview_params()
        else:
            self.performance_window.close()
            self.performance_window = None

    def toggle_shader_editor(self):
        if self.shader_editor_window is None:
            self.shader_editor_window = ShaderEditorWindow(self)
            self.shader_editor_window.show()
            self.shader_editor_window.load_style(self.style_combo.currentText())
        else:
            self.shader_editor_window.close()
            self.shader_editor_window = None

    def toggle_mode(self, index):
        is_realtime = (index == 1)
        
        self.audio_input.setVisible(not is_realtime)
        self.btn_audio.setVisible(not is_realtime)
        self.device_combo.setVisible(is_realtime)
        self.batch_check.setVisible(not is_realtime)
        
        if is_realtime:
            self.refresh_audio_devices()
            self.btn_start.setText(self.tr("toolbar_run_visualizer"))
            self.btn_preview.setVisible(False)
            self.stop_audio()
            self.preview_widget.set_analyzer(None)
        else:
            self.btn_start.setText(self.tr("toolbar_render"))
            self.btn_preview.setVisible(True)
            
        self.log(f"🔄 Mode changé: {self.mode_combo.currentText()}")

    def on_node_pipeline_generated(self, code):
        self.preview_widget.set_custom_pipeline(code)
        self.log("🔗 Pipeline nodal appliqué au moteur de rendu.")

    def sync_timeline_time(self, time_sec):
        """Met à jour l'aperçu visuel lors du déplacement de la tête de lecture"""
        self.playback_time = time_sec
        self.preview_widget.set_playback_time(time_sec)
        
        if self.timeline_widget:
            effects = self.timeline_widget.get_active_effects(time_sec)
            self.preview_widget.set_timeline_effects(effects)
            if self.performance_window:
                self.performance_window.preview_widget.set_timeline_effects(effects)
                
        self.preview_widget.update()

    def seek_audio(self, time_sec):
        # This method is being called from the timeline, but the implementation
        # was incomplete. Let's fix it to handle both playback and paused states.
        self.playback_offset = time_sec * 1000.0
        
        if self.is_playing:
            if self.audio_loaded:
                pygame.mixer.music.play(start=time_sec)
            if self.audio_thread:
                self.audio_thread.playback_offset = self.playback_offset
                if not self.audio_loaded:
                    self.audio_thread.start_time = time.time() - time_sec
        
        # Update UI regardless of playback state
        self.on_audio_update(time_sec, self.analyzer.get_features_at_time(time_sec) if self.analyzer else None, None)

    def seek_audio_legacy(self, time_sec):
        """Déplace la lecture audio (sur relâchement de la souris)"""
        if self.audio_loaded:
            try:
                pygame.mixer.music.play(start=time_sec)
                self.log(f"📍 Seek audio: {time_sec:.2f}s")
            except Exception as e:
                print(f"Seek error: {e}")

    def toggle_sequencer_window(self):
        if self.sequencer_window is None:
            self.sequencer_window = SequencerWindow(self)
            self.sequencer_window.show()
        else:
            self.sequencer_window.close()
            self.sequencer_window = None

    def toggle_connectivity_window(self):
        if self.connectivity_window is None:
            self.connectivity_window = ConnectivityWindow(self)
            self.connectivity_window.show()
        else:
            self.connectivity_window.close()
            self.connectivity_window = None

    def toggle_mode(self, index):
        is_realtime = (index == 1)
        self.batch_check.setVisible(not is_realtime)
        self.json_check.setVisible(not is_realtime)
        self.waveform.setVisible(not is_realtime)
        self.srt_input.setEnabled(not is_realtime) 
        self.btn_srt.setEnabled(not is_realtime)
        if is_realtime:
            self.lbl_audio.setText(self.tr("label_mic"))
            self.audio_input.setVisible(False)
            self.btn_audio.setVisible(False)
            self.device_combo.setVisible(True)
            self.btn_start.setText(self.tr("toolbar_run_visualizer"))
            self.btn_preview.setVisible(False)
            self.refresh_audio_devices()
            self.lbl_output.setText(self.tr("label_recording"))
            self.output_input.setPlaceholderText(self.tr("placeholder_recording_file"))
            self.btn_out.setText(self.tr("button_choose_file"))
        else:
            self.lbl_audio.setText(self.tr("label_audio_file"))
            self.audio_input.setText("")
            self.audio_input.setEnabled(True)
            self.audio_input.setVisible(True)
            self.btn_audio.setEnabled(True)
            self.btn_audio.setVisible(True)
            self.device_combo.setVisible(False)
            self.audio_input.setPlaceholderText(self.tr("placeholder_audio_file"))
            self.btn_start.setText(self.tr("toolbar_render"))
            self.btn_preview.setVisible(True)
            self.lbl_output.setText(self.tr("label_output_file"))
            self.output_input.setPlaceholderText(self.tr("placeholder_output_file"))
            self.btn_out.setText(self.tr("button_save_as"))

    def toggle_batch_mode(self, checked):
        if checked:
            self.lbl_audio.setText(self.tr("label_audio_folder"))
            self.audio_input.setPlaceholderText(self.tr("placeholder_audio_folder"))
            self.lbl_output.setText(self.tr("label_output_folder"))
            self.output_input.setPlaceholderText(self.tr("placeholder_output_folder"))
            self.btn_out.setText(self.tr("button_choose_folder"))
            self.title_input.setEnabled(False)
            self.artist_input.setEnabled(False)
            self.waveform.setVisible(False)
        else:
            self.lbl_audio.setText(self.tr("label_audio_file"))
            self.audio_input.setPlaceholderText(self.tr("placeholder_audio_file"))
            self.lbl_output.setText(self.tr("label_output_file"))
            self.output_input.setPlaceholderText(self.tr("placeholder_output_file"))
            self.btn_out.setText(self.tr("button_save_as"))
            self.title_input.setEnabled(True)
            self.artist_input.setEnabled(True)
            self.waveform.setVisible(True)

    def browse_srt(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("file_dialog_open_srt"), "", self.tr("file_dialog_srt_files"))
        if path:
            self.srt_input.setText(path)

    def browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("file_dialog_open_logo"), "", self.tr("file_dialog_image_files"))
        if path:
            self.logo_input.setText(path)

    def log(self, message):
        self.log_area.append(message)
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def swap_resolution(self):
        w = self.width_spin.value()
        h = self.height_spin.value()
        self.width_spin.setValue(h)
        self.height_spin.setValue(w)

    def show_update_dialog(self, version, url):
        reply = QMessageBox.question(self, self.tr("update_available_title"), 
                                     self.tr("update_available_text", version=version),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            webbrowser.open(url)

    def show_about(self):
        if not self.about_dialog:
            self.about_dialog = AboutDialog(self)
        self.about_dialog.show()
