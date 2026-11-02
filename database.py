import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:                                   # en tu computador lee el archivo .env si existe
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./gimnasio.db"   # sin DATABASE_URL usa un archivo local

# Supabase entrega "postgresql://" (o "postgres://"). Forzamos el controlador psycopg2.
for prefijo in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(prefijo):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(prefijo):]
        break

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    """Abre una sesión por cada petición y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
