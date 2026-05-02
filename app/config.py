import os


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://jolly-longma-5797b4.netlify.app",
]

DEFAULT_COMPS_PROVIDER = "apify"
DEFAULT_APIFY_ACTOR_ID = "caffein.dev~ebay-sold-listings"
DEFAULT_APIFY_ACTOR_MODE = "legacy_ebay_sold_listings"
DEFAULT_APIFY_EBAY_SITE = "ebay.com"
DEFAULT_APIFY_DAYS_TO_SCRAPE = 90
DEFAULT_APIFY_MAX_TOTAL_CHARGE_USD = "1"


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "")
    configured_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return configured_origins or DEFAULT_CORS_ORIGINS


def get_comps_provider_name() -> str:
    return os.getenv("COMPS_PROVIDER", DEFAULT_COMPS_PROVIDER).strip().casefold()


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def get_env(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    return int(raw_value)
