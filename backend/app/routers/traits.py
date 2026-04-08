from app.routers.crud import make_crud_router
from app.models.schemas import TraitCreate, TraitOut
router = make_crud_router("traits", TraitCreate, TraitOut, use_brapi_db=True)
