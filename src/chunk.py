"""Turn pages into retrievable chunks that respect the page's own sections.

Rules (kept simple so they are easy to describe in the methodology):
  * one chunk per h2/h3 section;
  * sections shorter than MIN_WORDS are merged into the next one on the same page;
  * sections longer than MAX_WORDS are split into windows with OVERLAP words;
  * every chunk text starts with "<page title> - <section heading>:" so the
    embedding sees the context a reader would see.
Output: data/processed/chunks.csv
"""
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIN_WORDS, MAX_WORDS, OVERLAP = 40, 200, 40


def merge_small(sections):
    merged, carry = [], None
    for s in sections:
        if carry:
            s = {"heading": carry["heading"] + " / " + s["heading"], "text": carry["text"] + " " + s["text"]}
            carry = None
        if len(s["text"].split()) < MIN_WORDS:
            carry = s
        else:
            merged.append(s)
    if carry:  # trailing short section joins the previous one, or stands alone
        if merged:
            merged[-1] = {"heading": merged[-1]["heading"] + " / " + carry["heading"],
                          "text": merged[-1]["text"] + " " + carry["text"]}
        else:
            merged.append(carry)
    return merged


def windows(words):
    if len(words) <= MAX_WORDS:
        return [words]
    step = MAX_WORDS - OVERLAP
    return [words[i:i + MAX_WORDS] for i in range(0, len(words) - OVERLAP, step)]


def main():
    pages = [json.loads(l) for l in open(ROOT / "data/processed/pages.jsonl")]
    rows = []
    for p in pages:
        for s_i, s in enumerate(merge_small(p["sections"])):
            for w_i, w in enumerate(windows(s["text"].split())):
                body = " ".join(w)
                rows.append({
                    "chunk_id": f"{p['id']}-{s_i:02d}-{w_i}",
                    "page_id": p["id"], "url": p["url"], "source": p["source"], "domain": p["domain"],
                    "title": p["title"], "heading": s["heading"],
                    "public_updated_at": p["public_updated_at"], "fetched_at": p["fetched_at"],
                    "words": len(w), "body": body,
                    "text": f"{p['title']} - {s['heading']}: {body}",
                })
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data/processed/chunks.csv", index=False)
    print(f"{len(pages)} pages -> {len(df)} chunks")
    print(df.groupby("domain").agg(pages=("page_id", "nunique"), chunks=("chunk_id", "count"),
                                   words=("words", "sum")).to_string())
    print("chunk words: median", int(df.words.median()), "min", df.words.min(), "max", df.words.max())


if __name__ == "__main__":
    main()
