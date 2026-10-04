"""Self-contained websites for end-to-end runs, served on 127.0.0.1.

Five small sites with fictional content, so a model cannot answer from memory:
  /findr   search engine over the wiki          /wiki    encyclopedia articles
  /shop    store with search, product pages, cart
  /desk    contact form and newsletter sign-up    /jotter  notes app (held-out site)
  /portal  pages behind a login wall (tasks that cannot be completed)

Everything an oracle needs (cart, form submissions, notes, autosaved drafts) is recorded
server side in STATE. Oracles read STATE in-process; the agent cannot reach it over HTTP.
"""

from __future__ import annotations

import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote_plus, urlsplit

ARTICLES = {
    "Velmora": {
        "summary": "Velmora is a river town in the fictional province of Ostland, on the River Ost.",
        "facts": {"Population (2020)": "48,213", "Founded": "1652", "River": "Ost", "Mayor": "Ilse Varga"},
        "body": "Velmora grew around a ferry crossing. Its old town has a covered market and the Halden Bridge.",
    },
    "Corvane": {
        "summary": "Edda Corvane was a chemist known for the Corvane reaction.",
        "facts": {"Born": "1871, Velmora", "Died": "1939", "Field": "Organic chemistry", "Known for": "Corvane reaction"},
        "body": "Corvane studied in Velmora and later taught at the Mirefield Institute.",
    },
    "Lake_Tessaly": {
        "summary": "Lake Tessaly is a glacial lake in northern Ostland.",
        "facts": {"Maximum depth": "214 m", "Surface area": "38 km2", "Outflow": "River Ost"},
        "body": "The lake freezes in most winters. A ferry links its two largest villages.",
    },
    "Halden_Bridge": {
        "summary": "The Halden Bridge is a steel arch bridge across the River Ost in Velmora.",
        "facts": {"Opened": "1934", "Length": "1,140 m", "Designer": "Piet Halden"},
        "body": "The bridge replaced the ferry crossing and carries road and tram traffic.",
    },
    "Mirefield_Observatory": {
        "summary": "Mirefield Observatory is an astronomical observatory on Mount Mire.",
        "facts": {"Altitude": "2,310 m", "Established": "1958", "Main telescope": "1.8 m reflector"},
        "body": "The observatory is run by the Mirefield Institute and is open to visitors on Saturdays.",
    },
    "Tarsk_language": {
        "summary": "Tarsk is a language spoken in the eastern valleys of Ostland.",
        "facts": {"Speakers": "92,000", "Script": "Latin", "Family": "Ostic"},
        "body": "Tarsk has three grammatical cases and a rich system of evidential markers.",
    },
}

PRODUCTS = {
    "QM-101": {"name": "Linen notebook A5", "price": "7.50", "category": "Stationery"},
    "QM-102": {"name": "Brass fountain pen", "price": "34.00", "category": "Stationery"},
    "QM-103": {"name": "Recycled paper pack", "price": "5.25", "category": "Stationery"},
    "QM-201": {"name": "Ceramic mug 300 ml", "price": "11.90", "category": "Kitchen"},
    "QM-202": {"name": "Steel kettle 1.2 l", "price": "42.00", "category": "Kitchen"},
    "QM-301": {"name": "Desk lamp with dimmer", "price": "29.99", "category": "Home"},
    "QM-302": {"name": "Wool blanket grey", "price": "54.00", "category": "Home"},
}

STATE: dict = {}
_LOCK = threading.Lock()


def reset_state() -> None:
    with _LOCK:
        STATE.clear()
        STATE.update({"cart": {}, "contact": [], "newsletter": [], "notes": [
            {"title": "Groceries", "body": "milk, bread, apples"},
            {"title": "Ferry times", "body": "Velmora ferry leaves at 07:40 and 17:10"},
        ], "drafts": {}, "requests": []})


def snapshot_state() -> dict:
    with _LOCK:
        return json.loads(json.dumps(STATE))


reset_state()

AUTOSAVE_JS = """<script>
document.addEventListener('input', e => {
  const el = e.target; if (!el.name) return;
  fetch('/__draft', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'page=' + encodeURIComponent(location.pathname) + '&field=' + encodeURIComponent(el.name) +
          '&value=' + encodeURIComponent(el.value)});
});
</script>"""


