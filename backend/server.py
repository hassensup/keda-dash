from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, select
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import json
import uuid
import bcrypt
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

# ============ DATABASE ============
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT_DIR}/keda_dashboard.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ============ ORM MODELS ============
class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScaledObjectModel(Base):
    __tablename__ = "scaled_objects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    namespace = Column(String, nullable=False, default="default")
    scaler_type = Column(String, nullable=False)
    target_deployment = Column(String, nullable=False)
    min_replicas = Column(Integer, default=0)
    max_replicas = Column(Integer, default=10)
    cooldown_period = Column(Integer, default=300)
    polling_interval = Column(Integer, default=30)
    triggers_json = Column(Text, default="[]")
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    cron_events = relationship("CronEventModel", back_populates="scaled_object", cascade="all, delete-orphan")


class CronEventModel(Base):
    __tablename__ = "cron_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scaled_object_id = Column(String, ForeignKey("scaled_objects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    timezone_str = Column(String, default="UTC")
    desired_replicas = Column(Integer, default=1)
    event_date = Column(String, nullable=False)
    start_time = Column(String, default="00:00")
    end_time = Column(String, default="23:59")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scaled_object = relationship("ScaledObjectModel", back_populates="cron_events")


# ============ PYDANTIC SCHEMAS ============
class LoginRequest(BaseModel):
    email: str
    password: str


class ScaledObjectCreate(BaseModel):
    name: str
    namespace: str = "default"
    scaler_type: str
    target_deployment: str
    min_replicas: int = 0
    max_replicas: int = 10
    cooldown_period: int = 300
    polling_interval: int = 30
    triggers: list = []


class ScaledObjectUpdate(BaseModel):
    name: Optional[str] = None
    namespace: Optional[str] = None
    scaler_type: Optional[str] = None
    target_deployment: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    cooldown_period: Optional[int] = None
    polling_interval: Optional[int] = None
    triggers: Optional[list] = None
    status: Optional[str] = None


class CronEventCreate(BaseModel):
    scaled_object_id: str
    name: str
    timezone_str: str = "UTC"
    desired_replicas: int = 1
    event_date: str
    start_time: str = "00:00"
    end_time: str = "23:59"


class CronEventUpdate(BaseModel):
    name: Optional[str] = None
    timezone_str: Optional[str] = None
    desired_replicas: Optional[int] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    scaled_object_id: Optional[str] = None


# ============ AUTH UTILITIES ============
JWT_ALGORITHM = "HS256"


def get_jwt_secret():
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "type": "access"
    }
    return pyjwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = pyjwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return {"id": payload["sub"], "email": payload["email"]}
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============ HELPERS ============
def so_to_dict(obj):
    return {
        "id": obj.id,
        "name": obj.name,
        "namespace": obj.namespace,
        "scaler_type": obj.scaler_type,
        "target_deployment": obj.target_deployment,
        "min_replicas": obj.min_replicas,
        "max_replicas": obj.max_replicas,
        "cooldown_period": obj.cooldown_period,
        "polling_interval": obj.polling_interval,
        "triggers": json.loads(obj.triggers_json) if obj.triggers_json else [],
        "status": obj.status,
        "created_at": obj.created_at.isoformat() if obj.created_at else "",
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else "",
    }


def event_to_dict(e, so_name="Unknown"):
    return {
        "id": e.id,
        "scaled_object_id": e.scaled_object_id,
        "name": e.name,
        "timezone_str": e.timezone_str,
        "desired_replicas": e.desired_replicas,
        "event_date": e.event_date,
        "start_time": e.start_time,
        "end_time": e.end_time,
        "scaled_object_name": so_name,
        "created_at": e.created_at.isoformat() if e.created_at else "",
        "updated_at": e.updated_at.isoformat() if e.updated_at else "",
    }


