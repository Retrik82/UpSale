import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError


def load_env_file() -> None:
    env_path = ".env"
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file()


JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_TRAINER_MODEL = os.getenv(
    "OPENROUTER_TRAINER_MODEL",
    "meta-llama/llama-3.3-70b-instruct",
)
OPENROUTER_REPORT_MODEL = os.getenv(
    "OPENROUTER_REPORT_MODEL",
    "qwen/qwen3.6-plus",
)
SUPPORTED_APP_LANGUAGES = {"ru": "Russian", "en": "English"}
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
PYANNOTE_MODEL_NAME = os.getenv("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
PYANNOTE_AUTH_TOKEN = os.getenv("PYANNOTE_AUTH_TOKEN", "").strip()
RECORDINGS_DIR = os.path.join(os.getcwd(), "recordings")
_whisper_model = None
_speaker_diarization_pipeline = None

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


class SystemRole(str, Enum):
    ADMIN = "admin"
    SALES_MANAGER = "sales_manager"


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class CallStatus(str, Enum):
    RECORDING = "recording"
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


stores = {
    "users": {},
    "workspaces": {},
    "workspace_members": {},
    "calls": {},
    "trainer_sessions": {},
}
_trainer_report_tasks: dict[str, asyncio.Task] = {}


TRAINER_SCENARIOS = [
    {
        "id": "warm-lead-easy",
        "title": "Warm lead",
        "difficulty": "Easy",
        "trainer_name": "Anna",
        "company_name": "BrightDesk",
        "summary": "The client already knows your product category and is open to a short intro.",
        "scenario": "A team lead from a small company wants to reduce response time and organize leads.",
        "persona": "Polite, busy, but interested if the value is clear quickly.",
        "pressure_points": [
            "Explain value in simple language",
            "Ask at least one discovery question",
            "Move toward a clear next step",
        ],
        "advice": [
            "Open with the client goal, not with a feature dump",
            "Clarify current process before pitching",
            "Offer a specific next step: demo, trial, or follow-up",
        ],
        "max_turns": 8,
        "opening_line": "Hello. I have about ten minutes. We already use a few tools, so tell me briefly why your solution is worth my attention.",
    },
    {
        "id": "price-pressure-medium",
        "title": "Price pressure",
        "difficulty": "Medium",
        "trainer_name": "Maksim",
        "company_name": "Northwind Retail",
        "summary": "The client sees some value but pushes hard on price and wants proof before moving.",
        "scenario": "An operations manager is comparing you with two competitors and is worried about budget.",
        "persona": "Skeptical, practical, wants numbers and dislikes vague claims.",
        "pressure_points": [
            "Handle price objections without immediately discounting",
            "Tie value to measurable business impact",
            "Keep control of the conversation when challenged",
        ],
        "advice": [
            "Do not defend the price too early; first uncover the cost of the current problem",
            "Use examples, metrics, and ROI language",
            "Check whether price is the real blocker or just the first objection",
        ],
        "max_turns": 10,
        "opening_line": "I already saw similar offers. Your price looks high, so if you want this conversation to continue, explain what exactly I get for that money.",
    },
    {
        "id": "hostile-procurement-hard",
        "title": "Hostile procurement",
        "difficulty": "Hard",
        "trainer_name": "Irina",
        "company_name": "Delta Procurement Group",
        "summary": "The client is cold, impatient, and ready to end the call if the conversation feels pushy or unstructured.",
        "scenario": "A procurement lead joined late, has little trust, and expects a concise business case immediately.",
        "persona": "Sharp, demanding, quick to interrupt, and willing to hang up.",
        "pressure_points": [
            "Earn the right to ask questions under pressure",
            "Stay calm when interrupted or challenged",
            "Recognize when to narrow the ask instead of forcing a close",
        ],
        "advice": [
            "Respect time pressure and acknowledge skepticism directly",
            "Use short, high-signal answers and confirm relevance often",
            "If resistance grows, pivot to a smaller next step instead of pushing harder",
        ],
        "max_turns": 12,
        "opening_line": "You have five minutes. If this is another generic sales pitch, I will end the call immediately. Start with the business case.",
    },
]

TRAINER_SCENARIO_TRANSLATIONS = {
    "warm-lead-easy": {
        "ru": {
            "title": "Тёплый лид",
            "summary": "Клиент уже понимает категорию продукта и готов выслушать короткое вступление.",
            "scenario": "Руководитель небольшой команды хочет сократить время ответа и лучше организовать лиды.",
            "pressure_points": [
                "Объяснить ценность простым языком",
                "Задать хотя бы один диагностический вопрос",
                "Подвести к чёткому следующему шагу",
            ],
            "advice": [
                "Начинай с цели клиента, а не с перечисления функций",
                "Сначала уточни текущий процесс, потом переходи к питчу",
                "Предлагай конкретный следующий шаг: демо, тест или созвон",
            ],
            "opening_line": "Здравствуйте. У меня есть минут десять. Мы уже пользуемся несколькими инструментами, поэтому кратко объясните, почему вашему решению стоит уделить внимание.",
        }
    },
    "price-pressure-medium": {
        "ru": {
            "title": "Давление по цене",
            "summary": "Клиент видит часть ценности, но жёстко давит на цену и хочет доказательств перед следующим шагом.",
            "scenario": "Операционный менеджер сравнивает вас с двумя конкурентами и переживает из-за бюджета.",
            "pressure_points": [
                "Обработать возражение по цене без мгновенной скидки",
                "Привязать ценность к измеримому бизнес-эффекту",
                "Не потерять контроль над разговором под давлением",
            ],
            "advice": [
                "Не защищай цену слишком рано; сначала вскрой стоимость текущей проблемы",
                "Используй цифры, примеры и язык ROI",
                "Проверь, цена ли это на самом деле или только первое возражение",
            ],
            "opening_line": "Я уже видел похожие предложения. У вас высокая цена, так что если хотите продолжить разговор, объясните, за что именно я должен платить.",
        }
    },
    "hostile-procurement-hard": {
        "ru": {
            "title": "Жёсткий закупщик",
            "summary": "Клиент холодный, нетерпеливый и быстро завершит разговор, если почувствует давление или слабую структуру.",
            "scenario": "Руководитель закупок подключился поздно, не доверяет вам и сразу ждёт чёткий бизнес-кейс.",
            "pressure_points": [
                "Заслужить право задавать вопросы под давлением",
                "Сохранять спокойствие, когда вас перебивают",
                "Понять, когда нужно сузить следующий шаг, а не дожимать",
            ],
            "advice": [
                "Признай дефицит времени и скепсис прямо в начале",
                "Отвечай коротко и по сути, регулярно подтверждая релевантность",
                "Если сопротивление растёт, предложи меньший следующий шаг вместо жёсткого дожима",
            ],
            "opening_line": "У вас пять минут. Если это будет очередной общий продажный питч, я сразу закончу разговор. Начните с бизнес-обоснования.",
        }
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


class User:
    def __init__(
        self,
        id: UUID,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        system_role: SystemRole = SystemRole.SALES_MANAGER,
        is_blocked: bool = False,
        created_at: datetime = None,
    ):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.system_role = system_role
        self.is_blocked = is_blocked
        self.created_at = created_at or datetime.utcnow()


class Workspace:
    def __init__(
        self,
        id: UUID,
        name: str,
        owner_id: UUID,
        description: Optional[str] = None,
        password: Optional[str] = None,
        created_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.description = description
        self.password = password
        self.created_at = created_at or datetime.utcnow()


class WorkspaceMember:
    def __init__(
        self,
        id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole = WorkspaceRole.MEMBER,
        created_at: datetime = None,
    ):
        self.id = id
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.role = role
        self.created_at = created_at or datetime.utcnow()


class RealCall:
    def __init__(
        self,
        id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        client_name: Optional[str] = None,
        notes: Optional[str] = None,
        sale_completed: bool = False,
        status: str = CallStatus.PENDING.value,
        recording_path: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        transcript: Optional[dict] = None,
        report: Optional[dict] = None,
        completed_at: Optional[datetime] = None,
        created_at: datetime = None,
    ):
        self.id = id
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.client_name = client_name
        self.notes = notes
        self.sale_completed = sale_completed
        self.status = status
        self.recording_path = recording_path
        self.duration_seconds = duration_seconds
        self.transcript = transcript
        self.report = report
        self.completed_at = completed_at
        self.created_at = created_at or datetime.utcnow()


def get_whisper_model():
    global _whisper_model

    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model(WHISPER_MODEL_NAME)

    return _whisper_model


def get_speaker_diarization_pipeline():
    global _speaker_diarization_pipeline

    if _speaker_diarization_pipeline is False:
        return None

    if _speaker_diarization_pipeline is None:
        try:
            from pyannote.audio import Pipeline

            _speaker_diarization_pipeline = Pipeline.from_pretrained(
                PYANNOTE_MODEL_NAME,
                use_auth_token=PYANNOTE_AUTH_TOKEN or None,
            )
            try:
                import torch

                _speaker_diarization_pipeline.to(torch.device("cpu"))
            except Exception:
                pass
        except Exception:
            _speaker_diarization_pipeline = False
            return None

    return _speaker_diarization_pipeline


def load_audio_samples(recording_path: str, preserve_channels: bool = False):
    import numpy as np
    import soundfile as sf

    samples, sample_rate = sf.read(recording_path, dtype="float32")

    if getattr(samples, "ndim", 1) > 1 and not preserve_channels:
        samples = samples.mean(axis=1)

    target_sample_rate = 16000
    if sample_rate != target_sample_rate:
        if len(samples) == 0:
            if preserve_channels and getattr(samples, "ndim", 1) > 1:
                return np.zeros((0, samples.shape[1]), dtype=np.float32)
            return np.zeros(0, dtype=np.float32)

        target_length = max(1, int(round(len(samples) * target_sample_rate / sample_rate)))
        source_positions = np.arange(len(samples), dtype=np.float32)
        target_positions = np.linspace(0, len(samples) - 1, num=target_length, dtype=np.float32)
        if preserve_channels and getattr(samples, "ndim", 1) > 1:
            channels = []
            for channel_index in range(samples.shape[1]):
                channels.append(np.interp(target_positions, source_positions, samples[:, channel_index]))
            samples = np.stack(channels, axis=1).astype(np.float32)
        else:
            samples = np.interp(target_positions, source_positions, samples).astype(np.float32)

    return samples.astype(np.float32)


def get_call_role_labels(language: str) -> tuple[str, str]:
    normalized = str(language or "").lower()
    if normalized.startswith("ru") or normalized == "russian":
        return ("Менеджер", "Клиент")
    return ("Sales manager", "Client")


def speaker_looks_like_manager(speaker: str) -> bool:
    normalized = str(speaker or "").strip().lower()
    return normalized in {"sales manager", "manager", "менеджер", "продавец"}


def assign_roles_from_stereo_channels(samples, sample_rate: int, segments: list[dict], language: str) -> list[dict]:
    if getattr(samples, "ndim", 1) < 2 or samples.shape[1] < 2:
        return segments

    sales_manager_label, client_label = get_call_role_labels(language)
    labeled_segments = []
    previous_speaker = sales_manager_label

    for segment in segments:
        start = max(0, int(round(float(segment.get("start") or 0) * sample_rate)))
        end = max(start + 1, int(round(float(segment.get("end") or 0) * sample_rate)))
        window = samples[start:end]
        if len(window) == 0:
            speaker = previous_speaker
        else:
            client_energy = float(abs(window[:, 0]).mean())
            manager_energy = float(abs(window[:, 1]).mean())
            if max(client_energy, manager_energy) < 1e-4:
                speaker = previous_speaker
            else:
                speaker = sales_manager_label if manager_energy >= client_energy else client_label

        labeled_segment = dict(segment)
        labeled_segment["speaker"] = speaker
        labeled_segments.append(labeled_segment)
        previous_speaker = speaker

    return labeled_segments


def run_speaker_diarization(recording_path: str) -> list[dict]:
    pipeline = get_speaker_diarization_pipeline()
    if pipeline is None:
        return []

    try:
        import torch

        samples = load_audio_samples(recording_path, preserve_channels=True)
        if getattr(samples, "ndim", 1) == 1:
            samples = samples[:, None]

        diarization_input = {
            "waveform": torch.from_numpy(samples.T.copy()),
            "sample_rate": 16000,
        }
    except Exception:
        diarization_input = recording_path

    diarization = pipeline(diarization_input)
    diarized_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        diarized_segments.append(
            {
                "start": float(turn.start),
                "end": float(turn.end),
                "speaker": str(speaker),
            }
        )

    return diarized_segments


def assign_roles_from_diarization(segments: list[dict], diarized_segments: list[dict], language: str) -> list[dict]:
    if not diarized_segments:
        return segments

    sales_manager_label, client_label = get_call_role_labels(language)
    role_by_speaker = {}
    next_role = sales_manager_label
    labeled_segments = []

    for segment in segments:
        segment_start = float(segment.get("start") or 0)
        segment_end = float(segment.get("end") or 0)
        best_speaker = None
        best_overlap = 0.0

        for diarized in diarized_segments:
            overlap = max(
                0.0,
                min(segment_end, float(diarized["end"])) - max(segment_start, float(diarized["start"])),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = diarized["speaker"]

        if best_speaker is None:
            speaker = labeled_segments[-1]["speaker"] if labeled_segments else sales_manager_label
        else:
            if best_speaker not in role_by_speaker:
                role_by_speaker[best_speaker] = next_role
                next_role = client_label if next_role == sales_manager_label else sales_manager_label
            speaker = role_by_speaker[best_speaker]

        labeled_segment = dict(segment)
        labeled_segment["speaker"] = speaker
        labeled_segments.append(labeled_segment)

    return labeled_segments


def list_transcript_speakers(segments: list[dict]) -> list[str]:
    speakers = []
    for segment in segments:
        speaker = str(segment.get("speaker") or "").strip()
        if speaker and speaker not in speakers:
            speakers.append(speaker)
    return speakers


def transcribe_call_recording(recording_path: str) -> dict:
    model = get_whisper_model()
    stereo_samples = None

    try:
        stereo_samples = load_audio_samples(recording_path, preserve_channels=True)
        audio_input = stereo_samples.mean(axis=1) if getattr(stereo_samples, "ndim", 1) > 1 else stereo_samples
    except Exception:
        audio_input = recording_path

    result = model.transcribe(audio_input, fp16=False, verbose=False)
    transcript_text = (result.get("text") or "").strip()
    segments = []
    language = result.get("language") or "unknown"

    for item in result.get("segments") or []:
        text = (item.get("text") or "").strip()
        if not text:
            continue

        segments.append(
            {
                "start": float(item.get("start") or 0),
                "end": float(item.get("end") or 0),
                "text": text,
                "speaker": "Speaker 1",
            }
        )

    if segments and stereo_samples is not None:
        segments = assign_roles_from_stereo_channels(stereo_samples, 16000, segments, language)

    if segments and all(segment.get("speaker") == "Speaker 1" for segment in segments):
        try:
            segments = assign_roles_from_diarization(segments, run_speaker_diarization(recording_path), language)
        except Exception:
            pass

    duration_seconds = segments[-1]["end"] if segments else None

    return {
        "id": str(uuid4()),
        "raw_text": transcript_text,
        "segments": segments,
        "speakers": list_transcript_speakers(segments),
        "language": language,
        "confidence": None,
        "duration_seconds": duration_seconds,
    }


def serialize_call(call: RealCall) -> dict:
    return {
        "id": str(call.id),
        "workspace_id": str(call.workspace_id),
        "user_id": str(call.user_id),
        "client_name": call.client_name,
        "notes": call.notes,
        "sale_completed": call.sale_completed,
        "status": call.status,
        "recording_path": call.recording_path,
        "duration_seconds": call.duration_seconds,
        "transcript": call.transcript,
        "report": call.report,
        "created_at": call.created_at.isoformat(),
        "completed_at": call.completed_at.isoformat() if call.completed_at else None,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = stores["users"].get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


app = FastAPI(title="UpSale API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    system_role: SystemRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    system_role: str
    is_blocked: bool
    created_at: str


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    password: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    created_at: str
    requires_password: bool = False
    is_member: bool = False


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    created_at: str


class JoinByPasswordRequest(BaseModel):
    password: str


class SetWorkspacePasswordRequest(BaseModel):
    password: str


class CallCreate(BaseModel):
    workspace_id: str
    client_name: Optional[str] = None
    notes: Optional[str] = None


class TranscriptSegmentResponse(BaseModel):
    start: float
    end: float
    text: str
    speaker: str


class TranscriptResponse(BaseModel):
    id: str
    raw_text: str
    segments: list[TranscriptSegmentResponse]
    speakers: list[str]
    language: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None


class CallResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    client_name: Optional[str]
    notes: Optional[str]
    sale_completed: bool
    status: str
    recording_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    transcript: Optional[TranscriptResponse] = None
    report: Optional[dict] = None
    created_at: str
    completed_at: Optional[str] = None


class UpdateSaleCompletedRequest(BaseModel):
    sale_completed: bool


class SalesStatsResponse(BaseModel):
    total_calls: int
    successful_sales: int
    conversion_rate: float
    total_members: int


class TrainerScenarioResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    trainer_name: str
    company_name: str
    summary: str
    scenario: str
    pressure_points: list[str]
    advice: list[str]
    max_turns: int


class TrainerMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


class TrainerReportResponse(BaseModel):
    id: str
    overall_score: int
    talk_ratio_seller: float
    talk_ratio_client: float
    engagement_score: int
    objection_handling_score: int
    closing_score: int
    product_knowledge_score: int
    communication_clarity_score: int
    strengths: list[str]
    areas_for_improvement: list[str]
    key_moments: list[dict]
    suggested_improvements: Optional[str] = None
    summary: Optional[str] = None
    full_analysis: Optional[str] = None


class TrainerSessionResponse(BaseModel):
    id: str
    workspace_id: str
    scenario_id: str
    language: str
    status: str
    end_reason: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    messages: list[TrainerMessageResponse]
    report: Optional[TrainerReportResponse] = None


class TrainerSessionCreateRequest(BaseModel):
    workspace_id: str
    scenario_id: str
    language: str = "ru"


class TrainerSessionMessageRequest(BaseModel):
    content: str


class TrainerSessionFinishRequest(BaseModel):
    reason: Optional[str] = None


def localize_trainer_scenario(scenario: dict, language: str) -> dict:
    if language == "en":
        return {
            key: scenario[key]
            for key in [
                "id",
                "title",
                "difficulty",
                "trainer_name",
                "company_name",
                "summary",
                "scenario",
                "pressure_points",
                "advice",
                "max_turns",
            ]
        }

    localized = TRAINER_SCENARIO_TRANSLATIONS.get(scenario["id"], {}).get(language)
    if not localized:
        return localize_trainer_scenario(scenario, "en")

    return {
        "id": scenario["id"],
        "title": localized["title"],
        "difficulty": scenario["difficulty"],
        "trainer_name": scenario["trainer_name"],
        "company_name": scenario["company_name"],
        "summary": localized["summary"],
        "scenario": localized["scenario"],
        "pressure_points": localized["pressure_points"],
        "advice": localized["advice"],
        "max_turns": scenario["max_turns"],
    }


def get_scenario_opening_line(scenario: dict, language: str) -> str:
    if language == "en":
        return scenario["opening_line"]

    localized = TRAINER_SCENARIO_TRANSLATIONS.get(scenario["id"], {}).get(language)
    if localized and localized.get("opening_line"):
        return localized["opening_line"]

    return scenario["opening_line"]


def get_workspace_membership(workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
    for member in stores["workspace_members"].values():
        if member.workspace_id == workspace_id and member.user_id == user_id:
            return member
    return None


def ensure_workspace_member(workspace_id: str, current_user: User) -> WorkspaceMember:
    member = get_workspace_membership(workspace_id, str(current_user.id))
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    return member


def build_sales_stats(workspace_id: str, user_id: Optional[str] = None) -> SalesStatsResponse:
    calls = [
        call for call in stores["calls"].values()
        if call.workspace_id == workspace_id and (user_id is None or call.user_id == user_id)
    ]
    total_calls = len(calls)
    successful_sales = sum(1 for call in calls if call.sale_completed)
    conversion_rate = (successful_sales / total_calls * 100) if total_calls > 0 else 0.0
    total_members = len(
        {str(member.user_id) for member in stores["workspace_members"].values() if member.workspace_id == workspace_id}
    )

    return SalesStatsResponse(
        total_calls=total_calls,
        successful_sales=successful_sales,
        conversion_rate=conversion_rate,
        total_members=total_members,
    )


def ensure_sales_manager(current_user: User) -> None:
    if current_user.system_role != SystemRole.SALES_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales managers can use the trainer",
        )


def get_trainer_scenario(scenario_id: str) -> dict:
    for scenario in TRAINER_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Trainer scenario not found",
    )


def ensure_openrouter_configured() -> str:
    if not OPENROUTER_API_KEY or "PASTE_YOUR_OPENROUTER_API_KEY_HERE" in OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouter is not configured. Set OPENROUTER_API_KEY in the root .env file.",
        )

    return OPENROUTER_API_KEY


def parse_json_object(content: str) -> dict:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start_index = content.find("{")
        end_index = content.rfind("}")
        if start_index != -1 and end_index != -1 and end_index > start_index:
            payload = json.loads(content[start_index:end_index + 1])
        else:
            raise

    if not isinstance(payload, dict):
        raise json.JSONDecodeError("Expected JSON object", content, 0)

    return payload


def strip_code_fence(content: str) -> str:
    stripped = content.strip()
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()

    return stripped


def normalize_trainer_payload(content: str) -> dict:
    cleaned_content = strip_code_fence(content)

    try:
        payload = parse_json_object(cleaned_content)
    except json.JSONDecodeError:
        fallback_reply = cleaned_content or "I need a clearer answer from you before we continue."
        return {
            "reply": fallback_reply,
            "should_end_call": False,
            "end_reason": None,
        }

    reply_text = str(payload.get("reply", "")).strip() or cleaned_content or "I need a clearer answer from you before we continue."
    end_reason = payload.get("end_reason")

    return {
        "reply": reply_text,
        "should_end_call": bool(payload.get("should_end_call", False)),
        "end_reason": str(end_reason).strip() if end_reason else None,
    }


async def openrouter_chat(messages: list[dict], model: str, temperature: float = 0.7) -> str:
    api_key = ensure_openrouter_configured()

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "UpSale",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenRouter request failed: {response.text}",
        )

    payload = response.json()
    choices = payload.get("choices", [])
    if not choices:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenRouter returned no completion choices",
        )

    return choices[0]["message"]["content"].strip()


def build_trainer_system_prompt(scenario: dict, language: str) -> str:
    language_name = SUPPORTED_APP_LANGUAGES.get(language, "Russian")

    return f"""
You are an AI sales trainer acting as a prospect in a role-play call.
Stay in character as {scenario['trainer_name']} from {scenario['company_name']}.
Difficulty: {scenario['difficulty']}.
Scenario: {scenario['scenario']}.
Persona: {scenario['persona']}.
Conversation language: {language_name}.

Rules:
- Reply as the prospect only, never as a coach or analyst.
- Keep replies concise, natural, and call-like.
- Speak strictly in {language_name} unless the sales manager explicitly asks to switch.
- Push back with realistic objections for this difficulty.
- If the sales manager says goodbye, asks to finish, or the conversation breaks down badly, you may end the call.
- Return strict JSON only with keys: reply, should_end_call, end_reason.
""".strip()


def build_report_fallback(session: dict, reason: str) -> dict:
    seller_messages = [message for message in session["messages"] if message["role"] == "user"]
    trainer_messages = [message for message in session["messages"] if message["role"] == "assistant"]
    total_messages = max(len(seller_messages) + len(trainer_messages), 1)
    seller_ratio = len(seller_messages) / total_messages
    is_russian = session.get("language") == "ru"

    return {
        "id": str(uuid4()),
        "overall_score": 70,
        "talk_ratio_seller": round(seller_ratio, 2),
        "talk_ratio_client": round(1 - seller_ratio, 2),
        "engagement_score": 72,
        "objection_handling_score": 68,
        "closing_score": 69,
        "product_knowledge_score": 71,
        "communication_clarity_score": 73,
        "strengths": [
            "Менеджер поддерживал движение разговора вперёд.",
            "Менеджер оставался вовлечённым на протяжении всей тренировки.",
        ] if is_russian else [
            "The manager kept the conversation moving forward.",
            "The manager stayed engaged throughout the role-play.",
        ],
        "areas_for_improvement": [
            "Добавить больше диагностики до перехода к питчу.",
            "Чётче связывать ценность с болью клиента.",
        ] if is_russian else [
            "Add more discovery before moving to the pitch.",
            "Use clearer value framing tied to client pain.",
        ],
        "key_moments": [
            {
                "timestamp": "00:00",
                "type": "neutral",
                "description": (
                    f"Создан резервный отчёт, потому что структурный анализ был недоступен ({reason})."
                    if is_russian
                    else f"Fallback report generated because structured analysis was unavailable ({reason})."
                ),
            }
        ],
        "suggested_improvements": (
            "Сфокусируйтесь на более точных диагностических вопросах, ясном языке ROI и сильном закрытии на следующий шаг."
            if is_russian
            else "Focus on sharper discovery questions, clearer ROI language, and a stronger next-step close."
        ),
        "summary": (
            "Разговор завершён, но структурированный LLM-анализ был недоступен, поэтому создан резервный отчёт."
            if is_russian
            else "The conversation was completed, but the structured LLM analysis was unavailable so a fallback report was generated."
        ),
        "full_analysis": None,
    }


def build_call_report_fallback(call: RealCall, reason: str) -> dict:
    transcript = call.transcript or {}
    segments = transcript.get("segments") or []
    language = str(transcript.get("language") or "").lower()
    is_russian = language.startswith("ru") or language == "russian"

    speaker_weights = {}
    for segment in segments:
        speaker = str(segment.get("speaker") or "Speaker 1")
        speaker_weights[speaker] = speaker_weights.get(speaker, 0) + max(len(str(segment.get("text") or "").split()), 1)

    seller_weight = sum(weight for speaker, weight in speaker_weights.items() if speaker_looks_like_manager(speaker))
    total_weight = sum(speaker_weights.values())

    if seller_weight and total_weight:
        talk_ratio_seller = round(seller_weight / total_weight, 2)
    elif speaker_weights:
        dominant_share = max(speaker_weights.values()) / max(sum(speaker_weights.values()), 1)
        talk_ratio_seller = round(min(max(dominant_share, 0.35), 0.65), 2)
    else:
        talk_ratio_seller = 0.5

    talk_ratio_client = round(1 - talk_ratio_seller, 2)

    return {
        "id": str(uuid4()),
        "overall_score": 70,
        "talk_ratio_seller": talk_ratio_seller,
        "talk_ratio_client": talk_ratio_client,
        "engagement_score": 72,
        "objection_handling_score": 68,
        "closing_score": 69,
        "product_knowledge_score": 71,
        "communication_clarity_score": 73,
        "strengths": [
            "Менеджер довёл разговор до содержательного обсуждения.",
            "В звонке есть материал для разбора и последующих улучшений.",
        ] if is_russian else [
            "The manager moved the conversation into a meaningful discussion.",
            "The call contains enough material for practical follow-up coaching.",
        ],
        "areas_for_improvement": [
            "Добавить больше диагностических вопросов до презентации решения.",
            "Сильнее связывать ценность продукта с задачами клиента.",
        ] if is_russian else [
            "Add more discovery questions before presenting the solution.",
            "Tie product value more directly to the client's needs.",
        ],
        "key_moments": [
            {
                "timestamp": "00:00",
                "type": "neutral",
                "description": (
                    f"Создан резервный отчёт, потому что структурный анализ был недоступен ({reason})."
                    if is_russian
                    else f"Fallback report generated because structured analysis was unavailable ({reason})."
                ),
            }
        ],
        "suggested_improvements": (
            "Уточняйте контекст клиента, фиксируйте ключевые боли и завершайте разговор конкретным следующим шагом."
            if is_russian
            else "Clarify the client context, anchor on the main pain points, and close with a concrete next step."
        ),
        "summary": (
            "Транскрибация завершена, но структурированный анализ был недоступен, поэтому создан резервный отчёт."
            if is_russian
            else "Transcription completed, but structured analysis was unavailable so a fallback report was generated."
        ),
        "full_analysis": None,
    }


def normalize_report_payload(payload: dict, fallback: dict) -> dict:

    def score(key: str) -> int:
        value = payload.get(key, fallback[key])
        try:
            return max(0, min(100, int(round(float(value)))))
        except (TypeError, ValueError):
            return fallback[key]

    def ratio(key: str) -> float:
        value = payload.get(key, fallback[key])
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return fallback[key]

    def string_list(key: str) -> list[str]:
        value = payload.get(key)
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
            return normalized or fallback[key]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return fallback[key]

    def optional_text(key: str, fallback_key: str) -> Optional[str]:
        value = payload.get(key)
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or fallback[fallback_key]
        if isinstance(value, list):
            normalized_items = [str(item).strip() for item in value if str(item).strip()]
            return "\n".join(normalized_items) if normalized_items else fallback[fallback_key]
        if value is None:
            return fallback[fallback_key]
        return str(value)

    def key_moment_list() -> list[dict]:
        value = payload.get("key_moments")
        if not isinstance(value, list):
            return fallback["key_moments"]

        normalized_moments = []
        for item in value:
            if isinstance(item, dict):
                timestamp = str(item.get("timestamp", "")).strip() or "00:00"
                moment_type = str(item.get("type", "neutral")).strip() or "neutral"
                description = str(item.get("description", "")).strip()
                if description:
                    normalized_moments.append(
                        {
                            "timestamp": timestamp,
                            "type": moment_type,
                            "description": description,
                        }
                    )
            elif isinstance(item, str) and item.strip():
                normalized_moments.append(
                    {
                        "timestamp": "00:00",
                        "type": "neutral",
                        "description": item.strip(),
                    }
                )

        return normalized_moments or fallback["key_moments"]

    return {
        "id": str(uuid4()),
        "overall_score": score("overall_score"),
        "talk_ratio_seller": ratio("talk_ratio_seller"),
        "talk_ratio_client": ratio("talk_ratio_client"),
        "engagement_score": score("engagement_score"),
        "objection_handling_score": score("objection_handling_score"),
        "closing_score": score("closing_score"),
        "product_knowledge_score": score("product_knowledge_score"),
        "communication_clarity_score": score("communication_clarity_score"),
        "strengths": string_list("strengths"),
        "areas_for_improvement": string_list("areas_for_improvement"),
        "key_moments": key_moment_list(),
        "suggested_improvements": optional_text("suggested_improvements", "suggested_improvements"),
        "summary": optional_text("summary", "summary"),
        "full_analysis": optional_text("full_analysis", "summary"),
    }


async def generate_trainer_report(session: dict, scenario: dict, end_reason: str) -> dict:
    language_name = SUPPORTED_APP_LANGUAGES.get(session.get("language"), "Russian")
    transcript_lines = []
    for message in session["messages"]:
        speaker = "Sales manager" if message["role"] == "user" else f"Trainer {scenario['trainer_name']}"
        transcript_lines.append(f"{speaker}: {message['content']}")

    report_prompt = [
        {
            "role": "system",
            "content": f"""
You analyze a sales training call and return strict JSON only.
Return keys: overall_score, talk_ratio_seller, talk_ratio_client, engagement_score,
objection_handling_score, closing_score, product_knowledge_score,
communication_clarity_score, strengths, areas_for_improvement, key_moments,
suggested_improvements, summary, full_analysis.

Rules:
- Scores are integers 0-100.
- Talk ratios are decimals from 0 to 1 and should add up to about 1.
- strengths and areas_for_improvement are arrays of short strings.
- key_moments is an array of objects with keys: timestamp, type, description.
- summary should be concise and manager-facing and written in {language_name}.
- full_analysis can be a short paragraph and must be written in {language_name}.
- strengths, areas_for_improvement, and key_moments descriptions must be written in {language_name}.
""".strip(),
        },
        {
            "role": "user",
            "content": (
                f"Scenario: {scenario['title']} ({scenario['difficulty']}).\n"
                f"End reason: {end_reason}.\n"
                f"Focus points: {', '.join(scenario['pressure_points'])}.\n\n"
                "Transcript:\n"
                + "\n".join(transcript_lines)
            ),
        },
    ]

    try:
        content = await openrouter_chat(report_prompt, OPENROUTER_REPORT_MODEL, temperature=0.2)
        return normalize_report_payload(parse_json_object(content), build_report_fallback(session, "invalid report payload"))
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        return build_report_fallback(session, f"report service failure: {exc.detail}")
    except json.JSONDecodeError:
        return build_report_fallback(session, "report json parse failure")
    except Exception:
        return build_report_fallback(session, "report generation failure")


async def populate_trainer_report(session_id: str) -> None:
    session = stores["trainer_sessions"].get(session_id)
    if not session or session.get("report"):
        return

    scenario = get_trainer_scenario(session["scenario_id"])
    end_reason = session.get("end_reason") or "session_completed"

    try:
        session["report"] = await generate_trainer_report(session, scenario, end_reason)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        session["report"] = build_report_fallback(session, f"report service failure: {exc.detail}")
    except Exception:
        session["report"] = build_report_fallback(session, "report generation failure")


def schedule_trainer_report_generation(session_id: str) -> None:
    existing_task = _trainer_report_tasks.get(session_id)
    if existing_task and not existing_task.done():
        return

    task = asyncio.create_task(populate_trainer_report(session_id))
    _trainer_report_tasks[session_id] = task

    def cleanup_report_task(completed_task: asyncio.Task) -> None:
        _trainer_report_tasks.pop(session_id, None)
        try:
            completed_task.result()
        except HTTPException:
            session = stores["trainer_sessions"].get(session_id)
            if session and not session.get("report"):
                session["report"] = build_report_fallback(session, "report service unavailable")
        except Exception:
            session = stores["trainer_sessions"].get(session_id)
            if session and not session.get("report"):
                session["report"] = build_report_fallback(session, "report generation failure")

    task.add_done_callback(cleanup_report_task)


async def generate_call_report(call: RealCall) -> dict:
    transcript = call.transcript or {}
    segments = transcript.get("segments") or []
    transcript_lines = []

    for segment in segments:
        speaker = str(segment.get("speaker") or "Speaker")
        text = str(segment.get("text") or "").strip()
        if text:
            transcript_lines.append(f"{speaker}: {text}")

    if not transcript_lines and transcript.get("raw_text"):
        transcript_lines.append(str(transcript["raw_text"]).strip())

    if not transcript_lines:
        return build_call_report_fallback(call, "empty transcript")

    language = str(transcript.get("language") or "").lower()
    if language.startswith("ru") or language == "russian":
        language_name = "Russian"
    elif language.startswith("en") or language == "english":
        language_name = "English"
    else:
        language_name = "English"

    report_prompt = [
        {
            "role": "system",
            "content": f"""
You analyze a real sales call transcript and return strict JSON only.
Return keys: overall_score, talk_ratio_seller, talk_ratio_client, engagement_score,
objection_handling_score, closing_score, product_knowledge_score,
communication_clarity_score, strengths, areas_for_improvement, key_moments,
suggested_improvements, summary, full_analysis.

Rules:
- Scores are integers 0-100.
- Talk ratios are decimals from 0 to 1 and should add up to about 1.
- strengths and areas_for_improvement are arrays of short strings.
- key_moments is an array of objects with keys: timestamp, type, description.
- summary must be concise, practical, and written in {language_name}.
- full_analysis can be a short paragraph and must be written in {language_name}.
- strengths, areas_for_improvement, and key_moments descriptions must be written in {language_name}.
""".strip(),
        },
        {
            "role": "user",
            "content": (
                f"Client name: {call.client_name or 'Unknown'}.\n"
                f"Manager marked sale completed: {'yes' if call.sale_completed else 'no'}.\n"
                "Transcript:\n"
                + "\n".join(transcript_lines)
            ),
        },
    ]

    try:
        content = await openrouter_chat(report_prompt, OPENROUTER_REPORT_MODEL, temperature=0.2)
        return normalize_report_payload(parse_json_object(content), build_call_report_fallback(call, "invalid report payload"))
    except HTTPException as exc:
        return build_call_report_fallback(call, f"report service failure: {exc.detail}")
    except json.JSONDecodeError:
        return build_call_report_fallback(call, "report json parse failure")
    except Exception:
        return build_call_report_fallback(call, "report generation failure")


def build_session_response(session: dict) -> TrainerSessionResponse:
    return TrainerSessionResponse(
        id=session["id"],
        workspace_id=session["workspace_id"],
        scenario_id=session["scenario_id"],
        language=session["language"],
        status=session["status"],
        end_reason=session.get("end_reason"),
        started_at=session["started_at"],
        completed_at=session.get("completed_at"),
        messages=[TrainerMessageResponse(**message) for message in session["messages"]],
        report=TrainerReportResponse(**session["report"]) if session.get("report") else None,
    )


def complete_trainer_session(session: dict, end_reason: str) -> None:
    session["status"] = "completed"
    session["end_reason"] = end_reason
    session["completed_at"] = datetime.utcnow().isoformat()
    schedule_trainer_report_generation(session["id"])


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    for user in stores["users"].values():
        if user.email == request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    
    user = User(
        id=uuid4(),
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        system_role=request.system_role,
    )
    stores["users"][str(user.id)] = user
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        system_role=user.system_role.value,
        is_blocked=user.is_blocked,
        created_at=user.created_at.isoformat(),
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = None
    for u in stores["users"].values():
        if u.email == request.email:
            user = u
            break
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        system_role=current_user.system_role.value,
        is_blocked=current_user.is_blocked,
        created_at=current_user.created_at.isoformat(),
    )


@app.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(current_user: User = Depends(get_current_user)):
    workspace_ids = set()
    for member in stores["workspace_members"].values():
        if member.user_id == str(current_user.id):
            workspace_ids.add(str(member.workspace_id))
    
    return [
        WorkspaceResponse(
            id=str(w.id),
            name=w.name,
            description=w.description,
            owner_id=str(w.owner_id),
            created_at=w.created_at.isoformat(),
            requires_password=bool(w.password),
            is_member=True,
        )
        for w in stores["workspaces"].values()
        if str(w.id) in workspace_ids
    ]


@app.get("/workspaces/discover", response_model=list[WorkspaceResponse])
async def discover_workspaces(current_user: User = Depends(get_current_user)):
    workspace_ids = set()
    for member in stores["workspace_members"].values():
        if member.user_id == str(current_user.id):
            workspace_ids.add(str(member.workspace_id))

    return [
        WorkspaceResponse(
            id=str(workspace.id),
            name=workspace.name,
            description=workspace.description,
            owner_id=str(workspace.owner_id),
            created_at=workspace.created_at.isoformat(),
            requires_password=bool(workspace.password),
            is_member=str(workspace.id) in workspace_ids,
        )
        for workspace in stores["workspaces"].values()
    ]


@app.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create workspaces",
        )

    if not request.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace password is required",
        )

    workspace = Workspace(
        id=str(uuid4()),
        name=request.name,
        owner_id=str(current_user.id),
        description=request.description,
        password=get_password_hash(request.password),
    )
    stores["workspaces"][str(workspace.id)] = workspace
    
    member = WorkspaceMember(
        id=str(uuid4()),
        workspace_id=workspace.id,
        user_id=str(current_user.id),
        role=WorkspaceRole.OWNER,
    )
    stores["workspace_members"][str(member.id)] = member
    
    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        description=workspace.description,
        owner_id=str(workspace.owner_id),
        created_at=workspace.created_at.isoformat(),
        requires_password=True,
        is_member=True,
    )


