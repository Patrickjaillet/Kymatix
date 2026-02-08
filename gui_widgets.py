import time
import queue
import numpy as np
import cv2
import os
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QRegularExpression, pyqtSignal, QThread
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QSyntaxHighlighter, QTextCharFormat, QFont
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from shader_generator import ProceduralShaderGenerator
from particle_system import ParticleSystem
from obj_loader import OBJLoader
from model_renderer import ModelRenderer
from collections import deque
import dearpygui.dearpygui as dpg

class WaveformWidget(QWidget):
    """Widget pour afficher la forme d'onde audio"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(10)
        self.data = None

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond
        painter.fillRect(self.rect(), QColor("#000000"))
        
        if self.data is None:
            painter.setPen(QColor("#444444"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.parent().tr("waveform_no_preview"))
            return

        # Dessin de la waveform
        painter.setPen(QPen(QColor("#00FF00"), 1))
        
        w = self.width()
        h = self.height()
        mid_h = h / 2
        
        # Downsampling simple pour l'affichage
        step = max(1, len(self.data) // w)
        samples = self.data[::step]
        
        # Normalisation
        max_val = np.max(np.abs(samples)) if len(samples) > 0 else 1.0
        if max_val == 0: max_val = 1.0
        
        # Création des lignes
        path_points = []
        for x, val in enumerate(samples):
            if x >= w: break
            y = mid_h - (val / max_val) * (mid_h - 5)
            path_points.append((x, y))
            
        for i in range(len(path_points) - 1):
            painter.drawLine(int(path_points[i][0]), int(path_points[i][1]), 
                             int(path_points[i+1][0]), int(path_points[i+1][1]))

class VUMeterWidget(QWidget):
    """VU-mètre stéréo vertical"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(24)
        self.left_level = 0.0
        self.right_level = 0.0
        self.peak_left = 0.0
        self.peak_right = 0.0
        self.decay = 0.02
        self.peak_hold = 20
        self.hold_counter_l = 0
        self.hold_counter_r = 0
        self.clip_left = False
        self.clip_right = False
        self.clip_timer_l = 0
        self.clip_timer_r = 0
        self.clip_hold = 20

    def set_levels(self, left, right):
        # Clipping detection
        if left > 1.0:
            self.clip_left = True
            self.clip_timer_l = self.clip_hold
        elif self.clip_timer_l > 0:
            self.clip_timer_l -= 1
        else:
            self.clip_left = False
            
        if right > 1.0:
            self.clip_right = True
            self.clip_timer_r = self.clip_hold
        elif self.clip_timer_r > 0:
            self.clip_timer_r -= 1
        else:
            self.clip_right = False

        self.left_level = np.clip(left, 0.0, 1.0)
        self.right_level = np.clip(right, 0.0, 1.0)
        
        if self.left_level > self.peak_left: 
            self.peak_left = self.left_level
            self.hold_counter_l = self.peak_hold
        else: 
            if self.hold_counter_l > 0: self.hold_counter_l -= 1
            else: self.peak_left = max(0.0, self.peak_left - self.decay)
            
        if self.right_level > self.peak_right: 
            self.peak_right = self.right_level
            self.hold_counter_r = self.peak_hold
        else: 
            if self.hold_counter_r > 0: self.hold_counter_r -= 1
            else: self.peak_right = max(0.0, self.peak_right - self.decay)
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111"))
        
        w = self.width()
        h = self.height()
        bar_w = (w - 4) // 2
        clip_h = 5
        
        # Draw Clip LEDs
        c_l = QColor("#FF0000") if self.clip_left else QColor("#440000")
        painter.fillRect(1, 0, bar_w, clip_h, c_l)
        
        c_r = QColor("#FF0000") if self.clip_right else QColor("#440000")
        painter.fillRect(1 + bar_w + 2, 0, bar_w, clip_h, c_r)
        
        # Draw Bars
        self._draw_bar(painter, 1, h, bar_w, self.left_level, self.peak_left, top_margin=clip_h+2)
        self._draw_bar(painter, 1 + bar_w + 2, h, bar_w, self.right_level, self.peak_right, top_margin=clip_h+2)

    def _draw_bar(self, painter, x, h, w, level, peak, top_margin=0):
        avail_h = h - top_margin
        fill_h = int(level * avail_h)
        peak_y = top_margin + int((1.0 - peak) * avail_h)
        
        if fill_h > 0:
            grad = QLinearGradient(x, h, x, 0)
            grad.setColorAt(0.0, QColor("#00FF00"))
            grad.setColorAt(0.7, QColor("#FFFF00"))
            grad.setColorAt(1.0, QColor("#FF0000"))
            painter.fillRect(x, h - fill_h, w, fill_h, grad)
            
        painter.fillRect(x, peak_y, w, 1, QColor("#FFFFFF"))

