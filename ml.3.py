import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# --- 0. Database Config ---
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "postgres",
    "user":     "postgres",
    "password": os.environ.get("PGPASSWORD")
}

# --- 1. SQLAlchemy Engine ---
engine = create_engine(
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# --- 2. Load Data ---
ML_SQL = """
SELECT
    EXTRACT(YEAR FROM AGE(dd.date, dc.dob))::INT        AS age_at_event,
    dc.gender,
    dc.state                                             AS runner_state,
    dc.blood_group,
    EXTRACT(EPOCH FROM fr.finish_time)::FLOAT            AS finish_time_seconds,
    fr.distance                                          AS distance_km,
    de.marathon_type,
    de.event_category,
    dd.weekend_flag,
    dd.month,
    dd.quarter,
    ds.contribution_amount                               AS sponsor_contribution
FROM public.fact_race_result  fr
JOIN public.dim_client        dc  ON fr.client_key  = dc.client_key
JOIN public.dim_event         de  ON fr.event_key   = de.event_key
JOIN public.dim_date          dd  ON fr.date_key    = dd.date_key
JOIN public.dim_sponsor       ds  ON fr.sponsor_key = ds.sponsor_key
WHERE fr.finish_time IS NOT NULL
  AND dc.dob         IS NOT NULL
"""

print("Data Loading...")
with engine.connect() as conn:
    df = pd.read_sql(ML_SQL, conn)
print(f"Loaded {len(df)} rows & {len(df.columns)} columns")

# --- 3. Distance Clean பண்ணு (10K → 10, 5K → 5, Half → 21, Full → 42) ---
def clean_distance(val):
    val = str(val).strip().upper()
    if "HALF" in val:
        return 21.0
    elif "FULL" in val:
        return 42.0
    else:
        return float(''.join(filter(lambda x: x.isdigit() or x == '.', val)))

df["distance_km"] = df["distance_km"].apply(clean_distance)
print("\nDistance values after clean:")
print(df["distance_km"].unique())

# --- 4. Encode Categoricals ---
cat_cols = ["gender", "runner_state", "blood_group", "marathon_type", "event_category"]
for col in cat_cols:
    df[col] = LabelEncoder().fit_transform(df[col].astype(str))
df["weekend_flag"] = df["weekend_flag"].astype(int)

# --- 5. Features & Target ---
FEATURES = [
    "age_at_event", "gender", "runner_state", "blood_group", "distance_km",
    "marathon_type", "event_category", "weekend_flag", "month", "quarter",
    "sponsor_contribution"
]
X = df[FEATURES]
y = df["finish_time_seconds"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"\nTrain Size : {len(X_train)} rows")
print(f"Test Size  : {len(X_test)} rows")

# --- 6. Train Model ---
print("\nModel Training...")
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=12,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)
print("Training Complete!")

# --- 7. Evaluate ---
y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae  = mean_absolute_error(y_test, y_pred)
r2   = r2_score(y_test, y_pred)

print(f"\nModel Performance:")
print(f"  RMSE : {rmse:.2f} seconds  ({rmse/60:.2f} mins)")
print(f"  MAE  : {mae:.2f} seconds  ({mae/60:.2f} mins)")
print(f"  R²   : {r2:.4f}")

# --- 8. Feature Importance ---
print(f"\nFeature Importances:")
fi = pd.Series(
    model.feature_importances_,
    index=FEATURES
).sort_values(ascending=False)
print(fi)

# --- 9. Sample Predictions ---
print(f"\nSample Predictions (first 5):")
sample = pd.DataFrame({
    "Actual (mins)"   : (y_test.values[:5] / 60).round(2),
    "Predicted (mins)": (y_pred[:5] / 60).round(2)
})
print(sample)