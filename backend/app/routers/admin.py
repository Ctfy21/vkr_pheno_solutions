import uuid
import subprocess
import tempfile
import os
import yaml
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.auth import require_role, get_current_user
from app.database import get_db_dep

router = APIRouter()


# --- Schemas ---
class ResourcesSchema(BaseModel):
    cpuRequest: str = "500m"
    cpuLimit: str = "2000m"
    memRequest: str = "256Mi"
    memLimit: str = "1Gi"
    gpu: bool = False
    timeoutMinutes: int = 30


class OutputVariableSchema(BaseModel):
    coTermId: str = ""
    name: str = ""
    unit: str = ""
    description: str = ""

class SolutionCreate(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0.0"
    dockerfile: str
    resources: ResourcesSchema = ResourcesSchema()
    outputVariables: List[OutputVariableSchema] = []


class SolutionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    dockerfile: Optional[str] = None
    resources: Optional[ResourcesSchema] = None
    outputVariables: Optional[List[OutputVariableSchema]] = None


class SolutionOut(BaseModel):
    id: str
    name: str
    description: str
    version: str
    dockerfile: str
    resources: Optional[ResourcesSchema] = None
    manifest: Optional[str] = None
    imageName: str
    imageBuilt: bool
    createdAt: str
    createdBy: str
    outputVariables: List[OutputVariableSchema] = []


class SolutionRunRequest(BaseModel):
    studyId: str
    imageIds: List[str] = []


def generate_k8s_manifest(image_name: str, job_name: str, resources: dict, study_id: str = "") -> str:
    """Generate a K8s Job manifest from resource parameters."""
    r = resources or {}
    container_resources = {
        "requests": {
            "cpu": r.get("cpuRequest", "500m"),
            "memory": r.get("memRequest", "256Mi"),
        },
        "limits": {
            "cpu": r.get("cpuLimit", "2000m"),
            "memory": r.get("memLimit", "1Gi"),
        },
    }
    if r.get("gpu"):
        container_resources["limits"]["nvidia.com/gpu"] = "1"

    timeout_seconds = r.get("timeoutMinutes", 30) * 60

    manifest = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": "default",
        },
        "spec": {
            "activeDeadlineSeconds": timeout_seconds,
            "backoffLimit": 0,
            "template": {
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "processor",
                            "image": image_name,
                            "resources": container_resources,
                            "env": [
                                {"name": "STUDY_ID", "value": study_id},
                                {"name": "JOB_NAME", "value": job_name},
                            ],
                        }
                    ],
                }
            },
        },
    }
    return yaml.dump(manifest, default_flow_style=False)


# --- Endpoints ---

@router.post("/solutions", response_model=SolutionOut)
async def create_solution(
    body: SolutionCreate,
    user: dict = Depends(require_role("admin")),
    db=Depends(get_db_dep),
):
    sol_id = str(uuid.uuid4())
    safe_name = body.name.lower().replace(" ", "-").replace("_", "-")
    image_name = f"phenoplant-solution-{safe_name}:{body.version}"
    doc = {
        "_id": sol_id,
        "name": body.name,
        "description": body.description,
        "version": body.version,
        "dockerfile": body.dockerfile,
        "resources": body.resources.model_dump(),
        "imageName": image_name,
        "imageBuilt": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": user.get("email", ""),
        "outputVariables": [ov.model_dump() for ov in body.outputVariables],
    }
    await db.phenotyping_solutions.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return SolutionOut(**doc)


@router.get("/solutions", response_model=List[SolutionOut])
async def list_solutions(
    user: dict = Depends(get_current_user),
    db=Depends(get_db_dep),
):
    docs = []
    async for doc in db.phenotyping_solutions.find().sort("createdAt", -1):
        doc["id"] = doc.pop("_id")
        # Ensure resources field exists for backward compat
        if "resources" not in doc:
            doc["resources"] = None
        docs.append(SolutionOut(**doc))
    return docs


