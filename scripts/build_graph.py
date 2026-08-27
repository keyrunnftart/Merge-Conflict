#!/usr/bin/env python3
"""
Task 5, part 2: assemble the final graph -- nodes (132 comments + root)
with all derived fields from tasks 2-4, and edges (from edges.py) with
camp_relationship added per the frozen decision in
VISUAL_LANGUAGE_SIGNALS.md: same-camp / cross-camp / touches-unclassified.
"""
import json


def camp_of(node_id, comments_by_id, issue):
    if node_id == "root":
        return "not-applicable"  # root post wasn't run through the camp classifier
    return comments_by_id[node_id]["camp"]["effective_label"]


def relationship(camp_a, camp_b):
    real_camps = {"own-display-type", "grid-extension"}
    if camp_a not in real_camps or camp_b not in real_camps:
        return "touches-unclassified"
    return "same-camp" if camp_a == camp_b else "cross-camp"


def main():
    with open("data/processed/comments.json") as f:
        comments = json.load(f)
    with open("data/processed/issue.json") as f:
        issue = json.load(f)
    with open("data/processed/edges.json") as f:
        edges = json.load(f)

    comments_by_id = {c["id"]: c for c in comments}

    nodes = [{
        "id": "root",
        "type": "issue-root",
        "author": issue["author"],
        "created_at": issue["created_at"],
        "body_length": issue["body_length"],
        "reactions": issue["reactions"],
        "camp": "not-applicable",
    }]
    for c in comments:
        nodes.append({
            "id": c["id"],
            "type": "comment",
            "author": c["author"],
            "created_at": c["created_at"],
            "body_length": c["body_length"],
            "reactions": c["reactions"],
            "is_meeting_transcript": c["is_meeting_transcript"],
            "camp": c["camp"]["effective_label"],
            "sentiment_computed_not_used_visually": c["sentiment"]["compound"],
        })

    for e in edges:
        ca = camp_of(e["source"], comments_by_id, issue)
        cb = camp_of(e["target"], comments_by_id, issue)
        e["camp_relationship"] = relationship(ca, cb)

    graph = {"nodes": nodes, "edges": edges}
    with open("data/processed/graph.json", "w") as f:
        json.dump(graph, f, indent=2)

    from collections import Counter
    rel_counts = Counter(e["camp_relationship"] for e in edges)
    print(f"nodes: {len(nodes)}  edges: {len(edges)}")
    print("edge camp_relationship counts:", dict(rel_counts))

    degree = Counter()
    for e in edges:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    all_ids = [n["id"] for n in nodes]
    isolated = [i for i in all_ids if degree[i] == 0]
    max_deg = max(degree.values()) if degree else 0
    top = sorted(degree.items(), key=lambda kv: -kv[1])[:5]
    print(f"isolated nodes: {len(isolated)} / {len(nodes)}")
    print(f"max degree: {max_deg}")
    print("top 5 by degree (id, degree):", top)


if __name__ == "__main__":
    main()