@app.get("/workspaces/{workspace_id}/members", response_model=list[MemberResponse])
async def list_workspace_members(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    ensure_workspace_member(workspace_id, current_user)
    
    result = []
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id:
            user = stores["users"].get(m.user_id)
            if user:
                result.append(MemberResponse(
                    id=str(m.id),
                    user_id=str(m.user_id),
                    email=user.email,
                    full_name=user.full_name,
                    role=m.role.value,
                    created_at=m.created_at.isoformat(),
                ))
    return result


@app.get("/workspaces/{workspace_id}/my-stats", response_model=SalesStatsResponse)
async def get_my_workspace_stats(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.SALES_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales managers can view personal workspace stats",
        )

    ensure_workspace_member(workspace_id, current_user)
    return build_sales_stats(workspace_id, str(current_user.id))


@app.post("/workspaces/{workspace_id}/join", response_model=MemberResponse)
async def join_workspace_by_password(
    workspace_id: str,
    request: JoinByPasswordRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.SALES_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales managers can join workspaces by password",
        )

    workspace = stores["workspaces"].get(str(workspace_id))
    if not workspace or not workspace.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace has no password or not found",
        )
    if not verify_password(request.password, workspace.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workspace password",
        )
    
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            user = stores["users"].get(m.user_id)
            return MemberResponse(
                id=str(m.id),
                user_id=str(m.user_id),
                email=user.email if user else "",
                full_name=user.full_name if user else None,
                role=m.role.value,
                created_at=m.created_at.isoformat(),
            )
    
    member = WorkspaceMember(
        id=str(uuid4()),
        workspace_id=str(workspace_id),
        user_id=str(current_user.id),
        role=WorkspaceRole.MEMBER,
    )
    stores["workspace_members"][str(member.id)] = member
    
    return MemberResponse(
        id=str(member.id),
        user_id=str(member.user_id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=member.role.value,
        created_at=member.created_at.isoformat(),
    )


@app.post("/workspaces/{workspace_id}/set-password", response_model=WorkspaceResponse)
async def set_workspace_password(
    workspace_id: str,
    request: SetWorkspacePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    workspace = stores["workspaces"].get(str(workspace_id))
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    member = get_workspace_membership(workspace_id, str(current_user.id))
    
    if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to set workspace password",
        )
    
    workspace.password = get_password_hash(request.password) if request.password else None
    
    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        description=workspace.description,
        owner_id=str(workspace.owner_id),
        created_at=workspace.created_at.isoformat(),
        requires_password=bool(workspace.password),
        is_member=True,
    )


