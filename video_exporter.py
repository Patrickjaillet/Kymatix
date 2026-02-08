import os
import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import cv2
import pygame
import wave
import numpy as np
from pygame.locals import *
from OpenGL.GL import *

from audio_analysis import AdvancedAudioAnalyzer, MusicStyleClassifier, RealTimeAudioAnalyzer
from shader_generator import ProceduralShaderGenerator
from opengl_renderer import OpenGLRenderer
from overlay_manager import OverlayManager
from ffmpeg_handler import FFmpegHandler
from ai_style import StyleTransferEngine

@dataclass
class RenderConfig:
    """Configuration pour l'export vidéo"""
    audio_path: str
    output_path: str
    width: int = 1920
    height: int = 1080
    fps: int = 60
    auto_detect_style: bool = True
    forced_style: Optional[str] = None
    save_json: bool = False
    export_format: str = "video" # video, png_seq, exr_seq
    video_bitrate: str = "High Quality (CRF 18)"
    codec: str = "H.264 (MP4)"
    export_audio: bool = False
    song_title: str = ""
    artist_name: str = ""
    
    # FX Parameters
    bloom_strength: float = 0.5
    aberration_strength: float = 0.1
    grain_strength: float = 0.05
    glitch_strength: float = 0.0
    vignette_strength: float = 0.0
    scanline_strength: float = 0.0
    contrast_strength: float = 1.0
    saturation_strength: float = 1.0
    brightness_strength: float = 0.0
    gamma_strength: float = 1.0
    exposure_strength: float = 1.0
    strobe_strength: float = 0.0
    light_leak_strength: float = 0.0
    mirror_strength: float = 0.0
    pixelate_strength: float = 0.0
    posterize_strength: float = 0.0
    solarize_strength: float = 0.0
    hue_shift_strength: float = 0.0
    invert_strength: float = 0.0
    sepia_strength: float = 0.0
    thermal_strength: float = 0.0
    edge_strength: float = 0.0
    fisheye_strength: float = 0.0
    twist_strength: float = 0.0
    ripple_strength: float = 0.0
    mirror_quad_strength: float = 0.0
    rgb_split_strength: float = 0.0
    bleach_strength: float = 0.0
    vhs_strength: float = 0.0
    neon_strength: float = 0.0
    cartoon_strength: float = 0.0
    sketch_strength: float = 0.0
    vibrate_strength: float = 0.0
    drunk_strength: float = 0.0
    pinch_strength: float = 0.0
    zoom_blur_strength: float = 0.0
    aura_strength: float = 0.0
    psycho_strength: float = 0.0
    
    # Logic
    dynamic_style: bool = False
    autopilot: bool = False
    autopilot_timer: int = 15
    autopilot_on_drop: bool = False
    modulations: List = field(default_factory=list)
    
    # Overlay & System
    scroller_font: str = "Arial"
    scroller_color: Tuple[int, int, int] = (255, 255, 255)
    text_effect: str = "Scroll"
    allowed_styles: Optional[List[str]] = None
    audio_preset: str = "Flat"
    srt_path: Optional[str] = None
    spectrogram_bg_color: Tuple[int, int, int, int] = (0, 0, 0, 128)
    spectrogram_position: str = "Bas"
    logo_path: Optional[str] = None
    spectrogram_enabled: bool = False
    video_source: Optional[str] = None
    pbo_enabled: bool = True
    vr_mode: bool = False
    user_texture_path: Optional[str] = None
    distort_user_texture: bool = False
    texture_blend_mode: str = "Mix"
    
    # AI Style Transfer
    ai_enabled: bool = False
    ai_model: Optional[str] = None
    ai_strength: float = 1.0
    
    # VST Effects
    vst_enabled: bool = False
    vst_model: Optional[str] = None
    vst_mix: float = 1.0

