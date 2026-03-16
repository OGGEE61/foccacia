export async function onRequestGet({ request, env }) {
  const product = new URL(request.url).searchParams.get('product');

  // All distinct products in the DB
  const { results: productRows } = await env.DB.prepare(
    `SELECT DISTINCT product_name FROM price_history ORDER BY product_name`
  ).all();
  const products = productRows.map(r => r.product_name);

  // Sessions for the selected product (or all if none specified)
  const activeProduct = product ?? products[0] ?? null;
  const { results: sessionRows } = activeProduct
    ? await env.DB.prepare(
        `SELECT DISTINCT substr(timestamp, 1, 16) AS ts
         FROM price_history WHERE product_name = ? ORDER BY ts DESC`
      ).bind(activeProduct).all()
    : await env.DB.prepare(
        `SELECT DISTINCT substr(timestamp, 1, 16) AS ts
         FROM price_history ORDER BY ts DESC`
      ).all();

  return Response.json({
    products,
    active_product: activeProduct,
    sessions: sessionRows.map(r => r.ts),
  });
}
