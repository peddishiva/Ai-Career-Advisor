"""Create resumes and resume_analyses tables with ownership and RLS."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_create_resumes_and_analyses"
down_revision: Union[str, Sequence[str], None] = "0003_auth_grants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RESUMES_FK_NAME = "fk_resumes_user_id_auth_users"
_ANALYSES_FK_NAME = "fk_resume_analyses_user_id_auth_users"

_RESUMES_POLICY_NAMES = (
    "resumes_select_own",
    "resumes_insert_own",
    "resumes_update_own",
    "resumes_delete_own",
)

_ANALYSES_POLICY_NAMES = (
    "resume_analyses_select_own",
    "resume_analyses_insert_own",
    "resume_analyses_update_own",
    "resume_analyses_delete_own",
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # 1. Create resumes table
    op.create_table(
        "resumes",
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
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1" if not _is_postgresql() else "true"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("id", "user_id", name="uq_resumes_id_user_id"),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_index("ix_resumes_content_hash", "resumes", ["content_hash"])
    op.create_index(
        "uq_resumes_user_active",
        "resumes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
        sqlite_where=sa.text("is_active = 1"),
    )

    # 2. Create resume_analyses table
    op.create_table(
        "resume_analyses",
        sa.Column(
            "id",
            sa.String(length=36).with_variant(postgresql.UUID(as_uuid=False), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.String(length=36).with_variant(postgresql.UUID(as_uuid=False), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255).with_variant(postgresql.UUID(as_uuid=False), "postgresql"),
            nullable=False,
        ),
        sa.Column("fit_score", sa.Integer(), nullable=True),
        sa.Column("target_role", sa.String(length=200), nullable=True),
        sa.Column(
            "analysis_data",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["resume_id", "user_id"],
            ["resumes.id", "resumes.user_id"],
            ondelete="CASCADE",
            name="fk_resume_analyses_resume_user",
        ),
        sa.UniqueConstraint("resume_id", name="uq_resume_analyses_resume_id"),
    )
    op.create_index("ix_resume_analyses_user_id", "resume_analyses", ["user_id"])

    # 3. PostgreSQL specific foreign keys to auth.users, RLS, and grants
    if not _is_postgresql():
        return

    op.create_foreign_key(
        _RESUMES_FK_NAME,
        "resumes",
        "users",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="auth",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        _ANALYSES_FK_NAME,
        "resume_analyses",
        "users",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="auth",
        ondelete="CASCADE",
    )

    op.execute("ALTER TABLE public.resumes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.resume_analyses ENABLE ROW LEVEL SECURITY")

    # Policies for resumes
    op.execute(
        """
        CREATE POLICY resumes_select_own
        ON public.resumes
        FOR SELECT TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY resumes_insert_own
        ON public.resumes
        FOR INSERT TO authenticated
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY resumes_update_own
        ON public.resumes
        FOR UPDATE TO authenticated
        USING ((select auth.uid()) = user_id)
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY resumes_delete_own
        ON public.resumes
        FOR DELETE TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )

    # Policies for resume_analyses
    op.execute(
        """
        CREATE POLICY resume_analyses_select_own
        ON public.resume_analyses
        FOR SELECT TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY resume_analyses_insert_own
        ON public.resume_analyses
        FOR INSERT TO authenticated
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY resume_analyses_update_own
        ON public.resume_analyses
        FOR UPDATE TO authenticated
        USING ((select auth.uid()) = user_id)
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY resume_analyses_delete_own
        ON public.resume_analyses
        FOR DELETE TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.resumes TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.resume_analyses TO authenticated")


def downgrade() -> None:
    if _is_postgresql():
        op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE public.resume_analyses FROM authenticated")
        op.execute("REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE public.resumes FROM authenticated")
        for policy_name in _ANALYSES_POLICY_NAMES:
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.resume_analyses")
        for policy_name in _RESUMES_POLICY_NAMES:
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.resumes")
        op.drop_constraint(_ANALYSES_FK_NAME, "resume_analyses", schema="public", type_="foreignkey")
        op.drop_constraint(_RESUMES_FK_NAME, "resumes", schema="public", type_="foreignkey")

    op.drop_index("ix_resume_analyses_user_id", table_name="resume_analyses")
    op.drop_table("resume_analyses")
    op.drop_index("uq_resumes_user_active", table_name="resumes")
    op.drop_index("ix_resumes_content_hash", table_name="resumes")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")
