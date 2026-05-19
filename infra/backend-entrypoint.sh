#!/bin/sh
python - <<'PYEOF'
import os, time, psycopg
db_url = os.environ["DATABASE_URL"]
deadline = time.time() + 120
while time.time() < deadline:
    try:
        psycopg.connect(db_url, connect_timeout=5)
        print("[backend] Database ready")
        break
    except Exception as e:
        time.sleep(2)
else:
    exit(1)
PYEOF
python -m alembic upgrade head || true
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
