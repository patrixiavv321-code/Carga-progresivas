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
