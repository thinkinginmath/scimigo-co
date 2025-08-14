"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-08-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tracks table
    op.create_table('tracks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('difficulty', sa.String(), nullable=False),
        sa.Column('modules', postgresql.JSONB(), nullable=False),
        sa.Column('outcomes', postgresql.JSONB(), nullable=False),
        sa.Column('is_published', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tracks_subject'), 'tracks', ['subject'], unique=False)
    op.create_index(op.f('ix_tracks_is_published'), 'tracks', ['is_published'], unique=False)

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('track_id', sa.String(), nullable=True),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('state', postgresql.JSONB(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_sessions_track_id'), 'sessions', ['track_id'], unique=False)

    # Create submissions table
    op.create_table('submissions',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('session_id', postgresql.UUID(), nullable=False),
        sa.Column('problem_id', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_submissions_session_id'), 'submissions', ['session_id'], unique=False)
    op.create_index(op.f('ix_submissions_problem_id'), 'submissions', ['problem_id'], unique=False)

    # Create mastery table
    op.create_table('mastery',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('proficiency', sa.Float(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('successes', sa.Integer(), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'topic', 'subject')
    )
    op.create_index(op.f('ix_mastery_user_id'), 'mastery', ['user_id'], unique=False)
    op.create_index(op.f('ix_mastery_topic'), 'mastery', ['topic'], unique=False)

    # Create review_queue table
    op.create_table('review_queue',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('problem_id', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('interval_days', sa.Integer(), nullable=False),
        sa.Column('ease_factor', sa.Float(), nullable=False),
        sa.Column('review_count', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'problem_id')
    )
    op.create_index(op.f('ix_review_queue_user_id'), 'review_queue', ['user_id'], unique=False)
    op.create_index(op.f('ix_review_queue_due_date'), 'review_queue', ['due_date'], unique=False)

    # Create rubrics table
    op.create_table('rubrics',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('problem_id', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('criteria', postgresql.JSONB(), nullable=False),
        sa.Column('max_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('problem_id')
    )
    op.create_index(op.f('ix_rubrics_problem_id'), 'rubrics', ['problem_id'], unique=False)

    # Create rubric_scores table
    op.create_table('rubric_scores',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('submission_id', postgresql.UUID(), nullable=False),
        sa.Column('rubric_id', postgresql.UUID(), nullable=False),
        sa.Column('scores', postgresql.JSONB(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['rubric_id'], ['rubrics.id'], ),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id')
    )


def downgrade() -> None:
    op.drop_table('rubric_scores')
    op.drop_index(op.f('ix_rubrics_problem_id'), table_name='rubrics')
    op.drop_table('rubrics')
    op.drop_index(op.f('ix_review_queue_due_date'), table_name='review_queue')
    op.drop_index(op.f('ix_review_queue_user_id'), table_name='review_queue')
    op.drop_table('review_queue')
    op.drop_index(op.f('ix_mastery_topic'), table_name='mastery')
    op.drop_index(op.f('ix_mastery_user_id'), table_name='mastery')
    op.drop_table('mastery')
    op.drop_index(op.f('ix_submissions_problem_id'), table_name='submissions')
    op.drop_index(op.f('ix_submissions_session_id'), table_name='submissions')
    op.drop_table('submissions')
    op.drop_index(op.f('ix_sessions_track_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_tracks_is_published'), table_name='tracks')
    op.drop_index(op.f('ix_tracks_subject'), table_name='tracks')
    op.drop_table('tracks')