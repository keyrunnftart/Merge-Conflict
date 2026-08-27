#!/usr/bin/env python3
"""
Task 5, part 1: real reply/relationship edges.

GitHub issue comments have NO native reply-to field (confirmed by
inspecting the raw API objects -- that's only present on PR review
comments). So edges here come from two real, checkable signals actually
present in the text itself:

  1. @mentions in a comment's OWN words (not inside a quote of someone
     else -- reuses camp.py's strip_quoted so a quoted "@x" isn't
     misread as the replier addressing x). Resolved to the mentioned
     user's most recent comment strictly before this one (or the root
     issue, if the mention is the root's author) -- a disclosed
     heuristic, not a guess: GitHub has no way to know which of a
     user's several comments a bare @mention refers to, so "their
     latest word in the conversation so far" is the most defensible
     single target.
  2. Blockquoted text (`> ...`) matched by exact substring (after
     whitespace normalization) against every earlier comment's body and
     the root issue body. Quotes under MIN_QUOTE_LEN chars are skipped
     -- a short quote ("> +1") matches too many things to mean anything.
     If a quote matches more than one earlier comment, the nearest
     preceding match is used as the edge target, and the ambiguity is
     recorded in the evidence rather than hidden.

No fuzzy matching, no NLP similarity -- if the text doesn't literally
appear, there's no edge. Conservative by design: a missed real reply is
better than a fabricated one, same standard applied everywhere else in
this pipeline.
"""
import json
import re
import sys
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("camp_mod", "scripts/camp.py")
camp_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camp_mod)
strip_quoted = camp_mod.strip_quoted

MIN_QUOTE_LEN = 20
MENTION_RE = re.compile(r"@([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)")


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_quotes(body):
    """Return list of quoted text blocks (contiguous '> ' lines, joined,
    markdown '>' stripped), longest-first isn't needed -- caller filters
    by length."""
    blocks = []
    current = []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith(">"):
            current.append(s.lstrip(">").strip())
        else:
            if current:
                blocks.append(" ".join(current))
                current = []
    if current:
        blocks.append(" ".join(current))
    return [normalize(b) for b in blocks if b.strip()]


def main():
    with open("data/raw/comments_raw.json") as f:
        raw_comments = json.load(f)
    with open("data/raw/issue_raw.json") as f:
        raw_issue = json.load(f)
    with open("data/processed/comments.json") as f:
        processed = json.load(f)

    # chronological order (API already returns ascending by created_at,
    # but don't rely on that silently)
    raw_comments = sorted(raw_comments, key=lambda c: c["created_at"])

    root_id = "root"
    root_author = raw_issue["user"]["login"]
    root_body_norm = normalize(raw_issue["body"] or "")

    # id -> (author, created_at, normalized_body), built incrementally so
    # "earlier" is enforced structurally, not just by field comparison.
    seen = []  # list of (id, author, created_at, body_norm)
    author_last_id = {}  # author -> most recent comment id seen so far
    edges = []

    for c in raw_comments:
        cid = c["id"]
        author = c["user"]["login"]
        body = c["body"] or ""
        own_text = strip_quoted(body)

        # --- @mentions (own words only) ---
        mentioned = set(MENTION_RE.findall(own_text))
        for target_user in mentioned:
            if target_user == author:
                continue
            if target_user in author_last_id:
                edges.append({
                    "source": cid,
                    "target": author_last_id[target_user],
                    "type": "mention",
                    "evidence": f"@{target_user}",
                })
            elif target_user == root_author:
                edges.append({
                    "source": cid,
                    "target": root_id,
                    "type": "mention",
                    "evidence": f"@{target_user}",
                })
            # else: mentioned user has no earlier node to point to -- no edge.

        # --- quote matches ---
        for q in extract_quotes(body):
            if len(q) < MIN_QUOTE_LEN:
                continue
            matches = []
            for (sid, sauthor, screated, sbody) in seen:
                if q in sbody:
                    matches.append(sid)
            if q in root_body_norm:
                matches.append(root_id)
            if matches:
                target = matches[-1]  # nearest preceding (seen is chronological)
                edges.append({
                    "source": cid,
                    "target": target,
                    "type": "quote",
                    "evidence": q[:80],
                    "ambiguous_candidates": len(matches) if len(matches) > 1 else None,
                })

        seen.append((cid, author, c["created_at"], normalize(body)))
        author_last_id[author] = cid

    with open("data/processed/edges.json", "w") as f:
        json.dump(edges, f, indent=2)

    n_mention = sum(1 for e in edges if e["type"] == "mention")
    n_quote = sum(1 for e in edges if e["type"] == "quote")
    n_ambig = sum(1 for e in edges if e.get("ambiguous_candidates"))
    connected_sources = len(set(e["source"] for e in edges))
    connected_targets = len(set(e["target"] for e in edges))
    all_nodes = set(c["id"] for c in raw_comments) | {root_id}
    touched = set(e["source"] for e in edges) | set(e["target"] for e in edges)
    isolated = all_nodes - touched

    print(f"total edges: {len(edges)} (mention={n_mention}, quote={n_quote}, "
          f"quote-ambiguous={n_ambig})")
    print(f"nodes with >=1 outgoing edge: {connected_sources} / {len(raw_comments)} comments")
    print(f"distinct edge targets: {connected_targets}")
    print(f"isolated nodes (no edge in or out): {len(isolated)} / {len(all_nodes)}")


if __name__ == "__main__":
    main()
