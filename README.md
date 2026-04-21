# Comic Comps Backend

FastAPI backend for comic book comparable sales workflows.

## Local Setup

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Run the API locally:

```powershell
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Endpoints

- `GET /health` returns service health.
- `GET /comps` returns sample comparable comic sales.
- `GET /comps?title=spider&issue_number=300` filters comparable sales by title and issue.

Interactive API docs are available at `/docs` when the server is running.

## Tests

```powershell
pytest
```

## Cloud Run Deployment

Build and deploy through Cloud Build:

```powershell
gcloud builds submit --config cloudbuild.yaml
```

The default Cloud Build substitutions deploy the service as `comic-comps-backend` in `us-central1`.
Override them as needed:

```powershell
gcloud builds submit --config cloudbuild.yaml --substitutions=_SERVICE_NAME=my-service,_REGION=us-east1
```

To deploy from a local Docker build instead, replace `PROJECT_ID` in `service.yaml` with your Google Cloud project ID and apply it with:

```powershell
gcloud run services replace service.yaml --region us-central1
```