@app.delete("/workspaces/{workspace_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    target_user_id: str,
    current_user: User = Depends(get_current_user),
):
    workspace = stores["workspaces"].get(str(workspace_id))
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    member = get_workspace_membership(workspace_id, str(current_user.id))
    
    if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove members",
        )
    
    for m_id, m in list(stores["workspace_members"].items()):
        if m.workspace_id == workspace_id and m.user_id == target_user_id:
            del stores["workspace_members"][m_id]


@app.delete("/workspaces/{workspace_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    membership = get_workspace_membership(workspace_id, str(current_user.id))
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace membership not found",
        )

    if membership.role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace owner cannot leave the workspace",
        )

    for member_id, member in list(stores["workspace_members"].items()):
        if member.workspace_id == workspace_id and member.user_id == str(current_user.id):
            del stores["workspace_members"][member_id]
            return


@app.get("/calls", response_model=list[CallResponse])
async def list_calls(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    ensure_workspace_member(workspace_id, current_user)

    calls = [
        CallResponse(**serialize_call(c))
        for c in stores["calls"].values()
        if c.workspace_id == workspace_id
    ]

    if current_user.system_role == SystemRole.SALES_MANAGER:
        calls = [call for call in calls if call.user_id == str(current_user.id)]

    return calls


@app.post("/calls", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    request: CallCreate,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.SALES_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales managers can create calls",
        )

    workspace = stores["workspaces"].get(str(request.workspace_id))
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    ensure_workspace_member(request.workspace_id, current_user)
    
    call = RealCall(
        id=str(uuid4()),
        workspace_id=str(request.workspace_id),
        user_id=str(current_user.id),
        client_name=request.client_name,
        notes=request.notes,
    )
    stores["calls"][str(call.id)] = call
    
    return CallResponse(**serialize_call(call))


@app.get("/calls/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(str(call_id))
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    ensure_workspace_member(call.workspace_id, current_user)

    if current_user.system_role == SystemRole.SALES_MANAGER and call.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales managers can only view their own calls",
        )
    
    return CallResponse(**serialize_call(call))


@app.patch("/calls/{call_id}/sale-completed", response_model=CallResponse)
async def update_sale_completed(
    call_id: str,
    request: UpdateSaleCompletedRequest,
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(str(call_id))
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    if current_user.system_role != SystemRole.SALES_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sales managers can update call results",
        )

    ensure_workspace_member(call.workspace_id, current_user)

    if call.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales managers can only update their own calls",
        )
    
    call.sale_completed = request.sale_completed
    
    return CallResponse(**serialize_call(call))


