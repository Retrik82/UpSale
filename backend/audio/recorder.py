import os
import uuid
import wave
import numpy as np
from datetime import datetime
from typing import Optional, Tuple

from backend.audio.audio_capture import AudioCapture
from backend.core.config import settings


class Recorder:
    def __init__(
        self,
        sample_rate: int = None,
        channels: int = None,
    ):
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.channels = channels or settings.AUDIO_CHANNELS
        self.capture = AudioCapture(
            sample_rate=self.sample_rate,
            channels=self.channels,
        )
        self._current_recording_path: Optional[str] = None
        self._recording_start_time: Optional[datetime] = None

    def start(self, output_dir: str = None, device: int = None) -> Tuple[bool, str]:
        os.makedirs(output_dir or settings.RECORDINGS_DIR, exist_ok=True)
        
        filename = f"{uuid.uuid4()}.wav"
        self._current_recording_path = os.path.join(
            output_dir or settings.RECORDINGS_DIR,
            filename
        )
        self._recording_start_time = datetime.utcnow()
        
        success = self.capture.start(device=device)
        if success:
            return True, self._current_recording_path
        return False, ""

    def stop(self) -> Tuple[Optional[str], int]:
        if not self.capture.is_recording():
            return None, 0
        
        audio_data, duration = self.capture.stop()
        
        if self._current_recording_path and len(audio_data) > 0:
            self._save_wav(self._current_recording_path, audio_data)
            path = self._current_recording_path
            self._current_recording_path = None
            return path, duration
        
        return None, 0

    def _save_wav(self, filepath: str, audio_data: np.ndarray):
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            wf.writeframes(audio_data.tobytes())

    def is_recording(self) -> bool:
        return self.capture.is_recording()

    def list_devices(self):
        return self.capture.list_devices()
