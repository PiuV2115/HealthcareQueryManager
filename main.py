"""
Hospital QMS - FastAPI Backend
All routes: patients, queue, departments, doctors, predictions, login
Run: uvicorn main:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

from models import (
    get_db, init_db,
    Patient, Doctor, Department, QueueToken,
    PatientPriority, PatientType, TokenStatus
)
from wait_time_predictor import extract_features, load_model

# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Hospital QMS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None

@app.on_event("startup")
def startup():
    global _model
    init_db()
    _model = load_model()
    print("DB ready. ML model loaded.")


# ── Credentials from .env ──────────────────────────────────────────────────────

STAFF_USERNAME = os.getenv("STAFF_USERNAME", "staff")
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "staff123")

def get_doctor_password(doctor_id: int) -> str:
    return os.getenv(f"DOCTOR_{doctor_id}_PASSWORD", "doc123")


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class PatientIn(BaseModel):
    name:         str
    phone:        Optional[str] = None
    age:          Optional[int] = None
    priority:     PatientPriority = PatientPriority.normal
    patient_type: PatientType     = PatientType.opd

class TokenIn(BaseModel):
    patient_id:    int
    department_id: int
    doctor_id:     Optional[int] = None

class TokenStatusUpdate(BaseModel):
    status: TokenStatus

class DoctorAvailability(BaseModel):
    is_available: bool

class StaffLoginIn(BaseModel):
    username: str
    password: str

class DoctorLoginIn(BaseModel):
    doctor_id: int
    password:  str


# ── Helpers ────────────────────────────────────────────────────────────────────

def generate_token(db: Session) -> str:
    """Simple daily counter: 001, 002, 003..."""
    count = db.query(QueueToken).filter(
        func.date(QueueToken.registered_at) == datetime.utcnow().date()
    ).count()
    return f"{count + 1:03d}"


def predict_wait(token: QueueToken, db: Session) -> float:
    dept   = db.query(Department).filter(Department.id == token.department_id).first()
    doctor = db.query(Doctor).filter(Doctor.id == token.doctor_id).first() if token.doctor_id else None

    tokens_ahead = db.query(QueueToken).filter(
        QueueToken.department_id == token.department_id,
        QueueToken.status == TokenStatus.waiting,
        QueueToken.id < token.id
    ).count()

    queue_len = db.query(QueueToken).filter(
        QueueToken.department_id == token.department_id,
        QueueToken.status.in_([TokenStatus.waiting, TokenStatus.called])
    ).count()

    record = {
        "department":        dept.code if dept else "OPD-GEN",
        "priority":          token.patient.priority.value if token.patient else "Normal",
        "tokens_ahead":      tokens_ahead,
        "avg_consult_time":  doctor.avg_consult_minutes if doctor else 10.0,
        "doctor_available":  1 if (doctor and doctor.is_available) else 0,
        "hour_of_day":       datetime.utcnow().hour,
        "day_of_week":       datetime.utcnow().weekday(),
        "is_holiday":        0,
        "current_queue_len": queue_len,
        "avg_wait_last_1h":  15.0,
    }
    features = extract_features(record)
    return round(float(_model.predict(features)[0]), 1)


# ── Routes: Health ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow()}


# ── Routes: Login ──────────────────────────────────────────────────────────────

@app.post("/login/staff")
def staff_login(data: StaffLoginIn):
    if data.username != STAFF_USERNAME or data.password != STAFF_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"success": True, "role": "staff", "name": "Staff"}

@app.post("/login/doctor")
def doctor_login(data: DoctorLoginIn, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    expected = get_doctor_password(data.doctor_id)
    if data.password != expected:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {
        "success":      True,
        "role":         "doctor",
        "doctor_id":    doctor.id,
        "name":         doctor.name,
        "department_id": doctor.department_id,
    }


# ── Routes: Departments ────────────────────────────────────────────────────────

@app.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).filter(Department.is_active == True).all()


# ── Routes: Doctors ────────────────────────────────────────────────────────────

@app.get("/doctors")
def get_doctors(department_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Doctor)
    if department_id:
        q = q.filter(Doctor.department_id == department_id)
    return q.all()

@app.patch("/doctors/{doctor_id}/availability")
def update_doctor_availability(doctor_id: int, body: DoctorAvailability, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.is_available = body.is_available
    db.commit()
    return {"message": "Updated", "is_available": doctor.is_available}


# ── Routes: Patients ───────────────────────────────────────────────────────────

@app.post("/patients", status_code=201)
def register_patient(data: PatientIn, db: Session = Depends(get_db)):
    patient = Patient(**data.dict())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

@app.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ── Routes: Queue Tokens ───────────────────────────────────────────────────────

@app.post("/tokens", status_code=201)
def create_token(data: TokenIn, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    dept = db.query(Department).filter(Department.id == data.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    token = QueueToken(
        token_number=generate_token(db),
        patient_id=data.patient_id,
        department_id=data.department_id,
        doctor_id=data.doctor_id,
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    token.predicted_wait_minutes = predict_wait(token, db)
    db.commit()
    db.refresh(token)

    return {
        "token_number":           token.token_number,
        "predicted_wait_minutes": token.predicted_wait_minutes,
        "status":                 token.status,
        "registered_at":          token.registered_at,
    }

@app.get("/tokens")
def get_tokens(
    department_id: Optional[int]         = None,
    status:        Optional[TokenStatus] = None,
    doctor_id:     Optional[int]         = None,
    db:            Session               = Depends(get_db)
):
    q = db.query(QueueToken)
    if department_id: q = q.filter(QueueToken.department_id == department_id)
    if status:        q = q.filter(QueueToken.status == status)
    if doctor_id:     q = q.filter(QueueToken.doctor_id == doctor_id)
    tokens = q.order_by(QueueToken.registered_at).all()

    return [{
        "id":                     t.id,
        "token_number":           t.token_number,
        "status":                 t.status,
        "predicted_wait_minutes": t.predicted_wait_minutes,
        "actual_wait_minutes":    t.actual_wait_minutes,
        "patient_name":           t.patient.name if t.patient else "—",
        "patient_priority":       t.patient.priority.value if t.patient else "Normal",
        "department_name":        t.department.name if t.department else "—",
        "doctor_name":            t.doctor.name if t.doctor else "—",
        "doctor_id":              t.doctor_id,
        "registered_at":          t.registered_at,
        "called_at":              t.called_at,
        "completed_at":           t.completed_at,
    } for t in tokens]

@app.patch("/tokens/{token_id}/status")
def update_token_status(token_id: int, body: TokenStatusUpdate, db: Session = Depends(get_db)):
    token = db.query(QueueToken).filter(QueueToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.status = body.status
    if body.status == TokenStatus.called:
        token.called_at = datetime.utcnow()
    elif body.status == TokenStatus.completed:
        token.completed_at = datetime.utcnow()
        if token.registered_at:
            delta = datetime.utcnow() - token.registered_at
            token.actual_wait_minutes = round(delta.total_seconds() / 60, 1)
    db.commit()
    return {"message": "Status updated", "status": token.status}

@app.delete("/tokens/{token_id}")
def delete_token(token_id: int, db: Session = Depends(get_db)):
    token = db.query(QueueToken).filter(QueueToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(token)
    db.commit()
    return {"message": "Token deleted"}


# ── Routes: Stats ──────────────────────────────────────────────────────────────

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    total_today     = db.query(QueueToken).filter(func.date(QueueToken.registered_at) == today).count()
    waiting         = db.query(QueueToken).filter(QueueToken.status == TokenStatus.waiting).count()
    in_consult      = db.query(QueueToken).filter(QueueToken.status == TokenStatus.in_consult).count()
    completed_today = db.query(QueueToken).filter(QueueToken.status == TokenStatus.completed, func.date(QueueToken.registered_at) == today).count()
    avg_wait        = db.query(func.avg(QueueToken.actual_wait_minutes)).filter(
        QueueToken.actual_wait_minutes != None,
        func.date(QueueToken.registered_at) == today
    ).scalar()
    return {
        "total_today":     total_today,
        "waiting":         waiting,
        "in_consult":      in_consult,
        "completed_today": completed_today,
        "avg_actual_wait": round(avg_wait, 1) if avg_wait else None,
    }


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
