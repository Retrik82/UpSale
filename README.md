# UpSale

UpSale is a local sales-call workspace with three core flows:

- record real calls in the browser
- transcribe and analyze them with AI
- practice sales conversations in a built-in trainer

The current project layout is a FastAPI backend in the repository root and a Next.js frontend in `frontend/`.

## Stack

- Backend: FastAPI
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
- Storage: local in-memory app state plus local files for recordings
- Transcription: `openai-whisper`
- Speaker separation:
  - primary path for new recordings: stereo channel split (`manager mic` + `call audio`)
  - fallback for mono audio: `pyannote.audio`
- LLM providers: OpenRouter models for trainer and call reports

## What Works

- JWT auth
- Workspaces and members
- Sales manager and admin roles
- Browser call recording
- Uploading call recordings
- Whisper transcription
- Role labeling in transcripts as manager/client
- AI-generated post-call analysis
- AI sales trainer with multiple scenarios
- Dashboard and call detail UI
- Russian and English UI language support

## How Transcription Works

For new recordings made inside the app:

- the browser recorder captures two audio sources
- system/tab audio is stored in one channel
- microphone audio is stored in the second channel
- backend uses channel energy to label transcript segments as `Менеджер/Клиент` or `Sales manager/Client`

For old or external mono recordings:

- backend runs Whisper for text
- backend can run `pyannote.audio` for speaker diarization
- diarization segments are matched to Whisper segments
- speakers are then mapped to call roles

This means new in-app recordings are the most reliable path. Mono fallback is useful, but less deterministic.

## Repository Layout

```text
.
├── main.py                # current FastAPI application entrypoint
├── app.py                 # older app entrypoint from previous structure
├── requirements.txt       # backend dependencies
├── .env.example           # example environment variables
├── recordings/            # saved uploaded/recorded audio files
├── tests/                 # backend tests
└── frontend/              # Next.js frontend
```

## Requirements

- Python 3.12+
- Node.js 18+
- npm

Recommended for `pyannote.audio` on Windows:

- a working C/C++ runtime
- enough RAM for PyTorch-based models
- optional Hugging Face access token for diarization model download

## Environment Setup

Create a `.env` file in the repository root based on `.env.example`.

Minimal useful variables:

```env
JWT_SECRET=your-super-secret-jwt-key-change-in-production
OPENROUTER_API_KEY=PASTE_YOUR_OPENROUTER_API_KEY_HERE
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TRAINER_MODEL=meta-llama/llama-3.3-70b-instruct
OPENROUTER_REPORT_MODEL=qwen/qwen3.6-plus
WHISPER_MODEL=base
PYANNOTE_MODEL=pyannote/speaker-diarization-3.1
PYANNOTE_AUTH_TOKEN=your-huggingface-token
```

Notes:

- `OPENROUTER_API_KEY` is required for trainer replies and report generation.
- `PYANNOTE_AUTH_TOKEN` is only required if you want diarization fallback for mono recordings.
- if `PYANNOTE_AUTH_TOKEN` is missing or `pyannote` fails to load, the app still works; only mono diarization fallback is unavailable.

## Backend Setup

Create a virtual environment and install dependencies.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```text
GET http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Frontend Setup

Install frontend dependencies:

```bash
cd frontend
npm install
```

If the backend is running on the default port, no extra frontend env is required.

Optional frontend env:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the frontend:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

## Running Both Apps

Terminal 1:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

## Audio And Speaker Roles

When recording from the call details page, the app asks for:

- display or browser tab capture with audio enabled
- microphone access

For best results:

- if the meeting is in the browser, share the exact tab and enable tab audio
- if the meeting is in a desktop app, enable system audio in the share dialog if your browser supports it
- allow microphone access so the manager voice is captured separately

Expected role mapping for new recordings:

- tab/system audio -> client
- microphone -> sales manager

If both sides end up mixed into one mono stream, backend falls back to diarization when available.

## pyannote Notes

`pyannote.audio` is included for mono-recording speaker diarization fallback.

Important practical notes:

- first use may download model files from Hugging Face
- you need a valid `PYANNOTE_AUTH_TOKEN` for gated models
- on Windows, `torchcodec` or FFmpeg-based file decoding may be unreliable depending on local setup
- this project avoids part of that problem by feeding waveform data from memory into the diarization pipeline instead of relying only on file-path decoding

If diarization is unavailable, stereo in-app recordings still keep working.

## Tests

Backend tests:

```bash
python -m unittest discover -s tests -v
```

Frontend production build:

```bash
cd frontend
npm run build
```

Current note about linting:

- `npm run lint` may open the interactive Next.js ESLint setup prompt if ESLint has not been initialized in the frontend yet

## Main API Routes

Auth:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Workspaces:

- `GET /workspaces`
- `GET /workspaces/discover`
- `POST /workspaces`
- `GET /workspaces/{workspace_id}/members`
- `GET /workspaces/{workspace_id}/my-stats`
- `POST /workspaces/{workspace_id}/join`
- `POST /workspaces/{workspace_id}/set-password`
- `DELETE /workspaces/{workspace_id}/members/{target_user_id}`
- `DELETE /workspaces/{workspace_id}/leave`

Calls:

- `GET /calls`
- `POST /calls`
- `GET /calls/{call_id}`
- `PATCH /calls/{call_id}/sale-completed`
- `POST /calls/{call_id}/transcribe`
- `POST /calls/{call_id}/analyze`
- `POST /calls/{call_id}/upload`

Trainer:

- `GET /trainer/scenarios`
- `POST /trainer/sessions`
- `POST /trainer/sessions/{session_id}/messages`
- `POST /trainer/sessions/{session_id}/finish`

Admin:

- `GET /admin/employees`
- `POST /admin/employees/{user_id}/block`
- `DELETE /admin/employees/{user_id}`
- `GET /admin/workspaces/{workspace_id}/stats`
- `POST /admin/workspaces/{workspace_id}/members/{target_user_id}/remove`
- `POST /admin/workspaces/{workspace_id}/members/{target_user_id}/remove-and-block`

Health:

- `GET /health`

## Known Limitations

- project still contains traces of an older backend structure in `app.py` and old docs references; current active entrypoint is `main.py`
- app state is currently local/in-memory in the active backend flow, so persistence is limited
- old mono recordings cannot be separated as reliably as new stereo in-app recordings
- `pyannote.audio` on Windows can be environment-sensitive because of PyTorch and codec dependencies
- frontend linting is not fully initialized yet

## Recommended Smoke Test

1. Start backend.
2. Start frontend.
3. Register or log in.
4. Open a workspace.
5. Create a call.
6. Start recording from the call detail page.
7. Share meeting audio and allow microphone.
8. Stop recording.
9. Confirm that transcript segments show `Менеджер/Клиент` or `Sales manager/Client`.
10. Confirm that the analysis report is generated.

## License

MIT
