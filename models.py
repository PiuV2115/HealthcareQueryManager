"""
Hospital QMS - Database Models
SQLAlchemy ORM models mapped to PostgreSQL tables
"""

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, Boolean, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = "sqlite:///./qms.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ── Enums ──────────────────────────────────────────────────────────────────────

class TokenStatus(str, enum.Enum):
    waiting    = "waiting"
    called     = "called"
    in_consult = "in_consult"
    completed  = "completed"
    skipped    = "skipped"

class PatientPriority(str, enum.Enum):
    normal            = "Normal"
    senior_citizen    = "Senior Citizen"
    pregnant          = "Pregnant"
    differently_abled = "Differently Abled"
    emergency         = "Emergency"

class PatientType(str, enum.Enum):
    opd = "OPD"
    ipd = "IPD"


# ── Models ─────────────────────────────────────────────────────────────────────

class Department(Base):
    __tablename__ = "departments"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), unique=True, nullable=False)
    code       = Column(String(20),  unique=True, nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctors = relationship("Doctor",     back_populates="department")
    tokens  = relationship("QueueToken", back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(100), nullable=False)
    department_id       = Column(Integer, ForeignKey("departments.id"), nullable=False)
    is_available        = Column(Boolean, default=True)
    avg_consult_minutes = Column(Float, default=10.0)
    created_at          = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="doctors")
    tokens     = relationship("QueueToken", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False)
    phone        = Column(String(15),  nullable=True)
    age          = Column(Integer,     nullable=True)
    priority     = Column(Enum(PatientPriority), default=PatientPriority.normal)
    patient_type = Column(Enum(PatientType),     default=PatientType.opd)
    created_at   = Column(DateTime, default=datetime.utcnow)

    tokens = relationship("QueueToken", back_populates="patient")


class QueueToken(Base):
    __tablename__ = "queue_tokens"

    id                     = Column(Integer, primary_key=True, index=True)
    token_number           = Column(String(20), unique=True, nullable=False)
    patient_id             = Column(Integer, ForeignKey("patients.id"),    nullable=False)
    department_id          = Column(Integer, ForeignKey("departments.id"), nullable=False)
    doctor_id              = Column(Integer, ForeignKey("doctors.id"),     nullable=True)
    status                 = Column(Enum(TokenStatus), default=TokenStatus.waiting)
    predicted_wait_minutes = Column(Float,    nullable=True)
    actual_wait_minutes    = Column(Float,    nullable=True)
    registered_at          = Column(DateTime, default=datetime.utcnow)
    called_at              = Column(DateTime, nullable=True)
    completed_at           = Column(DateTime, nullable=True)
    notes                  = Column(Text,     nullable=True)

    patient    = relationship("Patient",    back_populates="tokens")
    department = relationship("Department", back_populates="tokens")
    doctor     = relationship("Doctor",     back_populates="tokens")


# ── DB Helpers ─────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables and seed default departments + doctors."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Department).count() == 0:
            departments = [
                Department(name="General OPD",  code="OPD-GEN"),
                Department(name="Cardiology",    code="OPD-CARD"),
                Department(name="Orthopedics",   code="OPD-ORTH"),
                Department(name="Pediatrics",    code="OPD-PED"),
                Department(name="Gynecology",    code="OPD-GYN"),
                Department(name="ENT",           code="OPD-ENT"),
                Department(name="Dermatology",   code="OPD-DERM"),
                Department(name="Emergency",     code="EMRG"),
            ]
            db.add_all(departments)
            db.commit()
            print("Departments seeded.")

        if db.query(Doctor).count() == 0:
            doctors = [
                Doctor(name="Dr. Sharma",   department_id=1, avg_consult_minutes=10.0),
                Doctor(name="Dr. Mehta",    department_id=2, avg_consult_minutes=15.0),
                Doctor(name="Dr. Kulkarni", department_id=3, avg_consult_minutes=12.0),
                Doctor(name="Dr. Patil",    department_id=4, avg_consult_minutes=8.0),
                Doctor(name="Dr. Joshi",    department_id=5, avg_consult_minutes=10.0),
            ]
            db.add_all(doctors)
            db.commit()
            print("Doctors seeded.")
    finally:
        db.close()


def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
