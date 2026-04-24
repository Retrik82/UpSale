export interface User {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url?: string | null;
  system_role?: "admin" | "sales_manager";
  is_blocked?: boolean;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  requires_password?: boolean;
  is_member?: boolean;
}

export interface WorkspaceMember {
  id: string;
  user_id: string;
  email: string;
  full_name: string | null;
  role: "owner" | "admin" | "member" | "viewer";
  created_at: string;
}

export interface ClientTemplate {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  company_name: string | null;
  industry: string | null;
  pain_points: string[];
  objections: string[];
  talking_points: string[];
  preferred_tone: string;
  created_at: string;
}

export type CallStatus = "recording" | "pending" | "transcribing" | "analyzing" | "completed" | "failed";

export interface RealCall {
  id: string;
  workspace_id: string;
  user_id?: string;
  client_template_id?: string | null;
  recording_path?: string | null;
  duration_seconds?: number | null;
  status: CallStatus;
  client_name: string | null;
  notes: string | null;
  sale_completed?: boolean;
  created_at: string;
  completed_at?: string | null;
  transcript?: Transcript | null;
  report?: CallReport | null;
}

export interface Transcript {
  id: string;
  raw_text: string;
  segments: TranscriptSegment[];
  speakers: string[];
  language: string;
  confidence: number | null;
  duration_seconds: number | null;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker: string;
}

export interface CallReport {
  id: string;
  overall_score: number;
  talk_ratio_seller: number;
  talk_ratio_client: number;
  engagement_score: number;
  objection_handling_score: number;
  closing_score: number;
  product_knowledge_score: number;
  communication_clarity_score: number;
  strengths: string[];
  areas_for_improvement: string[];
  key_moments: KeyMoment[];
  suggested_improvements: string | null;
  summary: string | null;
  full_analysis: string | null;
}

export interface KeyMoment {
  timestamp: string;
  type: "positive" | "negative" | "neutral";
  description: string;
}

export type SimulationStatus = "draft" | "ready" | "in_progress" | "completed" | "failed";

export interface SimulationSession {
  id: string;
  workspace_id: string;
  client_template_id: string | null;
  name: string;
  scenario: string | null;
  status: SimulationStatus;
  duration_seconds: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  transcript?: string | null;
  user_input?: string[];
  ai_responses?: string[];
  metrics?: Record<string, unknown>;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface WorkspaceStats {
  total_calls: number;
  successful_sales: number;
  conversion_rate: number;
  total_members: number;
}

export interface ApiError {
  detail: string;
}
