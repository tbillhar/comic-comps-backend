from fastapi import HTTPException

from app.config import get_comps_provider_name
from app.providers.base import CompsProvider
from app.providers.sample_provider import SampleCompsProvider


def get_comps_provider() -> CompsProvider:
    provider_name = get_comps_provider_name()

    if provider_name == "sample":
        return SampleCompsProvider()

    raise HTTPException(
        status_code=500,
        detail={
            "code": "unsupported_comps_provider",
            "message": f"Unsupported COMPS_PROVIDER value: {provider_name}",
        },
    )
