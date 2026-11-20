"""Tests for the week 8 web server (src/app.py) with a stub assistant, so no model is loaded.

Run:  .venv/bin/python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import pathlib
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import app  # noqa: E402

NOTE = "If you need medical help now, call 111. In an emergency, call 999."
SOURCE = {"n": 1, "title": "Register with a GP surgery", "heading": "How to register", "source": "NHS.uk",
          "url": "https://www.nhs.uk/nhs-services/gps/how-to-register-with-a-gp-surgery/",
          "public_updated_at": "2025-07-28", "fetched_at": "2026-10-28T10:08:02+00:00", "chunk": 7}


class StubAssistant:
    def __init__(self):
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        if "refuse" in question:
            return {"lang": "en", "refused": True, "reason": "low relevance", "health_note": None,
                    "answer": "I could not find an answer.", "sources": [], "raw": ""}
        if "boom" in question:
            raise RuntimeError("model failed")
        return {"lang": "pl", "refused": False, "reason": None, "raw": "secret raw output",
                "answer": f"Zarejestruj się online [1].\n\n{NOTE}", "health_note": NOTE,
                "sources": [SOURCE], "passages": [{"text": "full passage"}]}


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = StubAssistant()
        cls.backend = app.Backend(lambda: cls.stub).start()
        cls.backend.loaded.wait(5)
        cls.server = app.make_server(cls.backend, port=0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, body=None, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_page_and_static_files(self):
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b'id="question"', body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        for name, ctype in (("app.js", "javascript"), ("style.css", "text/css"), ("i18n.json", "json")):
            status, headers, _ = self.request(f"/static/{name}")
            self.assertEqual(status, 200, name)
            self.assertIn(ctype, headers["Content-Type"])

    def test_no_files_outside_web_folder(self):
        for path in ("/static/../src/app.py", "/static/%2e%2e/README.md", "/static/", "/README.md",
                     "/static/missing.css", "/data/processed/chunks.csv"):
            self.assertEqual(self.request(path)[0], 404, path)

    def test_status(self):
        status, _, body = self.request("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ready", "max_chars": app.MAX_CHARS})

    def test_answer_shape(self):
        status, headers, body = self.request("/api/ask", {"question": "  Jak zarejestrować\nsię u lekarza?  "})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        res = json.loads(body)
        self.assertEqual(self.stub.questions[-1], "Jak zarejestrować się u lekarza?")  # whitespace collapsed
        self.assertEqual(res["answer"], "Zarejestruj się online [1].")              # note split off
        self.assertEqual(res["health_note"], NOTE)
        self.assertEqual(res["lang"], "pl")
        self.assertFalse(res["refused"])
        self.assertEqual(res["sources"], [{k: SOURCE[k] for k in app.SOURCE_KEYS}])
        for hidden in ("raw", "passages", "reason"):  # internals stay on the server
            self.assertNotIn(hidden, res)

    def test_refusal(self):
        res = json.loads(self.request("/api/ask", {"question": "please refuse"})[2])
        self.assertTrue(res["refused"])
        self.assertEqual(res["sources"], [])
        self.assertIsNone(res["health_note"])

    def test_bad_requests(self):
        cases = [({"question": "   "}, "empty"), ({"question": "x" * (app.MAX_CHARS + 1)}, "too_long"),
                 ({"q": "hi"}, "bad_request"), ({"question": 5}, "bad_request"), (["hi"], "bad_request")]
        for body, code in cases:
            status, _, out = self.request("/api/ask", body)
            self.assertEqual((status, json.loads(out)["error"]), (400, code), body)
        status, _, out = self.request("/api/ask", raw=b"not json")
        self.assertEqual((status, json.loads(out)["error"]), (400, "bad_request"))
        status, _, out = self.request("/api/ask", raw=b"x" * (app.MAX_BODY + 1))
        self.assertEqual((status, json.loads(out)["error"]), (400, "too_long"))
        self.assertEqual(self.request("/api/other", {"question": "hi"})[0], 404)

    def test_server_error_hides_details(self):
        with contextlib.redirect_stderr(io.StringIO()):  # the server prints the expected traceback
            status, _, body = self.request("/api/ask", {"question": "boom"})
        self.assertEqual((status, json.loads(body)), (500, {"error": "server"}))


class LoadingTest(unittest.TestCase):
    def test_not_ready_and_failed_load(self):
        gate = threading.Event()
        loading = app.Backend(lambda: gate.wait(5) and StubAssistant()).start()
        self.assertEqual(loading.status(), "loading")
        gate.set()
        loading.loaded.wait(5)
        self.assertEqual(loading.status(), "ready")

        def fail():
            raise OSError("model files missing")
        broken = app.Backend(fail)
        with contextlib.redirect_stderr(io.StringIO()):  # the traceback is expected
            broken._load()  # in this thread, to keep the test simple
        self.assertEqual(broken.status(), "error")
        self.assertIn("model files missing", broken.error)

    def test_ask_while_loading_returns_503(self):
        gate = threading.Event()
        backend = app.Backend(lambda: gate.wait(5) and StubAssistant()).start()
        server = app.make_server(backend, port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/ask",
                                         data=json.dumps({"question": "hi"}).encode())
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 503)
            self.assertEqual(json.loads(ctx.exception.read())["error"], "loading")
        finally:
            gate.set()
            server.shutdown()
            server.server_close()


class PublicTest(unittest.TestCase):
    def test_note_only_removed_from_the_end(self):
        res = app.public({"lang": "en", "refused": False, "answer": "Call 111 [1].", "health_note": "Call 111.",
                          "sources": []})
        self.assertEqual(res["answer"], "Call 111 [1].")

    def test_uncited_answer_still_links_to_pages(self):
        passages = [{**SOURCE, "n": 99, "text": "passage"}, {**SOURCE, "title": "Second page", "text": "p2"}]
        res = app.public({"lang": "en", "refused": False, "answer": "No markers here.", "health_note": None,
                          "sources": [], "passages": passages})
        self.assertFalse(res["cited"])
        self.assertEqual([s["title"] for s in res["sources"]], [SOURCE["title"], "Second page"])
        self.assertTrue(all(s["n"] is None and "text" not in s for s in res["sources"]))

    def test_refusal_shows_no_pages(self):
        res = app.public({"lang": "en", "refused": True, "answer": "No.", "sources": [],
                          "passages": [{**SOURCE, "text": "p"}]})
        self.assertEqual(res["sources"], [])


if __name__ == "__main__":
    unittest.main()
