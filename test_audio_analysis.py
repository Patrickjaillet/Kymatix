import unittest
from unittest.mock import patch
import numpy as np
import os
import sys

# Ensure we can import the module from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_analysis import AdvancedAudioAnalyzer, AdvancedAudioFeatures

class TestAdvancedAudioAnalyzer(unittest.TestCase):
    def setUp(self):
        # Create a synthetic audio signal: 2 seconds of 44100 Hz
        self.sr = 44100
        self.duration = 2.0
        t = np.linspace(0, self.duration, int(self.duration * self.sr), endpoint=False)
        
        # Mix of frequencies: 50Hz (Sub Bass), 440Hz (Low Mid), 5000Hz (Presence)
        # This ensures we have data across different frequency bands
        self.y = 0.5 * np.sin(2 * np.pi * 50 * t) + \
                 0.3 * np.sin(2 * np.pi * 440 * t) + \
                 0.2 * np.sin(2 * np.pi * 5000 * t)
        
        self.y = self.y.astype(np.float32)
        self.dummy_path = "test_audio.mp3"

    @patch('librosa.load')
    def test_initialization(self, mock_load):
        """Test if the analyzer initializes and computes features correctly."""
        mock_load.return_value = (self.y, self.sr)
        
        # Use a dummy logger to keep test output clean
        analyzer = AdvancedAudioAnalyzer(self.dummy_path, hop_length=512, logger=lambda x: None)
        
        self.assertEqual(analyzer.sr, self.sr)
        self.assertAlmostEqual(analyzer.duration, self.duration, places=1)
        
        # Verify that analysis arrays are populated
        self.assertTrue(len(analyzer.rms) > 0)
        self.assertTrue(len(analyzer.spectral_centroid) > 0)
        self.assertTrue(len(analyzer.beat_frames) >= 0) # Might be 0 for steady signals
        
        # Verify segmentation
        self.assertTrue(len(analyzer.segment_times) > 0)

    @patch('librosa.load')
    def test_get_features_at_time(self, mock_load):
        """Test feature extraction at a specific timestamp."""
        mock_load.return_value = (self.y, self.sr)
        analyzer = AdvancedAudioAnalyzer(self.dummy_path, logger=lambda x: None)
        
        # Test at 1.0 second
        features = analyzer.get_features_at_time(1.0)
        
        self.assertIsInstance(features, AdvancedAudioFeatures)
        
        # Check value ranges (0.0 to 1.0 for normalized features)
        self.assertTrue(0.0 <= features.sub_bass <= 1.0)
        self.assertTrue(0.0 <= features.intensity <= 1.0)
        self.assertTrue(0.0 <= features.brilliance <= 1.0)
        
        # Check specific fields exist
        self.assertTrue(hasattr(features, 'beat_strength'))
        self.assertTrue(hasattr(features, 'segment_type'))

    @patch('librosa.load')
    def test_get_spectrum_at_time(self, mock_load):
        """Test spectrum extraction."""
        mock_load.return_value = (self.y, self.sr)
        analyzer = AdvancedAudioAnalyzer(self.dummy_path, logger=lambda x: None)
        
        spectrum = analyzer.get_spectrum_at_time(1.0)
        
        self.assertIsInstance(spectrum, np.ndarray)
        # Default n_fft=2048 -> 1025 bins
        self.assertEqual(len(spectrum), 1025)
        
        # Test out of bounds time (should return zeros)
        spectrum_oob = analyzer.get_spectrum_at_time(10.0)
        self.assertEqual(np.sum(spectrum_oob), 0.0)

    @patch('librosa.load')
    def test_audio_presets(self, mock_load):
        """Test if applying EQ presets works without error."""
        mock_load.return_value = (self.y.copy(), self.sr)
        
        # Test Bass Boost
        try:
            AdvancedAudioAnalyzer(self.dummy_path, audio_preset="Bass Boost", logger=lambda x: None)
        except Exception as e:
            self.fail(f"Bass Boost preset raised exception: {e}")

        # Test Vocal Boost
        try:
            AdvancedAudioAnalyzer(self.dummy_path, audio_preset="Vocal Boost", logger=lambda x: None)
        except Exception as e:
            self.fail(f"Vocal Boost preset raised exception: {e}")

if __name__ == '__main__':
    unittest.main()