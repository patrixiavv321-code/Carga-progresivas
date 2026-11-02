import hmac
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, tuple_
from sqlalchemy.orm import Session

import models
import progreso
import schemas
from database import Base, SessionLocal, engine, get_db
from ejercicios_base import BASE, VERSION as VERSION_BASE

COLOMBIA = timezone(timedelta(hours=-5), "COL")
FRONTEND = Path(__file__).parent / "frontend"
NOMBRE_DIA = {1: "Torso", 2: "Brazo y hombro", 3: "Pierna"}


def clave_de_acceso() -> str:
    """Si defines la variable APP_CLAVE, la app pide esa clave. Sin ella, queda abierta."""
    return os.getenv("APP_CLAVE", "")


def hoy() -> date:
    return datetime.now(COLOMBIA).date()


def sembrar(db: Session) -> None:
    """Crea tus ejercicios y marcas iniciales. Solo corre cuando ejercicios_base.py sube de versión."""
    fila = db.get(models.Ajuste, "base_version")
    version = int(fila.valor) if fila and fila.valor.isdigit() else 0
    if version >= VERSION_BASE:
        return
    existentes = {n.lower() for (n,) in db.query(models.Ejercicio.nombre).all()}
    sesiones: Dict[int, models.Sesion] = {}
    orden_dia: Dict[int, int] = {}
    for dia, nombre, musculo, unidad, principal, series, ref, nota in BASE:
        orden_dia[dia] = orden_dia.get(dia, 0) + 1
        if nombre.lower() in existentes:
            continue
        ej = models.Ejercicio(nombre=nombre, musculo=musculo, dia=dia, orden=orden_dia[dia], unidad=unidad,
                              principal=principal, referencia=ref, nota=nota)
        db.add(ej)
        db.flush()
        if dia not in sesiones:
            sesiones[dia] = models.Sesion(fecha=hoy() - timedelta(days=7), dia=dia, nota="Marcas iniciales")
            db.add(sesiones[dia])
        for peso, reps, rir in series:
            sesiones[dia].series.append(models.Serie(ejercicio_id=ej.id, peso=peso, unidad=unidad, reps=reps, rir=rir))
    if fila is None:
        db.add(models.Ajuste(clave="base_version", valor=str(VERSION_BASE)))
    else:
        fila.valor = str(VERSION_BASE)
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        sembrar(db)
    yield


app = FastAPI(title="Gimnasio", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def verificar_clave(x_clave: Optional[str] = Header(default=None)) -> None:
    clave = clave_de_acceso()
    if clave and not hmac.compare_digest((x_clave or "").encode(), clave.encode()):
        raise HTTPException(status_code=401, detail="Clave incorrecta")


publico = APIRouter(prefix="/api")
api = APIRouter(prefix="/api", dependencies=[Depends(verificar_clave)])


@publico.get("/estado")
def estado():
    return {"requiere_clave": bool(clave_de_acceso())}


@api.get("/acceso")
def acceso():
    return {"ok": True}


# ---------- Ayudas de comparación ----------
def _serie_dict(s: models.Serie) -> dict:
    return {"peso_kg": progreso.a_kg(s.peso, s.unidad), "reps": s.reps, "rir": s.rir}


def _por_ejercicio(sesion: models.Sesion) -> Dict[int, List[models.Serie]]:
    res: Dict[int, List[models.Serie]] = {}
    for s in sesion.series:
        res.setdefault(s.ejercicio_id, []).append(s)
    return res


def _sesion_previa(db: Session, sesion: models.Sesion) -> Optional[models.Sesion]:
    return (db.query(models.Sesion).filter(models.Sesion.dia == sesion.dia,
            tuple_(models.Sesion.fecha, models.Sesion.id) < (sesion.fecha, sesion.id))
            .order_by(models.Sesion.fecha.desc(), models.Sesion.id.desc()).first())


def _historial(db: Session, ejercicio_id: int) -> List[dict]:
    """Sesiones donde se hizo el ejercicio, de la más antigua a la más reciente, con su veredicto."""
    filas = (db.query(models.Sesion, models.Serie).join(models.Serie, models.Serie.sesion_id == models.Sesion.id)
             .filter(models.Serie.ejercicio_id == ejercicio_id).order_by(models.Sesion.fecha, models.Sesion.id, models.Serie.id).all())
    out: List[dict] = []
    for ses, serie in filas:
        if not out or out[-1]["id"] != ses.id:
            out.append({"id": ses.id, "fecha": ses.fecha, "series": [], "crudas": []})
        out[-1]["series"].append(_serie_dict(serie))
        out[-1]["crudas"].append(serie)
    return progreso.historial_con_veredictos(out)


def _alertas(db: Session) -> List[dict]:
    res = []
    for ej in db.query(models.Ejercicio).filter(models.Ejercicio.principal.is_(True), models.Ejercicio.activo.is_(True)).all():
        motivo = progreso.alerta_fatiga(_historial(db, ej.id))
        if motivo:
            res.append({"ejercicio_id": ej.id, "nombre": ej.nombre, "motivo": motivo})
    return res


def _detalle(db: Session, sesion: models.Sesion) -> dict:
    previa = _sesion_previa(db, sesion)
    prev_map = _por_ejercicio(previa) if previa else {}
    nombres = {e.id: e for e in db.query(models.Ejercicio).filter(models.Ejercicio.id.in_([s.ejercicio_id for s in sesion.series])).all()}
    items = []
    for eid, series in _por_ejercicio(sesion).items():
        prev = prev_map.get(eid)
        cmp = progreso.comparar_series([_serie_dict(s) for s in series], [_serie_dict(s) for s in prev] if prev else None)
        items.append({"ejercicio_id": eid, "nombre": nombres[eid].nombre if eid in nombres else "(eliminado)",
                      "unidad": series[0].unidad, "veredicto": cmp["veredicto"], "marcas": cmp["series"],
                      "pct_volumen": cmp["pct"], "series": series, "series_previas": prev or []})
    return {"id": sesion.id, "fecha": sesion.fecha, "dia": sesion.dia, "previa_fecha": previa.fecha if previa else None,
            "resumen": progreso.resumen(items), "ejercicios": items}


# ---------- Ejercicios ----------
def _validar_imagen(img: Optional[str]) -> None:
    if img and not img.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="La imagen no es válida")


