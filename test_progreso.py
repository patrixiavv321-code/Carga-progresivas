from datetime import date, timedelta
from progreso import *

def s(p, r, rir=None, u="kg"): return {"peso_kg": a_kg(p, u), "reps": r, "rir": rir}

def test_series():
    assert comparar_serie(s(200,10,u="lbs"), s(200,9,u="lbs")) == "+"
    assert comparar_serie(s(34,8), s(34,8)) == "="
    assert comparar_serie(s(34,6), s(34,8)) == "-"
    assert comparar_serie(s(35,6), s(34,8)) == "-"      # más peso, 1RM estimado menor
    assert comparar_serie(s(40,8), s(34,8)) == "+"
    assert comparar_serie(s(50,8), s(110,8,u="lbs")) == "+"  # 110 lbs = 49.9 kg

def test_ejercicio():
    assert comparar_series([s(10,7), s(10,5)], [s(10,7), s(10,5)])["veredicto"] == "="
    assert comparar_series([s(10,8), s(10,5)], [s(10,7), s(10,5)])["veredicto"] == "+"
    assert comparar_series([s(10,8)], [s(10,7), s(10,5)])["veredicto"] == "-"   # menos series
    assert comparar_series([s(10,8)], None)["veredicto"] == "nuevo"

def test_fatiga():
    h = [{"fecha": date(2026,10,1)+timedelta(days=7*i), "series":[s(10,8)]} for i in range(3)]
    h[1]["veredicto"] = h[2]["veredicto"] = "-"; h[0]["veredicto"] = "="
    assert "baja" in alerta_fatiga(h)
    r = [{"fecha": date(2026,9,1)+timedelta(days=10*i), "series":[s(10,8,0)], "veredicto":"="} for i in range(5)]
    assert "RIR" in alerta_fatiga(r)
    assert alerta_fatiga(r[:3]) is None

def H(*sesiones, ver=None):
    out = []
    for i, ss in enumerate(sesiones):
        out.append({"fecha": date(2026,10,1)+timedelta(days=7*i), "series": ss, "veredicto": (ver or ["="]*len(sesiones))[i]})
    return out

def test_recomendar():
    r = recomendar(H([s(50,12),s(50,12)]), "kg", False, "Curl")
    assert r["tipo"] == "subir" and r["sugerido"] == 52.5
    r = recomendar(H([s(200,10,u="lbs"),s(200,10,u="lbs")]), "lbs", True, "Chest")
    assert r["tipo"] == "subir" and r["sugerido"] == 210
    assert recomendar(H([s(40,7),s(40,7)]), "kg", False, "X")["tipo"] == "mantener"
    assert recomendar(H([s(40,9,3),s(40,9,2)]), "kg", False, "X")["tipo"] == "subir"          # RIR>=2
    assert recomendar(H([s(40,9)], [s(40,7)], ver=["=","-"]), "kg", False, "X")["tipo"] == "mantener"
    assert recomendar(H([s(40,9)], [s(40,7)], [s(40,6)], ver=["=","-","-"]), "kg", False, "X")["tipo"] == "bajar"
    assert recomendar(H([s(34,8)], [s(34,8)], [s(34,8)]), "kg", True, "Press con mancuernas")["tipo"] == "estancado"
    assert incremento(34, "kg", "mancuernas") == 2

def ses(i, dia, mej, ig, emp, rir0=0, rirdef=0, start=date(2026,10,26)):
    return {"fecha": start+timedelta(days=i), "dia": dia, "resumen": {"mejoraron":mej,"iguales":ig,"empeoraron":emp,"nuevos":0}, "rir0": rir0, "rirdef": rirdef}
N = {1:"Torso", 2:"Brazo y hombro", 3:"Pierna"}

def test_recuperacion():
    bien = [ses(0,1,5,2,1), ses(1,2,4,2,0), ses(2,3,3,4,0)]
    r = estado_recuperacion(bien, date(2026,10,30), N)           # 1 día de descanso hecho
    assert r["nivel"] == "bien" and r["hoy"]["estado"] == "descansar"
    r = estado_recuperacion(bien, date(2026,11,1), N)            # 2 días de descanso hechos
    assert r["hoy"]["estado"] == "entrenar" and "Torso" in r["hoy"]["mensaje"]
    mal = [ses(0,1,1,2,5), ses(1,2,0,3,4), ses(2,3,1,2,5)]
    r = estado_recuperacion(mal, date(2026,11,1), N)
    assert r["nivel"] in ("atencion","alta") and r["hoy"]["estado"] == "descansar" and r["descanso_dias"] >= 3
    assert estado_recuperacion([bien[0]], date(2026,10,26), N)["hoy"]["estado"] == "ya"

