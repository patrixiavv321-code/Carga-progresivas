from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Ejercicio(Base):
    __tablename__ = "ejercicios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False, unique=True)
    musculo = Column(String(40), nullable=False)
    dia = Column(Integer, nullable=False, index=True)          # 1 = Torso, 2 = Brazo y hombro, 3 = Pierna
    orden = Column(Integer, nullable=False, default=0)
    unidad = Column(String(3), nullable=False, default="kg")   # kg | lbs
    principal = Column(Boolean, nullable=False, default=False) # cuenta para la alerta de fatiga
    nota = Column(String(200), nullable=False, default="")
    referencia = Column(String(300), nullable=False, default="")  # historial previo escrito a mano
    imagen = Column(Text, nullable=True)                       # foto en base64 (la reduce el celular antes de subirla)
    img_v = Column(String(8), nullable=False, default="")      # huella de la foto: el celular solo la descarga si cambió
    activo = Column(Boolean, nullable=False, default=True)


class Sesion(Base):
    """Un entrenamiento completo (por ejemplo, el Torso del lunes)."""
    __tablename__ = "sesiones"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, index=True)
    dia = Column(Integer, nullable=False, index=True)
    nota = Column(String(200), nullable=False, default="")
    cliente = Column(String(40), nullable=True, index=True)    # id creado por el celular: evita duplicar si se reenvía
    creado = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    series = relationship("Serie", cascade="all, delete-orphan", order_by="Serie.id", lazy="selectin")


class Serie(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False, index=True)
    ejercicio_id = Column(Integer, ForeignKey("ejercicios.id", ondelete="CASCADE"), nullable=False, index=True)
    peso = Column(Float, nullable=False)
    unidad = Column(String(3), nullable=False, default="kg")   # unidad usada ese día (el historial no cambia si luego la cambias)
    reps = Column(Integer, nullable=False)
    rir = Column(Integer, nullable=True)
    nota = Column(String(200), nullable=False, default="")


class Ajuste(Base):
    __tablename__ = "ajustes"

    clave = Column(String(40), primary_key=True)
    valor = Column(String(100), nullable=False)
