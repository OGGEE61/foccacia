export async function onRequestGet({ request, env }) {
  const product = new URL(request.url).searchParams.get('product');
  if (!product) return Response.json({ error: 'Missing ?product=' }, { status: 400 });

  const { results } = await env.DB.prepare(
    `SELECT substr(timestamp, 1, 16) AS session, price
     FROM price_history
     WHERE product_name = ?
     ORDER BY session ASC, price ASC`
  ).bind(product).all();

  // Group by session, compute stats (prices are already sorted from SQL)
  const map = {};
  for (const { session, price } of results) {
    if (!map[session]) map[session] = [];
    map[session].push(price);
  }

  const stats = Object.entries(map).map(([session, prices]) => {
    const n = prices.length;
    const median = n % 2 === 0
      ? (prices[n / 2 - 1] + prices[n / 2]) / 2
      : prices[Math.floor(n / 2)];
    return {
      session,
      min: prices[0],
      max: prices[n - 1],
      median: +median.toFixed(2),
      avg: +(prices.reduce((a, b) => a + b, 0) / n).toFixed(2),
      count: n,
    };
  });

  return Response.json(stats);
}
