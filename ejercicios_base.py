"""Tus marcas iniciales. VERSION sube cuando agregues ejercicios aquí; solo se crean los que falten."""
VERSION = 1
# (dia, nombre, músculo, unidad, principal, [(peso, reps, rir)], referencia, nota)
BASE = [
 (1, "Chest Press en máquina", "Pecho", "lbs", True, [(200, 10, None), (200, 9, None)], "Previo: 200×12 @RIR0, 200×9 @RIR1", ""),
 (1, "Press inclinado con mancuernas", "Pecho", "kg", True, [(34, 8, None), (34, 6, None)], "Previo: 34×7, 32×9", ""),
 (1, "Dominadas con lastre", "Espalda", "kg", True, [(10, 7, None), (10, 5, None)], "+2 reps sin peso en ambas series", "lastre + peso corporal"),
 (1, "Espalda unilateral en máquina", "Espalda", "kg", False, [(50, 8, None), (50, 8, None)], "Previo: 45×9, 50×7", ""),
 (1, "Pec fly (aperturas en máquina)", "Pecho", "kg", False, [(86, 8, None), (79, 8, None)], "Récord: 93×7", ""),
 (1, "Jalón al pecho", "Espalda", "lbs", False, [(110, 8, None), (110, 8, None)], "", ""),
 (1, "Remo en máquina sentado", "Espalda", "lbs", False, [(140, 8, 0), (140, 7, 0)], "", ""),
 (1, "Elevación lateral en máquina", "Hombro", "kg", False, [(55, 8, None), (55, 8, None)], "", ""),
 (2, "Press militar en máquina", "Hombro", "kg", True, [(50, 9, None), (50, 9, None)], "Previo: 45×10", ""),
 (2, "Elevaciones laterales (polea/máquina)", "Hombro", "lbs", True, [(130, 10, None), (130, 8, None)], "", ""),
 (2, "Bíceps curl en máquina", "Bíceps", "kg", True, [(45, 8, None), (45, 8, None)], "Drop/pirámide: 40×10, 42.5×9, 37.5×8", ""),
 (2, "Curl de bíceps con mancuernas", "Bíceps", "kg", False, [(18, 7, None), (18, 6, None)], "", ""),
 (2, "Tríceps copa tras nuca con mancuerna", "Tríceps", "kg", False, [(14, 9, None), (14, 8, None)], "", ""),
 (2, "Tríceps polea con barra recta", "Tríceps", "lbs", False, [(160, 10, None), (160, 8, None)], "Previo: 150×10", ""),
 (3, "Extensión de cuádriceps", "Cuádriceps", "lbs", True, [(220, 10, None), (205, 11, None)], "Drop: 205×9 + 100×7", ""),
 (3, "Leg press plana", "Cuádriceps", "lbs", True, [(235, 9, 0), (235, 9, 0)], "Previo: 220×12 @RIR0, 190×12", ""),
 (3, "Sentadilla hack (alternativa)", "Cuádriceps", "kg", True, [(22.5, 10, None)], "Aproximación: 20×11", ""),
 (3, "Isquiotibiales tumbado en máquina", "Isquiotibiales", "lbs", False, [(130, 9, None)], "Previo: 110 kg×12 / 115 lbs×10", ""),
 (3, "Hip thrust", "Glúteo", "kg", False, [(45, 12, None), (45, 10, None)], "Previo: 40×10 @RIR0", ""),
 (3, "Aductores en máquina", "Aductores", "lbs", False, [(110, 11, None), (110, 11, None)], "En máquina kg: 52×7", ""),
 (3, "Remo pesado", "Espalda", "kg", False, [(100, 3, 0), (90, 6, 0), (90, 6, 0), (80, 8, 0)], "", ""),
 (3, "Gemelos / pantorrillas", "Gemelos", "lbs", False, [(160, 0, 0)], "160 lbs al fallo / 150 lbs al fallo / 20 kg por lado ×15", "reps por registrar (al fallo)"),
]