@app.post("/calls/{call_id}/transcribe", response_model=CallResponse)
async def transcribe_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(str(call_id))
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    ensure_workspace_member(call.workspace_id, current_user)

    if current_user.system_role == SystemRole.SALES_MANAGER and call.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales managers can only transcribe their own calls",
        )

    if not call.recording_path or not os.path.exists(call.recording_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording not found for this call",
        )

    call.status = CallStatus.TRANSCRIBING.value

    try:
        transcript = transcribe_call_recording(call.recording_path)
        call.transcript = transcript
        call.duration_seconds = transcript.get("duration_seconds")
        call.status = CallStatus.ANALYZING.value
        call.report = await generate_call_report(call)
        call.status = CallStatus.COMPLETED.value
        call.completed_at = datetime.utcnow()
    except Exception as exc:
        call.status = CallStatus.FAILED.value
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe call: {exc}",
        ) from exc

    return CallResponse(**serialize_call(call))


@app.post("/calls/{call_id}/analyze", response_model=CallResponse)
async def analyze_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(str(call_id))
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    ensure_workspace_member(call.workspace_id, current_user)

    if current_user.system_role == SystemRole.SALES_MANAGER and call.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales managers can only analyze their own calls",
        )

    if not call.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript not found for this call",
        )

    call.status = CallStatus.ANALYZING.value
    call.report = await generate_call_report(call)
    call.status = CallStatus.COMPLETED.value
    call.completed_at = datetime.utcnow()

    return CallResponse(**serialize_call(call))


