"""
Kubernetes service layer for KEDA ScaledObject management.

Provides two implementations:
- MockK8sService: Uses SQLite database (for development)
- RealK8sService: Uses kubernetes Python client with in-cluster config (for production)

The K8S_MODE environment variable controls which implementation is used.
Falls back to mock mode if K8s cluster is not available.
"""

import os
import json
import logging
import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

KEDA_GROUP = "keda.sh"
KEDA_VERSION = "v1alpha1"
KEDA_PLURAL = "scaledobjects"


class K8sScaledObjectService(ABC):
    """Abstract interface for ScaledObject management."""

    @abstractmethod
    async def list_objects(self, namespace=None, scaler_type=None) -> list:
        pass

    @abstractmethod
    async def get_object(self, obj_id: str) -> dict:
        pass

    @abstractmethod
    async def create_object(self, data: dict) -> dict:
        pass

    @abstractmethod
    async def update_object(self, obj_id: str, data: dict) -> dict:
        pass

    @abstractmethod
    async def delete_object(self, obj_id: str) -> dict:
        pass

    @abstractmethod
    async def list_namespaces(self) -> list:
        pass

    @abstractmethod
    async def list_scaler_types(self) -> list:
        pass

    @abstractmethod
    def get_mode(self) -> str:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass


