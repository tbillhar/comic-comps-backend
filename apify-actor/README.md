# Comic Comps eBay Sold Actor

Custom Apify actor that scrapes eBay sold/completed search result cards and emits normalized rows for the backend's `comic_comps_custom` mode.

## Output Contract

Each emitted row looks like:

```json
{
  "id": "ebay-1234567890",
  "title": "X-Men #1 (Marvel, 1963) CGC 4.0",
  "url": "https://www.ebay.com/itm/1234567890",
  "saleDate": "2026-04-12T00:00:00.000Z",
  "price": "6401.69",
  "shippingPrice": "14.51",
  "totalPrice": "6416.20",
  "currency": "USD",
  "rawPriceText": "$6,401.69",
  "rawShippingText": "+$14.51 shipping",
  "rawDateText": "Sold Apr 12, 2026"
}
```

The backend only requires:

- `title`
- `url`
- `saleDate`
- `price`

The extra raw fields help diagnose parsing mistakes.

## Input

Example actor input:

```json
{
  "query": "X-Men #1 CGC 4.0",
  "maxResults": 50,
  "daysToScrape": 90,
  "ebaySite": "ebay.com",
  "currency": "USD",
  "sort": "endedRecently"
}
```

## Local Run

```bash
npm install
npm start
```

If running locally with Apify input:

```bash
apify run
```
