import os


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://jolly-longma-5797b4.netlify.app",
]

DEFAULT_COMPS_PROVIDER = "sample"


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "")
    configured_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return configured_origins or DEFAULT_CORS_ORIGINS


def get_comps_provider_name() -> str:
    return os.getenv("COMPS_PROVIDER", DEFAULT_COMPS_PROVIDER).strip().casefold()
