import csv
import os
import re
import sys
import io
import datetime
import psycopg2
from psycopg2 import sql

from config import (
    FILE_PATH,
    FILE_NAME_1,
    TABLE_NAME_1,
    FILE_NAME_2,
    TABLE_NAME_2,
    FILE_NAME_3,
    TABLE_NAME_3,
    DB_CONFIG,
    AUDIT_CREATED_BY,
    AUDIT_UPDATED_BY,
    AUDIT_BATCH_ID,
)

CSV_PATH_1 = os.path.join(FILE_PATH, FILE_NAME_1)
CSV_PATH_2 = os.path.join(FILE_PATH, FILE_NAME_2)
CSV_PATH_3 = os.path.join(FILE_PATH, FILE_NAME_3)

AUDIT_COLUMNS = ["created_by", "created_at", "updated_by", "updated_at", "batch_id"]


def clean_column_name(column_name: str) -> str:
    cleaned = column_name.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"__+", "_", cleaned)
    return cleaned.strip("_")


def get_connection():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )


def build_audit_row_values() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(sep=" ", timespec="seconds")
    return {
        "created_by": AUDIT_CREATED_BY,
        "created_at": now,
        "updated_by": AUDIT_UPDATED_BY,
        "updated_at": now,
        "batch_id": AUDIT_BATCH_ID,
    }


def fix_table_columns(conn, table_name: str):
    if table_name != "raw_client":
        return

    with conn.cursor() as cur:
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'raw_client'
              AND column_name  = 'distance'
        """)
        row = cur.fetchone()

        if row and row[0] != "text":
            print("  ⚠️ Fixing distance column to TEXT...")
            cur.execute("ALTER TABLE public.raw_client ALTER COLUMN distance TYPE TEXT")
            print("  ✅ distance column fixed.")


def prepare_augmented_csv(csv_path: str):
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    audit_values = build_audit_row_values()
    buffer = io.StringIO()

    with open(csv_path, "r", encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)

        original_fields = reader.fieldnames or []
        cleaned_fields = [clean_column_name(field) for field in original_fields]

        fieldnames = cleaned_fields + AUDIT_COLUMNS

        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            if not any(v.strip() for v in row.values()):
                continue

            cleaned_row = {
                clean_column_name(key): value for key, value in row.items()
            }

            cleaned_row.update(audit_values)
            writer.writerow(cleaned_row)

    buffer.seek(0)
    return buffer, fieldnames


def load_into_final_table(conn, source_table: str):
    mapping = {
        "raw_client": "client_all",
        "raw_result": "result_all",
        "raw_event": "event_all",
    }

    if source_table not in mapping:
        return

    target_table = mapping[source_table]

    print(f"➡️ Loading {source_table} → {target_table} ...")

    with conn.cursor() as cur:
        # ❌ DO NOT TRUNCATE final tables
        # ✅ Append data
        cur.execute(
            sql.SQL("INSERT INTO {target} SELECT * FROM {source}").format(
                target=sql.Identifier(target_table),
                source=sql.Identifier(source_table),
            )
        )

    print(f"✅ {target_table} loaded successfully.")


def load_csv_to_postgres(csv_path: str, table_name: str):
    print(f"\nLoading {os.path.basename(csv_path)} → {table_name} ...")

    buffer, fieldnames = prepare_augmented_csv(csv_path)

    columns_sql = sql.SQL(", ").join(sql.Identifier(col) for col in fieldnames)

    copy_sql = sql.SQL(
        "COPY {table} ({columns}) FROM STDIN WITH CSV HEADER DELIMITER ','"
    ).format(
        table=sql.Identifier(table_name),
        columns=columns_sql,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fix column issue
            fix_table_columns(conn, table_name)

            # ✅ Truncate ONLY raw tables
            cur.execute(
                sql.SQL("TRUNCATE TABLE {table} CASCADE").format(
                    table=sql.Identifier(table_name)
                )
            )

            # Load CSV into raw table
            cur.copy_expert(copy_sql, buffer)

        # ✅ Load into final table (NO TRUNCATE)
        load_into_final_table(conn, table_name)

        conn.commit()

    print(f"✅ {table_name} loaded successfully.")


def resolve_load_targets(args):
    known_targets = {
        "1": (CSV_PATH_1, TABLE_NAME_1),
        "2": (CSV_PATH_2, TABLE_NAME_2),
        "3": (CSV_PATH_3, TABLE_NAME_3),
        FILE_NAME_1: (CSV_PATH_1, TABLE_NAME_1),
        FILE_NAME_2: (CSV_PATH_2, TABLE_NAME_2),
        FILE_NAME_3: (CSV_PATH_3, TABLE_NAME_3),
        CSV_PATH_1: (CSV_PATH_1, TABLE_NAME_1),
        CSV_PATH_2: (CSV_PATH_2, TABLE_NAME_2),
        CSV_PATH_3: (CSV_PATH_3, TABLE_NAME_3),
    }

    if len(args) == 0:
        return [
            known_targets["1"],
            known_targets["2"],
            known_targets["3"],
        ]

    if len(args) == 1:
        requested = args[0]

        if requested in known_targets:
            return [known_targets[requested]]

        if os.path.isfile(requested):
            for key in ["1", "2", "3"]:
                if requested == known_targets[key][0]:
                    return [known_targets[key]]

            raise ValueError("Unknown CSV path provided.")

        raise ValueError("Invalid argument. Use 1, 2, or 3.")

    if len(args) == 2:
        csv_path, table_name = args

        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        return [(csv_path, table_name)]

    raise ValueError("Too many arguments.")


if __name__ == "__main__":
    try:
        targets = resolve_load_targets(sys.argv[1:])
    except Exception as exc:
        print(f"Error: {exc}")
        print("Usage: python load_bronze_all_data.py [1|2|3]")
        sys.exit(1)

    failed = []

    for csv_file, table_name in targets:
        try:
            load_csv_to_postgres(csv_file, table_name)
        except Exception as e:
            print(f"❌ Failed to load {table_name}: {e}")
            failed.append(table_name)

    print("\n" + "=" * 50)

    if failed:
        print(f"⚠️ Completed with errors: {failed}")
    else:
        print("🎉 All tables loaded successfully!")

    print("=" * 50)