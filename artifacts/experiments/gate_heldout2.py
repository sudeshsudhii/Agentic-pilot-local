"""Second held-out set for the completion-gate study (42 end states).

Protocol (R5): these states and their labels were written and committed to git BEFORE the gate was
run on any of them, and no gate code was changed afterwards. The commit that adds this file is the
freeze point; its SHA-256 is recorded in artifacts/results/gate_heldout2_freeze.txt.

Writing procedure: for each category, write varied user phrasings (including wordings the gate's
keyword triggers do not list, such as "tell me", "look up", "what year"), then pick for each phrasing a
satisfied or an unsatisfied end state, aiming at a balanced split. Labels state whether the goal is
actually achieved by the page and answer shown, judged from the page facts alone.

Limitation: written by the same author as the gate fixes (no independent annotator; see
AUTHOR_ACTIONS.md for the independent relabelling protocol).
"""

from __future__ import annotations


def build(Case, page, results, plan):
    EVEREST = page("Mount Everest - Wikipedia", "<h1>Mount Everest</h1><p>Mount Everest is Earth's highest mountain above sea level, at 8,849 m.</p>")
    BERLIN = page("Berlin Wall - Wikipedia", "<h1>Berlin Wall</h1><p>The Berlin Wall was built in 1961 and fell on 9 November 1989.</p>")
    AUSTRALIA = page("Australia - Wikipedia", "<h1>Australia</h1><p>Capital: Canberra. Largest city: Sydney.</p>")
    WATER = page("Water - Wikipedia", "<h1>Water</h1><p>Water boils at 100 °C at sea level.</p>")
    MARS = page("Mars - Wikipedia", "<h1>Mars</h1><p>Mars has two small moons, Phobos and Deimos.</p>")
    TOKYO = page("Tokyo - Wikipedia", "<h1>Tokyo</h1><p>Tokyo has a population of about 14 million people.</p>")
    LIBRARY = page("Opening hours - City Library", "<h1>Opening hours</h1><p>Mon–Fri 9:00–18:00, Sat 10:00–14:00</p>")
    WIKI = "https://en.wikipedia.org/wiki/"

    cases = [
        # search
        Case("G1", "search", "Look up 'solar eclipse 2026' on Google", "https://www.google.com/search?q=solar+eclipse+2026",
             results("solar eclipse 2026"), True, "results for the requested query"),
        Case("G2", "search", "Find 'best hiking boots' using Bing", "https://www.bing.com/",
             page("Bing", "<form><input type='search' name='q'></form>"), False, "home page, nothing searched"),
        Case("G3", "search", "Use DuckDuckGo to search for 'python asyncio tutorial'", "https://duckduckgo.com/?q=python+asyncio+tutorial",
             results("python asyncio tutorial"), True, "results for the requested query"),
        Case("G4", "search", "Google 'cheap flights to Lisbon'", "https://www.google.com/search?q=cheap+flights+to+Madrid",
             results("cheap flights to Madrid"), False, "results for a different destination"),
        Case("G5", "search", "Search for 'weather in Chennai'", "https://www.google.com/search?q=weather+in+Chennai",
             results("weather in Chennai"), True, "results for the requested query"),
        Case("G6", "search", "Search Google for 'electric cars' and show me the results", "https://www.google.com/",
             page("Google", "<form><textarea name='q'>electric cars</textarea></form>"), False, "query typed but not submitted"),
        # navigation
        Case("V1", "navigation", "Open https://www.python.org/downloads", "https://www.python.org/downloads/",
             page("Download Python | Python.org", "<h1>Download the latest version</h1>"), True, "requested page is open"),
        Case("V2", "navigation", "Go to https://news.example.org/today", "https://news.example.org/today",
             page("Today's news", "<h1>Today</h1>"), True, "requested page is open"),
        Case("V3", "navigation", "Visit https://shop.example.net/cart", "https://shop.example.net/cart",
             page("Something went wrong", "<p>We are having trouble loading this page.</p>"), False, "generic error page"),
        Case("V4", "navigation", "Open https://docs.example.org/v2/install", "https://docs.example.org/v1/",
             page("Docs v1", "<h1>Version 1 documentation</h1>"), False, "redirected to a different page"),
        Case("V5", "navigation", "Take me to the contact page of example.org", "https://example.org/contact",
             page("Contact us - Example", "<h1>Contact us</h1>"), True, "contact page is open"),
        Case("V6", "navigation", "Open https://intranet.example.com/hr", "https://intranet.example.com/sso/login?next=/hr",
             page("Single sign-on", "<form><input name='user'><input type='password'></form>"), False, "login wall"),
        Case("V7", "navigation", "Go to https://example.com/blog", "https://example.com/blog",
             page("410 Gone", "<h1>Gone</h1>"), False, "HTTP 410"),
        Case("V8", "navigation", "Open https://maps.example.com", "https://maps.example.com/",
             page("Maps", "<div id='map'></div>"), True, "requested page is open"),
        # captcha / bot checks
        Case("B1", "captcha", "Go to https://tickets.example.com", "https://tickets.example.com/",
             page("tickets.example.com", "<p>Please verify you are a human. Press &amp; Hold.</p>"), False, "press-and-hold human check"),
        Case("B2", "captcha", "Open https://en.wikipedia.org/wiki/Turing_test", WIKI + "Turing_test",
             page("Turing test - Wikipedia", "<h1>Turing test</h1><p>A test of whether a machine can be told apart from a human or a robot.</p>"),
             True, "article about the topic"),
        Case("B3", "captcha", "Go to https://search.example.com/?q=news", "https://search.example.com/?q=news",
             page("Are you a robot?", "<p>To continue, please type the characters below.</p><img src='c.png'><input name='c'>"), False, "text CAPTCHA"),
        Case("B4", "captcha", "Open https://www.example.com/security", "https://www.example.com/security",
             page("Security - Example", "<p>We use reCAPTCHA to protect our forms.</p>"), True, "page only mentions reCAPTCHA"),
        Case("B5", "captcha", "Go to https://forum.example.org", "https://forum.example.org/",
             page("Forum", "<iframe src='https://newassets.hcaptcha.com/captcha/v1/abc/static/hcaptcha.html' width='300' height='80'></iframe>"),
             False, "visible hCaptcha challenge"),
        Case("B6", "captcha", "Go to https://www.google.com/search?q=weather", "https://www.google.com/sorry/index?continue=x",
             page("https://www.google.com/search?q=weather", "<p>Our systems have detected unusual traffic.</p>"), False, "Google bot challenge"),
        # text entry
        Case("E1", "text_entry", "Go to https://notes.example.com and type 'Buy milk' into the note", "https://notes.example.com/",
             page("Notes", "<textarea>Buy milk</textarea>"), True, "text present"),
        Case("E2", "text_entry", "Go to https://notes.example.com and write 'Call Anna at 5' in the text box", "https://notes.example.com/",
             page("Notes", "<textarea></textarea>"), False, "field empty"),
        Case("E3", "text_entry", "In https://mail.example.com, put 'Quarterly report' in the subject line", "https://mail.example.com/compose",
             page("Compose", "<input name='subject' value='Quarterly report'><textarea name='body'></textarea>"), True, "subject filled"),
        Case("E4", "text_entry", "Go to https://notes.example.com and enter exactly: 'Order #4471'", "https://notes.example.com/",
             page("Notes", "<input type='text' value='Order #4417'>"), False, "digits transposed"),
        Case("E5", "text_entry", "Fill the search box on https://shop.example.com with 'red shoes'", "https://shop.example.com/",
             page("Shop", "<input name='q' value='red'>"), False, "only part of the text"),
        Case("E6", "text_entry", "Go to https://forms.example.com and type 'Priya Raman' as the name", "https://forms.example.com/",
             page("Form", "<label>Name <input name='name' value='Priya Raman'></label>"), True, "name filled"),
        # extraction
        Case("Xa", "extraction", "Go to wikipedia.org and tell me how tall Mount Everest is", WIKI + "Mount_Everest", EVEREST,
             True, "answer gives the height", final_answer="Mount Everest is 8,849 metres high."),
        Case("Xb", "extraction", "Go to wikipedia.org and tell me how tall Mount Everest is", WIKI + "Mount_Everest", EVEREST,
             False, "answer lacks the height", final_answer="Mount Everest is the highest mountain on Earth, in the Himalayas."),
        Case("Xc", "extraction", "What year did the Berlin Wall fall? Use Wikipedia.", WIKI + "Berlin_Wall", BERLIN,
             True, "correct year", final_answer="1989"),
        Case("Xd", "extraction", "What year did the Berlin Wall fall? Use Wikipedia.", WIKI + "Berlin_Wall", BERLIN,
             False, "wrong year", final_answer="The Berlin Wall fell in 1961."),
        Case("Xe", "extraction", "Find the capital of Australia on Wikipedia", WIKI + "Australia", AUSTRALIA,
             False, "wrong city", final_answer="The capital of Australia is Sydney."),
        Case("Xf", "extraction", "Find the capital of Australia on Wikipedia", WIKI + "Australia", AUSTRALIA,
             True, "correct city", final_answer="Canberra."),
        Case("Xg", "extraction", "Go to wikipedia.org and extract the boiling point of water", WIKI + "Water", WATER,
             True, "structured extraction has the value", extracted={"boiling point": "100 °C at sea level"}),
        Case("Xh", "extraction", "Get me the opening hours from https://library.example.org", "https://library.example.org/hours", LIBRARY,
             False, "no answer produced"),
        Case("Xi", "extraction", "Look up how many moons Mars has on Wikipedia", WIKI + "Mars", MARS,
             True, "correct count", final_answer="Mars has two moons: Phobos and Deimos."),
        Case("Xj", "extraction", "Extract the population of Tokyo from Wikipedia", WIKI + "Tokyo", TOKYO,
             False, "answer lacks the population", final_answer="Tokyo is the capital of Japan and has many districts."),
        # multi-step
        Case("M1", "multi_step", "Go to github.com, then open the Pricing page", "https://github.com/pricing",
             page("Pricing · GitHub", "<h1>Pricing</h1>"), True, "both steps done",
             task_plan=plan(("navigate", "completed"), ("click", "completed")), last_action="click"),
        Case("M2", "multi_step", "Go to python.org and then open the Downloads page", "https://www.python.org/",
             page("Welcome to Python.org", "<a href='/downloads/'>Downloads</a>"), False, "second step pending",
             task_plan=plan(("navigate", "completed"), ("click", "pending"))),
        Case("M3", "multi_step", "Open example.com, click About, then click Team", "https://example.com/about",
             page("About - Example", "<a href='/team'>Team</a>"), False, "third step pending",
             task_plan=plan(("navigate", "completed"), ("click", "completed"), ("click", "pending"))),
        Case("M4", "multi_step", "Go to wikipedia.org, search for 'Ada Lovelace' and open her article", WIKI + "Ada_Lovelace",
             page("Ada Lovelace - Wikipedia", "<h1>Ada Lovelace</h1>"), True, "all steps done",
             task_plan=plan(("navigate", "completed"), ("type_text", "completed"), ("click", "completed")), last_action="click"),
        Case("M5", "multi_step", "Go to shop.example.com, open Laptops, then add the first laptop to the cart",
             "https://shop.example.com/laptops", page("Laptops - Shop", "<h1>Laptops</h1><p>Your cart is empty.</p>"), False,
             "add-to-cart click dispatched but nothing was added",
             task_plan=plan(("navigate", "completed"), ("click", "completed"), ("click", "completed")), last_action="click"),
        Case("M6", "multi_step", "Go to news.example.org and open the Sports section, then the first article",
             "https://news.example.org/sports/article-1", page("Local team wins final - Sports", "<h1>Local team wins final</h1>"), True,
             "all steps done", task_plan=plan(("navigate", "completed"), ("click", "completed"), ("click", "completed")), last_action="click"),
    ]
    for c in cases:
        if c.category in ("search", "text_entry"):
            c.last_action = "type_text"
    return cases
