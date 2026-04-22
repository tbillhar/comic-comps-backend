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
- `POST /comps` searches comparable sales using a JSON request body.

Interactive API docs are available at `/docs` when the server is running.

### `POST /comps`

Request:

```json
{
  "query": "X-Men 1 CGC 4.0",
  "cert_type": "cgc",
  "max_results": 10
}
```

`cert_type` must be one of:

- `raw`
- `cgc`

Response:

```json
{
  "query": "X-Men 1 CGC 4.0",
  "cert_type": "cgc",
  "median": 6800,
  "low": 6500,
  "high": 7100,
  "usable_count": 3,
  "sales": [
    {
      "title": "X-Men 1 CGC 4.0",
      "price": 6500,
      "date": "2026-04-01",
      "source": "sample",
      "url": "https://example.com/x-men-1-cgc-4-0-2026-04-01"
    }
  ]
}
```

Money fields are JSON numbers, not strings. When no usable sales are found, `median`, `low`, and `high` are `null`, `usable_count` is `0`, and `sales` is an empty array.

Validation errors return FastAPI's standard `422` response with a `detail` array describing the invalid fields.

## CORS

Local frontend origins are allowed by default:

- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

Set deployed frontend origins with a comma-separated `CORS_ORIGINS` environment variable:

```powershell
$env:CORS_ORIGINS = "https://your-frontend.example.com"
```

## Comps Provider

The backend selects its comparable-sales source with `COMPS_PROVIDER`.

```powershell
$env:COMPS_PROVIDER = "sample"
```

Current supported value:

- `sample`: in-memory sample data used for development and contract testing.

Future paid scraper/API providers can be added behind the same provider interface without changing the `POST /comps` frontend contract.

## Tests

```powershell
python -m pytest
```

## Cloud Run Deployment

Current deployed backend URL:

```text
https://comic-comps-backend-7tckae75qq-uc.a.run.app
```

Build and deploy through Cloud Build:

```powershell
gcloud builds submit --config cloudbuild.yaml
```

The default Cloud Build substitutions deploy the service as `comic-comps-backend` in `us-central1`.
Override them as needed:

```powershell
gcloud builds submit --config cloudbuild.yaml --substitutions=_SERVICE_NAME=my-service,_REGION=us-east1,_IMAGE_TAG=latest
```

For commit-specific manual deploys from Cloud Shell:

```bash
IMAGE_TAG="$(git rev-parse --short HEAD)"
gcloud builds submit --config cloudbuild.yaml --substitutions=_SERVICE_NAME=comic-comps-backend,_REGION=us-central1,_IMAGE_TAG="$IMAGE_TAG"
```

Verify a deployed backend:

```bash
BACKEND_URL="https://comic-comps-backend-7tckae75qq-uc.a.run.app"

curl "$BACKEND_URL/health"

curl -X POST "$BACKEND_URL/comps" \
  -H "Content-Type: application/json" \
  -d '{"query":"X-Men 1 CGC 4.0","cert_type":"cgc","max_results":10}'
```

To deploy from a local Docker build instead, replace `PROJECT_ID` in `service.yaml` with your Google Cloud project ID and apply it with:

```powershell
gcloud run services replace service.yaml --region us-central1
```

After deployment, use the Cloud Run service URL as the frontend API base URL.
