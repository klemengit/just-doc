#!/usr/bin/env python3
"""just-doc -- highlight and comment a PDF in a local window.

Comments are written to ``<name>.comments.json`` next to the PDF, so a script
(or a coding assistant) can read exactly which text each comment refers to.

Usage
-----
    just_doc.py book.pdf            open the PDF for commenting
    just_doc.py book.pdf --read     print the comments (with source lines if
                                   book.synctex.gz is next to the PDF)

Only the Python standard library is needed.
"""
import argparse
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
            if self.path.split("?")[0] != "/api/annotations":
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


def source_line(doc, rect):
    """Map a highlight to ``file:line`` in the TeX source via SyncTeX, if available."""
    if not shutil.which("synctex"):
        return None
    if not any(doc.with_suffix(ext).exists() for ext in (".synctex.gz", ".synctex")):
        return None
    spot = f"{rect['p']}:{rect['x'] + 2:.2f}:{rect['y'] + rect['h'] / 2:.2f}:{doc.name}"
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
        a["source"] = source_line(doc, a["rects"][0])
    if as_json:
        print(json.dumps(annots, ensure_ascii=False, indent=1))
        return
    for i, a in enumerate(annots, 1):
        where = f"p. {a['rects'][0]['p']}" + (f"  {a['source']}" if a["source"] else "")
        print(f"[{i}] {where}\n    text:    {a['text']}\n    comment: {a['comment'] or '(none)'}\n")
    print(f"{len(annots)} comment(s) in {comments_path(doc).name}")


def main():
    ap = argparse.ArgumentParser(description="Highlight and comment a PDF; comments are saved as JSON.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--read", action="store_true", help="print the comments instead of opening the PDF")
    ap.add_argument("--json", action="store_true", help="with --read: print JSON")
    ap.add_argument("--port", type=int, default=0, help="port (default: derived from the file path)")
    ap.add_argument("--no-window", action="store_true", help="start the server only")
    args = ap.parse_args()
    doc = args.pdf.resolve()
    if not doc.is_file():
        sys.exit(f"not found: {doc}")
    if args.read:
        read(doc, args.json)
    else:
        serve(doc, args.port, not args.no_window)


if __name__ == "__main__":
    main()
