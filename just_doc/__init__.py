#!/usr/bin/env python3
"""just-doc -- highlight and comment a PDF in a local window.

Comments are written to ``<name>.comments.json`` next to the PDF, so a script
(or a coding assistant) can read exactly which text each comment refers to.

Usage
-----
    just-doc book.pdf            open the PDF for commenting
    just-doc notes.md            the same for a markdown file (needs pandoc)
    just-doc other.pdf           while a window is open: a new tab in it
    just-doc book.pdf --read     print the comments (with source lines if
                                 book.synctex.gz is next to the PDF)
    just-doc book.pdf --export   write book.commented.pdf with the comments
                                 as ordinary PDF annotations
"""
import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
PORT = 8700
MARKDOWN = (".md", ".markdown")
MERMAID = re.compile(r"^```+ *\{?\.?mermaid\}? *\n(.*?)^```+ *$", re.M | re.S)
BROWSERS = ("chromium", "brave", "google-chrome-stable", "google-chrome", "chromium-browser")


def comments_path(doc):
    """Return the path of the comments file that belongs to ``doc``."""
    return doc.with_suffix(".comments.json")


def load_comments(doc):
    path = comments_path(doc)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"annots": []}


def cache_dir():
    path = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "just-doc"
    path.mkdir(parents=True, exist_ok=True)
    return path


def draw_diagrams(text):
    """Replace the mermaid blocks of a markdown ``text`` with pictures.

    Each diagram is drawn once with mmdc (mermaid-cli) and kept in the cache
    folder under a name made from its content. Without mmdc, and for a
    diagram with an error, the block stays as it is and shows as code.
    """
    if not shutil.which("mmdc"):
        return text

    def picture(match):
        code = match.group(1)
        out = cache_dir() / ("mermaid-" + hashlib.sha1(code.encode()).hexdigest()[:16] + ".pdf")
        if not out.exists():
            src = out.with_suffix(".mmd")
            src.write_text(code, encoding="utf-8")
            res = subprocess.run(["mmdc", "-i", str(src), "-o", str(out), "--pdfFit"], capture_output=True)
            src.unlink()
            if res.returncode or not out.exists():
                return match.group(0)
        return f"![]({out})\n"

    return MERMAID.sub(picture, text)


def shown_pdf(doc):
    """Return the PDF that is shown for ``doc``.

    A PDF is shown as it is. A markdown file is converted with pandoc into a
    PDF in the cache folder, again whenever the markdown file is newer. Its
    mermaid diagrams are drawn first.
    """
    if doc.suffix.lower() not in MARKDOWN:
        return doc
    if not shutil.which("pandoc"):
        raise RuntimeError("a markdown file needs pandoc (https://pandoc.org) to be installed")
    out = cache_dir() / (hashlib.sha1(str(doc).encode()).hexdigest()[:16] + ".pdf")
    if not out.exists() or out.stat().st_mtime < doc.stat().st_mtime:
        cmd = ["pandoc", "--from=markdown", "-o", str(out)]
        if shutil.which("typst"):
            cmd.append("--pdf-engine=typst")
        text = draw_diagrams(doc.read_text(encoding="utf-8"))
        res = subprocess.run(cmd, cwd=doc.parent, input=text, capture_output=True, text=True, encoding="utf-8")
        if res.returncode:
            raise RuntimeError(f"pandoc could not convert {doc.name}:\n{res.stderr.strip()}")
    return out


def export_path(doc):
    """Return the path of the exported PDF that carries the comments."""
    return doc.with_suffix(".commented.pdf")


