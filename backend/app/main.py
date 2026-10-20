from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, programs, trials, studies, germplasm, traits, methods, scales, variables, observation_units, observations, images, dashboard, climate_chambers, sensor_readings, admin
from app.routers import brapi, brapi_sync, notifications, export

app = FastAPI(title="PhenoPlant API", version="1.0.0", description="BrAPI v2.1 compatible plant phenotyping platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(programs.router, prefix="/api/programs", tags=["Programs"])
app.include_router(trials.router, prefix="/api/trials", tags=["Trials"])
app.include_router(studies.router, prefix="/api/studies", tags=["Studies"])
app.include_router(germplasm.router, prefix="/api/germplasm", tags=["Germplasm"])
app.include_router(traits.router, prefix="/api/traits", tags=["Traits"])
app.include_router(methods.router, prefix="/api/methods", tags=["Methods"])
app.include_router(scales.router, prefix="/api/scales", tags=["Scales"])
app.include_router(variables.router, prefix="/api/variables", tags=["Variables"])
app.include_router(observation_units.router, prefix="/api/observationunits", tags=["ObservationUnits"])
app.include_router(observations.router, prefix="/api/observations", tags=["Observations"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(climate_chambers.router, prefix="/api/climate-chambers", tags=["ClimateChambers"])
app.include_router(sensor_readings.router, prefix="/api/sensor-readings", tags=["SensorReadings"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(brapi.router, prefix="/brapi/v2", tags=["BrAPI v2.1"])
app.include_router(brapi_sync.router, prefix="/api/admin", tags=["BrAPI Sync"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}
