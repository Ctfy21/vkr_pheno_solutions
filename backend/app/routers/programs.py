from app.routers.crud import make_crud_router
from app.models.schemas import ProgramCreate, ProgramOut
router = make_crud_router("programs", ProgramCreate, ProgramOut, use_brapi_db=True)
