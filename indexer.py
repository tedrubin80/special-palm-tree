"""Simple inverted index built from crawled pages."""

import json
import logging
import math
import os
import re
from collections import defaultdict

from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


class Indexer:
    """Builds and queries a basic inverted index over crawled HTML pages."""

    STOP_WORDS = frozenset(
        "a an and are as at be but by for from had has have he her his how i "
        "if in into is it its just me my no not of on or our out own s she so "
        "some such t than that the their them then there these they this to too "
        "us very was we were what when which who will with would you your".split()
    )

    def __init__(self):
        self.index = defaultdict(list)  # term -> [(url, title, score)]
        self.documents = {}  # url -> {title, word_count}
        os.makedirs(config.INDEX_DIR, exist_ok=True)

    # --- Text processing ---

    @staticmethod
    def tokenize(text):
        """Lowercase and split text into word tokens."""
        return re.findall(r"[a-z0-9]+", text.lower())

    @classmethod
    def filter_stop_words(cls, tokens):
        """Remove stop words from a token list."""
        return [t for t in tokens if t not in cls.STOP_WORDS]

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
            logger.warning("No crawled pages found. Run the crawler first.")
            return

        page_dirs = [
            d for d in os.listdir(config.PAGES_DIR)
            if os.path.isdir(os.path.join(config.PAGES_DIR, d))
        ]

        # First pass: collect term frequencies per document
        doc_tfs = {}  # url -> {term: raw_count}
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
            tokens = self.filter_stop_words(self.tokenize(text))
            title_tokens = set(self.filter_stop_words(self.tokenize(title)))

            # Store first 500 chars of visible text for search snippets
            snippet_text = text[:500] if len(text) > 500 else text

            self.documents[url] = {
                "title": title,
                "word_count": len(tokens),
                "title_tokens": list(title_tokens),
                "snippet_source": snippet_text,
            }

            tf = defaultdict(int)
            for token in tokens:
                tf[token] += 1
            doc_tfs[url] = dict(tf)

        # Compute document frequency for each term
        num_docs = len(self.documents)
        df = defaultdict(int)  # term -> number of docs containing it
        for tf in doc_tfs.values():
            for term in tf:
                df[term] += 1

        # Second pass: compute TF-IDF scores and build index
        for url, tf in doc_tfs.items():
            title = self.documents[url]["title"]
            title_tokens = set(self.documents[url]["title_tokens"])
            for term, count in tf.items():
                # Log-normalized TF * IDF
                tf_score = 1 + math.log(count)
                idf_score = math.log(1 + num_docs / df[term])
                score = tf_score * idf_score
                # Boost if term appears in the title
                if term in title_tokens:
                    score *= 2.0
                self.index[term].append((url, title, round(score, 4)))

        logger.info("Indexed %d documents, %d unique terms", len(self.documents), len(self.index))
        self._save()

    def _save(self):
        """Persist index to disk as JSON."""
        index_path = os.path.join(config.INDEX_DIR, "inverted_index.json")
        with open(index_path, "w") as f:
            json.dump(dict(self.index), f)
        docs_path = os.path.join(config.INDEX_DIR, "documents.json")
        with open(docs_path, "w") as f:
            json.dump(self.documents, f, indent=2)
        logger.info("Index saved to %s", config.INDEX_DIR)

    def load(self):
        """Load a previously built index from disk."""
        index_path = os.path.join(config.INDEX_DIR, "inverted_index.json")
        docs_path = os.path.join(config.INDEX_DIR, "documents.json")
        with open(index_path) as f:
            self.index = defaultdict(list, json.load(f))
        with open(docs_path) as f:
            self.documents = json.load(f)
        logger.info("Loaded index: %d documents, %d terms", len(self.documents), len(self.index))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    indexer = Indexer()
    indexer.build()
