#!/usr/bin/env python3
"""
Task 3: per-comment sentiment.

Runs VADER (lexicon-based, good for informal/short text; a defensible
"lightweight sentiment analysis" per the brief) over data/raw/comments_raw.json
body text. Writes ONLY the derived scores into data/processed/comments.json
(and issue.json) — merged into the existing processed records, keyed by id.
Body text is read here but never written to any file this script produces.
"""
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def score(text):
    s = analyzer.polarity_scores(text or "")
    return {
        "compound": s["compound"],
        "pos": s["pos"],
        "neu": s["neu"],
        "neg": s["neg"],
    }

def main():
    with open("data/raw/comments_raw.json") as f:
        raw_comments = json.load(f)
    with open("data/raw/issue_raw.json") as f:
        raw_issue = json.load(f)
    with open("data/processed/comments.json") as f:
        processed = json.load(f)
    with open("data/processed/issue.json") as f:
        processed_issue = json.load(f)

    raw_by_id = {c["id"]: c["body"] for c in raw_comments}

    for p in processed:
        p["sentiment"] = score(raw_by_id[p["id"]])

    processed_issue["sentiment"] = score(raw_issue["body"])

    with open("data/processed/comments.json", "w") as f:
        json.dump(processed, f, indent=2)
    with open("data/processed/issue.json", "w") as f:
        json.dump(processed_issue, f, indent=2)

    compounds = [p["sentiment"]["compound"] for p in processed]
    compounds.sort()
    print(f"scored {len(processed)} comments")
    print(f"compound range: min={compounds[0]:.3f} max={compounds[-1]:.3f} "
          f"mean={sum(compounds)/len(compounds):.3f}")
    neg = sum(1 for c in compounds if c <= -0.05)
    neu = sum(1 for c in compounds if -0.05 < c < 0.05)
    pos = sum(1 for c in compounds if c >= 0.05)
    print(f"negative(<=-0.05): {neg}  neutral: {neu}  positive(>=0.05): {pos}")

if __name__ == "__main__":
    main()
