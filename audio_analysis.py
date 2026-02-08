from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import json
import os
import hashlib
import librosa
from scipy import signal
from scipy.ndimage import gaussian_filter1d

@dataclass
class AdvancedAudioFeatures:
    """Features audio détaillées pour génération procédurale"""
    # Bandes de fréquences (0-1)
    sub_bass: float = 0.0      # 20-60 Hz
    bass: float = 0.0           # 60-250 Hz
    low_mid: float = 0.0        # 250-500 Hz
    mid: float = 0.0            # 500-2000 Hz
    high_mid: float = 0.0       # 2000-4000 Hz
    presence: float = 0.0       # 4000-6000 Hz
    brilliance: float = 0.0     # 6000+ Hz
    
    # Caractéristiques rythmiques
    beat_strength: float = 0.0
    tempo: float = 120.0
    onset_detected: bool = False
    
    # Caractéristiques spectrales
    spectral_centroid: float = 0.0
    spectral_bandwidth: float = 0.0
    spectral_rolloff: float = 0.0
    spectral_flux: float = 0.0
    
    # Caractéristiques harmoniques
    harmonicity: float = 0.0
    pitch: float = 0.0
    
    # Énergie globale
    rms_energy: float = 0.0
    zcr: float = 0.0  # Zero Crossing Rate
    
    # Méta-données de segment
    segment_type: str = "neutral"  # intro, verse, chorus, bridge, outro
    intensity: float = 0.5  # 0-1
    glitch_intensity: float = 0.0  # 0-1, pour effets de drops/glitch


# Définition centralisée des bandes de fréquences (Hz)
FREQUENCY_BANDS = {
    'sub_bass': (20, 60),
    'bass': (60, 250),
    'low_mid': (250, 500),
    'mid': (500, 2000),
    'high_mid': (2000, 4000),
    'presence': (4000, 6000),
    'brilliance': (6000, 20000)
}

