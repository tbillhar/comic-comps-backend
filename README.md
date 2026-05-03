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
- `POST /comps/debug` returns provider retrieval and filtering diagnostics for a query.

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

### `POST /comps/debug`

Use this temporary diagnostics endpoint when the backend disagrees with a manual eBay sold/completed search. It returns:

- attempted provider queries
- raw item count from the provider
- accepted count
- per-item inclusion decisions with rejection reasons
- raw provider price fields and the parsed price currently selected by the backend

Example:

```bash
curl -X POST "https://comic-comps-backend-7tckae75qq-uc.a.run.app/comps/debug" \
  -H "Content-Type: application/json" \
  -d '{"query":"X-Men #1 CGC 4.0","cert_type":"cgc","max_results":10}'
```

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

## Sold-Comps Provider

The backend selects its comparable-sales source with `COMPS_PROVIDER`.

```powershell
$env:COMPS_PROVIDER = "apify"
```

Current supported values:

- `apify`: real eBay sold listing retrieval through the configured Apify actor.
- `sample`: in-memory sample data used for development and contract testing.

The `apify` provider requires:

```powershell
$env:APIFY_API_TOKEN = "your-token"
```

Optional provider settings:

```powershell
$env:APIFY_ACTOR_ID = "caffein.dev~ebay-sold-listings"
$env:APIFY_ACTOR_MODE = "legacy_ebay_sold_listings"
$env:APIFY_EBAY_SITE = "ebay.com"
$env:APIFY_DAYS_TO_SCRAPE = "90"
$env:APIFY_MAX_TOTAL_CHARGE_USD = "1"
```

The provider returns sold listings and the service keeps the `POST /comps` response contract stable.

Supported `APIFY_ACTOR_MODE` values:

- `legacy_ebay_sold_listings`: current Apify eBay sold-listings actor contract.
- `comic_comps_custom`: custom actor contract for direct eBay sold/completed scraping.

The custom actor mode is expected to return item rows that include:

- `title`
- `url`
- one of `endedAt`, `saleDate`, or `date`
- one of `soldPrice`, `price`, or `salePrice`

It may also return `itemId`, `shippingPrice`, `totalPrice`, or a wrapped row with an `items` array.
The backend normalizes that output back into the same `/comps` and `/comps/debug` response contract.

## Custom Apify Actor

This repo now includes a custom Apify actor scaffold in [apify-actor/README.md](D:\Comic Comps\comic-comps-backend\comic-comps-backend\apify-actor\README.md).

That actor is intended to scrape the exact eBay sold/completed search result cards you manually compare against, then emit rows in the backend's `comic_comps_custom` format.

When the actor is deployed in Apify, switch Cloud Run to:

```powershell
$env:APIFY_ACTOR_MODE = "comic_comps_custom"
$env:APIFY_ACTOR_ID = "your-username~your-actor-name"
```

The custom actor currently emits:

- `id`
- `title`
- `url`
- `saleDate`
- `price`
- `shippingPrice`
- `totalPrice`
- raw display text fields for debugging

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

The Apify API token should be stored as a Cloud Run secret before deploying with the real provider:

```bash
PROJECT_NUMBER="$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')"
printf '%s' "$APIFY_API_TOKEN" | gcloud secrets create apify-api-token --data-file=-
gcloud secrets add-iam-policy-binding apify-api-token \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

After the first secret creation, rotate/update it with:

```bash
printf '%s' "$APIFY_API_TOKEN" | gcloud secrets versions add apify-api-token --data-file=-
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

To switch Cloud Run to the custom Apify actor:

```bash
IMAGE_TAG="$(git rev-parse --short HEAD)"
CUSTOM_ACTOR_ID="tbillhar~comic-comps-ebay-sold-actor"
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=comic-comps-backend,_REGION=us-central1,_IMAGE_TAG="$IMAGE_TAG",_APIFY_ACTOR_ID="$CUSTOM_ACTOR_ID",_APIFY_ACTOR_MODE="comic_comps_custom"
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