# ============ SEED DATA ============
async def seed_data():
    async with async_session_maker() as session:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        result = await session.execute(select(UserModel).where(UserModel.email == admin_email))
        existing = result.scalar_one_or_none()
        if not existing:
            session.add(UserModel(
                email=admin_email,
                password_hash=hash_password(admin_password),
                name="Admin",
                role="admin"
            ))
        elif not verify_password(admin_password, existing.password_hash):
            existing.password_hash = hash_password(admin_password)

        result = await session.execute(select(ScaledObjectModel))
        if not result.scalars().first():
            examples = [
                ScaledObjectModel(
                    name="web-app-scaler", namespace="production", scaler_type="cron",
                    target_deployment="web-app", min_replicas=2, max_replicas=20,
                    triggers_json=json.dumps([{"type": "cron", "metadata": {"timezone": "Europe/Paris", "start": "0 8 * * 1-5", "end": "0 20 * * 1-5", "desiredReplicas": "10"}}])
                ),
                ScaledObjectModel(
                    name="api-gateway-scaler", namespace="production", scaler_type="prometheus",
                    target_deployment="api-gateway", min_replicas=3, max_replicas=50,
                    triggers_json=json.dumps([{"type": "prometheus", "metadata": {"serverAddress": "http://prometheus:9090", "metricName": "http_requests_total", "threshold": "100"}}])
                ),
                ScaledObjectModel(
                    name="worker-scaler", namespace="staging", scaler_type="rabbitmq",
                    target_deployment="worker", min_replicas=0, max_replicas=30,
                    triggers_json=json.dumps([{"type": "rabbitmq", "metadata": {"queueName": "tasks", "host": "amqp://rabbitmq:5672", "queueLength": "50"}}])
                ),
                ScaledObjectModel(
                    name="batch-processor-scaler", namespace="default", scaler_type="kafka",
                    target_deployment="batch-processor", min_replicas=1, max_replicas=15,
                    triggers_json=json.dumps([{"type": "kafka", "metadata": {"bootstrapServers": "kafka:9092", "consumerGroup": "batch-group", "topic": "events", "lagThreshold": "10"}}])
                ),
                ScaledObjectModel(
                    name="ml-inference-scaler", namespace="ml", scaler_type="cpu",
                    target_deployment="ml-inference", min_replicas=2, max_replicas=10,
                    triggers_json=json.dumps([{"type": "cpu", "metadata": {"type": "Utilization", "value": "60"}}])
                ),
                ScaledObjectModel(
                    name="cache-scaler", namespace="production", scaler_type="redis",
                    target_deployment="cache-service", min_replicas=1, max_replicas=8,
                    triggers_json=json.dumps([{"type": "redis", "metadata": {"address": "redis:6379", "listName": "jobs", "listLength": "20"}}])
                ),
            ]
            session.add_all(examples)
        await session.commit()

        # Seed cron events
        result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.scaler_type == "cron"))
        cron_so = result.scalar_one_or_none()
        if cron_so:
            result = await session.execute(select(CronEventModel))
            if not result.scalars().first():
                from datetime import date
                today = date.today()
                events = [
                    CronEventModel(scaled_object_id=cron_so.id, name="Business Hours Scale Up",
                                   timezone_str="Europe/Paris", desired_replicas=10,
                                   event_date=today.isoformat(), start_time="08:00", end_time="20:00"),
                    CronEventModel(scaled_object_id=cron_so.id, name="Weekend Maintenance",
                                   timezone_str="Europe/Paris", desired_replicas=2,
                                   event_date=(today + timedelta(days=2)).isoformat(), start_time="02:00", end_time="06:00"),
                    CronEventModel(scaled_object_id=cron_so.id, name="Peak Traffic Prep",
                                   timezone_str="Europe/Paris", desired_replicas=15,
                                   event_date=(today + timedelta(days=5)).isoformat(), start_time="07:00", end_time="22:00"),
                    CronEventModel(scaled_object_id=cron_so.id, name="Nightly Batch Scale",
                                   timezone_str="UTC", desired_replicas=5,
                                   event_date=(today + timedelta(days=1)).isoformat(), start_time="01:00", end_time="05:00"),
                ]
                session.add_all(events)
                await session.commit()

        os.makedirs("/app/memory", exist_ok=True)
        with open("/app/memory/test_credentials.md", "w") as f:
            f.write(f"# Test Credentials\n\n## Admin\n- Email: {admin_email}\n- Password: {admin_password}\n- Role: admin\n\n")
            f.write("## Auth Endpoints\n- POST /api/auth/login\n- POST /api/auth/logout\n- GET /api/auth/me\n")


# ============ APP LIFECYCLE ============
@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    logger.info("Database initialized and seeded")
    yield
    await engine.dispose()


# ============ APP SETUP ============
app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============ AUTH ROUTES ============
@api_router.post("/auth/login")
async def login(req: LoginRequest, response: Response):
    async with async_session_maker() as session:
        result = await session.execute(select(UserModel).where(UserModel.email == req.email.lower()))
        user = result.scalar_one_or_none()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(user.id, user.email)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=False, samesite="lax", max_age=86400, path="/")
        return {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "token": token}


