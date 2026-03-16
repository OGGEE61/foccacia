import re
import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging
from datetime import datetime
import argparse
from dotenv import load_dotenv

load_dotenv()

# === CREDENTIALS (from .env) ===
SCRAPE_DO_TOKEN = os.getenv('SCRAPE_DO_TOKEN', '10242e393a904ff9bbeee5b837bb81897884216fac6')
CF_API_KEY      = os.getenv('CF_API_KEY')
CF_EMAIL        = os.getenv('CF_EMAIL')
CF_ACCOUNT_ID   = os.getenv('CF_ACCOUNT_ID')
D1_DATABASE_ID  = os.getenv('D1_DATABASE_ID')

# === PRODUCTS ===
# Add more products here as needed. Key = display name, value = Allegro listing URL.
PRODUCTS = {
    "Schar Focaccia con Rosmarino 200g": (
        "https://allegro.pl/oferty-produktu/"
        "schar-focaccia-con-rosmarino-3x66-g-200-g-8685e996-6e12-4b5c-8b6d-fb9d94a476f4"
    ),
    # "Another Product": "https://allegro.pl/oferty-produktu/...",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def get_scrape_do_url(url):
    encoded = urllib.parse.quote(url)
    return (
        f"https://api.scrape.do?token={SCRAPE_DO_TOKEN}"
        f"&url={encoded}&geoCode=pl&super=true&customHeaders=true&render=false"
    )


def extract_vendor(article):
    # Layout A: /uzytkownik/ link
    vendor_link = article.find('a', href=lambda h: h and '/uzytkownik/' in h)
    if vendor_link:
        return vendor_link['href'].split('/uzytkownik/')[-1].strip('/')

    # Layout B: element immediately before "Poleca sprzedającego"
    poleca = article.find(lambda t: t.name and t.get_text(strip=True).startswith('Poleca sprzeda'))
    if poleca:
        prev = poleca.find_previous_sibling()
        if prev:
            text = re.sub(r'^od', '', prev.get_text(strip=True)).strip()
            if text:
                return text
    return None


def extract_price(article):
    text = article.get_text(separator=' ', strip=True)
    match = re.search(r'(\d+),\s*(\d{2})\s*z', text)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    return None


def scrape_product(product_name, listing_url, limit=None):
    logging.info(f"Fetching: {product_name}")
    response = requests.get(get_scrape_do_url(listing_url))
    if response.status_code != 200:
        logging.error(f"Failed to fetch listing: HTTP {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article')
    logging.info(f"Found {len(articles)} articles.")
    if limit:
        articles = articles[:limit]

    seen_offer_ids = set()
    offers = []
    for article in articles:
        link = article.find('a', href=lambda h: h and 'offerId=' in h)
        if not link:
            continue
        offer_id = link['href'].split('offerId=')[-1].split('&')[0]
        vendor = extract_vendor(article)
        price = extract_price(article)

        if not vendor or not price:
            logging.warning(f"Skipping offer {offer_id}: vendor={vendor}, price={price}")
            continue

        if offer_id in seen_offer_ids:
            continue
        seen_offer_ids.add(offer_id)

        offers.append({
            "offer_id": offer_id,
            "name": product_name,
            "vendor": vendor,
            "price": price,
            "currency": "PLN",
            "timestamp": datetime.now().isoformat(),
        })
        logging.info(f"  {price:.2f} PLN from {vendor}")

    return offers


def write_to_d1(offers):
    if not all([CF_API_KEY, CF_EMAIL, CF_ACCOUNT_ID, D1_DATABASE_ID]):
        logging.error("Missing Cloudflare credentials in .env — cannot write to D1.")
        return False

    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}/query"
    headers = {
        "X-Auth-Key": CF_API_KEY,
        "X-Auth-Email": CF_EMAIL,
        "Content-Type": "application/json",
    }

    # D1 has a ~100 bound-parameter limit per query; chunk into groups of 10 rows (60 params each)
    CHUNK = 10
    for i in range(0, len(offers), CHUNK):
        chunk = offers[i:i + CHUNK]
        placeholders = ', '.join(['(?, ?, ?, ?, ?, ?)'] * len(chunk))
        params = []
        for d in chunk:
            params.extend([d['offer_id'], d['name'], d['vendor'], d['price'], d['currency'], d['timestamp']])

        resp = requests.post(url, headers=headers, json={
            "sql": f"INSERT INTO price_history (offer_id, product_name, vendor, price, currency, timestamp) VALUES {placeholders}",
            "params": params,
        })

        if not resp.ok:
            logging.error(f"D1 write failed ({resp.status_code}): {resp.text}")
            return False

    logging.info(f"Saved {len(offers)} rows to D1.")
    return True


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Allegro product listings and save to Cloudflare D1.")
    parser.add_argument("--test", action="store_true", help="Limit to first 5 offers per product.")
    parser.add_argument("--product", choices=list(PRODUCTS.keys()),
                        default=list(PRODUCTS.keys())[0],
                        help="Which product to scrape (default: first in PRODUCTS).")
    parser.add_argument("--all-products", action="store_true", help="Scrape all products in PRODUCTS.")
    return parser.parse_args()


def main():
    args = parse_args()
    limit = 5 if args.test else None
    if args.test:
        logging.info("TEST MODE: first 5 offers only.")

    to_scrape = PRODUCTS if args.all_products else {args.product: PRODUCTS[args.product]}

    for product_name, listing_url in to_scrape.items():
        offers = scrape_product(product_name, listing_url, limit=limit)
        logging.info(f"Parsed {len(offers)} valid offers for '{product_name}'.")
        if offers:
            write_to_d1(offers)


if __name__ == "__main__":
    main()
