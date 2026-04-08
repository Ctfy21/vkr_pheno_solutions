from app.routers.crud import make_crud_router
from app.models.schemas import ScaleCreate, ScaleOut
router = make_crud_router("scales", ScaleCreate, ScaleOut, use_brapi_db=True)
