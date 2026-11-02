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


# ---------- Recomendaciones de carga (progresión doble + regla del 2 por 2) ----------
def a_unidad(kg: float, unidad: str) -> float:
    return kg / LBS_A_KG if unidad == "lbs" else kg


def paso_carga(unidad: str, nombre: str) -> float:
    if unidad == "lbs":
        return 5.0
    return 2.0 if "mancuerna" in nombre.lower() else 2.5


def incremento(peso: float, unidad: str, nombre: str) -> float:
    """Un salto de ~5% redondeado al disco/placa más cercano (mínimo un paso)."""
    paso = paso_carga(unidad, nombre)
    return max(paso, round(peso * 0.05 / paso) * paso)


def recomendar(hist: List[dict], unidad: str, principal: bool, nombre: str) -> dict:
    """hist: sesiones del ejercicio (antigua → reciente), cada una con 'series' (peso_kg, reps, rir) y 'veredicto'."""
    if not hist:
        return {"tipo": "nuevo", "titulo": "Sin datos", "texto": "Registra este ejercicio para recibir recomendaciones.", "sugerido": None}
    ult = hist[-1]["series"]
    reps = [s["reps"] for s in ult]
    if max(reps) == 0:
        return {"tipo": "mantener", "titulo": "Falta registrar repeticiones",
                "texto": "Anota cuántas repeticiones lograste para poder medir tu progreso.", "sugerido": None}
    tope, base = (10, 6) if principal else (12, 8)
    peso = round(a_unidad(max(s["peso_kg"] for s in ult), unidad), 1)
    inc = incremento(peso, unidad, nombre)
    sug = round(peso + inc, 1)
    paso = paso_carga(unidad, nombre)
    rirs = [s["rir"] for s in ult if s.get("rir") is not None]
    holgado = bool(rirs) and min(rirs) >= 2
    min_reps = min(reps)
    e = [max(e1rm(s["peso_kg"], s["reps"]) for s in h["series"]) for h in hist]
    estancado = len(hist) >= 3 and e[-1] <= e[-3] * 1.005 and e[-2] <= e[-3] * 1.005
    if hist[-1]["veredicto"] == "-":
        if len(hist) >= 2 and hist[-2]["veredicto"] == "-":
            return {"tipo": "bajar", "titulo": "Baja un poco la carga",
                    "texto": f"Llevas 2 sesiones seguidas a la baja. Usa ~{fmt_n(peso - inc)} {unidad} y vuelve a subir cuando recuperes las repeticiones; revisa también sueño y comida.",
                    "sugerido": round(max(peso - inc, 0), 1)}
        return {"tipo": "mantener", "titulo": "Repite el peso",
                "texto": f"Rendiste menos que la vez anterior. Mantén {fmt_n(peso)} {unidad} e intenta recuperar tus repeticiones antes de subir.", "sugerido": peso}
    if min_reps >= tope:
        return {"tipo": "subir", "titulo": f"Sube a {fmt_n(sug)} {unidad}",
                "texto": f"Llegaste a {min_reps} repeticiones en todas las series (tu tope es {tope}). Es la señal para subir ~5%. Al principio es normal bajar a unas {base + 2} repeticiones.", "sugerido": sug}
    if min_reps >= tope - 1 and holgado:
        return {"tipo": "subir", "titulo": f"Sube a {fmt_n(sug)} {unidad}",
                "texto": f"Estás a una repetición del tope y terminaste con 2 o más repeticiones de reserva (RIR): tienes margen para subir.", "sugerido": sug}
    if holgado and min_reps > base:
        sug_p = round(peso + paso, 1)
        return {"tipo": "subir", "titulo": f"Prueba {fmt_n(sug_p)} {unidad}",
                "texto": "Terminaste con 2 o más repeticiones de reserva: un salto pequeño es seguro.", "sugerido": sug_p}
    if estancado:
        return {"tipo": "estancado", "titulo": "Estancado",
                "texto": "Tu fuerza estimada no sube hace 3 sesiones. Prueba con un día más de descanso, mejor técnica o pausa de 1 segundo; si sigue igual, una semana de descarga.", "sugerido": peso}
    if min_reps < base:
        return {"tipo": "mantener", "titulo": "Mantén y busca más repeticiones",
                "texto": f"Haces pocas repeticiones (menos de {base}). Mantén {fmt_n(peso)} {unidad} hasta llegar a {base}-{tope} repeticiones, y luego sube.", "sugerido": peso}
    return {"tipo": "mantener", "titulo": "Mantén y suma una repetición",
            "texto": f"Mantén {fmt_n(peso)} {unidad} y busca una repetición más por serie. Cuando llegues a {tope}, subes el peso.", "sugerido": peso}


