"""Simple inverted index built from crawled pages."""

import json
import os
import re
from collections import defaultdict

from bs4 import BeautifulSoup

import config


class Indexer:
    """Builds and queries a basic inverted index over crawled HTML pages."""

    def __init__(self):
        self.index = defaultdict(list)  # term -> [(url, title, score)]
        self.documents = {}  # url -> {title, word_count}
        os.makedirs(config.INDEX_DIR, exist_ok=True)

    # --- Text processing ---

    @staticmethod
    def tokenize(text):
        """Lowercase and split text into word tokens."""
        return re.findall(r"[a-z0-9]+", text.lower())

    @staticmethod
    def extract_text(html):
        """Strip tags and return visible text from HTML."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)

    # --- Build index ---

    def build(self):
        """Scan crawled pages and build the inverted index."""
        if not os.path.isdir(config.PAGES_DIR):
            print("No crawled pages found. Run the crawler first.")
            return

        page_dirs = [
            d for d in os.listdir(config.PAGES_DIR)
            if os.path.isdir(os.path.join(config.PAGES_DIR, d))
        ]

        for page_hash in page_dirs:
            page_dir = os.path.join(config.PAGES_DIR, page_hash)
            meta_path = os.path.join(page_dir, "metadata.json")
            html_path = os.path.join(page_dir, "page.html")

            if not os.path.exists(meta_path) or not os.path.exists(html_path):
                continue

            with open(meta_path) as f:
                meta = json.load(f)
            with open(html_path, encoding="utf-8") as f:
                html = f.read()

            url = meta["url"]
            title = meta.get("title", "")
            text = self.extract_text(html)
            tokens = self.tokenize(text)
            title_tokens = set(self.tokenize(title))

            self.documents[url] = {"title": title, "word_count": len(tokens)}

            # Count term frequency
            tf = defaultdict(int)
            for token in tokens:
                tf[token] += 1

            for term, count in tf.items():
                # Boost score if term appears in the title
                score = count + (10 if term in title_tokens else 0)
                self.index[term].append((url, title, score))

        print(f"Indexed {len(self.documents)} documents, {len(self.index)} unique terms")
        self._save()

    def _save(self):
        """Persist index to disk as JSON."""
        index_path = os.path.join(config.INDEX_DIR, "inverted_index.json")
        with open(index_path, "w") as f:
            json.dump(dict(self.index), f)
        docs_path = os.path.join(config.INDEX_DIR, "documents.json")
        with open(docs_path, "w") as f:
            json.dump(self.documents, f, indent=2)
        print(f"Index saved to {config.INDEX_DIR}")

    def load(self):
        """Load a previously built index from disk."""
        index_path = os.path.join(config.INDEX_DIR, "inverted_index.json")
        docs_path = os.path.join(config.INDEX_DIR, "documents.json")
        with open(index_path) as f:
            self.index = defaultdict(list, json.load(f))
        with open(docs_path) as f:
            self.documents = json.load(f)
        print(f"Loaded index: {len(self.documents)} documents, {len(self.index)} terms")


if __name__ == "__main__":
    indexer = Indexer()
    indexer.build()
