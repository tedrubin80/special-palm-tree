"""Flask web interface for the search engine."""

from flask import Flask, render_template, request

from indexer import Indexer

app = Flask(__name__)

# Load index once at startup
indexer = Indexer()
try:
    indexer.load()
except FileNotFoundError:
    print("Warning: No index found. Run indexer.py first.")


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    results = []

    if query:
        terms = indexer.tokenize(query)
        scores = {}
        for term in terms:
            for url, title, score in indexer.index.get(term, []):
                if url not in scores:
                    scores[url] = {"score": 0, "title": title}
                scores[url]["score"] += score

        results = [
            {"url": url, "title": info["title"], "score": round(info["score"], 2)}
            for url, info in scores.items()
        ]
        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[:20]

    return render_template("search.html", query=query, results=results)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
