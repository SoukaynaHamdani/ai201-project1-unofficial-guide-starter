"""
Milestone 4 - Step 1: EMBED chunks and load them into ChromaDB.

Reads data/processed/chunks.jsonl, embeds each chunk with all-MiniLM-L6-v2, and
stores the vectors in a local ChromaDB collection together with source metadata
(source_name, source_type, kind, title, url) so retrieval can attribute answers.

The collection uses cosine distance (hnsw:space=cosine) so distances land in the
0–2 range the milestone expects (good matches < 0.5).

Run:  python src/embed.py   (re-run any time chunks.jsonl changes)
"""

import json
import os

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = os.path.join("data", "processed", "chunks.jsonl")
DB_PATH = "chroma_db"
COLLECTION = "berkeley_guide"
MODEL_NAME = "all-MiniLM-L6-v2"


def main():
    if not os.path.exists(CHUNKS_PATH):
        raise SystemExit(f"{CHUNKS_PATH} not found. Run ingest.py + chunk.py first.")

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    if not chunks:
        raise SystemExit("No chunks found — nothing to embed.")
    print(f"Loaded {len(chunks)} chunks")

    # Embed locally (no API key, no rate limits)
    model = SentenceTransformer(MODEL_NAME)
    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks with {MODEL_NAME} ...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True).tolist()

    # Fresh collection each run so re-embedding never duplicates rows
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    coll = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    ids = [c["chunk_id"] for c in chunks]
    metadatas = [
        {
            "source_name": c["source_name"],
            "source_type": c["source_type"],
            "kind": c["kind"],
            "title": c["title"],
            "url": c["url"],
        }
        for c in chunks
    ]

    # ChromaDB prefers batched adds
    batch = 500
    for i in range(0, len(chunks), batch):
        coll.add(
            ids=ids[i:i + batch],
            embeddings=embeddings[i:i + batch],
            documents=texts[i:i + batch],
            metadatas=metadatas[i:i + batch],
        )

    print(f"Stored {coll.count()} chunks in ChromaDB at ./{DB_PATH} "
          f"(collection '{COLLECTION}')")


if __name__ == "__main__":
    main()
