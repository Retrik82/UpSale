import numpy as np
from typing import Optional, Tuple
import threading
import queue


class AudioCapture:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._stream = None
        self._is_recording = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._buffer: list = []

    def list_devices(self):
        import sounddevice as sd
        return sd.query_devices()

    def find_loopback_device(self) -> Optional[int]:
        import sounddevice as sd
        devices = sd.query_devices()
        if isinstance(devices, dict):
            devices = [devices]
        
        for i, device in enumerate(devices):
            if "loopback" in device.get("name", "").lower():
                return i
            if "wasapi" in device.get("name", "").lower() and "speaker" in device.get("name", "").lower():
                return i
        return None

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}")
        audio_data = indata.copy()
        self._audio_queue.put(audio_data)

    def start(self, device: Optional[int] = None) -> bool:
        import sounddevice as sd
        
        if self._is_recording:
            return False
        
        if device is None:
            device = self.find_loopback_device()
        
        if device is None:
            print("No loopback device found, using default")
            device = -1
        
        try:
            self._stream = sd.InputStream(
                device=device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            self._is_recording = True
            self._buffer = []
            return True
        except Exception as e:
            print(f"Failed to start audio capture: {e}")
            return False

    def stop(self) -> Tuple[np.ndarray, int]:
        import sounddevice as sd
        
        if not self._is_recording:
            return np.array([]), 0
        
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._is_recording = False
        
        while not self._audio_queue.empty():
            self._buffer.append(self._audio_queue.get())
        
        if self._buffer:
            audio_data = np.concatenate(self._buffer, axis=0)
        else:
            audio_data = np.array([])
        
        duration = len(audio_data) / self.sample_rate if len(audio_data) > 0 else 0
        return audio_data, int(duration)

    def is_recording(self) -> bool:
        return self._is_recording
