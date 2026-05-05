# nova_data_engineering
# 🏃 Nova Marathon Analytics — Data Engineering Project

A end-to-end **ETL Data Pipeline** built using Python and PostgreSQL, implementing the **Medallion Architecture** (Bronze → Silver → Gold) for Marathon race analytics.

---

## 🏗️ Architecture

```
CSV Files (Source)
      ↓
 Bronze Layer  →  Raw data loaded as-is
      ↓
 Silver Layer  →  Cleaned & transformed data
      ↓
  Gold Layer   →  Dimension & Fact tables (Star Schema)
```

---

## 🛠️ Tech Stack

| Tool | Usage |
|------|-------|
| Python | ETL Pipeline scripts |
| PostgreSQL | Data Warehouse |
| Pandas | Data transformation |
| psycopg2 | PostgreSQL connection |
| SQL | Table creation & queries |

---

## 📁 Project Structure

```
nova_data_engineering/
│
├── config.py                  # Database configuration
├── run_pipeline.py            # Master pipeline runner
├── load_bronze_data.py        # Bronze layer loader
├── load_bronze_all_data.py    # Bronze full load
├── load_silver_data.py        # Silver layer transformer
├── load_gold_dim_fact_data.py # Gold layer - Dimension & Fact tables
├── load_date_dim_data.py      # Date dimension loader
│
├── source_files/
│   ├── nova_event.csv         # Event source data
│   ├── nova_registration.csv  # Registration source data
│   └── nova_result.csv        # Result source data
│
└── .gitignore
```

---

## 📊 Data Model

### Source Tables (Bronze)
- `raw_event` — Marathon event details
- `raw_registration` — Runner registration data
- `raw_result` — Race results

### Gold Layer (Star Schema)
- `fact_race_result` — Central fact table
- `dim_event`, `dim_runner`, `dim_date` — Dimension tables

---

## 🚀 How to Run

### 1. Set Environment Variables
```bash
# Windows
$env:PGPASSWORD="your_password"
$env:PGUSER="postgres"
$env:PGDATABASE="postgres"
```

### 2. Run the Pipeline
```bash
python run_pipeline.py
```

---

## 👨‍💻 Author

**Maruthairaj** — Fresher Data Analyst  
📧 maruthairaj143@gmail.com  
🔗 [GitHub](https://github.com/maruthairaj143-byte)
