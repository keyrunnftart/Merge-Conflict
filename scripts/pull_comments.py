#!/usr/bin/env python3
"""
Pull the FULL comment set for w3c/csswg-drafts#9041 ("Alternative masonry
path forward") via the GitHub REST API, unauthenticated.

Writes:
  - data/raw/issue_raw.json       (full issue object, gitignored)
  - data/raw/comments_raw.json    (full array of ALL comment objects, gitignored)

This script does NOT compute derived data. It only pulls and saves raw
payloads so later steps (sentiment, camp signal, graph) can be re-run
against a stable local snapshot instead of re-hitting the API.
"""
import json
import sys
import time
import urllib.request
import urllib.error

OWNER = "w3c"
REPO = "csswg-drafts"
ISSUE = 9041
API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "merge-conflict-agent-data-pull",
}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        link = resp.headers.get("Link", "")
        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        return json.loads(body), link, remaining


def next_page_url(link_header):
    if not link_header:
        return None
    for part in link_header.split(","):
        segs = part.split(";")
        if len(segs) < 2:
            continue
        url = segs[0].strip().strip("<>")
        rel = segs[1].strip()
        if rel == 'rel="next"':
            return url
    return None


def main():
    # 1. Issue root object (the opening post — not a "comment" but context).
    issue_url = f"{API}/repos/{OWNER}/{REPO}/issues/{ISSUE}"
    issue, _, remaining = get(issue_url)
    print(f"Issue: #{issue['number']} \"{issue['title']}\"", file=sys.stderr)
    print(f"  state={issue['state']} created={issue['created_at']} "
          f"comments={issue['comments']} rate_limit_remaining={remaining}",
          file=sys.stderr)
    with open("data/raw/issue_raw.json", "w") as f:
        json.dump(issue, f, indent=2)

    # 2. Full paginated comment list.
    all_comments = []
    url = f"{API}/repos/{OWNER}/{REPO}/issues/{ISSUE}/comments?per_page=100&page=1"
    page_num = 1
    while url:
        page, link, remaining = get(url)
        print(f"  page {page_num}: {len(page)} comments "
              f"(rate_limit_remaining={remaining})", file=sys.stderr)
        all_comments.extend(page)
        url = next_page_url(link)
        page_num += 1
        time.sleep(0.5)  # be polite

    with open("data/raw/comments_raw.json", "w") as f:
        json.dump(all_comments, f, indent=2)

    print(f"\nTOTAL comments pulled: {len(all_comments)}", file=sys.stderr)
    print(f"issue.comments field said: {issue['comments']}", file=sys.stderr)
    if len(all_comments) != issue["comments"]:
        print("  WARNING: mismatch between pulled count and issue.comments field!",
              file=sys.stderr)


if __name__ == "__main__":
    main()
