"""initial migration

Revision ID: 001_initial
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    workspace_role = postgresql.ENUM('owner', 'admin', 'member', 'viewer', name='workspacerole')
    workspace_role.create(op.get_bind())
    
    call_status = postgresql.ENUM('recording', 'pending', 'transcribing', 'analyzing', 'completed', 'failed', name='callstatus')
    call_status.create(op.get_bind())
    
    simulation_status = postgresql.ENUM('draft', 'ready', 'in_progress', 'completed', 'failed', name='simulationstatus')
    simulation_status.create(op.get_bind())

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('settings', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'workspace_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'member', 'viewer', name='workspacerole', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'client_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('pain_points', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('objections', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('talking_points', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('preferred_tone', sa.String(50), default='professional'),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'real_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('client_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recording_path', sa.String(500), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('client_name', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'simulation_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('client_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('scenario', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='draft'),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('user_input', postgresql.JSONB, default=list),
        sa.Column('ai_responses', postgresql.JSONB, default=list),
        sa.Column('metrics', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('real_calls.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('segments', postgresql.JSONB, default=list),
        sa.Column('speakers', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('language', sa.String(10), default='en'),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'call_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('real_calls.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('overall_score', sa.Integer(), default=0),
        sa.Column('talk_ratio_seller', sa.Float(), default=0.0),
        sa.Column('talk_ratio_client', sa.Float(), default=0.0),
        sa.Column('engagement_score', sa.Integer(), default=0),
        sa.Column('objection_handling_score', sa.Integer(), default=0),
        sa.Column('closing_score', sa.Integer(), default=0),
        sa.Column('product_knowledge_score', sa.Integer(), default=0),
        sa.Column('communication_clarity_score', sa.Integer(), default=0),
        sa.Column('strengths', postgresql.JSONB, default=list),
        sa.Column('areas_for_improvement', postgresql.JSONB, default=list),
        sa.Column('key_moments', postgresql.JSONB, default=list),
        sa.Column('suggested_improvements', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('full_analysis', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('call_reports')
    op.drop_table('transcripts')
    op.drop_table('simulation_sessions')
    op.drop_table('real_calls')
    op.drop_table('client_templates')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    op.execute('DROP TYPE IF EXISTS simulationstatus')
    op.execute('DROP TYPE IF EXISTS callstatus')
    op.execute('DROP TYPE IF EXISTS workspacerole')
