import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, roc_auc_score

# ── Database configuration ──────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "maruthu",
}

engine = create_engine(
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# ── ML-03 SQL ───────────────────────────────────────────────────────────────
SQL = """
    SELECT
        EXTRACT(YEAR FROM AGE(dd.date, dc.dob))          AS age_at_event,
        dc.gender                                         AS gender,
        dc.blood_group                                    AS blood_group,
        dl.state                                          AS runner_state,
        de.marathon_type                                  AS marathon_type,
        dd.weekend_flag                                   AS weekend_flag,
        dd.month                                          AS month,
        COALESCE(ds.contribution_amount, 0)               AS sponsor_contribution,
        EXTRACT(EPOCH FROM frr.finish_time::interval)     AS finish_seconds,
        AVG(
            EXTRACT(EPOCH FROM frr.finish_time::interval)
        ) OVER (
            PARTITION BY frr.client_key
            ORDER BY dd.date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        )                                                 AS historical_avg_finish_seconds
    FROM fact_race_result  frr
    JOIN dim_client        dc  ON frr.client_key   = dc.client_key
    JOIN dim_event         de  ON frr.event_key    = de.event_key
    JOIN dim_date          dd  ON frr.date_key     = dd.date_key
    JOIN dim_location      dl  ON frr.location_key = dl.location_key
    LEFT JOIN dim_sponsor  ds  ON frr.sponsor_key  = ds.sponsor_key
"""

# ── Load data ───────────────────────────────────────────────────────────────
df = pd.read_sql(SQL, engine)
print(f"✅ Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")

# ── Create DNF flag: category-wise top 30% slow runners = DNF risk ──────────
# Each marathon type has different finish times, so compare within category
df["finish_rank_pct"] = df.groupby("marathon_type")["finish_seconds"] \
                          .rank(pct=True)
df["dnf_flag"] = (df["finish_rank_pct"] >= 0.70).astype(int)

print(f"✅ DNF flag distribution:\n{df['dnf_flag'].value_counts()}")

# ── Encode categorical columns ───────────────────────────────────────────────
cat_cols = ["gender", "blood_group", "runner_state", "marathon_type"]
for col in cat_cols:
    df[col] = LabelEncoder().fit_transform(df[col].astype(str))
df["weekend_flag"] = df["weekend_flag"].astype(int)

# ── Features & target ────────────────────────────────────────────────────────
FEATURES = [
    "age_at_event", "gender", "blood_group", "runner_state",
    "marathon_type", "weekend_flag", "month", "sponsor_contribution",
    "historical_avg_finish_seconds"
]
X = df[FEATURES].fillna(0)
y = df["dnf_flag"]

# ── Train / test split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# ── Scale features ───────────────────────────────────────────────────────────
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ── Build & train ensemble ───────────────────────────────────────────────────
lr  = LogisticRegression(max_iter=1000, class_weight="balanced")
rf  = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42)
ens = VotingClassifier([("lr", lr), ("rf", rf)], voting="soft")

print("⏳ Training ensemble model...")
ens.fit(X_train_s, y_train)
print("✅ Training complete!")

# ── Evaluate ─────────────────────────────────────────────────────────────────
y_pred = ens.predict(X_test_s)
y_prob = ens.predict_proba(X_test_s)[:, 1]

print("\n── Classification Report ──────────────────────────────")
print(classification_report(y_test, y_pred))
print(f"AUC-ROC: {roc_auc_score(y_test, y_prob):.4f}")