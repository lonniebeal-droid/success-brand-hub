from .database import get_database


def get_session():
    database = get_database()
    with database.session() as session:
        yield session
