from sqlalchemy.orm import DeclarativeBase,sessionmaker
from sqlalchemy import create_engine
from pathlib import Path
from contextlib import contextmanager
from collections.abc import Generator

class Base(DeclarativeBase):
    pass

# Anchor to the directory where db.py lives (app/)
BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL=f"sqlite:///{BASE_DIR / 'data' / 'reviews.db'}"

engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False})

SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False,)


@contextmanager
def get_db() -> Generator:
    db=SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