class AdvancedAudioAnalyzer:
    """Analyseur audio ultra-détaillé pour génération procédurale"""
    
    def __init__(self, audio_path: str, hop_length: int = 512, audio_preset: str = "Flat", logger=print):
        self.audio_path = audio_path
        self.hop_length = hop_length
        self.logger = logger
        
        # Tentative de chargement depuis le cache
        if self._load_from_cache():
            self.logger("⚡ Analyse chargée depuis le cache !")
            self._precompute_frequency_masks()
            return

        self.logger("🎵 Chargement de l'audio...")
        self.y, self.sr = librosa.load(audio_path, sr=44100)
        
        if audio_preset != "Flat":
            self.logger(f"🎚️ Application du preset audio: {audio_preset}")
            self._apply_eq(audio_preset)
            
        self.duration = librosa.get_duration(y=self.y, sr=self.sr)
        
        self.logger("📊 Analyse globale...")
        self._analyze_global_features()
        
        self.logger("🎼 Analyse spectrale détaillée...")
        self._compute_spectral_features()
        
        self.logger("🥁 Détection de beats et tempo...")
        self._analyze_rhythm()
        
        self.logger("🎹 Segmentation musicale...")
        self._segment_audio()
        
        self.logger("⚡ Détection des drops...")
        self._analyze_drops()
        
        # Pré-calcul des masques de fréquences (Optimisation CPU)
        self._precompute_frequency_masks()

        # Sauvegarde dans le cache
        self._save_to_cache()
        self.logger("✅ Analyse terminée!")

    def _get_cache_path(self):
        """Génère un chemin de cache unique basé sur le chemin du fichier et sa date de modif."""
        try:
            mtime = os.path.getmtime(self.audio_path)
            unique_str = f"{self.audio_path}_{mtime}_{self.hop_length}"
            file_hash = hashlib.md5(unique_str.encode('utf-8')).hexdigest()
            return os.path.join(os.path.dirname(self.audio_path), f".{os.path.basename(self.audio_path)}.{file_hash}.analysis.json")
        except Exception:
            return None

    def _save_to_cache(self):
        """Sérialise et sauvegarde les données d'analyse."""
        cache_path = self._get_cache_path()
        if not cache_path: return

        data = {
            "duration": self.duration,
            "sr": self.sr,
            "tempo": self.tempo,
            "beat_frames": self.beat_frames.tolist() if isinstance(self.beat_frames, np.ndarray) else list(self.beat_frames),
            "onset_times": self.onset_times.tolist() if isinstance(self.onset_times, np.ndarray) else list(self.onset_times),
            "rms": self.rms.tolist(),
            "zcr": self.zcr.tolist(),
            "spectral_centroid": self.spectral_centroid.tolist(),
            "spectral_bandwidth": self.spectral_bandwidth.tolist(),
            "spectral_rolloff": self.spectral_rolloff.tolist(),
            "spectral_flux": self.spectral_flux.tolist(),
            "beat_strength": self.beat_strength.tolist(),
            "segment_times": self.segment_times.tolist() if isinstance(self.segment_times, np.ndarray) else list(self.segment_times),
            "segment_types": self.segment_types,
            "drop_curve": self.drop_curve.tolist() if isinstance(self.drop_curve, np.ndarray) else list(self.drop_curve),
            # Note: On ne sauvegarde pas self.y (trop lourd) ni self.D (recalculable si besoin, ou on accepte de ne pas l'avoir pour get_spectrum)
        }
        
        # Pour self.D (Spectrogramme), c'est lourd. On peut choisir de ne pas le cacher 
        # et de le laisser vide ou de le recalculer rapidement si besoin.
        # Pour cette optimisation, on va ignorer self.D et self.chroma pour garder le cache léger,
        # et on les initialisera à vide. Les features scalaires sont les plus importantes.

        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.logger(f"⚠️ Impossible de sauvegarder le cache: {e}")

    def _load_from_cache(self):
        """Charge les données depuis le cache si disponible."""
        cache_path = self._get_cache_path()
        if not cache_path or not os.path.exists(cache_path):
            return False

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            self.duration = data["duration"]
            self.sr = data["sr"]
            self.tempo = data["tempo"]
            self.beat_frames = np.array(data["beat_frames"])
            self.onset_times = np.array(data["onset_times"])
            self.rms = np.array(data["rms"])
            self.zcr = np.array(data["zcr"])
            self.spectral_centroid = np.array(data["spectral_centroid"])
            self.spectral_bandwidth = np.array(data["spectral_bandwidth"])
            self.spectral_rolloff = np.array(data["spectral_rolloff"])
            self.spectral_flux = np.array(data["spectral_flux"])
            self.beat_strength = np.array(data["beat_strength"])
            self.segment_times = np.array(data["segment_times"])
            self.segment_types = data["segment_types"]
            self.drop_curve = np.array(data["drop_curve"])
            
            # Reconstruction partielle pour éviter les erreurs
            self.onset_env = np.zeros_like(self.rms) # Non critique
            self.y = np.array([]) # On ne charge pas l'audio brut
            self.D = np.zeros((1025, len(self.rms))) # Placeholder
            self.freqs = np.linspace(0, self.sr/2, 1025)
            self.chroma = np.zeros((12, len(self.rms))) # Placeholder
            
            return True
        except Exception as e:
            self.logger(f"⚠️ Cache corrompu ou incompatible: {e}")
            return False
    
    def _apply_eq(self, preset):
        """Applique un EQ simple pour accentuer certaines fréquences avant analyse"""
        if preset == "Bass Boost":
            # Boost des basses fréquences (< 150Hz)
            sos = signal.butter(10, 150, 'lp', fs=self.sr, output='sos')
            filtered = signal.sosfilt(sos, self.y)
            self.y = self.y + filtered * 2.0
        elif preset == "Vocal Boost":
            # Boost des fréquences vocales (300Hz - 3400Hz)
            sos = signal.butter(10, [300, 3400], 'bp', fs=self.sr, output='sos')
            filtered = signal.sosfilt(sos, self.y)
            self.y = self.y + filtered * 2.0
            
        # Normalisation pour éviter le clipping virtuel dans l'analyse
        if np.max(np.abs(self.y)) > 0:
            self.y = self.y / np.max(np.abs(self.y))
    
    def _analyze_global_features(self):
        """Analyse des caractéristiques globales"""
        # Tempo et beats
        tempo, self.beat_frames = librosa.beat.beat_track(
            y=self.y, 
            sr=self.sr,
            hop_length=self.hop_length
        )
        self.tempo = float(tempo[0]) if np.ndim(tempo) > 0 else float(tempo)
        self.beat_times = librosa.frames_to_time(self.beat_frames, sr=self.sr, hop_length=self.hop_length)
        
        # Onset detection (attaques de notes)
        self.onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.onset_frames = librosa.onset.onset_detect(
            onset_envelope=self.onset_env,
            sr=self.sr,
            hop_length=self.hop_length
        )
        self.onset_times = librosa.frames_to_time(self.onset_frames, sr=self.sr, hop_length=self.hop_length)
        
        # Chromagram pour analyse harmonique
        self.chroma = librosa.feature.chroma_stft(y=self.y, sr=self.sr, hop_length=self.hop_length)
        
        # RMS Energy
        self.rms = librosa.feature.rms(y=self.y, hop_length=self.hop_length)[0]
        
        # Zero Crossing Rate
        self.zcr = librosa.feature.zero_crossing_rate(y=self.y, hop_length=self.hop_length)[0]
    
    def _compute_spectral_features(self):
        """Calcul des features spectrales détaillées"""
        # STFT pour analyse fréquentielle
        self.D = np.abs(librosa.stft(self.y, hop_length=self.hop_length))
        self.freqs = librosa.fft_frequencies(sr=self.sr)
        
        # Spectral Centroid (centre de masse du spectre)
        self.spectral_centroid = librosa.feature.spectral_centroid(
            y=self.y, sr=self.sr, hop_length=self.hop_length
        )[0]
        
        # Spectral Bandwidth (largeur du spectre)
        self.spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=self.y, sr=self.sr, hop_length=self.hop_length
        )[0]
        
        # Spectral Rolloff (fréquence en dessous de laquelle se trouve 85% de l'énergie)
        self.spectral_rolloff = librosa.feature.spectral_rolloff(
            y=self.y, sr=self.sr, hop_length=self.hop_length, roll_percent=0.85
        )[0]
        
        # Spectral Flux (changement spectral)
        self.spectral_flux = np.concatenate([
            [0],
            np.sqrt(np.sum(np.diff(self.D, axis=1)**2, axis=0))
        ])
        
        # Lissage des features
        self.spectral_centroid = gaussian_filter1d(self.spectral_centroid, sigma=2)
        self.spectral_bandwidth = gaussian_filter1d(self.spectral_bandwidth, sigma=2)
        self.spectral_flux = gaussian_filter1d(self.spectral_flux, sigma=2)
    
    def _analyze_rhythm(self):
        """Analyse rythmique détaillée"""
        # Tempogram pour variations de tempo
        self.tempogram = librosa.feature.tempogram(
            onset_envelope=self.onset_env,
            sr=self.sr,
            hop_length=self.hop_length
        )
        
        # Beat strength (force des beats)
        self.beat_strength = np.zeros(len(self.onset_env))
        for beat_frame in self.beat_frames:
            if beat_frame < len(self.beat_strength):
                self.beat_strength[beat_frame] = 1.0
        
        # Smooth beat strength
        self.beat_strength = gaussian_filter1d(self.beat_strength, sigma=1)
    
    def _segment_audio(self):
        """Segmentation automatique de la musique"""
        # Utiliser la matrice de récurrence pour détecter les structures
        mfcc = librosa.feature.mfcc(y=self.y, sr=self.sr, n_mfcc=13, hop_length=self.hop_length)
        
        # Détection des frontières de segments
        self.segment_boundaries = librosa.segment.agglomerative(
            mfcc, 
            k=8  # Nombre de segments
        )
        
        self.segment_times = librosa.frames_to_time(
            self.segment_boundaries,
            sr=self.sr,
            hop_length=self.hop_length
        )
        
        # Classification basique des segments selon leur énergie
        self.segment_types = []
        for i in range(len(self.segment_times) - 1):
            start_frame = self.segment_boundaries[i]
            end_frame = self.segment_boundaries[i + 1]
            
            avg_energy = np.mean(self.rms[start_frame:end_frame])
            
            if i == 0:
                seg_type = "intro"
            elif i == len(self.segment_times) - 2:
                seg_type = "outro"
            elif avg_energy > np.percentile(self.rms, 75):
                seg_type = "chorus"
            elif avg_energy < np.percentile(self.rms, 25):
                seg_type = "bridge"
            else:
                seg_type = "verse"
            
            self.segment_types.append(seg_type)
    
    def _analyze_drops(self):
        """Détection des drops et changements soudains d'intensité"""
        # Dérivée de l'énergie RMS (changements d'intensité)
        rms_diff = np.diff(self.rms, prepend=self.rms[0])
        rms_diff = np.maximum(0, rms_diff)  # On ne garde que les montées soudaines
        
        # Normalisation
        if np.max(rms_diff) > 0:
            rms_diff /= np.max(rms_diff)
            
        # Flux spectral (déjà calculé)
        flux = self.spectral_flux
        if len(flux) > 0 and np.max(flux) > 0:
            flux = flux / np.max(flux)
            
        # Combinaison pour le score de glitch : changement d'énergie + changement spectral
        min_len = min(len(rms_diff), len(flux))
        self.drop_curve = rms_diff[:min_len] * flux[:min_len]
        
        # Amplification des pics pour un effet "trigger"
        self.drop_curve = np.where(self.drop_curve > 0.2, self.drop_curve * 2.0, 0.0)
        self.drop_curve = np.clip(self.drop_curve, 0.0, 1.0)

    def _precompute_frequency_masks(self):
        """Pré-calcule les masques booléens pour les bandes de fréquences afin d'éviter le recalcul par frame."""
        self.freq_masks = {}
        if hasattr(self, 'freqs'):
            for band, (low, high) in FREQUENCY_BANDS.items():
                # On stocke le masque booléen une seule fois
                self.freq_masks[band] = (self.freqs >= low) & (self.freqs < high)

    def get_features_at_time(self, time: float) -> AdvancedAudioFeatures:
        """Extrait toutes les features à un instant donné"""
        # Optimisation: Calcul direct sans appel à librosa pour performance temps réel
        frame = int(time * self.sr / self.hop_length)
        frame = min(frame, len(self.onset_env) - 1)
        
        # Extraction des bandes de fréquences
        if frame < self.D.shape[1]:
            freq_bins = self.D[:, frame]
            
            # Définition des bandes
            # Utilisation des masques pré-calculés (Gain de perf significatif)
            sub_bass = np.mean(freq_bins[self.freq_masks['sub_bass']]) if 'sub_bass' in self.freq_masks else 0.0
            bass = np.mean(freq_bins[self.freq_masks['bass']]) if 'bass' in self.freq_masks else 0.0
            low_mid = np.mean(freq_bins[self.freq_masks['low_mid']]) if 'low_mid' in self.freq_masks else 0.0
            mid = np.mean(freq_bins[self.freq_masks['mid']]) if 'mid' in self.freq_masks else 0.0
            high_mid = np.mean(freq_bins[self.freq_masks['high_mid']]) if 'high_mid' in self.freq_masks else 0.0
            presence = np.mean(freq_bins[self.freq_masks['presence']]) if 'presence' in self.freq_masks else 0.0
            brilliance = np.mean(freq_bins[self.freq_masks['brilliance']]) if 'brilliance' in self.freq_masks else 0.0
            
            # Normalisation
            max_val = np.max(freq_bins) + 1e-6
            sub_bass /= max_val
            bass /= max_val
            low_mid /= max_val
            mid /= max_val
            high_mid /= max_val
            presence /= max_val
            brilliance /= max_val
        else:
            sub_bass = bass = low_mid = mid = high_mid = presence = brilliance = 0.0
        
        # Détection de beat
        onset_detected = any(abs(time - onset_time) < 0.05 for onset_time in self.onset_times)
        
        # Déterminer le type de segment actuel
        segment_type = "neutral"
        for i, seg_time in enumerate(self.segment_times[:-1]):
            if time >= seg_time and time < self.segment_times[i + 1]:
                if i < len(self.segment_types):
                    segment_type = self.segment_types[i]
                break
        
        # Calcul de l'intensité globale
        intensity = min(self.rms[frame] / (np.max(self.rms) + 1e-6), 1.0) if frame < len(self.rms) else 0.5
        
        # Valeur de glitch
        glitch = 0.0
        if frame < len(self.drop_curve):
            glitch = float(self.drop_curve[frame])

        return AdvancedAudioFeatures(
            sub_bass=float(sub_bass),
            bass=float(bass),
            low_mid=float(low_mid),
            mid=float(mid),
            high_mid=float(high_mid),
            presence=float(presence),
            brilliance=float(brilliance),
            beat_strength=float(self.beat_strength[frame]) if frame < len(self.beat_strength) else 0.0,
            tempo=float(self.tempo),
            onset_detected=onset_detected,
            spectral_centroid=float(self.spectral_centroid[frame]) if frame < len(self.spectral_centroid) else 0.0,
            spectral_bandwidth=float(self.spectral_bandwidth[frame]) if frame < len(self.spectral_bandwidth) else 0.0,
            spectral_rolloff=float(self.spectral_rolloff[frame]) if frame < len(self.spectral_rolloff) else 0.0,
            spectral_flux=float(self.spectral_flux[frame]) if frame < len(self.spectral_flux) else 0.0,
            harmonicity=float(np.max(self.chroma[:, frame])) if frame < self.chroma.shape[1] else 0.0,
            rms_energy=float(self.rms[frame]) if frame < len(self.rms) else 0.0,
            zcr=float(self.zcr[frame]) if frame < len(self.zcr) else 0.0,
            segment_type=segment_type,
            intensity=float(intensity),
            glitch_intensity=glitch
        )
        
    def get_spectrum_at_time(self, time: float) -> np.ndarray:
        """Retourne le spectre (magnitude) à un instant donné"""
        frame = int(time * self.sr / self.hop_length)
        if frame < self.D.shape[1]:
            return self.D[:, frame]
        return np.zeros(self.D.shape[0])

