from app.routers.crud import make_crud_router
from app.models.schemas import MethodCreate, MethodOut
router = make_crud_router("methods", MethodCreate, MethodOut, use_brapi_db=True)
