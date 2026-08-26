#!/usr/bin/env python3
"""
Turn data/raw/*.json (gitignored, contains full comment text) into
data/processed/*.json (committed): author, timestamp, body length, and
full reaction breakdown per comment. No comment body text is written here.

This is task 2's deliverable. Sentiment (task 3) and camp signal (task 4)
are separate later passes that may read body text from data/raw/ but must
themselves only persist derived scores, never raw text, to data/processed/.
"""
import json

def reaction_breakdown(reactions):
    return {k: v for k, v in reactions.items() if k not in ("url", "total_count")} | {
        "total_count": reactions["total_count"]
    }

def main():
    with open("data/raw/issue_raw.json") as f:
        issue = json.load(f)
    with open("data/raw/comments_raw.json") as f:
        comments = json.load(f)

    processed_issue = {
        "number": issue["number"],
        "title": issue["title"],
        "author": issue["user"]["login"],
        "author_type": issue["user"]["type"],
        "state": issue["state"],
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "body_length": len(issue["body"] or ""),
        "reactions": reaction_breakdown(issue["reactions"]),
        "html_url": issue["html_url"],
        "comments_field": issue["comments"],
    }

    processed_comments = []
    for c in comments:
        processed_comments.append({
            "id": c["id"],
            "author": c["user"]["login"],
            "author_type": c["user"]["type"],  # "User" vs "Bot" — matters for camp signal later
            "created_at": c["created_at"],
            "updated_at": c["updated_at"],
            "body_length": len(c["body"] or ""),
            "reactions": reaction_breakdown(c["reactions"]),
            "html_url": c["html_url"],
        })

    with open("data/processed/issue.json", "w") as f:
        json.dump(processed_issue, f, indent=2)
    with open("data/processed/comments.json", "w") as f:
        json.dump(processed_comments, f, indent=2)

    print(f"Wrote data/processed/issue.json and data/processed/comments.json")
    print(f"  {len(processed_comments)} comments processed, 0 raw body text retained in processed output")

if __name__ == "__main__":
    main()
