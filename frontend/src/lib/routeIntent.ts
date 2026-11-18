/**
 * Decides whether a prompt typed into the single workbench input is a CAD part
 * to model (routed to the design pipeline) or a web task to run (routed to
 * browser automation).
 */

/** Matches a prompt that names a specific URL to visit. */
const URL_RE = /https?:\/\/\S+/i;

/**
 * Verbs that mark a prompt as an action to perform in a browser, anchored to
 * the start of the prompt. Users phrase a web task as an imperative leading
 * instruction ("Open ...", "Search for ..."), so only the prompt's own
 * leading verb counts -- otherwise a word like "open" inside legitimate
 * engineering vocabulary ("open-deck", "open channel") would wrongly flag an
 * unrelated CAD prompt as a browser task.
 */
const WEB_VERB_START_RE =
  /^\s*(open|search|browse|navigate|log ?in|sign ?in|download|scrape|book|order|email)\b/i;

/** Words that mark a prompt as a CAD part to model rather than a web task to run. */
const DESIGN_HINTS = [
  "design", "cad", "freecad", "model a", "part", "plate", "bracket", "flange",
  "standoff", "spacer", "shaft", "gear", "housing", "enclosure", "mount",
  "bore", "hole", "holes", "thickness", "thick", "diameter", "radius",
  "chamfer", "fillet", "extrude", "revolve", " mm", "millimet"
];

/** True when the prompt reads like a part to model in CAD rather than a web task. */
export function looksLikeDesign(prompt: string): boolean {
  // A URL names a specific page to visit, which is unambiguously a browser
  // task -- regardless of what words appear in the URL itself (an article
  // slug or shop name is not a design instruction). This must be checked
  // before any keyword match, or a URL like ".../Computer-aided_design" gets
  // misrouted to the CAD pipeline by the word "design" inside it.
  if (URL_RE.test(prompt)) {
    return false;
  }

  const text = prompt.toLowerCase();
  if (WEB_VERB_START_RE.test(text)) {
    return false;
  }
  return DESIGN_HINTS.some((hint) => text.includes(hint));
}
