# Fix: Vercel vendors Pydantic v1 which is incompatible with Python 3.12.
# Pydantic v1 calls ForwardRef._evaluate(globalns, localns, set())
# but Python 3.12 changed the signature to require recursive_guard as keyword-only.
# This patch bridges the two calling conventions.
import typing
import sys

_orig_evaluate = typing.ForwardRef._evaluate

def _patched_evaluate(self, globalns, localns, *args, **kwargs):
    try:
        return _orig_evaluate(self, globalns, localns, *args, **kwargs)
    except TypeError:
        # Python 3.12+: _evaluate(globalns, localns, type_params, *, recursive_guard)
        # Pydantic v1 passes: _evaluate(globalns, localns, recursive_guard_set)
        return _orig_evaluate(
            self, globalns, localns,
            type_params=(),
            recursive_guard=args[0] if args else frozenset(),
        )

typing.ForwardRef._evaluate = _patched_evaluate

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
import calendar
import os
import sys
from pathlib import Path

# Add parent directory to path (for imports and static files)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# -------------------- Database Setup --------------------
# Use Supabase PostgreSQL if DATABASE_URL is set (production/Vercel),
# otherwise fall back to local SQLite for development.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Supabase provides postgresql:// URLs; SQLAlchemy 2.x needs postgresql+psycopg2://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    from sqlalchemy.pool import NullPool
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,  # NullPool is best for serverless (no persistent connections)
        pool_pre_ping=True,
    )
else:
    # Local development fallback with SQLite
    SQLITE_URL = f"sqlite:///{BASE_DIR / 'checklist.db'}"
    engine = create_engine(
        SQLITE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# -------------------- Models --------------------
class DailyChecklist(Base):
    __tablename__ = "daily_checklist"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today(), unique=True)
    # Daily tasks
    gym = Column(Boolean, default=False)
    dsa = Column(Boolean, default=False)
    ml = Column(Boolean, default=False)
    # Weekly tasks
    django = Column(Boolean, default=False)
    sql = Column(Boolean, default=False)
    project_work = Column(Boolean, default=False)
    aws = Column(Boolean, default=False)

class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    week_number = Column(Integer)
    year = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    # Daily task percentages
    gym_percentage = Column(Float, default=0.0)
    dsa_percentage = Column(Float, default=0.0)
    ml_percentage = Column(Float, default=0.0)
    # Weekly task percentages
    django_percentage = Column(Float, default=0.0)
    sql_percentage = Column(Float, default=0.0)
    project_percentage = Column(Float, default=0.0)
    aws_percentage = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)

class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer)
    year = Column(Integer)
    avg_gym = Column(Float, default=0.0)
    avg_dsa = Column(Float, default=0.0)
    avg_ml = Column(Float, default=0.0)
    avg_django = Column(Float, default=0.0)
    avg_sql = Column(Float, default=0.0)
    avg_project = Column(Float, default=0.0)
    avg_aws = Column(Float, default=0.0)
    total_days_tracked = Column(Integer, default=0)

# Tables will be created lazily on first request (not at import time)
_tables_created = False

def ensure_tables():
    global _tables_created
    if not _tables_created:
        try:
            Base.metadata.create_all(bind=engine)
            _tables_created = True
        except Exception as e:
            print(f"Warning: Could not create tables: {e}")

# Dependency
def get_db():
    ensure_tables()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- Pydantic Schemas --------------------
from pydantic import BaseModel
from typing import Optional
from datetime import date as dt_date

class DailyChecklistCreate(BaseModel):
    date: Optional[str] = None
    gym: bool = False
    dsa: bool = False
    ml: bool = False
    django: bool = False
    sql: bool = False
    project_work: bool = False
    aws: bool = False

class DailyChecklistResponse(BaseModel):
    id: int
    date: dt_date
    gym: bool
    dsa: bool
    ml: bool
    django: bool
    sql: bool
    project_work: bool
    aws: bool
    
    class Config:
        orm_mode = True
        json_encoders = {
            dt_date: lambda v: v.isoformat()
        }

class WeeklyReportResponse(BaseModel):
    id: int
    week_number: int
    year: int
    start_date: dt_date
    end_date: dt_date
    gym_percentage: float
    dsa_percentage: float
    ml_percentage: float
    django_percentage: float
    sql_percentage: float
    project_percentage: float
    aws_percentage: float
    total_score: float
    
    class Config:
        orm_mode = True
        json_encoders = {
            dt_date: lambda v: v.isoformat()
        }

class MonthlyReportResponse(BaseModel):
    id: int
    month: int
    year: int
    avg_gym: float
    avg_dsa: float
    avg_ml: float
    avg_django: float
    avg_sql: float
    avg_project: float
    avg_aws: float
    total_days_tracked: int
    
    class Config:
        orm_mode = True

