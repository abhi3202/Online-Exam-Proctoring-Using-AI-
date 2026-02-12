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

        # Thresholds (tune them for your room)
        self.loud_db_thresh = -20.0  # louder -> violation
        self.multi_voice_flatness_thresh = 0.7

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

    def get_next_chunk(self) -> np.ndarray:
        data = self.stream.read(self.chunk_size, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return audio

    def analyze_audio_chunk(self, chunk: np.ndarray) -> Dict[str, Any]:
        """
        Returns:
          {
            "violations": [...],
            "metrics": {"db": float, "spectral_flatness": float}
          }

        Violations (README):
          - MULTIPLE_VOICES
          - LOUD_AUDIO
        """
        rms = np.sqrt(np.mean(chunk ** 2) + 1e-6)
        db = 20 * np.log10(rms + 1e-6)

        violations = []
        if db > self.loud_db_thresh:
            violations.append("LOUD_AUDIO")

        spectrum = np.fft.rfft(chunk)
        mag = np.abs(spectrum)
        spec_flat = np.exp(np.mean(np.log(mag + 1e-6))) / (np.mean(mag) + 1e-6)

        if spec_flat > self.multi_voice_flatness_thresh:
            violations.append("MULTIPLE_VOICES")

        return {
            "violations": list(set(violations)),
            "metrics": {
                "db": float(db),
                "spectral_flatness": float(spec_flat)
            }
        }


if __name__ == "__main__":
    analyzer = AudioAnalyzer(sample_rate=16000, chunk_duration=2.0)
    analyzer.start_recording()

    try:
        while True:
            chunk = analyzer.get_next_chunk()
            res = analyzer.analyze_audio_chunk(chunk)
            print(res)
    except KeyboardInterrupt:
        pass
    finally:
        analyzer.stop_recording()
