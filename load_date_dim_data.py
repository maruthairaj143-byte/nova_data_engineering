"""
=============================================================
 DIM DATE LOAD (CORRECT VERSION – NO ERROR)
=============================================================
"""

import psycopg2
from datetime import date, timedelta, datetime

# DB CONFIG
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="postgres",
    user="postgres",
    password=os.environ.get("PGPASSWORD")
)

cur = conn.cursor()

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
start = date(2026, 1, 1)
end   = date(2027, 12, 31)

current = start
i = 1
now = datetime.now()

created_by = "etl_user"
updated_by = "etl_user"
batch_id = int(date.today().strftime("%Y%m%d"))

while current <= end:

    cur.execute("""
        INSERT INTO dim_date (
            date_key, date, day, week, month, quarter, year, weekend_flag,
            created_by, created_at, updated_by, updated_at, batch_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        f"D{i:04d}",
        current,
        current.day,
        current.isocalendar()[1],
        current.month,
        (current.month - 1)//3 + 1,
        current.year,
        current.weekday() >= 5,
        created_by,
        now,
        updated_by,
        now,
        batch_id
    ))

    current += timedelta(days=1)
    i += 1

conn.commit()

print("✅ DIM_DATE LOADED SUCCESSFULLY")

cur.close()
conn.close()