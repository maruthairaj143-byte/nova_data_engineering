"""
=============================================================
  Common Config — Nova Marathon Data Engineering Project
  Used by : load_bronze_data.py
            load_silver_data.py
            load_fact_gold_data.py
=============================================================
"""

import os
from datetime import date

# ─────────────────────────────────────────────
# FILE PATHS  (Bronze layer source CSVs)
# ─────────────────────────────────────────────
FILE_PATH = os.environ.get(
    "SOURCE_FILE_PATH",
    r"D:\Nova_project\nova_data_engineering\source_files"
)

FILE_NAME_1  = "nova_registration.csv"
TABLE_NAME_1 = "raw_client"

FILE_NAME_2  = "nova_result.csv"
TABLE_NAME_2 = "raw_result"

FILE_NAME_3  = "nova_event.csv"
TABLE_NAME_3 = "raw_event"

# ─────────────────────────────────────────────
# DATABASE CONNECTION (PostgreSQL)
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": os.environ.get("PGPORT", "5432"),
    "dbname": os.environ.get("PGDATABASE", "postgres"),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", "os.environ.get("PGPASSWORD")"),
}

# Optional: connection string (useful for SQLAlchemy)
DB_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# ─────────────────────────────────────────────
# AUDIT COLUMNS (Used across all layers)
# ─────────────────────────────────────────────
AUDIT_CREATED_BY = os.environ.get("AUDIT_CREATED_BY", "etl_user")
AUDIT_UPDATED_BY = os.environ.get("AUDIT_UPDATED_BY", "etl_user")

# Batch ID
AUDIT_BATCH_ID = int(
    os.environ.get("AUDIT_BATCH_ID", date.today().strftime("%Y%m%d"))
)
AUDIT_BATCH_ID_STR = str(AUDIT_BATCH_ID)

# ─────────────────────────────────────────────
# SCHEMA NAMES (Recommended)
# ─────────────────────────────────────────────
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA   = "gold"

# ─────────────────────────────────────────────
# SILVER TABLES
# ─────────────────────────────────────────────
STG_CLIENT_RESULT_TABLE = f"{SILVER_SCHEMA}.stg_client_result"
STG_EVENT_TABLE         = f"{SILVER_SCHEMA}.stg_event"

# ─────────────────────────────────────────────
# GOLD TABLES (DIM + FACT)
# ─────────────────────────────────────────────
DIM_CLIENT_TABLE   = f"{GOLD_SCHEMA}.dim_client"
DIM_LOCATION_TABLE = f"{GOLD_SCHEMA}.dim_location"
DIM_EVENT_TABLE    = f"{GOLD_SCHEMA}.dim_event"
DIM_DATE_TABLE     = f"{GOLD_SCHEMA}.dim_date"
DIM_SPONSOR_TABLE  = f"{GOLD_SCHEMA}.dim_sponsor"

FACT_RACE_RESULT_TABLE = f"{GOLD_SCHEMA}.fact_race_result"