def test_unidades():
    assert convertir(93.5, "kg", "kg") == 93.5                       # misma unidad: valor exacto, sin pasar por conversión
    assert abs(convertir(convertir(200, "lbs", "kg"), "kg", "lbs") - 200) < 1e-9
    assert abs(convertir(100, "kg", "lbs") - 220.46226218) < 1e-6
    g = s(200, 10, u="lbs")                                          # el dato guardado no cambia al mostrarlo en kg
    antes = (200, "lbs"); convertir(200, "lbs", "kg"); assert antes == (200, "lbs") and abs(g["peso_kg"] - 90.718474) < 1e-6

def test_rpe_rir():
    assert rir_de_rpe(10) == 0 and rir_de_rpe(9.5) == 0 and rir_de_rpe(9) == 1 and rir_de_rpe(8) == 2
    assert rpe_de_rir(0) == 10.0 and rpe_de_rir(3) == 7.0

def P(p, r, u="kg"): return {"peso": p, "unidad": u, "reps": r, "peso_kg": a_kg(p, u)}

def test_pr():
    h = [{"fecha": date(2026,10,1), "series": [P(200, 10, "lbs"), P(100, 0)]},        # reps 0 (fallo sin registrar): se ignora
         {"fecha": date(2026,10,8), "series": [P(100, 3), P(90, 8)]},
         {"fecha": date(2026,10,15), "series": [P(100, 3)]}]                           # empate: se conserva el más antiguo
    pr = calcular_pr(h)
    assert pr["max"]["kg"] == 100 and pr["max"]["fecha"] == "2026-10-08"
    assert pr["e1rm"]["unidad"] == "lbs" and abs(pr["e1rm"]["kg"] - 120.958) < 0.01     # 200 lbs x10 > 100 kg x3 (110)
    assert calcular_pr([{"fecha": date(2026,10,1), "series": [P(50, 20)]}])["max"]["reps"] == 20
    assert calcular_pr([{"fecha": date(2026,10,1), "series": [P(50, 20)]}])["e1rm"] is None   # >12 reps: no sirve para 1RM
    assert calcular_pr([]) is None

def test_descarga():
    f = date(2026, 11, 10)
    assert semanas_continuas([f - timedelta(days=d) for d in (0, 3, 6, 9, 13, 17, 21, 25, 29, 34, 38, 42)], f) == 6
    assert semanas_continuas([f - timedelta(days=d) for d in (0, 2, 30)], f) == 0       # hueco de 28 días: se reinicia
    assert semanas_continuas([f - timedelta(days=d) for d in (0, 3, 6, 9, 13, 17, 21, 25, 29, 34)], f, f - timedelta(days=14)) == 2   # descarga marcada hace 14 días
    assert semanas_continuas([f - timedelta(days=10)], f) == 0                           # parado >7 días
    base = dict(n_sesiones=9, regresion=[], estancados=[], rir0_pct=0, semanas=3, dias_desde_descarga=None)
    assert evaluar_descarga(**base)["nivel"] == "ok"
    assert evaluar_descarga(**{**base, "estancados": ["A"]})["nivel"] == "ok"             # 1 ejercicio estancado no basta
    assert evaluar_descarga(**{**base, "regresion": ["A"]})["nivel"] == "vigilar"
    assert evaluar_descarga(**{**base, "regresion": ["A"], "rir0_pct": 70})["nivel"] == "recomendada"
    assert evaluar_descarga(**{**base, "semanas": 9, "estancados": ["A", "B"]})["nivel"] == "recomendada"
    assert evaluar_descarga(**{**base, "n_sesiones": 2, "regresion": ["A"]})["nivel"] == "sin_datos"
    assert evaluar_descarga(**{**base, "dias_desde_descarga": 2, "regresion": ["A"]})["nivel"] == "en_curso"

def test_marca_y_ciclo():
    assert convertir_marca("200×10 · 200×9", "lbs", "kg") == "90.7×10 · 90.7×9"
    assert convertir_marca("50x9", "kg", "kg") == "50x9" and convertir_marca("", "kg", "lbs") == ""
    assert convertir_marca("Previo: 100×8 @RIR1", "kg", "lbs") == "Previo: 220.5×8 @RIR1"
    r = estado_recuperacion([ses(0, 1, 2, 1, 0)], date(2026, 11, 3), N, 0, [1, 3])           # rutina 2 eliminada: tras Torso toca Pierna
    assert "Pierna" in r["hoy"]["mensaje"] and "Brazo" not in r["hoy"]["mensaje"]
    r = estado_recuperacion([ses(0, 3, 2, 1, 0)], date(2026, 11, 3), N, 0, [1, 3])           # tras Pierna (última) vuelve a Torso
    assert "Torso" in r["hoy"]["mensaje"]

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ok")
