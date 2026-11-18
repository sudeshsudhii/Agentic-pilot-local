"""Prompt templates for Claude-authored headless FreeCAD scripts.

The generated script follows a fixed five-section skeleton: Claude authors only the
dimension constants and ``build()``, while the preview helper and the epilogue
(document creation, file export, preview composition, sentinel printing) are supplied
verbatim so a single LLM slip cannot break artefact discovery.
"""

from __future__ import annotations

SENTINEL_OK = "@@PILOT_DESIGN_OK@@"
SENTINEL_METRICS_BEGIN = "@@PILOT_METRICS_BEGIN@@"
SENTINEL_METRICS_END = "@@PILOT_METRICS_END@@"

#: Verified-working preview composer. ``TechDraw.projectToSVG`` returns an SVG
#: fragment whose own ``<g>`` carries ``transform="scale(1, -1)"``; this helper
#: measures each fragment, lays the views out in a row, and wraps them into one
#: standalone ``<svg>`` document with a correct viewBox.
PREVIEW_HELPER = r'''# ---- PILOT PREVIEW HELPER (supplied; copy verbatim, do not modify) --------
_NUM = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _pilot_frag_bounds(frag):
    """Return (xmin, ymin, xmax, ymax) of a projectToSVG fragment after its scale(1,-1)."""
    xs = []
    ys = []
    for d in re.findall(r'd\s*=\s*"([^"]*)"', frag):
        tokens = re.findall(r"[MmLlAaCcQqSsTtZzHhVv]|" + _NUM, d)
        i = 0
        cmd = None
        while i < len(tokens):
            tok = tokens[i]
            if re.match(r"^[A-Za-z]$", tok):
                cmd = tok
                i += 1
                continue
            if cmd is None:
                i += 1
                continue
            up = cmd.upper()
            if up in ("M", "L", "T"):
                need = 2
            elif up in ("H", "V"):
                need = 1
            elif up == "A":
                need = 7
            elif up == "C":
                need = 6
            elif up in ("S", "Q"):
                need = 4
            else:
                i += 1
                continue
            chunk = tokens[i:i + need]
            if len(chunk) < need:
                break
            vals = [float(v) for v in chunk]
            if up == "A":
                rx, ry = abs(vals[0]), abs(vals[1])
                pts = [(vals[5] - rx, vals[6] - ry), (vals[5] + rx, vals[6] + ry)]
            elif up == "H":
                pts = [(vals[0], 0.0)]
            elif up == "V":
                pts = [(0.0, vals[0])]
            else:
                pts = [(vals[k], vals[k + 1]) for k in range(0, need, 2)]
            for px, py in pts:
                xs.append(px)
                ys.append(py)
            i += need
    circle_re = (
        r'<circle[^>]*cx\s*=\s*"(' + _NUM + r')"[^>]*cy\s*=\s*"(' + _NUM
        + r')"[^>]*r\s*=\s*"(' + _NUM + r')"'
    )
    for m in re.finditer(circle_re, frag):
        cx, cy, rr = float(m.group(1)), float(m.group(2)), float(m.group(3))
        xs.extend([cx - rr, cx + rr])
        ys.extend([cy - rr, cy + rr])
    if not xs or not ys:
        return (0.0, 0.0, 1.0, 1.0)
    return (min(xs), -max(ys), max(xs), -min(ys))


def _pilot_write_preview(shape, path, labels_and_dirs):
    """Compose projectToSVG fragments into one standalone SVG document."""
    gap = 12.0
    label_h = 7.0
    views = []
    for label, direction in labels_and_dirs:
        frag = TechDraw.projectToSVG(shape, App.Vector(*direction))
        if not frag:
            continue
        frag = re.sub(r'\sid\s*=\s*"[^"]*"', "", frag)
        frag = re.sub(r'stroke-width\s*=\s*"[^"]*"', 'stroke-width="0.6"', frag)
        views.append((label, frag, _pilot_frag_bounds(frag)))
    if not views:
        raise RuntimeError("projectToSVG produced no fragments")

    body = []
    cursor_x = 0.0
    total_h = 0.0
    for label, frag, bounds in views:
        x0, y0, x1, y1 = bounds
        w = max(x1 - x0, 1e-6)
        h = max(y1 - y0, 1e-6)
        dx = cursor_x - x0
        dy = -y0 + label_h
        body.append(
            '<g transform="translate(%.5f,%.5f)">\n%s\n'
            '<text x="%.5f" y="%.5f" font-family="sans-serif" font-size="4" '
            'fill="rgb(0,0,0)" stroke="none">%s</text>\n</g>'
            % (dx, dy, frag, x0, y0 - 2.0, label)
        )
        cursor_x += w + gap
        total_h = max(total_h, h + label_h)

    total_w = max(cursor_x - gap, 1e-6)
    pad = 6.0
    full_w = total_w + 2 * pad
    full_h = total_h + 2 * pad
    svg = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        'width="%.2fmm" height="%.2fmm" viewBox="%.5f %.5f %.5f %.5f">\n'
        '<rect x="%.5f" y="%.5f" width="%.5f" height="%.5f" fill="#ffffff" stroke="none"/>\n'
        '<g fill="none" stroke="rgb(0,0,0)" stroke-width="0.6" '
        'stroke-linecap="round" stroke-linejoin="round">\n%s\n</g>\n</svg>\n'
        % (
            full_w, full_h, -pad, -pad, full_w, full_h,
            -pad, -pad, full_w, full_h,
            "\n".join(body),
        )
    )
    with open(path, "w") as handle:
        handle.write(svg)


_PILOT_STAGES = []


def _pilot_snapshot(shape, label):
    """Record one construction stage: writes step_NN.svg and appends to steps.json.

    Call this inside build() right after each stage's shape exists. Stages are
    numbered in call order. Failures are swallowed: a missing stage frame must
    never break the build.
    """
    try:
        index = len(_PILOT_STAGES) + 1
        name = "step_%02d.svg" % index
        _pilot_write_preview(
            shape, os.path.join(OUT_DIR, name), [("", (1, -1, 1))]
        )
        brep = "stage_%02d.brep" % index
        try:
            shape.exportBrep(os.path.join(OUT_DIR, brep))
        except Exception:
            brep = ""
        _PILOT_STAGES.append(
            {"index": index, "label": str(label), "file": name, "solid": brep}
        )
        with open(os.path.join(OUT_DIR, "steps.json"), "w", encoding="utf-8") as fh:
            json.dump(_PILOT_STAGES, fh)
    except Exception as exc:
        print("PILOT_STAGE_FAILED", exc)
# ---- END PILOT PREVIEW HELPER ---------------------------------------------'''