@app.post("/calls/{call_id}/upload", response_model=CallResponse)
async def upload_call_recording(
    call_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(str(call_id))
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    ensure_workspace_member(call.workspace_id, current_user)

    if current_user.system_role != SystemRole.SALES_MANAGER or call.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales managers can only upload recordings to their own calls",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording file is required",
        )

    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    extension = os.path.splitext(file.filename)[1] or ".wav"
    recording_path = os.path.join(RECORDINGS_DIR, f"{call.id}{extension}")
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded recording is empty",
        )

    with open(recording_path, "wb") as output_file:
        output_file.write(file_bytes)

    call.recording_path = recording_path
    call.status = CallStatus.TRANSCRIBING.value

    try:
        transcript = transcribe_call_recording(recording_path)
        call.transcript = transcript
        call.duration_seconds = transcript.get("duration_seconds")
        call.status = CallStatus.ANALYZING.value
        call.report = await generate_call_report(call)
        call.status = CallStatus.COMPLETED.value
        call.completed_at = datetime.utcnow()
    except Exception as exc:
        call.status = CallStatus.FAILED.value
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process recording: {exc}",
        ) from exc

    return CallResponse(**serialize_call(call))


@app.get("/admin/employees", response_model=list[UserResponse])
async def list_employees(current_user: User = Depends(get_current_user)):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view sales managers",
        )
    
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            system_role=u.system_role.value,
            is_blocked=u.is_blocked,
            created_at=u.created_at.isoformat(),
        )
        for u in stores["users"].values()
        if u.system_role == SystemRole.SALES_MANAGER
    ]


