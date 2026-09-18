"""Build the curated text-to-image showcase from gap_tokenizer_vs_model.html.

The selection is deliberately explicit and the paper caption states that it is curated.
Each source row contains: real, f16 round-trip, f8 round-trip, CC3M, CC12M.
Only the Python standard library and the paper's LaTeX installation are required.
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SOURCE = Path(sys.argv[1]).resolve()
OUTPUT = Path(sys.argv[2]).resolve()
SELECTED_ROWS = [12, 13, 25, 20, 37, 41]


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in text)


html = SOURCE.read_text(encoding="utf-8")
captions = re.findall(
    r"<td class='cap'>(.*?)<span class='id'>.*?</span>", html, flags=re.S
)
captions = [re.sub(r"<[^>]+>", "", caption).strip() for caption in captions]
payloads = re.findall(r"<img src='data:image/jpeg;base64,([^']+)'", html)

if len(captions) != 48 or len(payloads) != 48 * 5:
    raise RuntimeError(
        f"expected 48 captions and 240 images, found {len(captions)} and {len(payloads)}"
    )

with tempfile.TemporaryDirectory(prefix="cobit-t2i-showcase-") as tmp_name:
    tmp = Path(tmp_name)
    cells: list[str] = []
    for panel, row in enumerate(SELECTED_ROWS):
        paths = []
        for source_col, model in ((3, "cc3m"), (4, "cc12m")):
            path = tmp / f"row{row:02d}_{model}.jpg"
            path.write_bytes(base64.b64decode(payloads[(row - 1) * 5 + source_col]))
            paths.append(path)
        prompt = tex_escape(captions[row - 1].rstrip("."))
        cells.append(
            rf"""\begin{{minipage}}[t]{{5.25cm}}
\centering\fontsize{{6.0}}{{6.6}}\selectfont
({chr(97 + panel)}) {prompt}\par\vspace{{1.2pt}}
\begin{{tabular}}{{@{{}}cc@{{}}}}
\textcolor{{cc3}}{{\bfseries CC3M}} & \textcolor{{cc12}}{{\bfseries CC12M}}\\[-1pt]
\includegraphics[width=2.58cm,height=2.58cm]{{{paths[0].as_posix()}}} &
\includegraphics[width=2.58cm,height=2.58cm]{{{paths[1].as_posix()}}}
\end{{tabular}}
\end{{minipage}}"""
        )

    tex = rf"""\documentclass[border=1pt]{{standalone}}
\usepackage{{graphicx,xcolor}}
\definecolor{{cc3}}{{HTML}}{{155E75}}
\definecolor{{cc12}}{{HTML}}{{9A3412}}
\setlength{{\tabcolsep}}{{1.5pt}}
\pagestyle{{empty}}
\begin{{document}}
\begin{{tabular}}{{@{{}}ccc@{{}}}}
{cells[0]} & {cells[1]} & {cells[2]} \\[3pt]
{cells[3]} & {cells[4]} & {cells[5]}
\end{{tabular}}
\end{{document}}
"""
    tex_path = tmp / "t2i_curated_showcase.tex"
    tex_path.write_text(tex, encoding="utf-8")
    subprocess.run(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(tmp),
            str(tex_path),
        ],
        check=True,
        cwd=tmp,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tmp / "t2i_curated_showcase.pdf", OUTPUT)

print(f"wrote {OUTPUT}")
