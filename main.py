import gzip
import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session, defer

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


def huella(imagen: Optional[str]) -> str:
    return hashlib.md5(imagen.encode()).hexdigest()[:8] if imagen else ""


def migrar() -> None:
    """Agrega columnas nuevas a tablas que ya existen (create_all solo crea tablas nuevas). No borra nada."""
    insp = inspect(engine)
    pendientes = [("ejercicios", "img_v", "VARCHAR(8) DEFAULT ''"), ("sesiones", "cliente", "VARCHAR(40)")]
    with engine.begin() as con:
        for tabla, col, tipo in pendientes:
            if tabla in insp.get_table_names() and col not in {c["name"] for c in insp.get_columns(tabla)}:
                con.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}"))
    with SessionLocal() as db:                       # fotos que ya subiste antes de existir la huella
        for e in db.query(models.Ejercicio).filter(models.Ejercicio.imagen.isnot(None)).all():
            if not e.img_v:
                e.img_v = huella(e.imagen)
        db.commit()


def sembrar(db: Session) -> None:
    """Crea tus ejercicios y marcas iniciales. Solo corre cuando ejercicios_base.py sube de versión; nunca pisa tus cambios."""
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
                              principal=principal, referencia=ref, nota=nota, img_v="")
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
    migrar()
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


# ---------- Análisis en memoria (una sola pasada; se recalcula solo cuando algo cambia) ----------
_cache: dict = {"a": None, "inicio": None}


def invalidar() -> None:
    _cache["a"] = None
    _cache["inicio"] = None


def _serie(x: models.Serie) -> dict:
    return {"ejercicio_id": x.ejercicio_id, "peso": x.peso, "unidad": x.unidad, "reps": x.reps, "rir": x.rir, "nota": x.nota,
            "peso_kg": progreso.a_kg(x.peso, x.unidad)}


def _analisis(db: Session) -> dict:
    if _cache["a"] is not None:
        return _cache["a"]
    ejs = {e.id: {"id": e.id, "nombre": e.nombre, "musculo": e.musculo, "dia": e.dia, "orden": e.orden, "unidad": e.unidad,
                  "principal": e.principal, "nota": e.nota, "referencia": e.referencia, "img_v": e.img_v or "", "activo": e.activo}
           for e in db.query(models.Ejercicio).options(defer(models.Ejercicio.imagen)).all()}
    sesiones = db.query(models.Sesion).order_by(models.Sesion.fecha, models.Sesion.id).all()
    previa: Dict[int, tuple] = {}
    hist: Dict[int, List[dict]] = {}
    det: Dict[int, dict] = {}
    lista: List[dict] = []
    for s in sesiones:
        mapa: Dict[int, List[dict]] = {}
        for x in s.series:
            mapa.setdefault(x.ejercicio_id, []).append(_serie(x))
        prev = previa.get(s.dia)
        items = []
        for eid, series in mapa.items():
            p = prev[1].get(eid) if prev else None
            c = progreso.comparar_series(series, p)
            items.append({"ejercicio_id": eid, "nombre": ejs[eid]["nombre"] if eid in ejs else "(eliminado)", "unidad": series[0]["unidad"],
                          "veredicto": c["veredicto"], "marcas": c["series"], "pct_volumen": c["pct"], "series": series, "series_previas": p or []})
            hist.setdefault(eid, []).append({"id": s.id, "fecha": s.fecha, "dia": s.dia, "series": series, "crudas": series, "veredicto": c["veredicto"]})
        res = progreso.resumen(items)
        det[s.id] = {"id": s.id, "fecha": s.fecha, "dia": s.dia, "previa_fecha": prev[0] if prev else None, "resumen": res, "ejercicios": items}
        todas = [x for v in mapa.values() for x in v]
        lista.append({"id": s.id, "fecha": s.fecha, "dia": s.dia, "nota": s.nota, "num_ejercicios": len(mapa), "resumen": res,
                      "rir0": sum(1 for x in todas if x["rir"] == 0), "rirdef": sum(1 for x in todas if x["rir"] is not None),
                      "series_por_ejercicio": mapa})
        previa[s.dia] = (s.fecha, mapa)
    a = {"ej": ejs, "det": det, "hist": hist, "lista": lista}
    a["alertas"] = _alertas(a)
    _cache["a"] = a
    return a


def _activos(a: dict) -> List[dict]:
    return sorted((e for e in a["ej"].values() if e["activo"]), key=lambda e: (e["dia"], e["orden"], e["id"]))


