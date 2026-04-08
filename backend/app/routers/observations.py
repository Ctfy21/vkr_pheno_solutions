from app.routers.crud import make_crud_router
from app.models.schemas import ObservationCreate, ObservationOut
router = make_crud_router("observations", ObservationCreate, ObservationOut, use_brapi_db=True)