def page(title: str, body: str, site: str = "") -> bytes:
    nav = {
        "findr": '<a href="/findr">Findr</a>',
        "wiki": '<a href="/wiki/Main_Page">Openpedia</a> | <form action="/wiki/search" style="display:inline">'
                '<input name="q" placeholder="Search Openpedia" aria-label="Search Openpedia"> <button>Go</button></form>',
        "shop": '<a href="/shop">Quillmart</a> | <a href="/shop/cart">Cart</a> | <form action="/shop/search" style="display:inline">'
                '<input name="q" placeholder="Search products" aria-label="Search products"> <button>Search</button></form>',
        "desk": '<a href="/desk">CivicDesk</a> | <a href="/desk/contact">Contact</a> | <a href="/desk/newsletter">Newsletter</a>',
        "jotter": '<a href="/jotter">Jotter</a> | <a href="/jotter/new">New note</a>',
    }.get(site, "")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head>"
            f"<body><header>{nav}</header><main>{body}</main>{AUTOSAVE_JS}</body></html>").encode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def _send(self, body: bytes, status: int = 200, headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, to: str):
        self._send(b"", 303, {"Location": to})

    def _form(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        data = parse_qs(self.rfile.read(n).decode(), keep_blank_values=True)
        return {k: v[-1] for k, v in data.items()}

    # ---------------- GET ----------------
    def do_GET(self):
        u = urlsplit(self.path)
        q = {k: v[-1] for k, v in parse_qs(u.query).items()}
        p = u.path.rstrip("/") or "/"
        with _LOCK:
            STATE["requests"].append(("GET", self.path))

        if p == "/findr":
            return self._send(page("Findr", "<h1>Findr</h1><form action='/findr/search'><input name='q' "
                                   "placeholder='Search the web' aria-label='Search'> <button>Search</button></form>", "findr"))
        if p == "/findr/search":
            query = q.get("q", "")
            words = [w for w in query.lower().split() if w]
            hits = [s for s, a in ARTICLES.items()
                    if words and any(w in (s + " " + a["summary"] + " " + a["body"]).lower() for w in words)]
            items = "".join(f"<li><a href='/wiki/{s}'>{s.replace('_', ' ')} - Openpedia</a><p>{html.escape(ARTICLES[s]['summary'])}</p></li>"
                            for s in hits) or "<p>No results.</p>"
            return self._send(page(f"{query} - Findr Search", f"<h1>Results for &quot;{html.escape(query)}&quot;</h1>"
                                   f"<form action='/findr/search'><input name='q' value='{html.escape(query)}' aria-label='Search'>"
                                   f"<button>Search</button></form><ol>{items}</ol>", "findr"))
        if p == "/wiki/Main_Page":
            links = "".join(f"<li><a href='/wiki/{s}'>{s.replace('_', ' ')}</a></li>" for s in ARTICLES)
            return self._send(page("Openpedia", f"<h1>Openpedia</h1><p>Articles about Ostland.</p><ul>{links}</ul>", "wiki"))
        if p == "/wiki/search":
            target = q.get("q", "").strip().replace(" ", "_")
            for s in ARTICLES:
                if s.lower() == target.lower():
                    return self._redirect(f"/wiki/{s}")
            return self._redirect(f"/findr/search?q={quote_plus(q.get('q', ''))}")
        if p.startswith("/wiki/"):
            slug = p.split("/", 2)[2]
            a = ARTICLES.get(slug)
            if not a:
                return self._send(page("Page not found - Openpedia", "<h1>Page not found</h1><p>Openpedia has no article with this name.</p>", "wiki"), 404)
            rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in a["facts"].items())
            return self._send(page(f"{slug.replace('_', ' ')} - Openpedia",
                                   f"<h1>{slug.replace('_', ' ')}</h1><table class='infobox'>{rows}</table>"
                                   f"<p>{a['summary']}</p><p>{a['body']}</p>", "wiki"))

        if p == "/shop":
            cats: dict = {}
            for sku, pr in PRODUCTS.items():
                cats.setdefault(pr["category"], []).append(f"<li><a href='/shop/item/{sku}'>{pr['name']}</a> - {pr['price']} EUR</li>")
            body = "".join(f"<h2>{c}</h2><ul>{''.join(v)}</ul>" for c, v in cats.items())
            return self._send(page("Quillmart", f"<h1>Quillmart</h1>{body}", "shop"))
        if p == "/shop/search":
            query = q.get("q", "").lower()
            hits = [f"<li><a href='/shop/item/{s}'>{pr['name']}</a> - {pr['price']} EUR</li>"
                    for s, pr in PRODUCTS.items() if query and any(w in pr["name"].lower() for w in query.split())]
            return self._send(page(f"Search: {q.get('q', '')} - Quillmart",
                                   f"<h1>Products matching &quot;{html.escape(q.get('q', ''))}&quot;</h1><ul>{''.join(hits) or '<li>No products found.</li>'}</ul>", "shop"))
        if p.startswith("/shop/item/"):
            sku = p.rsplit("/", 1)[1]
            pr = PRODUCTS.get(sku)
            if not pr:
                return self._send(page("Not found - Quillmart", "<h1>Product not found</h1>", "shop"), 404)
            return self._send(page(f"{pr['name']} - Quillmart",
                                   f"<h1>{pr['name']}</h1><p>Price: {pr['price']} EUR</p><p>Item number: {sku}</p>"
                                   f"<form method='post' action='/shop/cart/add'><input type='hidden' name='sku' value='{sku}'>"
                                   f"<label>Quantity <input name='qty' type='number' value='1' min='1' aria-label='Quantity'></label> "
                                   f"<button type='submit'>Add to cart</button></form>", "shop"))
        if p == "/shop/cart":
            with _LOCK:
                cart = dict(STATE["cart"])
            rows = "".join(f"<li>{PRODUCTS[s]['name']} x {n}</li>" for s, n in cart.items()) or "<li>Your cart is empty.</li>"
            return self._send(page("Cart - Quillmart", f"<h1>Your cart</h1><ul>{rows}</ul>", "shop"))

        if p == "/desk":
            return self._send(page("CivicDesk", "<h1>CivicDesk</h1><p>Contact the town office or subscribe to the newsletter.</p>", "desk"))
        if p == "/desk/contact":
            return self._send(page("Contact - CivicDesk",
                                   "<h1>Contact the town office</h1><form method='post' action='/desk/contact'>"
                                   "<label>Name <input name='name' aria-label='Name'></label><br>"
                                   "<label>Email <input name='email' type='email' aria-label='Email'></label><br>"
                                   "<label>Subject <select name='subject' aria-label='Subject'><option value=''>Choose</option>"
                                   "<option>Waste collection</option><option>Parking</option><option>Other</option></select></label><br>"
                                   "<label>Message <textarea name='message' aria-label='Message'></textarea></label><br>"
                                   "<button type='submit'>Send message</button></form>", "desk"))
        if p == "/desk/newsletter":
            return self._send(page("Newsletter - CivicDesk",
                                   "<h1>Newsletter</h1><form method='post' action='/desk/newsletter'>"
                                   "<label>Email <input name='email' type='email' aria-label='Email'></label> "
                                   "<label><input type='checkbox' name='weekly' value='yes'> Weekly digest</label> "
                                   "<button type='submit'>Subscribe</button></form>", "desk"))
        if p == "/desk/thanks":
            return self._send(page("Message sent - CivicDesk", f"<h1>Thank you</h1><p>Your ticket number is {html.escape(q.get('t', ''))}.</p>", "desk"))
        if p == "/desk/subscribed":
            return self._send(page("Subscribed - CivicDesk", "<h1>You are subscribed</h1>", "desk"))

        if p == "/jotter":
            with _LOCK:
                notes = list(STATE["notes"])
            items = "".join(f"<li><a href='/jotter/note/{i}'>{html.escape(n['title'])}</a></li>" for i, n in enumerate(notes))
            return self._send(page("Jotter", f"<h1>Your notes</h1><ul>{items}</ul>", "jotter"))
        if p.startswith("/jotter/note/"):
            try:
                with _LOCK:
                    n = STATE["notes"][int(p.rsplit("/", 1)[1])]
            except (ValueError, IndexError):
                return self._send(page("Not found - Jotter", "<h1>Note not found</h1>", "jotter"), 404)
            return self._send(page(f"{n['title']} - Jotter", f"<h1>{html.escape(n['title'])}</h1><p>{html.escape(n['body'])}</p>", "jotter"))
        if p == "/jotter/new":
            return self._send(page("New note - Jotter",
                                   "<h1>New note</h1><form method='post' action='/jotter/new'>"
                                   "<label>Title <input name='title' aria-label='Title'></label><br>"
                                   "<label>Body <textarea name='body' aria-label='Body'></textarea></label><br>"
                                   "<button type='submit'>Save note</button></form>", "jotter"))

        if p.startswith("/portal"):
            if p == "/portal/login":
                return self._send(page("Sign in - Portal", "<h1>Sign in</h1><form><input name='user' aria-label='User'>"
                                       "<input name='pw' type='password' aria-label='Password'><button>Sign in</button></form>"))
            return self._redirect("/portal/login?next=" + quote_plus(p))
        return self._send(page("Page not found", "<h1>Page not found</h1>"), 404)

    # ---------------- POST ----------------
    def do_POST(self):
        p = urlsplit(self.path).path.rstrip("/")
        f = self._form()
        with _LOCK:
            STATE["requests"].append(("POST", self.path))
        if p == "/__draft":
            with _LOCK:
                STATE["drafts"].setdefault(f.get("page", ""), {})[f.get("field", "")] = f.get("value", "")
            return self._send(b"ok")
        if p == "/shop/cart/add":
            sku = f.get("sku", "")
            try:
                qty = max(1, int(f.get("qty") or 1))
            except ValueError:
                qty = 1
            if sku in PRODUCTS:
                with _LOCK:
                    STATE["cart"][sku] = STATE["cart"].get(sku, 0) + qty
            return self._redirect("/shop/cart")
        if p == "/desk/contact":
            with _LOCK:
                STATE["contact"].append(f)
                ticket = f"CD-{1000 + len(STATE['contact'])}"
            return self._redirect(f"/desk/thanks?t={ticket}")
        if p == "/desk/newsletter":
            with _LOCK:
                STATE["newsletter"].append(f)
            return self._redirect("/desk/subscribed")
        if p == "/jotter/new":
            with _LOCK:
                STATE["notes"].append({"title": f.get("title", ""), "body": f.get("body", "")})
            return self._redirect("/jotter")
        return self._send(b"not found", 404)


class SiteServer:
    """Run the sites on 127.0.0.1 in a background thread."""

    def __init__(self, port: int = 0):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


if __name__ == "__main__":
    with SiteServer(8800) as s:
        print(f"Sites running at {s.base} (Ctrl+C to stop)")
        threading.Event().wait()
