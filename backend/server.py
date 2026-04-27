from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
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
from k8s_service import create_k8s_service, K8sScaledObjectService

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
    created_at = Column(DateTime, default=lambda: datetime.now())


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
    scaling_behavior_json = Column(Text, default=None, nullable=True)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now())
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
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now())
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
    scaling_behavior: Optional[dict] = None


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
    scaling_behavior: Optional[dict] = None
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
    scaling_behavior = None
    if obj.scaling_behavior_json:
        try:
            scaling_behavior = json.loads(obj.scaling_behavior_json)
        except:
            scaling_behavior = None
    
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
        "scaling_behavior": scaling_behavior,
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


# ============ K8S SERVICE ============
k8s_service: K8sScaledObjectService = None


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
        cron_so = result.scalars().first()
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
    global k8s_service
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Migration: Add scaling_behavior_json column if it doesn't exist
    async with engine.begin() as conn:
        def add_column_if_not_exists(connection):
            from sqlalchemy import inspect, text
            inspector = inspect(connection)
            columns = [col['name'] for col in inspector.get_columns('scaled_objects')]
            if 'scaling_behavior_json' not in columns:
                logger.info("Adding scaling_behavior_json column to scaled_objects table")
                # Detect database type
                dialect_name = connection.dialect.name
                if dialect_name == 'postgresql':
                    connection.execute(text(
                        "ALTER TABLE scaled_objects ADD COLUMN scaling_behavior_json TEXT"
                    ))
                elif dialect_name == 'sqlite':
                    connection.execute(text(
                        "ALTER TABLE scaled_objects ADD COLUMN scaling_behavior_json TEXT"
                    ))
                logger.info("Column scaling_behavior_json added successfully")
        
        await conn.run_sync(add_column_if_not_exists)
    
    await seed_data()

    # Initialize K8s service
    k8s_service = create_k8s_service(
        session_maker=async_session_maker,
        models={"ScaledObjectModel": ScaledObjectModel, "select": select}
    )
    logger.info(f"K8s service initialized: mode={k8s_service.get_mode()}, connected={k8s_service.is_connected()}")

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


