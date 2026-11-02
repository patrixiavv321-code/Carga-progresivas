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

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ok")
