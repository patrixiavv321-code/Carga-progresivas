# Gimnasio

Misma estructura que tu app de calorías: FastAPI + Supabase (Postgres) + Render.

1. Sube esta carpeta a un repositorio nuevo en GitHub (el `.env` no se sube, ya está en `.gitignore`).
2. En Supabase: Project Settings → Database → Connection string (modo "Transaction pooler", puerto 6543). Copia la URL.
3. En Render: New → Blueprint → elige el repositorio. Cuando pida variables:
   - `DATABASE_URL` = la URL de Supabase
   - `APP_CLAVE` = una clave tuya (recomendado)
4. Al primer arranque se crean las tablas y se cargan tus ejercicios y marcas iniciales. Ábrela en el celular y pulsa "Agregar a pantalla de inicio".

Probar en tu computador: `pip install -r requirements.txt` y `uvicorn main:app --reload` (sin DATABASE_URL usa un archivo local).
Para agregar ejercicios base nuevos: edita `ejercicios_base.py` y sube `VERSION`.
