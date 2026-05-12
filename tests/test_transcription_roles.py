import unittest
from uuid import uuid4
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import main


class TranscriptionRoleTests(unittest.TestCase):
    def setUp(self):
        self._stores_backup = {name: value.copy() for name, value in main.stores.items()}

    def tearDown(self):
        for name, value in self._stores_backup.items():
            main.stores[name] = value

    def test_normalize_trainer_payload_accepts_json_inside_code_fence(self):
        payload = main.normalize_trainer_payload(
            """```json
            {"reply": "Здравствуйте!", "should_end_call": false, "end_reason": null}
            ```"""
        )

        self.assertEqual(payload["reply"], "Здравствуйте!")
        self.assertFalse(payload["should_end_call"])
        self.assertIsNone(payload["end_reason"])

    def test_normalize_trainer_payload_falls_back_to_plain_text_reply(self):
        payload = main.normalize_trainer_payload("Здравствуйте! Чем могу помочь?")

        self.assertEqual(payload["reply"], "Здравствуйте! Чем могу помочь?")
        self.assertFalse(payload["should_end_call"])
        self.assertIsNone(payload["end_reason"])

    def test_list_trainer_sessions_filters_by_user_and_workspace(self):
        user_id = uuid4()
        other_user_id = uuid4()
        workspace_id = uuid4()
        other_workspace_id = uuid4()
        user = main.User(
            id=user_id,
            email="manager@example.com",
            hashed_password="hash",
            system_role=main.SystemRole.SALES_MANAGER,
        )
        main.stores["users"][str(user_id)] = user
        main.stores["workspaces"][str(workspace_id)] = main.Workspace(
            id=workspace_id,
            name="Workspace",
            owner_id=user_id,
        )
        main.stores["workspace_members"][str(uuid4())] = main.WorkspaceMember(
            id=str(uuid4()),
            workspace_id=str(workspace_id),
            user_id=str(user_id),
        )

        def make_session(session_id, owner_id, target_workspace_id, started_at):
            return {
                "id": session_id,
                "workspace_id": str(target_workspace_id),
                "user_id": str(owner_id),
                "scenario_id": "easy-discovery",
                "language": "ru",
                "status": "completed",
                "end_reason": "session_completed",
                "started_at": started_at,
                "completed_at": started_at,
                "messages": [{"role": "assistant", "content": "Hello", "created_at": started_at}],
                "report": None,
            }

        main.stores["trainer_sessions"]["older"] = make_session("older", user_id, workspace_id, "2024-01-01T10:00:00")
        main.stores["trainer_sessions"]["newer"] = make_session("newer", user_id, workspace_id, "2024-01-02T10:00:00")
        main.stores["trainer_sessions"]["other-user"] = make_session("other-user", other_user_id, workspace_id, "2024-01-03T10:00:00")
        main.stores["trainer_sessions"]["other-workspace"] = make_session("other-workspace", user_id, other_workspace_id, "2024-01-04T10:00:00")

        client = TestClient(main.app)
        response = client.get(
            f"/trainer/sessions?workspace_id={workspace_id}",
            headers={"Authorization": f"Bearer {main.create_access_token({'sub': str(user_id)})}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([session["id"] for session in response.json()], ["newer", "older"])

    def test_run_speaker_diarization_passes_waveform_to_pipeline(self):
        class FakeTurn:
            def __init__(self, start, end):
                self.start = start
                self.end = end

        class FakeDiarizationResult:
            def itertracks(self, yield_label=False):
                yield FakeTurn(0.0, 1.0), None, "SPEAKER_00"

        class FakePipeline:
            def __init__(self):
                self.received_input = None

            def __call__(self, diarization_input):
                self.received_input = diarization_input
                return FakeDiarizationResult()

        fake_pipeline = FakePipeline()
        stereo_samples = np.zeros((16000, 2), dtype=np.float32)

        with patch.object(main, "get_speaker_diarization_pipeline", return_value=fake_pipeline), patch.object(
            main, "load_audio_samples", return_value=stereo_samples
        ):
            diarized_segments = main.run_speaker_diarization("fake.wav")

        self.assertEqual(diarized_segments, [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}])
        self.assertIsInstance(fake_pipeline.received_input, dict)
        self.assertEqual(fake_pipeline.received_input["sample_rate"], 16000)
        self.assertEqual(tuple(fake_pipeline.received_input["waveform"].shape), (2, 16000))

    def test_assign_roles_from_stereo_channels_uses_manager_and_client_labels(self):
        samples = np.zeros((32000, 2), dtype=np.float32)
        samples[:16000, 1] = 0.8
        samples[16000:, 0] = 0.6
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Добрый день", "speaker": "Speaker 1"},
            {"start": 1.0, "end": 2.0, "text": "Здравствуйте", "speaker": "Speaker 1"},
        ]

        labeled = main.assign_roles_from_stereo_channels(samples, 16000, segments, "ru")

        self.assertEqual([segment["speaker"] for segment in labeled], ["Менеджер", "Клиент"])

    def test_assign_roles_from_diarization_maps_two_speakers_to_call_roles(self):
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello", "speaker": "Speaker 1"},
            {"start": 1.0, "end": 2.0, "text": "Hi", "speaker": "Speaker 1"},
        ]
        diarized_segments = [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
            {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_01"},
        ]

        labeled = main.assign_roles_from_diarization(segments, diarized_segments, "en")

        self.assertEqual([segment["speaker"] for segment in labeled], ["Sales manager", "Client"])

    def test_fallback_report_uses_manager_role_weight_for_talk_ratio(self):
        call = main.RealCall(
            id=uuid4(),
            workspace_id=uuid4(),
            user_id=uuid4(),
            transcript={
                "language": "en",
                "segments": [
                    {"speaker": "Sales manager", "text": "one two three four", "start": 0.0, "end": 1.0},
                    {"speaker": "Client", "text": "one two", "start": 1.0, "end": 2.0},
                ],
            },
        )

        report = main.build_call_report_fallback(call, "test")

        self.assertEqual(report["talk_ratio_seller"], 0.67)
        self.assertEqual(report["talk_ratio_client"], 0.33)

    def test_transcribe_call_recording_uses_diarization_for_mono_audio(self):
        class FakeWhisperModel:
            def transcribe(self, audio_input, fp16=False, verbose=False):
                return {
                    "text": "Hello Hi",
                    "language": "en",
                    "segments": [
                        {"start": 0.0, "end": 1.0, "text": "Hello"},
                        {"start": 1.0, "end": 2.0, "text": "Hi"},
                    ],
                }

        mono_samples = np.zeros(32000, dtype=np.float32)
        diarized_segments = [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
            {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_01"},
        ]

        with patch.object(main, "get_whisper_model", return_value=FakeWhisperModel()), patch.object(
            main, "load_audio_samples", return_value=mono_samples
        ), patch.object(main, "run_speaker_diarization", return_value=diarized_segments):
            transcript = main.transcribe_call_recording("fake.wav")

        self.assertEqual([segment["speaker"] for segment in transcript["segments"]], ["Sales manager", "Client"])
        self.assertEqual(transcript["speakers"], ["Sales manager", "Client"])


if __name__ == "__main__":
    unittest.main()