#: Fixed epilogue. Claude copies this verbatim; it is the only code that writes
#: files or prints the sentinels the runner greps for.
EPILOGUE = r'''# ---- PILOT EPILOGUE (supplied; copy verbatim, do not modify) --------------
def _pilot_main():
    """Build the part, export every artefact and report metrics."""
    doc = App.newDocument("Model")
    shape = build()
    obj = doc.addObject("Part::Feature", "Model")
    obj.Shape = shape
    doc.recompute()

    doc.saveAs(os.path.join(OUT_DIR, "model.FCStd"))
    Part.export([obj], os.path.join(OUT_DIR, "model.step"))
    Mesh.export([obj], os.path.join(OUT_DIR, "model.stl"))
    _pilot_write_preview(
        shape,
        os.path.join(OUT_DIR, "preview.svg"),
        [("TOP", (0, 0, 1)), ("FRONT", (0, -1, 0)), ("ISO", (1, -1, 1))],
    )

    bb = shape.BoundBox
    metrics = {
        "bbox_mm": [round(bb.XLength, 3), round(bb.YLength, 3), round(bb.ZLength, 3)],
        "volume_mm3": round(shape.Volume, 3),
    }
    print("@@PILOT_METRICS_BEGIN@@")
    print(json.dumps(metrics))
    print("@@PILOT_METRICS_END@@")
    print("@@PILOT_DESIGN_OK@@")


try:
    _pilot_main()
except Exception:
    traceback.print_exc()
    raise
# ---- END PILOT EPILOGUE ---------------------------------------------------'''