@app.post("/admin/employees/{user_id}/block", response_model=UserResponse)
async def block_employee(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can block sales managers",
        )
    
    user = stores["users"].get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_blocked = True
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        system_role=user.system_role.value,
        is_blocked=user.is_blocked,
        created_at=user.created_at.isoformat(),
    )


@app.delete("/admin/employees/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete sales managers",
        )
    
    if user_id not in stores["users"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    del stores["users"][user_id]
    
    for m_id, m in list(stores["workspace_members"].items()):
        if m.user_id == user_id:
            del stores["workspace_members"][m_id]


@app.get("/admin/workspaces/{workspace_id}/stats", response_model=SalesStatsResponse)
async def get_workspace_stats(
    workspace_id: str,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view workspace stats",
        )
    
    workspace = stores["workspaces"].get(str(workspace_id))
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    ensure_workspace_member(workspace_id, current_user)
    return build_sales_stats(workspace_id, user_id)


@app.post("/admin/workspaces/{workspace_id}/members/{target_user_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_from_workspace(
    workspace_id: str,
    target_user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove members",
        )
    
    target_membership = get_workspace_membership(workspace_id, target_user_id)
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace membership not found",
        )

    if target_membership.role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace owner cannot be removed",
        )

    for m_id, m in list(stores["workspace_members"].items()):
        if m.workspace_id == workspace_id and m.user_id == target_user_id:
            del stores["workspace_members"][m_id]
            return