class MusicStyleClassifier:
    """Classifie automatiquement le style musical"""
    
    @staticmethod
    def classify(analyzer: AdvancedAudioAnalyzer) -> Tuple[str, Dict]:
        """Retourne le style et un profil de caractéristiques"""
        
        # Calcul des statistiques globales
        avg_tempo = float(analyzer.tempo)
        avg_energy = float(np.mean(analyzer.rms))
        avg_spectral_centroid = float(np.mean(analyzer.spectral_centroid))
        avg_zcr = float(np.mean(analyzer.zcr))
        onset_density = float(len(analyzer.onset_times) / analyzer.duration)
        
        # Analyse harmonique
        chroma_var = float(np.var(analyzer.chroma, axis=1).mean())
        
        profile = {
            'tempo': avg_tempo,
            'energy': avg_energy,
            'spectral_centroid': avg_spectral_centroid,
            'zcr': avg_zcr,
            'onset_density': onset_density,
            'chroma_var': chroma_var
        }
        
        # Classification basée sur les règles
        if avg_tempo > 130 and avg_energy > 0.1 and onset_density > 5:
            if avg_spectral_centroid > 3000:
                return "electronic", profile  # EDM, House, Techno
            else:
                return "rock", profile  # Rock, Metal
        
        elif avg_tempo < 100 and avg_energy < 0.08:
            return "ambient", profile  # Ambient, Chill
        
        elif chroma_var > 0.5 and onset_density > 3:
            return "jazz", profile  # Jazz, Funk
        
        elif avg_tempo > 110 and avg_tempo < 130:
            return "pop", profile  # Pop, R&B
        
        else:
            return "fractal", profile  # Style par défaut (fractal)

