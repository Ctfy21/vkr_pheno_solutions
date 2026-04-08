import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "phenoplant")
JWT_SECRET = os.getenv("JWT_SECRET", "phenoplant-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/data/uploads")

# Keycloak
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak-svc:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "phenoplant")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "phenoplant-app")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
