# LaTeX → DOCX template

This project turns a conventional LaTeX manuscript into a journal-formatted
DOCX. The same source can also be compiled to PDF with XeLaTeX. The converter
is self-contained and does not require an external Word template.

The implemented layout uses A4 paper, Times New Roman 14 pt, 1.5 line spacing,
a 1.25 cm first-line indent, justified body text, margins of 2.5 cm (top), 1 cm
(right), 2 cm (bottom), and 2.5 cm (left), plus a centered page number in the
footer. Title blocks, abstracts, keywords, run-in headings, captions, tables,
bibliography entries, and explicit page breaks receive dedicated Word styles.

## VS Code and Docker

Only Docker and Make are required on the host; LaTeX, Pandoc, and LibreOffice
remain inside the image. On Linux, Docker must be usable by the account running
VS Code without `sudo`. On Windows, open the project and run the tasks from WSL.

1. Open the project root folder in VS Code
2. Install the recommended **LaTeX Workshop** and **Container Tools** extensions
   when VS Code offers them.
3. Open `template/article.tex`. 
4. run `make docker-build`
5. run `make pdf`


The repository settings use LaTeX Workshop's external-build support, so its
normal **Build LaTeX project** command (`Ctrl+Alt+B` on Linux/Windows) also runs
Docker. Run **LaTeX Workshop: View LaTeX PDF file** once to open
`build/article.pdf` beside the source; it then refreshes after successful builds.
SyncTeX is enabled for source/PDF navigation.

The available commands are:

| Action | VS Code command | Result |
| --- | --- | --- |
| Build the root PDF | Save or press `Ctrl+Alt+B` | `build/<name>.pdf` |
| Build the active TeX file | Press `Ctrl+Shift+B` | `build/<name>.pdf` |
| Build PDF and DOCX | Run task **LaTeX: Build PDF and DOCX (Docker)** | Both formats |
| Build only DOCX | Run task **LaTeX: Build DOCX from active file (Docker)** | `build/<name>.docx` |
| Validate DOCX | Run task **LaTeX: Validate DOCX from active file (Docker)** | Archive and rendering checks |
| Rebuild the image | Run task **Docker: Build LaTeX image** | `latex-to-ntv:local` |
| Delete generated files | Run task **LaTeX: Clean generated files** | Removes `build/` |




## Build

Build the image once:

```sh
make docker-build
```

Compile the included example:

```sh
make docx
```

The result is `build/article.docx`. To compile another source:

```sh
make docx INPUT=path/to/paper.tex OUTPUT=build/paper.docx
```

Compile the same source to PDF:

```sh
make pdf INPUT=template/article.tex
```

Run a structural DOCX check and a headless LibreOffice rendering check:

```sh
make validate
```

The equivalent direct Docker command is:

```sh
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD:/work" latex-to-ntv:local \
  template/article.tex build/article.docx
```

## Authoring rules

- Start run-in sections with `\paragraph*{Section name}`. The Pandoc filter joins
  the heading to the following paragraph and preserves its bold formatting.
- Store bibliography records in `template/references.bib`, cite them with
  `\cite{record-key}`, and print the generated list with
  `\printbibliography[heading=none]`. PDF uses BibLaTeX/Biber and DOCX uses the
  same `.bib` file through Pandoc citeproc. Both use a numeric GOST-style
  bibliography patterned after the original Word manuscript.
- Use normal `equation`, `table`, and `figure` environments. Use `\tag{N}` when
  an equation number must be identical in PDF and DOCX.
- Use PNG, JPEG, or SVG figures for DOCX. TikZ and other TeX-only drawings must
  first be exported to an image format.
- Figure and table captions are numbered automatically in both outputs as
  `Рисунок N – …` and `Таблица N – …`. The template includes working examples;
  replace `assets/example-image.png` with your project image.
- Put `\label{fig:name}` or `\label{tab:name}` immediately after its caption,
  then refer to it with `рисунок~\ref{fig:name}` or
  `таблица~\ref{tab:name}`. DOCX references, DOI values, and URLs are emitted as
  plain text; the Word output intentionally contains no hyperlinks.
- `\newpage` and `\clearpage` are converted into real Word page breaks.
- Abstract and keyword paragraphs are recognized by their `Аннотация.`,
  `Abstract.`, `Ключевые слова:`, or `Keywords:` prefixes.
- Keep document structure semantic. Pandoc converts LaTeX structure and content;
  it does not run TeX while producing DOCX, so arbitrary low-level TeX layout
  commands cannot be reproduced reliably in Word.

At each conversion, `scripts/prepare_reference.py` starts from Pandoc's built-in
reference document and programmatically installs the page setup, centered page
number footer, and reusable Word styles. No source DOCX is required.
