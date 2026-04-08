from app.routers.crud import make_crud_router
from app.models.schemas import ClimateChamberCreate, ClimateChamberOut
router = make_crud_router("climate_chambers", ClimateChamberCreate, ClimateChamberOut)
