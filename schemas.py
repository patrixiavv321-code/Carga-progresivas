from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Unidad = Literal["kg", "lbs"]
Veredicto = Literal["+", "=", "-", "nuevo"]


class EjercicioCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    musculo: str = Field(min_length=2, max_length=40)
    dia: int = Field(ge=1, le=3)
    unidad: Unidad = "kg"
    nota: str = Field(default="", max_length=200)
    imagen: Optional[str] = Field(default=None, max_length=400_000)
    marca: str = Field(default="", max_length=300)
    n_series: int = Field(default=0, ge=0, le=12)


class EjercicioEditar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=120)
    musculo: Optional[str] = Field(default=None, min_length=2, max_length=40)
    dia: Optional[int] = Field(default=None, ge=1, le=3)
    unidad: Optional[Unidad] = None
    nota: Optional[str] = Field(default=None, max_length=200)
    imagen: Optional[str] = Field(default=None, max_length=400_000)   # "" = quitar la foto
    principal: Optional[bool] = None
    referencia: Optional[str] = Field(default=None, max_length=300)   # "Previo"
    marca: Optional[str] = Field(default=None, max_length=300)        # "Marca a batir"; "" = automática
    n_series: Optional[int] = Field(default=None, ge=0, le=12)        # 0 = automático


class EjercicioLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    musculo: str
    dia: int
    orden: int
    unidad: str
    principal: bool
    nota: str
    referencia: str
    marca: str = ""
    n_series: int = 0
    img_v: str = ""                    # la foto se pide aparte (ver /api/imagenes)


class SerieEntrada(BaseModel):
    ejercicio_id: int
    peso: float = Field(ge=0, le=1500)
    reps: int = Field(ge=0, le=200)
    rir: Optional[int] = Field(default=None, ge=0, le=10)
    rpe: Optional[float] = Field(default=None, ge=1, le=10)         # acepta medios puntos (8.5)
    unidad: Optional[Unidad] = None                                # unidad en la que se escribió el peso (si no, la del ejercicio)
    nota: str = Field(default="", max_length=200)


class SesionCrear(BaseModel):
    dia: int = Field(ge=1, le=3)
    fecha: Optional[date] = None
    descarga: bool = False                                         # semana de descarga: no cuenta para alertas ni marcas
    cliente: Optional[str] = Field(default=None, max_length=40)
    series: List[SerieEntrada] = Field(min_length=1, max_length=300)


class SerieLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ejercicio_id: int
    peso: float
    unidad: str
    reps: int
    rir: Optional[int]
    rpe: Optional[float] = None
    nota: str


class ComparacionEjercicio(BaseModel):
    ejercicio_id: int
    nombre: str
    unidad: str
    veredicto: Veredicto
    marcas: List[str]                 # un "+", "=" o "-" por serie
    pct_volumen: Optional[float]
    series: List[SerieLeer]
    series_previas: List[SerieLeer]


class Resumen(BaseModel):
    mejoraron: int
    iguales: int
    empeoraron: int
    nuevos: int


class SesionDetalle(BaseModel):
    id: int
    fecha: date
    dia: int
    previa_fecha: Optional[date]
    resumen: Resumen
    ejercicios: List[ComparacionEjercicio]
    alertas: List[str] = []
    descarga: bool = False


class SesionResumen(BaseModel):
    id: int
    fecha: date
    dia: int
    nota: str
    num_ejercicios: int
    resumen: Resumen


class PuntoHistorial(BaseModel):
    fecha: date
    mejor_kg: float
    volumen_kg: float
    veredicto: Veredicto
    series: List[SerieLeer]


class Alerta(BaseModel):
    ejercicio_id: int
    nombre: str
    motivo: str


class Inicio(BaseModel):
    ejercicios: List[EjercicioLeer]
    ultimas: dict                      # sesión anterior de cada día
    alertas: List[Alerta]
    progreso: dict                     # recuperación + recomendaciones + puntos para las gráficas
    sesiones: List[SesionResumen]
    prs: dict = {}                     # récord histórico por ejercicio (peso máximo y mejor 1RM estimado)
    descarga: dict = {}                # detector de descarga / estancamiento
    ajustes: dict = {}


class UnidadGlobal(BaseModel):
    unidad: Unidad
