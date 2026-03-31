"""
Hospital QMS - Wait Time Predictor
Stack: Python + XGBoost + FastAPI
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# ──────────────────────────────────────────────
# 1. FEATURE ENGINEERING
# ──────────────────────────────────────────────

DEPARTMENT_CODES = {
    "OPD-General": 0,
    "OPD-Cardiology": 1,
    "OPD-Orthopedics": 2,
    "OPD-Pediatrics": 3,
    "OPD-Gynecology": 4,
    "OPD-ENT": 5,
    "OPD-Dermatology": 6,
    "Emergency": 7,
}

PRIORITY_CODES = {
    "Normal": 0,
    "Senior Citizen": 1,
    "Pregnant": 2,
    "Differently Abled": 3,
    "Emergency": 4,
}


def extract_features(record: dict) -> np.ndarray:
    """
    Convert a raw queue record into model-ready features.

    Expected keys in `record`:
        - department        : str   (e.g. "OPD-Cardiology")
        - priority          : str   (e.g. "Normal", "Emergency")
        - tokens_ahead      : int   (patients ahead in queue)
        - avg_consult_time  : float (dept rolling average consultation minutes)
        - doctor_available  : int   (0 = no, 1 = yes)
        - hour_of_day       : int   (0-23)
        - day_of_week       : int   (0=Mon … 6=Sun)
        - is_holiday        : int   (0 or 1)
        - current_queue_len : int   (total active tokens in department)
        - avg_wait_last_1h  : float (rolling 1-hour avg wait in minutes)
    """
    dept_enc   = DEPARTMENT_CODES.get(record.get("department", "OPD-General"), 0)
    prio_enc   = PRIORITY_CODES.get(record.get("priority", "Normal"), 0)

    features = np.array([
        dept_enc,
        prio_enc,
        record.get("tokens_ahead", 0),
        record.get("avg_consult_time", 10.0),
        record.get("doctor_available", 1),
        record.get("hour_of_day", datetime.now().hour),
        record.get("day_of_week", datetime.now().weekday()),
        record.get("is_holiday", 0),
        record.get("current_queue_len", 1),
        record.get("avg_wait_last_1h", 15.0),
    ], dtype=np.float32)

    return features.reshape(1, -1)


FEATURE_NAMES = [
    "department",
    "priority",
    "tokens_ahead",
    "avg_consult_time",
    "doctor_available",
    "hour_of_day",
    "day_of_week",
    
    "is_holiday",
    "current_queue_len",
    "avg_wait_last_1h",
]


# ──────────────────────────────────────────────
# 2. SYNTHETIC DATA GENERATOR (for demo / testing)
# ──────────────────────────────────────────────

def generate_synthetic_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic hospital queue data for training.
    In production, replace this with your actual PostgreSQL query.
    """
    rng = np.random.default_rng(seed)

    dept_keys  = list(DEPARTMENT_CODES.keys())
    prio_keys  = list(PRIORITY_CODES.keys())

    departments = rng.choice(dept_keys, n_samples)
    priorities  = rng.choice(prio_keys, n_samples, p=[0.65, 0.12, 0.10, 0.08, 0.05])

    dept_enc = np.array([DEPARTMENT_CODES[d] for d in departments])
    prio_enc = np.array([PRIORITY_CODES[p]   for p in priorities])

    tokens_ahead      = rng.integers(0, 30, n_samples)
    avg_consult_time  = rng.uniform(5, 20, n_samples)
    doctor_available  = rng.integers(0, 2, n_samples)
    hour_of_day       = rng.integers(8, 20, n_samples)
    day_of_week       = rng.integers(0, 7, n_samples)
    is_holiday        = rng.choice([0, 1], n_samples, p=[0.92, 0.08])
    current_queue_len = rng.integers(1, 50, n_samples)
    avg_wait_last_1h  = rng.uniform(5, 60, n_samples)

    # Target: wait time in minutes (with realistic noise)
    wait_time = (
        tokens_ahead * avg_consult_time * 0.85
        + (1 - doctor_available) * 20
        + is_holiday * 15
        + (hour_of_day > 10) * (hour_of_day < 14) * 10   # lunch rush
        - prio_enc * 8                                      # higher priority = less wait
        + rng.normal(0, 5, n_samples)                       # noise
    ).clip(0, 180)

    df = pd.DataFrame({
        "department":        dept_enc,
        "priority":          prio_enc,
        "tokens_ahead":      tokens_ahead,
        "avg_consult_time":  avg_consult_time,
        "doctor_available":  doctor_available,
        "hour_of_day":       hour_of_day,
        "day_of_week":       day_of_week,
        "is_holiday":        is_holiday,
        "current_queue_len": current_queue_len,
        "avg_wait_last_1h":  avg_wait_last_1h,
        "wait_time_minutes": wait_time,
    })
    return df


