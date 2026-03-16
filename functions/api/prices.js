export async function onRequestGet({ request, env }) {
  const session = new URL(request.url).searchParams.get('session');
  if (!session) return Response.json({ error: 'Missing ?session= parameter' }, { status: 400 });

  const { results } = await env.DB.prepare(
    `SELECT vendor, price, offer_id, timestamp
     FROM price_history
     WHERE substr(timestamp, 1, 16) = ?
     ORDER BY price ASC`
  ).bind(session).all();

  return Response.json(results);
}
