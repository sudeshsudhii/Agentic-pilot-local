"""Flatten paper/main.tex into a pandoc-friendly LaTeX file for Word conversion."""
import re, sys
from pathlib import Path
PAPER = Path('/home/user/Agentic-pilot-local/paper')
OUT = Path(sys.argv[1])
FIG = OUT / 'fig'
aux = (PAPER/'main.aux').read_text() + (PAPER/'supplement.aux').read_text()
lab = dict(re.findall(r'\\newlabel\{([^}]*)\}\{\{([^}]*)\}', aux))
lab = {k: re.sub(r'\\mbox\s*\{', '', v) for k, v in lab.items()}
cites = dict(re.findall(r'\\bibcite\{([^}]*)\}\{([^}]*)\}', (PAPER/'main.aux').read_text()))

def expand(text):
    def inc(m):
        p = PAPER / (m.group(1) if m.group(1).endswith('.tex') else m.group(1) + '.tex')
        return expand(p.read_text())
    return re.sub(r'\\input\{([^}]*)\}', inc, text)

def balanced(s, start):
    """Return index just after the balanced {...} starting at s[start]=='{'."""
    d = 0
    for k in range(start, len(s)):
        if s[k] == '{': d += 1
        elif s[k] == '}':
            d -= 1
            if d == 0: return k + 1
    raise ValueError

def grab_caption(block):
    i = block.find('\\caption{')
    if i < 0: return ''
    j = balanced(block, i + len('\\caption'))
    return block[i + len('\\caption{'): j - 1]

s = (PAPER/'main.tex').read_text()
body = s[s.index('\\begin{document}') + len('\\begin{document}'): s.index('\\end{document}')]
body = expand(body)
# title/author are declared inside the document body in main.tex; drop them (the preamble below sets them)
i = body.find('\\title{'); body = body[:i] + body[balanced(body, i + len('\\title')):] if i >= 0 else body
i = body.find('\\author{'); body = body[:i] + body[balanced(body, i + len('\\author')):] if i >= 0 else body
# IEEE numbering: I., II., ... for sections; A., B., ... for subsections
def roman(n):
    vals = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]; r = ''
    for v, c in vals:
        while n >= v: r += c; n -= v
    return r
sec = [0, 0]
def number(m):
    kind, title = m.group(1), m.group(2)
    if kind == 'section':
        sec[0] += 1; sec[1] = 0
        return f'\\section*{{{roman(sec[0])}. {title}}}'
    sec[1] += 1
    return f'\\subsection*{{{chr(64 + sec[1])}. {title}}}'
body = re.sub(r'\\(section|subsection)\{([^}]*)\}', number, body)

# figures -> images (caption kept as text)
figmap = {'fig:arch': ('architecture', '3.4in'), 'fig:verify': ('verification', '3.4in'),
          'fig:sim-sens': ('sensitivity', '3.3in')}
def fig_repl(m):
    block = m.group(0)
    for key, (name, w) in figmap.items():
        if f'\\label{{{key}}}' in block:
            cap = grab_caption(block)
            return f'\\begin{{figure}}\n\\includegraphics[width={w}]{{{FIG}/{name}.png}}\n\\caption{{Fig.~{lab[key]}. {cap}}}\n\\end{{figure}}'
    return block
body = re.sub(r'\\begin\{figure\*?\}.*?\\end\{figure\*?\}', fig_repl, body, flags=re.S)
body = re.sub(r'\\begin\{algorithm\}.*?\\end\{algorithm\}',
              f'\\\\begin{{figure}}\n\\\\includegraphics[width=3.4in]{{{FIG}/algorithm.png}}\n\\\\end{{figure}}', body, flags=re.S)

# table captions: prefix "TABLE n"
def tab_repl(m):
    block = m.group(0)
    if block.count('\\begin{tabular}') == 2:
        env = 'table*' if block.startswith('\\begin{table*}') else 'table'
        k = block.index('\\begin{tabular}', block.index('\\end{tabular}'))
        first = block[:k] + '\\end{' + env + '}'
        lm = re.search(r'\\label\{([^}]*)\}', block)
        num = lab.get(lm.group(1), '') if lm else ''
        second = '\\begin{' + env + '}\n\\caption{TABLE ' + num + ' (continued). Totals by set.}\n' + block[k:]
        return tab_repl_one(first) + '\n\n' + second
    return tab_repl_one(block)
