"""Parse DATABASE_URL and verify pooler login (used by fix-azure-db-pooler.py)."""
import sys
import time

import psycopg2
from sqlalchemy.engine.url import make_url

raw = sys.argv[1]
url = make_url(raw.replace("postgresql://", "postgresql+psycopg2://", 1))

last_err: Exception | None = None
for attempt in range(5):
    try:
        conn = psycopg2.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            dbname=url.database or "postgres",
            sslmode="require",
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        conn.close()
        print("pooler connection ok")
        raise SystemExit(0)
    except psycopg2.Error as exc:
        last_err = exc
        time.sleep(2)

print(last_err, file=sys.stderr)
raise SystemExit(1)
