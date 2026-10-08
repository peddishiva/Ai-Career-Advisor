"""Link profiles to Supabase Auth and enforce database ownership."""

from typing import Sequence, Union

from alembic import op


revision: str = "0002_profile_auth_ownership"
down_revision: Union[str, Sequence[str], None] = "0001_create_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FOREIGN_KEY_NAME = "fk_profiles_user_id_auth_users"
_POLICY_NAMES = (
    "profiles_select_own",
    "profiles_insert_own",
    "profiles_update_own",
    "profiles_delete_own",
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # Local SQLite remains a development fallback; Supabase ownership controls
    # are applied only where the managed auth schema exists.
    if not _is_postgresql():
        return

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM public.profiles
                WHERE user_id IS NULL
                   OR user_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            ) THEN
                RAISE EXCEPTION 'profiles.user_id contains null or invalid UUID values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.profiles AS p
                LEFT JOIN auth.users AS u ON p.user_id::uuid = u.id
                WHERE u.id IS NULL
            ) THEN
                RAISE EXCEPTION 'profiles contains user IDs without matching auth.users rows';
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE public.profiles
        ALTER COLUMN user_id TYPE uuid USING user_id::uuid
        """
    )
    op.create_foreign_key(
        _FOREIGN_KEY_NAME,
        "profiles",
        "users",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="auth",
        ondelete="CASCADE",
    )
    op.execute("ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY profiles_select_own
        ON public.profiles
        FOR SELECT TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY profiles_insert_own
        ON public.profiles
        FOR INSERT TO authenticated
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY profiles_update_own
        ON public.profiles
        FOR UPDATE TO authenticated
        USING ((select auth.uid()) = user_id)
        WITH CHECK ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY profiles_delete_own
        ON public.profiles
        FOR DELETE TO authenticated
        USING ((select auth.uid()) = user_id)
        """
    )


def downgrade() -> None:
    if not _is_postgresql():
        return

    for policy_name in _POLICY_NAMES:
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.profiles")
    # Keep RLS enabled. It may have been enabled before this migration, and
    # disabling it during rollback would weaken an existing security boundary.
    op.drop_constraint(_FOREIGN_KEY_NAME, "profiles", schema="public", type_="foreignkey")
    op.execute(
        """
        ALTER TABLE public.profiles
        ALTER COLUMN user_id TYPE varchar(255) USING user_id::text
        """
    )
