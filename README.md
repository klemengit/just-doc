# just-doc

Read a PDF, select text, press a key, write what is wrong with it. Every comment
is saved to a JSON file together with the exact text and position it refers to,
so a script or a coding assistant can find the right place in the source.

```bash
just-doc book.pdf          # open for commenting
just-doc book.pdf --read   # print the comments
just-doc book.pdf --export # write book.commented.pdf with the comments inside
```

## Install

With [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/klemengit/just-doc
```

or with pipx: `pipx install git+https://github.com/klemengit/just-doc`.

To try it without installing: `uvx --from git+https://github.com/klemengit/just-doc just-doc book.pdf`.

Needs Python 3.9 or newer; the only dependency is `pypdf`, used for the export. The window is a Chromium, Brave or
Chrome app window if one is installed, otherwise a tab in the default browser.

## Keys

| key | action |
|---|---|
| `a` | highlight the selected text |
| `s` | highlight the selection and write a comment, or edit the comment of the selected highlight |
| `r` | draw a rectangle (for a figure, an equation or code) and comment on it |
| `d` | delete the selected highlight or rectangle (click it first) |
| `u` | undo the last delete |
| `c` | hide or show the comment list, so the page gets the full width |
| `C` | hide or show the highlights on the page, to read the clean text; the selected one stays visible |
| `n` / `p` | go to the next / previous comment, starting from the current page |
| `/` | search the whole PDF: type the text, `Enter`; then `n` / `N` go to the next / previous match and `Esc` ends the search |
| `t` | table of contents: `j` / `k` move, `Enter` goes there, `Esc` closes |
| `h` `j` `k` `l`, `w` `b` `e`, `0` `$` | move the cursor (see below); the page follows it |
| `gg` / `G` | go to the top / bottom of the document; with a number first (`12G`) go to that page |
| `Ctrl` `d` / `Ctrl` `u` | half a page down / up |
| `v` / `V` | start a visual / visual line selection (see below) |
| `Ctrl` + wheel, `Ctrl` `+` / `-` / `0` | zoom the page around the pointer; the toolbar and comment list keep their size |
| `Ctrl` `S` | export a copy of the PDF with the comments inside |
| `?` | show or hide the full key list |
| `Esc` | deselect |

In the comment box, `Enter` saves and `Shift+Enter` starts a new line.

### Cursor and visual selection

A blue block marks the cursor. It moves as in vim, so no mouse is needed:

| key | move |
|---|---|
| `h` / `l` | one character left / right |
| `w` / `b` / `e` | next word / start of the word / end of the word |
| `j` / `k` | one line down / up |
| `0` / `$` | start / end of the line |

A number first repeats the move: `3w`, `5j`. The page scrolls to follow the
cursor, and when you scroll the page the cursor stays on the screen. A click
puts the cursor on the clicked word.

`v` starts a selection at the cursor; `V` does the same but selects whole
lines. The same keys then extend the selection, also onto the next page, and
`o` switches to its other end. Press `a` to highlight the selection or `s` to
highlight and comment on it. `Esc` cancels.

`c` remembers its state between runs.

### Search

`/` searches all pages, not only the ones on the screen. Lower-case text
matches both cases; a capital letter in the query makes the search exact. The
cursor moves to the match, so `v` can start a selection there. While a search
is active, `n` and `N` step through the matches and not through the comments.

## Where comments go

`book.pdf` → `book.comments.json`, in the same folder, rewritten after every
change. Each entry holds the selected `text`, the `comment`, and `rects`: page
number `p` and position in PDF points measured from the top-left corner.

## Sharing the comments

The comments are not stored in the PDF, so other viewers do not show them.
`Ctrl+S` (or `--export`) writes `book.commented.pdf`: a copy of the PDF with
every highlight and comment as an ordinary PDF annotation, readable in Okular,
Evince, Acrobat and others. The original PDF is never changed. The JSON file
stays the working copy; export again after adding comments.

## LaTeX: comment → source line

If `book.synctex.gz` is next to the PDF (compile with `-synctex=1`), `--read`
adds the `.tex` file and line for each comment:

```
[1] p. 37  /path/chapters/chapter_02.tex:1228
    text:    the roots are found with a method that always converges
    comment: too strong, say when it converges
```

Positions refer to the PDF as it was when you commented. Recompiling moves the
text, so comment on a copy of the PDF (and of its `.synctex.gz`) and read the
comments before replacing it.

## Third-party code

`web/pdfjs/` is a copy of [PDF.js](https://mozilla.github.io/pdf.js/) 4.10.38
(Apache License 2.0, see `web/pdfjs/LICENSE`).
