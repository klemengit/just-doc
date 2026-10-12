# just-doc

Read a PDF, select text, press a key, write what is wrong with it. Every comment
is saved to a JSON file together with the exact text and position it refers to,
so a script or a coding assistant can find the right place in the source.

```bash
python3 just_doc.py book.pdf          # open for commenting
python3 just_doc.py book.pdf --read   # print the comments
```

Needs only Python 3 (standard library). The window is a Chromium, Brave or
Chrome app window if one is installed, otherwise a tab in the default browser.

## Keys

| key | action |
|---|---|
| `a` | highlight the selected text |
| `s` | highlight the selection and write a comment, or edit the comment of the selected highlight |
| `d` | delete the selected highlight (click it first) |
| `u` | undo the last delete |
| `Ctrl` + wheel, `Ctrl` `+` / `-` / `0` | zoom the page around the pointer; the toolbar and comment list keep their size |
| `Esc` | deselect |

In the comment box, `Enter` saves and `Shift+Enter` starts a new line.

## Where comments go

`book.pdf` → `book.comments.json`, in the same folder, rewritten after every
change. Each entry holds the selected `text`, the `comment`, and `rects`: page
number `p` and position in PDF points measured from the top-left corner.

## LaTeX: comment → source line

If `book.synctex.gz` is next to the PDF (compile with `-synctex=1`), `--read`
adds the `.tex` file and line for each comment:

```
[1] p. 37  /path/vsebina/poglavje_02.tex:1228
    text:    ničle poiščemo z zajamčeno konvergentnim postopkom
    comment: ni ok beseda
```

Positions refer to the PDF as it was when you commented. Recompiling moves the
text, so comment on a copy of the PDF (and of its `.synctex.gz`) and read the
comments before replacing it.

## Third-party code

`web/pdfjs/` is a copy of [PDF.js](https://mozilla.github.io/pdf.js/) 4.10.38
(Apache License 2.0, see `web/pdfjs/LICENSE`).
