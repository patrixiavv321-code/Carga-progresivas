# Gimnasio

FastAPI + Supabase (Postgres) + Render. Funciona como app instalable y sin internet (PWA).

## Subirla
1. Sube esta carpeta a un repositorio de GitHub (el `.env` no se sube).
2. Supabase → botón **Connect** → **Transaction pooler** → copia la URL y cambia `[YOUR-PASSWORD]` por tu clave.
3. Render → New → Blueprint → tu repositorio. Variables: `DATABASE_URL` (la de Supabase) y `APP_CLAVE` (tu clave).
4. Si ya la tenías publicada, solo haz `git push`: al arrancar agrega las columnas nuevas solo, sin borrar tus entrenamientos ni tus fotos.

## Usarla sin internet (gratis)
1. Con internet, abre la dirección de Render en Chrome (Android) o Safari (iPhone) y entra una vez.
2. Android: menú ⋮ → "Instalar app" / "Agregar a pantalla de inicio". iPhone: Compartir → "Agregar a pantalla de inicio".
3. Ábrela desde ese ícono. Ya queda guardada en el teléfono.
4. En el gimnasio, sin señal: entrena normal. Al terminar te muestra la comparación y guarda el entrenamiento en el teléfono.
5. Cuando vuelva el internet, lo sube solo (también al abrir la app).

No limpies los datos del navegador antes de que se suba lo pendiente.

## Probar en tu computador
`pip install -r requirements.txt` y `uvicorn main:app --reload` (sin DATABASE_URL usa un archivo local).
Pruebas de la lógica: `python test_progreso.py`

## Novedades
- **Unidades (kg / lbs):** botón global junto al buscador (y en *Rutina → Ajustes*) y botón ⇄ en cada ejercicio. Solo cambia cómo ves los pesos: cada serie guarda el peso y la unidad con que la registraste (`series.peso` + `series.unidad`) y nunca se reescribe, así que el historial no pierde precisión. Funciona también sin internet.
- **Récord personal:** cada tarjeta muestra el peso máximo y el mejor 1RM estimado (Epley, solo series de hasta 12 reps) de todo el historial, y marca 🏆 PR al superarlo. Al terminar el entrenamiento te avisa de los récords nuevos.
- **Buscador difuso:** barra fija en *Entrenar*; tolera errores de ortografía y tildes, busca por nombre, músculo y nota, y entiende algunos nombres en inglés (squat, lat, calf…). Si no hay resultados en el día actual, te dice en qué otro día están.
- **Eliminar rutina:** *Rutina → Eliminar rutina* (confirmación con modal). Por defecto conserva el historial; hay una casilla para borrarlo también. La rutina eliminada desaparece de Entrenar, Progreso y Guías (y el ciclo de descanso la salta); en Rutina queda vacía y puedes recrearla agregando un ejercicio en ese día.
- **Historial completo:** series, repeticiones, peso + unidad, **RIR y RPE** (se guardan ambos, RPE ≈ 10 − RIR; elige la escala en Ajustes). `GET /api/ejercicios/{id}/historial` devuelve todo el historial cronológico de un ejercicio y `GET /api/exportar` lo respalda todo.
- **Guías → Descarga:** detector (rendimiento a la baja, estancamiento en varios ejercicios, series al fallo, semanas seguidas), plan calculado con tus pesos (volumen / carga / ambos) y guía con fuentes. Con *Empezar mi semana de descarga* los entrenamientos de esos 7 días no disparan alertas ni cuentan como marca a superar.
- **Guías → Sueño:** plan gradual (30 min cada 3 días) con calculadora y guía de cronobiología con fuentes.

Al arrancar se agrega sola la columna `series.rpe` (y se rellena con 10 − RIR en tus series anteriores). No se borra nada.
