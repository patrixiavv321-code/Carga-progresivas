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