def _nombre_repetido(db: Session, nombre: str, ignorar: Optional[int] = None) -> bool:
    q = db.query(models.Ejercicio.id).filter(func.lower(models.Ejercicio.nombre) == nombre.lower(), models.Ejercicio.activo.is_(True))
    if ignorar is not None:
        q = q.filter(models.Ejercicio.id != ignorar)
    return q.first() is not None


@api.get("/ejercicios", response_model=List[schemas.EjercicioLeer])
def listar_ejercicios(db: Session = Depends(get_db)):
    return (db.query(models.Ejercicio).filter(models.Ejercicio.activo.is_(True))
            .order_by(models.Ejercicio.dia, models.Ejercicio.orden, models.Ejercicio.id).all())


@api.post("/ejercicios", response_model=schemas.EjercicioLeer, status_code=201)
def crear_ejercicio(datos: schemas.EjercicioCrear, db: Session = Depends(get_db)):
    nombre = datos.nombre.strip()
    _validar_imagen(datos.imagen)
    if _nombre_repetido(db, nombre):
        raise HTTPException(status_code=400, detail="Ya tienes un ejercicio con ese nombre")
    ultimo = db.query(func.max(models.Ejercicio.orden)).filter(models.Ejercicio.dia == datos.dia).scalar() or 0
    nuevo = models.Ejercicio(**{**datos.model_dump(), "nombre": nombre}, orden=ultimo + 1)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@api.patch("/ejercicios/{ejercicio_id}", response_model=schemas.EjercicioLeer)
def editar_ejercicio(ejercicio_id: int, datos: schemas.EjercicioEditar, db: Session = Depends(get_db)):
    ej = db.get(models.Ejercicio, ejercicio_id)
    if ej is None or not ej.activo:
        raise HTTPException(status_code=404, detail="El ejercicio no existe")
    cambios = datos.model_dump(exclude_unset=True)
    if cambios.get("nombre") is not None:
        cambios["nombre"] = cambios["nombre"].strip()
        if _nombre_repetido(db, cambios["nombre"], ignorar=ejercicio_id):
            raise HTTPException(status_code=400, detail="Ya tienes un ejercicio con ese nombre")
    if "imagen" in cambios:
        _validar_imagen(cambios["imagen"])
        cambios["imagen"] = cambios["imagen"] or None
    for campo, valor in cambios.items():
        if valor is not None or campo == "imagen":
            setattr(ej, campo, valor)
    db.commit()
    db.refresh(ej)
    return ej


@api.delete("/ejercicios/{ejercicio_id}", status_code=204)
def quitar_ejercicio(ejercicio_id: int, db: Session = Depends(get_db)):
    """No borra el historial: solo lo oculta de tu rutina."""
    ej = db.get(models.Ejercicio, ejercicio_id)
    if ej is None:
        raise HTTPException(status_code=404, detail="El ejercicio no existe")
    ej.activo = False
    db.commit()


