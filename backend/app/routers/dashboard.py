from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.database import get_db_dep, get_brapi_db_dep
from app.models.schemas import DashboardStats

router = APIRouter()

@router.get("", response_model=DashboardStats)
async def get_dashboard(db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    return DashboardStats(
        programs=await brapi_db.programs.count_documents({}),
        trials=await brapi_db.trials.count_documents({}),
        experiments=await brapi_db.studies.count_documents({}),
        plants=await brapi_db.observation_units.count_documents({}),
        observations=await brapi_db.observations.count_documents({}),
        images=await db.images.count_documents({}),
    )