@app.post("/admin/workspaces/{workspace_id}/members/{target_user_id}/remove-and-block", response_model=UserResponse)
async def remove_and_block_member_from_workspace(
    workspace_id: str,
    target_user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove and block members",
        )

    target_user = stores["users"].get(target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    target_membership = get_workspace_membership(workspace_id, target_user_id)
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace membership not found",
        )

    if target_membership.role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace owner cannot be removed or blocked",
        )

    for member_id, member in list(stores["workspace_members"].items()):
        if member.workspace_id == workspace_id and member.user_id == target_user_id:
            del stores["workspace_members"][member_id]

    target_user.is_blocked = True

    return UserResponse(
        id=str(target_user.id),
        email=target_user.email,
        full_name=target_user.full_name,
        system_role=target_user.system_role.value,
        is_blocked=target_user.is_blocked,
        created_at=target_user.created_at.isoformat(),
    )


@app.get("/trainer/scenarios", response_model=list[TrainerScenarioResponse])
async def list_trainer_scenarios(
    workspace_id: str,
    language: str = "en",
    current_user: User = Depends(get_current_user),
):
    ensure_sales_manager(current_user)
    ensure_workspace_member(workspace_id, current_user)

    if language not in SUPPORTED_APP_LANGUAGES:
        language = "en"

    return [
        TrainerScenarioResponse(**localize_trainer_scenario(scenario, language))
        for scenario in TRAINER_SCENARIOS
    ]


