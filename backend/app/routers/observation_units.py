from app.routers.crud import make_crud_router
from app.models.schemas import ObservationUnitCreate, ObservationUnitOut
router = make_crud_router("observation_units", ObservationUnitCreate, ObservationUnitOut, use_brapi_db=True)
