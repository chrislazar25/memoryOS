"""
retrieval.py — TF-IDF cosine similarity retrieval for MemoryOS.

Each memory is embedded as a single text blob:
    commit_message + reason + tradeoffs (chosen / rejected / known_downsides) + tags

A TF-IDF matrix is built at query time over all memories for the repo.
The query is transformed into the same space and cosine similarity is computed.

Usage
-----
    python retrieval.py "your natural language query" --repo demo-api [--top 3] [--db <path>]

Flags
-----
  --repo <name>   Repo name to search (required)
  --top <n>       Number of results to return (default: 3)
  --db <path>     Path to the SQLite database (default: memories.db next to this file)
"""

import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import store

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print(
        "sklearn is required: pip install scikit-learn",
        file=sys.stderr,
    )
    sys.exit(1)


def _flatten_tradeoffs(tradeoffs: dict) -> str:
    """Flatten tradeoffs dict to a single string for embedding."""
    parts = []
    for key in ("chosen", "rejected", "known_downsides"):
        val = tradeoffs.get(key, "")
        if isinstance(val, list):
            parts.extend(val)
        elif val:
            parts.append(val)
    return " ".join(parts)


def _embed_text(mem: dict) -> str:
    """Combine all meaningful fields into one string for TF-IDF."""
    parts = [
        mem.get("commit_message", ""),
        mem.get("reason", ""),
        _flatten_tradeoffs(mem.get("tradeoffs", {})),
        " ".join(mem.get("tags", [])),
    ]
    return " ".join(p for p in parts if p)


def retrieve(
    query: str,
    repo: str,
    top_k: int = 3,
    db_path: Path | None = None,
) -> list[dict]:
    """
    Return up to *top_k* memories ranked by TF-IDF cosine similarity to *query*.

    Each result dict contains:
        score, commit_hash, commit_message, reason, decision_type, tradeoffs, tags
    """
    kwargs = {"db_path": db_path} if db_path else {}
    memories = store.fetch_all(repo, **kwargs)

    if not memories:
        return []

    corpus = [_embed_text(m) for m in memories]

    vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    # Fit on corpus + query together so query terms are in the vocabulary
    tfidf_matrix = vectorizer.fit_transform(corpus + [query])
    doc_vectors = tfidf_matrix[:-1]
    query_vector = tfidf_matrix[-1]

    scores = cosine_similarity(query_vector, doc_vectors).flatten()

    # Pair scores with memories and sort descending
    ranked = sorted(
        zip(scores, memories),
        key=lambda x: x[0],
        reverse=True,
    )

    results = []
    for score, mem in ranked[:top_k]:
        results.append(
            {
                "score": round(float(score), 4),
                "commit_hash": mem["commit_hash"],
                "commit_message": mem["commit_message"],
                "decision_type": mem["decision_type"],
                "reason": mem["reason"],
                "tradeoffs": mem["tradeoffs"],
                "tags": mem["tags"],
            }
        )
    return results


def _print_results(results: list[dict], query: str) -> None:
    if not results:
        print("No memories found.")
        return

    print(f"Query: \"{query}\"\n")
    print("=" * 72)
    for i, r in enumerate(results, 1):
        short = r["commit_hash"][:7]
        print(f"  #{i}  score={r['score']:.4f}  [{short}]  {r['commit_message']}")
        print(f"       type: {r['decision_type']}")
        print()
        print("  Reason:")
        for line in textwrap.wrap(r["reason"], width=68, initial_indent="    ", subsequent_indent="    "):
            print(line)
        print()
        t = r["tradeoffs"]
        chosen = t.get("chosen", "")
        if chosen:
            print(f"  Chosen:  {chosen}")
        rejected = t.get("rejected", "")
        if isinstance(rejected, list):
            rejected = "; ".join(rejected)
        if rejected:
            for line in textwrap.wrap(f"  Rejected: {rejected}", width=72, subsequent_indent="           "):
                print(line)
        downsides = t.get("known_downsides", "")
        if downsides:
            for line in textwrap.wrap(f"  Downsides: {downsides}", width=72, subsequent_indent="            "):
                print(line)
        print()
        print(f"  Tags: {', '.join(r['tags'])}")
        print("-" * 72)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    query = args[0]
    repo = None
    top_k = 3
    db_path = None

    i = 1
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo = args[i + 1]
            i += 2
        elif args[i] == "--top" and i + 1 < len(args):
            top_k = int(args[i + 1])
            i += 2
        elif args[i] == "--db" and i + 1 < len(args):
            db_path = Path(args[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)

    if not repo:
        print("Error: --repo is required.", file=sys.stderr)
        sys.exit(1)

    results = retrieve(query, repo, top_k=top_k, db_path=db_path)
    _print_results(results, query)


if __name__ == "__main__":
    main()
