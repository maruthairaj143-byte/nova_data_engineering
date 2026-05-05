import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# ── Database configuration ──────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "postgres",
    "user":     "postgres",
    "password": "os.environ.get("PGPASSWORD")",
}

engine = create_engine(
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# ── ML-04 SQL ───────────────────────────────────────────────────────────────
SQL = """
    SELECT
        EXTRACT(EPOCH FROM frr.finish_time::interval)    AS finish_time_seconds,
        EXTRACT(YEAR FROM AGE(dd.date, dc.dob))          AS age_at_event,
        dc.gender                                         AS gender,
        de.marathon_type                                  AS marathon_type,
        dd.weekend_flag                                   AS weekend_flag,
        dd.month                                          AS month,
        CASE
            WHEN EXTRACT(EPOCH FROM frr.finish_time::interval) <= 1800  THEN 'Elite'
            WHEN EXTRACT(EPOCH FROM frr.finish_time::interval) <= 3600  THEN 'Competitive'
            WHEN EXTRACT(EPOCH FROM frr.finish_time::interval) <= 7200  THEN 'Recreational'
            ELSE 'Beginner'
        END                                               AS performance_tier
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
print(f"✅ Performance tier distribution:\n{df['performance_tier'].value_counts()}")

# ── Encode target ────────────────────────────────────────────────────────────
le_target = LabelEncoder()
df["tier_encoded"] = le_target.fit_transform(df["performance_tier"])

# ── Encode categorical columns ───────────────────────────────────────────────
for col in ["gender", "marathon_type"]:
    df[col] = LabelEncoder().fit_transform(df[col].astype(str))
df["weekend_flag"] = df["weekend_flag"].astype(int)

# ── Features & target ────────────────────────────────────────────────────────
FEATURES = [
    "finish_time_seconds", "age_at_event", "gender",
    "marathon_type", "weekend_flag", "month"
]
X = df[FEATURES].fillna(0)
y = df["tier_encoded"]

# ── Train / test split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── Build & train model ──────────────────────────────────────────────────────
model = GradientBoostingClassifier(
    n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42
)
print("⏳ Training model...")
model.fit(X_train, y_train)
print("✅ Training complete!")

# ── Evaluate ─────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
print(f"\nAccuracy : {accuracy_score(y_test, y_pred):.4f}")
print(f"Macro F1 : {f1_score(y_test, y_pred, average='macro'):.4f}")

# ── Confusion Matrix ─────────────────────────────────────────────────────────
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d',
            xticklabels=le_target.classes_,
            yticklabels=le_target.classes_,
            cmap="Blues")
plt.title("Performance Tier Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.tight_layout()
plt.show()