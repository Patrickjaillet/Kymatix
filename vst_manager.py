import os
import numpy as np
import librosa

try:
    from pedalboard import load_plugin
except ImportError:
    load_plugin = None

class VSTManager:
    def __init__(self, logger=print):
        self.logger = logger
        self.plugin = None
        self.plugin_path = None
        self.vst_paths = self._get_vst_paths()
        self.found_plugins = {} # {name: path}
        
        if load_plugin is None:
            self.logger("⚠️ 'pedalboard' library not found. Please install it via 'pip install pedalboard'.")

    def _get_vst_paths(self):
        paths = []
        if os.name == 'nt': # Windows
            paths.extend([
                os.path.join(os.environ.get("ProgramFiles", ""), "VSTPlugins"),
                os.path.join(os.environ.get("ProgramFiles", ""), "Common Files", "VST3"),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "VSTPlugins"),
            ])
        elif os.name == 'posix': # macOS/Linux
            paths.extend([
                "/Library/Audio/Plug-Ins/VST",
                "/Library/Audio/Plug-Ins/VST3",
                os.path.expanduser("~/Library/Audio/Plug-Ins/VST"),
                os.path.expanduser("~/Library/Audio/Plug-Ins/VST3"),
                "/usr/lib/vst",
                "/usr/local/lib/vst",
            ])
        return [p for p in paths if os.path.isdir(p)]

    def scan_plugins(self):
        self.logger("🔍 Scanning for VST plugins...")
        self.found_plugins = {}
        for path in self.vst_paths:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(('.dll', '.vst3')):
                        plugin_path = os.path.join(root, file)
                        plugin_name = os.path.splitext(file)[0]
                        self.found_plugins[plugin_name] = plugin_path
        self.logger(f"✅ Found {len(self.found_plugins)} plugins.")
        return self.found_plugins

    def load_plugin(self, path):
        if load_plugin is None:
            return False

        if self.plugin_path == path and self.plugin is not None:
            return True
        
        self.logger(f"🔌 Loading VST: {os.path.basename(path)}")
        try:
            self.plugin = load_plugin(path)
            self.plugin_path = path
            self.logger(f"✅ VST Loaded: {self.plugin.name}")
            return True
        except Exception as e:
            self.logger(f"❌ Failed to load VST: {e}")
            self.plugin = None
            self.plugin_path = None
            return False

    def unload_plugin(self):
        self.plugin = None
        self.plugin_path = None

    def open_editor(self):
        if self.plugin:
            try:
                self.plugin.show_editor()
                self.logger(f"🖥️ Opening VST Editor for: {self.plugin.name}")
            except AttributeError:
                self.logger("⚠️ This plugin does not support showing an editor.")
            except Exception as e:
                self.logger(f"❌ Error opening editor: {e}")
        else:
            self.logger("⚠️ No VST plugin loaded.")

    def process_buffer(self, audio_buffer, sr, wet_dry_mix=1.0):
        if not self.plugin or audio_buffer is None:
            return audio_buffer

        # Prepare buffer for pedalboard (channels, samples)
        # Librosa loads as (channels, samples) or (samples,) if mono
        input_audio = audio_buffer
        is_mono_input = False
        
        if input_audio.ndim == 1:
            input_audio = input_audio[np.newaxis, :] # (1, samples)
            is_mono_input = True
        
        # Ensure float32
        if input_audio.dtype != np.float32:
            input_audio = input_audio.astype(np.float32)

        try:
            output_audio = self.plugin.process(input_audio, sample_rate=sr)
        except Exception as e:
            self.logger(f"❌ VST Process Error: {e}")
            return audio_buffer
            
        if wet_dry_mix < 1.0:
            # Handle channel expansion (Mono -> Stereo)
            if input_audio.shape[0] == 1 and output_audio.shape[0] == 2:
                input_audio = np.vstack([input_audio, input_audio])
            
            if input_audio.shape == output_audio.shape:
                output_audio = (output_audio * wet_dry_mix) + (input_audio * (1.0 - wet_dry_mix))
             
        # Return to original shape if possible (flatten if it was mono and output is still mono)
        if is_mono_input and output_audio.shape[0] == 1:
            return output_audio.flatten()
            
        return output_audio