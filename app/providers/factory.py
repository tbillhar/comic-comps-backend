from fastapi import HTTPException

from app.config import get_comps_provider_name
from app.providers.apify_provider import ApifySoldCompsProvider
from app.providers.base import CompsProvider
from app.providers.sample_provider import SampleCompsProvider
from app.providers.soldcomps_provider import SoldCompsProvider


def get_comps_provider() -> CompsProvider:
    provider_name = get_comps_provider_name()

    if provider_name == "apify":
        try:
            return ApifySoldCompsProvider()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_not_configured",
                    "message": str(exc),
                },
            ) from exc

    if provider_name == "sample":
        return SampleCompsProvider()

    if provider_name == "soldcomps":
        try:
            return SoldCompsProvider()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_not_configured",
                    "message": str(exc),
                },
            ) from exc

    raise HTTPException(
        status_code=500,
        detail={
            "code": "unsupported_comps_provider",
            "message": f"Unsupported COMPS_PROVIDER value: {provider_name}",
        },
    )
