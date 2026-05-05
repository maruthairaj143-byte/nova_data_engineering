"""
=============================================================
  Nova Marathon — Master ETL Pipeline Wrapper (FINAL VERSION)
=============================================================
"""

import subprocess
import sys
import logging
import os
import time
from datetime import datetime

# =============================================================
# FORCE UTF-8 (for safety)
# =============================================================
sys.stdout.reconfigure(encoding='utf-8')

# =============================================================
# LOGGING SETUP
# =============================================================

LOG_FILE = "etl_master_pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

log = logging.getLogger("ETL_MASTER")

# =============================================================
# PIPELINE STEPS
# =============================================================

PIPELINE_STEPS = [
    (1, "BRONZE  - CSV to RAW", "load_bronze_all_data.py"),
    (2, "SILVER  - RAW to STG", "load_silver_data.py"),
    (3, "GOLD    - STG to DIM/FACT", "load_gold_dim_fact_data.py"),
]

# =============================================================
# STEP RUNNER
# =============================================================

def run_step(step, label, script):
    log.info("=" * 60)
    log.info(f"STEP {step} START | {label}")
    log.info("=" * 60)

    if not os.path.isfile(script):
        log.error(f"{script} not found in {os.getcwd()}")
        return False

    # 🔥 Force UTF-8 in subprocess
    cmd = [sys.executable, "-Xutf8", script]

    start = time.time()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",     # ✅ FIX decode issue
            errors="replace",     # ✅ prevent crash
            bufsize=1
        )

        # Stream output safely
        for line in process.stdout:
            if line:
                log.info(line.strip())

        process.wait()

        elapsed = time.time() - start

        if process.returncode != 0:
            log.error(f"STEP {step} FAILED | Time: {elapsed:.2f}s")
            return False

        log.info(f"STEP {step} SUCCESS | Time: {elapsed:.2f}s")
        return True

    except Exception as e:
        log.error(f"Unexpected error in step {step}: {e}")
        return False


# =============================================================
# MAIN PIPELINE
# =============================================================

def main():
    start_time = datetime.now()

    log.info("=" * 60)
    log.info("NOVA MARATHON MASTER PIPELINE STARTED")
    log.info("=" * 60)

    results = []

    for step, label, script in PIPELINE_STEPS:
        success = run_step(step, label, script)
        results.append((step, label, success))

        if not success:
            log.error("PIPELINE STOPPED DUE TO ERROR")
            break

    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()

    # =========================================================
    # SUMMARY
    # =========================================================
    log.info("=" * 60)
    log.info("PIPELINE SUMMARY")
    log.info("=" * 60)

    for step, label, success in results:
        status = "SUCCESS" if success else "FAILED"
        log.info(f"Step {step} | {status} | {label}")

    log.info("-" * 60)
    log.info(f"Start Time : {start_time}")
    log.info(f"End Time   : {end_time}")
    log.info(f"Total Time : {total_time:.2f}s")

    if all(r[2] for r in results):
        log.info("PIPELINE COMPLETED SUCCESSFULLY")
        sys.exit(0)
    else:
        log.error("PIPELINE COMPLETED WITH ERRORS")
        sys.exit(1)


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    main()