from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional
from uuid import UUID


class RecordingError(Exception):
    pass


@dataclass
class ActiveRecording:
    call_id: UUID
    recorder: object


class RecordingManager:
    def __init__(self):
        self._lock = Lock()
        self._active: Optional[ActiveRecording] = None

    def start(self, call_id: UUID, device: Optional[int] = None) -> None:
        with self._lock:
            if self._active is not None:
                if self._active.call_id == call_id:
                    raise RecordingError("Recording is already running for this call")
                raise RecordingError("Another call is already being recorded")

            try:
                from backend.audio.recorder import Recorder
            except ImportError as exc:
                raise RecordingError(f"Audio recording dependencies are unavailable: {exc}") from exc

            recorder = Recorder()
            success, _ = recorder.start(device=device)
            if not success:
                raise RecordingError("Failed to start audio capture")

            self._active = ActiveRecording(call_id=call_id, recorder=recorder)

    def stop(self, call_id: UUID) -> tuple[str, int]:
        with self._lock:
            if self._active is None or self._active.call_id != call_id:
                raise RecordingError("No active recording for this call")

            path, duration = self._active.recorder.stop()
            self._active = None

        if not path:
            raise RecordingError("Recording stopped but no audio was captured")

        return path, duration

    def is_recording(self, call_id: UUID) -> bool:
        with self._lock:
            return self._active is not None and self._active.call_id == call_id


recording_manager = RecordingManager()
