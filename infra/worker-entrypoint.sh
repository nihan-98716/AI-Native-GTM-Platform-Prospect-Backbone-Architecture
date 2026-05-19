#!/bin/sh
python - <<'PYEOF'
import os, time, psycopg
db_url = os.environ["DATABASE_URL"]
deadline = time.time() + 120
while time.time() < deadline:
    try:
        psycopg.connect(db_url, connect_timeout=5)
        print("[worker] Database ready")
        break
    except Exception as e:
        time.sleep(2)
else:
    exit(1)
PYEOF
python - <<'PYEOF'
import os, time, redis, logging
from app.core.config import get_settings
from app.storage.db import session_scope
from app.services.workflow import ProspectWorkflowService
logging.basicConfig(level=logging.INFO)
while True:
    try:
        r = redis.Redis.from_url(os.environ["WORKFLOW_REDIS_URL"])
        r.ping()
        settings = get_settings()
        with session_scope() as session:
            service = ProspectWorkflowService(session=session, settings=settings)
            while True:
                jobs = r.lrange("workflow_jobs", 0, 0)
                if jobs:
                    job = jobs[0]
                    r.lpop("workflow_jobs")
                    try:
                        service.process_job(job)
                    except Exception as e:
                        logging.error(f"Job failed: {e}")
                        r.rpush("workflow_jobs", job)
                time.sleep(1)
    except Exception as e:
        logging.error(f"Worker error: {e}")
        time.sleep(5)
PYEOF
