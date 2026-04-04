# AI Sales Coach Platform

A web application for recording, transcribing and analyzing sales calls with AI-powered insights and training simulations.

## Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: Next.js 14 + React + TypeScript + TailwindCSS
- **Database**: SQLite (local file) with SQLAlchemy 2.0
- **Audio**: Whisper (CPU) + pyannote.audio for diarization
- **LLM**: Ollama (default) | OpenAI (optional)
- **Runtime**: CPU only

## Features

- User authentication with JWT
- Workspace system for team collaboration
- Call recording (desktop audio capture)
- Offline transcription with speaker diarization
- LLM-based sales analysis with scoring metrics
- AI training simulator for practice sessions
- Dashboard with analytics

## Project Structure

```
├── backend/
│   ├── core/          # Config, database, security
│   ├── models/        # SQLAlchemy models
│   ├── repositories/  # CRUD layer
│   ├── api/routes/    # FastAPI routes
│   ├── audio/         # Audio recording
│   ├── ai/            # Transcription
│   └── analysis/      # Sales analysis & LLM
├── frontend/          # Next.js app
├── alembic/           # Database migrations
└── .env               # Environment variables
```

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- SQLite (auto-created locally)

### Backend Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Optional: adjust DATABASE_URL if you want a different local SQLite file
```

4. Start the server:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The SQLite database file is created automatically on startup as `salescoach.db`.

### Frontend Setup

1. Install dependencies:
```bash
npm install
cd frontend


```

2. Start development server:
```bash
npm run dev
```

3. Open http://localhost:3000

### Optional: Ollama Setup

For local LLM analysis:
```bash
ollama serve
ollama pull llama3.2
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Workspaces
- `GET /api/workspaces` - List user workspaces
- `POST /api/workspaces` - Create workspace
- `GET /api/workspaces/{id}` - Get workspace
- `POST /api/workspaces/{id}/members` - Add member

### Calls
- `GET /api/calls` - List workspace calls
- `POST /api/calls` - Create call
- `GET /api/calls/{id}` - Get call details
- `POST /api/calls/{id}/transcribe` - Transcribe call
- `POST /api/calls/{id}/analyze` - Analyze call
- `POST /api/calls/{id}/upload` - Upload recording

### Simulations
- `GET /api/simulations` - List simulations
- `POST /api/simulations` - Create simulation
- `POST /api/simulations/{id}/start` - Start session
- `POST /api/simulations/{id}/finish` - Finish session

### Templates
- `GET /api/templates` - List templates
- `POST /api/templates` - Create template
- `PUT /api/templates/{id}` - Update template
- `DELETE /api/templates/{id}` - Delete template

## License

MIT