# ──────────────────────────────────────────────
# 3. MODEL TRAINING
# ──────────────────────────────────────────────

MODEL_PATH = "wait_time_model.json"


def train_model(df: Optional[pd.DataFrame] = None, save: bool = True) -> xgb.XGBRegressor:
    """Train XGBoost model on queue history data."""
    if df is None:
        print("No data provided — generating synthetic training data...")
        df = generate_synthetic_data(n_samples=8000)

    X = df[FEATURE_NAMES]
    y = df["wait_time_minutes"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        eval_metric="mae",
        early_stopping_rounds=20,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluation
    preds = model.predict(X_test)
    mae  = mean_absolute_error(y_test, preds)
    rmse = mean_squared_error(y_test, preds) ** 0.5
    print(f"Model trained  |  MAE: {mae:.2f} min  |  RMSE: {rmse:.2f} min")

    if save:
        model.save_model(MODEL_PATH)
        print(f"Model saved to {MODEL_PATH}")

    return model


def load_model() -> xgb.XGBRegressor:
    """Load model from disk; train if not found."""
    if os.path.exists(MODEL_PATH):
        m = xgb.XGBRegressor()
        m.load_model(MODEL_PATH)
        return m
    print("Model not found — training from scratch...")
    return train_model()


# ──────────────────────────────────────────────
# 4. FASTAPI SERVICE
# ──────────────────────────────────────────────

app = FastAPI(
    title="Hospital QMS — Wait Time Predictor",
    description="XGBoost-based patient wait time estimation API",
    version="1.0.0",
)

_model: Optional[xgb.XGBRegressor] = None


def get_model() -> xgb.XGBRegressor:
    global _model
    if _model is None:
        _model = load_model()
    return _model


class PatientQueueRecord(BaseModel):
    department:        str   = "OPD-General"
    priority:          str   = "Normal"
    tokens_ahead:      int   = 5
    avg_consult_time:  float = 10.0
    doctor_available:  int   = 1
    hour_of_day:       int   = 10
    day_of_week:       int   = 0
    is_holiday:        int   = 0
    current_queue_len: int   = 10
    avg_wait_last_1h:  float = 15.0


class PredictionResponse(BaseModel):
    estimated_wait_minutes: float
    estimated_wait_display: str
    confidence_band:        str
    priority:               str
    department:             str


@app.on_event("startup")
async def startup_event():
    get_model()
    print("Model loaded and ready.")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/predict", response_model=PredictionResponse)
def predict_wait_time(record: PatientQueueRecord):
    model = get_model()
    features = extract_features(record.dict())

    raw_pred = float(model.predict(features)[0])
    wait_min = max(0.0, round(raw_pred, 1))

    # Human-friendly display
    if wait_min < 60:
        display = f"{int(wait_min)} min"
    else:
        h, m = divmod(int(wait_min), 60)
        display = f"{h}h {m}min"

    # Simple confidence band (±15%)
    low  = max(0, round(wait_min * 0.85, 1))
    high = round(wait_min * 1.15, 1)
    band = f"{low}–{high} min"

    return PredictionResponse(
        estimated_wait_minutes=wait_min,
        estimated_wait_display=display,
        confidence_band=band,
        priority=record.priority,
        department=record.department,
    )


@app.get("/departments")
def list_departments():
    return {"departments": list(DEPARTMENT_CODES.keys())}


@app.get("/priorities")
def list_priorities():
    return {"priorities": list(PRIORITY_CODES.keys())}


# ──────────────────────────────────────────────
# 5. ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("Training model on synthetic data...")
    train_model()

    print("\nStarting FastAPI server at http://localhost:8000")
    print("Swagger docs at  http://localhost:8000/docs\n")
    uvicorn.run("wait_time_predictor:app", host="0.0.0.0", port=8000, reload=True)
