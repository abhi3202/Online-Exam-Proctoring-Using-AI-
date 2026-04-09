# models/audio_analyzer.py

import pyaudio
import numpy as np
from typing import Dict, Any

class AudioAnalyzer:
    def __init__(self, sample_rate: int = 16000, chunk_duration: float = 2.0):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)

        self.pa = pyaudio.PyAudio()
        self.stream = None

        # Adaptive thresholds
        self.noise_floor_db = None   # measured during calibration
        self.loud_offset_db = 10.0   # how much louder than baseline counts as "LOUD_AUDIO"
        self.multi_voice_flatness_thresh = 0.5

    def start_recording(self):
        if self.stream:
            return
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )

    def stop_recording(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.pa.terminate()

    def get_next_chunk(self) -> np.ndarray:
        data = self.stream.read(self.chunk_size, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return audio

    def calibrate_noise_floor(self, seconds: int = 5):
        """Measure ambient noise for a few seconds to set baseline."""
        print("Calibrating noise floor... stay quiet")
        samples = []
        for _ in range(int(seconds / self.chunk_duration)):
            chunk = self.get_next_chunk()
            rms = np.sqrt(np.mean(chunk ** 2) + 1e-6)
            db = 20 * np.log10(rms + 1e-6)
            samples.append(db)
        self.noise_floor_db = np.mean(samples)
        print(f"Noise floor calibrated at {self.noise_floor_db:.2f} dB")

    def analyze_audio_chunk(self, chunk: np.ndarray) -> Dict[str, Any]:
        """
        Returns:
          {
            "violations": [...],
            "metrics": {"db": float, "spectral_flatness": float}
          }

        Violations:
          - MULTIPLE_VOICES
          - LOUD_AUDIO
        """
        rms = np.sqrt(np.mean(chunk ** 2) + 1e-6)
        db = 20 * np.log10(rms/ 32768.0 + 1e-6)

        violations = []

        # Loud audio relative to baseline
        if db > -10.0:
            violations.append("LOUD_AUDIO")

        # Multiple voices heuristic
        spectrum = np.fft.rfft(chunk)
        mag = np.abs(spectrum)
        spec_flat = np.exp(np.mean(np.log(mag + 1e-6))) / (np.mean(mag) + 1e-6)
        spec_flat = float(np.clip(spec_flat, 0, 1))

        if spec_flat > 0.6:
            violations.append("MULTIPLE_VOICES")

        return {
            "violations": list(set(violations)),
            "metrics": {"db": float(db), "spectral_flatness": float(spec_flat)}
        }


if __name__ == "__main__":
    analyzer = AudioAnalyzer(sample_rate=16000, chunk_duration=2.0)
    analyzer.start_recording()
    analyzer.calibrate_noise_floor(seconds=5)  # calibrate before monitoring

    try:
        while True:
            chunk = analyzer.get_next_chunk()
            res = analyzer.analyze_audio_chunk(chunk)
            print(res)
    except KeyboardInterrupt:
        pass
    finally:
        analyzer.stop_recording()

