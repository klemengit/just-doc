#!/usr/bin/env python3
"""just-doc -- highlight and comment a PDF in a local window.

Comments are written to ``<name>.comments.json`` next to the PDF, so a script
(or a coding assistant) can read exactly which text each comment refers to.

Usage
-----
    just-doc book.pdf            open the PDF for commenting
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
import shutil
import subprocess
import sys
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
BROWSERS = ("chromium", "brave", "google-chrome-stable", "google-chrome", "chromium-browser")


def comments_path(doc):
    """Return the path of the comments file that belongs to ``doc``."""
    return doc.with_suffix(".comments.json")


def load_comments(doc):
    path = comments_path(doc)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"annots": []}


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

    writer = PdfWriter(clone_from=PdfReader(str(doc)))
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
            annot[NameObject("/T")] = author
            if a["comment"] and k == 0:
                annot[NameObject("/Contents")] = TextStringObject(a["comment"])
            writer.add_annotation(page_number=number - 1, annotation=annot)
            count += 1
    out = export_path(doc)
    writer.write(str(out))
    return out, count


def make_handler(doc):
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

        def do_GET(self):
            route = self.path.split("?")[0]
            if route == "/doc":
                self._send(200, doc.read_bytes(), "application/pdf")
            elif route == "/api/info":
                self._json(200, {"name": doc.name, "path": str(doc)})
            elif route == "/api/annotations":
                self._json(200, load_comments(doc))
            else:
                super().do_GET()

        def do_POST(self):
            route = self.path.split("?")[0]
            if route == "/api/export":
                try:
                    out, count = export(doc)
                except Exception as exc:  # noqa: BLE001
                    self._json(500, {"error": str(exc)})
                    return
                self._json(200, {"ok": True, "file": out.name, "n": count})
                return
            if route != "/api/annotations":
                self._json(404, {"error": "not found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                obj = json.loads(self.rfile.read(size).decode("utf-8"))
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


def already_serving(port, doc):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/info", timeout=1) as resp:
            return json.loads(resp.read()).get("path") == str(doc)
    except Exception:  # noqa: BLE001
        return False


def serve(doc, port, window):
    # The port is derived from the path, so one document keeps one address
    # (and with it the remembered page and zoom) between runs.
    first = port or 8700 + int(hashlib.sha1(str(doc).encode()).hexdigest()[:6], 16) % 1000
    for candidate in range(first, first + 20):
        url = f"http://127.0.0.1:{candidate}/"
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), make_handler(doc))
        except OSError:
            if already_serving(candidate, doc):
                print(f"already running: {url}")
                if window:
                    open_window(url)
                return
            continue
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


def read(doc, as_json):
    annots = load_comments(doc)["annots"]
    for a in annots:
        a["source"] = source_line(doc, a["rects"][0], centre=a.get("kind") == "box")
    if as_json:
        print(json.dumps(annots, ensure_ascii=False, indent=1))
        return
    for i, a in enumerate(annots, 1):
        where = f"p. {a['rects'][0]['p']}" + (f"  {a['source']}" if a["source"] else "")
        kind = "area" if a.get("kind") == "box" else "text"
        print(f"[{i}] {where}\n    {kind}:    {a['text'] or '(no text inside)'}\n    comment: {a['comment'] or '(none)'}\n")
    print(f"{len(annots)} comment(s) in {comments_path(doc).name}")


def main():
    ap = argparse.ArgumentParser(prog="just-doc", description="Highlight and comment a PDF; comments are saved as JSON.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--read", action="store_true", help="print the comments instead of opening the PDF")
    ap.add_argument("--json", action="store_true", help="with --read: print JSON")
    ap.add_argument("--export", action="store_true", help="write <name>.commented.pdf with the comments inside")
    ap.add_argument("--port", type=int, default=0, help="port (default: derived from the file path)")
    ap.add_argument("--no-window", action="store_true", help="start the server only")
    args = ap.parse_args()
    doc = args.pdf.resolve()
    if not doc.is_file():
        sys.exit(f"not found: {doc}")
    if args.export:
        try:
            out, count = export(doc)
        except RuntimeError as exc:
            sys.exit(str(exc))
        print(f"{count} annotation(s) -> {out}")
    elif args.read:
        read(doc, args.json)
    else:
        serve(doc, args.port, not args.no_window)


if __name__ == "__main__":
    main()
