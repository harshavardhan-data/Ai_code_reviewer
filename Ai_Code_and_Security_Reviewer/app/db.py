from sqlalchemy.orm import DeclarativeBase,sessionmaker
from sqlalchemy import create_engine
from pathlib import Path

class Base(DeclarativeBase):
    pass

# Anchor to the directory where db.py lives (app/)
BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL=f"sqlite:///{BASE_DIR / 'data' / 'reviews.db'}"

engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False})

SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False,)

