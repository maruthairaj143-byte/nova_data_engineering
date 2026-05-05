"""
=============================================================
  Bronze → Silver Layer ETL Script
  Tables : STG_client_result | STG_event
=============================================================
"""

import psycopg2
from datetime import datetime, date
import logging
import sys

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CONFIG = {
    "db_host": "localhost",
    "db_port": 5432,
    "db_name": "postgres",
    "db_user": "postgres",
    "db_password": os.environ.get("PGPASSWORD"),
    "created_by": "etl_user",
    "updated_by": "etl_user",
    "batch_id": int(date.today().strftime("%Y%m%d")),
}

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etl_silver.log"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────
def get_connection():
    conn = psycopg2.connect(
        host=CONFIG["db_host"],
        port=CONFIG["db_port"],
        dbname=CONFIG["db_name"],
        user=CONFIG["db_user"],
        password=CONFIG["db_password"],
    )
    conn.autocommit = False
    log.info("✅ Database connected.")
    return conn


# ─────────────────────────────────────────────
# CREATE TABLES
# ─────────────────────────────────────────────
DDL_STG_CLIENT_RESULT = """
CREATE TABLE IF NOT EXISTS public.stg_client_result (
    Id BIGINT,
    First_Name VARCHAR(50),
    Last_Name VARCHAR(50),
    Date_Of_Birth DATE,
    Gender VARCHAR(10),
    City VARCHAR(50),
    State VARCHAR(50),
    Blood_Group VARCHAR(5),
    Mobile_Number VARCHAR(15),
    Finish_Time INTERVAL,
    Rank INTEGER,
    Distance VARCHAR(20),
    Timing_Chip_Data TEXT,
    Event_ID BIGINT,
    Event_date DATE,
    created_by VARCHAR(50),
    created_at TIMESTAMP,
    updated_by VARCHAR(50),
    updated_at TIMESTAMP,
    Batch_ID INTEGER
);
"""

DDL_STG_EVENT = """
CREATE TABLE IF NOT EXISTS public.stg_event (
    Event_ID BIGINT,
    Event_Name VARCHAR(100),
    Event_date DATE,
    Marathon_Type VARCHAR(20),
    Organizer_Name VARCHAR(100),
    Event_Status VARCHAR(30),
    Event_Category VARCHAR(50),
    Sponsor_Name VARCHAR(100),
    Sponsor_Type VARCHAR(50),
    Contribution_Amount NUMERIC(12,2),
    City VARCHAR(50),
    State VARCHAR(50),
    Country VARCHAR(50),
    Venue_Name VARCHAR(100),
    created_by VARCHAR(50),
    created_at TIMESTAMP,
    updated_by VARCHAR(50),
    updated_at TIMESTAMP,
    Batch_ID INTEGER
);
"""


def create_silver_tables(conn):
    with conn.cursor() as cur:
        cur.execute(DDL_STG_CLIENT_RESULT)
        cur.execute(DDL_STG_EVENT)
    conn.commit()
    log.info("✅ Silver tables ready.")


# ─────────────────────────────────────────────
# ETL — STG_CLIENT_RESULT
# ─────────────────────────────────────────────
TRUNCATE_STG_CLIENT_RESULT = "TRUNCATE TABLE public.stg_client_result CASCADE;"

INSERT_STG_CLIENT_RESULT = """
INSERT INTO public.stg_client_result
SELECT
    rc.id::BIGINT,
    TRIM(rc.first_name),
    TRIM(rc.last_name),
    NULLIF(TRIM(rc.dob),'')::DATE,
    TRIM(rc.gender),
    TRIM(rc.city),
    TRIM(rc.state),
    TRIM(rc.blood_group),
    rc.mobile_number,
    NULLIF(TRIM(rr.split4),'')::INTERVAL,
    rr.teamrank,
    TRIM(rr.distance),
    TRIM(rr.chiptime),
    TRIM(re.event_id)::BIGINT,
    NULLIF(TRIM(re.event_date),'')::DATE,
    %(created_by)s,
    %(now)s,
    %(updated_by)s,
    %(now)s,
    %(batch_id)s
FROM public.raw_client rc
LEFT JOIN public.raw_result rr ON rc.mobile_number = rr.mobile_no
LEFT JOIN public.raw_event re ON TRIM(rc.event_id) = TRIM(re.event_id);
"""


def load_stg_client_result(conn):
    params = {
        "created_by": CONFIG["created_by"],
        "updated_by": CONFIG["updated_by"],
        "batch_id": CONFIG["batch_id"],
        "now": datetime.now(),
    }

    with conn.cursor() as cur:
        log.info("Truncating stg_client_result...")
        cur.execute(TRUNCATE_STG_CLIENT_RESULT)

        log.info("Loading stg_client_result...")
        cur.execute(INSERT_STG_CLIENT_RESULT, params)

    conn.commit()
    log.info("✅ stg_client_result loaded.")


# ─────────────────────────────────────────────
# ETL — STG_EVENT
# ─────────────────────────────────────────────
TRUNCATE_STG_EVENT = "TRUNCATE TABLE public.stg_event CASCADE;"

INSERT_STG_EVENT = """
INSERT INTO public.stg_event
SELECT
    TRIM(event_id)::BIGINT,
    TRIM(event_name),
    NULLIF(TRIM(event_date),'')::DATE,
    TRIM(marathon_type),
    TRIM(organizer_name),
    TRIM(event_status),
    TRIM(event_category),
    TRIM(sponsor_name),
    TRIM(sponsor_type),
    contribution_amount,
    TRIM(city),
    TRIM(state),
    TRIM(country),
    TRIM(venue_name),
    %(created_by)s,
    %(now)s,
    %(updated_by)s,
    %(now)s,
    %(batch_id)s
FROM public.raw_event;
"""


def load_stg_event(conn):
    params = {
        "created_by": CONFIG["created_by"],
        "updated_by": CONFIG["updated_by"],
        "batch_id": CONFIG["batch_id"],
        "now": datetime.now(),
    }

    with conn.cursor() as cur:
        log.info("Truncating stg_event...")
        cur.execute(TRUNCATE_STG_EVENT)

        log.info("Loading stg_event...")
        cur.execute(INSERT_STG_EVENT, params)

    conn.commit()
    log.info("✅ stg_event loaded.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    log.info("🚀 Starting Silver ETL...")

    conn = get_connection()

    try:
        create_silver_tables(conn)
        load_stg_client_result(conn)
        load_stg_event(conn)
        log.info("🎉 Silver layer load complete!")
    except Exception as e:
        conn.rollback()
        log.error(f"❌ ETL failed: {e}")
        sys.exit(1)
    finally:
        conn.close()
        log.info("DB connection closed.")


if __name__ == "__main__":
    main()