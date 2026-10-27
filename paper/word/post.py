import sys, copy
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
d = Document(sys.argv[1])
body = d.element.body
paras = d.paragraphs
# 1) section break before the first Heading 1 (Introduction): title block 1 column, body 2 columns
first_h = next(p for p in paras if p.style.name.startswith('Heading 1'))
prev = first_h._p.getprevious()
while prev is not None and prev.tag != qn('w:p'):
    prev = prev.getprevious()
final_sect = body.find(qn('w:sectPr'))
sect1 = copy.deepcopy(final_sect)
for c in sect1.findall(qn('w:cols')): sect1.remove(c)
cols1 = OxmlElement('w:cols'); cols1.set(qn('w:num'), '1'); sect1.append(cols1)
ppr = prev.find(qn('w:pPr'))
if ppr is None:
    ppr = OxmlElement('w:pPr'); prev.insert(0, ppr)
ppr.append(sect1)
for c in final_sect.findall(qn('w:cols')): final_sect.remove(c)
cols2 = OxmlElement('w:cols'); cols2.set(qn('w:num'), '2'); cols2.set(qn('w:space'), str(int(0.25 * 1440)))
final_sect.append(cols2)
t = final_sect.find(qn('w:type'))
if t is None:
    t = OxmlElement('w:type'); final_sect.insert(0, t)
t.set(qn('w:val'), 'continuous')
# 1b) IEEE author block: two authors side by side (name / affiliation / e-mail), borderless table
authors = [p for p in d.paragraphs if p.style.name == 'Author']
if authors:
    blocks = [[x.strip() for x in p.text.split(',')] for p in authors if p.text.strip()]
    anchor = authors[0]._p
    tbl = d.add_table(rows=1, cols=len(blocks))
    tbl.autofit = True
    tblPr = tbl._tbl.tblPr
    bd = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{edge}'); e.set(qn('w:val'), 'nil'); bd.append(e)
    tblPr.append(bd)
    jc = OxmlElement('w:jc'); jc.set(qn('w:val'), 'center'); tblPr.append(jc)
    w = OxmlElement('w:tblW'); w.set(qn('w:type'), 'pct'); w.set(qn('w:w'), '5000')
    old = tblPr.find(qn('w:tblW'))
    if old is not None: tblPr.remove(old)
    tblPr.append(w)
    for cell, lines in zip(tbl.rows[0].cells, blocks):
        cell.paragraphs[0].text = ''
        for i, line in enumerate(lines):
            p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
            r = p.add_run(line); r.font.name = 'Times New Roman'
            r.font.size = Pt(11) if i == 0 else Pt(10)
    anchor.addprevious(tbl._tbl)
    for p in authors:
        p._p.getparent().remove(p._p)
    author_tbl = tbl._tbl
else:
    author_tbl = None

# 1c) title in Times New Roman (drop theme-font overrides); IEEE inline "Abstract---"
for p in d.paragraphs:
    if p.style.name == 'Title':
        for r in p.runs:
            rpr = r._r.get_or_add_rPr()
            rf = rpr.find(qn('w:rFonts'))
            if rf is None:
                rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
            for k in list(rf.attrib):
                del rf.attrib[k]
            for a_ in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
                rf.set(qn('w:' + a_), 'Times New Roman')
            r.font.size = Pt(22)
abs_title = next((p for p in d.paragraphs if p.style.name == 'Abstract Title'), None)
if abs_title is not None:
    nxt = abs_title._p.getnext()
    abs_title._p.getparent().remove(abs_title._p)
    from docx.text.paragraph import Paragraph
    ap = Paragraph(nxt, abs_title._parent)
    first = ap.runs[0]._r if ap.runs else None
    lead = ap.add_run('Abstract\u2014'); lead.italic = True; lead.bold = True
    if first is not None:
        first.addprevious(lead._r)

# 2) tables: 8 pt text, booktabs-like rules, autofit to column
for tbl in d.tables:
    if tbl._tbl is author_tbl: continue
    tblPr = tbl._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge, sz in (('top', 8), ('bottom', 8), ('insideH', 0), ('insideV', 0), ('left', 0), ('right', 0)):
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single' if sz else 'nil'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:space'), '0'); e.set(qn('w:color'), '000000')
        borders.append(e)
    old = tblPr.find(qn('w:tblBorders'))
    if old is not None: tblPr.remove(old)
    tblPr.append(borders)
    lay = tblPr.find(qn('w:tblLayout'))
    if lay is None:
        lay = OxmlElement('w:tblLayout'); tblPr.append(lay)
    lay.set(qn('w:type'), 'autofit')
    for tc in tbl._tbl.iter(qn('w:tcW')):
        tc.set(qn('w:type'), 'auto'); tc.set(qn('w:w'), '0')
    w = tblPr.find(qn('w:tblW'))
    if w is not None: w.set(qn('w:type'), 'pct'); w.set(qn('w:w'), '5000')
    for i, row in enumerate(tbl.rows):
        for cell in row.cells:
            if i == 0:
                tcPr = cell._tc.get_or_add_tcPr()
                b = OxmlElement('w:tcBorders'); bt = OxmlElement('w:bottom')
                bt.set(qn('w:val'), 'single'); bt.set(qn('w:sz'), '4'); bt.set(qn('w:color'), '000000'); b.append(bt); tcPr.append(b)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.size = Pt(7.5); r.font.name = 'Times New Roman'
# merge repeated header cells produced from \\multicolumn
for tbl in d.tables:
    if tbl._tbl is author_tbl: continue
    row = tbl.rows[0]; cells = row.cells; j = 0
    while j < len(cells):
        k = j
        while k + 1 < len(cells) and cells[k + 1].text == cells[j].text and cells[j].text.strip():
            k += 1
        if k > j:
            txt = cells[j].text
            m = cells[j].merge(cells[k])
            for p in m.paragraphs[1:]:
                p._p.getparent().remove(p._p)
            m.paragraphs[0].text = ''
            r = m.paragraphs[0].add_run(txt); r.font.size = Pt(7.5); r.font.name = 'Times New Roman'
            m.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cells = row.cells
        j = k + 1
# 3) captions / figure paragraphs centred, references 8 pt
in_refs = False
for p in d.paragraphs:
    txt = p.text.strip()
    if p.style.name.startswith('Heading') and txt.lower() == 'references': in_refs = True; continue
    if in_refs:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in p.runs: r.font.size = Pt(8)
    if txt.startswith('TABLE ') or txt.startswith('Fig.'):
        for r in p.runs: r.font.size = Pt(8)
d.core_properties.author = 'Sudesh P; Dr. Kanchana M'
d.core_properties.title = 'Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation'
d.save(sys.argv[2])
print('saved')