@api.get("/ejercicios/{ejercicio_id}/historial", response_model=List[schemas.PuntoHistorial])
def historial_ejercicio(ejercicio_id: int, db: Session = Depends(get_db)):
    out = []
    for h in _historial(db, ejercicio_id):
        kg = [progreso.e1rm(s["peso_kg"], s["reps"]) for s in h["series"]]
        out.append({"fecha": h["fecha"], "mejor_kg": round(max(kg), 1), "veredicto": h["veredicto"],
                    "volumen_kg": round(sum(s["peso_kg"] * s["reps"] for s in h["series"]), 1), "series": h["crudas"]})
    return out


# ---------- Sesiones ----------
@api.get("/inicio", response_model=schemas.Inicio)
def inicio(db: Session = Depends(get_db)):
    """Todo lo que la pantalla necesita para arrancar: ejercicios, la última sesión de cada día y alertas."""
    ejercicios = listar_ejercicios(db)
    ultimas: dict = {}
    for dia in (1, 2, 3):
        s = db.query(models.Sesion).filter(models.Sesion.dia == dia).order_by(models.Sesion.fecha.desc(), models.Sesion.id.desc()).first()
        ultimas[str(dia)] = {
            "fecha": s.fecha.isoformat() if s else None,
            "ejercicios": {str(k): [schemas.SerieLeer.model_validate(x).model_dump() for x in v] for k, v in _por_ejercicio(s).items()} if s else {},
        }
    return {"ejercicios": ejercicios, "ultimas": ultimas, "alertas": _alertas(db)}


@api.post("/sesiones", response_model=schemas.SesionDetalle, status_code=201)
def terminar_entrenamiento(datos: schemas.SesionCrear, db: Session = Depends(get_db)):
    ids = {s.ejercicio_id for s in datos.series}
    unidades = {e.id: e.unidad for e in db.query(models.Ejercicio).filter(models.Ejercicio.id.in_(ids)).all()}
    if ids - set(unidades):
        raise HTTPException(status_code=400, detail="Hay un ejercicio que ya no existe")
    sesion = models.Sesion(fecha=datos.fecha or hoy(), dia=datos.dia)
    for s in datos.series:
        sesion.series.append(models.Serie(ejercicio_id=s.ejercicio_id, peso=s.peso, unidad=unidades[s.ejercicio_id],
                                          reps=s.reps, rir=s.rir, nota=s.nota.strip()))
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return {**_detalle(db, sesion), "alertas": [f"{a['nombre']}: {a['motivo']}" for a in _alertas(db)]}


@api.get("/sesiones", response_model=List[schemas.SesionResumen])
def listar_sesiones(dia: Optional[int] = None, limite: int = 60, db: Session = Depends(get_db)):
    q = db.query(models.Sesion)
    if dia:
        q = q.filter(models.Sesion.dia == dia)
    sesiones = q.order_by(models.Sesion.fecha.desc(), models.Sesion.id.desc()).limit(max(1, min(limite, 200))).all()
    return [{"id": s.id, "fecha": s.fecha, "dia": s.dia, "nota": s.nota, "num_ejercicios": len(_por_ejercicio(s)),
             "resumen": _detalle(db, s)["resumen"]} for s in sesiones]


@api.get("/sesiones/{sesion_id}", response_model=schemas.SesionDetalle)
def detalle_sesion(sesion_id: int, db: Session = Depends(get_db)):
    s = db.get(models.Sesion, sesion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="El entrenamiento no existe")
    return _detalle(db, s)


@api.delete("/sesiones/{sesion_id}", status_code=204)
def eliminar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    s = db.get(models.Sesion, sesion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="El entrenamiento no existe")
    db.delete(s)
    db.commit()


@api.get("/exportar")
def exportar(db: Session = Depends(get_db)):
    """Copia de seguridad en JSON (ejercicios + todos tus entrenamientos)."""
    return {
        "ejercicios": [schemas.EjercicioLeer.model_validate(e).model_dump() for e in db.query(models.Ejercicio).all()],
        "sesiones": [{"fecha": s.fecha.isoformat(), "dia": s.dia, "nota": s.nota,
                      "series": [schemas.SerieLeer.model_validate(x).model_dump() for x in s.series]}
                     for s in db.query(models.Sesion).order_by(models.Sesion.fecha, models.Sesion.id).all()],
    }


app.include_router(publico)
app.include_router(api)

if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
