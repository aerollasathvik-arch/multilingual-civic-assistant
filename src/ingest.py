"""Fetch every source page, keep a raw snapshot, and write one clean record per page.

Output: data/raw/<id>.(json|html) and data/processed/pages.jsonl
Each record keeps the section structure (h2/h3 headings) so chunks can carry
their heading, plus three dates: the publisher's own date, the publisher's
last technical update, and when we fetched it (for data-currency reporting).
"""
import hashlib
import json
import pathlib
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from sources import GOVUK, NHS

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "pages.jsonl"
UA = {"User-Agent": "MSc research prototype (multilingual civic assistant); polite crawler"}

# GOV.UK formats store text in different fields; order follows the rendered page.
GOVUK_TEXT_FIELDS = ["introduction", "introductory_paragraph", "body", "more_information",
                     "need_to_know", "other_ways_to_apply", "what_you_need_to_know"]


def page_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:10]


def sections_from_html(html, page_title):
    """Split HTML into (heading, text) sections at h2/h3 boundaries."""
    soup = BeautifulSoup(html, "html.parser")
    sections, heading, buf = [], page_title, []
    for el in soup.find_all(["h2", "h3", "p", "li", "td", "th"]):
        if el.name in ("h2", "h3"):
            if buf:
                sections.append({"heading": heading, "text": " ".join(buf)})
            heading, buf = el.get_text(" ", strip=True), []
        elif not el.find_parent(["li", "td", "th"]) or el.name in ("td", "th"):
            # skip nested elements already covered by their parent's text
            t = el.get_text(" ", strip=True)
            if t:
                buf.append(t)
    if buf:
        sections.append({"heading": heading, "text": " ".join(buf)})
    return sections


def fetch_govuk(path, domain):
    r = requests.get("https://www.gov.uk/api/content/" + path, headers=UA, timeout=30)
    r.raise_for_status()
    data = r.json()
    url = "https://www.gov.uk/" + path
    (RAW / f"{page_id(url)}.json").write_text(r.text)
    det = data.get("details", {})
    html = "".join(det.get(f, "") for f in GOVUK_TEXT_FIELDS if isinstance(det.get(f), str))
    for part in det.get("parts", []):
        html += f"<h2>{part['title']}</h2>{part['body']}"
    title = data.get("title", "")
    return {
        "id": page_id(url), "url": url, "source": "GOV.UK", "domain": domain,
        "title": title, "format": data.get("schema_name"),
        "public_updated_at": (data.get("public_updated_at") or "")[:10],
        "updated_at": (data.get("updated_at") or "")[:10],
        "sections": sections_from_html(html, title),
    }


def fetch_nhs(url, domain):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    (RAW / f"{page_id(url)}.html").write_text(r.text)
    soup = BeautifulSoup(r.text, "html.parser")
    reviewed = soup.find(string=lambda s: s and "Page last reviewed" in s)
    reviewed = reviewed.strip().split(":", 1)[1].strip() if reviewed else ""
    modified = ""
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            modified = (json.loads(s.string or "{}").get("dateModified") or modified)[:10]
        except (ValueError, AttributeError):
            pass
    article = soup.find("article") or soup.find("main")
    for junk in article.find_all(["aside", "nav", "footer", "script", "style"]):
        junk.decompose()
    title = soup.find("h1").get_text(" ", strip=True)
    # the lead sentence ("999 is for life-threatening emergencies...") sits outside <article>
    lede = soup.find(class_="nhsuk-lede-text")
    html = (str(lede) if lede and article not in lede.parents else "") + str(article)
    return {
        "id": page_id(url), "url": url, "source": "NHS.uk", "domain": domain,
        "title": title, "format": "nhs_article",
        "public_updated_at": datetime.strptime(reviewed, "%d %B %Y").strftime("%Y-%m-%d") if reviewed else "",
        "updated_at": modified,
        "sections": sections_from_html(html, title),
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = [(fetch_govuk, p, d) for d, ps in GOVUK.items() for p in ps]
    jobs += [(fetch_nhs, u, d) for d, us in NHS.items() for u in us]
    records, failed = [], []
    for fn, target, domain in jobs:
        try:
            rec = fn(target, domain)
            rec["fetched_at"] = fetched_at
            rec["words"] = sum(len(s["text"].split()) for s in rec["sections"])
            records.append(rec)
            print(f"ok   {rec['domain']:8} {rec['words']:5}w  {rec['title']}")
        except Exception as e:  # keep going; report at the end
            failed.append((target, repr(e)))
            print(f"FAIL {target}: {e}")
        time.sleep(0.5)
    with OUT.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\n{len(records)} pages written to {OUT.relative_to(ROOT)}; {len(failed)} failed")
    for t, e in failed:
        print("  failed:", t, e)


if __name__ == "__main__":
    main()