# ============ SCALED OBJECT ROUTES (via K8s Service) ============
@api_router.get("/scaled-objects")
async def list_scaled_objects(namespace: Optional[str] = None, scaler_type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    try:
        return await k8s_service.list_objects(namespace=namespace, scaler_type=scaler_type)
    except Exception as e:
        logger.error(f"Failed to list ScaledObjects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list ScaledObjects: {str(e)}")


@api_router.post("/scaled-objects")
async def create_scaled_object(data: ScaledObjectCreate, current_user: dict = Depends(get_current_user)):
    try:
        data_dict = data.model_dump()
        logger.info(f"Creating ScaledObject with data: {json.dumps(data_dict, indent=2)}")
        result = await k8s_service.create_object(data_dict)
        return result
    except Exception as e:
        logger.error(f"Failed to create ScaledObject: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ScaledObject: {str(e)}")


@api_router.get("/scaled-objects/{obj_id:path}")
async def get_scaled_object(obj_id: str, current_user: dict = Depends(get_current_user)):
    result = await k8s_service.get_object(obj_id)
    if not result:
        raise HTTPException(status_code=404, detail="ScaledObject not found")
    return result


@api_router.put("/scaled-objects/{obj_id:path}")
async def update_scaled_object(obj_id: str, data: ScaledObjectUpdate, current_user: dict = Depends(get_current_user)):
    # First, let's see what Pydantic gives us
    update_data_unset = data.model_dump(exclude_unset=True)
    update_data_all = data.model_dump(exclude_unset=False)
    
    logger.info(f"Pydantic model_dump(exclude_unset=True): {json.dumps(update_data_unset, indent=2)}")
    logger.info(f"Pydantic model_dump(exclude_unset=False): {json.dumps(update_data_all, indent=2)}")
    
    # Use the one that includes all fields
    update_data = update_data_all
    
    logger.info(f"Updating ScaledObject {obj_id} with data: {json.dumps(update_data, indent=2)}")
    logger.info(f"Keys in update_data: {list(update_data.keys())}")
    logger.info(f"'scaling_behavior' in update_data: {'scaling_behavior' in update_data}")
    if 'scaling_behavior' in update_data:
        logger.info(f"scaling_behavior value: {update_data['scaling_behavior']}")
    
    try:
        result = await k8s_service.update_object(obj_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="ScaledObject not found")
        logger.info(f"Updated ScaledObject result: {json.dumps(result, indent=2)}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update ScaledObject: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update ScaledObject: {str(e)}")


@api_router.delete("/scaled-objects/{obj_id:path}")
async def delete_scaled_object(obj_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = await k8s_service.delete_object(obj_id)
        if not result:
            raise HTTPException(status_code=404, detail="ScaledObject not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete ScaledObject: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete ScaledObject: {str(e)}")


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
        # Use the k8s_service to resolve the object, as it handles both UUID and namespace/name formats consistently
        so_dict = await k8s_service.get_object(data.scaled_object_id)

        if not so_dict:
            # FALLBACK: If k8s_service fails, try a direct database lookup by name/namespace
            if "/" in data.scaled_object_id:
                ns, name = data.scaled_object_id.split("/", 1)
                result = await session.execute(
                    select(ScaledObjectModel).where(
                        ScaledObjectModel.name == name,
                        ScaledObjectModel.namespace == ns
                    )
                )
                db_so = result.scalar_one_or_none()
                if db_so:
                    so_dict = so_to_dict(db_so)
            else:
                result = await session.execute(select(ScaledObjectModel).where(ScaledObjectModel.id == data.scaled_object_id))
                db_so = result.scalar_one_or_none()
                if db_so:
                    so_dict = so_to_dict(db_so)

        if not so_dict:
            logger.error(f"ScaledObject not found for ID: {data.scaled_object_id}")
            raise HTTPException(status_code=404, detail=f"ScaledObject not found: {data.scaled_object_id}")

        # Normalize the ID to a UUID for the database foreign key
        so_id_to_store = so_dict["id"]
        if "/" in so_id_to_store:
            ns, name = so_id_to_store.split("/", 1)
            result = await session.execute(
                select(ScaledObjectModel).where(
                    ScaledObjectModel.name == name,
                    ScaledObjectModel.namespace == ns
                )
            )
            db_so = result.scalar_one_or_none()
            if db_so:
                so_id_to_store = db_so.id

        event = CronEventModel(
            scaled_object_id=so_id_to_store, name=data.name, timezone_str=data.timezone_str,
            desired_replicas=data.desired_replicas, event_date=data.event_date,
            start_time=data.start_time, end_time=data.end_time,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event_to_dict(event, so_dict["name"])


@api_router.put("/cron-events/{event_id}")
async def update_cron_event(event_id: str, data: CronEventUpdate, current_user: dict = Depends(get_current_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(CronEventModel).where(CronEventModel.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="CronEvent not found")
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
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


# ============ NAMESPACE ROUTES (via K8s Service) ============
@api_router.get("/namespaces")
async def list_namespaces(current_user: dict = Depends(get_current_user)):
    try:
        return await k8s_service.list_namespaces()
    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ SCALER TYPES (via K8s Service) ============
@api_router.get("/scaler-types")
async def list_scaler_types(current_user: dict = Depends(get_current_user)):
    try:
        return await k8s_service.list_scaler_types()
    except Exception as e:
        logger.error(f"Failed to list scaler types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ DEPLOYMENTS (via K8s Service) ============
@api_router.get("/deployments")
async def list_deployments(namespace: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    try:
        return await k8s_service.list_deployments(namespace=namespace)
    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ K8S STATUS ============
@api_router.get("/k8s-status")
async def get_k8s_status(current_user: dict = Depends(get_current_user)):
    return {
        "mode": k8s_service.get_mode() if k8s_service else "unknown",
        "connected": k8s_service.is_connected() if k8s_service else False,
        "configured_mode": os.environ.get("K8S_MODE", "mock"),
    }


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

# ============ STATIC FILES FOR FRONTEND ============
# Mount static files from frontend build directory
frontend_build_path = ROOT_DIR.parent / "frontend" / "build"
if frontend_build_path.exists():
    # Custom StaticFiles class to serve index.html for SPA routes
    class SPAStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            try:
                return await super().get_response(path, scope)
            except HTTPException as exc:
                if exc.status_code == 404:
                    request_path = scope.get("path", "")
                    # Exclude API routes
                    if request_path.startswith("/api/"):
                        raise exc
                    # Exclude paths with file extensions (static assets)
                    if "." in request_path.split("/")[-1]:
                        raise exc
                    # Try to serve index.html for SPA routing
                    index_path = "index.html"
                    try:
                        return await super().get_response(index_path, scope)
                    except HTTPException:
                        # If index.html not found, return original 404
                        raise exc
                else:
                    raise

    app.mount("/", SPAStaticFiles(directory=str(frontend_build_path), html=True), name="frontend")
    logger.info(f"Serving frontend static files from: {frontend_build_path}")
else:
    logger.warning(f"Frontend build directory not found at: {frontend_build_path}. Frontend will not be served.")
