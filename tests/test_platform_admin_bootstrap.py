from sqlalchemy import select

from core.auth import create_user, verify_password
from core.database.database import Database
from core.database.models import User
from core.platform_api import create_app


def _make_db(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'platform.db'}")
    database.migrate()
    return database


def _user_count(database):
    with database.session() as session:
        return len(session.scalars(select(User)).all())


def test_first_empty_startup_creates_one_admin(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", "correct-horse-battery-staple")

    create_app(db)

    assert _user_count(db) == 1
    with db.session() as session:
        user = session.scalar(select(User))
        assert user.username == "bootstrap-admin"
        assert user.role == "admin"


def test_second_startup_creates_no_duplicate(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", "correct-horse-battery-staple")

    create_app(db)
    create_app(db)

    assert _user_count(db) == 1


def test_existing_users_are_untouched(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    with db.session() as session:
        create_user(session, "existing-viewer", "already-here-password", "viewer")
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", "correct-horse-battery-staple")

    create_app(db)

    assert _user_count(db) == 1
    with db.session() as session:
        user = session.scalar(select(User))
        assert user.username == "existing-viewer"
        assert user.role == "viewer"


def test_missing_variables_create_no_user(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    monkeypatch.delenv("PLATFORM_BOOTSTRAP_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    create_app(db)

    assert _user_count(db) == 0


def test_password_is_hashed(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", "correct-horse-battery-staple")

    create_app(db)

    with db.session() as session:
        user = session.scalar(select(User))
        assert user.password_hash != "correct-horse-battery-staple"
        assert user.password_hash.startswith("pbkdf2_sha256$")
        assert verify_password("correct-horse-battery-staple", user.password_hash)


def test_no_secret_appears_in_logs(tmp_path, monkeypatch, caplog):
    db = _make_db(tmp_path)
    monkeypatch.setenv("PLATFORM_JWT_SECRET", "test-only-secret-that-is-long-enough-12345")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", "correct-horse-battery-staple")

    with caplog.at_level("DEBUG"):
        create_app(db)

    assert "correct-horse-battery-staple" not in caplog.text
    assert "bootstrap-admin" not in caplog.text
