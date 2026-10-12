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

# Image collection module
IMAGE_MAX_MB = int(os.getenv("IMAGE_MAX_MB", "25"))
IMAGE_MAX_BYTES = IMAGE_MAX_MB * 1024 * 1024
# Secret for short-lived signed image links (<img src> cannot send a Bearer token)
SIGNED_URL_SECRET = os.getenv("SIGNED_URL_SECRET", JWT_SECRET)
SIGNED_URL_TTL_SECONDS = int(os.getenv("SIGNED_URL_TTL_SECONDS", "900"))
# Window for linking an image to climate-chamber sensor readings
SENSOR_WINDOW_MINUTES = int(os.getenv("SENSOR_WINDOW_MINUTES", "30"))

# Export
# TTF font with Cyrillic glyphs for PDF reports; autodetected when empty
PDF_FONT_PATH = os.getenv("PDF_FONT_PATH", "")
PDF_MAX_THUMBNAILS = int(os.getenv("PDF_MAX_THUMBNAILS", "6"))
