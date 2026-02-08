import os
import random
import sys
from pathlib import Path

# This script attempts to import the actual project classes.
# If some modules are not yet available, it falls back to dummy classes for demonstration.
try:
    from audio_analysis import AdvancedAudioAnalyzer as AudioAnalyzer
    # NOTE: The classes below are placeholders until their modules (e.g., opengl_renderer.py) are created.
    from opengl_renderer import Renderer
    from video_exporter import VideoExporter
except ImportError:
    print("---")
    print("Warning: Could not import all required modules. Using dummy classes for Renderer/Exporter.")
    print("---")
    class AudioAnalyzer:
        def __init__(self, path): print(f"  [DUMMY] Analyzing {Path(path).name}...")
        def analyze(self): return {}
    class Renderer:
        def __init__(self, preset): print(f"  [DUMMY] Initializing renderer with {Path(preset).name}...")
        def process(self, features):
            print("  [DUMMY] Simulating frame generation...")
            for _ in range(10): yield b'' # Yield dummy byte data
    class VideoExporter:
        def __init__(self, path, resolution, fps): self.path = path
        def __enter__(self):
            print(f"  [DUMMY] Opening video exporter for {Path(self.path).name}...")
            return self
        def __exit__(self, type, value, traceback): print(f"  [DUMMY] Closing video exporter.")
        def write_frame(self, data): pass


def batch_render(audio_dir, preset_dir, output_dir):
    """
    Processes all audio files in a directory, applying a random preset
    to each and exporting a video.
    """
    print(f"--- Starting Batch Render ---")
    print(f"Audio Source: {audio_dir}")
    print(f"Presets:      {preset_dir}")
    print(f"Output:       {output_dir}")
    print("-" * 29)

    # 1. Find all audio and preset files
    try:
        audio_files = [p for p in Path(audio_dir).glob('*') if p.suffix.lower() in ['.mp3', '.wav', '.flac']]
        preset_files = list(Path(preset_dir).glob('*.json'))
    except FileNotFoundError as e:
        print(f"Error: Directory not found - {e.filename}", file=sys.stderr)
        return

    if not audio_files:
        print("Error: No audio files (.mp3, .wav, .flac) found in the specified directory.", file=sys.stderr)
        return
    if not preset_files:
        print("Error: No preset files (.json) found in the specified directory.", file=sys.stderr)
        return

    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 2. Process each audio file
    for i, audio_path in enumerate(audio_files):
        print(f"\n[{i+1}/{len(audio_files)}] Processing: {audio_path.name}")

        random_preset = random.choice(preset_files)
        output_filename = f"{audio_path.stem}.mp4"
        output_path = Path(output_dir) / output_filename

        try:
            analyzer = AudioAnalyzer(str(audio_path))
            audio_features = analyzer.analyze()

            renderer = Renderer(preset=str(random_preset))

            with VideoExporter(str(output_path), resolution=(1920, 1080), fps=60) as exporter:
                for frame_data in renderer.process(audio_features):
                    exporter.write_frame(frame_data)
            
            print(f"✅ Successfully exported: {output_path}")

        except Exception as e:
            print(f"❌ An error occurred while processing {audio_path.name}: {e}", file=sys.stderr)
            continue

    print("\n--- Batch Render Complete ---")


if __name__ == "__main__":
    # --- Configuration ---
    # Please change these paths to match your project structure.
    # It's recommended to use absolute paths.
    AUDIO_FOLDER = "path/to/your/music"
    PRESETS_FOLDER = "path/to/your/presets"
    OUTPUT_FOLDER = "path/to/your/output_videos"
    # ---------------------

    if "path/to" in AUDIO_FOLDER:
        print("Warning: Please configure the folder paths in the script before running.", file=sys.stderr)
    else:
        batch_render(AUDIO_FOLDER, PRESETS_FOLDER, OUTPUT_FOLDER)