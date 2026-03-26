import os
import uuid
import subprocess
from typing import Optional, Tuple, List, Dict
from pathlib import Path

import numpy as np

from backend.audio.writer import AudioWriter


class Transcriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
    ):
        self.model_size = model_size
        self.device = device
        self._model = None

    def _load_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_size, device=self.device)
        return self._model

    def _prepare_audio(self, audio_path: str) -> str:
        temp_path = os.path.join(os.path.dirname(audio_path), f"{uuid.uuid4()}_mono.wav")
        AudioWriter.convert_to_mono(audio_path, temp_path, target_sample_rate=16000)
        return temp_path

    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        task: str = "transcribe",
    ) -> Dict:
        model = self._load_model()
        temp_audio = self._prepare_audio(audio_path)
        
        try:
            result = model.transcribe(
                temp_audio,
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
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

    def transcribe_with_diarization(
        self,
        audio_path: str,
        language: str = "en",
    ) -> Dict:
        model = self._load_model()
        temp_audio = self._prepare_audio(audio_path)
        
        try:
            audio_data, sample_rate, _, _ = AudioWriter.read_wav(temp_audio)
            
            if sample_rate != 16000:
                import torchaudio
                waveform = torch.from_numpy(audio_data.astype(np.float32) / 32768.0)
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                audio_data = resampler(waveform).squeeze().numpy()
                sample_rate = 16000
            
            try:
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
            
            result = model.transcribe(
                temp_audio,
                language=language,
                task="transcribe",
                verbose=False,
            )
            
            segments = []
            for seg in result.get("segments", []):
                speaker = "Speaker_1"
                if speaker_map:
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
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
