"""add study path tracking tables"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1e2fbf87c0b9"
down_revision = "d3fa9090ded3"
branch_labels = None
depends_on = None

# Enumerations

task_status_enum = sa.Enum(
    "scheduled",
    "in_progress",
    "completed",
    "skipped",
    "expired",
    name="task_status",
)

task_event_type_enum = sa.Enum(
    "created",
    "started",
    "submitted",
    "evaluated",
    "hint_requested",
    "tutor_interaction",
    "status_changed",
    name="task_event_type",
)


def upgrade() -> None:
    """Create study path tracking tables."""
    op.create_table(
        "study_paths",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "track_id",
            sa.String(length=100),
            nullable=False,
            server_default="coding-interview-meta",
        ),
        sa.Column(
            "config",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_study_paths_user",
        "study_paths",
        ["user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "study_tasks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "path_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("study_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("problem_id", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column(
            "topic_tags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            task_status_enum,
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "hints_used",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "metadata",
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
        sa.CheckConstraint(
            "difficulty >= 1 AND difficulty <= 5", name="check_difficulty"
        ),
    )
    op.create_index(
        "idx_study_tasks_path_schedule",
        "study_tasks",
        ["path_id", "scheduled_at"],
        unique=False,
    )
    op.create_index(
        "idx_study_tasks_path_module_status",
        "study_tasks",
        ["path_id", "module", "status"],
        unique=False,
    )
    op.create_index(
        "idx_study_tasks_problem",
        "study_tasks",
        ["problem_id"],
        unique=False,
    )

    op.create_table(
        "task_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("study_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", task_event_type_enum, nullable=False),
        sa.Column(
            "payload",
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
    op.create_index(
        "idx_task_events_task",
        "task_events",
        ["task_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "task_evaluations",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("study_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "submission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("submissions.id"),
            nullable=True,
        ),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column(
            "test_cases_passed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "test_cases_total",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("runtime_ms", sa.Integer(), nullable=True),
        sa.Column("memory_mb", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "idx_task_eval_task",
        "task_evaluations",
        ["task_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop study path tracking tables."""
    op.drop_index("idx_task_eval_task", table_name="task_evaluations")
    op.drop_table("task_evaluations")
    op.drop_index("idx_task_events_task", table_name="task_events")
    op.drop_table("task_events")
    op.drop_index("idx_study_tasks_problem", table_name="study_tasks")
    op.drop_index("idx_study_tasks_path_module_status", table_name="study_tasks")
    op.drop_index("idx_study_tasks_path_schedule", table_name="study_tasks")
    op.drop_table("study_tasks")
    op.drop_index("idx_study_paths_user", table_name="study_paths")
    op.drop_table("study_paths")
    task_event_type_enum.drop(op.get_bind(), checkfirst=True)
    task_status_enum.drop(op.get_bind(), checkfirst=True)