def fmt_n(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.1f}"


# ---------- Recuperación: ¿entreno hoy o descanso más? ----------
def estado_recuperacion(ses: List[dict], hoy: date, nombres: Dict[int, str], alertas: int = 0) -> dict:
    """ses: sesiones de la más antigua a la más reciente: {'fecha','dia','resumen','rir0','rirdef'}.
    Tu ritmo normal: 3 días seguidos de entreno y 2 de descanso."""
    if not ses:
        return {"nivel": "bien", "titulo": "Empieza tu primer ciclo", "texto": "Cuando termines tu primer entrenamiento calcularé tu recuperación.",
                "descanso_dias": 2, "hoy": {"estado": "entrenar", "mensaje": "Hoy puedes entrenar."}, "indicadores": {}}
    ciclo, previo = ses[-3:], ses[-6:-3]

    def pct_peor(grupo):
        tot = sum(s["resumen"]["mejoraron"] + s["resumen"]["iguales"] + s["resumen"]["empeoraron"] for s in grupo)
        return (sum(s["resumen"]["empeoraron"] for s in grupo) / tot * 100) if tot else 0.0
    peor, peor_prev = pct_peor(ciclo), pct_peor(previo)
    rd = sum(s["rirdef"] for s in ciclo)
    rir0 = (sum(s["rir0"] for s in ciclo) / rd * 100) if rd else 0.0
    seguidos, fechas = 1, [s["fecha"] for s in ses]
    for i in range(len(fechas) - 1, 0, -1):
        if (fechas[i] - fechas[i - 1]).days == 1:
            seguidos += 1
        else:
            break
    score = peor + (15 if rir0 >= 60 else 0) + (15 if peor >= 35 and peor_prev >= 35 else 0) + (20 if alertas else 0)
    if score >= 50:
        nivel, desc = "alta", 5
        titulo = "Fatiga acumulada: toca descargar"
        texto = "Alerta de fatiga acumulada: se sugiere una semana de descarga (deload al 50% de volumen) o 3-5 días de descanso completo para recuperar el SNC y evitar estancamiento."
    elif score >= 25:
        nivel, desc = "atencion", 3
        titulo = "Descansa un día extra"
        texto = "Varias marcas bajaron en tu último ciclo. Con 2 días de descanso no te está alcanzando: descansa 3 días antes de volver a empezar."
    else:
        nivel, desc = "bien", 2
        titulo = "Recuperación bien"
        texto = "Tus cargas se mantienen o suben. Con 2 días de descanso después de tus 3 días de entreno vas bien."
    ult = ses[-1]
    gap = (hoy - ult["fecha"]).days
    sig = ult["dia"] % 3 + 1
    completo = ult["dia"] == 3 or seguidos >= 3
    hechos = max(gap - 1, 0)
    if gap <= 0:
        if completo:
            h = {"estado": "ya", "mensaje": f"Ya terminaste tu ciclo. Ahora descansa {desc} días."}
        else:
            h = {"estado": "ya", "mensaje": f"Ya entrenaste hoy. Mañana toca {nombres[sig]}."}
    elif completo:
        falta = desc - hechos
        if falta > 0:
            h = {"estado": "descansar", "mensaje": f"Hoy descansa: llevas {hechos} de {desc} días de descanso recomendados."}
        else:
            ok = " Con tus cargas estables, 2 días de descanso fueron suficientes." if nivel == "bien" and hechos == 2 else ""
            h = {"estado": "entrenar", "mensaje": f"Estás recuperado: hoy toca {nombres[sig]}.{ok}"}
    else:
        h = {"estado": "entrenar", "mensaje": f"Hoy toca {nombres[sig]}." if gap == 1 else f"Llevas {hechos} día(s) sin entrenar: hoy toca {nombres[sig]}."}
    if gap >= 8:
        h["mensaje"] += " Llevas más de una semana parado: retoma con ~10% menos de peso."
    return {"nivel": nivel, "titulo": titulo, "texto": texto, "descanso_dias": desc, "hoy": h,
            "indicadores": {"peor_pct": round(peor), "rir0_pct": round(rir0), "dias_seguidos": seguidos}}
