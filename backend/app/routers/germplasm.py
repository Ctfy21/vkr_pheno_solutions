from app.routers.crud import make_crud_router
from app.models.schemas import GermplasmCreate, GermplasmOut
router = make_crud_router("germplasm", GermplasmCreate, GermplasmOut, use_brapi_db=True)
