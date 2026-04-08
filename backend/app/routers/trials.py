from app.routers.crud import make_crud_router
from app.models.schemas import TrialCreate, TrialOut
router = make_crud_router("trials", TrialCreate, TrialOut, use_brapi_db=True)
