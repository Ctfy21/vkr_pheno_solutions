from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import uuid

def new_id() -> str:
    return str(uuid.uuid4())

# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    organization: str = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str
    refresh_token: str = ""

# --- Programs ---
class ProgramCreate(BaseModel):
    name: str
    abbreviation: str = ""
    objective: str = ""
    crop: str = ""
    leadPerson: str = ""

class ProgramOut(ProgramCreate):
    id: str
    organizationId: str = ""

# --- Trials ---
class TrialCreate(BaseModel):
    name: str
    description: str = ""
    programId: str
    startDate: str = ""
    endDate: str = ""
    active: bool = True

class TrialOut(TrialCreate):
    id: str

# --- Studies ---
class PlantInput(BaseModel):
    name: str
    germplasm_id: str = ""
    position: str = ""
    treatment: str = ""

class StudyCreate(BaseModel):
    model_config = {"populate_by_name": True}

    name: str
    description: str = ""
    studyType: str = Field(default="", alias="study_type")
    trialId: str = Field(default="", alias="trial_id")
    startDate: str = Field(default="", alias="start_date")
    endDate: str = Field(default="", alias="end_date")
    locationId: str = Field(default="", alias="location_id")
    climateChamberId: Optional[str] = Field(default=None, alias="climate_chamber_id")
    observationVariableIds: List[str] = Field(default=[], alias="observation_variable_ids")
    plantCount: int = Field(default=0, alias="plant_count")
    status: str = "draft"
    programId: str = Field(default="", alias="program_id")
    plants: List[PlantInput] = []

class StudyOut(StudyCreate):
    id: str

# --- Germplasm ---
class GermplasmCreate(BaseModel):
    germplasmName: str
    genus: str = ""
    species: str = ""
    accessionNumber: str = ""
    pedigree: str = ""
    instituteCode: str = ""

class GermplasmOut(GermplasmCreate):
    id: str

# --- Traits ---
class TraitCreate(BaseModel):
    traitName: str
    traitDescription: str = ""
    traitClass: str = "morphological"
    entity: str = ""
    attribute: str = ""
    coTermId: str = ""

class TraitOut(TraitCreate):
    id: str

# --- Methods ---
class MethodCreate(BaseModel):
    methodName: str
    methodClass: str = "measurement"
    description: str = ""
    formula: Optional[str] = None
    reference: Optional[str] = None

class MethodOut(MethodCreate):
    id: str

# --- Scales ---
class ScaleCreate(BaseModel):
    scaleName: str
    dataType: str = "numerical"
    units: Optional[str] = None
    decimalPlaces: Optional[int] = None
    validValues: Optional[List[str]] = None

class ScaleOut(ScaleCreate):
    id: str

# --- Observation Variables ---
class ObservationVariableCreate(BaseModel):
    name: str
    traitId: str
    methodId: str
    scaleId: str
    coTermId: str = ""

class ObservationVariableOut(ObservationVariableCreate):
    id: str

# --- Observation Units ---
class ObservationUnitCreate(BaseModel):
    name: str
    studyId: str
    germplasmId: str = ""
    position: str = ""
    treatment: Optional[str] = None

class ObservationUnitOut(ObservationUnitCreate):
    id: str

# --- Observations ---
class ObservationCreate(BaseModel):
    observationUnitId: str
    variableId: str
    variableName: str = ""
    value: str
    observationTimeStamp: str = ""
    collector: str = ""

class ObservationOut(ObservationCreate):
    id: str

# --- Climate Chambers ---
class SensorSchema(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    type: str
    unit: str

class ClimateChamberCreate(BaseModel):
    name: str
    organizationId: str = ""
    locationId: str = ""
    sensors: List[SensorSchema] = []

class ClimateChamberOut(ClimateChamberCreate):
    id: str

# --- Sensor Readings ---
class SensorReadingCreate(BaseModel):
    chamberId: str
    sensorId: str
    value: float
    timestamp: str = ""

# --- Dashboard ---
class DashboardStats(BaseModel):
    programs: int = 0
    trials: int = 0
    experiments: int = 0
    plants: int = 0
    observations: int = 0
    images: int = 0