class RealTimeAudioAnalyzer:
    """Analyseur audio temps réel pour le visualiseur"""
    
    def __init__(self, sr=44100, buffer_size=1024):
        self.sr = sr
        self.buffer_size = buffer_size
        self.freqs = np.fft.rfftfreq(buffer_size, 1/sr)
        
        # Lissage temporel
        self.prev_features = None
        self.smooth_factor = 0.3
        self.current_magnitude = None
        
    def process(self, audio_buffer) -> AdvancedAudioFeatures:
        """Traite un buffer audio brut et retourne les features"""
        # Normalisation
        if np.max(np.abs(audio_buffer)) > 0:
            audio_buffer = audio_buffer / np.max(np.abs(audio_buffer))
            
        # FFT
        magnitude = np.abs(np.fft.rfft(audio_buffer))
        self.current_magnitude = magnitude
        
        # Calcul des bandes (simplifié pour le temps réel)
        def get_band_energy(min_freq, max_freq):
            mask = (self.freqs >= min_freq) & (self.freqs < max_freq)
            if np.any(mask):
                return float(np.mean(magnitude[mask]))
            return 0.0

        sub_bass = get_band_energy(*FREQUENCY_BANDS['sub_bass']) * 3.0
        bass = get_band_energy(*FREQUENCY_BANDS['bass']) * 2.0
        low_mid = get_band_energy(*FREQUENCY_BANDS['low_mid'])
        mid = get_band_energy(*FREQUENCY_BANDS['mid'])
        high_mid = get_band_energy(*FREQUENCY_BANDS['high_mid'])
        presence = get_band_energy(*FREQUENCY_BANDS['presence'])
        brilliance = get_band_energy(*FREQUENCY_BANDS['brilliance']) * 2.0
        
        # RMS / Intensité
        rms = float(np.sqrt(np.mean(audio_buffer**2)))
        intensity = min(rms * 5.0, 1.0)
        
        # Beat strength approximatif (basé sur les basses)
        beat_strength = min(bass * 3.0, 1.0) if bass > 0.1 else 0.0
        
        features = AdvancedAudioFeatures(
            sub_bass=min(sub_bass, 1.0),
            bass=min(bass, 1.0),
            low_mid=min(low_mid, 1.0),
            mid=min(mid, 1.0),
            high_mid=min(high_mid, 1.0),
            presence=min(presence, 1.0),
            brilliance=min(brilliance, 1.0),
            beat_strength=beat_strength,
            intensity=intensity,
            segment_type="neutral", # Difficile à déterminer en temps réel sans latence
            glitch_intensity=0.0
        )
        
        # Lissage
        if self.prev_features:
            for field in features.__dataclass_fields__:
                if field not in ['segment_type', 'onset_detected']:
                    curr = getattr(features, field)
                    prev = getattr(self.prev_features, field)
                    setattr(features, field, prev * self.smooth_factor + curr * (1 - self.smooth_factor))
        
        self.prev_features = features
        return features