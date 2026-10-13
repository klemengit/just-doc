# just-doc

Read a PDF, select text, press a key, write what is wrong with it. Every comment
is saved to a JSON file together with the exact text and position it refers to,
so a script or a coding assistant can find the right place in the source.

```bash
just-doc book.pdf          # open for commenting
just-doc book.pdf --read   # print the comments
just-doc book.pdf --export # write book.commented.pdf with the comments inside
just-doc notes.md          # a markdown file works the same way
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
| `a` | highlight the selection and write a comment, or edit the comment of the selected mark; `Enter` in an empty box leaves a plain highlight |
| `s` | strike through the selection: this text should be deleted |
| `r` | draw a rectangle (for a figure, an equation or code) and comment on it |
| `d` | delete the selected highlight or rectangle (click it first) |
| `u` | undo the last delete |
| `c` | hide or show the comment list, so the page gets the full width |
| `C` | hide or show the highlights and the link marks on the page, to read the clean text; the selected one stays visible |
| `n` / `p` | go to the next / previous comment, starting from the current page; the cursor goes to the start of its text |
| `Enter` | follow the link under the cursor (a click on a link does the same); `Tab` / `Shift` `Tab` move the cursor to the next / previous link on the page |
| `Ctrl` `o` / `Ctrl` `i` | jump back to where you were before a jump / forward again |
| `/` | search the whole PDF: type the text, `Enter`; then `n` / `N` go to the next / previous match and `Esc` ends the search |
| `t` | table of contents: `j` / `k` move, `Enter` goes there, `Esc` closes |
| `h` `j` `k` `l`, `w` `b` `e`, `0` `$` | move the cursor (see below); the page follows it |
| `gg` / `G` | go to the top / bottom of the document; with a number first (`12G`) go to that page |
| `Ctrl` `d` / `Ctrl` `u` | half a page down / up |
| `←` / `→` | go to the previous / next page |
| `P` | single page view: show one page at a time, fitted to the window; `P` again goes back to the continuous view and the zoom from before |
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
`o` switches to its other end. Press `a` to comment on the selection or `s` to
strike it through. `Esc` cancels.

`c` and `P` remember their state between runs.

In the single page view, `j` on the last line and `k` on the first line turn
the page, and so do `PageDown` and `PageUp`. A selection stays on its page.

### Links and jumping back

Links inside the PDF (a reference to an equation, a citation, an entry of the
printed contents) are marked with a blue underline and work: put the cursor on one and press `Enter`, or click it.
`Ctrl+o` then returns to the place of the link, with the cursor where it was.
The same key returns from every other jump: a search, the contents panel,
`n` / `p`, `gg`, `G`. `Ctrl+i` goes forward again. A web link opens in the
browser.

### Search

`/` searches all pages, not only the ones on the screen. Lower-case text
matches both cases; a capital letter in the query makes the search exact. The
cursor moves to the match, so `v` can start a selection there. While a search
is active, `n` and `N` step through the matches and not through the comments.

## Where comments go

`book.pdf` → `book.comments.json`, in the same folder, rewritten after every
change. Each entry holds the selected `text`, the `comment`, and `rects`: page
number `p` and position in PDF points measured from the top-left corner.
An entry with `kind` `strike` is struck-through text that should be deleted,
and `kind` `box` is a rectangle; an entry without `kind` is a highlight.

## Sharing the comments

The comments are not stored in the PDF, so other viewers do not show them.
`Ctrl+S` (or `--export`) writes `book.commented.pdf`: a copy of the PDF with
every highlight, strike-through and comment as an ordinary PDF annotation, readable in Okular,
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

## Markdown files

`just-doc notes.md` converts the file to a PDF with [pandoc](https://pandoc.org)
and opens that, so pandoc must be installed (with [typst](https://typst.app)
or a LaTeX installation to make the PDF; typst is used when it is found). The
PDF is kept in `~/.cache/just-doc` and made again when the markdown file has
changed. Comments go to `notes.comments.json` next to the markdown file, and
`--export` writes `notes.commented.pdf` there.

`--read` adds the line in the markdown file for each comment. It finds the
line by searching for the selected text, so it also works after the file was
edited elsewhere; a text that occurs more than once gets its first line and a
note:

```
[1] p. 1  notes.md:3 (first of 2 places)
    text:    always converges
    comment: too strong
```

The positions of the highlights on the page refer to the PDF as it was when
you commented, as with LaTeX.

## Third-party code

`web/pdfjs/` is a copy of [PDF.js](https://mozilla.github.io/pdf.js/) 4.10.38
(Apache License 2.0, see `web/pdfjs/LICENSE`).
