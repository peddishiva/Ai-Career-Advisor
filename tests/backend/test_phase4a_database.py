"""Phase 4A profile schema, repository, and Alembic migration tests."""

from pathlib import Path
import os
import sys
import tempfile
import unittest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from db.repositories import ProfileRepository  # noqa: E402


class TestPhase4ADatabase(unittest.TestCase):
    def test_migration_upgrade_downgrade_and_reupgrade(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migration.db"
            url = f"sqlite:///{db_path}"
            config = Config(str(Path(__file__).resolve().parent.parent.parent / "alembic.ini"))
            previous_url = os.environ.get("DATABASE_URL")
            os.environ["DATABASE_URL"] = url
            try:
                command.upgrade(config, "head")
                engine = create_engine(url)
                self.assertIn("profiles", inspect(engine).get_table_names())
                command.downgrade(config, "base")
                self.assertNotIn("profiles", inspect(engine).get_table_names())
                command.upgrade(config, "head")
                self.assertIn("profiles", inspect(engine).get_table_names())
                engine.dispose()
            finally:
                if previous_url is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = previous_url

    def test_profile_repository_create_read_update(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = create_engine(f"sqlite:///{Path(temp_dir) / 'profiles.db'}")
            from db.base import Base
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, expire_on_commit=False)
            repository = ProfileRepository()
            with Session() as session:
                profile = repository.get_or_create(session, "user-one")
                session.commit()
                self.assertEqual("user-one", profile.user_id)
                self.assertIsNotNone(repository.get(session, "user-one"))
                updated = repository.update_display_name(session, "user-one", "Updated")
                session.commit()
                self.assertEqual("Updated", updated.display_name)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
