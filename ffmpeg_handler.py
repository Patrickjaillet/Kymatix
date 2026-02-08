import subprocess
import os

class FFmpegHandler:
    @staticmethod
    def merge_audio_video(video_path, audio_path, output_path, bitrate="High Quality (CRF 18)", codec="H.264 (MP4)", logger=print):
        logger(f"\n🔊 Fusion audio + vidéo avec ffmpeg (Codec: {codec})...")
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error', '-stats',
            '-i', video_path
        ]
        
        if "GIF" not in codec:
            cmd.extend(['-i', audio_path])

        # Codec specific settings
        if "ProRes" in codec:
            cmd.extend(['-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0', '-bits_per_mb', '8000', '-pix_fmt', 'yuv422p10le'])
            cmd.extend(['-c:a', 'pcm_s16le'])
        elif "H.265" in codec:
            cmd.extend(['-c:v', 'libx265', '-preset', 'medium', '-pix_fmt', 'yuv420p'])
            cmd.extend(['-c:a', 'aac', '-b:a', '320k'])
            if "CRF" in bitrate:
                crf_val = bitrate.split("CRF ")[1].split(")")[0] if "CRF " in bitrate else "23"
                cmd.extend(['-crf', crf_val])
            elif "Mbps" in bitrate:
                cmd.extend(['-b:v', bitrate.split(" ")[0] + "M"])
        elif "VP9" in codec:
            cmd.extend(['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '30', '-c:a', 'libvorbis'])
        elif "GIF" in codec:
            cmd.extend(['-vf', 'fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse'])
        else: # H.264 Default
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-pix_fmt', 'yuv420p'])
            cmd.extend(['-c:a', 'aac', '-b:a', '320k'])
            if "CRF" in bitrate:
                crf_val = bitrate.split("CRF ")[1].split(")")[0] if "CRF " in bitrate else "18"
                cmd.extend(['-crf', crf_val])
            elif "Mbps" in bitrate:
                cmd.extend(['-b:v', bitrate.split(" ")[0] + "M"])
            
        if "GIF" not in codec:
            cmd.append('-shortest')
            
        cmd.append(output_path)

        try:
            subprocess.run(cmd, check=True)
            if os.path.exists(video_path): os.remove(video_path)
            logger(f"\n🎉 SUCCÈS! Vidéo exportée: {output_path}")
        except subprocess.CalledProcessError as e:
            logger(f"\n❌ Erreur ffmpeg: {e}")
        except FileNotFoundError:
            logger("\n❌ ffmpeg n'est pas installé!")

    @staticmethod
    def merge_rt_recording(video_path, audio_path, output_path, logger=print):
        logger("🎬 Fusion Audio/Vidéo...")
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-i', video_path, '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            output_path
        ]
        try:
            subprocess.run(cmd, check=True)
            if os.path.exists(video_path): os.remove(video_path)
            if os.path.exists(audio_path): os.remove(audio_path)
            logger(f"✅ Enregistrement terminé avec succès: {output_path}")
        except Exception as e:
            logger(f"❌ Erreur lors de la finalisation: {e}")

    @staticmethod
    def export_audio_segment(audio_path, output_path, duration=None, logger=print):
        logger(f"🔊 Export de l'audio vers: {output_path}")
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', audio_path]
        if duration:
            cmd.extend(['-t', str(duration)])
        cmd.extend(['-vn', '-acodec', 'copy', output_path])
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            logger(f"❌ Erreur export audio: {e}")
