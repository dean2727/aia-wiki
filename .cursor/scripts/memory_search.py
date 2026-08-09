#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["chromadb>=1.0"]
# ///
"""Semantic search over cross-session memory (claude-mem index in Chroma Cloud).

Past work from Claude Code and Cursor sessions is compressed by claude-mem into
observations and session summaries, then indexed in Chroma Cloud. This queries
that index so an agent — including a Cursor cloud agent, which has no access to
the local claude-mem worker or its SQLite database — can recall prior context.

Requires CHROMA_API_KEY in the environment. Set it as a cloud-agent secret;
never commit it.

Run with uv (resolves chromadb automatically):
    uv run .cursor/scripts/memory_search.py "how is this deployed?"

Or with a plain interpreter that has chromadb installed:
    python3 .cursor/scripts/memory_search.py "how is this deployed?"

Examples:
    memory_search.py "railway env vars"                # current project only
    memory_search.py "auth design" --project kairos    # a specific project
    memory_search.py "chroma setup" --all-projects     # every project
    memory_search.py "deploy" --kind session_summary   # session-level intent only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def default_projects() -> list[str]:
    """Project labels this working tree plausibly recorded memory under.

    claude-mem derives a project name from the git repo root basename, falling
    back to the cwd basename outside a repo. Nested layouts therefore split:
    sessions run from a non-repo parent are filed under the parent's name while
    sessions run from the inner repo use the inner name (here, work landed under
    'wiki-project' even though this directory is its own repo named 'aia-wiki').
    Search every candidate rather than guessing one and silently finding nothing.
    """
    cwd = Path.cwd()
    candidates = [cwd.name, cwd.parent.name]
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        ).stdout.strip()
        if root:
            candidates.insert(0, Path(root).name)
    except (OSError, subprocess.TimeoutExpired):
        pass
    seen: dict[str, None] = {}
    for name in candidates:
        if name:
            seen.setdefault(name, None)
    return list(seen)

# The index is one collection spanning every project; `project` lives in
# document metadata, so queries must filter on it or a search here will surface
# unrelated work from other repos.
TENANT = "d42fe42f-30b4-492c-a960-5607a61b0d1a"
DATABASE = "deans-cross-session-memory"
COLLECTION = "cm__claude-mem"

# Chroma Cloud's free tier caps the Get action at 300 items per request and
# rejects the whole call above it. Queries are lighter, but stay well under.
MAX_RESULTS = 50


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search cross-session memory in Chroma Cloud.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", help="natural-language question (semantic, not keyword)")
    parser.add_argument(
        "--project",
        action="append",
        help="project to scope to; repeatable "
        "(default: this directory, its git root, and its parent)",
    )
    parser.add_argument("--all-projects", action="store_true", help="do not filter by project")
    parser.add_argument(
        "--kind",
        choices=["observation", "session_summary", "user_prompt"],
        help="restrict to one record type "
        "(session_summary = what a session accomplished; observation = a single finding)",
    )
    parser.add_argument("-n", type=int, default=8, help="number of results (default 8)")
    parser.add_argument("--chars", type=int, default=900, help="max chars printed per result")
    args = parser.parse_args()

    api_key = os.environ.get("CHROMA_API_KEY")
    if not api_key:
        print(
            "CHROMA_API_KEY is not set — cross-session memory is unavailable.\n"
            "Continue without it; do not invent prior context.",
            file=sys.stderr,
        )
        return 2

    try:
        import chromadb
    except ImportError:
        print(
            "chromadb is not installed. Run this with `uv run` (which resolves it\n"
            "automatically), or `pip install chromadb`.",
            file=sys.stderr,
        )
        return 2

    try:
        client = chromadb.CloudClient(
            tenant=os.environ.get("CHROMA_TENANT", TENANT),
            database=os.environ.get("CHROMA_DATABASE", DATABASE),
            api_key=api_key,
        )
        # No embedding_function argument on purpose: the documents were written
        # with chromadb's default (all-MiniLM-L6-v2). Passing a different one
        # yields a dimension mismatch, not merely worse ranking.
        collection = client.get_collection(COLLECTION)
    except Exception as err:  # noqa: BLE001 — surface any connection/auth failure plainly
        print(f"Could not reach the memory index: {type(err).__name__}: {err}", file=sys.stderr)
        return 1

    projects = args.project or default_projects()
    conditions = []
    if not args.all_projects:
        conditions.append(
            {"project": projects[0]} if len(projects) == 1
            else {"project": {"$in": projects}}
        )
    if args.kind:
        conditions.append({"doc_type": args.kind})
    where = None
    if len(conditions) == 1:
        where = conditions[0]
    elif conditions:
        where = {"$and": conditions}

    try:
        result = collection.query(
            query_texts=[args.query],
            n_results=min(args.n, MAX_RESULTS),
            where=where,
            include=["documents", "metadatas"],
        )
    except Exception as err:  # noqa: BLE001
        print(f"Query failed: {type(err).__name__}: {err}", file=sys.stderr)
        return 1

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]

    if not documents:
        scope = "any project" if args.all_projects else f"project(s) {', '.join(projects)}"
        print(f"No memory found for {scope}. Try --all-projects or a different phrasing.")
        return 0

    scope = "all projects" if args.all_projects else ", ".join(projects)
    print(f"{len(documents)} result(s) for {args.query!r} in {scope}\n")

    for doc, meta in zip(documents, metadatas):
        meta = meta or {}
        kind = meta.get("doc_type", "?")
        field = meta.get("field_type", "")
        header = f"[{kind}{'/' + field if field else ''}] {meta.get('project', '?')}"
        title = meta.get("title")
        if title:
            header += f" — {title}"
        print(header)
        body = (doc or "").strip()
        if len(body) > args.chars:
            body = body[: args.chars] + " …"
        print(textwrap.indent(body, "    "))
        print()

    print(
        "Note: these are AI-compressed summaries of past sessions, not source of truth.\n"
        "Verify anything load-bearing against the actual code before acting on it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
