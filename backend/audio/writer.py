import wave
import numpy as np
from pathlib import Path
from typing import Optional, Tuple


class AudioWriter:
    @staticmethod
    def read_wav(filepath: str) -> Tuple[np.ndarray, int, int, int]:
        with wave.open(filepath, 'rb') as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            audio_data = wf.readframes(n_frames)
            
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)
                audio_array = audio_array.mean(axis=1)
            
            return audio_array, sample_rate, channels, sample_width

    @staticmethod
    def write_wav(
        filepath: str,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
        
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

    @staticmethod
    def convert_to_mono(input_path: str, output_path: str, target_sample_rate: int = 16000):
        audio_data, sample_rate, channels, _ = AudioWriter.read_wav(input_path)
        
        if channels > 1:
            audio_data = audio_data.reshape(-1, channels).mean(axis=1)
        
        AudioWriter.write_wav(output_path, audio_data, sample_rate=target_sample_rate, channels=1)

    @staticmethod
    def get_duration(filepath: str) -> float:
        with wave.open(filepath, 'rb') as wf:
            return wf.getnframes() / wf.getframerate()
