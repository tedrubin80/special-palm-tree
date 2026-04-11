"""Search interface for querying the inverted index."""

import sys

from indexer import Indexer


def search(query, top_n=10):
    """Search the index and return ranked results."""
    indexer = Indexer()
    indexer.load()

    terms = indexer.filter_stop_words(indexer.tokenize(query))
    if not terms:
        return []

    # Aggregate scores per URL across query terms
    scores = {}  # url -> {score, title}
    for term in terms:
        for url, title, score in indexer.index.get(term, []):
            if url not in scores:
                scores[url] = {"score": 0, "title": title}
            scores[url]["score"] += score

    # Sort by score descending
    results = [
        {"url": url, "title": info["title"], "score": info["score"]}
        for url, info in scores.items()
    ]
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_n]


def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f'Searching for: "{query}"\n')

    results = search(query)
    if not results:
        print("No results found.")
        return

    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r['score']}] {r['title']}")
        print(f"     {r['url']}\n")


if __name__ == "__main__":
    main()
