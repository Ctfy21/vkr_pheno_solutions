from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URL, DB_NAME

BRAPI_DB_NAME = DB_NAME + "_brapi"

_client = None
_db = None
_brapi_db = None

async def get_db():
    global _client, _db
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
        _db = _client[DB_NAME]
    return _db

async def get_brapi_db():
    global _client, _brapi_db
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
        _brapi_db = _client[BRAPI_DB_NAME]
    if _brapi_db is None:
        _brapi_db = _client[BRAPI_DB_NAME]
    return _brapi_db

async def close_db():
    global _client, _db, _brapi_db
    if _client:
        _client.close()
        _client = None
        _db = None
        _brapi_db = None

def set_db(db):
    """For testing: inject a mock database."""
    global _db
    _db = db

async def get_db_dep():
    """FastAPI dependency — local DB."""
    return await get_db()

async def get_brapi_db_dep():
    """FastAPI dependency — BrAPI data DB."""
    return await get_brapi_db()
