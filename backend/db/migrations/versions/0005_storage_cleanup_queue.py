"""Create storage_cleanup_jobs table with ownership and RLS.

Revision ID: 0005_storage_cleanup_queue
Revises: 0004_create_resumes_and_analyses
Create Date: 2026-10-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_storage_cleanup_queue"
down_revision: Union[str, Sequence[str], None] = "0004_create_resumes_and_analyses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CLEANUP_FK_NAME = "fk_storage_cleanup_jobs_user_id_auth_users"

_CLEANUP_POLICY_NAMES = (
    "storage_cleanup_jobs_select_own",
    "storage_cleanup_jobs_insert_own",
    "storage_cleanup_jobs_update_own",
    "storage_cleanup_jobs_delete_own",
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "storage_cleanup_jobs",
        sa.Column(
            "id",
            sa.String(length=36).with_variant(postgresql.UUID(as_uuid=False), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255).with_variant(postgresql.UUID(as_uuid=False), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.String(length=36).with_variant(postgresql.UUID(as_uuid=False), "postgresql"),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("object_name", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storage_cleanup_jobs_user_id", "storage_cleanup_jobs", ["user_id"])
    op.create_index("ix_storage_cleanup_jobs_resume_id", "storage_cleanup_jobs", ["resume_id"])
    op.create_index("ix_storage_cleanup_jobs_status", "storage_cleanup_jobs", ["status"])

    if not _is_postgresql():
        return

    op.create_foreign_key(
        _CLEANUP_FK_NAME,
        "storage_cleanup_jobs",
        "users",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="auth",
        ondelete="CASCADE",
    )

    op.execute("ALTER TABLE public.storage_cleanup_jobs ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY storage_cleanup_jobs_select_own
        ON public.storage_cleanup_jobs
        FOR SELECT TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY storage_cleanup_jobs_insert_own
        ON public.storage_cleanup_jobs
        FOR INSERT TO authenticated
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY storage_cleanup_jobs_update_own
        ON public.storage_cleanup_jobs
        FOR UPDATE TO authenticated
        USING ((select auth.uid()) = user_id)
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY storage_cleanup_jobs_delete_own
        ON public.storage_cleanup_jobs
        FOR DELETE TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.storage_cleanup_jobs TO authenticated")


def downgrade() -> None:
    if _is_postgresql():
        op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE public.storage_cleanup_jobs FROM authenticated")
        for policy_name in _CLEANUP_POLICY_NAMES:
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.storage_cleanup_jobs")
        op.drop_constraint(_CLEANUP_FK_NAME, "storage_cleanup_jobs", schema="public", type_="foreignkey")

    op.drop_index("ix_storage_cleanup_jobs_status", table_name="storage_cleanup_jobs")
    op.drop_index("ix_storage_cleanup_jobs_resume_id", table_name="storage_cleanup_jobs")
    op.drop_index("ix_storage_cleanup_jobs_user_id", table_name="storage_cleanup_jobs")
    op.drop_table("storage_cleanup_jobs")
