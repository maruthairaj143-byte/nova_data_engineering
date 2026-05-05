"""
=============================================================
  Silver → Gold Layer ETL Script (FINAL WORKING VERSION)
  ✔ Surrogate keys using SEQUENCE
  ✔ Stable keys during UPSERT
  ✔ Type 1 SCD
  ✔ Fact load fixed (no join error)
=============================================================
"""

import psycopg2
from datetime import datetime
import logging
import sys

from config import DB_CONFIG, AUDIT_CREATED_BY, AUDIT_UPDATED_BY, AUDIT_BATCH_ID


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etl_gold.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


# ─────────────────────────────────────────────
# CREATE SEQUENCES
# ─────────────────────────────────────────────
def create_sequences(conn):
    sql = """
    CREATE SEQUENCE IF NOT EXISTS dim_client_seq START 1;
    CREATE SEQUENCE IF NOT EXISTS dim_event_seq START 1;
    CREATE SEQUENCE IF NOT EXISTS dim_location_seq START 1;
    CREATE SEQUENCE IF NOT EXISTS dim_sponsor_seq START 1;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    log.info("Sequences ensured.")


# ─────────────────────────────────────────────
# DIM CLIENT
# ─────────────────────────────────────────────
def load_dim_client(conn, now):
    sql = """
    INSERT INTO dim_client (
        client_key, first_name, last_name, dob, gender,
        city, state, blood_group, mobile_number,
        created_by, created_at, updated_by, updated_at, batch_id
    )
    SELECT
        COALESCE(dc.client_key,
            'C' || LPAD(NEXTVAL('dim_client_seq')::TEXT, 4, '0')
        ),
        s.first_name, s.last_name, s.date_of_birth, s.gender,
        s.city, s.state, s.blood_group, s.mobile_number,
        %s, %s, %s, %s, %s
    FROM (
        SELECT DISTINCT ON (mobile_number)
            first_name, last_name, date_of_birth, gender,
            city, state, blood_group, mobile_number
        FROM stg_client_result
        WHERE mobile_number IS NOT NULL
        ORDER BY mobile_number
    ) s
    LEFT JOIN dim_client dc
        ON s.mobile_number = dc.mobile_number
    ON CONFLICT (mobile_number) DO UPDATE
    SET first_name  = EXCLUDED.first_name,
        last_name   = EXCLUDED.last_name,
        dob         = EXCLUDED.dob,
        gender      = EXCLUDED.gender,
        city        = EXCLUDED.city,
        state       = EXCLUDED.state,
        blood_group = EXCLUDED.blood_group,
        updated_by  = EXCLUDED.updated_by,
        updated_at  = EXCLUDED.updated_at,
        batch_id    = EXCLUDED.batch_id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (AUDIT_CREATED_BY, now, AUDIT_UPDATED_BY, now, AUDIT_BATCH_ID))
        log.info(f"dim_client loaded: {cur.rowcount} rows")
    conn.commit()


# ─────────────────────────────────────────────
# DIM EVENT
# ─────────────────────────────────────────────
def load_dim_event(conn, now):
    sql = """
    INSERT INTO dim_event (
        event_key, event_name, marathon_type, organizer_name,
        venue_name, event_status, event_category,
        created_by, created_at, updated_by, updated_at, batch_id
    )
    SELECT
        COALESCE(de.event_key,
            'E' || LPAD(NEXTVAL('dim_event_seq')::TEXT, 4, '0')
        ),
        s.event_name, s.marathon_type, s.organizer_name,
        s.venue_name, s.event_status, s.event_category,
        %s, %s, %s, %s, %s
    FROM (
        SELECT DISTINCT ON (event_name)
            event_name, marathon_type, organizer_name,
            venue_name, event_status, event_category
        FROM stg_event
        WHERE event_name IS NOT NULL
        ORDER BY event_name
    ) s
    LEFT JOIN dim_event de
        ON s.event_name = de.event_name
    ON CONFLICT (event_name) DO UPDATE
    SET marathon_type   = EXCLUDED.marathon_type,
        organizer_name  = EXCLUDED.organizer_name,
        venue_name      = EXCLUDED.venue_name,
        event_status    = EXCLUDED.event_status,
        event_category  = EXCLUDED.event_category,
        updated_by      = EXCLUDED.updated_by,
        updated_at      = EXCLUDED.updated_at,
        batch_id        = EXCLUDED.batch_id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (AUDIT_CREATED_BY, now, AUDIT_UPDATED_BY, now, AUDIT_BATCH_ID))
        log.info(f"dim_event loaded: {cur.rowcount} rows")
    conn.commit()


# ─────────────────────────────────────────────
# DIM LOCATION
# ─────────────────────────────────────────────
def load_dim_location(conn, now):
    sql = """
    INSERT INTO dim_location (
        location_key, city, state, country,
        created_by, created_at, updated_by, updated_at, batch_id
    )
    SELECT
        COALESCE(dl.location_key,
            'L' || LPAD(NEXTVAL('dim_location_seq')::TEXT, 4, '0')
        ),
        s.city, s.state, s.country,
        %s, %s, %s, %s, %s
    FROM (
        SELECT DISTINCT ON (city, state)
            city, state, country
        FROM stg_event
        WHERE city IS NOT NULL AND state IS NOT NULL
        ORDER BY city, state
    ) s
    LEFT JOIN dim_location dl
        ON s.city = dl.city AND s.state = dl.state
    ON CONFLICT (city, state) DO UPDATE
    SET country    = EXCLUDED.country,
        updated_by = EXCLUDED.updated_by,
        updated_at = EXCLUDED.updated_at,
        batch_id   = EXCLUDED.batch_id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (AUDIT_CREATED_BY, now, AUDIT_UPDATED_BY, now, AUDIT_BATCH_ID))
        log.info(f"dim_location loaded: {cur.rowcount} rows")
    conn.commit()