class GoniometerWidget(QWidget):
    """Visualiseur de champ stéréo (Lissajous)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(10)
        self.samples = None
        self.mode = "Lissajous"
        self.correlation = 0.0
        self.setStyleSheet("background-color: #000; border: 1px solid #333;")

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def set_samples(self, samples):
        self.samples = samples
        # Calcul de la corrélation de phase
        if samples is not None and samples.shape[0] == 2 and samples.shape[1] > 0:
            l = samples[0]
            r = samples[1]
            # Corrélation = sum(L*R) / (sqrt(sum(L^2)) * sqrt(sum(R^2)))
            num = np.sum(l * r)
            den = np.sqrt(np.sum(l**2)) * np.sqrt(np.sum(r**2))
            self.correlation = num / den if den > 1e-6 else 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        
        # --- Phase Correlation Meter ---
        rect = self.rect()
        bar_h = 12
        bar_y = rect.height() - bar_h - 5
        bar_x = 10
        bar_w = rect.width() - 20
        
        # Background
        painter.fillRect(bar_x, bar_y, bar_w, bar_h, QColor("#222"))
        
        # Center line
        cx_bar = bar_x + bar_w / 2
        painter.setPen(QPen(QColor("#666"), 1))
        painter.drawLine(int(cx_bar), bar_y, int(cx_bar), bar_y + bar_h)
        
        # Value Bar
        val_x = cx_bar + self.correlation * (bar_w / 2)
        color = QColor("#00FF00") if self.correlation >= 0 else QColor("#FF0000")
        
        if val_x > cx_bar:
            painter.fillRect(int(cx_bar), bar_y + 2, int(val_x - cx_bar), bar_h - 4, color)
        else:
            painter.fillRect(int(val_x), bar_y + 2, int(cx_bar - val_x), bar_h - 4, color)
            
        # Labels
        painter.setPen(QColor("#AAA"))
        font = painter.font()
        font.setPixelSize(8)
        painter.setFont(font)
        painter.drawText(bar_x, bar_y - 2, "-1")
        painter.drawText(int(cx_bar) - 3, bar_y - 2, "0")
        painter.drawText(bar_x + bar_w - 10, bar_y - 2, "+1")

        # --- Vectorscope ---
        if self.samples is None or self.samples.ndim != 2 or self.samples.shape[0] != 2:
            return
            
        # Downsample pour la performance
        data = self.samples[:, ::2]
        if data.shape[1] < 2: return

        # Zone de dessin (au dessus de la barre)
        viz_h = bar_y - 5
        cx, cy = self.width() / 2, viz_h / 2
        scale = min(cx, cy) * 0.9
        
        # Rotation 45 deg (Mid/Side)
        # X = (L - R) * 0.707 (Side)
        # Y = (L + R) * 0.707 (Mid)
        side = (data[0] - data[1]) * 0.707
        mid = (data[0] + data[1]) * 0.707
        
        x = cx + side * scale
        y = cy - mid * scale # Y inversé écran
        
        if self.mode == "Lissajous":
            painter.setPen(QPen(QColor(0, 255, 0, 150), 1))
            for i in range(len(x)):
                painter.drawPoint(int(x[i]), int(y[i]))
        elif self.mode == "Polar":
            # Mode "Jellyfish" : lignes depuis le centre
            painter.setPen(QPen(QColor(0, 255, 0, 40), 1))
            for i in range(0, len(x), 2): # Skip pour performance
                painter.drawLine(int(cx), int(cy), int(x[i]), int(y[i]))

class GLSLHighlighter(QSyntaxHighlighter):
    """Coloration syntaxique pour le code GLSL"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#00E5FF")) # Cyan
        keywordFormat.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "attribute", "const", "uniform", "varying", "break", "continue",
            "do", "for", "while", "if", "else", "in", "out", "inout",
            "float", "int", "void", "bool", "true", "false", "discard",
            "return", "mat2", "mat3", "mat4", "vec2", "vec3", "vec4",
            "ivec2", "ivec3", "ivec4", "bvec2", "bvec3", "bvec4", "sampler2D",
            "samplerCube", "struct", "layout", "version", "#section", "#config"
        ]
        for pattern in keywords:
            self.highlightingRules.append((QRegularExpression(r"\b" + pattern + r"\b"), keywordFormat))

        # Built-in functions
        funcFormat = QTextCharFormat()
        funcFormat.setForeground(QColor("#F72585")) # Pink
        funcs = [
            "radians", "degrees", "sin", "cos", "tan", "asin", "acos", "atan",
            "pow", "exp", "log", "exp2", "log2", "sqrt", "inversesqrt",
            "abs", "sign", "floor", "ceil", "fract", "mod", "min", "max",
            "clamp", "mix", "step", "smoothstep", "length", "distance",
            "dot", "cross", "normalize", "faceforward", "reflect", "refract",
            "matrixCompMult", "lessThan", "lessThanEqual", "greaterThan",
            "greaterThanEqual", "equal", "notEqual", "any", "all", "not",
            "texture", "texture2D", "textureCube"
        ]
        for pattern in funcs:
            self.highlightingRules.append((QRegularExpression(r"\b" + pattern + r"\b"), funcFormat))

        # Comments
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#808080"))
        self.highlightingRules.append((QRegularExpression(r"//[^\n]*"), commentFormat))
        self.highlightingRules.append((QRegularExpression(r"/\*.*?\*/"), commentFormat))
        
        # Numbers
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#00E676")) # Green
        self.highlightingRules.append((QRegularExpression(r"\b\d+(\.\d*)?f?\b"), numberFormat))
        self.highlightingRules.append((QRegularExpression(r"\b\.\d+f?\b"), numberFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class ModelLoaderThread(QThread):
    """Thread pour charger les modèles 3D sans bloquer l'interface"""
    model_loaded = pyqtSignal(object) # Renvoie l'instance OBJLoader
    progress_signal = pyqtSignal(int)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            loader = OBJLoader(self.path, progress_callback=self.progress_signal.emit, check_cancel=lambda: self.is_cancelled)
            self.model_loaded.emit(loader)
        except Exception as e:
            if "cancelled" in str(e):
                print("🛑 Chargement du modèle annulé par l'utilisateur.")
            else:
                print(f"❌ Erreur thread chargement modèle: {e}")
            self.model_loaded.emit(None)

class VideoRecorderThread(QThread):
    """Thread dédié à l'encodage vidéo pour ne pas bloquer le rendu OpenGL"""
    def __init__(self, path, width, height, fps=60.0):
        super().__init__()
        self.path = path
        self.width = width
        self.height = height
        self.fps = fps
        self.queue = queue.Queue()
        self.running = True

    def run(self):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        recorder = cv2.VideoWriter(self.path, fourcc, self.fps, (self.width, self.height))
        
        while self.running or not self.queue.empty():
            try:
                data = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            try:
                # Conversion des données brutes (PBO) en image
                frame = np.frombuffer(data, dtype=np.uint8).reshape(self.height, self.width, 3)
                frame = cv2.flip(frame, 0) # OpenGL est inversé verticalement
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                recorder.write(frame)
            except Exception as e:
                print(f"❌ Erreur enregistrement frame: {e}")
                
        recorder.release()

    def add_frame(self, data):
        if self.running:
            self.queue.put(data)

    def stop(self):
        self.running = False
        self.wait()

class ShaderPreviewWidget(QOpenGLWidget):
    """Widget OpenGL pour prévisualiser les shaders et effets en temps réel"""
    fps_changed = pyqtSignal(float)
    model_loading_progress = pyqtSignal(int)
    model_info = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(10, 10)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.start_time = time.time()
        self.program = None
        self.vao = None
        self.mouse_pos = QPoint(0, 0)
        self.mouse_click = QPoint(0, 0)
        self.mouse_down = False
        self.video_texture = None
        self.current_video_frame = None
        self.spout_sender = None
        self.spout_receiver = None
        self.spout_texture_id = None # Cached texture for Spout
        self.output_mode = "No Output" # "Spout"
        self.spout_input_enabled = False
        
        # Recording Async
        self.recording_thread = None
        self.node_editor = None
        self.preview_pbo_ids = None
        self.preview_pbo_index = 0
        self.pbo_ids = []
        
        self.analyzer = None
        self.current_features = None # Cached features from audio thread
        self.playback_time = 0.0
        self.particle_system = ParticleSystem()
        self.compute_particles_enabled = False
        self.last_frame_time = time.time()
        self.particle_gravity = 0.5
        self.particle_life = 3.0
        self.particle_turbulence = 1.0
        self.particle_color = (0.2, 0.5, 1.0)
        self.particle_size = 2.0
        self.vr_mode = False
        self.model_renderer = None
        self.model_loader = None
        self.model_texture_id = None
        self.model_rotation_y = 0.0
        self.model_base_scale = 1.0
        self.model_enabled = False
        self.model_speed = 0.5
        self.light2_color = (0.8, 0.2, 1.0)
        self.model_wireframe = False
        self.model_flat_shading = False
        self.model_deformation = 0.0
        self.model_reflection = 0.0
        self.model_ghosting = 0.0
        self.model_matrix_history = deque(maxlen=20)
        self.env_map_id = None
        self.model_texture_id_2 = None
        self.current_model_texture_id = None
        self.beat_triggered_texture_swap = False
        self.user_texture_id = None
        self.has_user_texture = False
        self.distort_user_texture = False
        self.texture_blend_mode = "Mix"
        self.auto_center_model = False
        self.auto_normalize_model = False
        self.show_normals = False
        self.normal_length = 0.1
        self.show_bbox = False
        self.custom_pipeline = None
        
        # OSD (On Screen Display)
        self.osd_label = QLabel(self)
        self.osd_label.setStyleSheet("color: #00FF00; font-size: 20px; font-weight: bold; background-color: rgba(0, 0, 0, 150); padding: 8px; border-radius: 4px;")
        self.osd_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.osd_label.hide()
        self.osd_timer = QTimer(self)
        self.osd_timer.setSingleShot(True)
        self.osd_timer.timeout.connect(self.osd_label.hide)
        
        # FPS Counter
        self.frame_count = 0
        self.last_fps_time = time.time()
        
        # Paramètres par défaut
        self.current_style = "fractal"
        self.bloom = 0.5
        self.aberration = 0.1
        self.grain = 0.05
        self.glitch = 0.0
        self.vignette = 0.0
        self.scanline = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.brightness = 0.0
        self.gamma = 1.0
        self.exposure = 1.0
        self.strobe = 0.0
        self.light_leak = 0.0
        self.mirror = 0.0
        self.pixelate = 0.0
        self.posterize = 0.0
        self.solarize = 0.0
        self.hue_shift = 0.0
        self.invert = 0.0
        self.sepia = 0.0
        self.thermal = 0.0
        self.edge = 0.0
        self.fisheye = 0.0
        self.twist = 0.0
        self.ripple = 0.0
        self.mirror_quad = 0.0
        self.rgb_split = 0.0
        self.bleach = 0.0
        self.vhs = 0.0
        self.neon = 0.0
        self.cartoon = 0.0
        self.sketch = 0.0
        self.vibrate = 0.0
        self.drunk = 0.0
        self.pinch = 0.0
        self.zoom_blur = 0.0
        self.aura = 0.0
        self.psycho = 0.0
        self.modulations = []
        
        # Masking
        self.mask_points = []
        self.is_drawing_mask = False
        self.mask_enabled = False
        self.mask_fbo = None
        self.mask_texture = None
        self.mask_mode = "Inside"
        self.mask_fill_program = None
        self.mask_outline_program = None
        self.timeline_effects = {}
        
        # Feedback
        self.feedback_decay = 0.0
        self.feedback_fbos = None
        self.feedback_textures = None
        self.feedback_index = 0
        self.blit_program = None
        
    def initializeGL(self):
        self.particle_system.init_gl()
        # Quad plein écran
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0
        ], dtype=np.float32)
        
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        glBindVertexArray(0)
        
        self.update_shader()
        self.timer.start(16) # ~60 FPS
        
        self._init_mask_rendering()

    def resizeGL(self, w, h):
        """Mise à jour critique du viewport lors du redimensionnement des docks"""
        pixel_ratio = self.devicePixelRatio()
        glViewport(0, 0, int(w * pixel_ratio), int(h * pixel_ratio))

        # Resize mask texture
        if self.mask_fbo:
            glBindTexture(GL_TEXTURE_2D, self.mask_texture)
            w_px = int(w * pixel_ratio)
            h_px = int(h * pixel_ratio)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, w_px, h_px, 0, GL_RED, GL_UNSIGNED_BYTE, None)
            
        # Resize feedback buffers if they exist
        if self.feedback_fbos:
            self._init_feedback_buffers(int(w * pixel_ratio), int(h * pixel_ratio))
            
        # Invalidate Spout texture to force recreation
        if self.spout_texture_id:
            glDeleteTextures([self.spout_texture_id])
            self.spout_texture_id = None

        # --- 3D Model Loading ---
        # This must be done here, where the GL context is active.
        try:
            model_path = "assets/cube.obj" # Assumes an 'assets' folder at the project root
            if os.path.exists(model_path):
                self.model_loader = OBJLoader(model_path)
                self.model_renderer = ModelRenderer(self.model_loader)
                print("✅ 3D Model Renderer initialized.")
        except Exception as e:
            print(f"❌ Error initializing 3D model: {e}")
            
        # --- 3D Model Texture Loading ---
        try:
            texture_path = "assets/checker.png"
            if not os.path.exists(texture_path):
                # Crée une texture damier simple si elle n'existe pas
                checker = np.zeros((64, 64, 3), dtype=np.uint8)
                c1 = (np.arange(64) // 32) % 2
                c2 = (np.arange(64) // 32) % 2
                checkerboard = (c1[:, None] ^ c2[None, :]) * 255
                checker[:, :, 0] = checkerboard # Canal Bleu
                checker[:, :, 2] = 255 - checkerboard # Canal Rouge
                cv2.imwrite(texture_path, checker)
                print(f"🎨 Texture par défaut créée : {texture_path}")

            frame = cv2.imread(texture_path)
            self.model_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.model_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, frame.shape[1], frame.shape[0], 0, GL_BGR, GL_UNSIGNED_BYTE, frame)
            glGenerateMipmap(GL_TEXTURE_2D)
            print("🎨 Texture du modèle 3D initialisée.")
        except Exception as e:
            print(f"❌ Erreur initialisation texture 3D: {e}")
            
        # --- 3D Model Texture 2 Loading ---
        try:
            texture_path_2 = "assets/checker_inv.png"
            if not os.path.exists(texture_path_2):
                # Crée une texture damier inversée
                checker = np.zeros((64, 64, 3), dtype=np.uint8)
                c1 = (np.arange(64) // 32) % 2
                c2 = (np.arange(64) // 32) % 2
                checkerboard = (c1[:, None] ^ c2[None, :]) * 255
                checker[:, :, 0] = 255 - checkerboard # Canal Bleu inversé
                checker[:, :, 2] = checkerboard # Canal Rouge inversé
                cv2.imwrite(texture_path_2, checker)
                print(f"🎨 Texture 2 par défaut créée : {texture_path_2}")

            frame = cv2.imread(texture_path_2)
            self.model_texture_id_2 = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.model_texture_id_2)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, frame.shape[1], frame.shape[0], 0, GL_BGR, GL_UNSIGNED_BYTE, frame)
            glGenerateMipmap(GL_TEXTURE_2D)
            print("🎨 Texture 2 du modèle 3D initialisée.")
            self.current_model_texture_id = self.model_texture_id
        except Exception as e:
            print(f"❌ Erreur initialisation texture 2: {e}")
            
        # --- Environment Map Loading ---
        try:
            env_path = "assets/env_map.jpg"
            if not os.path.exists(env_path):
                # Création d'un dégradé simple si pas d'image
                env_img = np.zeros((256, 256, 3), dtype=np.uint8)
                for y in range(256):
                    for x in range(256):
                        env_img[y, x] = [x, y, 255] # Gradient coloré
                cv2.imwrite(env_path, env_img)
                print(f"🎨 Env Map par défaut créée : {env_path}")
            
            env_frame = cv2.imread(env_path)
            self.env_map_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.env_map_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, env_frame.shape[1], env_frame.shape[0], 0, GL_BGR, GL_UNSIGNED_BYTE, env_frame)
            print("🎨 Environment Map initialisée.")
        except Exception as e:
            print(f"❌ Erreur initialisation Env Map: {e}")

    def reset_model_rotation(self):
        self.model_rotation_y = 0.0
        self.model_matrix_history.clear()
        self.update()

    def load_model(self, path):
        """Charge un nouveau modèle 3D depuis un fichier (Asynchrone)"""
        if os.path.exists(path):
            print(f"⏳ Chargement du modèle en arrière-plan : {os.path.basename(path)}...")
            self.loader_thread = ModelLoaderThread(path)
            self.loader_thread.model_loaded.connect(self.on_model_loaded)
            self.loader_thread.progress_signal.connect(self.model_loading_progress.emit)
            self.loader_thread.start()
        else:
            print(f"❌ Fichier introuvable : {path}")

    def on_model_loaded(self, loader):
        if loader:
            if self.auto_center_model:
                loader.center_mesh()
            if self.auto_normalize_model:
                loader.normalize_mesh()

            self.makeCurrent()
            self.model_loader = loader
            self.model_renderer = ModelRenderer(self.model_loader)
            self.doneCurrent()
            self.update()
            print(f"✅ Modèle 3D chargé avec succès !")
            self.model_loading_progress.emit(100) # Force 100% à la fin
            self.model_info.emit(f"Vertices: {loader.vertex_count:,}")

    def cancel_model_loading(self):
        """Annule le chargement en cours"""
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            self.loader_thread.cancel()
            self.model_loading_progress.emit(0) # Masquer la barre

    def load_user_texture(self, path):
        self.makeCurrent()
        try:
            if self.user_texture_id:
                glDeleteTextures([self.user_texture_id])
                self.user_texture_id = None
            
            img = cv2.imread(path)
            if img is not None:
                img = cv2.flip(img, 0)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.user_texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, self.user_texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.shape[1], img.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, img)
                self.has_user_texture = True
        except Exception as e:
            print(f"Error loading texture: {e}")
        self.doneCurrent()
        self.update()

    def clear_user_texture(self):
        self.makeCurrent()
        if self.user_texture_id:
            glDeleteTextures([self.user_texture_id])
            self.user_texture_id = None
        self.has_user_texture = False
        self.doneCurrent()
        self.update()

    def set_analyzer(self, analyzer):
        self.analyzer = analyzer
        
    def set_audio_features(self, features):
        """Reçoit les features audio calculées par le thread audio"""
        self.current_features = features

    def _init_mask_rendering(self):
        vs_simple = "#version 330\nlayout(location=0) in vec2 pos; void main() { gl_Position = vec4(pos, 0.0, 1.0); }"
        fs_fill = "#version 330\nout vec4 color; void main() { color = vec4(1.0); }"
        self.mask_fill_program = compileProgram(compileShader(vs_simple, GL_VERTEX_SHADER), compileShader(fs_fill, GL_FRAGMENT_SHADER))
        
        fs_outline = "#version 330\nout vec4 color; uniform vec3 outlineColor; void main() { color = vec4(outlineColor, 1.0); }"
        self.mask_outline_program = compileProgram(compileShader(vs_simple, GL_VERTEX_SHADER), compileShader(fs_outline, GL_FRAGMENT_SHADER))
        
        self.mask_fbo = glGenFramebuffers(1)
        self.mask_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.mask_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, self.width(), self.height(), 0, GL_RED, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        
        glBindFramebuffer(GL_FRAMEBUFFER, self.mask_fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.mask_texture, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
        self.mask_vao = glGenVertexArrays(1)
        self.mask_vbo = glGenBuffers(1)
        glBindVertexArray(self.mask_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.mask_vbo)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        glBindVertexArray(0)

    def set_mask_enabled(self, enabled):
        self.mask_enabled = enabled
        self.update()

    def set_mask_drawing_mode(self, enabled):
        self.is_drawing_mask = enabled
        if not enabled and len(self.mask_points) > 0:
            self.update()

    def set_mask_mode(self, mode):
        self.mask_mode = mode
        self.update()

    def clear_mask(self):
        self.mask_points = []
        self.update()
        
    def _init_feedback_buffers(self, w, h):
        if self.feedback_fbos:
            glDeleteFramebuffers(2, self.feedback_fbos)
            glDeleteTextures(2, self.feedback_textures)
            
        self.feedback_fbos = glGenFramebuffers(2)
        self.feedback_textures = glGenTextures(2)
        self.feedback_index = 0
        
        for i in range(2):
            glBindFramebuffer(GL_FRAMEBUFFER, self.feedback_fbos[i])
            glBindTexture(GL_TEXTURE_2D, self.feedback_textures[i])
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.feedback_textures[i], 0)
            
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
        if not self.blit_program:
            vs = "#version 330 core\nlayout(location = 0) in vec2 position;\nout vec2 vTexCoord;\nvoid main() { gl_Position = vec4(position, 0.0, 1.0); vTexCoord = position * 0.5 + 0.5; }"
            fs = "#version 330 core\nin vec2 vTexCoord;\nout vec4 FragColor;\nuniform sampler2D tex;\nvoid main() { FragColor = texture(tex, vTexCoord); }"
            self.blit_program = compileProgram(compileShader(vs, GL_VERTEX_SHADER), compileShader(fs, GL_FRAGMENT_SHADER))

    def set_playback_time(self, time):
        self.playback_time = time

    def set_timeline_effects(self, effects):
        self.timeline_effects = effects

    def set_output_mode(self, mode):
        self.output_mode = mode
        
        # Cleanup
        if mode != "Spout" and self.spout_sender:
            self.spout_sender = None
            
        # Init
        if mode == "Spout" and not self.spout_sender:
            try:
                from SpoutGL import SpoutSender
                self.spout_sender = SpoutSender()
                self.spout_sender.setSenderName("MusicVideoGenPreview")
            except Exception as e: print(f"Spout Error: {e}")

    def set_spout_input(self, enabled):
        self.spout_input_enabled = enabled
        if enabled and not self.spout_receiver:
            try:
                from SpoutGL import SpoutReceiver
                self.spout_receiver = SpoutReceiver()
                self.spout_receiver.setReceiverName("MusicVideoGenInput") # Optional, receives active
            except Exception as e: print(f"Spout Receiver Error: {e}")

    def toggle_recording(self, output_path=None):
        if self.recording_thread:
            self.recording_thread.stop()
            self.recording_thread = None
            # Nettoyage des PBOs
            if self.pbo_ids:
                self.makeCurrent()
                glDeleteBuffers(len(self.pbo_ids), self.pbo_ids)
                self.pbo_ids = []
                self.doneCurrent()
            return False # Stopped
        elif output_path:
            w = int(self.width() * self.devicePixelRatio())
            h = int(self.height() * self.devicePixelRatio())
            if w % 2 != 0: w -= 1
            if h % 2 != 0: h -= 1
            
            self.recording_width = w
            self.recording_height = h
            self.recording_frame_count = 0
            
            # Initialisation des PBOs (Ping-Pong)
            self.makeCurrent()
            self.pbo_ids = glGenBuffers(2)
            self.pbo_index = 0
            self.pbo_next_index = 1
            
            size = w * h * 3
            for pbo in self.pbo_ids:
                glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo)
                glBufferData(GL_PIXEL_PACK_BUFFER, size, None, GL_STREAM_READ)
            glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
            self.doneCurrent()
            
            self.recording_thread = VideoRecorderThread(output_path, w, h, 60.0)
            self.recording_thread.start()
            return True # Started

    def update_video_frame(self, frame):
        """Met à jour la texture iChannel0 avec une frame vidéo (numpy array BGR)"""
        if frame is None: return
        
        h, w, ch = frame.shape
        
        if self.video_texture is None:
            self.video_texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.video_texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            # Allocation initiale
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_BGR, GL_UNSIGNED_BYTE, frame)
            self.video_texture_size = (w, h)
        else:
            glBindTexture(GL_TEXTURE_2D, self.video_texture)
            # Si la taille change, on réalloue, sinon on met à jour (plus rapide)
            if not hasattr(self, 'video_texture_size') or self.video_texture_size != (w, h):
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_BGR, GL_UNSIGNED_BYTE, frame)
                self.video_texture_size = (w, h)
            else:
                glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_BGR, GL_UNSIGNED_BYTE, frame)

    def update_shader(self):
        # Génération du shader avec un profil audio fictif
        dummy_profile = {'tempo': 120, 'energy': 0.5}
        shader_code = ProceduralShaderGenerator.generate_shader(self.current_style, dummy_profile, vr_mode=self.vr_mode, custom_pipeline=self.custom_pipeline)
        
        try:
            vs_code = ProceduralShaderGenerator.VERTEX_SHADER
            vs = compileShader(vs_code, GL_VERTEX_SHADER)
            fs = compileShader(shader_code, GL_FRAGMENT_SHADER)
            
            new_program = compileProgram(vs, fs)
            
            old_program = self.program
            self.program = new_program
            
            if old_program:
                try:
                    glDeleteProgram(old_program)
                except Exception:
                    pass
        except Exception as e:
            print(f"Erreur compilation preview: {e}")

    def set_custom_pipeline(self, code):
        """Définit le code GLSL généré par l'éditeur nodal"""
        self.custom_pipeline = code
        self.makeCurrent()
        self.update_shader()
        self.doneCurrent()

    def show_osd(self, text, duration=1000):
        """Affiche un message temporaire sur l'aperçu"""
        self.osd_label.setText(text)
        self.osd_label.adjustSize()
        x = (self.width() - self.osd_label.width()) // 2
        y = (self.height() - self.osd_label.height()) // 2
        self.osd_label.move(x, y)
        self.osd_label.show()
        self.osd_timer.start(duration)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.osd_label.isVisible():
             x = (self.width() - self.osd_label.width()) // 2
             y = (self.height() - self.osd_label.height()) // 2
             self.osd_label.move(x, y)

    def check_shader_code(self, fragment_code):
        """Compiles a fragment shader string and returns error string or None."""
        self.makeCurrent()
        error = None
        program = vs = fs = None
        try:
            vs_code = ProceduralShaderGenerator.VERTEX_SHADER
            vs = compileShader(vs_code, GL_VERTEX_SHADER)
            fs = compileShader(fragment_code, GL_FRAGMENT_SHADER)
            program = compileProgram(vs, fs)
        except Exception as e:
            error = str(e)
        finally:
            if program: glDeleteProgram(program)
            if vs: glDeleteShader(vs)
            if fs: glDeleteShader(fs)
            self.doneCurrent()
        return error

    def mousePressEvent(self, event):
        if self.is_drawing_mask and event.button() == Qt.MouseButton.LeftButton:
            self.mask_points = []
            self.mouseMoveEvent(event) # Add first point
        else:
            self.mouse_down = True
            self.mouse_pos = event.pos()
            self.mouse_click = event.pos()
        
    def mouseMoveEvent(self, event):
        if self.is_drawing_mask and event.buttons() & Qt.MouseButton.LeftButton:
            w = self.width() * self.devicePixelRatio()
            h = self.height() * self.devicePixelRatio()
            if w == 0 or h == 0: return
            
            x_ndc = (event.pos().x() * self.devicePixelRatio() / w) * 2.0 - 1.0
            y_ndc = 1.0 - (event.pos().y() * self.devicePixelRatio() / h) * 2.0
            self.mask_points.append((x_ndc, y_ndc))
            self.update()
        elif self.mouse_down:
            self.mouse_pos = event.pos()
            
    def mouseReleaseEvent(self, event):
        if self.is_drawing_mask:
            self.update() # Final update
        else:
            self.mouse_down = False

    def paintGL(self):
        # Calcul du delta time pour les particules
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now
        
        # FPS Calculation
        self.frame_count += 1
        if now - self.last_fps_time >= 0.5:
            fps = self.frame_count / (now - self.last_fps_time)
            self.fps_changed.emit(fps)
            self.frame_count = 0
            self.last_fps_time = now

        if not self.program: return
        
        w = self.width() * self.devicePixelRatio()
        h = self.height() * self.devicePixelRatio()

        # --- MASK RENDER PASS ---
        has_mask = self.mask_enabled and len(self.mask_points) > 2
        if has_mask:
            glBindFramebuffer(GL_FRAMEBUFFER, self.mask_fbo)
            glViewport(0, 0, int(w), int(h))
            glClearColor(0,0,0,0)
            glClear(GL_COLOR_BUFFER_BIT)
            
            glUseProgram(self.mask_fill_program)
            glBindVertexArray(self.mask_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.mask_vbo)
            mask_vtx_data = np.array(self.mask_points, dtype=np.float32)
            glBufferData(GL_ARRAY_BUFFER, mask_vtx_data.nbytes, mask_vtx_data, GL_DYNAMIC_DRAW)
            
            glDrawArrays(GL_TRIANGLE_FAN, 0, len(self.mask_points))
            
            glBindVertexArray(0)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
        # --- END MASK RENDER PASS ---
        
        audio_features = {}
        current_time = 0.0

        # Priorité aux données poussées par le thread audio
        if self.current_features:
            current_time = self.playback_time
            features = self.current_features
            audio_features = {
                'sub_bass': features.sub_bass,
                'bass': features.bass,
                'low_mid': features.low_mid,
                'mid': features.mid,
                'high_mid': features.high_mid,
                'presence': features.presence,
                'brilliance': features.brilliance,
                'beat_strength': features.beat_strength,
                'intensity': features.intensity,
                'spectral_centroid': features.spectral_centroid / 22050.0, # Normalize
                'spectral_flux': min(features.spectral_flux / 10.0, 1.0), # Normalize
                'glitch_intensity_feature': features.glitch_intensity,
                'is_chorus': 1.0 if features.segment_type == 'chorus' else 0.0
            }
        elif self.analyzer:
            # Fallback (lent) si pas de données poussées
            current_time = self.playback_time
            features = self.analyzer.get_features_at_time(current_time)
            audio_features = {
                'sub_bass': features.sub_bass,
                'bass': features.bass,
                'low_mid': features.low_mid,
                'mid': features.mid,
                'high_mid': features.high_mid,
                'presence': features.presence,
                'brilliance': features.brilliance,
                'beat_strength': features.beat_strength,
                'intensity': features.intensity,
                'spectral_centroid': features.spectral_centroid / 22050.0, # Normalize
                'spectral_flux': min(features.spectral_flux / 10.0, 1.0), # Normalize
                'glitch_intensity_feature': features.glitch_intensity,
                'is_chorus': 1.0 if features.segment_type == 'chorus' else 0.0
            }
        else:
            # Fallback to simulation if no audio is analyzed
            current_time = time.time() - self.start_time
            beat = max(0.0, np.sin(current_time * (120.0/60.0) * np.pi) * 0.5 + 0.5) # Assuming 120 BPM
            audio_features = {
                'sub_bass': beat, 'bass': beat, 'beat_strength': beat,
                'low_mid': 0.3, 'mid': 0.3, 'high_mid': 0.2, 'presence': 0.1, 'brilliance': 0.1,
                'intensity': 0.5, 'spectral_centroid': 0.2, 'spectral_flux': 0.0,
                'glitch_intensity_feature': 0.0, 'is_chorus': 0.0
            }
        
        # Application des modulations
        params = {
            'bloom_strength': self.bloom, 'aberration_strength': self.aberration, 'grain_strength': self.grain,
            'glitch_strength': self.glitch, 'vignette_strength': self.vignette, 'scanline_strength': self.scanline,
            'contrast_strength': self.contrast, 'saturation_strength': self.saturation, 'brightness_strength': self.brightness,
            'gamma_strength': self.gamma, 'exposure_strength': self.exposure, 'strobe_strength': self.strobe,
            'light_leak_strength': self.light_leak, 'mirror_strength': self.mirror, 'pixelate_strength': self.pixelate,
            'posterize_strength': self.posterize, 'solarize_strength': self.solarize, 'hue_shift_strength': self.hue_shift,
            'invert_strength': self.invert, 'sepia_strength': self.sepia, 'thermal_strength': self.thermal,
            'edge_strength': self.edge, 'fisheye_strength': self.fisheye, 'twist_strength': self.twist,
            'ripple_strength': self.ripple, 'mirror_quad_strength': self.mirror_quad,
            'rgb_split_strength': self.rgb_split, 'bleach_strength': self.bleach, 'vhs_strength': self.vhs, 'neon_strength': self.neon,
            'cartoon_strength': self.cartoon, 'sketch_strength': self.sketch, 'vibrate_strength': self.vibrate, 'drunk_strength': self.drunk,
            'pinch_strength': self.pinch, 'zoom_blur_strength': self.zoom_blur, 'aura_strength': self.aura, 'psycho_strength': self.psycho
        }
        
        for mod in self.modulations:
            if mod['source'] in audio_features and mod['target'] in params:
                params[mod['target']] += audio_features[mod['source']] * mod['amount']
        
        # Apply Timeline Effects
        fx_map = {"Blur": "zoom_blur_strength"}
        for fx, val in self.timeline_effects.items():
            key = fx_map.get(fx, f"{fx.lower()}_strength")
            if key in params:
                params[key] = min(1.0, params[key] + val)
        
        # Feedback Setup
        use_feedback = self.feedback_decay > 0.0
        if use_feedback:
            if not self.feedback_fbos:
                self._init_feedback_buffers(int(w), int(h))
            glBindFramebuffer(GL_FRAMEBUFFER, self.feedback_fbos[self.feedback_index])
            glViewport(0, 0, int(w), int(h))
        
        try:
            glUseProgram(self.program)
        except Exception:
            return
        
        glUniform2f(glGetUniformLocation(self.program, 'resolution'), float(w), float(h))
        glUniform1f(glGetUniformLocation(self.program, 'time'), current_time)

        # iMouse uniform (Shadertoy style: xy = current, zw = click)
        mx = self.mouse_pos.x() * self.devicePixelRatio()
        my = self.mouse_pos.y() * self.devicePixelRatio()
        mcx = self.mouse_click.x() * self.devicePixelRatio()
        mcy = self.mouse_click.y() * self.devicePixelRatio()
        # OpenGL coords (0,0 is bottom-left)
        glUniform4f(glGetUniformLocation(self.program, 'iMouse'), mx, h - my, mcx, h - mcy)
        
        # iChannel0
        if self.video_texture:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.video_texture)
            glUniform1i(glGetUniformLocation(self.program, 'iChannel0'), 0)
        elif self.spout_input_enabled and self.spout_receiver:
            # Receive Spout Texture
            # We need a texture to receive into. Re-use video_texture or create one.
            if self.video_texture is None:
                self.video_texture = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, self.video_texture)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width(), self.height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
            
            # SpoutGL receiveTexture returns true if updated
            self.spout_receiver.receiveTexture(self.video_texture, GL_TEXTURE_2D, False, 0)
            
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.video_texture)
            glUniform1i(glGetUniformLocation(self.program, 'iChannel0'), 0)
            
        # User Texture (iChannel1 / userTexture)
        if self.has_user_texture and self.user_texture_id:
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, self.user_texture_id)
            glUniform1i(glGetUniformLocation(self.program, 'userTexture'), 1)
            glUniform1f(glGetUniformLocation(self.program, 'hasUserTexture'), 1.0)
            glUniform1f(glGetUniformLocation(self.program, 'distortUserTexture'), 1.0 if self.distort_user_texture else 0.0)
            
            mode_map = {"Mix": 0, "Add": 1, "Multiply": 2, "Screen": 3}
            mode_int = mode_map.get(self.texture_blend_mode, 0)
            glUniform1i(glGetUniformLocation(self.program, 'userTextureBlendMode'), mode_int)
        else:
            glUniform1f(glGetUniformLocation(self.program, 'hasUserTexture'), 0.0)
        
        # Mask Texture (iChannel2)
        if has_mask:
            glActiveTexture(GL_TEXTURE2)
            glBindTexture(GL_TEXTURE_2D, self.mask_texture)
            glUniform1i(glGetUniformLocation(self.program, "maskTexture"), 2)

        # Envoi des features
        glUniform1f(glGetUniformLocation(self.program, 'sub_bass'), audio_features.get('sub_bass', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'bass'), audio_features.get('bass', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'low_mid'), audio_features.get('low_mid', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'beat_strength'), audio_features.get('beat_strength', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'mid'), audio_features.get('mid', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'high_mid'), audio_features.get('high_mid', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'presence'), audio_features.get('presence', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'brilliance'), audio_features.get('brilliance', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'intensity'), audio_features.get('intensity', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'spectral_centroid'), audio_features.get('spectral_centroid', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'spectral_flux'), audio_features.get('spectral_flux', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'is_chorus'), audio_features.get('is_chorus', 0.0))
        
        # Envoi des paramètres modulés
        glUniform1f(glGetUniformLocation(self.program, 'bloom_strength'), params['bloom_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'aberration_strength'), params['aberration_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'grain_strength'), params['grain_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'glitch_intensity'), params['glitch_strength'] + audio_features.get('glitch_intensity_feature', 0.0))
        glUniform1f(glGetUniformLocation(self.program, 'vignette_strength'), params['vignette_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'scanline_strength'), params['scanline_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'contrast_strength'), params['contrast_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'saturation_strength'), params['saturation_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'brightness_strength'), params['brightness_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'gamma_strength'), params['gamma_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'exposure_strength'), params['exposure_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'strobe_strength'), params['strobe_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'light_leak_strength'), params['light_leak_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'mirror_strength'), params['mirror_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'pixelate_strength'), params['pixelate_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'posterize_strength'), params['posterize_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'solarize_strength'), params['solarize_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'hue_shift_strength'), params['hue_shift_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'invert_strength'), params['invert_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'sepia_strength'), params['sepia_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'thermal_strength'), params['thermal_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'edge_strength'), params['edge_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'fisheye_strength'), params['fisheye_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'twist_strength'), params['twist_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'ripple_strength'), params['ripple_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'mirror_quad_strength'), params['mirror_quad_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'rgb_split_strength'), params['rgb_split_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'bleach_strength'), params['bleach_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'vhs_strength'), params['vhs_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'neon_strength'), params['neon_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'cartoon_strength'), params['cartoon_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'sketch_strength'), params['sketch_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'vibrate_strength'), params['vibrate_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'drunk_strength'), params['drunk_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'pinch_strength'), params['pinch_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'zoom_blur_strength'), params['zoom_blur_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'aura_strength'), params['aura_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'psycho_strength'), params['psycho_strength'])
        glUniform1f(glGetUniformLocation(self.program, 'hasMask'), 1.0 if has_mask else 0.0)
        
        if use_feedback:
            glActiveTexture(GL_TEXTURE3)
            glBindTexture(GL_TEXTURE_2D, self.feedback_textures[self.feedback_index ^ 1])
            glUniform1i(glGetUniformLocation(self.program, "feedbackTexture"), 3)
            glUniform1f(glGetUniformLocation(self.program, "hasFeedback"), 1.0)
            glUniform1f(glGetUniformLocation(self.program, "feedback_decay"), self.feedback_decay)
        else:
            glUniform1f(glGetUniformLocation(self.program, "hasFeedback"), 0.0)
        
        mode_map = {"Inside": 0, "Outside": 1}
        mask_mode_int = mode_map.get(self.mask_mode, 0)
        glUniform1i(glGetUniformLocation(self.program, "maskMode"), mask_mode_int)
        
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT)
        
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        # --- Rendu du modèle 3D ---
        if self.model_renderer and self.model_enabled:
            w, h = self.width() * self.devicePixelRatio(), self.height() * self.devicePixelRatio()
            aspect = w / h if h > 0 else 1.0
            
            # Matrices de transformation
            model_mat = np.identity(4, dtype=np.float32)
            
            # --- Réactivité à la musique ---
            bass_strength = audio_features.get('bass', 0.0)
            scale_factor = self.model_base_scale * (1.0 + bass_strength * 0.5) # Pulse par rapport à la taille de base
            
            # Changement de texture sur le beat
            beat_strength = audio_features.get('beat_strength', 0.0)
            if beat_strength > 0.8 and not self.beat_triggered_texture_swap:
                if self.current_model_texture_id == self.model_texture_id:
                    self.current_model_texture_id = self.model_texture_id_2
                else:
                    self.current_model_texture_id = self.model_texture_id
                self.beat_triggered_texture_swap = True
            elif beat_strength < 0.2:
                self.beat_triggered_texture_swap = False
            
            scale_mat = np.diag([scale_factor, scale_factor, scale_factor, 1.0]).astype(np.float32)
            model_mat = scale_mat @ model_mat # Appliquer la mise à l'échelle
            
            # Rotation dynamique basée sur l'intensité
            intensity = audio_features.get('intensity', 0.0)
            rotation_speed = self.model_speed + intensity * 2.0 # Vitesse de base + boost d'intensité
            self.model_rotation_y += rotation_speed * dt
            
            # Application de la rotation
            rot_y = np.array([[np.cos(self.model_rotation_y), 0, np.sin(self.model_rotation_y), 0],
                              [0, 1, 0, 0],
                              [-np.sin(self.model_rotation_y), 0, np.cos(self.model_rotation_y), 0],
                              [0, 0, 0, 1]], dtype=np.float32)
            model_mat = rot_y @ model_mat
            
            # Sauvegarde pour le ghosting
            self.model_matrix_history.append(model_mat)

            view_mat = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, -5, 1]], dtype=np.float32)
            view_pos = (0.0, 0.0, 5.0)
            
            fov = 45.0
            f = 1.0 / np.tan(np.radians(fov) / 2.0)
            zNear, zFar = 0.1, 100.0
            proj_mat = np.array([
                [f/aspect, 0, 0, 0],
                [0, f, 0, 0],
                [0, 0, (zFar+zNear)/(zNear-zFar), -1],
                [0, 0, (2*zFar*zNear)/(zNear-zFar), 0]
            ], dtype=np.float32)

            # --- Position de la lumière dynamique ---
            light_radius = 5.0
            light_angle = current_time * 0.8 # Vitesse d'orbite constante
            light_y = 2.0 + audio_features.get('mid', 0.0) * 4.0 # La lumière monte et descend avec les fréquences moyennes
            light_pos = (light_radius * np.cos(light_angle), light_y, light_radius * np.sin(light_angle))

            # --- Deuxième lumière dynamique ---
            light_radius2 = 4.5
            light_angle2 = -current_time * 1.1 # Orbite en sens inverse
            high_freq_strength = audio_features.get('presence', 0.0)
            light_y2 = -2.0 - high_freq_strength * 3.0
            light_pos2 = (light_radius2 * np.cos(light_angle2), light_y2, light_radius2 * np.sin(light_angle2))
            light_color2 = (self.light2_color[0], self.light2_color[1], max(0.0, self.light2_color[2] - high_freq_strength * 0.5))
            
            # --- Morphing ---
            deformation_amount = (audio_features.get('mid', 0.0) * 0.5) + self.model_deformation # Audio + Manuel

            glEnable(GL_DEPTH_TEST)
            glClear(GL_DEPTH_BUFFER_BIT)
            
            # --- Rendu des Ghosts (Traînée) ---
            if self.model_ghosting > 0.0 and len(self.model_matrix_history) > 1:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glDepthMask(GL_FALSE) # Les fantômes n'écrivent pas dans le depth buffer
                
                num_ghosts = int(self.model_ghosting * 15) # Max 15 fantômes
                history_len = len(self.model_matrix_history)
                step = max(1, history_len // (num_ghosts + 1)) if num_ghosts > 0 else 1
                
                # On parcourt l'historique à l'envers
                indices = list(range(history_len - 2, max(-1, history_len - 2 - num_ghosts * step), -step))
                
                for i in indices:
                    mat = self.model_matrix_history[i]
                    ghost_alpha = 0.4 * ((i + 1) / history_len) # Fade out
                    self.model_renderer.render(mat, view_mat, proj_mat, light_pos, view_pos, light_pos2, light_color2, texture_id=self.current_model_texture_id, wireframe=self.model_wireframe, flat_shading=self.model_flat_shading, deformation=deformation_amount, time=current_time, env_map_id=self.env_map_id, reflection_strength=self.model_reflection, alpha=ghost_alpha)
                
                glDepthMask(GL_TRUE)
                glDisable(GL_BLEND)

            self.model_renderer.render(model_mat, view_mat, proj_mat, 
                                     light_pos=light_pos, view_pos=view_pos, 
                                     light_pos2=light_pos2, light_color2=light_color2,
                                     texture_id=self.current_model_texture_id,
                                     wireframe=self.model_wireframe,
                                     flat_shading=self.model_flat_shading,
                                     deformation=deformation_amount,
                                     time=current_time,
                                     env_map_id=self.env_map_id,
                                     reflection_strength=self.model_reflection,
                                     alpha=1.0)

            if self.show_normals:
                self.model_renderer.render_normals(model_mat, view_mat, proj_mat, length=self.normal_length)

            if self.show_bbox:
                min_pt, max_pt = self.model_loader.bbox
                self.model_renderer.render_bbox(model_mat, view_mat, proj_mat, min_pt, max_pt)

            glDisable(GL_DEPTH_TEST)

        # --- Rendu des Particules (Compute Shader) ---
        if self.compute_particles_enabled:
            # Préparation des features audio pour le système de particules
            class AudioFeaturesWrapper:
                def __init__(self, d): self.__dict__ = d
            
            p_features = features if self.analyzer else AudioFeaturesWrapper(audio_features)
            
            # Position de l'émetteur pour le mode 'emit' (orbite circulaire)
            emitter_pos = (np.sin(current_time * 0.5) * 15.0, 
                           np.cos(current_time * 0.8) * 5.0, 
                           np.cos(current_time * 0.5) * 15.0)
            
            # Mise à jour physique
            self.particle_system.update(dt, current_time, p_features, self.particle_gravity, self.particle_life, self.particle_turbulence, emitter_pos)
            
            # Matrices pour le rendu (Perspective simple)
            w, h = self.width() * self.devicePixelRatio(), self.height() * self.devicePixelRatio()
            aspect = w / h if h > 0 else 1.0
            fov = 60.0
            f = 1.0 / np.tan(np.radians(fov) / 2.0)
            zNear, zFar = 0.1, 100.0
            
            # Projection Matrix (Column-Major memory layout via Numpy Row-Major Transpose)
            proj = np.array([
                [f/aspect, 0, 0, 0],
                [0, f, 0, 0],
                [0, 0, (zFar+zNear)/(zNear-zFar), -1],
                [0, 0, (2*zFar*zNear)/(zNear-zFar), 0]
            ], dtype=np.float32)
            
            # View Matrix (Camera at 0,0,30 looking at 0,0,0)
            # Translation (0, 0, -30)
            view = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, -30, 1]
            ], dtype=np.float32)
            
            # Rendu par dessus le shader
            beat_val = audio_features.get('beat_strength', 0.0)
            self.particle_system.render(view, proj, beat_val, self.particle_color, self.particle_size)
            
            # Reset state for other draws if needed
            glUseProgram(0)
        
        if use_feedback:
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            glViewport(0, 0, int(w), int(h)) # Restore screen viewport
            
            # Blit to screen
            glUseProgram(self.blit_program)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.feedback_textures[self.feedback_index])
            glUniform1i(glGetUniformLocation(self.blit_program, "tex"), 0)
            glBindVertexArray(self.vao)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
            
            self.feedback_index = self.feedback_index ^ 1
        
        # --- MASK OUTLINE RENDER PASS ---
        if (self.is_drawing_mask or self.mask_enabled) and len(self.mask_points) > 1:
            glUseProgram(self.mask_outline_program)
            color = (0.0, 1.0, 0.0) if self.is_drawing_mask else (0.8, 0.8, 0.0)
            glUniform3f(glGetUniformLocation(self.mask_outline_program, "outlineColor"), *color)
            glBindVertexArray(self.mask_vao)
            # VBO is already updated from fill pass
            glDrawArrays(GL_LINE_LOOP, 0, len(self.mask_points))
            glBindVertexArray(0)

        # Spout Output
        if self.output_mode == "Spout" and self.spout_sender:
            if self.spout_texture_id is None:
                self.spout_texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, self.spout_texture_id)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, int(w), int(h), 0, GL_RGB, GL_UNSIGNED_BYTE, None)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            
            # Copy current framebuffer to texture
            glBindTexture(GL_TEXTURE_2D, self.spout_texture_id)
            glCopyTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 0, 0, int(w), int(h))
            
            self.spout_sender.sendTexture(self.spout_texture_id, GL_TEXTURE_2D, int(w), int(h), True, 0)
            
        # --- Recording Asynchrone (PBO) ---
        if self.recording_thread and self.recording_thread.isRunning():
            w = self.recording_width
            h = self.recording_height
            size = w * h * 3
            
            # 1. Lire les pixels dans le PBO courant (Asynchrone, retourne immédiatement)
            glBindBuffer(GL_PIXEL_PACK_BUFFER, self.pbo_ids[self.pbo_index])
            glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, 0)
            
            # 2. Récupérer les données du PBO précédent (Déjà prêt, pas de blocage GPU)
            if self.recording_frame_count > 0:
                glBindBuffer(GL_PIXEL_PACK_BUFFER, self.pbo_ids[self.pbo_next_index])
                try:
                    # glGetBufferSubData retourne des bytes
                    data = glGetBufferSubData(GL_PIXEL_PACK_BUFFER, 0, size)
                    self.recording_thread.add_frame(data)
                except Exception:
                    pass
            
            glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
            
            # Swap des indices PBO
            self.pbo_index, self.pbo_next_index = self.pbo_next_index, self.pbo_index
            self.recording_frame_count += 1
            
        # --- Node Editor Preview (PBO Optimized) ---
        if self.node_editor and dpg.is_dearpygui_running():
            target_w, target_h = 320, 180
            size = target_w * target_h * 4 # RGBA

            # Initialisation des PBOs pour la preview si nécessaire
            if self.preview_pbo_ids is None:
                self.preview_pbo_ids = glGenBuffers(2)
                for pbo in self.preview_pbo_ids:
                    glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo)
                    glBufferData(GL_PIXEL_PACK_BUFFER, size, None, GL_STREAM_READ)
                glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)

            # Création d'un FBO intermédiaire pour redimensionner l'image proprement
            if not hasattr(self, 'preview_fbo'):
                self.preview_fbo = glGenFramebuffers(1)
                self.preview_tex = glGenTextures(1)
                glBindFramebuffer(GL_FRAMEBUFFER, self.preview_fbo)
                glBindTexture(GL_TEXTURE_2D, self.preview_tex)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, target_w, target_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.preview_tex, 0)
                glBindFramebuffer(GL_FRAMEBUFFER, 0)

            # 1. Blit (Redimensionnement) de l'écran vers le FBO de preview
            glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self.preview_fbo)
            glBlitFramebuffer(0, 0, int(w), int(h), 0, 0, target_w, target_h, GL_COLOR_BUFFER_BIT, GL_LINEAR)
            glBindFramebuffer(GL_READ_FRAMEBUFFER, self.preview_fbo)

            # 2. Lancer la lecture asynchrone vers le PBO courant
            glBindBuffer(GL_PIXEL_PACK_BUFFER, self.preview_pbo_ids[self.preview_pbo_index])
            glReadPixels(0, 0, target_w, target_h, GL_RGBA, GL_UNSIGNED_BYTE, 0)

            # 3. Récupérer les données du PBO précédent (Frame N-1)
            next_idx = (self.preview_pbo_index + 1) % 2
            glBindBuffer(GL_PIXEL_PACK_BUFFER, self.preview_pbo_ids[next_idx])
            
            # glGetBufferSubData récupère les données sans bloquer si le transfert est fini
            try:
                raw_data = glGetBufferSubData(GL_PIXEL_PACK_BUFFER, 0, size)
                arr = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) / 255.0
                arr = np.flip(arr.reshape((target_h, target_w, 4)), axis=0)
                self.node_editor.update_preview(arr.ravel())
            except Exception: pass

            glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            self.preview_pbo_index = next_idx

    def set_style(self, style):
        if style != self.current_style and style != "Auto-détection":
            self.current_style = style
            self.makeCurrent()
            self.update_shader()
            self.doneCurrent()
            self.update()

    def update_params(self, bloom, aberration, grain, glitch, vignette, scanline, contrast, saturation, brightness, gamma, exposure, strobe, light_leak, mirror, pixelate, posterize, solarize, hue_shift, invert, sepia, thermal, edge, fisheye, twist, ripple, mirror_quad, rgb_split, bleach, vhs, neon, cartoon, sketch, vibrate, drunk, pinch, zoom_blur, aura, psycho, modulations, compute_particles=False, particle_gravity=0.5, particle_life=3.0, particle_turbulence=1.0, particle_color=(0.2, 0.5, 1.0), particle_mode="rain", vr_mode=False, model_base_scale=1.0, model_enabled=True, model_speed=0.5, light2_color=(0.8, 0.2, 1.0), model_wireframe=False, model_deformation=0.0, model_reflection=0.0, model_ghosting=0.0, particle_size=2.0, distort_user_texture=False, texture_blend_mode="Mix", model_flat_shading=False, feedback_decay=0.0):
        self.bloom = bloom
        self.aberration = aberration
        self.grain = grain
        self.glitch = glitch
        self.vignette = vignette
        self.scanline = scanline
        self.contrast = contrast
        self.saturation = saturation
        self.brightness = brightness
        self.gamma = gamma
        self.exposure = exposure
        self.strobe = strobe
        self.light_leak = light_leak
        self.mirror = mirror
        self.pixelate = pixelate
        self.posterize = posterize
        self.solarize = solarize
        self.hue_shift = hue_shift
        self.invert = invert
        self.sepia = sepia
        self.thermal = thermal
        self.edge = edge
        self.fisheye = fisheye
        self.twist = twist
        self.ripple = ripple
        self.mirror_quad = mirror_quad
        self.rgb_split = rgb_split
        self.bleach = bleach
        self.vhs = vhs
        self.neon = neon
        self.cartoon = cartoon
        self.sketch = sketch
        self.vibrate = vibrate
        self.drunk = drunk
        self.pinch = pinch
        self.zoom_blur = zoom_blur
        self.aura = aura
        self.psycho = psycho
        self.modulations = modulations
        self.compute_particles_enabled = compute_particles
        self.particle_gravity = particle_gravity
        self.particle_life = particle_life
        self.particle_turbulence = particle_turbulence
        self.particle_color = particle_color
        self.particle_system.set_mode(particle_mode)
        self.particle_size = particle_size
        self.vr_mode = vr_mode
        self.model_base_scale = model_base_scale
        self.model_enabled = model_enabled
        self.model_speed = model_speed
        self.light2_color = light2_color
        self.model_wireframe = model_wireframe
        self.model_deformation = model_deformation
        self.model_reflection = model_reflection
        self.model_ghosting = model_ghosting
        self.distort_user_texture = distort_user_texture
        self.texture_blend_mode = texture_blend_mode
        self.model_flat_shading = model_flat_shading
        self.feedback_decay = feedback_decay
        self.update()

    def update_particle_count(self, count):
        self.makeCurrent()
        self.particle_system.set_particle_count(count)
        self.doneCurrent()
        self.update()
