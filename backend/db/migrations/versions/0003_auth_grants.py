"""Allow the authenticated role to use profiles under RLS policies."""

from typing import Sequence, Union

from alembic import op


revision: str = "0003_auth_grants"
down_revision: Union[str, Sequence[str], None] = "0002_profile_auth_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.profiles TO authenticated"
    )


def downgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE public.profiles FROM authenticated"
    )
