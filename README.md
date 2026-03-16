# Allegro Price Tracker

Tracks vendor prices for a given Allegro product listing. One click to scrape, historical session browser to compare over time, with trend and distribution charts.

**Stack:** Cloudflare Pages · Cloudflare D1 · scrape.do

**Author:** Max Gustaw ([@OGGEE61](https://github.com/OGGEE61))

---

## Features

- Scrape all vendor prices for a product listing with one click
- Historical session browser — compare prices across runs
- Median price over time chart with min/max range band
- Price distribution histogram per session
- Multi-product support — add more products in `scrapper.py`
- Runs fully on Cloudflare (Pages + D1), no server needed

---

## Architecture

```
public/index.html          → Cloudflare Pages (static frontend)
functions/api/scrape.js    → POST /api/scrape    — fetches Allegro, parses, saves to D1
functions/api/prices.js    → GET  /api/prices    — reads a session from D1
functions/api/sessions.js  → GET  /api/sessions  — lists all scrape sessions + products
functions/api/stats.js     → GET  /api/stats     — per-session min/median/max aggregates
scrapper.py                → local scraper (Python), writes directly to D1
app.py                     → local web UI (Flask), for development
```

---

## Deploy to Cloudflare

**1. Install dependencies**
```bash
npm install
```

**2. Create the D1 database table**
```bash
wrangler d1 execute allegro-prices --file schema.sql --remote
```

**3. Set the scrape.do token as a secret in Cloudflare Pages dashboard**

Settings → Environment variables → add `SCRAPE_DO_TOKEN` (mark as secret)

**4. Connect repo to Cloudflare Pages**

Pages → Create application → Connect to Git → select this repo
- Build command: `npm install`
- Output directory: `public`

The `LISTING_URL` and `PRODUCT_NAME` are already set in `wrangler.toml`.

---

## Local scraping (writes to D1)

Create a `.env` file (git-ignored):
```
SCRAPE_DO_TOKEN=your_token
CF_API_KEY=your_cloudflare_api_key
CF_EMAIL=your@email.com
CF_ACCOUNT_ID=your_account_id
D1_DATABASE_ID=your_database_id
```

Then:
```bash
pip install -r requirements.txt

python scrapper.py                   # scrape default product → D1
python scrapper.py --test            # first 5 offers only
python scrapper.py --all-products    # scrape all products in PRODUCTS dict
```

---

## Adding a product to track

Edit the `PRODUCTS` dict in `scrapper.py`:
```python
PRODUCTS = {
    "Schar Focaccia con Rosmarino 200g": "https://allegro.pl/oferty-produktu/...",
    "Your Product Name":                 "https://allegro.pl/oferty-produktu/...",
}
```

---

## Configuration

| Location | Variable | Purpose |
|---|---|---|
| `wrangler.toml` `[vars]` | `LISTING_URL` | Allegro product listing URL |
| `wrangler.toml` `[vars]` | `PRODUCT_NAME` | Canonical product display name |
| Cloudflare Pages secret | `SCRAPE_DO_TOKEN` | scrape.do API token |
| `.env` | `CF_API_KEY`, `CF_EMAIL`, `CF_ACCOUNT_ID`, `D1_DATABASE_ID` | Local D1 access |