@router.get("/solutions/{sol_id}", response_model=SolutionOut)
async def get_solution(
    sol_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db_dep),
):
    doc = await db.phenotyping_solutions.find_one({"_id": sol_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Solution not found")
    doc["id"] = doc.pop("_id")
    if "resources" not in doc:
        doc["resources"] = None
    return SolutionOut(**doc)


@router.put("/solutions/{sol_id}", response_model=SolutionOut)
async def update_solution(
    sol_id: str,
    body: SolutionUpdate,
    user: dict = Depends(require_role("admin")),
    db=Depends(get_db_dep),
):
    doc = await db.phenotyping_solutions.find_one({"_id": sol_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Solution not found")

    update_data = body.model_dump(exclude_none=True)
    # Convert resources Pydantic model to dict if present
    if "resources" in update_data and isinstance(update_data["resources"], dict):
        pass  # already dict from model_dump

    if "name" in update_data or "version" in update_data:
        name = update_data.get("name", doc["name"])
        version = update_data.get("version", doc["version"])
        safe_name = name.lower().replace(" ", "-").replace("_", "-")
        update_data["imageName"] = f"phenoplant-solution-{safe_name}:{version}"
        update_data["imageBuilt"] = False
    
    # If version, dockerfile, or resources changed — reset imageBuilt
    if "version" in update_data or "dockerfile" in update_data or "resources" in update_data:
        update_data["imageBuilt"] = False

    await db.phenotyping_solutions.update_one({"_id": sol_id}, {"$set": update_data})
    doc = await db.phenotyping_solutions.find_one({"_id": sol_id})
    doc["id"] = doc.pop("_id")
    if "resources" not in doc:
        doc["resources"] = None
    return SolutionOut(**doc)


@router.delete("/solutions/{sol_id}")
async def delete_solution(
    sol_id: str,
    user: dict = Depends(require_role("admin")),
    db=Depends(get_db_dep),
):
    result = await db.phenotyping_solutions.delete_one({"_id": sol_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Solution not found")
    return {"detail": "Deleted"}


@router.post("/solutions/{sol_id}/build")
async def build_solution(
    sol_id: str,
    user: dict = Depends(require_role("admin")),
    db=Depends(get_db_dep),
):
    doc = await db.phenotyping_solutions.find_one({"_id": sol_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Solution not found")

    image_name = doc["imageName"]

    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(doc["dockerfile"])

        # Build with docker
        result = subprocess.run(
            ["docker", "build", "-t", image_name, tmpdir],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Build failed: {result.stderr[-1000:]}")

        # Import into microk8s
        save = subprocess.run(
            f"docker save {image_name} | microk8s ctr image import -",
            shell=True, capture_output=True, text=True, timeout=300,
        )
        if save.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Import failed: {save.stderr[-500:]}")

    await db.phenotyping_solutions.update_one(
        {"_id": sol_id}, {"$set": {"imageBuilt": True}}
    )
    return {"detail": "Image built and imported", "imageName": image_name}


@router.post("/solutions/{sol_id}/run")
async def run_solution(
    sol_id: str,
    body: SolutionRunRequest,
    user: dict = Depends(require_role("admin")),
    db=Depends(get_db_dep),
):
    doc = await db.phenotyping_solutions.find_one({"_id": sol_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Solution not found")
    if not doc.get("imageBuilt"):
        raise HTTPException(status_code=400, detail="Image not built yet")

    job_name = f"phenoplant-job-{sol_id[:8]}-{uuid.uuid4().hex[:6]}"

    # Generate manifest from resources
    resources = doc.get("resources", {})
    if resources:
        manifest_str = generate_k8s_manifest(
            image_name=doc["imageName"],
            job_name=job_name,
            resources=resources,
            study_id=body.studyId,
        )
    else:
        # Fallback: use legacy manifest field if resources not set
        manifest_str = doc.get("manifest", "")
        manifest_str = manifest_str.replace("{{IMAGE_NAME}}", doc["imageName"])
        manifest_str = manifest_str.replace("{{JOB_NAME}}", job_name)
        manifest_str = manifest_str.replace("{{STUDY_ID}}", body.studyId)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(manifest_str)
        manifest_path = f.name

    try:
        result = subprocess.run(
            ["microk8s", "kubectl", "apply", "-f", manifest_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to create job: {result.stderr}")
    finally:
        os.unlink(manifest_path)

    return {"detail": "Job created", "jobName": job_name}


# --- Keycloak User Management ---



class CreateUserRequest(BaseModel):
    email: str
    password: str
    firstName: str = ""
    lastName: str = ""
    role: str = "researcher"


@router.post("/users")
async def create_user(
    body: CreateUserRequest,
    user: dict = Depends(require_role("admin")),
):
    """Create a new user in Keycloak with specified role."""
    import httpx as hx
    from app.config import KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASSWORD

    # Get admin token
    async with hx.AsyncClient() as client:
        resp = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": KEYCLOAK_ADMIN_USER,
                "password": KEYCLOAK_ADMIN_PASSWORD,
            },
            timeout=10,
        )
        admin_token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

        # Create user
        user_payload = {
            "username": body.email,
            "email": body.email,
            "firstName": body.firstName,
            "lastName": body.lastName,
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": body.password, "temporary": False}],
        }
        resp = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
            json=user_payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 409:
            raise HTTPException(status_code=409, detail="Email already registered")
        if resp.status_code not in (201, 204):
            raise HTTPException(status_code=500, detail=f"Keycloak error: {resp.text}")

        location = resp.headers.get("location", "")
        user_id = location.split("/")[-1] if location else ""

        # Assign role
        if user_id and body.role in ("admin", "researcher", "observer"):
            role_resp = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles/{body.role}",
                headers=headers,
                timeout=10,
            )
            if role_resp.status_code == 200:
                role = role_resp.json()
                await client.post(
                    f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
                    json=[role],
                    headers=headers,
                    timeout=10,
                )

    return {
        "id": user_id,
        "email": body.email,
        "name": f"{body.firstName} {body.lastName}".strip(),
        "role": body.role,
        "enabled": True,
    }


@router.get("/users")
async def list_users(user: dict = Depends(require_role("admin"))):
    import httpx as hx
    from app.config import KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASSWORD

    # Get admin token
    async with hx.AsyncClient() as client:
        resp = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": KEYCLOAK_ADMIN_USER,
                "password": KEYCLOAK_ADMIN_PASSWORD,
            },
            timeout=10,
        )
        admin_token = resp.json()["access_token"]

        # Get users
        users_resp = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"max": 100},
            timeout=10,
        )
        users = users_resp.json()

    result = []
    for u in users:
        # Get roles for each user
        async with hx.AsyncClient() as client:
            roles_resp = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{u['id']}/role-mappings/realm",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10,
            )
            roles = [r["name"] for r in roles_resp.json()] if roles_resp.status_code == 200 else []

        role = "admin" if "admin" in roles else "researcher" if "researcher" in roles else "observer"
        result.append({
            "id": u["id"],
            "email": u.get("email", ""),
            "name": u.get("firstName", "") + (" " + u.get("lastName", "") if u.get("lastName") else ""),
            "username": u.get("username", ""),
            "role": role,
            "enabled": u.get("enabled", True),
        })
    return result



@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Delete a user from Keycloak by user ID."""
    import httpx as hx
    from app.config import KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASSWORD

    async with hx.AsyncClient() as client:
        # Get admin token
        resp = await client.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": KEYCLOAK_ADMIN_USER,
                "password": KEYCLOAK_ADMIN_PASSWORD,
            },
            timeout=10,
        )
        admin_token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Delete user
        del_resp = await client.delete(
            f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
            headers=headers,
            timeout=10,
        )
        if del_resp.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        if del_resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail=f"Keycloak error: {del_resp.text}")

    return {"detail": "User deleted"}
