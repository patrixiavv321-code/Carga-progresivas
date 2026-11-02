"""Lógica pura de progreso (sin base de datos): compara sesiones y detecta fatiga."""
from datetime import date
from typing import Dict, List, Optional

LBS_A_KG = 0.45359237


def a_kg(peso: float, unidad: str) -> float:
    return peso * LBS_A_KG if unidad == "lbs" else peso


def e1rm(kg: float, reps: int) -> float:
    return kg * (1 + reps / 30)


def comparar_serie(act: dict, prev: Optional[dict]) -> str:
    """'+' mejora, '=' igual, '-' menor. Los dicts traen peso_kg y reps."""
    if prev is None:
        return "="
    pa, ra, pp, rp = round(act["peso_kg"], 1), act["reps"], round(prev["peso_kg"], 1), prev["reps"]
    if pa >= pp and ra >= rp:
        return "+" if (pa > pp or ra > rp) else "="
    if pa > pp:                                    # más peso pero menos reps: gana quien tenga mayor 1RM estimado
        return "+" if e1rm(pa, ra) > e1rm(pp, rp) else "-"
    return "-"


def comparar_series(act: List[dict], prev: Optional[List[dict]]) -> dict:
    """Compara las series de un ejercicio contra la sesión anterior del mismo día."""
    if not prev:
        return {"veredicto": "nuevo", "series": ["="] * len(act), "pct": None}
    por_serie = [comparar_serie(s, prev[min(i, len(prev) - 1)]) for i, s in enumerate(act)]
    if len(act) < len(prev):
        veredicto = "-"
    elif "-" in por_serie:
        veredicto = "-"
    elif "+" in por_serie:
        veredicto = "+"
    else:
        veredicto = "="
    vol = lambda ss: sum(s["peso_kg"] * s["reps"] for s in ss)
    vp = vol(prev)
    pct = round((vol(act) - vp) / vp * 100, 1) if vp > 0 else None
    return {"veredicto": veredicto, "series": por_serie, "pct": pct}


def resumen(items: List[dict]) -> dict:
    cuenta = {"+": 0, "=": 0, "-": 0, "nuevo": 0}
    for it in items:
        cuenta[it["veredicto"]] += 1
    return {"mejoraron": cuenta["+"], "iguales": cuenta["="], "empeoraron": cuenta["-"], "nuevos": cuenta["nuevo"]}


def alerta_fatiga(sesiones: List[dict]) -> Optional[str]:
    """sesiones: de la más antigua a la más reciente, cada una {'fecha': date, 'series': [...], 'veredicto': str}
    Devuelve el motivo si hay fatiga acumulada, o None."""
    if len(sesiones) >= 2 and sesiones[-1]["veredicto"] == "-" and sesiones[-2]["veredicto"] == "-":
        return "2 sesiones seguidas a la baja"
    racha: List[date] = []
    for s in reversed(sesiones):
        if any(x.get("rir") == 0 for x in s["series"]):
            racha.append(s["fecha"])
        else:
            break
    if len(racha) >= 4 and (racha[0] - racha[-1]).days > 28:
        return "más de 4 semanas seguidas llegando al fallo (RIR 0)"
    return None


def historial_con_veredictos(sesiones: List[dict]) -> List[dict]:
    """Agrega 'veredicto' a cada sesión comparándola con la anterior (misma lista, ya ordenada)."""
    prev = None
    for s in sesiones:
        s["veredicto"] = comparar_series(s["series"], prev)["veredicto"] if prev else "nuevo"
        prev = s["series"]
    return sesiones
