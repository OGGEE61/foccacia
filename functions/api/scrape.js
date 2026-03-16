const NOISE = new Set([
  'od', 'Super Sprzedawcy', 'Sponsorowane', 'Firma', 'Nowy', 'Stan', 'Gwarancja', '|',
]);

function getScrapeDoUrl(token, url) {
  return `https://api.scrape.do?token=${token}&url=${encodeURIComponent(url)}&geoCode=pl&super=true&customHeaders=true&render=false`;
}

function extractArticles(html) {
  const articles = [];
  const re = /<article[\s>][\s\S]*?<\/article>/gi;
  for (const m of html.matchAll(re)) articles.push(m[0]);
  return articles;
}

function extractOfferId(articleHtml) {
  const m = articleHtml.match(/offerId=(\d+)/);
  return m ? m[1] : null;
}

function extractVendor(articleHtml) {
  // Layout A: /uzytkownik/ link — most reliable
  const linkMatch = articleHtml.match(/href="[^"]*\/uzytkownik\/([^"/?#\s]+)"/);
  if (linkMatch) return linkMatch[1];

  // Layout B: last meaningful text node before "Poleca sprzedającego"
  const beforePoleca = articleHtml.split(/Poleca sprzeda/)[0];
  if (!beforePoleca) return null;

  const candidates = [...beforePoleca.matchAll(/>([^<]{2,60})</g)]
    .map(m => m[1].trim())
    .filter(t => t && !NOISE.has(t) && !/^\d/.test(t));

  return candidates.at(-1) ?? null;
}

function extractPrice(articleHtml) {
  const m = articleHtml.replace(/\s+/g, ' ').match(/(\d+),\s*(\d{2})\s*z/);
  return m ? parseFloat(`${m[1]}.${m[2]}`) : null;
}

export async function onRequestPost({ env }) {
  const token = env.SCRAPE_DO_TOKEN;
  const listingUrl = env.LISTING_URL;

  if (!token) return Response.json({ error: 'SCRAPE_DO_TOKEN secret not set' }, { status: 500 });
  if (!listingUrl) return Response.json({ error: 'LISTING_URL var not set' }, { status: 500 });

  let html;
  try {
    const res = await fetch(getScrapeDoUrl(token, listingUrl));
    if (!res.ok) return Response.json({ error: `scrape.do returned ${res.status}` }, { status: 502 });
    html = await res.text();
  } catch (e) {
    return Response.json({ error: `Fetch failed: ${e.message}` }, { status: 502 });
  }

  const productName = env.PRODUCT_NAME || (html.match(/<h1[^>]*>([^<]+)<\/h1>/)?.[1].trim() ?? 'Unknown Product');

  const articles = extractArticles(html);
  const timestamp = new Date().toISOString();
  const stmts = [];
  let skipped = 0;

  for (const article of articles) {
    const offerId = extractOfferId(article);
    if (!offerId) continue;

    const vendor = extractVendor(article);
    const price = extractPrice(article);

    if (!vendor || !price) { skipped++; continue; }

    stmts.push(
      env.DB.prepare(
        'INSERT INTO price_history (offer_id, product_name, vendor, price, currency, timestamp) VALUES (?, ?, ?, ?, ?, ?)'
      ).bind(offerId, productName, vendor, price, 'PLN', timestamp)
    );
  }

  if (stmts.length > 0) await env.DB.batch(stmts);

  return Response.json({ success: true, saved: stmts.length, skipped, product: productName });
}
