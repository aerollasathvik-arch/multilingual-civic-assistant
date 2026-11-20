"""Week 8 web front-end (task T34): the week 6 assistant behind a small local web page.

    browser (web/index.html, app.js, style.css, i18n.json)
      -> POST /api/ask {"question": "..."}
      -> Assistant.ask (assistant.py, unchanged pipeline: direct mode, threshold 0.0052, yes/no check)
      -> JSON: answer, answer language, refusal flag, health note, source cards with dates

Design choices (see docs/week-08-report.md):
  * Python standard library only (http.server): no new dependencies, nothing to deploy.
  * Binds to 127.0.0.1 by default and calls no outside service, so questions never leave the machine
    (docs/ethics-notes.md). Questions are not logged or stored: the request log has method, path and
    status only.
  * The models take a minute or two to load, so the page is served at once and the assistant loads in
    a background thread; /api/status tells the page when it is ready.
  * One question at a time (a lock): the models are not thread-safe, and a laptop has one GPU.

Run:  .venv/bin/python src/app.py            then open http://127.0.0.1:8000
"""
import argparse
import json
import pathlib
import sys
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MAX_CHARS = 500     # longest question accepted; the longest test question is under 200 characters
MAX_BODY = 8_192    # bytes; 500 Arabic or Urdu characters are about 1 KB of UTF-8
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".svg": "image/svg+xml"}
SECURITY_HEADERS = {
    # Everything is served from this machine: no fonts, scripts or trackers from elsewhere.
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; object-src 'none'; "
                               "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
SOURCE_KEYS = ("n", "title", "heading", "url", "source", "public_updated_at", "fetched_at")


class Backend:
    """Loads the assistant in a background thread and answers one question at a time."""

    def __init__(self, factory):
        self.factory = factory
        self.assistant = None
        self.error = None
        self.loaded = threading.Event()
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._load, name="load-assistant", daemon=True).start()
        return self

    def _load(self):
        t0 = time.time()
        try:
            self.assistant = self.factory()
            print(f"assistant ready in {time.time() - t0:.0f} s", flush=True)
        except Exception as e:  # shown on /api/status so the page can say the assistant is unavailable
            self.error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
        finally:
            self.loaded.set()

    def status(self):
        if not self.loaded.is_set():
            return "loading"
        return "error" if self.error else "ready"

    def ask(self, question):
        with self.lock:
            t0 = time.time()
            result = self.assistant.ask(question)
            return public(result, time.time() - t0)


def public(result, seconds=None):
    """What the page needs from an Assistant result. Raw model output, passages and the refusal reason
    stay on the server: the page only shows the answer and the official pages behind it."""
    note = result.get("health_note")
    answer = result["answer"]
    if note:
        answer = answer.removesuffix("\n\n" + note)
    sources, cited = result.get("sources", []), True
    if not result["refused"] and not sources:
        # About 4% of answers carry no [n] markers (6/150 in week 6, 10/248 in week 7). Every answer must still link to the official
        # pages it was written from (docs/ethics-notes.md), so show the passages given to the model.
        sources, cited = [{**p, "n": None} for p in result.get("passages", [])], False
    return {"lang": result["lang"], "refused": bool(result["refused"]), "answer": answer, "health_note": note,
            "cited": cited, "sources": [{k: s.get(k) for k in SOURCE_KEYS} for s in sources],
            "seconds": None if seconds is None else round(seconds, 1)}


def validate(body):
    """Return (question, None) or (None, error code). Codes match the page's i18n keys."""
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "bad_request"
    question = data.get("question") if isinstance(data, dict) else None
    if not isinstance(question, str):
        return None, "bad_request"
    question = " ".join(question.split())  # collapse newlines and repeated spaces
    if not question:
        return None, "empty"
    if len(question) > MAX_CHARS:
        return None, "too_long"
    return question, None


def make_handler(backend):
    class Handler(BaseHTTPRequestHandler):
        server_version = "civic-assistant"
        sys_version = ""

        def log_message(self, fmt, *args):
            pass  # replaced by log_request below, which never includes the question

        def log_request(self, code="-", size="-"):
            code = getattr(code, "value", code)
            print(f"{time.strftime('%H:%M:%S')} {self.command} {self.path.split('?')[0]} {code}", flush=True)

        def send(self, status, body, ctype, cache="no-store"):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, status, obj):
            self.send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), TYPES[".json"])

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/status":
                return self.send_json(HTTPStatus.OK, {"status": backend.status(), "max_chars": MAX_CHARS})
            name = "index.html" if path in ("/", "/index.html") else path.removeprefix("/static/")
            if name == path:  # neither the page nor /static/...
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            file = (WEB / name).resolve()
            if file.parent != WEB.resolve() or file.suffix not in TYPES or not file.is_file():
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            self.send(HTTPStatus.OK, file.read_bytes(), TYPES[file.suffix], cache="no-cache")

        def do_POST(self):
            if self.path.split("?")[0] != "/api/ask":
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "too_long" if length > MAX_BODY
                                                               else "bad_request"})
            question, error = validate(self.rfile.read(length))
            if error:
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": error})
            status = backend.status()
            if status != "ready":
                return self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": status})
            try:
                return self.send_json(HTTPStatus.OK, backend.ask(question))
            except Exception:
                traceback.print_exc()  # the traceback has no question text in it
                return self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "server"})

    return Handler


def make_server(backend, host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), make_handler(backend))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1: only this computer can connect")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mode", choices=("direct", "translate"), default="direct",
                    help="answer language: direct (chosen in week 6) or NLLB back-translation")
    args = ap.parse_args(argv)
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(f"warning: listening on {args.host}; questions travel over the network unencrypted", file=sys.stderr)

    def load():
        sys.path.insert(0, str(ROOT / "src"))
        import torch  # heavy imports (torch, models) only once the page is up
        from assistant import Assistant
        from pipeline import SearchPipeline
        # NLLB on the Apple GPU when there is one: about 0.3 s per question instead of minutes on a busy CPU.
        device = None if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else None
        return Assistant(pipeline=SearchPipeline(translator_device=device), mode=args.mode)

    backend = Backend(load).start()
    server = make_server(backend, args.host, args.port)
    print(f"serving on http://{args.host}:{args.port}  (models loading in the background)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
