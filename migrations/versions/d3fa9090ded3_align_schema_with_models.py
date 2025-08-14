"""align_schema_with_models

Revision ID: d3fa9090ded3
Revises: 001
Create Date: 2025-08-14 03:44:16.660072

Migration to align the database schema with the SQLAlchemy models. This drops
the legacy tables from the initial migration and recreates them using the
latest model definitions so that the database matches the ORM models defined in
``co.db.models``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d3fa9090ded3"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the new schema."""

    # Drop legacy tables
    op.drop_table("rubric_scores")
    op.drop_table("rubrics")
    op.drop_table("review_queue")
    op.drop_table("mastery")
    op.drop_table("submissions")
    op.drop_table("sessions")
    op.drop_table("tracks")

    # Recreate tracks table
    op.create_table(
        "tracks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "labels",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "modules",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("version", sa.String(), nullable=False, server_default="v1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subject IN ('coding', 'math', 'systems')", name="check_subject"
        ),
    )
    op.create_index("ix_tracks_slug", "tracks", ["slug"], unique=True)
    op.create_index("ix_tracks_subject", "tracks", ["subject"], unique=False)
    op.create_index(
        "idx_tracks_labels",
        "tracks",
        ["labels"],
        postgresql_using="gin",
    )

    # Recreate sessions table
    op.create_table(
        "sessions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column(
            "track_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracks.id"),
            nullable=True,
        ),
        sa.Column("problem_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("last_hint_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subject IN ('coding', 'math', 'systems')",
            name="check_session_subject",
        ),
        sa.CheckConstraint("mode IN ('practice', 'mock', 'track')", name="check_mode"),
    )
    op.create_index("idx_sessions_user", "sessions", ["user_id"], unique=False)
    op.create_index("idx_sessions_track", "sessions", ["track_id"], unique=False)
    op.create_index(
        "idx_sessions_user_subject",
        "sessions",
        ["user_id", "subject"],
        unique=False,
    )

    # Recreate submissions table
    op.create_table(
        "submissions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("visible_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visible_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hidden_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hidden_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "categories",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("exec_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_sha256", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subject IN ('coding', 'math', 'systems')",
            name="check_submission_subject",
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'timeout', 'error')",
            name="check_status",
        ),
    )
    op.create_index(
        "idx_submissions_session", "submissions", ["session_id"], unique=False
    )
    op.create_index("idx_submissions_user", "submissions", ["user_id"], unique=False)
    op.create_index(
        "idx_submissions_problem", "submissions", ["problem_id"], unique=False
    )
    op.create_index(
        "idx_submissions_user_problem",
        "submissions",
        ["user_id", "problem_id"],
        unique=False,
    )

    # Recreate mastery table
    op.create_table(
        "mastery",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key_type", sa.String(), primary_key=True),
        sa.Column("key_id", sa.String(), primary_key=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("ema", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("key_type IN ('topic', 'outcome')", name="check_key_type"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="check_score_range"),
    )
    op.create_index("idx_mastery_user", "mastery", ["user_id"], unique=False)

    # Recreate review_queue table
    op.create_table(
        "review_queue",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "problem_id", name="unique_user_problem"),
    )
    op.create_index("idx_review_due", "review_queue", ["next_due_at"], unique=False)

    # Recreate rubrics table
    op.create_table(
        "rubrics",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(), nullable=False),
        sa.Column(
            "meta_data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Recreate rubric_scores table
    op.create_table(
        "rubric_scores",
        sa.Column(
            "submission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "rubric_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rubrics.id"),
            primary_key=True,
        ),
        sa.Column("scores", postgresql.JSONB(), nullable=False),
        sa.Column("feedback", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    """Revert to the legacy schema (drops new tables)."""

    op.drop_table("rubric_scores")
    op.drop_table("rubrics")
    op.drop_index("idx_review_due", table_name="review_queue")
    op.drop_table("review_queue")
    op.drop_index("idx_mastery_user", table_name="mastery")
    op.drop_table("mastery")
    op.drop_index("idx_submissions_user_problem", table_name="submissions")
    op.drop_index("idx_submissions_problem", table_name="submissions")
    op.drop_index("idx_submissions_user", table_name="submissions")
    op.drop_index("idx_submissions_session", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("idx_sessions_user_subject", table_name="sessions")
    op.drop_index("idx_sessions_track", table_name="sessions")
    op.drop_index("idx_sessions_user", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("idx_tracks_labels", table_name="tracks")
    op.drop_index("ix_tracks_subject", table_name="tracks")
    op.drop_index("ix_tracks_slug", table_name="tracks")
    op.drop_table("tracks")
