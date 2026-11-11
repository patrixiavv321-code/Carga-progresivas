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
def estado_recuperacion(ses: List[dict], hoy: date, nombres: Dict[int, str], alertas: int = 0, activos: Optional[List[int]] = None) -> dict:
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
    activos = sorted(activos or [1, 2, 3])                       # solo cuentan las rutinas que no eliminaste
    sig = next((d for d in activos if d > ult["dia"]), activos[0])
    completo = sig <= ult["dia"] or seguidos >= len(activos) or len(activos) == 1
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


# ---------- Unidades: solo se convierte para MOSTRAR; lo guardado nunca se reescribe ----------
def convertir(peso: float, de: str, a: str) -> float:
    """Convierte sin pasos intermedios redondeados. Si la unidad es la misma devuelve el valor original, exacto."""
    if de == a:
        return peso
    return a_unidad(a_kg(peso, de), a)


# ---------- RIR ↔ RPE (RPE ≈ 10 − RIR) ----------
def rir_de_rpe(rpe: float) -> int:
    """Se redondea hacia abajo (hacia 'más esfuerzo'): RPE 9.5 → RIR 0. Es la lectura prudente para fatiga y subidas de carga."""
    return max(0, min(10, int(10 - rpe)))


def rpe_de_rir(rir: int) -> float:
    return float(10 - rir)


# ---------- Récord personal: peso máximo y mejor 1RM estimado de toda la historia ----------
def calcular_pr(hist: List[dict], max_reps_1rm: int = 12) -> Optional[dict]:
    """hist: sesiones del ejercicio, cada una {'fecha': date, 'series': [{'peso','unidad','reps','peso_kg'}]}.
    El 1RM estimado solo usa series de hasta 12 repeticiones (más allá la fórmula se vuelve poco fiable).
    Ante un empate gana el récord más antiguo (el que hay que superar)."""
    mejor_peso = mejor_1rm = None
    for h in hist:
        for s in h["series"]:
            if s["reps"] <= 0 or s["peso_kg"] <= 0:
                continue
            k = round(s["peso_kg"], 4)
            if mejor_peso is None or (k, s["reps"]) > (mejor_peso["_k"], mejor_peso["reps"]):
                mejor_peso = {"_k": k, "kg": s["peso_kg"], "reps": s["reps"], "peso": s["peso"], "unidad": s["unidad"], "fecha": h["fecha"].isoformat()}
            if s["reps"] <= max_reps_1rm:
                e = round(e1rm(s["peso_kg"], s["reps"]), 4)
                if mejor_1rm is None or e > mejor_1rm["_k"]:
                    mejor_1rm = {"_k": e, "kg": e1rm(s["peso_kg"], s["reps"]), "de_kg": s["peso_kg"], "reps": s["reps"], "peso": s["peso"], "unidad": s["unidad"], "fecha": h["fecha"].isoformat()}
    if mejor_peso is None:
        return None
    for d in (mejor_peso, mejor_1rm):
        if d:
            d.pop("_k")
    return {"max": mejor_peso, "e1rm": mejor_1rm}


# ---------- Descarga (deload): detector basado en señales ----------
def semanas_continuas(fechas: List[date], hoy: date, ultima_descarga: Optional[date] = None, hueco: int = 7) -> int:
    """Semanas entrenando sin pausa: se reinicia con un hueco de ≥7 días entre sesiones o al marcar una descarga."""
    fechas = sorted(set(fechas))
    if not fechas or (hoy - fechas[-1]).days >= hueco:
        return 0
    inicio = fechas[0]
    for a, b in zip(fechas, fechas[1:]):
        if (b - a).days >= hueco:
            inicio = b
    if ultima_descarga and ultima_descarga > inicio:
        inicio = ultima_descarga
    return max(0, (hoy - inicio).days // 7)


def evaluar_descarga(*, n_sesiones: int, regresion: List[str], estancados: List[str], rir0_pct: float,
                     semanas: int, dias_desde_descarga: Optional[int]) -> dict:
    """Suma puntos por señales independientes. Ninguna señal sola obliga a descargar:
    el rendimiento a la baja y el esfuerzo constante al límite pesan más que el calendario o un solo ejercicio estancado."""
    if dias_desde_descarga is not None and dias_desde_descarga < 7:
        return {"nivel": "en_curso", "puntos": 0, "senales": [], "semanas": semanas, "dias": dias_desde_descarga + 1}
    if n_sesiones < 4:
        return {"nivel": "sin_datos", "puntos": 0, "senales": [], "semanas": semanas, "dias": None}
    senales, pts = [], 0
    if regresion:
        p = 3 if len(regresion) >= 2 else 2
        pts += p
        senales.append({"tipo": "rendimiento", "peso": p, "texto": f"Rendimiento a la baja 2 sesiones seguidas en: {', '.join(regresion[:3])}."})
    if estancados:
        p = 2 if len(estancados) >= 2 else 1
        pts += p
        senales.append({"tipo": "estancamiento", "peso": p, "texto": f"Sin mejora de fuerza estimada en 3 sesiones: {', '.join(estancados[:3])}."
                        + ("" if len(estancados) >= 2 else " Con un solo ejercicio, revisa primero técnica, sueño y progresión antes de descargar.")})
    if rir0_pct >= 40:
        p = 2 if rir0_pct >= 60 else 1
        pts += p
        senales.append({"tipo": "esfuerzo", "peso": p, "texto": f"{round(rir0_pct)}% de tus series del último ciclo terminaron al fallo (RIR 0)."})
    if semanas >= 5:
        p = 2 if semanas >= 8 else 1
        pts += p
        senales.append({"tipo": "tiempo", "peso": p, "texto": f"Llevas {semanas} semanas seguidas sin bajar la carga" + (" (más allá de la ventana habitual de 4 a 8)." if semanas >= 8 else " (dentro de la ventana habitual de 4 a 8).")})
    nivel = "recomendada" if pts >= 4 else "vigilar" if pts >= 2 else "ok"
    return {"nivel": nivel, "puntos": pts, "senales": senales, "semanas": semanas, "dias": None}


# ---------- "Marca a batir" escrita a mano: al cambiar de unidad se convierten sus pesos ----------
def convertir_marca(texto: str, de: str, a: str) -> str:
    """'50×9 · 50×8' → pesos convertidos a 1 decimal. Solo toca el número antes de la 'x'; las repeticiones no cambian."""
    import re
    if not texto or de == a:
        return texto

    def cambia(m):
        v = round(convertir(float(m.group(1).replace(",", ".")), de, a), 1)
        return f"{fmt_n(v)}{m.group(2)}"
    return re.sub(r"(\d+(?:[.,]\d+)?)(\s*[x×*]\s*\d+)", cambia, texto, flags=re.I)
