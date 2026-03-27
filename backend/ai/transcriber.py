import os
from typing import Optional, Tuple, Dict

import numpy as np

from backend.audio.writer import AudioWriter
from backend.core.config import settings


class Transcriber:
    def __init__(
        self,
        model_size: str = None,
        device: str = None,
    ):
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self.device = device or settings.WHISPER_DEVICE
        self._model = None

    def _load_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_size, device=self.device)
        return self._model

    def _load_audio_array(self, audio_path: str) -> Tuple[np.ndarray, int]:
        audio_data, sample_rate, _, _ = AudioWriter.read_wav(audio_path)

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        audio_data = audio_data / 32768.0

        if sample_rate != 16000 and len(audio_data) > 0:
            duration = len(audio_data) / sample_rate
            target_length = max(1, int(duration * 16000))
            source_indices = np.linspace(0, len(audio_data) - 1, num=len(audio_data))
            target_indices = np.linspace(0, len(audio_data) - 1, num=target_length)
            audio_data = np.interp(target_indices, source_indices, audio_data).astype(np.float32)
            sample_rate = 16000

        return audio_data, sample_rate

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> Dict:
        model = self._load_model()
        audio_data, _ = self._load_audio_array(audio_path)

        result = model.transcribe(
            audio_data,
            language=language,
            task=task,
            verbose=False,
        )

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", "").strip(),
                "speaker": f"Speaker_{len(segments) % 2 + 1}",
            })

        return {
            "text": result.get("text", "").strip(),
            "segments": segments,
            "language": result.get("language", language),
        }

    def transcribe_with_diarization(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Dict:
        model = self._load_model()
        audio_data, sample_rate = self._load_audio_array(audio_path)

        try:
            import torch
            from pyannote.audio import Pipeline

            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=os.getenv("HF_TOKEN"),
            )
            diarization = pipeline(
                {"waveform": torch.from_numpy(audio_data).unsqueeze(0), "sample_rate": sample_rate}
            )

            speakers = []
            speaker_map = {}
            current_speaker_idx = 0

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker not in speaker_map:
                    speaker_map[speaker] = current_speaker_idx
                    current_speaker_idx += 1
                    speakers.append(speaker)

        except Exception as e:
            print(f"Diarization failed: {e}, using fallback")
            speakers = ["Speaker_1", "Speaker_2"]
            speaker_map = {}
            diarization = None

        result = model.transcribe(
            audio_data,
            language=language,
            task="transcribe",
            verbose=False,
        )

        segments = []
        for seg in result.get("segments", []):
            speaker = "Speaker_1"
            if speaker_map and diarization is not None:
                seg_start = seg.get("start", 0)
                for turn, _, spk in diarization.itertracks(yield_label=True):
                    if turn.start <= seg_start <= turn.end:
                        speaker = spk
                        break

            segments.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", "").strip(),
                "speaker": speaker,
            })

        return {
            "text": result.get("text", "").strip(),
            "segments": segments,
            "speakers": list(set(speaker_map.keys())) if speaker_map else speakers,
            "language": result.get("language", language),
            "duration": len(audio_data) / sample_rate if len(audio_data) > 0 else 0,
        }
