import { describe, expect, it } from "vitest";
import { looksLikeDesign } from "./routeIntent";

describe("looksLikeDesign", () => {
  it("routes an explicit CAD part request to design", () => {
    expect(
      looksLikeDesign(
        "Design a rectangular mounting plate 80 mm long, 50 mm wide and 5 mm thick, " +
          "with a 4 mm diameter through-hole in each corner, centred 6 mm in from both edges."
      )
    ).toBe(true);
  });

  it("routes a hex standoff request to design", () => {
    expect(
      looksLikeDesign(
        "Design a hexagonal standoff 20 mm across the flats and 25 mm tall, with a 6 mm hole through it."
      )
    ).toBe(true);
  });

  // Regression: this exact prompt was typed into the live UI and was wrongly
  // routed to the CAD pipeline, which opened FreeCAD instead of running a
  // browser task. The Wikipedia URL contains the literal substring
  // "computer-aided_design", which matches the "design" keyword hint.
  it("routes an 'Open <url> and extract ...' prompt to the web task pipeline, even when the URL contains a design-sounding word", () => {
    expect(
      looksLikeDesign(
        "Open https://en.wikipedia.org/wiki/Computer-aided_design and extract the first paragraph of the article."
      )
    ).toBe(false);
  });

  it("routes a plain extraction prompt to the web task pipeline", () => {
    expect(looksLikeDesign("Open https://example.com and extract the main heading text on the page.")).toBe(false);
  });

  it("routes a search/browse prompt to the web task pipeline", () => {
    expect(looksLikeDesign("Search Google for latest AI agent news")).toBe(false);
  });

  it("routes a login/download prompt to the web task pipeline", () => {
    expect(looksLikeDesign("Log in to the portal and download my invoice")).toBe(false);
  });

  it("routes a booking prompt to the web task pipeline", () => {
    expect(looksLikeDesign("Book a flight to Chennai")).toBe(false);
  });

  it("routes a plain factual question to the web task pipeline", () => {
    expect(looksLikeDesign("What is the capital of France?")).toBe(false);
  });

  // Any URL in the prompt means the user wants a specific page visited, which
  // is unambiguously a browser task -- regardless of what words appear in the
  // URL itself (slugs, article titles, etc. are not under the user's control).
  it("never routes a prompt containing a URL to the design pipeline", () => {
    const urlPrompts = [
      "Open https://en.wikipedia.org/wiki/Mounting_plate_design and read the summary.",
      "Browse https://www.example-bracket-design-shop.com and find the price.",
      "Navigate to https://cad-models.example.com/parts and list the categories."
    ];
    for (const prompt of urlPrompts) {
      expect(looksLikeDesign(prompt)).toBe(false);
    }
  });

  // Structural gap: the current implementation only excludes a URL prompt when
  // it also contains one of a fixed list of verbs ("open", "browse", ...). A
  // URL pasted with no such verb and a design-sounding slug has nothing to save
  // it, and is wrongly routed to the CAD pipeline. This is the general form of
  // the bug the user actually hit, not fixed by the verb list alone.
  it("still routes to the web task pipeline when the prompt has a URL but no listed verb", () => {
    expect(
      looksLikeDesign("https://en.wikipedia.org/wiki/Computer-aided_design -- summarize the history section.")
    ).toBe(false);
  });

  // Regression: a real CAD prompt was misrouted to the web-task pipeline because
  // the web-verb check matched "open" as a whole word anywhere in the text --
  // here inside "open-deck", a legitimate engineering term, not the instruction
  // to open a web page. The verb check must only fire on the prompt's own
  // leading instruction, not any occurrence of the word in the body.
  it("routes a CAD prompt to design even when it contains 'open' as part of engineering vocabulary", () => {
    expect(
      looksLikeDesign(
        "Design an inline 4-cylinder engine block measuring 420 mm long, 140 mm wide, and 200 mm tall " +
          "with four vertical cylinder bores of 80 mm diameter. Surround the four bores with a continuous " +
          "8 mm wide, 110 mm deep open-deck cooling water jacket channel offset 6 mm outward from the bore walls."
      )
    ).toBe(true);
  });

  it("still routes a prompt that genuinely starts with 'Open' as its instruction to the web task pipeline", () => {
    expect(looksLikeDesign("Open the settings panel and enable dark mode, then order the list by name.")).toBe(
      false
    );
  });
});