def export(doc):
    """Write a copy of ``doc`` with the comments as standard PDF highlights.

    The original PDF is not changed. Returns the output path and the number
    of annotations written.
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.annotations import Highlight, Rectangle
        from pypdf.generic import ArrayObject, FloatObject, NameObject, TextStringObject
    except ImportError as exc:
        raise RuntimeError("export needs the pypdf package (it comes with 'uv tool install')") from exc

    writer = PdfWriter(clone_from=PdfReader(str(shown_pdf(doc))))
    author = TextStringObject(getpass.getuser())
    count = 0
    for a in load_comments(doc)["annots"]:
        by_page = {}
        for r in a["rects"]:
            by_page.setdefault(r["p"], []).append(r)
        for k, (number, rects) in enumerate(sorted(by_page.items())):
            # stored positions are measured from the top-left corner; PDF counts from the bottom-left
            box = writer.pages[number - 1].cropbox
            left, top = float(box.left), float(box.top)
            quads, xs, ys = [], [], []
            for r in rects:
                x1, x2 = left + r["x"], left + r["x"] + r["w"]
                y1, y2 = top - r["y"], top - r["y"] - r["h"]
                quads += [x1, y1, x2, y1, x1, y2, x2, y2]
                xs += [x1, x2]
                ys += [y1, y2]
            bounds = (min(xs), min(ys), max(xs), max(ys))
            if a.get("kind") == "box":
                annot = Rectangle(rect=bounds)
                annot[NameObject("/C")] = ArrayObject(FloatObject(v) for v in (0.94, 0.5, 0.0))
            else:
                annot = Highlight(rect=bounds, quad_points=ArrayObject(FloatObject(round(v, 2)) for v in quads),
                                  highlight_color="ffb347" if a["comment"] else "ffe45c")
                if a.get("kind") == "strike":
                    annot[NameObject("/Subtype")] = NameObject("/StrikeOut")
                    annot[NameObject("/C")] = ArrayObject(FloatObject(v) for v in (0.82, 0.0, 0.0))
            annot[NameObject("/T")] = author
            if a["comment"] and k == 0:
                annot[NameObject("/Contents")] = TextStringObject(a["comment"])
            writer.add_annotation(page_number=number - 1, annotation=annot)
            count += 1
    out = export_path(doc)
    writer.write(str(out))
    return out, count


class Tabs:
    """The documents that are open in the window, one per tab."""

    def __init__(self):
        self.docs = {}       # id -> path, in the order of the tabs
        self.focus = None    # id of the document that was opened last
        self.opened = 0      # counts the open requests, so the window shows each one once
        self.version = 0     # counts every change of the list
        self.windows = 0     # windows that are listening for changes
        self.changed = threading.Condition()

    def open(self, doc):
        key = hashlib.sha1(str(doc).encode()).hexdigest()[:10]
        with self.changed:
            self.docs[key] = doc
            self.focus = key
            self.opened += 1
            self.version += 1
            self.changed.notify_all()

    def close(self, key):
        with self.changed:
            if self.docs.pop(key, None) is not None:
                self.version += 1
                self.changed.notify_all()

    def listing(self):
        tabs = [{"id": key, "name": doc.name, "path": str(doc)} for key, doc in self.docs.items()]
        return {"tabs": tabs, "focus": self.focus, "opened": self.opened}


def make_handler(tabs):
    class Handler(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript"}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB), **kwargs)

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _route(self):
            """Return the route and the document that the request is about.

            The document is named by ``?d=<id>``; without it the first one is taken.
            """
            url = urllib.parse.urlsplit(self.path)
            key = urllib.parse.parse_qs(url.query).get("d", [None])[0]
            docs = dict(tabs.docs)
            return url.path, key, docs.get(key) if key else next(iter(docs.values()), None)

        def _events(self):
            """Send the list of tabs to a window, now and after every change."""
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            with tabs.changed:
                tabs.windows += 1
            sent = None
            try:
                while True:
                    with tabs.changed:
                        if sent == tabs.version:
                            tabs.changed.wait(2)
                        version, listing = tabs.version, tabs.listing()
                    if version != sent:
                        self.wfile.write(f"data: {json.dumps(listing, ensure_ascii=False)}\n\n".encode("utf-8"))
                        sent = version
                    else:
                        # a line that the window ignores; writing it fails once the window is closed
                        self.wfile.write(b": still here\n\n")
                    self.wfile.flush()
            except OSError:
                pass
            finally:
                with tabs.changed:
                    tabs.windows -= 1

        def do_GET(self):
            route, _, doc = self._route()
            if route == "/api/events":
                self._events()
            elif route == "/api/tabs":
                self._json(200, {"app": "just-doc", "windows": tabs.windows, **tabs.listing()})
            elif route in ("/", "/view"):
                self.path = "/tabs.html" if route == "/" else "/index.html"
                super().do_GET()
            elif route in ("/doc", "/api/info", "/api/annotations") and doc is None:
                self._json(404, {"error": "this document is not open"})
            elif route == "/doc":
                try:
                    body = shown_pdf(doc).read_bytes()
                except RuntimeError as exc:
                    self._json(500, {"error": str(exc)})
                    return
                self._send(200, body, "application/pdf")
            elif route == "/api/info":
                self._json(200, {"name": doc.name, "path": str(doc)})
            elif route == "/api/annotations":
                self._json(200, load_comments(doc))
            else:
                super().do_GET()

        def _body(self):
            size = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(size).decode("utf-8"))

        def do_POST(self):
            route, key, doc = self._route()
            if route == "/api/open":
                # a web page cannot send JSON to another address, so this comes from the just-doc command
                if self.headers.get("Content-Type") != "application/json":
                    self._json(400, {"error": "JSON expected"})
                    return
                try:
                    new = Path(self._body()["path"])
                    if not new.is_file():
                        raise ValueError(f"not found: {new}")
                    shown_pdf(new)
                except Exception as exc:  # noqa: BLE001
                    self._json(400, {"error": str(exc)})
                    return
                windows = tabs.windows
                tabs.open(new)
                self._json(200, {"ok": True, "windows": windows})
                return
            if route == "/api/close":
                tabs.close(key)
                self._json(200, {"ok": True})
                return
            if route not in ("/api/export", "/api/annotations") or doc is None:
                self._json(404, {"error": "not found"})
                return
            if route == "/api/export":
                try:
                    out, count = export(doc)
                except Exception as exc:  # noqa: BLE001
                    self._json(500, {"error": str(exc)})
                    return
                self._json(200, {"ok": True, "file": out.name, "n": count})
                return
            try:
                obj = self._body()
                if not isinstance(obj.get("annots"), list):
                    raise ValueError("annots must be a list")
            except Exception as exc:  # noqa: BLE001
                self._json(400, {"error": str(exc)})
                return
            out = {"source": doc.name, "annots": obj["annots"]}
            tmp = comments_path(doc).with_suffix(".json.tmp")
            tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, comments_path(doc))
            self._json(200, {"ok": True, "n": len(out["annots"])})

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *args):
            pass

    return Handler


def open_window(url):
    """Open ``url`` in a chromeless app window, or in the default browser."""
    for name in BROWSERS:
        exe = shutil.which(name)
        if exe:
            subprocess.Popen([exe, f"--app={url}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return
    webbrowser.open(url)


def hand_over(url, doc):
    """Open ``doc`` as a tab of the just-doc that runs at ``url``.

    Returns the number of windows it has, or None when no just-doc answers there.
    """
    try:
        with urllib.request.urlopen(url + "api/tabs", timeout=1) as resp:
            if json.loads(resp.read()).get("app") != "just-doc":
                return None
    except Exception:  # noqa: BLE001
        return None
    req = urllib.request.Request(url + "api/open", data=json.dumps({"path": str(doc)}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["windows"]
    except urllib.error.HTTPError as exc:
        raise RuntimeError(json.loads(exc.read()).get("error", str(exc))) from exc


def serve(doc, port, window):
    # One just-doc serves all open documents: the first command starts it, and every later
    # command hands its document over to it as a new tab and returns.
    first = port or PORT
    for candidate in range(first, first + 20):
        url = f"http://127.0.0.1:{candidate}/"
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), make_handler(tabs := Tabs()))
        except OSError:
            windows = hand_over(url, doc)
            if windows is None:
                continue
            print(f"{doc.name}: new tab in the running just-doc, {url}")
            if window and not windows:
                open_window(url)
            return
        tabs.open(doc)
        print(f"{doc.name}: {url}  (comments -> {comments_path(doc).name}, Ctrl+C to stop)")
        if window:
            open_window(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return
    sys.exit("no free port found")


def source_line(doc, rect, centre=False):
    """Map a highlight to ``file:line`` in the TeX source via SyncTeX, if available.

    A text highlight is looked up at its start, a rectangle at its centre.
    """
    if not shutil.which("synctex"):
        return None
    if not any(doc.with_suffix(ext).exists() for ext in (".synctex.gz", ".synctex")):
        return None
    x = rect["x"] + (rect["w"] / 2 if centre else 2)
    spot = f"{rect['p']}:{x:.2f}:{rect['y'] + rect['h'] / 2:.2f}:{doc.name}"
    res = subprocess.run(["synctex", "edit", "-o", spot], cwd=doc.parent, capture_output=True, text=True)
    name = line = None
    for row in res.stdout.splitlines():
        if row.startswith("Input:") and name is None:
            name = os.path.normpath(row[6:])
        elif row.startswith("Line:") and line is None:
            line = row[5:]
    return f"{name}:{line}" if name and line else None


def markdown_lines(doc, annots):
    """Find the line of each comment's text in the markdown file ``doc``.

    Only letters and digits are compared, so the markup, the line breaks and
    the hyphenation of the PDF do not matter. A text that occurs more than
    once gets the line of its first occurrence and a note.
    """
    chars, lines = [], []
    for number, row in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        for ch in row:
            if ch.isalnum():
                chars.append(ch.lower())
                lines.append(number)
    body = "".join(chars)
    for a in annots:
        key = "".join(ch.lower() for ch in a["text"] if ch.isalnum())[:80]
        at = body.find(key) if len(key) > 2 else -1
        if at < 0:
            a["source"] = None
            continue
        count = body.count(key)
        a["source"] = f"{doc.name}:{lines[at]}" + (f" (first of {count} places)" if count > 1 else "")


def read(doc, as_json):
    annots = load_comments(doc)["annots"]
    if doc.suffix.lower() in MARKDOWN:
        markdown_lines(doc, annots)
    else:
        for a in annots:
            a["source"] = source_line(doc, a["rects"][0], centre=a.get("kind") == "box")
    if as_json:
        print(json.dumps(annots, ensure_ascii=False, indent=1))
        return
    for i, a in enumerate(annots, 1):
        where = f"p. {a['rects'][0]['p']}" + (f"  {a['source']}" if a["source"] else "")
        kind = {"box": "area", "strike": "delete"}.get(a.get("kind"), "text")
        print(f"[{i}] {where}\n    {kind + ':':<8} {a['text'] or '(no text inside)'}\n    comment: {a['comment'] or '(none)'}\n")
    print(f"{len(annots)} comment(s) in {comments_path(doc).name}")


def main():
    ap = argparse.ArgumentParser(prog="just-doc", description="Highlight and comment a PDF or a markdown file; comments are saved as JSON.")
    ap.add_argument("pdf", type=Path, metavar="file", help="a PDF or a markdown file")
    ap.add_argument("--read", action="store_true", help="print the comments instead of opening the PDF")
    ap.add_argument("--json", action="store_true", help="with --read: print JSON")
    ap.add_argument("--export", action="store_true", help="write <name>.commented.pdf with the comments inside")
    ap.add_argument("--port", type=int, default=0, help=f"port (default: {PORT})")
    ap.add_argument("--no-window", action="store_true", help="start the server only")
    args = ap.parse_args()
    doc = args.pdf.resolve()
    if not doc.is_file():
        sys.exit(f"not found: {doc}")
    try:
        if args.export:
            out, count = export(doc)
            print(f"{count} annotation(s) -> {out}")
        elif args.read:
            read(doc, args.json)
        else:
            shown_pdf(doc)
            serve(doc, args.port, not args.no_window)
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