def _alertas(a: dict) -> List[dict]:
    res = []
    for e in _activos(a):
        if e["principal"]:
            motivo = progreso.alerta_fatiga(a["hist"].get(e["id"], []))
            if motivo:
                res.append({"ejercicio_id": e["id"], "nombre": e["nombre"], "motivo": motivo})
    return res


def _progreso(a: dict) -> dict:
    ejercicios = []
    for e in _activos(a):
        h = a["hist"].get(e["id"], [])
        puntos = []
        for x in h[-16:]:
            ks = [progreso.e1rm(s["peso_kg"], s["reps"]) for s in x["series"]]
            conv = lambda kg: progreso.a_unidad(kg, e["unidad"])
            puntos.append({"fecha": x["fecha"], "e1rm": round(conv(max(ks)), 1), "peso_max": round(conv(max(s["peso_kg"] for s in x["series"])), 1),
                           "volumen": round(conv(sum(s["peso_kg"] * s["reps"] for s in x["series"]))), "veredicto": x["veredicto"],
                           "series": [{"peso": s["peso"], "reps": s["reps"], "rir": s["rir"]} for s in x["series"]]})
        cambio = round((puntos[-1]["e1rm"] - puntos[0]["e1rm"]) / puntos[0]["e1rm"] * 100, 1) if len(puntos) >= 2 and puntos[0]["e1rm"] > 0 else None
        ejercicios.append({"id": e["id"], "nombre": e["nombre"], "musculo": e["musculo"], "dia": e["dia"], "unidad": e["unidad"],
                           "principal": e["principal"], "puntos": puntos, "cambio_pct": cambio,
                           "recomendacion": progreso.recomendar(h, e["unidad"], e["principal"], e["nombre"])})
    ses = [{"fecha": s["fecha"], "dia": s["dia"], "resumen": s["resumen"], "rir0": s["rir0"], "rirdef": s["rirdef"]} for s in a["lista"][-9:]]
    return {"recuperacion": progreso.estado_recuperacion(ses, hoy(), NOMBRE_DIA, len(a["alertas"])), "ejercicios": ejercicios}


def _resumen_sesiones(a: dict, dia: Optional[int] = None, limite: int = 60) -> List[dict]:
    l = [s for s in reversed(a["lista"]) if not dia or s["dia"] == dia][:limite]
    return [{k: s[k] for k in ("id", "fecha", "dia", "nota", "num_ejercicios", "resumen")} for s in l]


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
    return _activos(_analisis(db))


@api.post("/ejercicios", response_model=schemas.EjercicioLeer, status_code=201)
def crear_ejercicio(datos: schemas.EjercicioCrear, db: Session = Depends(get_db)):
    nombre = datos.nombre.strip()
    _validar_imagen(datos.imagen)
    if _nombre_repetido(db, nombre):
        raise HTTPException(status_code=400, detail="Ya tienes un ejercicio con ese nombre")
    ultimo = db.query(func.max(models.Ejercicio.orden)).filter(models.Ejercicio.dia == datos.dia).scalar() or 0
    nuevo = models.Ejercicio(**{**datos.model_dump(), "nombre": nombre}, orden=ultimo + 1, img_v=huella(datos.imagen))
    db.add(nuevo)
    db.commit()
    invalidar()
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
        ej.img_v = huella(cambios["imagen"])
    for campo, valor in cambios.items():
        if valor is not None or campo == "imagen":
            setattr(ej, campo, valor)
    db.commit()
    invalidar()
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
    invalidar()


@api.get("/imagenes")
def imagenes(v: str = "", db: Session = Depends(get_db)):
    """Solo devuelve las fotos que el celular no tiene o que cambiaron. v = '3:ab12cd34,4:' (id:huella que ya tiene)."""
    conocidas = {int(i): h for i, _, h in (p.partition(":") for p in v.split(",") if ":" in p) if i.isdigit()}
    return [{"id": e.id, "v": e.img_v or "", "imagen": e.imagen}
            for e in db.query(models.Ejercicio).filter(models.Ejercicio.activo.is_(True)).all()
            if (e.img_v or "") != conocidas.get(e.id, "")]