def tab_repl_one(block):
    lm = re.search(r'\\label\{([^}]*)\}', block)
    if lm and lm.group(1) in lab:
        i = block.find('\\caption{')
        if i >= 0:
            block = block[:i] + f'\\caption{{TABLE {lab[lm.group(1)]}. ' + block[i + len('\\caption{'):]
    return block
body = re.sub(r'\\begin\{table\*?\}.*?\\end\{table\*?\}', tab_repl, body, flags=re.S)

# references, citations
body = re.sub(r'\\eqref\{([^}]*)\}', lambda m: f'({lab.get(m.group(1), "?")})', body)
body = re.sub(r'\\ref\{([^}]*)\}', lambda m: lab.get(m.group(1), '?'), body)
body = re.sub(r'\\cite\{([^}]*)\}', lambda m: '[' + ', '.join(cites[k.strip()] for k in m.group(1).split(',')) + ']', body)

# environments / macros pandoc does not handle well
body = body.replace('\\bstctlcite{IEEEexample:BSTcontrol}', '').replace('\\maketitle', '')
body = re.sub(r'\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}', lambda m: '\\textbf{\\textit{Index Terms}}---' + m.group(1).strip(), body, flags=re.S)
body = re.sub(r'\\noindent\\fbox\{\\parbox\{[^}]*\}\{\\small (.*?)\}\}', r'\\textit{\1}', body, flags=re.S)
body = re.sub(r'\\paragraph\{([^}]*)\}', r'\\textit{\1.}', body)
body = re.sub(r'\\label\{[^}]*\}', '', body)
for cmd in ('\\scriptsize', '\\footnotesize', '\\small', '\\raggedright', '\\centering'):
    body = body.replace(cmd + '\n', '\n').replace(cmd + ' ', ' ')
body = re.sub(r'\\setlength\{\\tabcolsep\}\{[^}]*\}', '', body)
body = re.sub(r'\\vspace\{[^}]*\}', '', body)
body = re.sub(r'\\cmidrule\([a-z]*\)\{[^}]*\}|\\cmidrule\{[^}]*\}', '', body)

body = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}', lambda m: '\\begin{equation}' + re.sub(r'\n\s*\n', '\n', m.group(1)) + '\\end{equation}', body, flags=re.S)
# bibliography from the compiled .bbl
bbl = (PAPER/'main.bbl').read_text()
items = re.findall(r'\\bibitem\{([^}]*)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\})', bbl, flags=re.S)
refs = ['\\section*{References}']
for key, txt in items:
    txt = re.sub(r'\\BIBentryALTinterwordspacing|\\BIBentrySTDinterwordspacing|\\BIBentryALTinterwordstretchfactor', '', txt)
    txt = re.sub(r'\\url\{([^}]*)\}', r'\1', txt)
    txt = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', txt)
    refs.append(f'[{cites[key]}] ' + ' '.join(txt.split()) + '\n')
refstxt = '\n\n'.join(refs); body = re.sub(r'\\bibliographystyle\{[^}]*\}\s*\\bibliography\{[^}]*\}', lambda m: refstxt, body)

title = re.search(r'\\title\{(.*?)\}\n', s, flags=re.S).group(1).replace('\\\\', ' ')
pre = (r"\documentclass{article}" "\n" r"\newcommand{\status}[1]{\textsc{#1}}" "\n"
       f"\\title{{{title}}}\n"
       r"\author{Sudesh P, SRM Institute of Science and Technology, sp3782@srmist.edu.in \and Dr. Kanchana M, SRM Institute of Science and Technology, kanchanm@srmist.edu.in}"
       "\n\\begin{document}\n\\maketitle\n")
(OUT/'flat.tex').write_text(pre + body + '\n\\end{document}\n')
print('ok', len(body))