@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(UserModel).where(UserModel.id == current_user["id"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out"}


# ============ SCALED OBJECT ROUTES ============
@api_router.get("/scaled-objects")
async def list_scaled_objects(namespace: Optional[str] = None, scaler_type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        query = select(ScaledObjectModel)
        if namespace:
            query = query.where(ScaledObjectModel.namespace == namespace)
        if scaler_type:
            query = query.where(ScaledObjectModel.scaler_type == scaler_type)
        result = await session.execute(query.order_by(ScaledObjectModel.name))
        return [so_to_dict(obj) for obj in result.scalars().all()]


@api_router.post("/scaled-objects")
async def create_scaled_object(data: ScaledObjectCreate, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        obj = ScaledObjectModel(
            name=data.name, namespace=data.namespace, scaler_type=data.scaler_type,
            target_deployment=data.target_deployment, min_replicas=data.min_replicas,
            max_replicas=data.max_replicas, cooldown_period=data.cooldown_period,
            polling_interval=data.polling_interval, triggers_json=json.dumps(data.triggers),
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return so_to_dict(obj)


@api_router.get("/scaled-objects/{obj_id}")
async def get_scaled_object(obj_id: str, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id == obj_id))
        obj = result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="ScaledObject not found")
        return so_to_dict(obj)


@api_router.put("/scaled-objects/{obj_id}")
async def update_scaled_object(obj_id: str, data: ScaledObjectUpdate, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id == obj_id))
        obj = result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="ScaledObject not found")
        update_data = data.model_dump(exclude_unset=True)
        if "triggers" in update_data:
            update_data["triggers_json"] = json.dumps(update_data.pop("triggers"))
        update_data["updated_at"] = datetime.now(timezone.utc)
        for key, value in update_data.items():
            setattr(obj, key, value)
        await session.commit()
        await session.refresh(obj)
        return so_to_dict(obj)


@api_router.delete("/scaled-objects/{obj_id}")
async def delete_scaled_object(obj_id: str, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id == obj_id))
        obj = result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="ScaledObject not found")
        await session.delete(obj)
        await session.commit()
        return {"message": "Deleted"}


# ============ CRON EVENT ROUTES ============
@api_router.get("/cron-events")
async def list_cron_events(scaled_object_id: Optional[str] = None, month: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        query = select(CronEventModel)
        if scaled_object_id:
            query = query.where(CronEventModel.scaled_object_id == scaled_object_id)
        if month:
            query = query.where(CronEventModel.event_date.like(f"{month}%"))
        result = await session.execute(query.order_by(CronEventModel.event_date))
        events = result.scalars().all()
        so_ids = {e.scaled_object_id for e in events}
        so_names = {}
        if so_ids:
            so_result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id.in_(so_ids)))
            for so in so_result.scalars().all():
                so_names[so.id] = so.name
        return [event_to_dict(e, so_names.get(e.scaled_object_id, "Unknown")) for e in events]


@api_router.post("/cron-events")
async def create_cron_event(data: CronEventCreate, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id == data.scaled_object_id))
        so = result.scalar_one_or_none()
        if not so:
            raise HTTPException(status_code=404, detail="ScaledObject not found")
        event = CronEventModel(
            scaled_object_id=data.scaled_object_id, name=data.name, timezone_str=data.timezone_str,
            desired_replicas=data.desired_replicas, event_date=data.event_date,
            start_time=data.start_time, end_time=data.end_time,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event_to_dict(event, so.name)


@api_router.put("/cron-events/{event_id}")
async def update_cron_event(event_id: str, data: CronEventUpdate, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(CronEventModel).where(CronEventModel.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="CronEvent not found")
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)
        for key, value in update_data.items():
            setattr(event, key, value)
        await session.commit()
        await session.refresh(event)
        so_result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id == event.scaled_object_id))
        so = so_result.scalar_one_or_none()
        return event_to_dict(event, so.name if so else "Unknown")


@api_router.delete("/cron-events/{event_id}")
async def delete_cron_event(event_id: str, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(CronEventModel).where(CronEventModel.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="CronEvent not found")
        await session.delete(event)
        await session.commit()
        return {"message": "Deleted"}


# ============ NAMESPACE ROUTES ============
@api_router.get("/namespaces")
async def list_namespaces(current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(ScaledObjectModel.namespace).distinct())
        return [row[0] for row in result.all()]


# ============ SCALER TYPES ============
@api_router.get("/scaler-types")
async def list_scaler_types(current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(ScaledObjectModel.scaler_type).distinct())
        return [row[0] for row in result.all()]


# ============ HEALTH ============
@api_router.get("/health")
async def health():
    return {"status": "ok"}


# ============ INCLUDE ROUTER + MIDDLEWARE ============
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
