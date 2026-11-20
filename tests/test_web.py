"""Static checks on the week 8 page (T35): translations complete, labels present, colour contrast.

These are the WCAG 2.2 AA checks that can be automated without a browser. The manual checks (keyboard,
screen reader, zoom, right-to-left reading) are in docs/accessibility.md.
"""
import ast
import csv
import json
import pathlib
import re
import unittest
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
I18N = json.loads((WEB / "i18n.json").read_text(encoding="utf-8"))
LANGS = I18N["order"]
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")


def assistant_constant(name):
    """Read a dict constant from src/assistant.py without importing it (that would load torch)."""
    tree = ast.parse((ROOT / "src/assistant.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


# ---------- contrast (WCAG 2.x relative luminance) ----------
def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


TOKENS = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;", CSS.split("}", 1)[0]))

# (foreground, background, where it is used). Text needs 4.5:1 (1.4.3).
TEXT_PAIRS = [
    ("ink", "bg", "body text"), ("ink", "surface", "source cards, footer"),
    ("muted", "bg", "hints, status, answer language"), ("muted", "surface", "card labels, dates, licence"),
    ("link", "bg", "links, example buttons"), ("link", "surface", "links on source cards"),
    ("link-visited", "bg", "visited links"), ("link-visited", "surface", "visited links on cards"),
    ("brand-ink", "brand", "header text, Ask button"), ("ink", "notice-bg", "research notice"),
    ("ink", "health-bg", "NHS 111/999 note"), ("error", "bg", "error message"),
    ("ink", "focus-halo", "skip link"),
]
# Borders of controls and focus indicators need 3:1 against what is next to them (1.4.11, 2.4.13 guidance).
UI_PAIRS = [
    ("ink", "bg", "text box and select border"), ("line", "bg", "example button border"),
    ("error", "bg", "invalid text box border"), ("focus-ring", "bg", "focus ring on the page"),
    ("focus-ring", "surface", "focus ring on cards and footer"), ("focus-halo", "brand", "focus halo on button and header"),
    ("brand", "bg", "Ask button against the page"),
]


class ContrastTest(unittest.TestCase):
    def test_tokens_found(self):
        for fg, bg, _ in TEXT_PAIRS + UI_PAIRS:
            self.assertIn(fg, TOKENS)
            self.assertIn(bg, TOKENS)

    def test_text_contrast(self):
        for fg, bg, where in TEXT_PAIRS:
            ratio = contrast(TOKENS[fg], TOKENS[bg])
            self.assertGreaterEqual(ratio, 4.5, f"{where}: --{fg} on --{bg} is {ratio:.2f}:1")

    def test_non_text_contrast(self):
        for fg, bg, where in UI_PAIRS:
            ratio = contrast(TOKENS[fg], TOKENS[bg])
            self.assertGreaterEqual(ratio, 3.0, f"{where}: --{fg} on --{bg} is {ratio:.2f}:1")


# ---------- translations ----------
class TranslationTest(unittest.TestCase):
    def test_every_language_has_every_key(self):
        keys = set(I18N["en"])
        for lang in LANGS:
            self.assertEqual(set(I18N[lang]), keys, lang)
            for key, value in I18N[lang].items():
                self.assertTrue(value, f"{lang}.{key} is empty")

    def test_placeholders_match_english(self):
        for key, en in I18N["en"].items():
            if isinstance(en, str):
                want = set(re.findall(r"\{\w+\}", en))
                for lang in LANGS:
                    self.assertEqual(set(re.findall(r"\{\w+\}", I18N[lang][key])), want, f"{lang}.{key}")

    def test_keys_used_by_page_exist(self):
        used = set(re.findall(r'data-i18n="([\w]+)"', HTML))
        used |= set(re.findall(r'\bt\("(\w+)"', JS))
        used |= {f"err_{c}" for c in ("empty", "too_long", "loading", "error", "server", "network", "bad_request")}
        missing = used - set(I18N["en"])
        self.assertFalse(missing, f"keys used but not translated: {missing}")

    def test_health_note_matches_assistant(self):
        note = assistant_constant("HEALTH_NOTE")
        for lang in LANGS:
            self.assertEqual(I18N[lang]["help"], note[lang], lang)

    def test_examples_are_test_set_questions(self):
        with open(ROOT / "eval/queries.csv", encoding="utf-8") as f:
            rows = {(r["qid"], r["lang"]): r["question"] for r in csv.DictReader(f)}
        for lang in LANGS:
            want = [rows[(qid, lang)] for qid in ("M01", "H02", "S06")]
            self.assertEqual(I18N[lang]["examples_list"], want, lang)

    def test_rtl_languages(self):
        self.assertEqual(sorted(I18N["rtl"]), ["ar", "ur"])
        self.assertEqual(sorted(LANGS), sorted(assistant_constant("REFUSAL")))


# ---------- page structure ----------
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = PageParser()
        p.feed(HTML)
        cls.tags = p.tags

    def find(self, tag):
        return [a for t, a in self.tags if t == tag]

    def test_language_and_direction_declared(self):
        html = self.find("html")[0]
        self.assertEqual((html.get("lang"), html.get("dir")), ("en", "ltr"))
        self.assertIn("root.lang = lang", JS)
        self.assertIn("root.dir = dirOf(lang)", JS)

    def test_zoom_not_blocked(self):
        viewport = [a for a in self.find("meta") if a.get("name") == "viewport"][0]["content"]
        self.assertNotIn("user-scalable=no", viewport)
        self.assertNotIn("maximum-scale", viewport)

    def test_form_controls_have_labels(self):
        labelled = {a["for"] for a in self.find("label")}
        for tag in ("textarea", "select", "input"):
            for a in self.find(tag):
                self.assertIn(a.get("id"), labelled, f"<{tag} id={a.get('id')}> has no <label>")

    def test_one_h1_and_landmarks(self):
        names = [t for t, _ in self.tags]
        self.assertEqual(names.count("h1"), 1)
        for landmark in ("header", "main", "footer"):
            self.assertIn(landmark, names)

    def test_live_region_for_status(self):
        status = [a for t, a in self.tags if a.get("id") == "status"][0]
        self.assertEqual(status.get("role"), "status")

    def test_new_tab_links_say_so(self):
        for a in self.find("a"):
            if a.get("target") == "_blank":
                self.assertIn("noopener", a.get("rel", ""))
        self.assertEqual(HTML.count('target="_blank"'), HTML.count('data-i18n="new_tab"'))
        self.assertIn('t("new_tab")', JS)

    def test_no_inline_script_or_style(self):
        """The Content-Security-Policy allows only files from this server, so inline code would be blocked."""
        for a in self.find("script"):
            self.assertIn("src", a)
        self.assertFalse(self.find("style"))
        self.assertFalse([a for _, a in self.tags if "style" in a or any(k.startswith("on") for k in a)])

    def test_model_text_never_parsed_as_html(self):
        found = re.findall(r"\.(?:inner|outer)HTML\s*\+?=|insertAdjacentHTML\s*\(|document\.write\s*\(", JS)
        self.assertEqual(found, [])

    def test_targets_at_least_24px(self):
        """2.5.8 Target Size (Minimum): buttons and the select are 2.75rem = 44px tall."""
        for selector in (".button", ".example", "select"):
            block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS).group(1)
            self.assertIn("min-height: 2.75rem", block, selector)


if __name__ == "__main__":
    unittest.main()