class MockK8sService(K8sScaledObjectService):
    """Mock implementation using SQLAlchemy/SQLite database."""

    def __init__(self, session_maker, models):
        self._session_maker = session_maker
        self._ScaledObjectModel = models["ScaledObjectModel"]
        self._select = models["select"]

    def get_mode(self) -> str:
        return "mock"

    def is_connected(self) -> bool:
        return True

    async def list_objects(self, namespace=None, scaler_type=None) -> list:
        async with self._session_maker() as session:
            query = self._select(self._ScaledObjectModel)
            if namespace:
                query = query.where(self._ScaledObjectModel.namespace == namespace)
            if scaler_type:
                query = query.where(self._ScaledObjectModel.scaler_type == scaler_type)
            result = await session.execute(query.order_by(self._ScaledObjectModel.name))
            return [self._to_dict(obj) for obj in result.scalars().all()]

    async def get_object(self, obj_id: str) -> dict:
        async with self._session_maker() as session:
            result = await session.execute(
                self._select(self._ScaledObjectModel).where(self._ScaledObjectModel.id == obj_id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                return None
            return self._to_dict(obj)

    async def create_object(self, data: dict) -> dict:
        async with self._session_maker() as session:
            obj = self._ScaledObjectModel(
                name=data["name"], namespace=data.get("namespace", "default"),
                scaler_type=data["scaler_type"], target_deployment=data["target_deployment"],
                min_replicas=data.get("min_replicas", 0), max_replicas=data.get("max_replicas", 10),
                cooldown_period=data.get("cooldown_period", 300), polling_interval=data.get("polling_interval", 30),
                triggers_json=json.dumps(data.get("triggers", [])),
            )
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return self._to_dict(obj)

    async def update_object(self, obj_id: str, data: dict) -> dict:
        async with self._session_maker() as session:
            result = await session.execute(
                self._select(self._ScaledObjectModel).where(self._ScaledObjectModel.id == obj_id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                return None

            logger.info(f"Updating ScaledObject {obj_id} with data: {data}")

            if "triggers" in data:
                data["triggers_json"] = json.dumps(data.pop("triggers"))

            data["updated_at"] = datetime.now(timezone.utc)

            for key, value in data.items():
                if hasattr(obj, key):
                    logger.debug(f"Setting {key} = {value}")
                    setattr(obj, key, value)

            await session.commit()
            await session.refresh(obj)
            return self._to_dict(obj)

    async def delete_object(self, obj_id: str) -> dict:
        async with self._session_maker() as session:
            result = await session.execute(
                self._select(self._ScaledObjectModel).where(self._ScaledObjectModel.id == obj_id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                return None
            await session.delete(obj)
            await session.commit()
            return {"message": "Deleted", "name": obj.name}

    async def list_namespaces(self) -> list:
        async with self._session_maker() as session:
            result = await session.execute(
                self._select(self._ScaledObjectModel.namespace).distinct()
            )
            return [row[0] for row in result.all()]

    async def list_scaler_types(self) -> list:
        async with self._session_maker() as session:
            result = await session.execute(
                self._select(self._ScaledObjectModel.scaler_type).distinct()
            )
            return [row[0] for row in result.all()]

    def _to_dict(self, obj):
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


class RealK8sService(K8sScaledObjectService):
    """Real Kubernetes implementation using in-cluster or kubeconfig access."""

    def __init__(self):
        self._connected = False
        self._custom_api = None
        self._core_api = None
        self._init_client()

    def _init_client(self):
        try:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
                logger.info("K8s: Loaded in-cluster config")
            except config.ConfigException:
                try:
                    config.load_kube_config()
                    logger.info("K8s: Loaded kubeconfig")
                except config.ConfigException:
                    logger.warning("K8s: No config available, cannot connect")
                    return
            self._custom_api = client.CustomObjectsApi()
            self._core_api = client.CoreV1Api()
            self._connected = True
            logger.info("K8s: Client initialized successfully")
        except Exception as e:
            logger.error(f"K8s: Failed to initialize client: {e}")
            self._connected = False

    def get_mode(self) -> str:
        return "in-cluster"

    def is_connected(self) -> bool:
        return self._connected

    async def list_objects(self, namespace=None, scaler_type=None) -> list:
        def _list():
            if namespace:
                resp = self._custom_api.list_namespaced_custom_object(
                    group=KEDA_GROUP, version=KEDA_VERSION,
                    namespace=namespace, plural=KEDA_PLURAL
                )
            else:
                resp = self._custom_api.list_cluster_custom_object(
                    group=KEDA_GROUP, version=KEDA_VERSION, plural=KEDA_PLURAL
                )
            return resp.get("items", [])

        items = await asyncio.to_thread(_list)
        result = [self._crd_to_dict(item) for item in items]
        if scaler_type:
            result = [r for r in result if r["scaler_type"] == scaler_type]
        return sorted(result, key=lambda x: x["name"])

    async def get_object(self, obj_id: str) -> dict:
        ns, name = self._parse_id(obj_id)

        def _get():
            return self._custom_api.get_namespaced_custom_object(
                group=KEDA_GROUP, version=KEDA_VERSION,
                namespace=ns, plural=KEDA_PLURAL, name=name
            )

        try:
            item = await asyncio.to_thread(_get)
            return self._crd_to_dict(item)
        except Exception as e:
            logger.error(f"K8s: Failed to get ScaledObject {obj_id}: {e}")
            return None

    async def create_object(self, data: dict) -> dict:
        body = self._dict_to_crd(data)
        ns = data.get("namespace", "default")

        def _create():
            return self._custom_api.create_namespaced_custom_object(
                group=KEDA_GROUP, version=KEDA_VERSION,
                namespace=ns, plural=KEDA_PLURAL, body=body
            )

        result = await asyncio.to_thread(_create)
        return self._crd_to_dict(result)

    async def update_object(self, obj_id: str, data: dict) -> dict:
        ns, name = self._parse_id(obj_id)

        def _update():
            existing = self._custom_api.get_namespaced_custom_object(
                group=KEDA_GROUP, version=KEDA_VERSION,
                namespace=ns, plural=KEDA_PLURAL, name=name
            )
            spec = existing.get("spec", {})

            if "target_deployment" in data:
                spec["scaleTargetRef"] = {"name": data["target_deployment"]}
            if "min_replicas" in data:
                spec["minReplicaCount"] = data["min_replicas"]
            if "max_replicas" in data:
                spec["maxReplicaCount"] = data["max_replicas"]
            if "cooldown_period" in data:
                spec["cooldownPeriod"] = data["cooldown_period"]
            if "polling_interval" in data:
                spec["pollingInterval"] = data["polling_interval"]
            if "triggers" in data:
                spec["triggers"] = data["triggers"]

            existing["spec"] = spec

            # Handle name/namespace change via delete + recreate
            new_name = data.get("name", name)
            new_ns = data.get("namespace", ns)
            if new_name != name or new_ns != ns:
                self._custom_api.delete_namespaced_custom_object(
                    group=KEDA_GROUP, version=KEDA_VERSION,
                    namespace=ns, plural=KEDA_PLURAL, name=name
                )
                existing["metadata"]["name"] = new_name
                existing["metadata"]["namespace"] = new_ns
                existing["metadata"].pop("resourceVersion", None)
                existing["metadata"].pop("uid", None)
                return self._custom_api.create_namespaced_custom_object(
                    group=KEDA_GROUP, version=KEDA_VERSION,
                    namespace=new_ns, plural=KEDA_PLURAL, body=existing
                )
            else:
                return self._custom_api.replace_namespaced_custom_object(
                    group=KEDA_GROUP, version=KEDA_VERSION,
                    namespace=ns, plural=KEDA_PLURAL, name=name, body=existing
                )

        result = await asyncio.to_thread(_update)
        return self._crd_to_dict(result)

    async def delete_object(self, obj_id: str) -> dict:
        ns, name = self._parse_id(obj_id)

        def _delete():
            self._custom_api.delete_namespaced_custom_object(
                group=KEDA_GROUP, version=KEDA_VERSION,
                namespace=ns, plural=KEDA_PLURAL, name=name
            )

        await asyncio.to_thread(_delete)
        return {"message": "Deleted", "name": name}

    async def list_namespaces(self) -> list:
        def _list():
            resp = self._core_api.list_namespace()
            return [ns.metadata.name for ns in resp.items]

        return await asyncio.to_thread(_list)

    async def list_scaler_types(self) -> list:
        objects = await self.list_objects()
        types = set()
        for obj in objects:
            types.add(obj["scaler_type"])
        return sorted(list(types))

    @staticmethod
    def _parse_id(obj_id: str):
        """Parse 'namespace/name' ID format. Fallback to default ns."""
        if "/" in obj_id:
            parts = obj_id.split("/", 1)
            return parts[0], parts[1]
        return "default", obj_id

    @staticmethod
    def _crd_to_dict(crd: dict) -> dict:
        """Convert K8s CRD to our API dict format."""
        metadata = crd.get("metadata", {})
        spec = crd.get("spec", {})
        status = crd.get("status", {})

        triggers = spec.get("triggers", [])
        scaler_type = triggers[0]["type"] if triggers else "unknown"

        # Determine status from conditions
        conditions = status.get("conditions", [])
        is_ready = any(
            c.get("type") in ("Ready", "Active") and c.get("status") == "True"
            for c in conditions
        )
        is_paused = any(
            c.get("type") == "Paused" and c.get("status") == "True"
            for c in conditions
        )

        if is_paused:
            obj_status = "Paused"
        elif is_ready:
            obj_status = "Active"
        elif conditions:
            obj_status = "Error"
        else:
            obj_status = "Active"

        ns = metadata.get("namespace", "default")
        name = metadata.get("name", "")

        return {
            "id": f"{ns}/{name}",
            "name": name,
            "namespace": ns,
            "scaler_type": scaler_type,
            "target_deployment": spec.get("scaleTargetRef", {}).get("name", ""),
            "min_replicas": spec.get("minReplicaCount", 0),
            "max_replicas": spec.get("maxReplicaCount", 10),
            "cooldown_period": spec.get("cooldownPeriod", 300),
            "polling_interval": spec.get("pollingInterval", 30),
            "triggers": triggers,
            "status": obj_status,
            "created_at": metadata.get("creationTimestamp", ""),
            "updated_at": metadata.get("creationTimestamp", ""),
        }

    @staticmethod
    def _dict_to_crd(data: dict) -> dict:
        """Convert our API dict to K8s CRD format for create."""
        return {
            "apiVersion": f"{KEDA_GROUP}/{KEDA_VERSION}",
            "kind": "ScaledObject",
            "metadata": {
                "name": data["name"],
                "namespace": data.get("namespace", "default"),
            },
            "spec": {
                "scaleTargetRef": {
                    "name": data["target_deployment"],
                },
                "minReplicaCount": data.get("min_replicas", 0),
                "maxReplicaCount": data.get("max_replicas", 10),
                "cooldownPeriod": data.get("cooldown_period", 300),
                "pollingInterval": data.get("polling_interval", 30),
                "triggers": data.get("triggers", []),
            },
        }


def create_k8s_service(session_maker=None, models=None) -> K8sScaledObjectService:
    """Factory: creates the appropriate K8s service based on K8S_MODE env."""
    mode = os.environ.get("K8S_MODE", "mock")

    if mode == "in-cluster":
        service = RealK8sService()
        if service.is_connected():
            logger.info("K8s service: Running in IN-CLUSTER mode (real Kubernetes API)")
            return service
        else:
            logger.warning("K8s service: in-cluster mode requested but connection failed, falling back to mock")

    if session_maker and models:
        logger.info("K8s service: Running in MOCK mode (SQLite database)")
        return MockK8sService(session_maker, models)

    raise RuntimeError("Cannot create K8s service: no valid mode available")