class AdvancedVideoExporter:
    """Exporteur vidéo avec génération procédurale de shaders"""
    
    def __init__(self, config: RenderConfig, logger=print):
        self.config = config
        self.logger = logger
        
        self.width = config.width - (config.width % 2)
        self.height = config.height - (config.height % 2)
        
        self.params = {
            'bloom_strength': config.bloom_strength, 'aberration_strength': config.aberration_strength, 
            'grain_strength': config.grain_strength, 'glitch_strength': config.glitch_strength, 
            'vignette_strength': config.vignette_strength, 'scanline_strength': config.scanline_strength, 
            'contrast_strength': config.contrast_strength, 'saturation_strength': config.saturation_strength, 
            'brightness_strength': config.brightness_strength, 'gamma_strength': config.gamma_strength, 
            'exposure_strength': config.exposure_strength, 'strobe_strength': config.strobe_strength, 
            'light_leak_strength': config.light_leak_strength, 'mirror_strength': config.mirror_strength,
            'pixelate_strength': config.pixelate_strength, 'posterize_strength': config.posterize_strength, 
            'solarize_strength': config.solarize_strength, 'hue_shift_strength': config.hue_shift_strength,
            'invert_strength': config.invert_strength, 'sepia_strength': config.sepia_strength, 
            'thermal_strength': config.thermal_strength, 'edge_strength': config.edge_strength,
            'fisheye_strength': config.fisheye_strength, 'twist_strength': config.twist_strength,
            'ripple_strength': config.ripple_strength, 'mirror_quad_strength': config.mirror_quad_strength,
            'rgb_split_strength': config.rgb_split_strength, 'bleach_strength': config.bleach_strength,
            'vhs_strength': config.vhs_strength, 'neon_strength': config.neon_strength, 'cartoon_strength': config.cartoon_strength,
            'sketch_strength': config.sketch_strength, 'vibrate_strength': config.vibrate_strength, 'drunk_strength': config.drunk_strength,
            'pinch_strength': config.pinch_strength, 'zoom_blur_strength': config.zoom_blur_strength, 'aura_strength': config.aura_strength,
            'psycho_strength': config.psycho_strength
        }
        
        self.available_styles = config.allowed_styles if config.allowed_styles else ProceduralShaderGenerator.get_available_styles()
        self.style_mapping = {
            "electronic": "geometric_tunnel", "rock": "crystal", "metal": "glitch_art",
            "jazz": "volumetric_light", "ambient": "aquatic", "pop": "vaporwave",
            "vaporwave": "vaporwave", "lofi": "lofi", "fractal": "fractal", "abstract_geometry": "abstract_geometry"
        }

        audio_path_for_analysis = config.audio_path

        # VST Processing before analysis
        if config.vst_enabled and config.vst_model:
            from vst_manager import VSTManager
            import soundfile as sf
            import librosa
            self.logger("🎧 Applying VST effect for render...")
            vst_manager = VSTManager(logger=self.logger)
            vst_path = vst_manager.scan_plugins().get(config.vst_model)
            if vst_path and vst_manager.load_plugin(vst_path):
                y, sr = librosa.load(config.audio_path, sr=44100, mono=False)
                y_processed = vst_manager.process_buffer(y, sr, config.vst_mix)
                
                temp_vst_path = "temp_render_vst.wav"
                sf.write(temp_vst_path, y_processed.T, sr)
                audio_path_for_analysis = temp_vst_path
                self.logger("✅ VST effect applied and saved to temporary file.")
            else:
                self.logger("❌ Could not load VST plugin for render.")

        if config.audio_path:
            self.logger("=" * 50)
            self.logger("🎬 DÉMARRAGE DU MOTEUR DE RENDU")
            self.logger("=" * 50)
            self.analyzer = AdvancedAudioAnalyzer(audio_path_for_analysis, audio_preset=config.audio_preset, logger=self.logger)
            computed_style, computed_profile = MusicStyleClassifier.classify(self.analyzer)
            if config.auto_detect_style and config.forced_style is None:
                self.style = computed_style
                self.profile = computed_profile
                self.logger(f"\n🎼 Style détecté: {self.style.upper()}")
            else:
                self.style = config.forced_style or "fractal"
                self.profile = computed_profile
                self.logger(f"\n🎼 Style forcé: {self.style.upper()}")
        else:
            self.style = config.forced_style or "fractal"
            self.profile = {'tempo': 120, 'energy': 0.5}
            self.analyzer = None
            
        if config.save_json:
            json_path = os.path.splitext(config.output_path)[0] + "_analysis.json"
            try:
                with open(json_path, 'w') as f: json.dump(self.profile, f, indent=4)
                self.logger(f"💾 Profil d'analyse sauvegardé: {json_path}")
            except Exception as e: self.logger(f"⚠️ Erreur sauvegarde JSON: {e}")
        
        self.logger("🖥️  Initialisation OpenGL...")
        try:
            self.renderer = OpenGLRenderer(self.width, self.height)
            self.renderer.set_pbo_enabled(config.pbo_enabled)
            self.overlay = OverlayManager(self.width, self.height)
            
            scroller_text = f"   +++   {config.artist_name.upper()} - {config.song_title.upper()}   +++   " if config.song_title or config.artist_name else ""
            self.overlay.setup_scroller(scroller_text, config.scroller_font, config.scroller_color)
            self.overlay.setup_subtitles(config.srt_path)
            self.overlay.setup_logo(config.logo_path)
            self.overlay.setup_spectrogram(config.spectrogram_enabled, config.spectrogram_position, config.spectrogram_bg_color)
            
            self.logger("✅ Initialisation terminée!\n")
            
            # Load User Texture if present
            self.user_texture_id = None
            if config.user_texture_path and os.path.exists(config.user_texture_path):
                try:
                    img = cv2.imread(config.user_texture_path)
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
                        self.logger(f"🖼️ Texture utilisateur chargée pour l'export.")
                except Exception as e:
                    self.logger(f"⚠️ Erreur chargement texture utilisateur: {e}")

        except Exception as e:
            pygame.quit()
            raise e
            
        # Initialize AI Engine
        self.ai_engine = None
        if config.ai_enabled and config.ai_model:
            self.logger("🧠 Initialisation du moteur IA...")
            self.ai_engine = StyleTransferEngine()
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style_models", config.ai_model)
            if self.ai_engine.load_model(model_path):
                self.logger(f"✅ Modèle IA chargé: {config.ai_model}")
            else:
                self.logger(f"❌ Erreur chargement modèle IA: {config.ai_model}")
                self.ai_engine = None

    def export(self, preview_window: bool = False, progress_callback=None, check_cancel=None, merge_callback=None, max_duration=None, macro_data=None):
        is_sequence = self.config.export_format in ["png_seq", "exr_seq"]
        out = None
        temp_video = None

        if not is_sequence:
            temp_video = "temp_visual.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video, fourcc, self.config.fps, (self.width, self.height))
        else:
            if not os.path.exists(self.config.output_path):
                os.makedirs(self.config.output_path, exist_ok=True)
            self.logger(f"📁 Export Séquence Images vers: {self.config.output_path}")
        
        duration = self.analyzer.duration
        if max_duration: duration = min(duration, max_duration)
        total_frames = int(duration * self.config.fps)
        
        self.logger(f"🎥 Rendu de {total_frames} frames ({duration:.1f}s)...")
        macro_idx = 0
        last_autopilot_time = -100.0
        
        # Video Input Init
        cap = None
        if self.config.video_source:
            if self.config.video_source == "Webcam":
                cap = cv2.VideoCapture(0)
            elif os.path.exists(self.config.video_source):
                cap = cv2.VideoCapture(self.config.video_source)
            self.logger(f"📹 Video Input: {self.config.video_source}")
        
        try:
            for frame_num in range(total_frames):
                if check_cancel and check_cancel():
                    self.logger("\n⚠️  Export annulé par l'utilisateur")
                    return

                time = frame_num / self.config.fps
                features = self.analyzer.get_features_at_time(time)
                spectrum = self.analyzer.get_spectrum_at_time(time)
                
                # Style Logic
                # Macro Playback override
                while macro_data and macro_idx < len(macro_data):
                    event = macro_data[macro_idx]
                    if time >= event['time']:
                        # Gestion des styles (nouveau format et legacy)
                        if event.get('type') == 'style':
                            self.style = event['value']
                            self.logger(f"⏱️ Macro: Style changé pour {self.style} à {time:.2f}s")
                        elif 'style' in event: # Legacy support
                            self.style = event['style']
                            self.logger(f"⏱️ Macro: Style changé pour {self.style} à {time:.2f}s")
                        # Gestion des paramètres (sliders MIDI)
                        elif event.get('type') == 'param':
                            param_name = event['name']
                            if param_name in self.params:
                                self.params[param_name] = event['value']
                        
                        macro_idx += 1
                    else:
                        break

                # Auto-Pilot Logic
                if self.config.autopilot:
                    should_change = False
                    
                    # Timer based
                    if self.config.autopilot_timer > 0 and (time - last_autopilot_time) >= self.config.autopilot_timer:
                        should_change = True
                        self.logger(f"🤖 Auto-Pilot: Timer trigger at {time:.2f}s")

                    # Drop based
                    if self.config.autopilot_on_drop:
                        if features.glitch_intensity > 0.7 and (time - last_autopilot_time) > 4.0:
                            should_change = True
                            self.logger(f"🤖 Auto-Pilot: Drop detected at {time:.2f}s")

                    if should_change:
                        import random
                        new_style = random.choice(self.available_styles)
                        if len(self.available_styles) > 1:
                            while new_style == self.style:
                                new_style = random.choice(self.available_styles)
                        self.style = new_style
                        last_autopilot_time = time

                if self.config.dynamic_style and not self.config.autopilot:
                    style_duration = 10.0
                    style_index = int(time / style_duration)
                    style1 = self.available_styles[style_index % len(self.available_styles)]
                    style2 = self.available_styles[(style_index + 1) % len(self.available_styles)]
                    progress = max(0.0, (time % style_duration - 8.0) / 2.0)
                    shader_code = ProceduralShaderGenerator.generate_shader(style1, self.profile, style2, progress, vr_mode=self.config.vr_mode)
                else:
                    base = self.style_mapping.get(self.style, self.style) if self.style in self.style_mapping or self.style in self.available_styles else "fractal"
                    shader_code = ProceduralShaderGenerator.generate_shader(base, self.profile, vr_mode=self.config.vr_mode)
                
                # Apply Modulations
                current_params = self.params.copy()
                for mod in self.config.modulations:
                    if hasattr(features, mod['source']) and mod['target'] in current_params:
                        source_val = getattr(features, mod['source'])
                        current_params[mod['target']] += source_val * mod['amount']

                program = self.renderer.get_program(shader_code, ProceduralShaderGenerator.VERTEX_SHADER)
                
                # Update iChannel0
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        # Resize to fit if needed, or just upload
                        # frame = cv2.resize(frame, (self.width, self.height))
                        if not hasattr(self, 'video_texture'):
                            self.video_texture = glGenTextures(1)
                        glBindTexture(GL_TEXTURE_2D, self.video_texture)
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, frame.shape[1], frame.shape[0], 0, GL_BGR, GL_UNSIGNED_BYTE, frame)

                # Uniforms
                uniforms = {
                    'resolution': (float(self.width), float(self.height)), 'time': time,
                    'sub_bass': features.sub_bass, 'bass': features.bass, 'low_mid': features.low_mid,
                    'mid': features.mid, 'high_mid': features.high_mid, 'presence': features.presence,
                    'brilliance': features.brilliance, 'beat_strength': features.beat_strength,
                    'intensity': features.intensity, 'spectral_centroid': features.spectral_centroid / 22050.0,
                    'spectral_flux': min(features.spectral_flux / 10.0, 1.0),
                    'glitch_intensity': min(1.0, features.glitch_intensity + current_params['glitch_strength']),
                    'is_chorus': 1.0 if features.segment_type == 'chorus' else 0.0
                }
                for k, v in current_params.items(): uniforms[k] = v
                
                if hasattr(self, 'video_texture'):
                    glActiveTexture(GL_TEXTURE0)
                    glBindTexture(GL_TEXTURE_2D, self.video_texture)
                    uniforms['iChannel0'] = 0
                
                if self.user_texture_id:
                    glActiveTexture(GL_TEXTURE1)
                    glBindTexture(GL_TEXTURE_2D, self.user_texture_id)
                    uniforms['userTexture'] = 1
                    uniforms['hasUserTexture'] = 1.0
                    uniforms['distortUserTexture'] = 1.0 if self.config.distort_user_texture else 0.0
                    
                    mode_map = {"Mix": 0, "Add": 1, "Multiply": 2, "Screen": 3}
                    uniforms['userTextureBlendMode'] = mode_map.get(self.config.texture_blend_mode, 0)
                else:
                    uniforms['hasUserTexture'] = 0.0
                
                self.renderer.render_to_fbo(program, uniforms)
                self.overlay.render(time, self.config.text_effect, spectrum)
                
                pixels = self.renderer.read_pixels()
                self.renderer.blit_to_screen()
                
                if preview_window:
                    pygame.display.flip()
                    for event in pygame.event.get():
                        if event.type == QUIT: return
                else:
                    pygame.event.pump()
                
                frame = np.frombuffer(pixels, dtype=np.uint8).reshape(self.height, self.width, 3)
                frame = cv2.flip(frame, 0)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Apply AI Style Transfer
                if self.ai_engine:
                    frame = self.ai_engine.process_frame(frame, self.config.ai_strength)
                
                if is_sequence:
                    ext = "png" if self.config.export_format == "png_seq" else "exr"
                    filename = os.path.join(self.config.output_path, f"frame_{frame_num:05d}.{ext}")
                    cv2.imwrite(filename, frame)
                else:
                    out.write(frame)
                
                if frame_num == total_frames // 2 and not max_duration:
                    thumb_path = os.path.join(self.config.output_path if is_sequence else os.path.dirname(self.config.output_path), "thumbnail.jpg")
                    cv2.imwrite(thumb_path, frame)
                
                if progress_callback and (frame_num % self.config.fps == 0 or frame_num == total_frames - 1):
                    progress_callback((frame_num + 1) / total_frames * 100)
            
            self.logger("\n✅ Rendu visuel terminé!")
        finally:
            if out: out.release()
            if cap: cap.release()
            self.renderer.cleanup()
        
        if not is_sequence:
            if merge_callback: merge_callback()
            FFmpegHandler.merge_audio_video(temp_video, self.config.audio_path, self.config.output_path, self.config.video_bitrate, self.config.codec, self.logger)
        elif self.config.export_audio and self.config.audio_path:
            # Export audio séparé pour les séquences d'images
            ext = os.path.splitext(self.config.audio_path)[1]
            audio_out = os.path.join(self.config.output_path, f"audio{ext}")
            FFmpegHandler.export_audio_segment(self.config.audio_path, audio_out, duration if max_duration else None, self.logger)

    def visualize(self, check_cancel=None, output_path=None, input_device_index=None, merge_callback=None):
        try: import pyaudio
        except ImportError:
            self.logger("❌ Erreur: PyAudio n'est pas installé.")
            return

        self.logger("🎤 Démarrage du Visualiseur Temps Réel...")
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paFloat32, channels=1, rate=44100, input=True, input_device_index=input_device_index, frames_per_buffer=1024)
        except Exception as e:
            self.logger(f"❌ Erreur Audio: {e}")
            return

        rt_analyzer = RealTimeAudioAnalyzer(sr=44100, buffer_size=1024)
        recorder = None
        audio_frames = []
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            recorder = cv2.VideoWriter("temp_rt.mp4", fourcc, self.config.fps, (self.width, self.height))
            self.logger(f"🔴 Enregistrement activé vers: {output_path}")

        clock = pygame.time.Clock()
        start_time = pygame.time.get_ticks()
        
        try:
            running = True
            while running:
                if check_cancel and check_cancel(): break
                for event in pygame.event.get():
                    if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE): running = False
                
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_buffer = np.frombuffer(data, dtype=np.float32)
                except: continue
                    
                features = rt_analyzer.process(audio_buffer)
                time = (pygame.time.get_ticks() - start_time) / 1000.0
                
                shader_code = ProceduralShaderGenerator.generate_shader(self.style, self.profile, vr_mode=self.config.vr_mode)
                program = self.renderer.get_program(shader_code, ProceduralShaderGenerator.VERTEX_SHADER)
                
                uniforms = {
                    'resolution': (float(self.width), float(self.height)), 'time': time,
                    'sub_bass': features.sub_bass, 'bass': features.bass, 'low_mid': features.low_mid,
                    'mid': features.mid, 'high_mid': features.high_mid, 'presence': features.presence,
                    'brilliance': features.brilliance, 'beat_strength': features.beat_strength,
                    'intensity': features.intensity, 'spectral_centroid': 0.5, 'spectral_flux': 0.0,
                    'glitch_intensity': min(1.0, features.glitch_intensity + self.params['glitch_strength']),
                    'is_chorus': 0.0
                }
                for k, v in self.params.items(): uniforms[k] = v
                
                self.renderer.render_to_fbo(program, uniforms)
                self.overlay.render(time, self.config.text_effect, rt_analyzer.current_magnitude)
                
                if recorder:
                    pixels = self.renderer.read_pixels()
                    frame = np.frombuffer(pixels, dtype=np.uint8).reshape(self.height, self.width, 3)
                    frame = cv2.flip(frame, 0)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    recorder.write(frame)
                    audio_frames.append((audio_buffer * 32767).astype(np.int16).tobytes())

                self.renderer.blit_to_screen()
                clock.tick(self.config.fps)
                pygame.display.flip()
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            self.renderer.cleanup()
            if recorder: recorder.release()
        
        if recorder:
            self.logger("💾 Sauvegarde de l'audio temporaire...")
            try:
                with wave.open("temp_rt.wav", 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(b''.join(audio_frames))
                if merge_callback: merge_callback()
                FFmpegHandler.merge_rt_recording("temp_rt.mp4", "temp_rt.wav", output_path, self.logger)
            except Exception as e: self.logger(f"❌ Erreur finalisation: {e}")
