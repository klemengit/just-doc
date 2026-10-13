# just-doc

Read a PDF, select text, press a key, write what is wrong with it. Every comment
is saved to a JSON file together with the exact text and position it refers to,
so a script or a coding assistant can find the right place in the source.

```bash
just-doc book.pdf          # open for commenting
just-doc book.pdf --read   # print the comments
just-doc book.pdf --export # write book.commented.pdf with the comments inside
just-doc notes.md          # a markdown file works the same way
just-doc book.pdf --wait   # open it, wait for Ctrl+Enter, then print the comments
just-doc book.pdf --reply 2 "text"   # add a reply to comment 2
just-doc --guide           # how a coding assistant reviews a document with you
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
| `A` | add a reply to the selected comment (see "Reviewing with a coding assistant") |
| `gn` | go to the next comment with a new reply |
| `D` | show or hide the comments that are done |
| `Ctrl` `Enter` | hand the comments over to the `just-doc --wait` that is waiting for them |
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
| `f` / `F` + a character | move the cursor to that character after / before it on the line (`fa`, `3fa`); the wait for the character ends after 1.5 s |
| `gg` / `G` | go to the top / bottom of the document; with a number first (`12G`) go to that page |
| `Ctrl` `d` / `Ctrl` `u` | half a page down / up |
| `zt` / `zz` / `zb` | scroll so that the cursor line is at the top / in the middle / at the bottom of the window; also in a selection |
| `←` / `→` | go to the previous / next page |
| `P` | single page view: show one page at a time, fitted to the window; `P` again goes back to the continuous view and the zoom from before |
| `v` / `V` | start a visual / visual line selection (see below) |
| `Ctrl` + wheel, `Ctrl` `+` / `-` / `0` | zoom the page around the pointer; the toolbar and comment list keep their size |
| `Ctrl` `S` | export a copy of the PDF with the comments inside |
| `H` / `L` | previous / next tab, when several documents are open; `Alt` `←` / `Alt` `→` do the same |
| `Ctrl` `w` | close the tab; `Alt` `w` does the same |
| `?` | show or hide the full key list |
| `Esc` | deselect |

In the comment box, `Enter` saves and `Shift+Enter` starts a new line.

The browser's own shortcuts (print, find, history, bookmarks and so on) are
switched off in the window. Copy (`Ctrl+C`), reload (`Ctrl+R`, `F5`), full
screen (`F11`) and the developer tools (`F12`) still work.

### Tabs

The first `just-doc book.pdf` opens the window. While it runs, every further
`just-doc other.pdf` adds the document as a new tab of the same window and
returns at once. `H` and `L` change the tab and `Ctrl+w` closes it; the
tab bar shows only when more than one document is open. Each tab keeps its
page, zoom, cursor and search.

All tabs belong to the first command, so stopping it with `Ctrl+C` closes
them all. If the window was closed but the command still runs, the next
`just-doc` opens a new window with the tabs.

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

In a selection, `i` and one more key select the thing around the cursor:

| keys | select |
|---|---|
| `iw` | the word |
| `is` | the sentence |
| `ip` | the paragraph |
| `i(` `i[` `i{` `i<` | the text inside the brackets around the cursor |
| `i"` `i'` | the text inside the quotes, straight or typographic |

So `vis` `a` comments on the sentence under the cursor. The selection can be
extended with the usual keys afterwards.

In vim, `a` is the "around" form (`va(` takes the brackets too). Here `a` in a
selection writes the comment, so `va(` does not exist; the capital `A` takes
its place: `vA(`, `vA"`.

A sentence ends at `.`, `?` or `!` before a capital letter, so it can stop too
early after an abbreviation that is not known. A PDF stores lines and not
paragraphs, so a paragraph is guessed from a larger gap between lines, an
indented first line or a change of the text size. Both stay on one page. A
margin note next to the text is left out of the sentence or paragraph, and it
is a paragraph of its own.

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

`before` and `after` hold the letters and digits around the text, to find it
again in a changed document (see "When the document changes"); `was` is the
text as it was when it has changed since, and `lost` marks a comment whose
text is not found any more.

A comment can have `replies`, a list of entries with `text`, the time `at` and
`from`, the name given with `--reply`. A reply without `from` was written in
the window.

## Reviewing with a coding assistant

A coding assistant (Claude Code, opencode, pi or any other that can run shell
commands) can answer your comments in the window and fix the source, so the
whole review happens in just-doc. Tell it:

> Run `just-doc --guide`, then review `notes.md` with me.

`just-doc --guide` prints the instructions for the assistant: which commands
to run and how to read their output. Nothing is set up for a particular
assistant; it only runs the three commands below.

The round goes like this:

1. The assistant runs `just-doc notes.md --wait`. The window opens.
2. You write comments and press `Ctrl+Enter`. The message at the bottom says
   whether somebody is waiting for them.
3. The assistant replies. Each reply shows at once under its comment in the
   list. A blue mark in the toolbar counts the comments with a new reply, and
   so do the tab and the title of the window; in the list they are blue.
   `gn` goes to the next one, and a comment that you go to is no longer new.
   While no reply has come, the mark says that the comments are handed over.
4. To answer a reply, select the comment (`n` / `p`), press `A`, write, and
   press `Ctrl+Enter` again. The box shows the comment and the replies so far.
5. When you agree, the assistant changes the source. The window loads the new
   version by itself and the comment is marked as done.

### The commands

```bash
just-doc book.pdf --wait
```

opens the document if it is not open, waits for `Ctrl+Enter` in the window,
prints the open comments and ends. A comment is open when it is not done and
you spoke last. A `Ctrl+Enter` pressed while nobody waits is kept for the next
`--wait`. With `--timeout 100` the command gives up after 100 seconds with
exit status 2, for an assistant whose shell limits the run time; it then runs
the command again.

```bash
just-doc book.pdf --reply 2 "it converges only for a simple root" --from Ana
```

adds a reply to comment 2: its number in the `--read` output, or its `id` from
`--read --json`. `--from` is the name shown on the reply. `--reply` can be
given several times in one command. The export writes the replies into the
note of the highlight.

```bash
just-doc book.pdf --done 2
```

marks comment 2 as done (`done` in the JSON file). Its highlight leaves the
page and it is greyed in the list. At your next `Ctrl+Enter` the done comments
that you have looked at leave the list, so each round starts with what is
still open; nothing leaves the list before that. `D` shows them again, and the
top of the list says how many there are. The reply box (`A`) says whether the
comment is open or done. Answering a done comment opens it again, so the next
`--wait` prints it. `--done` can be combined
with `--reply` and given several times.

`--read` prints all comments with their replies, and marks each one that is
`(done)` or `(answered)`.

### When the document changes

When the file of an open document changes on disk (the markdown file was
edited, the PDF was compiled again), the window loads it again by itself and
stays on the page. It then looks for the text of every comment in the new
version:

- Text that only moved, to another line or page, gets its highlight at the
  new place.
- Text that was changed is found by the text around it. What stands there
  now is marked green, and the list shows both: ~~«teh»~~ → «the». `--read`
  prints the new text and the old one.
- When the text around it is gone too, the comment keeps its old place and
  the list says "text not found".

Each comment remembers 120 letters and digits before and after its text for
this. A changed text next to another changed text is found as one piece, so
two comments can then point to the same new sentence. A rectangle (`r`) stays
where it was drawn. The search runs in the window, so a document that changed
while it was not open is handled when it is opened next.

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

The lookup uses the position of the comment in the PDF. After compiling again
the window moves the comments to their text in the new PDF (see "When the
document changes"), so the lines stay right as long as the document is open
in the window, or is opened once before `--read`.

## Markdown files

`just-doc notes.md` converts the file to a PDF with [pandoc](https://pandoc.org)
and opens that, so pandoc must be installed (with [typst](https://typst.app)
or a LaTeX installation to make the PDF; typst is used when it is found). The
PDF is kept in `~/.cache/just-doc` and made again when the markdown file has
changed. Comments go to `notes.comments.json` next to the markdown file, and
`--export` writes `notes.commented.pdf` there.

A ```` ```mermaid ```` block is drawn as a diagram when `mmdc`
([mermaid-cli](https://github.com/mermaid-js/mermaid-cli)) is installed;
without it the block shows as code. The text in a diagram can be selected and
searched like the rest of the page.

`--read` adds the line in the markdown file for each comment. It finds the
line by searching for the selected text, so it also works after the file was
edited elsewhere; a text that occurs more than once gets its first line and a
note:

```
[1] p. 1  notes.md:3 (first of 2 places)
    text:    always converges
    comment: too strong
```

After the markdown file was edited, the highlights move to their text in the
new PDF (see "When the document changes").

## Third-party code

`web/pdfjs/` is a copy of [PDF.js](https://mozilla.github.io/pdf.js/) 4.10.38
(Apache License 2.0, see `web/pdfjs/LICENSE`).
