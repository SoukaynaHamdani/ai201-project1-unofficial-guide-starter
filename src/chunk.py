"""
Milestone 3 - Step 2: CHUNKING

Reads data/processed/documents.jsonl and splits each document into chunks,
carrying all source metadata onto every chunk. Writes data/processed/chunks.jsonl.

Chunking strategy (justify this in planning.md / README.md):
  - Long-form docs (html, pdf, txt): sliding window of CHUNK_SIZE chars with
    OVERLAP chars of overlap, split on paragraph/sentence boundaries when possible.
  - Short atomic docs (csv reviews, reddit comments are already short): kept whole
    if they fit in one chunk, so we never split a single review mid-sentence.

Run:  python src/chunk.py
"""

import json
import os

IN_PATH = os.path.join("data", "processed", "documents.jsonl")
OUT_PATH = os.path.join("data", "processed", "chunks.jsonl")

CHUNK_SIZE = 800     # characters
OVERLAP = 150        # characters of overlap between consecutive chunks


def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """Sliding-window character chunker that prefers to break on whitespace."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            # back up to the nearest space so we don't cut a word in half
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap  # step forward, keeping `overlap` chars of context
    return chunks


def main():
    if not os.path.exists(IN_PATH):
        raise SystemExit(f"{IN_PATH} not found. Run `python src/ingest.py` first.")

    out = []
    with open(IN_PATH, "r", encoding="utf-8") as f:
        documents = [json.loads(line) for line in f if line.strip()]

    for doc in documents:
        pieces = chunk_text(doc["text"])
        for i, piece in enumerate(pieces):
            out.append({
                "chunk_id": f"{doc['id']}-c{i:03d}",
                "text": piece,
                # ---- metadata carried onto every chunk (used at retrieval time) ----
                "source_name": doc["source_name"],
                "source_type": doc["source_type"],
                "kind": doc["kind"],
                "title": doc["title"],
                "url": doc["url"],
            })

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for c in out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # quick summary
    by_type = {}
    for c in out:
        by_type[c["source_type"]] = by_type.get(c["source_type"], 0) + 1
    print(f"DONE. {len(documents)} documents -> {len(out)} chunks")
    print("Chunks by source_type:", by_type)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