# -------------------- FastAPI App --------------------
app = FastAPI(title="Personal Checklist API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = BASE_DIR / "static"

# -------------------- Helper Functions --------------------
def get_week_number(date_obj):
    return date_obj.isocalendar()[1]

def get_week_range(date_obj):
    start = date_obj - datetime.timedelta(days=date_obj.weekday())
    end = start + datetime.timedelta(days=6)
    return start, end

def generate_weekly_report(db: Session, date_obj: datetime.date):
    week_number = get_week_number(date_obj)
    year = date_obj.year
    week_start, week_end = get_week_range(date_obj)

    existing = db.query(WeeklyReport).filter(
        WeeklyReport.week_number == week_number,
        WeeklyReport.year == year
    ).first()
    if existing:
        return existing

    entries = db.query(DailyChecklist).filter(
        DailyChecklist.date >= week_start,
        DailyChecklist.date <= week_end
    ).all()
    if not entries:
        return None

    total_days = len(entries)
    counts = {
        'gym': sum(1 for e in entries if e.gym),
        'dsa': sum(1 for e in entries if e.dsa),
        'ml': sum(1 for e in entries if e.ml),
        'django': sum(1 for e in entries if e.django),
        'sql': sum(1 for e in entries if e.sql),
        'project': sum(1 for e in entries if e.project_work),
        'aws': sum(1 for e in entries if e.aws)
    }

    percentages = {k: (v / total_days) * 100 for k, v in counts.items()}

    # Overall score = average of all 7 tasks
    total_score = sum(percentages.values()) / 7

    report = WeeklyReport(
        week_number=week_number,
        year=year,
        start_date=week_start,
        end_date=week_end,
        gym_percentage=percentages['gym'],
        dsa_percentage=percentages['dsa'],
        ml_percentage=percentages['ml'],
        django_percentage=percentages['django'],
        sql_percentage=percentages['sql'],
        project_percentage=percentages['project'],
        aws_percentage=percentages['aws'],
        total_score=total_score
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

def generate_monthly_report(db: Session, year: int, month: int):
    existing = db.query(MonthlyReport).filter(
        MonthlyReport.month == month,
        MonthlyReport.year == year
    ).first()
    if existing:
        return existing

    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(year, month, calendar.monthrange(year, month)[1])
    entries = db.query(DailyChecklist).filter(
        DailyChecklist.date >= first_day,
        DailyChecklist.date <= last_day
    ).all()
    if not entries:
        return None

    total_days = len(entries)
    counts = {
        'gym': sum(1 for e in entries if e.gym),
        'dsa': sum(1 for e in entries if e.dsa),
        'ml': sum(1 for e in entries if e.ml),
        'django': sum(1 for e in entries if e.django),
        'sql': sum(1 for e in entries if e.sql),
        'project': sum(1 for e in entries if e.project_work),
        'aws': sum(1 for e in entries if e.aws)
    }

    monthly = MonthlyReport(
        month=month,
        year=year,
        avg_gym=(counts['gym'] / total_days) * 100,
        avg_dsa=(counts['dsa'] / total_days) * 100,
        avg_ml=(counts['ml'] / total_days) * 100,
        avg_django=(counts['django'] / total_days) * 100,
        avg_sql=(counts['sql'] / total_days) * 100,
        avg_project=(counts['project'] / total_days) * 100,
        avg_aws=(counts['aws'] / total_days) * 100,
        total_days_tracked=total_days
    )
    db.add(monthly)
    db.commit()
    db.refresh(monthly)
    return monthly

# -------------------- API Endpoints --------------------
@app.post("/api/daily/", response_model=DailyChecklistResponse)
async def create_daily_checklist(
    checklist: DailyChecklistCreate,
    db: Session = Depends(get_db)
):
    if checklist.date:
        try:
            date_obj = datetime.datetime.strptime(checklist.date, "%Y-%m-%d").date()
        except ValueError:
            date_obj = datetime.date.today()
    else:
        date_obj = datetime.date.today()

    existing = db.query(DailyChecklist).filter(DailyChecklist.date == date_obj).first()
    if existing:
        raise HTTPException(status_code=400, detail="Entry already exists for this date. Cannot edit previous entries.")

    db_checklist = DailyChecklist(
        date=date_obj,
        gym=checklist.gym,
        dsa=checklist.dsa,
        ml=checklist.ml,
        django=checklist.django,
        sql=checklist.sql,
        project_work=checklist.project_work,
        aws=checklist.aws
    )
    db.add(db_checklist)
    db.commit()
    db.refresh(db_checklist)

    generate_weekly_report(db, date_obj)
    return db_checklist

@app.get("/api/daily/", response_model=List[DailyChecklistResponse])
async def get_daily_checklist(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(DailyChecklist)
    if start_date:
        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(DailyChecklist.date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(DailyChecklist.date <= end)
        except ValueError:
            pass
    return query.order_by(DailyChecklist.date.desc()).all()

@app.get("/api/daily/{date}", response_model=DailyChecklistResponse)
async def get_daily_by_date(date: str, db: Session = Depends(get_db)):
    try:
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    checklist = db.query(DailyChecklist).filter(DailyChecklist.date == date_obj).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found for this date")
    return checklist

@app.get("/api/today")
async def get_today_checklist(db: Session = Depends(get_db)):
    today = datetime.date.today()
    checklist = db.query(DailyChecklist).filter(DailyChecklist.date == today).first()
    if not checklist:
        return {
            "date": today.isoformat(),
            "gym": False,
            "dsa": False,
            "ml": False,
            "django": False,
            "sql": False,
            "project_work": False,
            "aws": False,
            "exists": False
        }
    return {
        "date": checklist.date.isoformat(),
        "gym": checklist.gym,
        "dsa": checklist.dsa,
        "ml": checklist.ml,
        "django": checklist.django,
        "sql": checklist.sql,
        "project_work": checklist.project_work,
        "aws": checklist.aws,
        "exists": True
    }

@app.get("/api/weekly/", response_model=List[WeeklyReportResponse])
async def get_weekly_reports(
    week: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(WeeklyReport)
    if year:
        query = query.filter(WeeklyReport.year == year)
    if week:
        query = query.filter(WeeklyReport.week_number == week)
    reports = query.order_by(WeeklyReport.year.desc(), WeeklyReport.week_number.desc()).all()

    if not reports and not week and not year:
        dates = db.query(DailyChecklist.date).distinct().all()
        for (d,) in dates:
            generate_weekly_report(db, d)
        reports = query.order_by(WeeklyReport.year.desc(), WeeklyReport.week_number.desc()).all()
    return reports

@app.get("/api/weekly/generate/{date}")
async def generate_weekly_report_manual(date: str, db: Session = Depends(get_db)):
    try:
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    return generate_weekly_report(db, date_obj)

@app.get("/api/monthly/", response_model=List[MonthlyReportResponse])
async def get_monthly_reports(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MonthlyReport)
    if year:
        query = query.filter(MonthlyReport.year == year)
    if month:
        query = query.filter(MonthlyReport.month == month)
    reports = query.order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc()).all()

    if not reports and not month and not year:
        dates = db.query(DailyChecklist.date).distinct().all()
        months = set((d.year, d.month) for (d,) in dates)
        for y, m in months:
            generate_monthly_report(db, y, m)
        reports = query.order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc()).all()
    return reports

@app.get("/api/stats/")
async def get_statistics(db: Session = Depends(get_db)):
    total_days = db.query(DailyChecklist).count()
    total_weeks = db.query(WeeklyReport).count()
    total_months = db.query(MonthlyReport).count()

    latest_daily = db.query(DailyChecklist).order_by(DailyChecklist.date.desc()).first()
    latest_weekly = db.query(WeeklyReport).order_by(WeeklyReport.year.desc(), WeeklyReport.week_number.desc()).first()
    latest_monthly = db.query(MonthlyReport).order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc()).first()

    today = datetime.date.today()
    week_start, week_end = get_week_range(today)
    week_entries = db.query(DailyChecklist).filter(
        DailyChecklist.date >= week_start,
        DailyChecklist.date <= today
    ).all()

    week_progress = {
        "days_this_week": len(week_entries),
        "gym_count": sum(1 for e in week_entries if e.gym),
        "dsa_count": sum(1 for e in week_entries if e.dsa),
        "ml_count": sum(1 for e in week_entries if e.ml),
        "django_count": sum(1 for e in week_entries if e.django),
        "sql_count": sum(1 for e in week_entries if e.sql),
        "project_count": sum(1 for e in week_entries if e.project_work),
        "aws_count": sum(1 for e in week_entries if e.aws),
    }

    return {
        "total_days_tracked": total_days,
        "total_weeks_reported": total_weeks,
        "total_months_reported": total_months,
        "latest_daily": latest_daily.date.isoformat() if latest_daily else None,
        "latest_weekly_score": latest_weekly.total_score if latest_weekly else None,
        "latest_monthly_avg": latest_monthly.avg_gym if latest_monthly else None,
        "current_week_progress": week_progress,
        "today": today.isoformat()
    }

# -------------------- Static File Serving --------------------
@app.get("/app")
async def serve_frontend():
    html_path = STATIC_DIR / "index.html"
    return FileResponse(str(html_path))

@app.get("/")
async def root():
    # Redirect to the app frontend
    html_path = STATIC_DIR / "index.html"
    return FileResponse(str(html_path))

# Catch-all to serve static files (must be last)
@app.get("/{path:path}")
async def serve_static(path: str):
    # Try to serve from static directory
    static_path = STATIC_DIR / path
    if static_path.exists() and static_path.is_file():
        return FileResponse(str(static_path))
    # Also try with 'static/' prefix stripped
    if path.startswith("static/"):
        stripped_path = STATIC_DIR / path[7:]
        if stripped_path.exists() and stripped_path.is_file():
            return FileResponse(str(stripped_path))
    raise HTTPException(status_code=404, detail="File not found")