SYSTEM_PROMPT = '''You are a FreeCAD scripting engine. Your only job is to emit one complete, \
runnable FreeCAD Python script for the part the user describes. You output code and nothing else.

HARD RULES
- Reply with the script only. No prose, no explanation, no commentary before or after.
- All dimensions are millimetres. FreeCAD's native unit is mm, so use raw numbers.
- No network access. No file reads. No imports beyond the exact import block below.
- The script must write its outputs into the directory the script itself lives in, derived
  as OUT_DIR below. Never hardcode a path and never rely on the current working directory.
- Build solid geometry with the `Part` module's scripted primitives and booleans
  (Part.makeBox, Part.makeCylinder, Part.makeCone, Part.makeSphere, Part.makeTorus,
  Part.makePolygon / Part.Face / .extrude(), and .cut() .fuse() .common()). Do NOT use
  Sketcher, PartDesign or Draft document objects - they are unreliable headless.
- Do NOT call TechDraw.writePageAsSvg or TechDraw.viewPartAsSvg; neither works headless.
  Preview generation is already handled for you by the supplied helper.

REQUIRED SCRIPT STRUCTURE - emit exactly these five sections in this order:

1. This import block, verbatim:

import os
import re
import json
import math
import traceback

import FreeCAD as App
import Part
import Mesh
import TechDraw

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

2. The PILOT PREVIEW HELPER block, copied verbatim from the user message.

3. Your named dimension constants, in mm, as module-level UPPER_CASE floats, one per
   line, so a human can read the part specification off the top of the file.

4. A single function:

def build():
    """Build and return the finished Part shape.
"""
    ...
    return shape

   Inside `build()`, immediately after each construction stage produces a shape,
   call the supplied helper to record that stage:

       _pilot_snapshot(plate, "Base plate 80 x 50 x 5 mm")
       ...
       _pilot_snapshot(shape, "Corner hole 1")

   Record one stage for the base solid and one after each feature or cut, passing the
   shape as it stands at that moment and a short human-readable label. These frames
   let the application play the build back stage by stage. Always record at least the
   base solid and the finished shape.

   `build()` must return exactly one `Part.Shape` solid - fuse multiple bodies into one.
   This function is the only part of the script you actually design. Keep it readable:
   named constants, one comment per feature. Make every hole a true through hole by
   starting its cutting cylinder below the material and over-running its length.

5. The PILOT EPILOGUE block, copied verbatim from the user message.

The epilogue saves model.FCStd, model.step, model.stl and preview.svg, and prints the
sentinel lines @@PILOT_METRICS_BEGIN@@ / @@PILOT_METRICS_END@@ / @@PILOT_DESIGN_OK@@.
A run that does not print @@PILOT_DESIGN_OK@@ is treated as a failure, so the epilogue
must be present and unmodified.'''


def build_user_prompt(prompt: str) -> str:
    """Return the first-attempt user message for a design prompt."""

    return (
        "Design this part:\n\n"
        + prompt.strip()
        + "\n\nCopy this block verbatim as section 2:\n\n"
        + PREVIEW_HELPER
        + "\n\nCopy this block verbatim as section 5:\n\n"
        + EPILOGUE
        + "\n\nNow emit the complete script."
    )


def build_repair_prompt(prompt: str, script: str, failure: str) -> str:
    """Return the repair user message sent after a failed headless run."""

    return (
        "This FreeCAD script was generated for the following part:\n\n"
        + prompt.strip()
        + "\n\nIt FAILED when run headless under freecadcmd. The script was:\n\n"
        + "```python\n"
        + script
        + "\n```\n\nThe captured failure output was:\n\n"
        + "```\n"
        + failure.strip()[:6000]
        + "\n```\n\nDiagnose the mistake and emit a corrected complete script. Keep the same "
        "five-section structure, keep the PILOT PREVIEW HELPER and PILOT EPILOGUE blocks "
        "byte-identical to the originals, and fix only what is actually broken. "
        "Reply with the script only."
    )