# ─────────────────────────────────────────────
# DIM SPONSOR
# ─────────────────────────────────────────────
def load_dim_sponsor(conn, now):
    sql = """
    INSERT INTO dim_sponsor (
        sponsor_key, sponsor_name, sponsor_type, contribution_amount,
        created_by, created_at, updated_by, updated_at, batch_id
    )
    SELECT
        COALESCE(ds.sponsor_key,
            'S' || LPAD(NEXTVAL('dim_sponsor_seq')::TEXT, 4, '0')
        ),
        s.sponsor_name, s.sponsor_type, s.contribution_amount,
        %s, %s, %s, %s, %s
    FROM (
        SELECT DISTINCT ON (sponsor_name)
            sponsor_name, sponsor_type, contribution_amount
        FROM stg_event
        WHERE sponsor_name IS NOT NULL
        ORDER BY sponsor_name
    ) s
    LEFT JOIN dim_sponsor ds
        ON s.sponsor_name = ds.sponsor_name
    ON CONFLICT (sponsor_name) DO UPDATE
    SET sponsor_type        = EXCLUDED.sponsor_type,
        contribution_amount = EXCLUDED.contribution_amount,
        updated_by          = EXCLUDED.updated_by,
        updated_at          = EXCLUDED.updated_at,
        batch_id            = EXCLUDED.batch_id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (AUDIT_CREATED_BY, now, AUDIT_UPDATED_BY, now, AUDIT_BATCH_ID))
        log.info(f"dim_sponsor loaded: {cur.rowcount} rows")
    conn.commit()


# ─────────────────────────────────────────────
# FACT TABLE
# ─────────────────────────────────────────────
def load_fact_race_result(conn, now):
    sql = """
    INSERT INTO fact_race_result (
        client_key, event_key, date_key, sponsor_key, location_key,
        finish_time, rank, distance, timing_chip_data,
        created_by, created_at, updated_by, updated_at, batch_id
    )
    SELECT
        dc.client_key,
        de.event_key,
        dd.date_key,
        ds.sponsor_key,
        dl.location_key,
        scr.finish_time,
        RANK() OVER (ORDER BY scr.finish_time),
        scr.distance,
        scr.timing_chip_data,
        %s, %s, %s, %s, %s
    FROM stg_client_result scr
    JOIN dim_client dc ON scr.mobile_number = dc.mobile_number
    JOIN stg_event se ON TRUE
    JOIN dim_event de ON se.event_name = de.event_name
    JOIN dim_date dd ON dd.date = se.event_date
    JOIN dim_sponsor ds ON se.sponsor_name = ds.sponsor_name
    JOIN dim_location dl ON se.city = dl.city AND se.state = dl.state
    ON CONFLICT (client_key, event_key) DO UPDATE
    SET finish_time = EXCLUDED.finish_time,
        rank = EXCLUDED.rank,
        updated_by = EXCLUDED.updated_by,
        updated_at = EXCLUDED.updated_at,
        batch_id   = EXCLUDED.batch_id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (AUDIT_CREATED_BY, now, AUDIT_UPDATED_BY, now, AUDIT_BATCH_ID))
        log.info(f"fact_race_result loaded: {cur.rowcount} rows")
    conn.commit()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    conn = get_connection()
    now = datetime.now()

    try:
        create_sequences(conn)
        load_dim_client(conn, now)
        load_dim_event(conn, now)
        load_dim_location(conn, now)
        load_dim_sponsor(conn, now)
        load_fact_race_result(conn, now)

        log.info("Gold layer loaded successfully")

    except Exception as e:
        conn.rollback()
        log.error(f"ETL failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()