@app.post("/trainer/sessions", response_model=TrainerSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_trainer_session(
    request: TrainerSessionCreateRequest,
    current_user: User = Depends(get_current_user),
):
    ensure_sales_manager(current_user)
    ensure_workspace_member(request.workspace_id, current_user)
    ensure_openrouter_configured()

    if request.language not in SUPPORTED_APP_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported trainer language. Use 'ru' or 'en'.",
        )

    scenario = get_trainer_scenario(request.scenario_id)
    started_at = datetime.utcnow().isoformat()
    session = {
        "id": str(uuid4()),
        "workspace_id": request.workspace_id,
        "user_id": str(current_user.id),
        "scenario_id": scenario["id"],
        "language": request.language,
        "status": "in_progress",
        "end_reason": None,
        "started_at": started_at,
        "completed_at": None,
        "messages": [
            {
                "role": "assistant",
                "content": get_scenario_opening_line(scenario, request.language),
                "created_at": started_at,
            }
        ],
        "report": None,
    }
    stores["trainer_sessions"][session["id"]] = session
    return build_session_response(session)


@app.get("/trainer/sessions", response_model=list[TrainerSessionResponse])
async def list_trainer_sessions(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    ensure_sales_manager(current_user)
    ensure_workspace_member(workspace_id, current_user)

    sessions = [
        session
        for session in stores["trainer_sessions"].values()
        if session["workspace_id"] == workspace_id and session["user_id"] == str(current_user.id)
    ]
    sessions.sort(key=lambda session: session["started_at"], reverse=True)

    return [build_session_response(session) for session in sessions]


@app.get("/trainer/sessions/{session_id}", response_model=TrainerSessionResponse)
async def get_trainer_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    ensure_sales_manager(current_user)

    session = stores["trainer_sessions"].get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer session not found")

    ensure_workspace_member(session["workspace_id"], current_user)
    if session["user_id"] != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trainer session")

    return build_session_response(session)


@app.post("/trainer/sessions/{session_id}/messages", response_model=TrainerSessionResponse)
async def send_trainer_message(
    session_id: str,
    request: TrainerSessionMessageRequest,
    current_user: User = Depends(get_current_user),
):
    ensure_sales_manager(current_user)

    session = stores["trainer_sessions"].get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer session not found")

    ensure_workspace_member(session["workspace_id"], current_user)
    if session["user_id"] != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trainer session")
    if session["status"] != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trainer session is already finished")

    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content is required")

    scenario = get_trainer_scenario(session["scenario_id"])
    session["messages"].append(
        {
            "role": "user",
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }
    )

    completion_messages = [{"role": "system", "content": build_trainer_system_prompt(scenario, session["language"])}]
    completion_messages.extend(
        {"role": message["role"], "content": message["content"]}
        for message in session["messages"]
    )

    trainer_payload = normalize_trainer_payload(
        await openrouter_chat(completion_messages, OPENROUTER_TRAINER_MODEL, temperature=0.8)
    )

    reply_text = str(trainer_payload.get("reply", "")).strip() or "I need a clearer answer from you before we continue."
    should_end_call = bool(trainer_payload.get("should_end_call", False))
    end_reason = str(trainer_payload.get("end_reason") or "session_completed")

    session["messages"].append(
        {
            "role": "assistant",
            "content": reply_text,
            "created_at": datetime.utcnow().isoformat(),
        }
    )

    seller_turns = sum(1 for message in session["messages"] if message["role"] == "user")
    if seller_turns >= scenario["max_turns"]:
        should_end_call = True
        if not trainer_payload.get("end_reason"):
            end_reason = "trainer_ended_after_max_turns"

    if should_end_call:
        complete_trainer_session(session, end_reason)

    return build_session_response(session)


@app.post("/trainer/sessions/{session_id}/finish", response_model=TrainerSessionResponse)
async def finish_trainer_session(
    session_id: str,
    request: TrainerSessionFinishRequest,
    current_user: User = Depends(get_current_user),
):
    ensure_sales_manager(current_user)

    session = stores["trainer_sessions"].get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer session not found")

    ensure_workspace_member(session["workspace_id"], current_user)
    if session["user_id"] != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your trainer session")

    if session["status"] == "completed":
        return build_session_response(session)

    complete_trainer_session(session, request.reason or "sales_manager_finished")
    return build_session_response(session)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
