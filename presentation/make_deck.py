"""Build the Final Review deck for the Agentic Pilot case study (python-pptx).

Run from this folder:  python make_deck.py
All numbers come from the report (report/report.pdf); classes are stated on the slides.
"""

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt
from PIL import Image

NAVY = RGBColor(0x12, 0x41, 0x7F)
GOLD = RGBColor(0xC9, 0xA2, 0x27)
INK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x6B, 0x6B, 0x6B)
LIGHT = RGBColor(0xD7, 0xE0, 0xF0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ORANGE = RGBColor(0xD0, 0x7A, 0x1C)
FONT = "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
FOOT = "SRM Institute of Science and Technology  |  21CSC601T Case Studies  |  Final Review"
page_no = [0]


def text(slide, x, y, w, h, s, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, line in enumerate(s.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), bold, color
    return tb


def bullets(slide, items, x=0.6, y=1.55, w=12.1, h=5.3, size=18, gap=10):
    """items: list of (lead, rest). Lead is bold navy, like the reference deck."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (lead, rest) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r0 = p.add_run()
        r0.text = "▪  "
        r0.font.name, r0.font.size, r0.font.color.rgb = FONT, Pt(size - 4), GOLD
        if lead:
            r = p.add_run()
            r.text = lead + " "
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), True, NAVY
        r = p.add_run()
        r.text = rest
        r.font.name, r.font.size, r.font.color.rgb = FONT, Pt(size), INK
    return tb


def picture(slide, path, x, y, max_w, max_h):
    w, h = Image.open(path).size
    scale = min(max_w / w, max_h / h)
    pw, ph = w * scale, h * scale
    return slide.shapes.add_picture(path, Inches(x + (max_w - pw) / 2), Inches(y + (max_h - ph) / 2), Inches(pw), Inches(ph))


def footer(slide):
    page_no[0] += 1
    slide.shapes.add_picture("img/srm_logo.jpg", Inches(0.45), Inches(7.02), height=Inches(0.32))
    text(slide, 1.5, 7.05, 9, 0.3, FOOT, size=9, color=GREY)
    text(slide, 12.3, 7.05, 0.6, 0.3, str(page_no[0]), size=10, color=GREY, align=PP_ALIGN.RIGHT)
    ln = slide.shapes.add_connector(1, Inches(0.45), Inches(6.95), Inches(12.9), Inches(6.95))
    ln.line.color.rgb = LIGHT


def content(label, title):
    s = prs.slides.add_slide(BLANK)
    text(s, 0.5, 0.33, 11, 0.3, label.upper(), size=12, bold=True, color=GOLD)
    text(s, 0.5, 0.62, 12.2, 0.6, title, size=26, bold=True, color=NAVY)
    footer(s)
    return s


def table(slide, rows, x, y, w, col_w, size=13, row_h=0.42):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    t = shape.table
    for j, cw in enumerate(col_w):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = val
            p = c.text_frame.paragraphs[0]
            for r in p.runs:
                r.font.name, r.font.size = FONT, Pt(size)
                r.font.bold = i == 0
                r.font.color.rgb = WHITE if i == 0 else INK
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (RGBColor(0xF2, 0xF5, 0xFA) if i % 2 == 0 else WHITE)
            c.margin_top = c.margin_bottom = Inches(0.04)
    return t


def bar_chart(slide, cats, series, x, y, w, h, colors, maxv=None, fmt='0.00', title=None):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = len(series) > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(12)
    if title:
        ch.has_title = True
        ch.chart_title.text_frame.text = title
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
        ch.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = NAVY
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xE3, 0xE3, 0xE3)
    va.tick_labels.font.size = Pt(11)
    if maxv is not None:
        va.maximum_scale, va.minimum_scale = maxv, 0
    ch.category_axis.tick_labels.font.size = Pt(12)
    plot = ch.plots[0]
    plot.gap_width = 70
    plot.has_data_labels = True
    plot.data_labels.number_format = fmt
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(11)
    plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    for s, col in zip(plot.series, colors):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = col
    return ch


def note(slide, s, y=6.45):
    text(slide, 0.6, y, 12.1, 0.45, s, size=11, color=GREY)


# 1. Title -------------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
text(s, 1.0, 1.3, 11.3, 1.9, "Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation", size=32, bold=True, color=WHITE)
text(s, 1.0, 3.45, 11, 0.5, "A browser agent that runs its models on your machine and says “done” only when the page shows it", size=18, color=LIGHT)
text(s, 1.0, 4.15, 11, 0.5, "Final Review  |  21CSC601T Case Studies", size=16, color=LIGHT)
text(s, 1.0, 4.85, 11.5, 1.0, "Sudesh P  |  RA2512005010025  |  M.Tech CSE\nGuided by: Dr. Kanchana M, Professor, Department of Computing Technologies\nSRM Institute of Science and Technology, Kattankulathur  |  November 2026", size=13, color=WHITE)
box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(6.15), Inches(1.95), Inches(0.75))
box.fill.solid(); box.fill.fore_color.rgb = WHITE; box.line.fill.background()
s.shapes.add_picture("img/srm_logo.jpg", Inches(1.08), Inches(6.25), height=Inches(0.55))
page_no[0] += 1

# 2. Roadmap -----------------------------------------------------------------------------------
s = content("A quick roadmap", "Here is what I will walk you through")
items = ["The problem I looked at", "What I set out to do", "How I went about it", "How the system works",
         "What the data told me", "The ideas that guided me", "What I recommend", "Can it really be done?",
         "Who benefits, and how", "What I learned"]
for i, it in enumerate(items):
    col, row = divmod(i, 5)
    x, y = 0.9 + col * 6.1, 1.6 + row * 0.98
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(0.5), Inches(0.5))
    c.fill.solid(); c.fill.fore_color.rgb = NAVY; c.line.fill.background()
    tf = c.text_frame; tf.word_wrap = False; tf.margin_left = tf.margin_right = 0; tf.text = str(i + 1)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size, p.runs[0].font.bold, p.runs[0].font.color.rgb = Pt(14), True, WHITE
    text(s, x + 0.75, y + 0.05, 4.8, 0.45, it, size=18)

# 3. Problem -----------------------------------------------------------------------------------
s = content("The problem", "The problem I looked at")
bullets(s, [
    ("AI agents now use the browser for us:", "they open pages, fill in forms and read results."),
    ("They can say “done” too early.", "An agent opens Google, types nothing, and reports the search finished. Every action worked; the task did not. I call this premature completion."),
    ("Usually the model itself decides it is done,", "and models correcting themselves without outside feedback are not reliable (Huang et al., ICLR 2024)."),
    ("Many agents send every screenshot to a hosted model.", "Those screens carry names, messages and account data."),
    ("So the question was:", "can an agent keep its data on my machine and also refuse to claim success until the screen shows it, and what does that cost?"),
])

# 4. Goal --------------------------------------------------------------------------------------
s = content("The goal", "What I set out to do")
bullets(s, [
    ("Separate “the action ran” from “the task is done”", "inside the agent's own loop, with a rule over what the page actually shows."),
    ("Keep inference local:", "the model client talks only to a model server on this machine (Ollama on 127.0.0.1)."),
    ("Store the evidence", "behind every completion decision, so anyone can check it later."),
    ("Measure honestly", "what the rule catches, what it rejects by mistake, and how long it takes, on test cases written before the rule was run on them."),
    ("Label every number:", "measured (ACTUAL) or simulated (SYNTHETIC), never mixed."),
])

# 5. Approach ----------------------------------------------------------------------------------
s = content("The approach", "How I went about it")
bullets(s, [
    ("I built the system:", "about 11,000 lines of Python (FastAPI, LangGraph, Playwright, Chroma, Ollama), open source under MIT."),
    ("I tested the completion gate", "on 92 constructed page states in three sets: 38 design, 12 held-out, and 42 held-out states frozen in Git before testing."),
    ("I measured the components:", "latency, memory retrieval, recovery classification, and every network connection in 70 agent episodes."),
    ("I analysed with small-sample statistics:", "Wilson 95% intervals and exact McNemar tests on paired decisions."),
    ("I ran a seeded simulation", "to see what the measured parts imply for whole tasks. It is labelled SYNTHETIC and depends on assumed planner behaviour."),
])

# 6. Loops -------------------------------------------------------------------------------------
s = content("The approach", "A normal agent loop next to mine")
picture(s, "img/loops.png", 0.8, 1.45, 11.7, 4.6)
note(s, "Shaded boxes are what a normal loop does not have: the gate checks the page after the action, and only a passing state can end the task as Completed.", y=6.2)

# 7. Architecture ------------------------------------------------------------------------------
s = content("How the system works", "System architecture")
picture(s, "img/architecture.png", 0.5, 1.4, 7.4, 5.3)
bullets(s, [
    ("Desktop client", "(React + Tauri) sends a request to a FastAPI service bound to 127.0.0.1."),
    ("LangGraph control loop", "with eleven nodes; only the verification node can end a task as Completed."),
    ("Playwright + Chromium", "gives each task its own page and records before/after screenshots."),
    ("Local models", "via Ollama: Qwen2.5, Qwen3.5, DeepSeek-R1 (1.5B–7B) and a small vision model."),
    ("Local stores:", "SQLite for events, Chroma for memory, an evidence folder per task."),
], x=8.1, y=1.5, w=4.9, size=15, gap=8)

# 8. How a task moves --------------------------------------------------------------------------
s = content("How the system works", "How a request moves through the loop")
picture(s, "img/algorithm.png", 7.3, 1.3, 5.6, 5.55)
bullets(s, [
    ("Understand the request.", "A small model extracts action, site, target and risk; long requests are split into steps."),
    ("Observe and plan.", "Up to 50 ranked page elements, sanitised against prompt injection, go to the planner with memory."),
    ("Act and read back.", "Navigate, click, type, scroll or extract; typed text is read back from the page."),
    ("Recover.", "Three inline retries, then the recovery engine (up to six attempts in total)."),
    ("Verify.", "Only when the gate Φ holds is the task reported complete; the evidence is stored."),
], x=0.6, y=1.5, w=6.5, size=16)

# 9. Algorithms --------------------------------------------------------------------------------
s = content("The algorithms", "Which algorithm I used, where, and why")
table(s, [
    ["Algorithm / method", "Where it is used", "Why I chose it"],
    ["LangGraph state machine (ReAct-style loop)", "Control loop", "One guarded path to Completed, checkpoints after every node"],
    ["Conjunctive rule Φ (execution monitoring)", "Verification node", "Fast, inspectable, fails closed, no model call"],
    ["Bot-check pre-check β", "Before Φ", "Hand CAPTCHAs to the user instead of solving them"],
    ["Element ranking + sanitising", "Observation", "Small models need a short, safe element list"],
    ["Failure classifier + strategy table", "Recovery engine", "Retry, other selector, vision fallback, replan"],
    ["Vector retrieval (Chroma)", "Memory", "Reuse outcomes of earlier tasks"],
    ["Loopback endpoint check", "Model client", "Refuse any non-local model server by default"],
    ["Wilson interval, exact McNemar, Monte Carlo", "Evaluation", "Right tools for small paired samples"],
], 0.6, 1.5, 12.1, [4.3, 2.9, 4.9], size=13)

# 10. Gate checks ------------------------------------------------------------------------------
s = content("The completion gate", "The six checks behind “done”")
table(s, [
    ["Check", "It fails when…"],
    ["E  Error state", "error URL, “not found” title, bot-check page, or an unexpected sign-in page"],
    ["H  Search home", "still on the search engine's home page when a search was asked for"],
    ["Q  Query", "the results page is for a different query than the one requested"],
    ["T  Typed text", "the text the user asked to enter is not in any input box"],
    ["X  Extraction", "an extraction request has no answer mentioning what was asked"],
    ["R  Remaining steps", "a multi-step plan still has a pending step"],
    ["β  Bot-check", "a CAPTCHA appears: the task stops as Blocked and goes to the user"],
], 0.6, 1.5, 12.1, [3.0, 9.1], size=15, row_h=0.5)
note(s, "Each check switches on only when its trigger words appear in the request. A check that cannot read the page also fails, so the gate fails closed.", y=5.9)

# 11. One claim's path -------------------------------------------------------------------------
s = content("The completion gate", "What happens to one completion claim")
picture(s, "img/verification.png", 0.5, 1.4, 8.0, 4.6)
bullets(s, [
    ("Example:", "“Search Google for ‘electric cars’ and show me the results.” The query was typed but not submitted."),
    ("The agent claims done.", "The page is still google.com with no query."),
    ("Check H fails,", "so the claim is rejected and the agent goes back to work."),
    ("The decision and the values it used", "are written to the task's evidence folder."),
], x=8.7, y=1.5, w=4.3, size=15)
note(s, "Held-out-2 case G6 (ACTUAL): oracle says unsatisfied; gate decision: rejected.", y=6.2)

# 12. Evidence: gate ---------------------------------------------------------------------------
s = content("The evidence", "What the data told me about the gate")
bar_chart(s, ["Design (before fixes)", "Design (after fixes)", "Held-out 1", "Held-out 2 (frozen)"],
          [("Unsatisfied states withheld", (15 / 23, 20 / 23, 2 / 5, 9 / 22)),
           ("Satisfied states rejected", (3 / 15, 1 / 15, 1 / 7, 1 / 20))],
          0.5, 1.4, 7.0, 5.0, [NAVY, ORANGE], maxv=1.0)
bullets(s, [
    ("Held-out 2:", "9 of 22 premature claims withheld (95% CI 0.23–0.61); 1 of 20 good states rejected."),
    ("Better than accepting every claim:", "exact McNemar p = 0.021."),
    ("Not yet clearly better than the error check alone:", "p = 0.070 (7 vs 1)."),
    ("Design states: 20 of 23,", "because the rules were fixed on them. New wording escapes the checks."),
], x=7.8, y=1.5, w=5.2, size=15)
note(s, "ACTUAL: constructed states, the real verification node with stubbed I/O. Counts in report Table 3.4.", y=6.45)

# 13. Ablation ---------------------------------------------------------------------------------
s = content("The evidence", "How much each check contributes")
bar_chart(s, ["Full Φ", "−E", "−H", "−Q", "−T", "−X", "−R", "−β"],
          [("False completions on design states (of 23)", (3, 8, 7, 4, 6, 6, 4, 5))],
          0.5, 1.4, 7.4, 5.0, [NAVY], fmt='0', title="False completions when one check is removed (of 23)")
bullets(s, [
    ("Removing E or H hurts most", "on the design states (3 → 8 and 3 → 7)."),
    ("On held-out states", "any single removal changes at most three decisions; removing Q or X changes none."),
    ("So coverage limits the gate,", "not the strength of any one check."),
], x=8.2, y=1.6, w=4.8, size=16)
note(s, "ACTUAL. With at most five discordant states the smallest attainable p is 0.063, so this ablation is descriptive.", y=6.45)

# 14. Speed and privacy ------------------------------------------------------------------------
s = content("The evidence", "Speed and privacy")
table(s, [
    ["Operation (self-hosted pages, 30 runs)", "Median (ms)"],
    ["Navigate", "17.1"], ["Click", "65.2"], ["Fill text", "12.5"],
    ["DOM extraction", "76.4"], ["Screenshot", "61.3"], ["Gate Φ", "5.2"],
], 0.6, 1.5, 5.6, [4.0, 1.6], size=14, row_h=0.48)
bullets(s, [
    ("A full gate decision:", "median 26.8 ms over 83 decisions (max 34.6 ms), no model call, zero tokens."),
    ("70 agent episodes,", "every socket connection of the agent's Python processes logged: all 555 went to 127.0.0.1. A rerun on a clean commit gave the same."),
    ("By default the model client refuses", "any non-loopback server unless PILOT_ALLOW_REMOTE_MODEL=true."),
    ("Scope:", "a scripted stand-in model server; DNS, UDP and the browser itself were not logged."),
], x=6.6, y=1.5, w=6.4, size=15)

# 15. Memory and recovery ----------------------------------------------------------------------
s = content("The evidence", "Two weaknesses the measurements exposed")
bullets(s, [
    ("Memory has no relevance threshold.", "On 10 queries over 22 records: P@3 0.52 (the most this corpus allows), R@3 1.00, MRR 0.93, but in 3 of 10 queries the top record was irrelevant or retrieval failed."),
    ("Recovery misses a missing confirmation.", "Of 6 failure messages, the one where the task ended without its goal met was classed “unknown” and got the generic retry sequence."),
    ("Stored evidence found real bugs,", "now fixed: fixed extraction text, a node that trusted the planner's reasoning, an over-eager bot-check rule, and inert features."),
    ("Oracle and tests:", "the end-to-end oracle agreed on all 114 scripted trajectories; 144 of 147 tests pass (3 need live web or a model)."),
])

# 16. Simulation -------------------------------------------------------------------------------
s = content("The evidence", "What the simulation suggests (SYNTHETIC)")
picture(s, "img/sensitivity.png", 0.5, 1.45, 7.2, 4.6)
bullets(s, [
    ("False completions:", "19 with Φ vs 28 without, in 100 scenarios."),
    ("Decisions:", "52 vs 46 correct of 74 (p = 0.15); not significant."),
    ("Overhead:", "+2.6% episode time with Φ; +14% for a model self-check."),
    ("The benefit depends on π,", "how often the planner claims done too early, which is not measured yet."),
], x=7.9, y=1.5, w=5.1, size=15)
note(s, "SYNTHETIC: seeded simulation v2, revised post hoc, conditional on ASSUMED planner behaviour. Not a measurement of the agent.", y=6.3)

# 17. Theory -----------------------------------------------------------------------------------
s = content("The thinking behind it", "The ideas that guided me")
bullets(s, [
    ("Execution monitoring:", "check a plan's expected conditions against the observed world (PLANEX, robotics)."),
    ("State machines:", "if only one guarded edge leads to Completed, the guarantee comes from the graph, not the model."),
    ("Fail-closed rules:", "a conjunction withholds on any failed check; more checks mean fewer false completions and more false rejections."),
    ("Small-sample statistics:", "Wilson intervals and exact McNemar; some tests simply cannot reach significance with three discordant cases."),
    ("Privacy by design:", "keep data on the device by default; make sending it elsewhere an explicit choice."),
])

# 18. Recommendation ---------------------------------------------------------------------------
s = content("The answer", "What I recommend")
bullets(s, [
    ("Keep the rule-based gate", "as the fail-closed authority on “done”: it beats accepting every claim and costs milliseconds."),
    ("Widen its checks:", "more trigger words for extraction and text entry, and answers that must contain a value of the requested type."),
    ("Add a relevance threshold", "to memory retrieval."),
    ("Add a missing-confirmation class", "to recovery that re-reads the page before re-planning."),
    ("Use a model judge only where no rule fires,", "and measure its errors separately."),
])

# 19. Feasibility ------------------------------------------------------------------------------
s = content("A reality check", "Can it really be done?")
table(s, [
    ["The question", "My honest view", "Notes"],
    ["Technically, can it be built?", "Yes. It is built and open source.", "Desktop backend is designed, not built"],
    ["Does it run on a normal machine?", "Yes, with 1.5B–7B local models via Ollama", "Small models plan less well"],
    ["What does the gate cost?", "About 27 ms per decision, no model call", "Rejections add re-planning time"],
    ["Is the data kept local?", "Yes for the agent's Python processes, by default", "Browser and DNS not yet instrumented"],
    ["What could go wrong?", "Wider checks may reject good states", "Keep a frozen held-out set"],
    ["What is the next step?", "Run the released 40-task harness with local models", "Oracle already validated"],
], 0.6, 1.5, 12.1, [3.3, 4.6, 4.2], size=14, row_h=0.55)

# 20. Benefits ---------------------------------------------------------------------------------
s = content("The difference it makes", "Who benefits, and how")
bullets(s, [
    ("Users:", "an honest “not done” instead of a false “done”, and screens that stay on their own machine."),
    ("Developers of agents:", "a cheap, testable completion check and an evidence trail that finds bugs."),
    ("Researchers:", "evaluation code, frozen data and an end-to-end harness to measure task-level effects."),
    ("Organisations handling personal data:", "local inference supports data minimisation under the DPDP Act, 2023."),
])

# 21. Lessons ----------------------------------------------------------------------------------
s = content("Wrapping up", "What I learned")
bullets(s, [
    ("In short:", "a successful action is not a finished task, and checking the page before saying “done” is cheap."),
    ("Test on cases written afterwards:", "20 of 23 on design states fell to 9 of 22 on frozen ones; that gap was the most useful number."),
    ("Evidence pays for itself:", "storing what each decision used exposed bugs the tests missed."),
    ("Label every number:", "keeping measured and simulated results apart kept the claims honest."),
    ("Not covered this time:", "task success of the full agent with a model planner; the harness for it is released."),
])

# 22. Sources ----------------------------------------------------------------------------------
s = content("Sources", "Sources and thanks")
bullets(s, [
    ("", "S. Yao et al., “ReAct: Synergizing reasoning and acting in language models,” ICLR, 2023."),
    ("", "S. Zhou et al., “WebArena: A realistic web environment for building autonomous agents,” ICLR, 2024."),
    ("", "H. He et al., “WebVoyager: Building an end-to-end web agent with large multimodal models,” ACL, 2024."),
    ("", "J. Huang et al., “Large language models cannot self-correct reasoning yet,” ICLR, 2024."),
    ("", "R. E. Fikes, P. E. Hart and N. J. Nilsson, “Learning and executing generalized robot plans,” Artificial Intelligence, 1972."),
    ("", "K. Greshake et al., “Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,” ACM AISec, 2023."),
    ("", "E. B. Wilson, 1927; Q. McNemar, 1947 (interval and paired test)."),
    ("", "Code and data: github.com/sudeshsudhii/Agentic-pilot-local (branch ccr-4b8200f0-5i3k5m). Full list of references in the report."),
    ("", "With thanks to my guide, Dr. Kanchana M, and the Department of Computing Technologies, SRM IST. AI assistance (Claude) is disclosed in the report."),
], size=14, gap=6)

# 23. Thank you --------------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
text(s, 0, 2.7, 13.333, 1.0, "Thank you", size=44, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
text(s, 0, 3.7, 13.333, 0.6, "I would be glad to take your questions", size=18, color=LIGHT, align=PP_ALIGN.CENTER)
box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(5.69), Inches(5.2), Inches(1.95), Inches(0.75))
box.fill.solid(); box.fill.fore_color.rgb = WHITE; box.line.fill.background()
s.shapes.add_picture("img/srm_logo.jpg", Inches(5.77), Inches(5.3), height=Inches(0.55))

prs.save("Agentic_Pilot_Final_Review.pptx")
print("slides:", len(prs.slides))