# ---------- Inicio y sesiones ----------
@api.get("/inicio")
def inicio(request: Request, db: Session = Depends(get_db)):
    """Todo lo que la app necesita para arrancar, en una sola petición.
    La respuesta ya armada se guarda en memoria (hasta que algo cambie o pase la medianoche) y lleva ETag:
    si el celular ya tiene la última versión, el servidor solo contesta '304 sin cambios' y no manda nada."""
    clave = hoy()
    c = _cache["inicio"]
    if c is None or c[0] != clave:
        a = _analisis(db)
        ultimas = {str(d): {"fecha": None, "ejercicios": {}} for d in (1, 2, 3)}
        for s in a["lista"]:
            ultimas[str(s["dia"])] = {"fecha": s["fecha"].isoformat(), "ejercicios": {str(k): v for k, v in s["series_por_ejercicio"].items()}}
        cuerpo = schemas.Inicio(ejercicios=_activos(a), ultimas=ultimas, alertas=a["alertas"], progreso=_progreso(a),
                                sesiones=_resumen_sesiones(a)).model_dump_json().encode()
        c = _cache["inicio"] = (clave, cuerpo, '"' + hashlib.md5(cuerpo).hexdigest() + '"', gzip.compress(cuerpo, 6, mtime=0))
    cab = {"ETag": c[2], "Cache-Control": "no-cache", "Vary": "Accept-Encoding"}
    if request.headers.get("if-none-match") == c[2]:
        return Response(status_code=304, headers=cab)
    if "gzip" in request.headers.get("accept-encoding", ""):             # ya viene comprimida: no se comprime en cada petición
        return Response(content=c[3], media_type="application/json", headers={**cab, "Content-Encoding": "gzip"})
    return Response(content=c[1], media_type="application/json", headers=cab)


@api.post("/sesiones", response_model=schemas.SesionDetalle, status_code=201)
def terminar_entrenamiento(datos: schemas.SesionCrear, db: Session = Depends(get_db)):
    if datos.cliente:                                              # si el celular reenvía lo mismo, no se duplica
        previa = db.query(models.Sesion).filter(models.Sesion.cliente == datos.cliente).first()
        if previa:
            a = _analisis(db)
            return {**a["det"][previa.id], "alertas": [f"{x['nombre']}: {x['motivo']}" for x in a["alertas"]]}
    ids = {s.ejercicio_id for s in datos.series}
    unidades = {e.id: e.unidad for e in db.query(models.Ejercicio).filter(models.Ejercicio.id.in_(ids)).all()}
    if ids - set(unidades):
        raise HTTPException(status_code=400, detail="Hay un ejercicio que ya no existe")
    sesion = models.Sesion(fecha=datos.fecha or hoy(), dia=datos.dia, cliente=datos.cliente)
    for s in datos.series:
        sesion.series.append(models.Serie(ejercicio_id=s.ejercicio_id, peso=s.peso, unidad=unidades[s.ejercicio_id],
                                          reps=s.reps, rir=s.rir, nota=s.nota.strip()))
    db.add(sesion)
    db.commit()
    invalidar()
    a = _analisis(db)
    return {**a["det"][sesion.id], "alertas": [f"{x['nombre']}: {x['motivo']}" for x in a["alertas"]]}


@api.get("/sesiones", response_model=List[schemas.SesionResumen])
def listar_sesiones(dia: Optional[int] = None, limite: int = 60, db: Session = Depends(get_db)):
    return _resumen_sesiones(_analisis(db), dia, max(1, min(limite, 200)))


@api.get("/sesiones/{sesion_id}", response_model=schemas.SesionDetalle)
def detalle_sesion(sesion_id: int, db: Session = Depends(get_db)):
    d = _analisis(db)["det"].get(sesion_id)
    if d is None:
        raise HTTPException(status_code=404, detail="El entrenamiento no existe")
    return d


@api.delete("/sesiones/{sesion_id}", status_code=204)
def eliminar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    s = db.get(models.Sesion, sesion_id)
    if s is None:
        raise HTTPException(status_code=404, detail="El entrenamiento no existe")
    db.delete(s)
    db.commit()
    invalidar()


@api.get("/exportar")
def exportar(db: Session = Depends(get_db)):
    """Copia de seguridad en JSON (ejercicios + todos tus entrenamientos)."""
    a = _analisis(db)
    return {"ejercicios": list(a["ej"].values()),
            "sesiones": [{"fecha": s["fecha"].isoformat(), "dia": s["dia"], "nota": s["nota"],
                          "series": [x for v in s["series_por_ejercicio"].values() for x in v]} for s in a["lista"]]}


app.include_router(publico)
app.include_router(api)

if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
