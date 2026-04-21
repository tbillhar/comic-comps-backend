from fastapi import FastAPI

from app.routers import comps


app = FastAPI(
    title="Comic Comps Backend",
    description="API backend for comic book comparable sales and valuation workflows.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(comps.router)
