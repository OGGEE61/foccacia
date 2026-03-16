import sqlite3
from flask import Flask, render_template_string

app = Flask(__name__)
DB_NAME = "allegro_prices.db"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Allegro Price Tracker</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f5f5f5; color: #222; }
  header { background: #ff5a00; color: white; padding: 20px 32px; }
  header h1 { font-size: 1.4rem; font-weight: 700; }
  header p  { font-size: 0.85rem; opacity: 0.85; margin-top: 4px; }
  main { max-width: 960px; margin: 32px auto; padding: 0 16px; }

  .card { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 32px; overflow: hidden; }
  .card-header { padding: 16px 24px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
  .card-header h2 { font-size: 1rem; font-weight: 600; }
  .card-header span { font-size: 0.8rem; color: #888; }

  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 10px 24px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: .05em; color: #888; background: #fafafa; border-bottom: 1px solid #eee; }
  td { padding: 11px 24px; font-size: 0.9rem; border-bottom: 1px solid #f0f0f0; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #fffaf7; }

  .price { font-weight: 600; color: #111; }
  .best { color: #ff5a00; }
  .rank { color: #bbb; font-size: 0.8rem; }
  .ts { color: #aaa; font-size: 0.8rem; }

  .empty { padding: 40px 24px; color: #aaa; text-align: center; }

  .scrapes { display: flex; flex-wrap: wrap; gap: 8px; padding: 16px 24px; }
  .scrape-btn { padding: 6px 14px; border-radius: 20px; border: 1px solid #ddd; background: white; font-size: 0.82rem; cursor: pointer; color: #555; text-decoration: none; }
  .scrape-btn.active { background: #ff5a00; color: white; border-color: #ff5a00; }
</style>
</head>
<body>

<header>
  <h1>Allegro Price Tracker</h1>
  <p>{{ product_name }}</p>
</header>

<main>
  {% if not scrapes %}
    <div class="card"><div class="empty">No data yet. Run <code>python test_scrapdo.py</code> first.</div></div>
  {% else %}

  <div class="card">
    <div class="card-header"><h2>Scrape sessions</h2><span>{{ scrapes|length }} run(s)</span></div>
    <div class="scrapes">
      {% for s in scrapes %}
        <a class="scrape-btn {% if s == selected_scrape %}active{% endif %}" href="/?scrape={{ loop.index0 }}">{{ s }}</a>
      {% endfor %}
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <h2>Prices — {{ selected_scrape }}</h2>
      <span>{{ rows|length }} offers</span>
    </div>
    {% if rows %}
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Vendor</th>
          <th>Price (PLN)</th>
          <th>Offer ID</th>
          <th>Saved at</th>
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
        <tr>
          <td class="rank">{{ loop.index }}</td>
          <td>{{ row.vendor }}</td>
          <td class="price {% if loop.first %}best{% endif %}">{{ "%.2f"|format(row.price) }} zł</td>
          <td><a href="https://allegro.pl/oferta/x-{{ row.offer_id }}" target="_blank" style="color:#888;font-size:.8rem">{{ row.offer_id[:12] }}…</a></td>
          <td class="ts">{{ row.timestamp[:19] }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
      <div class="empty">No offers for this session.</div>
    {% endif %}
  </div>

  {% endif %}
</main>
</body>
</html>
"""


def get_data(scrape_index=0):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        # Distinct scrape sessions (by date prefix of timestamp)
        scrapes = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT substr(timestamp, 1, 19) as ts FROM price_history ORDER BY ts DESC"
            ).fetchall()
        ]

        if not scrapes:
            return None, [], []

        # Group by minute to handle offers saved in the same run
        sessions = []
        for s in scrapes:
            minute = s[:16]  # "YYYY-MM-DD HH:MM"
            if not sessions or sessions[-1] != minute:
                sessions.append(minute)

        # Deduplicate sessions
        sessions = list(dict.fromkeys(sessions))

        scrape_index = max(0, min(scrape_index, len(sessions) - 1))
        selected = sessions[scrape_index]

        rows = conn.execute(
            """SELECT vendor, price, offer_id, timestamp
               FROM price_history
               WHERE substr(timestamp, 1, 16) = ?
               ORDER BY price ASC""",
            (selected,)
        ).fetchall()

        product_name = conn.execute(
            "SELECT product_name FROM price_history LIMIT 1"
        ).fetchone()
        product_name = product_name[0] if product_name else "Unknown Product"

        return product_name, sessions, rows, selected


@app.route("/")
def index():
    from flask import request
    try:
        scrape_index = int(request.args.get("scrape", 0))
    except ValueError:
        scrape_index = 0

    result = get_data(scrape_index)
    if result[1]:  # has sessions
        product_name, scrapes, rows, selected_scrape = result
    else:
        product_name, scrapes, rows, selected_scrape = "Unknown Product", [], [], ""

    return render_template_string(
        HTML,
        product_name=product_name,
        scrapes=scrapes,
        rows=rows,
        selected_scrape=selected_scrape,
    )


if __name__ == "__main__":
    app.run(debug=True)
